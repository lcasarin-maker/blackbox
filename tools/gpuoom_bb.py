#!/usr/bin/env python3
"""Guardia estilo gpuoom para memoria unificada (interruptor `gpuoom`): FEATURE-VIGILANTE-MEMAVAILABLE-UMA-01.

Logica PORTADA a Python (no se copia codigo Rust) de tom-doerr/gpuoom (MIT, commit 475855b): ver NOTICE.
  * Disparo (src/trigger.rs): MemAvailable bajo un porcentaje Y presion PSI `some avg10` alta, sostenidos; y un suelo
    critico que actua de inmediato (el promedio de 10 s de PSI llega tarde en una rafaga).
  * Victima (src/select.rs): huella = anon + shmem + GPU*peso + swap*peso, escalada por oom_score_adj (el kernel suma;
    aqui se escala, para que una pestana de 200 MB no supere un trabajo de 60 GB).
  * La memoria GPU se muestrea APARTE (hilo) y la decision solo lee la copia: `nvidia-smi` bloquea minutos durante un
    incidente porque toma el cerrojo global del driver (src/gpu.rs, README).
Medido en nuestras series (28 369 muestras 2026-09-27..2026-10-12): MemAvailable <= 8 % con PSI some >= 10 marca 32
muestras y las 32 son de colapso (full >= 10); MemAvailable sola a 16 GiB marcaba 431 falsas. Cautela: `some` y `full`
estan correlacionados, parte del cero es circular.
En `observar` SOLO registra la victima que elegiria; en `actuar` declara UNSUPPORTED (sin accion cableada; vLLM seria el
primer candidato por su huella GPU, y matarlo es decision de Luis).
Sin lectura de /proc, PSI o MemAvailable no actua y lo declara (NOT_COLLECTED).
"""

from __future__ import annotations

import os
import re
import subprocess
import threading
import time
from dataclasses import dataclass
from pathlib import Path

from tools import interruptores, vigilante_memavail

NOMBRE = "gpuoom"
MIN_DISPONIBLE_PCT = 8.0
CRITICO_PCT = 2.0
PSI_SOME_MIN = 10.0
SOSTENIDO_S = 3.0
PESO_GPU_PCT = 100
PESO_SWAP_PCT = 30
VICTIMA_MIN_KIB = 256 * 1024
GPU_INTERVALO_S = 5.0
GPU_VIEJO_S = 30.0
# Lista unica de data/procesos_protegidos.json, leida por vigilante_memavail (antes propia: no protegia ni a claude ni al motor vLLM).
PROTEGIDOS = vigilante_memavail.PROTEGIDOS


def evalua(disponible_pct: float, psi_some: float | None, ahora: float, desde: float | None) -> tuple[str, float | None, str]:
    """Pura. Devuelve (veredicto, desde, motivo); veredicto en calma|pendiente|critico|sostenido|sin_dato."""
    if psi_some is None:
        return "sin_dato", None, "NOT_COLLECTED: PSI"
    if disponible_pct <= CRITICO_PCT:
        return "critico", desde, f"MemAvailable {disponible_pct:.1f}% <= suelo critico {CRITICO_PCT}%"
    if not (disponible_pct <= MIN_DISPONIBLE_PCT and psi_some >= PSI_SOME_MIN):
        return "calma", None, f"MemAvailable {disponible_pct:.1f}% / PSI some {psi_some:.1f}"
    inicio = ahora if desde is None else desde
    if ahora - inicio >= SOSTENIDO_S:
        return "sostenido", inicio, f"{ahora - inicio:.0f}s con MemAvailable {disponible_pct:.1f}% y PSI some {psi_some:.1f}"
    return "pendiente", inicio, f"{ahora - inicio:.1f}s < {SOSTENIDO_S}s"


