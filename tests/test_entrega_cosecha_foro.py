"""entrega_cosecha_foro: frontmatter de solo cadenas (el indexador de Atlas fallo con otros tipos), truncado declarado, manifiesto."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from tools import entrega_cosecha_foro as e


def _cand(tmp: Path, tid: int, texto: str, fuente: str = "oleada2") -> dict:
    p = tmp / f"{tid}.txt"
    p.write_text(texto, encoding="utf-8")
    res = {"id": tid, "candidato": "si", "senales": ["reloj"], "una_frase": "reloj atascado con ciclo de corriente", "proposito": ["solucionar"]}
    return {"id": tid, "fuente": fuente, "res": res, "texto": p, "nivel": "si", "inv": {"titulo": "GPU clock: bug (año 2026) / ¿qué?"}}


def _valores_frontmatter(md: str) -> dict[str, object]:
    cabecera = md.split("---\n")[1]
    return {ln.split(": ", 1)[0]: json.loads(ln.split(": ", 1)[1]) for ln in cabecera.splitlines()}


def test_todo_valor_del_frontmatter_es_cadena(tmp_path: Path) -> None:
    m = e.escribe(tmp_path / "out", [_cand(tmp_path, 1, "POST 1 | u | f | url\nhola")], "2026-10-12", {"oleada1": True})
    md = next((tmp_path / "out").glob("hilo_1_*.md")).read_text(encoding="utf-8")
    vals = _valores_frontmatter(md)
    assert vals and all(isinstance(v, str) for v in vals.values()) and vals["id"] == "1"
    assert "00_INDICE.md" in m and "catalogo_mecanismos.md" in m


def test_texto_largo_se_trunca_y_se_declara(tmp_path: Path) -> None:
    e.escribe(tmp_path / "out", [_cand(tmp_path, 2, "x" * (e.TOPE_TEXTO + 50))], "2026-10-12", {})
    md = next((tmp_path / "out").glob("hilo_2_*.md")).read_text(encoding="utf-8")
    assert _valores_frontmatter(md)["texto_truncado"] == "si" and "[...truncado...]" in md


def test_manifiesto_tiene_el_sha256_de_cada_archivo(tmp_path: Path) -> None:
    m = e.escribe(tmp_path / "out", [_cand(tmp_path, 3, "hola")], "2026-10-12", {})
    for nombre, h in m.items():
        assert hashlib.sha256((tmp_path / "out" / nombre).read_bytes()).hexdigest() == h


def test_nombre_de_archivo_sin_caracteres_raros() -> None:
    assert e.slug("GPU clock: bug (año 2026) / ¿qué?") == "gpu_clock_bug_ano_2026_que"
    assert e.slug("???") == "sin_titulo"


def test_el_catalogo_agrupa_por_proposito(tmp_path: Path) -> None:
    e.escribe(tmp_path / "out", [_cand(tmp_path, 4, "t")], "2026-10-12", {})
    cat = (tmp_path / "out" / "catalogo_mecanismos.md").read_text(encoding="utf-8")
    assert "## solucionar (1)" in cat and "## medir (0)" in cat
