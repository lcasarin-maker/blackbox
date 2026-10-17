"""Mide el --avoid desplegado y el pendiente contra data/procesos_protegidos.json (solo lectura, sin root).

Tres instrumentos: el matcher del repo (tests/test_procesos_protegidos.faltan_en_earlyoom, re.search sin anclar),
`grep -E` (regcomp/regexec de glibc, POSIX ERE como earlyoom 1.7) y, sobre los comm vivos de `ps -eo comm`, solo
cuentas (no se imprimen nombres ajenos a la lista). Uso, desde la raiz del repo:
    python3 tasks/evidence/DEBT-EARLYOOM-AVOID-NO-CUBRE-LA-LISTA-UNICA-01/mide_avoid.py
"""

from __future__ import annotations

import importlib
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[3]


def grep_e(regex: str, comms: list[str]) -> set[str]:
    r = subprocess.run(["grep", "-E", regex], input="\n".join(comms) + "\n", capture_output=True, text=True)
    return set(r.stdout.split("\n")) - {""}


def main() -> int:
    sys.path.insert(0, str(RAIZ))
    tp = importlib.import_module("tests.test_procesos_protegidos")
    exactos_prefijos, d = tp._fichero()
    nombres = sorted(e["nombre"] for e in d["comm"])
    ps = subprocess.run(["ps", "-eo", "comm="], capture_output=True, text=True, check=True).stdout
    vivos = sorted(set(ps.split("\n")) - {""})
    regs = {}
    for etiqueta, ruta in (("desplegado", tp.EARLYOOM), ("pendiente", tp.EARLYOOM_PENDIENTE)):
        avoid = tp._avoid_earlyoom(ruta)
        regs[etiqueta] = avoid
        falta_py = sorted(tp.faltan_en_earlyoom(ruta))
        falta_ere = sorted(set(nombres) - grep_e(avoid.pattern, nombres))
        print(f"== {etiqueta}: {ruta.relative_to(RAIZ)}")
        print(f"   --avoid {avoid.pattern}")
        print(f"   nombres de la lista: {len(nombres)}; faltan (re.search): {len(falta_py)} {falta_py}")
        print(f"   faltan (grep -E, POSIX ERE): {len(falta_ere)} {falta_ere}")
        print(f"   los dos instrumentos coinciden: {falta_py == falta_ere}")
        print(f"   NO_PROTEGIDOS {list(tp.NO_PROTEGIDOS)} evitados: {[c for c in tp.NO_PROTEGIDOS if avoid.search(c)]}")
    evita = {k: {c for c in vivos if r.search(c)} for k, r in regs.items()}
    nuevos = evita["pendiente"] - evita["desplegado"]
    fuera = sorted(c for c in nuevos if not tp._protege(*exactos_prefijos, c))
    print(f"== comm vivos distintos (ps -eo comm): {len(vivos)}")
    print(f"   evitados por el desplegado: {len(evita['desplegado'])}; por el pendiente: {len(evita['pendiente'])}")
    print(f"   evitados por el desplegado y NO por el pendiente (debe ser 0): "
          f"{len(evita['desplegado'] - evita['pendiente'])}")
    print(f"   evitados solo por el pendiente: {len(nuevos)}; de ellos fuera de la lista unica: {len(fuera)} {fuera}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
