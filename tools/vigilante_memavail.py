#!/usr/bin/env python3
"""Vigilante de MemAvailable (interruptor `memavail`): FEATURE-VIGILANTE-MEMAVAILABLE-UMA-01.

Dispara cuando MemAvailable baja de una linea dura. En `observar` registra, con el PSI full del mismo
instante, la unidad que DETENDRIA y su origen, sin tocar nada, para medir sus falsos positivos en vivo.
En `actuar` detiene (`systemctl --user stop`) UNA sola unidad: la de mayor `memory.current` entre las
unidades del gestor de usuario cuyo nombre casa con `ELEGIBLES` y no casa con `PROTEGIDAS`. Antes de
detenerla guarda el origen de sus procesos (`tools.origen_proceso.origen`, reusado).

Alcance, por construccion: solo el arbol cgroup `user@UID.service` (docker y el motor vLLM viven en
system.slice y no se ven), y por defecto `ELEGIBLES` solo admite `bb-lab-*.scope` (scopes de laboratorio).
Ampliar `ELEGIBLES` a unidades de trabajo reales es una decision de Luis, no un defecto de este codigo.
Sin unidad elegible: NOT_COLLECTED y no se mata nada. La mayor unidad elegible pero protegida: REFUSED.
"""

from __future__ import annotations

import fnmatch
import json
import logging
import os
import re
import subprocess
import time
from pathlib import Path
from typing import Any, Callable, NamedTuple

from tools import interruptores, origen_proceso

NOMBRE = "memavail"
LINEA_GIB = 8.0
PSI_COLAPSO = 10.0
ELEGIBLES = ("bb-lab-*.scope", "bb-portero-suite-*.scope")  # suites reintentables bajo el portero (voto de Luis 2026-10-14)
ORIGEN_MAX_PIDS = 5


# --- Lista unica de procesos protegidos (voto de Luis 2026-10-14) ---
# Antes habia cinco listas que no coincidian (escalon de bb-usable, bb-guardia-proceso, gpuoom, memavail y el
# --avoid de earlyoom): la guardia podia mandar SIGTERM a un hijo de la sesion de Claude que el escalon protegia y
# gpuoom elegia al motor vLLM. La fuente es data/procesos_protegidos.json; este lector lo usan memavail y gpuoom, y
# bin/bb-usable y bin/bb-guardia-proceso llevan el suyo de pocas lineas para no importar nada desde un demonio.
# `cargar_protegidos` NUNCA lanza: con el fichero ausente o mal formado devuelve la copia RESPALDO y el error, y se
# avisa por stderr. tests/test_procesos_protegidos.py exige que RESPALDO sea identico al fichero.
PROTEGIDOS_RUTA = Path(__file__).resolve().parent.parent / "data" / "procesos_protegidos.json"

# (comm, prefijo, fragmento de unidad o None = comm escapado)
_BB_UNIDAD = "bb-(?!lab-|portero-suite-)"
RESPALDO_COMM: tuple[tuple[str, bool, str | None], ...] = (
    ("claude", True, None), ("node", False, None), ("cowork-linux-he", False, None), ("electron", False, None),
    ("chrome_crashpad", False, None), ("Xorg", False, None), ("Xwayland", False, None), ("gnome-shell", True, None),
    ("gnome-session", True, None), ("gdm", True, None), ("systemd", True, None), ("init", False, None),
    ("sshd", True, None), ("dbus", True, None), ("pipewire", True, None), ("wireplumber", False, None),
    ("xdg-", True, None), ("earlyoom", False, None), ("docker", True, None), ("containerd", True, None),
    ("vllm", True, None), ("VLLM", True, None), ("bb", False, _BB_UNIDAD), ("bb-", True, _BB_UNIDAD),
)
RESPALDO_UNIDADES: tuple[str, ...] = ("anthropic", "gnome", "session", "user@")


