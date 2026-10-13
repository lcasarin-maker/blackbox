#!/usr/bin/env python3
"""Vigilante de MemAvailable (interruptor `memavail`): FEATURE-VIGILANTE-MEMAVAILABLE-UMA-01.

Dispara cuando MemAvailable baja de una linea dura. En `observar` solo registra, con el PSI full del mismo
instante, para medir sus falsos positivos en vivo. En `actuar` NO hay accion cableada todavia: declara
UNSUPPORTED (la accion se decide con el registro de `observar`; no se inventa antes).
"""

from __future__ import annotations

import re
import time
from pathlib import Path

from tools import interruptores

NOMBRE = "memavail"
LINEA_GIB = 8.0
PSI_COLAPSO = 10.0


def decide(mem_avail_kb: int | None, psi_full: float | None, linea_gib: float = LINEA_GIB) -> dict:
    """Pura. Sin lectura de MemAvailable no dispara y lo declara."""
    if mem_avail_kb is None:
        return {"dispara": False, "motivo": "NOT_COLLECTED: MemAvailable"}
    dispara = mem_avail_kb / 1048576 < linea_gib
    return {
        "dispara": dispara,
        "mem_avail_gib": round(mem_avail_kb / 1048576, 2),
        "psi_full": psi_full,
        "confirmado_por_psi": psi_full is not None and psi_full >= PSI_COLAPSO,
    }


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


def paso(modo_actual: str, meminfo: int | None, psi: float | None, directorio: Path | None = None) -> dict | None:
    if modo_actual == "off":
        return None
    d = decide(meminfo, psi)
    if not d["dispara"]:
        return None
    ev = {"modo": modo_actual, "habria_actuado": True, **d}
    if modo_actual == "actuar":
        ev["accion"] = "UNSUPPORTED: sin accion cableada; ver FEATURE-VIGILANTE-MEMAVAILABLE-UMA-01"
    interruptores.registra(NOMBRE, ev, directorio)
    return ev


def main() -> None:
    while True:
        paso(interruptores.modo(NOMBRE), lee_meminfo(), lee_psi_full())
        time.sleep(1)  # blocking-sleep: intervalo del vigilante de vida larga, sin I/O que esperar -- DEBT-COLAPSOS-11-OCT-SUITES-PYTEST-SIN-TECHO-01  # sunset-reviewed: 3.6 -- re-revisado 2026-10-13 contra 3.5: `git blame` de la linea 67 (7280a6a4) es anterior al bump 3.5.0 (b99560e8), la linea no cambio desde su revision anterior; la razon sigue valiendo: re-revisado 2026-10-13 contra 3.4: `git blame` de la linea 67 (095c3a35) es anterior al bump 3.4.1 (eb89c383), la linea no cambio desde su revision anterior; la razon sigue valiendo: re-revisado 2026-10-13 contra 3.3: `git blame` de la linea 67 (b008b6ee) es anterior al bump 3.3.0 (3512a16a), la linea no cambio desde su revision anterior; la razon sigue valiendo: re-revisado 2026-10-13 contra 3.2: `git blame` de la linea 67 (804713d5) es anterior al bump 3.2.0 (e8e5aa8d), la linea no cambio desde su revision anterior; la razon sigue valiendo: re-revisado 2026-10-13 contra 3.1: `git blame` de la linea 67 (93850773) es anterior al bump 3.1.0 (7a5bd48b), la linea no cambio desde su revision anterior; la razon sigue valiendo: re-revisado 2026-10-12 contra 3.0: `git blame` de la linea 67 (92598b79) es anterior al bump 2.9.1 (ab63e2b), la linea no cambio desde su revision anterior; la razon sigue valiendo: re-revisado 2026-10-12 contra 2.9: `git blame` de la linea 67 (8d33e5cb) no cambio desde su revision anterior; la razon sigue valiendo: revalidado 2026-10-12: demonio de usuario sin otro hilo; a 1 Hz la rampa de 0.7 GiB/s mueve MemAvailable ~0.7 GiB entre lecturas ; re-revisado 2026-10-13 contra 3.1: la linea no cambio desde 20256295 (git blame de esta linea)


if __name__ == "__main__":
    main()