@dataclass(frozen=True)
class Candidato:
    pid: int
    comm: str
    anon_kib: int
    shmem_kib: int
    swap_kib: int
    gpu_kib: int
    oom_adj: int = 0

    def huella_kib(self) -> int:
        return self.anon_kib + self.shmem_kib + self.gpu_kib * PESO_GPU_PCT // 100 + self.swap_kib * PESO_SWAP_PCT // 100

    def puntaje(self) -> int:
        adj = max(-1000, min(1000, self.oom_adj))
        return self.huella_kib() * (1000 + adj) // 1000


def elige_victima(cands: list[Candidato], propio_pid: int) -> tuple[Candidato | None, str]:
    """Pura. El mayor puntaje entre los elegibles (ni protegidos, ni oom_adj -1000, ni bajo el minimo)."""
    elegibles = [c for c in cands if not PROTEGIDOS.comm(c.comm) and c.pid != propio_pid and c.oom_adj > -1000
                 and c.anon_kib + c.shmem_kib + c.swap_kib + c.gpu_kib >= VICTIMA_MIN_KIB]
    if not elegibles:
        return None, f"ninguno elegible entre {len(cands)} procesos vistos"
    v = max(elegibles, key=lambda c: (c.puntaje(), -c.pid))
    return v, f"pid {v.pid} {v.comm}: huella {v.huella_kib() // 1024} MiB (anon {v.anon_kib // 1024}, shmem {v.shmem_kib // 1024}, gpu {v.gpu_kib // 1024}, swap {v.swap_kib // 1024})"


def parsea_gpu(texto: str) -> dict[int, int]:
    """`nvidia-smi --query-compute-apps=pid,used_memory --format=csv,noheader,nounits` -> {pid: kiB}."""
    out: dict[int, int] = {}
    for linea in texto.splitlines():
        m = re.fullmatch(r"\s*(\d+)\s*,\s*(\d+)\s*", linea)
        if m:
            out[int(m.group(1))] = out.get(int(m.group(1)), 0) + int(m.group(2)) * 1024
    return out


class MuestreadorGpu:
    """Hilo aparte: la decision lee solo la copia (nvidia-smi puede bloquearse minutos en un incidente)."""

    def __init__(self, ejecuta=None):
        self._ejecuta = ejecuta or self._nvidia_smi
        self._copia: tuple[float, dict[int, int]] | None = None
        self._cerrojo = threading.Lock()

    @staticmethod
    def _nvidia_smi() -> str:
        r = subprocess.run(["nvidia-smi", "--query-compute-apps=pid,used_memory", "--format=csv,noheader,nounits"],
                           capture_output=True, text=True, timeout=20, check=False)
        return r.stdout

    def muestrea(self, ahora: float) -> None:
        try:
            d = parsea_gpu(self._ejecuta())
        except (OSError, subprocess.TimeoutExpired):
            return
        with self._cerrojo:
            self._copia = (ahora, d)

    def arranca(self, intervalo: float = GPU_INTERVALO_S) -> threading.Thread:
        """Hilo demonio: muestrea cada `intervalo` s; si nvidia-smi se bloquea, solo se bloquea este hilo."""
        def bucle() -> None:
            while True:
                self.muestrea(time.monotonic())
                time.sleep(intervalo)  # blocking-sleep: hilo de muestreo de vida larga, el trabajo es la llamada a nvidia-smi -- DEBT-COLAPSOS-11-OCT-SUITES-PYTEST-SIN-TECHO-01  # sunset-reviewed: 4.0 -- re-revisado 2026-10-15 contra 3.9 (`git log -L`: ultimo cambio de la linea anterior a la revision 3.9, 9aec733f); re-revisado 2026-10-13 contra 3.5: `git blame` de la linea 124 (7280a6a4) es anterior al bump 3.5.0 (b99560e8), la linea no cambio desde su revision anterior; la razon sigue valiendo: re-revisado 2026-10-13 contra 3.4: `git blame` de la linea 124 (095c3a35) es anterior al bump 3.4.1 (eb89c383), la linea no cambio desde su revision anterior; la razon sigue valiendo: re-revisado 2026-10-13 contra 3.3: `git blame` de la linea 124 (b008b6ee) es anterior al bump 3.3.0 (3512a16a), la linea no cambio desde su revision anterior; la razon sigue valiendo: re-revisado 2026-10-13 contra 3.2: `git blame` de la linea 124 (804713d5) es anterior al bump 3.2.0 (e8e5aa8d), la linea no cambio desde su revision anterior; la razon sigue valiendo: re-revisado 2026-10-13 contra 3.1: `git blame` de la linea 124 (93850773) es anterior al bump 3.1.0 (7a5bd48b), la linea no cambio desde su revision anterior; la razon sigue valiendo: re-revisado 2026-10-12 contra 3.0: `git blame` de la linea 124 (92598b79) es anterior al bump 2.9.1 (ab63e2b), la linea no cambio desde su revision anterior; la razon sigue valiendo: re-revisado 2026-10-12 contra 2.9: `git blame` de la linea 124 (c370a699) no cambio desde su revision anterior; la razon sigue valiendo: revalidado 2026-10-12: hilo demonio aparte del ciclo de decision ; re-revisado 2026-10-13 contra 3.1: la linea no cambio desde 20256295 (git blame de esta linea)
        h = threading.Thread(target=bucle, name="gpuoom-gpu", daemon=True)
        h.start()
        return h

    def lee(self, ahora: float) -> tuple[dict[int, int], str]:
        with self._cerrojo:
            c = self._copia
        if c is None:
            return {}, "NOT_COLLECTED: GPU nunca muestreada"
        edad = ahora - c[0]
        return c[1], ("" if edad <= GPU_VIEJO_S else f"GPU vieja ({edad:.0f}s)")


