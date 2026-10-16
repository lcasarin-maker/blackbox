#!/usr/bin/env python3
"""Verificador de FEATURE-DMEM-CLASES-DE-MEMORIA-POR-CGROUP-01: que cgroup paga cada clase de memoria de CUDA en GB10.

Lee `raw.json` (capture.py) y RECALCULA el veredicto; el archivo no trae ninguno. Reglas, cada una con su control negativo
en tests/test_verify_clases_memoria.py:
  nada     -> ningun contador se mueve (el instrumento ve cero: sin esto, los demas deltas no valen);
  device   -> dmem sube ~lo pedido y memory.current no;
  managed / pinned -> memory.current sube ~lo pedido y dmem no;
  sobre el tope (pide el doble del MemoryMax): managed y pinned mueren por el OOM del cgroup; device NO muere
  (memory.max no lo frena: solo lo frena dmem.max);
  bajo el tope: managed pasa.
rc 0 = pass, 1 = fail, 2 = unknown (faltan filas o el JSON es ilegible: no es un veredicto de limpio).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

TOLERANCIA_MIB = 16.0
FRACCION = 0.95
MUERTO = (-9, 137)


def _mueve(valor: float | None, n_mib: float) -> bool:
    return valor is not None and valor >= FRACCION * n_mib


def _quieto(valor: float | None) -> bool:
    return valor is not None and abs(valor) < TOLERANCIA_MIB


def _fila(filas: list[dict[str, Any]], rotulo_prefijo: str, tipo: str) -> list[dict[str, Any]]:
    return [f for f in filas if str(f.get("rotulo", "")).startswith(rotulo_prefijo) and f.get("tipo") == tipo]


def _pequena(filas: list[dict[str, Any]], tipo: str, dmem: str, memcg: str) -> tuple[list[str], list[str]]:
    """(fallos, sin_datos) de las filas pequenas de un tipo; dmem/memcg valen 'mueve' o 'quieto'."""
    fallos: list[str] = []
    sin_datos: list[str] = []
    candidatas = _fila(filas, "pequena", tipo)
    if not candidatas:
        return [], [f"faltan filas pequenas de {tipo}"]
    for f in candidatas:
        d, m, n = f.get("dmem_delta_mib"), f.get("memcg_delta_mib"), float(f.get("n_mib", 0))
        if f.get("exit") != 0 or d is None or m is None:
            sin_datos.append(f"{tipo}: la corrida no dejo numeros (exit={f.get('exit')})")
            continue
        for nombre, valor, esperado in (("dmem", d, dmem), ("memcg", m, memcg)):
            bien = _mueve(valor, n) if esperado == "mueve" else _quieto(valor)
            if not bien:
                fallos.append(f"{tipo}: {nombre} delta {valor} MiB, se esperaba que {esperado} (n={n})")
    return fallos, sin_datos


def _sobre_el_tope(filas: list[dict[str, Any]]) -> tuple[list[str], list[str]]:
    fallos: list[str] = []
    sin_datos: list[str] = []
    for tipo, debe_morir in (("managed", True), ("pinned", True), ("device", False)):
        f = _fila(filas, "sobre-el-tope", tipo)
        if not f:
            sin_datos.append(f"falta la fila sobre-el-tope de {tipo}")
        elif (f[0].get("exit") in MUERTO) != debe_morir:
            fallos.append(f"sobre el tope, {tipo}: exit={f[0].get('exit')}, se esperaba {'muerte por OOM' if debe_morir else 'seguir vivo'}")
        elif not debe_morir and not _mueve(f[0].get("dmem_delta_mib"), float(f[0].get("n_mib", 0))):
            fallos.append("sobre el tope, device: no hay cobro en dmem")
    bajo = _fila(filas, "bajo-el-tope", "managed")
    if not bajo:
        sin_datos.append("falta la fila bajo-el-tope de managed")
    elif bajo[0].get("exit") != 0:
        fallos.append(f"bajo el tope, managed murio (exit={bajo[0].get('exit')}): el control no es un control")
    return fallos, sin_datos


def verifica(datos: Any) -> tuple[str, list[str]]:
    filas = datos.get("filas") if isinstance(datos, dict) else None
    if not isinstance(filas, list) or not filas:
        return "unknown", ["raw.json sin filas"]
    fallos: list[str] = []
    sin_datos: list[str] = []
    for tipo, dmem, memcg in (("nada", "quieto", "quieto"), ("device", "mueve", "quieto"),
                              ("managed", "quieto", "mueve"), ("pinned", "quieto", "mueve")):
        f, s = _pequena(filas, tipo, dmem, memcg)
        fallos += f
        sin_datos += s
    f, s = _sobre_el_tope(filas)
    fallos += f
    sin_datos += s
    if fallos:
        return "fail", fallos + sin_datos
    return ("unknown", sin_datos) if sin_datos else ("pass", [])


def main(argv: list[str]) -> int:
    if len(argv) != 1:
        print("uso: python3 -m tools.verify_clases_memoria <raw.json>", file=sys.stderr)
        return 2
    try:
        datos = json.loads(Path(argv[0]).read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        print(json.dumps({"status": "unknown", "findings": [f"raw.json ilegible: {e}"]}))
        return 2
    estado, hallazgos = verifica(datos)
    print(json.dumps({"status": estado, "findings": hallazgos}, ensure_ascii=False))
    return {"pass": 0, "fail": 1}.get(estado, 2)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
