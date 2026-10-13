"""entrega_cosecha_foro: frontmatter de solo cadenas (el indexador de Atlas fallo con otros tipos), truncado declarado, manifiesto."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

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


def _j(p: Path, d: dict) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(d), encoding="utf-8")


def _evidencia(tmp: Path) -> tuple[Path, Path, Path]:
    ev, h1, h2 = tmp / "ev", tmp / "h1", tmp / "h2"
    _j(ev / "ola1-resultados/10.json", {"id": 10, "utilidad_atom": "alta"})
    _j(ev / "ola1-resultados/11.json", {"id": 11, "utilidad_atom": "baja"})
    _j(ev / "ola1-resultados/12.json", {"id": 12, "utilidad_atom": "media"})
    _j(ev / "ola2-triaje/20.json", {"id": 20, "candidato": "quizas"})
    _j(ev / "ola2-triaje/21.json", {"id": 21, "candidato": "no"})
    return ev, h1, h2


def test_candidatos_filtra_por_nivel_y_adjunta_inventario(tmp_path: Path) -> None:
    ev, h1, h2 = _evidencia(tmp_path)
    cs = e.candidatos(ev, h1, h2, {10: {"titulo": "T10"}})
    assert [(c["id"], c["fuente"], c["nivel"]) for c in cs] == [(10, "oleada1", "alta"), (12, "oleada1", "media"), (20, "oleada2", "quizas")]
    assert cs[0]["inv"] == {"titulo": "T10"} and cs[1]["inv"] == {}
    assert cs[0]["texto"] == h1 / "threads/10.txt" and cs[2]["texto"] == h2 / "threads/20.txt"
    assert {11, 21}.isdisjoint(c["id"] for c in cs)  # control negativo: baja y no quedan fuera


def test_cuerpo_oleada1_con_mecanismos_y_omision(tmp_path: Path) -> None:
    t = tmp_path / "t.txt"
    t.write_text("texto del hilo", encoding="utf-8")
    res = {"clase": "mecanismo", "utilidad_atom": "alta", "razon": "porque si", "omision_nvidia": "no documentan X",
           "mecanismos": [{"que": "contar", "como": "cat x", "fuente_post": 3, "repositorio": "r", "licencia": "MIT", "riesgo": "bajo"}]}
    texto, trunc = e.cuerpo({"fuente": "oleada1", "res": res, "texto": t})
    assert trunc is False
    assert "Clase: mecanismo · utilidad: alta · lectura: no declarada" in texto
    assert "**contar** — `cat x` (post 3; repositorio: r; licencia: MIT; riesgo: bajo)" in texto
    assert "Omision de NVIDIA: no documentan X" in texto and "texto del hilo" in texto


def test_cuerpo_oleada1_sin_omision_ni_mecanismos(tmp_path: Path) -> None:
    t = tmp_path / "t.txt"
    t.write_text("h", encoding="utf-8")
    texto, _ = e.cuerpo({"fuente": "oleada1", "res": {"clase": "c", "utilidad_atom": "media", "razon": "r", "lectura": "completa"}, "texto": t})
    assert "lectura: completa" in texto and "Omision de NVIDIA" not in texto and "- **" not in texto


def test_cuerpo_oleada2_y_texto_no_disponible(tmp_path: Path) -> None:
    res = {"candidato": "si", "senales": ["a", "b"], "una_frase": "frase"}
    texto, trunc = e.cuerpo({"fuente": "oleada2", "res": res, "texto": tmp_path / "no_existe.txt"})
    assert "Triaje: si · senales: a, b" in texto and "frase" in texto and "Lectura corta" in texto
    assert "(texto no disponible)" in texto and trunc is False


def test_cuerpo_no_trunca_en_el_limite_exacto(tmp_path: Path) -> None:
    t = tmp_path / "t.txt"
    t.write_text("y" * e.TOPE_TEXTO, encoding="utf-8")
    c = {"fuente": "oleada2", "res": {"candidato": "si", "una_frase": "f"}, "texto": t}
    assert e.cuerpo(c)[1] is False
    t.write_text("y" * (e.TOPE_TEXTO + 1), encoding="utf-8")
    texto, trunc = e.cuerpo(c)
    assert trunc is True and "[...truncado...]" in texto


def test_escribe_titulo_de_respaldo_y_proposito_desconocido(tmp_path: Path) -> None:
    c = _cand(tmp_path, 7, "t")
    c["inv"] = {}
    c["res"] = {**c["res"], "proposito": ["medir", "inventado"], "una_frase": "", "razon": "razon\ncon salto"}
    e.escribe(tmp_path / "out", [c], "2026-10-12", {})
    assert (tmp_path / "out" / "hilo_7_tema_7.md").exists()
    cat = (tmp_path / "out" / "catalogo_mecanismos.md").read_text(encoding="utf-8")
    assert "## medir (1)" in cat and "razon con salto" in cat and "inventado" not in cat


def _raiz_falsa(tmp: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    raiz = tmp / "repo"
    (raiz / "tools").mkdir(parents=True)
    monkeypatch.setattr(e, "__file__", str(raiz / "tools" / "entrega_cosecha_foro.py"))
    monkeypatch.setenv("HOME", str(tmp / "home"))
    ev = raiz / "tasks/evidence/FEATURE-COSECHA-FORO-CATEGORIAS-722-723-01"
    _j(ev / "inventario.json", {"temas": [{"id": 10, "titulo": "Tema diez"}]})
    _j(ev / "inventario-721-33.json", {"temas": [{"id": 20, "titulo": "Tema veinte"}]})
    _j(ev / "ola1-verificacion.json", {"cobertura_completa": True})
    _j(ev / "ola2-verificacion.json", {})
    _j(ev / "ola1-resultados/10.json", {"id": 10, "clase": "c", "utilidad_atom": "alta", "razon": "r", "proposito": ["medir"]})
    _j(ev / "ola2-triaje/20.json", {"id": 20, "candidato": "si", "senales": [], "una_frase": "f", "proposito": ["prevenir"]})
    return ev


def test_main_sin_argumentos_o_con_dos_da_uso_y_2(capsys: pytest.CaptureFixture[str]) -> None:
    assert e.main([]) == 2 and "uso:" in capsys.readouterr().err
    assert e.main(["a", "b"]) == 2


def test_main_entrega_carpeta_y_manifiesto_en_formato_sha256sum(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    ev = _raiz_falsa(tmp_path, monkeypatch)
    destino = tmp_path / "atlas"
    assert e.main([str(destino)]) == 0
    assert "4 archivos escritos" in capsys.readouterr().out
    man = (ev / "entrega_atlas_manifiesto.sha256").read_text(encoding="utf-8").splitlines()
    assert len(man) == 4
    for ln in man:
        h, n = ln.split("  ", 1)
        assert hashlib.sha256((destino / n).read_bytes()).hexdigest() == h
    assert "Tema diez" in (destino / "hilo_10_tema_diez.md").read_text(encoding="utf-8")
    assert '"oleada1": true, "oleada2": null' in (destino / "00_INDICE.md").read_text(encoding="utf-8")


def test_main_sin_inventario_falla_sin_escribir_destino(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    ev = _raiz_falsa(tmp_path, monkeypatch)
    (ev / "inventario.json").unlink()
    with pytest.raises(FileNotFoundError):
        e.main([str(tmp_path / "atlas")])
    assert not (tmp_path / "atlas").exists()