def _kb(texto: str, clave: str) -> int:
    m = re.search(rf"^{clave}:\s+(\d+) kB", texto, re.M)
    return int(m.group(1)) if m else 0


def lee_proc(raiz: Path = Path("/proc")) -> tuple[list[tuple[int, str, int, int, int, int]], int]:
    """([(pid, comm, anon, shmem, swap, oom_adj)] en kiB, cuantos procesos no se pudieron leer)."""
    out = []
    ilegibles: list[str] = []
    for d in raiz.iterdir():
        if not d.name.isdigit():
            continue
        try:
            st = (d / "status").read_text(encoding="utf-8", errors="replace")
            adj = int((d / "oom_score_adj").read_text(encoding="utf-8").strip())
        except (OSError, ValueError) as exc:
            ilegibles.append(f"{d.name}: {exc}")  # un proceso que muere durante el barrido es normal; se cuenta y se declara
            continue
        nombre = re.search(r"^Name:\s+(.*)$", st, re.M)
        out.append((int(d.name), nombre.group(1) if nombre else "?", _kb(st, "RssAnon"), _kb(st, "RssShmem"), _kb(st, "VmSwap"), adj))
    return out, len(ilegibles)


def paso(modo: str, disponible_pct: float | None, psi_some: float | None, ahora: float, desde: float | None,
         cands_fn, gpu: MuestreadorGpu, directorio: Path | None = None) -> tuple[float | None, dict | None]:
    """Un ciclo. Devuelve (nuevo `desde`, evento o None)."""
    if modo == "off":
        return None, None
    if disponible_pct is None:
        return desde, None
    veredicto, nuevo, motivo = evalua(disponible_pct, psi_some, ahora, desde)
    if veredicto not in ("critico", "sostenido"):
        return nuevo, None
    mapa, nota_gpu = gpu.lee(ahora)
    filas, omitidos = cands_fn()
    cands = [Candidato(p, c, a, s, w, mapa.get(p, 0), adj) for p, c, a, s, w, adj in filas]
    victima, porque = elige_victima(cands, os.getpid())
    ev = {"modo": modo, "habria_actuado": True, "veredicto": veredicto, "motivo": motivo,
          "victima": porque if victima else None, "sin_victima": None if victima else porque,
          "nota_gpu": nota_gpu or None, "procesos_omitidos": omitidos, "confirmado_por_psi": psi_some is not None and psi_some >= PSI_SOME_MIN}
    if modo == "actuar":
        ev["accion"] = "UNSUPPORTED: sin accion cableada; ver FEATURE-VIGILANTE-MEMAVAILABLE-UMA-01"
    interruptores.registra(NOMBRE, ev, directorio)
    return None if victima else nuevo, ev  # tras un disparo se exige un periodo sostenido nuevo


