#!/usr/bin/env python3
"""`bb saber`: busca en la KB de Atlas, SOLO LEYENDO archivos.

Relacion de informacion, no de codigo: no importa nada de Atlas, solo recorre los `.md` bajo la ruta que
dice `ATLAS_KNOWLEDGE` (por defecto `~/projects/Atlas/knowledge`). Es la misma consulta de texto que Atlas
llama `grep_kb`, y como ella no necesita el indice semantico ni la GPU. Para recuperacion semantica se usa
`atlas "<pregunta>"` en Atlas.

Reglas del formato de reporte de blackbox: un cero se escribe con su alcance (`0 en <ruta>: N archivos`),
y una ruta ausente es `COULD_NOT_RUN`, nunca "sin resultados".

Codigos de salida, como grep: 0 hubo coincidencias, 1 ninguna, 2 no se pudo correr.
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path
from typing import Any

MAX_POR_DEFECTO = 40


def raiz() -> Path:
    return Path(
        os.environ.get("ATLAS_KNOWLEDGE", Path.home() / "projects/Atlas/knowledge")
    )


def busca(
    patron: str,
    *,
    base: Path | None = None,
    regex: bool = False,
    maximo: int = MAX_POR_DEFECTO,
) -> dict[str, Any]:
    base = base or raiz()
    if not base.is_dir():
        return {
            "estado": "COULD_NOT_RUN",
            "detalle": f"{base} no existe (ATLAS_KNOWLEDGE)",
        }
    try:
        rx = re.compile(patron if regex else re.escape(patron), re.I)
    except re.error as e:
        return {"estado": "COULD_NOT_RUN", "detalle": f"patron invalido: {e}"}
    hallazgos: list[dict[str, Any]] = []
    revisados = total = 0
    ilegibles: list[str] = []
    for f in sorted(base.rglob("*.md")):
        rel = f.relative_to(base)
        if f.name.startswith(".") or any(
            p.startswith("_") for p in rel.parts
        ):  # igual que el indexador de Atlas
            continue
        revisados += 1
        try:
            lineas = f.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            ilegibles.append(str(rel))
            continue
        for n, linea in enumerate(lineas, 1):
            if rx.search(linea):
                total += 1
                if len(hallazgos) < maximo:
                    hallazgos.append(
                        {"archivo": str(rel), "linea": n, "texto": linea.strip()[:220]}
                    )
    return {
        "estado": "ok",
        "raiz": str(base),
        "archivos_revisados": revisados,
        "archivos_ilegibles": ilegibles,
        "total": total,
        "mostradas": len(hallazgos),
        "truncado": total > len(hallazgos),
        "coincidencias": hallazgos,
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("patron")
    ap.add_argument("--regex", action="store_true")
    ap.add_argument("--max", type=int, default=MAX_POR_DEFECTO)
    a = ap.parse_args(argv)
    r = busca(a.patron, regex=a.regex, maximo=a.max)
    if r["estado"] != "ok":
        print(f"COULD_NOT_RUN: {r['detalle']}", file=sys.stderr)
        return 2
    for c in r["coincidencias"]:
        print(f"{c['archivo']}:{c['linea']}: {c['texto']}")
    if r["archivos_ilegibles"]:
        print(
            f"COULD_NOT_RUN parcial: {len(r['archivos_ilegibles'])} archivos ilegibles",
            file=sys.stderr,
        )
    if r["total"] == 0:
        print(
            f"0 coincidencias en {r['raiz']} ({r['archivos_revisados']} archivos revisados)",
            file=sys.stderr,
        )
        return 1
    if r["truncado"]:
        print(
            f"# {r['mostradas']} de {r['total']} coincidencias (usa --max)",
            file=sys.stderr,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