class Protegidos(NamedTuple):
    exactos: frozenset[str]
    prefijos: tuple[str, ...]
    unidades: re.Pattern[str]   # para nombres de unidad systemd (memavail)
    error: str | None           # None = leido del fichero; si no, por que se uso RESPALDO

    def comm(self, comm: str) -> bool:
        return comm in self.exactos or comm.startswith(self.prefijos)


def _construye(comm: tuple[tuple[str, bool, str | None], ...], unidades: tuple[str, ...], error: str | None) -> Protegidos:
    fragmentos = [u if u is not None else re.escape(n) for n, _, u in comm] + list(unidades)
    return Protegidos(frozenset(n for n, p, _ in comm if not p), tuple(n for n, p, _ in comm if p),
                      re.compile("|".join(dict.fromkeys(fragmentos)), re.IGNORECASE), error)


def _lee(ruta: Path) -> tuple[tuple[tuple[str, bool, str | None], ...], tuple[str, ...]]:
    datos = json.loads(ruta.read_text(encoding="utf-8"))
    comm = tuple((e["nombre"], e["prefijo"], e.get("unidad")) for e in datos["comm"])
    unidades = tuple(e["patron"] for e in datos["unidades"])
    if not comm or not all(isinstance(n, str) and n and isinstance(p, bool) and (u is None or isinstance(u, str) and u)
                           for n, p, u in comm) or not all(isinstance(u, str) and u for u in unidades):
        raise ValueError("lista vacia o entrada mal formada")
    return comm, unidades


def cargar_protegidos(ruta: Path = PROTEGIDOS_RUTA) -> Protegidos:
    """El fichero si es valido; si no, RESPALDO con el motivo en `error`. Nunca lanza."""
    try:
        comm, unidades = _lee(ruta)
        return _construye(comm, unidades, None)
    except Exception as exc:  # un fichero roto no puede tumbar a un vigilante: se usa el respaldo y se dice
        error = f"{type(exc).__name__}: {exc}"
        # sin handler configurado, logging lo saca por stderr (lastResort): llega al journal de la unidad
        logging.getLogger("procesos_protegidos").warning(
            "[procesos_protegidos] %s no se pudo usar (%s): se usa la copia de respaldo", ruta, error)
        return _construye(RESPALDO_COMM, RESPALDO_UNIDADES, error)


PROTEGIDOS = cargar_protegidos()


# Nunca se detienen aunque casen con ELEGIBLES (doble guarda): contenedores, motor, sesion, escritorio, bb.
# La lista unica traducida a nombres de unidad (incluye bb-(?!lab-|portero-suite-)).
PROTEGIDAS = PROTEGIDOS.unidades


class Unidad(NamedTuple):
    nombre: str
    cgroup: str
    memoria_bytes: int | None  # None = memory.current ilegible (la unidad salio durante el barrido)


def decide(mem_avail_kb: int | None, psi_full: float | None, linea_gib: float = LINEA_GIB) -> dict:
    """Pura. Sin lectura de MemAvailable no dispara y lo declara."""
    if mem_avail_kb is None:
        return {"dispara": False, "motivo": "NOT_COLLECTED: MemAvailable"}
    dispara = mem_avail_kb / 1048576 < linea_gib
    return {
        "dispara": dispara,
        "mem_avail_gib": round(mem_avail_kb / 1048576, 2),
        "linea_gib": linea_gib,
        "psi_full": psi_full,
        "confirmado_por_psi": psi_full is not None and psi_full >= PSI_COLAPSO,
    }


