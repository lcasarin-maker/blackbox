#!/usr/bin/env python3
"""Guardia de GPU por contenedor (interruptor `guardia_gpu`): el barandal que faltaba el 2026-11-05 y el 2026-11-06.

Por que existe: `tools/vigilante_memavail.py` solo ve el arbol de usuario (Docker y vLLM viven fuera) y earlyoom elige por
memoria residente (un vLLM con 89 GiB de GPU pesa 0,9 GB). Los dos colapsos los provoco un contenedor de GPU que ninguna
guardia podia ver ni detener. Esta guardia mira MemAvailable cada segundo y, si queda bajo `LINEA_MB` durante `MUESTRAS`
segundos seguidos, lee la GPU por contenedor (nvidia-smi -> cgroup -> docker) y DETIENE al mayor entre los que DECLARAN un
`lanzado_por` (etiqueta `--label lanzado_por=...`), antes de que earlyoom llegue a su 10 %.

Elegibilidad por etiqueta, por construccion: un contenedor sin `lanzado_por` (por ejemplo el motor de chat `nemotron-server`) NUNCA
se detiene aqui; quien lanza un trabajo de GPU que puede morir lo declara. Un trabajo que no llega a `MIN_GPU_GIB` tampoco se toca
(no es el que llena la memoria). Un solo paro por `ENFRIAMIENTO_S`.

`off` no hace nada; `observar` registra lo que habria detenido; `actuar` detiene (`docker stop -t 15`), registra y avisa por ntfy.
"""

from __future__ import annotations

import re
import subprocess
import sys
import time
from collections import defaultdict
from pathlib import Path
from typing import Any, Callable

from tools import aviso_earlyoom, interruptores

NOMBRE = "guardia_gpu"
LINEA_MB = 20000
MUESTRAS = 3
MIN_GPU_GIB = 8.0
ENFRIAMIENTO_S = 300.0
Run = Callable[..., Any]


def contenedores_gpu(run: Run = subprocess.run, cgroup_de: Callable[[int], str] | None = None) -> list[dict[str, Any]]:
    """GPU usada por contenedor Docker (suma de sus procesos), de mayor a menor. Lo que no es de un contenedor se omite."""
    cgroup_de = cgroup_de or (lambda pid: Path(f"/proc/{pid}/cgroup").read_text(encoding="utf-8"))
    try:
        r = run(["nvidia-smi", "--query-compute-apps=pid,used_memory", "--format=csv,noheader,nounits"],
                capture_output=True, text=True, timeout=20, check=False)
    except (OSError, subprocess.SubprocessError):
        return []
    por_id: dict[str, int] = defaultdict(int)
    for linea in (r.stdout or "").splitlines():
        try:
            pid, mib = (int(x) for x in linea.split(","))
            m = re.search(r"docker-([0-9a-f]{12})", cgroup_de(pid))
        except (ValueError, OSError):
            continue
        if m:
            por_id[m[1]] += mib
    out = []
    for cid, mib in por_id.items():
        try:
            i = run(["docker", "inspect", "--format", '{{.Name}}|{{index .Config.Labels "lanzado_por"}}', cid],
                    capture_output=True, text=True, timeout=20, check=False)
        except (OSError, subprocess.SubprocessError):
            continue
        nombre, _, etiqueta = (i.stdout or "").strip().partition("|")
        if nombre:
            out.append({"id": cid, "nombre": nombre.lstrip("/"), "gib": mib / 1024, "lanzado_por": etiqueta})
    return sorted(out, key=lambda c: c["gib"], reverse=True)


def elige(conts: list[dict[str, Any]]) -> dict[str, Any] | None:
    """El mayor contenedor que declara `lanzado_por` y llega a MIN_GPU_GIB; None si ninguno es elegible."""
    for c in conts:
        if c["lanzado_por"] and c["gib"] >= MIN_GPU_GIB:
            return c
    return None


def decide(estado: dict[str, Any], mem_avail_mb: int, ahora: float) -> tuple[dict[str, Any], bool]:
    """PURA. Cuenta muestras seguidas bajo la linea; devuelve (estado, leer_gpu). Solo pide leer la GPU al cumplir MUESTRAS
    y fuera del enfriamiento: nvidia-smi cuesta, y una sola muestra baja no es una emergencia."""
    bajas = estado.get("bajas", 0) + 1 if mem_avail_mb < LINEA_MB else 0
    nuevo = {**estado, "bajas": bajas}
    en_enfriamiento = ahora - estado.get("ultimo_paro", -1e12) < ENFRIAMIENTO_S
    return nuevo, bajas >= MUESTRAS and not en_enfriamiento


def actua(modo: str, mem_avail_mb: int, conts: list[dict[str, Any]], run: Run = subprocess.run, url: str | None = None,
          envia: Callable[[str, str], bool] = aviso_earlyoom.manda,
          registra: Callable[..., None] = interruptores.registra) -> dict[str, Any]:
    """Un paro (o su simulacion) segun el modo. Devuelve la fila registrada; `paro` dice si hubo que registrar un paro."""
    c = elige(conts)
    fila: dict[str, Any] = {"modo": modo, "mem_avail_mb": mem_avail_mb, "contenedores": [(x["nombre"], round(x["gib"], 1), x["lanzado_por"]) for x in conts[:4]],
                            "habria_actuado": c is not None, "paro": False}
    if c is None:
        fila["motivo"] = "ningun contenedor con lanzado_por y GPU suficiente"
    else:
        fila["objetivo"] = {k: c[k] for k in ("nombre", "gib", "lanzado_por")}
        if modo == "actuar":
            try:
                r = run(["docker", "stop", "-t", "15", c["nombre"]], capture_output=True, text=True, timeout=60, check=False)
                fila["paro"] = r.returncode == 0
                if r.returncode != 0:
                    fila["error"] = f"docker stop rc={r.returncode}"
            except (OSError, subprocess.SubprocessError) as e:
                fila["error"] = type(e).__name__
            msg = (f"bb detuvo {c['nombre']} ({c['gib']:.1f} GiB de GPU, lanzado_por={c['lanzado_por']}): MemAvailable {mem_avail_mb} MB "
                   f"< {LINEA_MB} MB. Resultado: {'detenido' if fila['paro'] else 'NO se pudo detener'}.")
            if url:
                try:
                    fila["avisado"] = envia(url, msg)
                except Exception as e:  # ntfy caido: el paro ya ocurrio y queda en el registro
                    fila["avisado"] = False
                    fila["error_aviso"] = type(e).__name__
    if modo != "off":
        registra(NOMBRE, fila)
    return fila


def main() -> int:  # pragma: no cover  (bucle a 1 Hz sobre /proc/meminfo; la logica esta en decide/elige/actua)
    estado: dict[str, Any] = {}
    while True:
        ahora = time.monotonic()
        mem = next((int(x.split()[1]) // 1024 for x in Path("/proc/meminfo").read_text().splitlines() if x.startswith("MemAvailable")), None)
        modo = interruptores.modo(NOMBRE)
        if mem is not None and modo != "off":
            estado, leer = decide(estado, mem, ahora)
            if leer:
                fila = actua(modo, mem, contenedores_gpu(), url=aviso_earlyoom.url_ntfy())
                # tras un paro (o su simulacion) espera todo el enfriamiento; sin objetivo elegible, vuelve a mirar en 30 s
                estado["ultimo_paro"] = ahora if fila["habria_actuado"] else ahora - ENFRIAMIENTO_S + 30.0
        time.sleep(1.0)


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
