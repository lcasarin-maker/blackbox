#!/usr/bin/env python3
"""Guardia de integridad de los archivos de texto versionados.

Reemplaza a las guardias de corrupcion del kit anterior. Un archivo de texto con bytes NUL, UTF-8 invalido, BOM,
finales de linea CRLF o mojibake (una vocal acentuada leida como dos caracteres) se rechaza: son las formas en que un log o una ficha llegan danados
(medido en este repo: un `remine_lote_*.txt` con 167 bytes NUL; mojibake al pasar texto por otra codificacion).

Uso: `python3 -m tools.guardia_integridad archivos...` o `--arbol` (recorre `git ls-files`). Sin archivos ni `--arbol` no examina nada: pre-commit lanza el hook en paralelo y algunos lotes llegan vacios. Sale 0 limpio,
1 con hallazgos, 2 si no pudo enumerar el arbol (COULD_NOT_RUN). Los binarios (por extension) no se examinan.
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

EXTENSIONES_TEXTO = frozenset({
    ".md", ".txt", ".py", ".sh", ".json", ".jsonl", ".yaml", ".yml", ".toml", ".service", ".timer", ".conf",
    ".cfg", ".ini", ".rules", ".patch", ".csv", ".log",
})
# Secuencias que aparecen cuando UTF-8 se lee como Latin-1/CP1252 y se vuelve a guardar.
MOJIBAKE = re.compile(
    "\u00c3[\u00a1\u00a9\u00ad\u00b3\u00ba\u00f1\u00c1\u00c9\u00cd\u00d3\u00da\u00d1\u00bc\u00b6\u00a4]"
    "|\u00e2\u20ac[\u2122\u0153\u009d\u0093\u0094\u00a6\u201c\u201d\u02dc]"
    "|\u00c2[\u00a0 \u00bf\u00a1]"
)


def problemas(datos: bytes) -> list[str]:
    """Lista de problemas de un archivo de texto; vacia si esta integro."""
    encontrados: list[str] = []
    nul = datos.count(b"\x00")
    if nul:
        encontrados.append(f"{nul} bytes NUL")
    if datos.startswith(b"\xef\xbb\xbf"):
        encontrados.append("BOM al inicio")
    if b"\r\n" in datos:
        encontrados.append("finales de linea CRLF")
    try:
        texto = datos.decode("utf-8")
    except UnicodeDecodeError as exc:
        encontrados.append(f"UTF-8 invalido en el byte {exc.start}")
        return encontrados
    m = MOJIBAKE.search(texto)
    if m:
        encontrados.append(f"mojibake {m.group(0)!r}")
    return encontrados


def _archivos_versionados(raiz: Path) -> list[Path] | None:
    r = subprocess.run(["git", "-C", str(raiz), "ls-files", "-z"], capture_output=True, check=False)
    if r.returncode != 0:
        return None
    return [raiz / p for p in r.stdout.decode("utf-8", "replace").split("\0") if p]


def main(argv: list[str] | None = None, raiz: Path | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    raiz = raiz or Path.cwd()
    arbol = "--arbol" in args
    args = [a for a in args if a != "--arbol"]
    archivos = _archivos_versionados(raiz) if arbol else [Path(a) for a in args]
    if archivos is None:
        print("[guardia-integridad] COULD_NOT_RUN: git ls-files fallo; no se pudo enumerar el arbol", file=sys.stderr)
        return 2
    malos = 0
    examinados = 0
    for f in archivos:
        if f.suffix.lower() not in EXTENSIONES_TEXTO or not f.is_file():
            continue
        examinados += 1
        for p in problemas(f.read_bytes()):
            malos += 1
            print(f"[guardia-integridad] {f}: {p}", file=sys.stderr)
    print(f"[guardia-integridad] hallazgos={malos} examinados={examinados}")
    return 1 if malos else 0


if __name__ == "__main__":
    sys.exit(main())