def elige_culpable(unidades: list[Unidad] | None, elegibles: tuple[str, ...] = ELEGIBLES,
                   protegidas: re.Pattern[str] = PROTEGIDAS) -> dict[str, Any]:
    """Pura. La unidad elegible de mayor memoria; si es protegida, REFUSED; si no hay, NOT_COLLECTED."""
    if unidades is None:
        return {"veredicto": "NOT_COLLECTED", "motivo": "cgroup del gestor de usuario ilegible"}
    todas = [u for u in unidades if any(fnmatch.fnmatchcase(u.nombre, g) for g in elegibles)]
    casan = [u for u in todas if u.memoria_bytes is not None]
    ilegibles = [u.nombre for u in todas if u.memoria_bytes is None]
    if not casan:
        return {"veredicto": "NOT_COLLECTED", "motivo": f"ninguna unidad legible casa con {list(elegibles)}",
                "unidades_vistas": len(unidades), "elegibles_ilegibles": ilegibles}
    mayor = max(casan, key=lambda u: (u.memoria_bytes or 0, u.nombre))
    if protegidas.search(mayor.nombre):
        return {"veredicto": "REFUSED", "motivo": f"{mayor.nombre} es protegida", "unidad": mayor._asdict(),
                "elegibles_ilegibles": ilegibles}
    return {"veredicto": "DETENER", "unidad": mayor._asdict(), "elegibles_ilegibles": ilegibles}


def lee_meminfo(ruta: Path = Path("/proc/meminfo")) -> int | None:
    try:
        m = re.search(r"^MemAvailable:\s+(\d+) kB", ruta.read_text(encoding="utf-8"), re.M)
    except OSError:
        return None
    return int(m.group(1)) if m else None


def lee_psi_full(ruta: Path = Path("/proc/pressure/memory")) -> float | None:
    try:
        m = re.search(r"^full avg10=([\d.]+)", ruta.read_text(encoding="utf-8"), re.M)
    except OSError:
        return None
    return float(m.group(1)) if m else None


def raiz_usuario(uid: int | None = None, cg: Path = Path("/sys/fs/cgroup")) -> Path:
    u = os.getuid() if uid is None else uid
    return cg / f"user.slice/user-{u}.slice/user@{u}.service"


def lee_unidades(raiz: Path | None = None) -> list[Unidad] | None:
    """Toda unidad .scope/.service bajo el gestor de usuario con su memory.current. None si la raiz falta."""
    raiz = raiz or raiz_usuario()
    if not raiz.is_dir():
        return None
    out: list[Unidad] = []
    for d in raiz.rglob("*"):
        if d.name.endswith((".scope", ".service")) and d.is_dir():
            try:
                out.append(Unidad(d.name, str(d), int((d / "memory.current").read_text(encoding="ascii"))))
            except (OSError, ValueError):
                out.append(Unidad(d.name, str(d), None))  # se cuenta como ilegible, no se pierde
    return out


def origen_de(cgroup: str) -> list[dict[str, Any]] | str:
    """Origen de hasta ORIGEN_MAX_PIDS procesos de la unidad, antes de detenerla."""
    # ponytail: sin plazo propio; leer cmdline toma mmap_lock y bajo estancamiento puede tardar -- si el
    # registro de `observar` muestra vueltas lentas, correrlo con plazo como hace bin/bb-usable.
    try:
        pids = [int(x) for x in (Path(cgroup) / "cgroup.procs").read_text(encoding="ascii").split()]
    except (OSError, ValueError):
        return "NOT_COLLECTED: cgroup.procs ilegible"
    return [origen_proceso.origen(p) for p in pids[:ORIGEN_MAX_PIDS]]


def detiene(nombre: str) -> dict[str, Any]:
    try:
        r = subprocess.run(["systemctl", "--user", "stop", nombre], capture_output=True, text=True,
                           timeout=30, check=False)
    except (OSError, subprocess.TimeoutExpired) as e:
        return {"rc": None, "salida": f"COULD_NOT_RUN: {e}"}
    return {"rc": r.returncode, "salida": (r.stdout + r.stderr).strip()}


class Contexto(NamedTuple):
    """La regla (linea, elegibles) y los efectos (leer unidades, leer origen, detener), sustituibles en prueba."""
    linea_gib: float = LINEA_GIB
    elegibles: tuple[str, ...] = ELEGIBLES
    unidades: Callable[[], list[Unidad] | None] = lee_unidades
    origen: Callable[[str], Any] = origen_de
    detener: Callable[[str], dict[str, Any]] = detiene