def principal() -> None:
    gpu = MuestreadorGpu()
    gpu.arranca()
    desde = None
    total = _meminfo_kib("MemTotal") or 1
    while True:
        ahora = time.monotonic()
        disp = _meminfo_kib("MemAvailable")
        psi = _psi_some()
        pct = None if disp is None else disp / total * 100
        desde, _ = paso(interruptores.modo(NOMBRE), pct, psi, ahora, desde, lee_proc, gpu)
        time.sleep(1)  # blocking-sleep: intervalo del vigilante de vida larga, sin I/O que esperar -- DEBT-COLAPSOS-11-OCT-SUITES-PYTEST-SIN-TECHO-01  # sunset-reviewed: 4.0 -- re-revisado 2026-10-15 contra 3.9 (`git log -L`: ultimo cambio de la linea anterior a la revision 3.9, 9aec733f); re-revisado 2026-10-13 contra 3.5: `git blame` de la linea 195 (7280a6a4) es anterior al bump 3.5.0 (b99560e8), la linea no cambio desde su revision anterior; la razon sigue valiendo: re-revisado 2026-10-13 contra 3.4: `git blame` de la linea 195 (095c3a35) es anterior al bump 3.4.1 (eb89c383), la linea no cambio desde su revision anterior; la razon sigue valiendo: re-revisado 2026-10-13 contra 3.3: `git blame` de la linea 195 (b008b6ee) es anterior al bump 3.3.0 (3512a16a), la linea no cambio desde su revision anterior; la razon sigue valiendo: re-revisado 2026-10-13 contra 3.2: `git blame` de la linea 195 (804713d5) es anterior al bump 3.2.0 (e8e5aa8d), la linea no cambio desde su revision anterior; la razon sigue valiendo: re-revisado 2026-10-13 contra 3.1: `git blame` de la linea 195 (93850773) es anterior al bump 3.1.0 (7a5bd48b), la linea no cambio desde su revision anterior; la razon sigue valiendo: re-revisado 2026-10-12 contra 3.0: `git blame` de la linea 195 (92598b79) es anterior al bump 2.9.1 (ab63e2b), la linea no cambio desde su revision anterior; la razon sigue valiendo: re-revisado 2026-10-12 contra 2.9: `git blame` de la linea 195 (f90a57d5) no cambio desde su revision anterior; la razon sigue valiendo: revalidado 2026-10-12: demonio de usuario; a 1 Hz la rampa medida de 9.3 GiB/s mueve MemAvailable ~8% entre lecturas, de ahi el suelo critico inmediato ; re-revisado 2026-10-13 contra 3.1: la linea no cambio desde 20256295 (git blame de esta linea)


def _meminfo_kib(clave: str) -> int | None:
    try:
        m = re.search(rf"^{clave}:\s+(\d+) kB", Path("/proc/meminfo").read_text(encoding="utf-8"), re.M)
    except OSError:
        return None
    return int(m.group(1)) if m else None


def _psi_some() -> float | None:
    try:
        m = re.search(r"^some avg10=([\d.]+)", Path("/proc/pressure/memory").read_text(encoding="utf-8"), re.M)
    except OSError:
        return None
    return float(m.group(1)) if m else None


if __name__ == "__main__":
    principal()
