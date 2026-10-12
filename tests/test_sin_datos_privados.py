"""Guarda del repo publico: ningun archivo versionado gana datos de la maquina ni de proyectos privados.

Medido el 2026-10-11 (analisis bb/Atlas): el arbol ya publicaba MACs, IPs de LAN, el hostname y nombres de
proyectos privados dentro de evidencias historicas. Esas evidencias llevan hashes de procedencia y NO se
reescriben; quedan en `datos_privados_baseline.json` con su cuenta. La guarda falla si un archivo nuevo
contiene estos datos o si uno de la lista sube su cuenta. La lista solo puede encogerse.
"""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
BASE = Path(__file__).parent / "fixtures" / "datos_privados_baseline.json"
PATRON = re.compile(
    r"(?:[0-9a-f]{2}:){5}[0-9a-f]{2}|192\.168\.100\.25|10\.194\.62\.85|aitopatom-41f1"
    r"|aequitas|own_chats|office2office|cuenza|declutter",
    re.I,
)


def cuenta(texto: str) -> int:
    return len(PATRON.findall(texto))


def archivos_versionados() -> list[str]:
    r = subprocess.run(
        ["git", "ls-files", "-z"], cwd=RAIZ, capture_output=True, check=True
    )
    return [p for p in r.stdout.decode().split("\0") if p]


def medir() -> dict[str, int]:
    out: dict[str, int] = {}
    ilegibles: list[str] = []
    for rel in archivos_versionados():
        if rel == "tests/fixtures/datos_privados_baseline.json" or rel == Path(__file__).relative_to(RAIZ).as_posix():
            continue
        p = RAIZ / rel
        try:
            if not p.is_file():
                continue
            n = cuenta(p.read_bytes().decode("utf-8", errors="ignore"))
        except OSError:
            ilegibles.append(rel)
            continue
        if n:
            out[rel] = n
    assert ilegibles == [], f"archivos versionados que no se pudieron leer: {ilegibles}"
    return out


def compara(actual: dict[str, int], base: dict[str, int]) -> list[str]:
    faltas = [f"{r}: archivo nuevo con {n} dato(s) privado(s)" for r, n in actual.items() if r not in base]
    faltas += [f"{r}: sube de {base[r]} a {n}" for r, n in actual.items() if r in base and n > base[r]]
    return faltas


def test_el_repo_no_gana_datos_privados():
    base = json.loads(BASE.read_text(encoding="utf-8"))
    assert compara(medir(), base) == []


def test_la_guarda_detecta_un_archivo_nuevo_y_una_subida():
    assert compara({"nuevo.md": 1}, {}) == ["nuevo.md: archivo nuevo con 1 dato(s) privado(s)"]
    assert compara({"a.md": 3}, {"a.md": 2}) == ["a.md: sube de 2 a 3"]
    assert compara({"a.md": 2}, {"a.md": 2}) == []
    assert cuenta("host aitopatom-41f1 y 48:21:0b:95:41:f1") == 2
    assert cuenta("texto limpio") == 0
