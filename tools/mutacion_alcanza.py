"""El runner de mutacion del kit ALCANZA a este repo.

## Por que existe

`simplecode/verification/mutation_verify.py` viene vendorizado en cada
satelite, y hasta el 2026-09-25 no podia resolver el sujeto de un solo test
aqui: exigia una disposicion `root/src/` que este repo no tiene -- su codigo
vive en `tools/` y `bin/`. Medido ese dia con su propia funcion: **0 de 9**
ficheros de test resolvian, y en Atlas 0 de 365. Un gate vendorizado donde no
puede capturar nada es un defecto del instrumento, nunca evidencia de que el
sujeto este limpio.

El arreglo aterrizo aguas arriba (simplecode 8.3.1 y 8.3.2). Esto es lo que
impide que vuelva a perderse en silencio en la proxima sincronizacion del kit.

## Lo que NO mide, dicho antes de que alguien lo suponga

No mide si los tests son buenos. `mutation_verify --gate` sale 1 tanto con
WEAK como con COULD_NOT_RUN, y WEAK es el veredicto NORMAL aqui: el runner
muta el modulo entero y corre UN test, asi que un test enfocado sobre un
modulo de varias funciones deja mutantes vivos en las otras por construccion.
Medido el 2026-09-25 sobre cuatro tests de tres modulos distintos: los cuatro
WEAK.

Usar `--gate` como criterio de una ficha seria, por tanto, un criterio que no
puede pasar nunca -- tan inservible como uno que no puede fallar. Este script
contesta la pregunta que si tiene respuesta: **¿puede el runner encontrar el
sujeto de nuestros tests?**
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

RUNTIME = ".simplecode/runtime.zip"


def resuelven(raiz: Path) -> tuple[int, int]:
    """Cuantos ficheros de `tests/` resuelven su sujeto, y cuantos hay."""
    sys.path.insert(0, str(raiz / RUNTIME))
    from simplecode.verification import mutation_verify as mv

    ficheros = sorted((raiz / "tests").glob("test_*.py"))
    alcanzados = sum(1 for t in ficheros if mv.resolve_source_for_test(t, raiz) is not None)
    return alcanzados, len(ficheros)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--root", default=".", help="raiz del repo")
    args = p.parse_args(argv)

    raiz = Path(args.root).resolve()
    alcanzados, total = resuelven(raiz)
    print(f"[mutacion-alcanza] {alcanzados} de {total} ficheros de test resuelven su sujeto")
    if alcanzados == 0:
        print("[mutacion-alcanza] FAIL: el runner de mutacion no alcanza a este repo.")
        print("[mutacion-alcanza] No es que los tests sean malos: es que el instrumento "
              "no encuentra que mutar, y entonces no puede capturar nada.")
        return 1
    return 0


if __name__ == "__main__":  # pragma: no cover -- entry point, ejercitado via main()
    sys.exit(main())
