#!/usr/bin/env python3
"""Lanzador del limitador CUDA que falla cerrado (FEATURE-LIMITADOR-INTEGRAR-LANZADOR-FALLA-CERRADO-01).

`bb limita --limite 512m --lib <libvgpu.so> -- <cmd...>` lanza `cmd` con HAMi-core (LD_PRELOAD) solo si una asignacion
CENTINELA por encima del tope es RECHAZADA con OOM antes de lanzar. Sin variable, sin la biblioteca, con una
biblioteca que no exporta simbolos `cu*` (compilada Release) o con una centinela que pasa: no lanza (rc 3).
El motivo: HAMi-core falla abierto (sin la variable corre sin tope y registra "Initializing"; medido 2026-10-12).

Interruptor `limitador` (tools/interruptores.py): `off` lanza el comando sin tocarlo; `observar` corre la centinela,
la registra y lanza SIN limitador; `actuar` lanza con limitador solo si la centinela rechaza.
Limite declarado: la memoria fijada del anfitrion no se limita (medido), ni las rutas que HAMi no intercepta.
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Callable

from tools import interruptores

NOMBRE = "limitador"
CENTINELA_SOBRE_MIB = 64
CUDA_OOM = 2
UNIDADES = {"k": 1 << 10, "m": 1 << 20, "g": 1 << 30}
Sondeo = Callable[[int, dict[str, str]], int]


def parsea_limite(txt: str) -> int | None:
    m = re.fullmatch(r"(\d+)([kmg])", txt.strip().lower())
    return int(m.group(1)) * UNIDADES[m.group(2)] if m and int(m.group(1)) > 0 else None


def exporta_cu(lib: Path) -> bool:
    """La biblioteca debe exportar simbolos `cu*`; una compilada Release los oculta y no limita nada."""
    try:
        r = subprocess.run(["nm", "-D", str(lib)], capture_output=True, text=True, timeout=30, check=False)
    except (OSError, subprocess.TimeoutExpired):
        return False
    return any(re.search(r" T cu\w+", linea) for linea in r.stdout.splitlines())


def centinela_driver(nbytes: int, entorno: dict[str, str]) -> int:
    """cuMemAlloc de `nbytes` en un proceso hijo con `entorno`; devuelve el codigo CUresult (-1: no se pudo medir)."""
    codigo = (
        "import ctypes,sys\n"
        "c=ctypes.CDLL('libcuda.so.1')\n"
        "if c.cuInit(0): sys.exit(90)\n"
        "d=ctypes.c_int(); x=ctypes.c_void_p()\n"
        "if c.cuDeviceGet(ctypes.byref(d),0) or c.cuDevicePrimaryCtxRetain(ctypes.byref(x),d) or c.cuCtxSetCurrent(x): sys.exit(91)\n"
        "p=ctypes.c_void_p(); r=c.cuMemAlloc_v2(ctypes.byref(p),ctypes.c_size_t(int(sys.argv[1])))\n"
        "if r==0: c.cuMemFree_v2(p)\n"
        "sys.exit(100+r)\n"
    )
    try:
        r = subprocess.run([sys.executable, "-I", "-c", codigo, str(nbytes)], env=entorno, capture_output=True, timeout=120, check=False)
    except (OSError, subprocess.TimeoutExpired):
        return -1
    return r.returncode - 100 if r.returncode >= 100 else -1


def prepara(limite: int, lib: Path, base: dict[str, str], cache: Path) -> dict[str, str]:
    e = dict(base)
    e["CUDA_DEVICE_MEMORY_LIMIT"] = f"{limite >> 20}m"
    e["CUDA_DEVICE_MEMORY_SHARED_CACHE"] = str(cache)
    e["LD_PRELOAD"] = f"{lib}:{base['LD_PRELOAD']}" if base.get("LD_PRELOAD") else str(lib)
    return e


def decide(modo: str, limite: int | None, lib: Path, existe_lib: bool, simbolos: bool, centinela_rc: int | None) -> tuple[str, str]:
    """Pura. Devuelve (accion, motivo): accion en {lanza, lanza_sin_limitador, rechaza}."""
    if modo == "off":
        return "lanza_sin_limitador", "interruptor off"
    if limite is None:
        return "rechaza", "NOT_COLLECTED: limite ausente o ilegible (se espera p. ej. 512m)"
    if not existe_lib:
        return "rechaza", f"biblioteca ausente: {lib}"
    if not simbolos:
        return "rechaza", "la biblioteca no exporta simbolos cu* (compilada Release?): no limitaria nada"
    if centinela_rc != CUDA_OOM:
        return "rechaza", f"centinela por encima del tope NO fue rechazada (rc={centinela_rc}, se esperaba {CUDA_OOM}): el limitador no aplica"
    return ("lanza" if modo == "actuar" else "lanza_sin_limitador"), f"centinela rechazada; modo {modo}"


def principal(argv: list[str], sondeo: Sondeo = centinela_driver, ejecuta=os.execvpe) -> int:
    ap = argparse.ArgumentParser(prog="bb limita")
    ap.add_argument("--limite", required=False, default=os.environ.get("CUDA_DEVICE_MEMORY_LIMIT", ""))
    ap.add_argument("--lib", type=Path, required=True)
    ap.add_argument("--cache", type=Path, default=Path.home() / ".local/share/blackbox/limitador.cache")
    ap.add_argument("cmd", nargs=argparse.REMAINDER)
    a = ap.parse_args(argv)
    cmd = a.cmd[1:] if a.cmd[:1] == ["--"] else a.cmd
    if not cmd:
        print("limita: falta el comando tras --", file=sys.stderr)
        return 2
    modo = interruptores.modo(NOMBRE)
    limite = parsea_limite(a.limite)
    existe = a.lib.is_file()
    simbolos = exporta_cu(a.lib) if existe else False
    rc = None
    if modo != "off" and limite and existe and simbolos:
        a.cache.parent.mkdir(parents=True, exist_ok=True)
        rc = sondeo(limite + (CENTINELA_SOBRE_MIB << 20), prepara(limite, a.lib, dict(os.environ), a.cache))
    accion, motivo = decide(modo, limite, a.lib, existe, simbolos, rc)
    interruptores.registra(NOMBRE, {"modo": modo, "accion": accion, "motivo": motivo, "cmd": cmd[0], "centinela_rc": rc})
    if accion == "rechaza":
        print(f"limita: NO lanzo: {motivo}", file=sys.stderr)
        return 3
    entorno = prepara(limite, a.lib, dict(os.environ), a.cache) if accion == "lanza" and limite is not None else dict(os.environ)
    ejecuta(cmd[0], cmd, entorno)
    return 0  # ejecuta no vuelve; solo los tests llegan aqui


if __name__ == "__main__":
    sys.exit(principal(sys.argv[1:]))