def paso(modo_actual: str, meminfo: int | None, psi: float | None, directorio: Path | None = None,
         ctx: Contexto = Contexto()) -> dict | None:
    if modo_actual == "off":
        return None
    d = decide(meminfo, psi, ctx.linea_gib)
    if not d["dispara"]:
        return None
    c = elige_culpable(ctx.unidades(), ctx.elegibles)
    ev: dict[str, Any] = {"modo": modo_actual, "habria_actuado": True, **d, "culpable": c}
    if c["veredicto"] == "DETENER":
        ev["origen"] = ctx.origen(c["unidad"]["cgroup"])
        if modo_actual == "actuar":
            ev["accion"] = {"detenida": c["unidad"]["nombre"], **ctx.detener(c["unidad"]["nombre"])}
    elif modo_actual == "actuar":
        ev["accion"] = f"{c['veredicto']}: no se detiene nada"
    interruptores.registra(NOMBRE, ev, directorio)
    return ev


def una_vuelta(linea_gib: float = LINEA_GIB, elegibles: tuple[str, ...] = ELEGIBLES) -> dict | None:
    return paso(interruptores.modo(NOMBRE), lee_meminfo(), lee_psi_full(), None, Contexto(linea_gib, elegibles))


def main() -> None:
    while True:
        una_vuelta()
        time.sleep(1)  # blocking-sleep: intervalo del vigilante de vida larga, sin I/O que esperar -- DEBT-COLAPSOS-11-OCT-SUITES-PYTEST-SIN-TECHO-01  # sunset-reviewed: 4.1 -- re-revisado 2026-10-15 contra 4.0 (`git log -L` c4977a8b..HEAD sobre la linea +-6: 0 commits, linea identica a la revision 4.0 c4977a8b; sigue siendo el intervalo del `while True` de main()); re-revisado 2026-10-15 contra 3.9 (`git log -L`: ultimo cambio de la linea anterior a la revision 3.9, 9aec733f); re-revisado 2026-10-13 contra 3.5: `git blame` de la linea 67 (7280a6a4) es anterior al bump 3.5.0 (b99560e8), la linea no cambio desde su revision anterior; la razon sigue valiendo: re-revisado 2026-10-13 contra 3.4: `git blame` de la linea 67 (095c3a35) es anterior al bump 3.4.1 (eb89c383), la linea no cambio desde su revision anterior; la razon sigue valiendo: re-revisado 2026-10-13 contra 3.3: `git blame` de la linea 67 (b008b6ee) es anterior al bump 3.3.0 (3512a16a), la linea no cambio desde su revision anterior; la razon sigue valiendo: re-revisado 2026-10-13 contra 3.2: `git blame` de la linea 67 (804713d5) es anterior al bump 3.2.0 (e8e5aa8d), la linea no cambio desde su revision anterior; la razon sigue valiendo: re-revisado 2026-10-13 contra 3.1: `git blame` de la linea 67 (93850773) es anterior al bump 3.1.0 (7a5bd48b), la linea no cambio desde su revision anterior; la razon sigue valiendo: re-revisado 2026-10-12 contra 3.0: `git blame` de la linea 67 (92598b79) es anterior al bump 2.9.1 (ab63e2b), la linea no cambio desde su revision anterior; la razon sigue valiendo: re-revisado 2026-10-12 contra 2.9: `git blame` de la linea 67 (8d33e5cb) no cambio desde su revision anterior; la razon sigue valiendo: revalidado 2026-10-12: demonio de usuario sin otro hilo; a 1 Hz la rampa de 0.7 GiB/s mueve MemAvailable ~0.7 GiB entre lecturas ; re-revisado 2026-10-13 contra 3.1: la linea no cambio desde 20256295 (git blame de esta linea)


if __name__ == "__main__":
    main()
