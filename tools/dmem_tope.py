#!/usr/bin/env python3
"""Tope de memoria de GPU por cgroup (dmem.max) para el motor y para user.slice.

`bb dmem-tope` decide, sin root, si los topes sellados en `adopted/root-scripts/dmem-tope-aplicar.sh` caben en lo que se
mide hoy, y en modo `actuar` los pone con `sudo -n bb-root-run dmem-tope-aplicar`. El modulo NVIDIA parcheado ya cobra la
memoria de GPU por cgroup y hace cumplir `dmem.max` (FEATURE-DMEM-PARCHE-REGION-Y-COBRO-SYSMEM-GB10-01, medido
2026-10-12); lo que faltaba era ponerlo, con fallo cerrado y retroceso.

Interruptor `dmem_tope`: `off` no hace nada; `observar` mide, registra y NO escribe; `actuar` escribe solo si la medicion
cabe (consumo actual dentro del tope, suma de topes dentro de la capacidad) y devuelve el rc del script. Retroceso:
`sudo bb-root-run dmem-tope-quitar`.
Cada clase de memoria de CUDA tiene SU tope (medido 2026-10-16, FEATURE-DMEM-CLASES-DE-MEMORIA-POR-CGROUP-01): `device`
(cudaMalloc) se cobra a dmem y lo frena `dmem.max`; `managed` y `pinned` se cobran a `memory.current` y los frena `memory.max`
(el cgroup muere por OOM con exit 137). Por eso `bb dmem-tope` avisa, sin bloquear, si el motor o el slice del usuario tienen
`memory.max` en `max`: ahi managed y pinned no tendrian tope.
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path
from collections.abc import Mapping
from typing import Any, Callable

from tools import interruptores

NOMBRE = "dmem_tope"
COMM_MOTOR = "VLLM::EngineCor"
TOPE_MOTOR_GIB = 40
TOPE_USER_GIB = 8
GIB = 1 << 30
CGROUP = Path("/sys/fs/cgroup")
RUTA_MOTOR = re.compile(r"/[a-z0-9.-]+\.slice/[a-zA-Z0-9_.:-]+\.scope")
Ejecutor = Callable[[list[str]], tuple[int, str]]


def lee_region(texto: str) -> tuple[str, int] | None:
    """`dmem.capacity` debe traer UNA region con su capacidad; cualquier otra forma no se interpreta."""
    filas = [f.split() for f in texto.splitlines() if f.strip()]
    if len(filas) != 1 or len(filas[0]) != 2 or not filas[0][1].isdigit():
        return None
    return filas[0][0], int(filas[0][1])


def lee_consumo(texto: str, region: str) -> int | None:
    for fila in texto.splitlines():
        campos = fila.split()
        if len(campos) == 2 and campos[0] == region and campos[1].isdigit():
            return int(campos[1])
    return None


def evalua(capacidad: int | None, consumo: Mapping[str, int | None]) -> tuple[bool, list[str]]:
    """Pura. Devuelve (cabe, motivos): cabe es verdadero solo si TODA la medicion existe y entra en los topes."""
    topes = {"motor": TOPE_MOTOR_GIB * GIB, "user": TOPE_USER_GIB * GIB}
    motivos: list[str] = []
    if capacidad is None:
        motivos.append("NOT_COLLECTED: sin region dmem")
    elif sum(topes.values()) > capacidad:
        motivos.append(f"los topes suman {sum(topes.values())} B y la capacidad es {capacidad} B")
    for quien, tope in topes.items():
        usado = consumo.get(quien)
        if usado is None:
            motivos.append(f"NOT_COLLECTED: consumo de {quien}")
        elif usado > tope:
            motivos.append(f"{quien} usa {usado} B, por encima del tope {tope} B")
    return (not motivos), motivos


def _ejecuta(argv: list[str]) -> tuple[int, str]:
    try:
        r = subprocess.run(argv, capture_output=True, text=True, timeout=300, check=False)
    except (OSError, subprocess.TimeoutExpired) as e:
        return 127, str(e)
    return r.returncode, r.stdout + r.stderr


def _lee(p: Path) -> str:
    try:
        return p.read_text(encoding="utf-8")
    except OSError:
        return ""


def cgroup_motor(proc: Path = Path("/proc")) -> str | None:
    """El cgroup de los procesos `VLLM::EngineCor`; solo vale si es UNO y tiene la forma de un scope."""
    rutas: set[str] = set()
    for comm in proc.glob("[0-9]*/comm"):
        if _lee(comm).strip() == COMM_MOTOR:
            m = re.search(r"^0::(.*)$", _lee(comm.parent / "cgroup"), re.M)
            rutas.add(m.group(1) if m else "")
    return next(iter(rutas)) if len(rutas) == 1 and RUTA_MOTOR.fullmatch(next(iter(rutas))) else None


def avisos(memory_max: Mapping[str, str | None]) -> list[str]:
    """Pura. Un `memory.max` ausente o `max` deja a managed y pinned sin tope en ese cgroup."""
    return [f"{quien}: memory.max={valor or 'ilegible'}; managed y pinned no tienen tope" for quien, valor in memory_max.items()
            if valor is None or valor == "max"]


def mide(raiz: Path = CGROUP, proc: Path = Path("/proc")) -> dict[str, Any]:
    region = lee_region(_lee(raiz / "dmem.capacity"))
    ruta = cgroup_motor(proc)
    consumo: dict[str, int | None] = {"motor": None, "user": None}
    if region:
        if ruta:
            consumo["motor"] = lee_consumo(_lee(raiz / ruta.lstrip("/") / "dmem.current"), region[0])
        consumo["user"] = lee_consumo(_lee(raiz / "user.slice" / "dmem.current"), region[0])
    motor = (raiz / ruta.lstrip("/") / "memory.max") if ruta else None
    usuario = raiz / "user.slice" / f"user-{os.getuid()}.slice" / "memory.max"
    memory_max = {quien: (_lee(p).strip() or None) if p else None for quien, p in (("motor", motor), ("user", usuario))}
    return {"capacidad": region[1] if region else None, "consumo": consumo, "memory_max": memory_max}


def topes_puestos(raiz: Path = CGROUP, proc: Path = Path("/proc")) -> dict[str, int | None]:
    """El `dmem.max` que tienen hoy el motor y user.slice (None: no se pudo leer o esta en `max`)."""
    region = lee_region(_lee(raiz / "dmem.capacity"))
    ruta = cgroup_motor(proc)
    destinos = {"motor": raiz / ruta.lstrip("/") / "dmem.max" if ruta else None, "user": raiz / "user.slice" / "dmem.max"}
    return {quien: _tope(_lee(p), region[0]) if p and region else None for quien, p in destinos.items()}


def _tope(texto: str, region: str) -> int | None:
    return lee_consumo(texto, region)


def principal(argv: list[str], ejecuta: Ejecutor = _ejecuta, raiz: Path = CGROUP, proc: Path = Path("/proc")) -> int:
    if argv == ["--estado"]:
        puestos = topes_puestos(raiz, proc)
        print(" ".join(f"{q}={'sin tope' if v is None else f'{v / GIB:.0f}GiB'}" for q, v in puestos.items()))
        return 0 if all(v is not None for v in puestos.values()) else 1
    modo = interruptores.modo(NOMBRE)
    if modo == "off":
        print("dmem-tope: interruptor off; no hago nada")
        return 0
    medicion = mide(raiz, proc)
    cabe, motivos = evalua(medicion["capacidad"], medicion["consumo"])
    avisados = avisos(medicion["memory_max"])
    accion = "aplicaria" if cabe else "rechaza"
    if modo == "actuar" and cabe:
        rc, salida = ejecuta(["sudo", "-n", "bb-root-run", "dmem-tope-aplicar"])
        accion, motivos = ("aplicado" if rc == 0 else "fallo_al_aplicar"), ([] if rc == 0 else [salida.strip()[-300:]])
    interruptores.registra(NOMBRE, {"modo": modo, "accion": accion, "motivos": motivos, "avisos": avisados, **medicion})
    print(f"dmem-tope: {accion}" + "".join(f"\n  - {m}" for m in motivos) + "".join(f"\n  ! {a}" for a in avisados))
    return 0 if accion in ("aplicaria", "aplicado") else 3


if __name__ == "__main__":
    sys.exit(principal(sys.argv[1:]))
