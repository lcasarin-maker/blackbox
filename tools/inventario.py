"""Comprueba que los inventarios de SPEC.md describen el repo y la maquina.

Una tabla escrita a mano envejece en silencio: se anade un subcomando, nadie
toca la spec, y a partir de ahi la spec es lo que alguien recordaba. Esto la
ata al sujeto -- `bin/bb`, `tools/`, `adopted/` -- y bloquea el commit cuando
divergen.

Lo que NO hace: juzgar la prosa. Comprueba COBERTURA (que cada sujeto real
aparezca, y que ninguna fila describa algo que no existe), nunca si la
descripcion es buena.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

SEC_FUNCIONES = "## Inventario de funciones"
SEC_PROPIEDAD = "## Inventario de propiedad"
IGNORADOS = {"__init__.py", "__pycache__"}


def seccion(spec: str, titulo: str) -> str:
    """El texto entre `titulo` y el siguiente encabezado de nivel 2."""
    i = spec.find(titulo)
    if i < 0:
        raise LookupError(f"SPEC.md no tiene la seccion {titulo!r}")
    resto = spec[i + len(titulo) :]
    j = resto.find("\n## ")
    return resto if j < 0 else resto[:j]


def sujetos_ejecutables(root: Path) -> set[str]:
    """Lo que el repo ejecuta: subcomandos de bb, y cada fichero de bin/ y tools/."""
    bb = (root / "bin" / "bb").read_text(encoding="utf-8")
    nombres = {f"bb {m}" for m in re.findall(r"^cmd_([a-z_]+)\(\)", bb, re.M)}
    for d in ("bin", "tools"):
        for f in sorted((root / d).iterdir()):
            if f.is_file() and f.name not in IGNORADOS:
                nombres.add(f"{d}/{f.name}")
    nombres.discard("bin/bb")  # se inventaria por subcomando, no como fichero
    return nombres


def destino_desplegado(f: Path) -> str:
    """Donde vive en la maquina un fichero de adopted/, segun el mapeo de `bb drift`."""
    if f.parent.name == "system-config":
        return "/" + f.name.replace("_", "/")
    if f.parent.name == "systemd-user":
        return "~/.config/systemd/user/" + f.name
    return "/srv/ai/gpu_governance/" + f.name


def sujetos_adoptados(root: Path) -> set[str]:
    return {
        destino_desplegado(f)
        for f in sorted((root / "adopted").rglob("*"))
        if f.is_file()
    }


def citados(texto: str) -> set[str]:
    """Lo que la seccion nombra entre acentos graves, normalizado.

    Un subcomando se inventaria con sus argumentos (`bb scan ["hace X"]`), asi
    que se recorta a las dos primeras palabras. Sin esto el gate marcaba cinco
    subcomandos bien inventariados como ausentes -- defecto del instrumento,
    encontrado en su primera corrida.
    """
    fuera: set[str] = set()
    for c in re.findall(r"`([^`]+)`", texto):
        fuera.add(c)
        partes = c.split()
        if len(partes) > 1 and partes[0] == "bb":
            fuera.add(f"bb {partes[1]}")
    return fuera


def filas_de_tabla(texto: str) -> set[str]:
    """Solo la primera celda de cada fila de tabla, no la prosa de alrededor.

    La seccion de propiedad explica al final que `/etc/systemd/system.conf` NO
    se adopta. Leer eso como una fila hacia que el gate exigiera adoptarlo --
    el segundo defecto del instrumento en su primera corrida.
    """
    return {
        m.group(1)
        for m in re.finditer(r"^\|\s*`([^`]+)`\s*\|", texto, re.M)
    }


def revisa(root: Path) -> list[str]:
    """Devuelve los hallazgos. Lista vacia = los inventarios describen el sujeto."""
    spec = (root / "SPEC.md").read_text(encoding="utf-8")
    fallos: list[str] = []

    fun = citados(seccion(spec, SEC_FUNCIONES))
    for s in sorted(sujetos_ejecutables(root)):
        if s not in fun:
            fallos.append(f"funcion sin inventariar en SPEC.md: {s}")

    prop = filas_de_tabla(seccion(spec, SEC_PROPIEDAD))
    adoptados = sujetos_adoptados(root)
    for s in sorted(adoptados):
        if s not in prop:
            fallos.append(f"sujeto adoptado sin inventariar en SPEC.md: {s}")
    for s in sorted(prop):
        if s.startswith(("/", "~")) and s not in adoptados:
            fallos.append(f"SPEC.md inventaria algo que no esta en adopted/: {s}")

    return fallos


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--root", default=".", help="raiz del repo")
    p.add_argument("--check", action="store_true", help="sale 1 si hay hallazgos")
    args = p.parse_args(argv)

    fallos = revisa(Path(args.root))
    for f in fallos:
        print(f"  {f}")
    print(f"[inventario] HALLAZGOS: {len(fallos)}")
    if fallos:
        print("[inventario] FAIL: SPEC.md y el sujeto no coinciden.")
        print("[inventario] La spec describe lo que alguien recordaba, no lo que hay.")
        return 1
    print("[inventario] OK: los dos inventarios describen el repo y la maquina.")
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
