"""verifica_cosecha_foro: la completitud se prueba sobre el sujeto (texto bajado + resultado valido), con tres estados."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tools import verifica_cosecha_foro as v


def _tema(hilos: Path, tid: int, *, esperados: int = 2, bajados: int = 2, texto: bool = True, error: str | None = None) -> None:
    d = hilos / "threads"
    d.mkdir(parents=True, exist_ok=True)
    if error:
        rec = {"id": tid, "status": "could_not_run", "error": error}
    else:
        rec = {"id": tid, "status": "fetched", "posts_expected": esperados, "posts_fetched": bajados}
    (d / f"{tid}.fetch.json").write_text(json.dumps(rec), encoding="utf-8")
    if texto and not error:
        cuerpo = "".join(f"\nPOST {i} | u | f | url\nhola mundo de prueba largo" for i in range(1, esperados + 1))
        (d / f"{tid}.txt").write_text("titulo\nurl\n" + cuerpo, encoding="utf-8")


def _res(tid: int, **kw: object) -> dict:
    base = {"id": tid, "titulo": "t", "leido": True, "posts_leidos": 2, "clase": "ruido", "proposito": [],
            "mecanismos": [], "lectura": "completa", "utilidad_atom": "ninguna", "razon": "no aporta nada reutilizable al caso"}
    base.update(kw)
    return base


def _guarda(res: Path, d: dict) -> None:
    res.mkdir(parents=True, exist_ok=True)
    (res / f"{d['id']}.json").write_text(json.dumps(d), encoding="utf-8")


def test_cobertura_completa(tmp_path: Path) -> None:
    h, r = tmp_path / "h", tmp_path / "r"
    _tema(h, 1)
    _guarda(r, _res(1))
    out = v.verifica([{"id": 1}], h, r)
    assert out["cobertura_completa"] is True and out["descarga"]["descargado"] == 1


def test_tema_sin_resultado_no_es_limpio(tmp_path: Path) -> None:
    h, r = tmp_path / "h", tmp_path / "r"
    _tema(h, 1)
    _tema(h, 2)
    _guarda(r, _res(1))
    out = v.verifica([{"id": 1}, {"id": 2}], h, r)
    assert out["sin_resultado"] == [2] and out["cobertura_completa"] is False


def test_mensajes_faltantes_son_fallo_de_descarga(tmp_path: Path) -> None:
    h, r = tmp_path / "h", tmp_path / "r"
    _tema(h, 1, esperados=5, bajados=3)
    out = v.verifica([{"id": 1}], h, r)
    assert 1 in out["fallos_de_descarga"] and out["cobertura_completa"] is False


def test_404_es_vacio_del_producto_y_no_hueco(tmp_path: Path) -> None:
    h, r = tmp_path / "h", tmp_path / "r"
    _tema(h, 1, error="HTTP Error 404: Not Found")
    out = v.verifica([{"id": 1}], h, r)
    assert out["descarga"]["vacio_del_producto"] == 1 and out["cobertura_completa"] is True


def test_error_de_red_si_cuenta_como_fallo(tmp_path: Path) -> None:
    h, r = tmp_path / "h", tmp_path / "r"
    _tema(h, 1, error="<urlopen error timed out>")
    assert v.verifica([{"id": 1}], h, r)["cobertura_completa"] is False


def test_utilidad_alta_sin_mecanismo_es_invalida() -> None:
    assert any("alta sin ningun mecanismo" in m for m in v.valida_resultado(_res(1, utilidad_atom="alta"), 1))


def test_clase_mecanismo_exige_comando_o_formula() -> None:
    mal = _res(1, clase="mecanismo", mecanismos=[{"que": "x", "como": "", "fuente_post": 1}])
    assert any("faltan que/como" in m for m in v.valida_resultado(mal, 1))
    bien = _res(1, clase="mecanismo", utilidad_atom="alta", proposito=["medir"],
                mecanismos=[{"que": "leer", "como": "cat /proc/meminfo", "fuente_post": 3}])
    assert v.valida_resultado(bien, 1) == []


def test_resultado_que_no_demuestra_lectura() -> None:
    assert v.valida_resultado(_res(1, leido=False), 1) and v.valida_resultado(_res(1, posts_leidos=0), 1)


def test_id_cruzado_se_detecta() -> None:
    assert any("distinto" in m for m in v.valida_resultado(_res(9), 1))


def test_lectura_parcial_no_es_cobertura_completa(tmp_path: Path) -> None:
    h, r = tmp_path / "h", tmp_path / "r"
    _tema(h, 1, esperados=2, bajados=2)
    _guarda(r, _res(1, posts_leidos=2, lectura="parcial"))
    out = v.verifica([{"id": 1}], h, r)
    assert 1 in out["lectura_parcial_por_completar"] and out["cobertura_completa"] is False


def test_declarar_mas_mensajes_de_los_que_tiene_el_tema(tmp_path: Path) -> None:
    h, r = tmp_path / "h", tmp_path / "r"
    _tema(h, 1, esperados=2, bajados=2)
    _guarda(r, _res(1, posts_leidos=9))
    out = v.verifica([{"id": 1}], h, r)
    assert 1 in out["lectura_declarada_de_mas"] and out["cobertura_completa"] is False


def test_posts_leidos_menor_que_los_reales_se_marca_aunque_diga_completa(tmp_path: Path) -> None:
    h, r = tmp_path / "h", tmp_path / "r"
    _tema(h, 1, esperados=8, bajados=8)
    _guarda(r, _res(1, posts_leidos=3, lectura="completa"))
    assert 1 in v.verifica([{"id": 1}], h, r)["lectura_parcial_por_completar"]


def test_diferencia_de_un_mensaje_es_contabilidad_y_no_parcial(tmp_path: Path) -> None:
    h, r = tmp_path / "h", tmp_path / "r"
    _tema(h, 1, esperados=6, bajados=6)
    _guarda(r, _res(1, posts_leidos=7))
    out = v.verifica([{"id": 1}], h, r)
    assert 1 in out["diferencia_de_contabilidad_tolerada"] and out["cobertura_completa"] is True


def test_resultado_sin_campo_lectura_es_invalido() -> None:
    d = _res(1)
    del d["lectura"]
    assert any("lectura" in m for m in v.valida_resultado(d, 1))


def _tri(tid: int, **kw: object) -> dict:
    base = {"id": tid, "leido": True, "mensajes_leidos": 2, "candidato": "no", "proposito": [], "senales": [], "una_frase": "pregunta sin respuesta sobre la instalacion inicial"}
    base.update(kw)
    return base


def test_triaje_valido_y_conteo_de_candidatos(tmp_path: Path) -> None:
    h, r = tmp_path / "h", tmp_path / "r"
    _tema(h, 1)
    _tema(h, 2)
    _guarda(r, _tri(1))
    _guarda(r, _tri(2, candidato="si", proposito=["medir"], senales=["reloj"]))
    out = v.verifica_triaje([{"id": 1}, {"id": 2}], h, r)
    assert out["cobertura_completa"] is True and out["candidatos"] == {"si": 1, "quizas": 0, "no": 1}


def test_triaje_si_sin_proposito_es_invalido() -> None:
    assert any("exige proposito" in m for m in v.valida_triaje(_tri(1, candidato="si"), 1))


def test_triaje_tema_sin_resultado_no_es_cobertura(tmp_path: Path) -> None:
    h, r = tmp_path / "h", tmp_path / "r"
    _tema(h, 1)
    out = v.verifica_triaje([{"id": 1}], h, r)
    assert out["sin_resultado"] == [1] and out["cobertura_completa"] is False


def test_triaje_declarar_de_mas_se_detecta(tmp_path: Path) -> None:
    h, r = tmp_path / "h", tmp_path / "r"
    _tema(h, 1, esperados=2, bajados=2)
    _guarda(r, _tri(1, mensajes_leidos=30))
    assert 1 in v.verifica_triaje([{"id": 1}], h, r)["lectura_declarada_de_mas"]


def test_estado_descarga_ramas_de_recibo_y_texto(tmp_path: Path) -> None:
    h = tmp_path / "h"
    assert v.estado_descarga(h, 1) == ("no_se_pudo", "sin recibo de descarga")
    _tema(h, 2, texto=False)
    assert v.estado_descarga(h, 2) == ("no_se_pudo", "recibo dice fetched pero falta el texto")
    _tema(h, 3)
    (h / "threads" / "3.txt").write_text("POST 1 |", encoding="utf-8")
    assert v.estado_descarga(h, 3) == ("no_se_pudo", "texto vacio")
    (h / "threads" / "3.txt").write_text("sin marcas de mensaje " * 5, encoding="utf-8")
    assert v.estado_descarga(h, 3) == ("no_se_pudo", "texto vacio")
    _tema(h, 4)
    assert v.estado_descarga(h, 4) == ("descargado", "")  # control negativo: el mismo camino puede dar descargado
    _tema(h, 5, error="HTTP Error 403: Forbidden")
    assert v.estado_descarga(h, 5)[0] == "vacio_del_producto"
    _tema(h, 6, error="")
    (h / "threads" / "6.fetch.json").write_text(json.dumps({"status": "could_not_run"}), encoding="utf-8")
    assert v.estado_descarga(h, 6) == ("no_se_pudo", "sin detalle")


def test_mensajes_reales_cuenta_marcas_y_tolera_texto_ausente(tmp_path: Path) -> None:
    h = tmp_path / "h"
    assert v.mensajes_reales(h, 1) == 0
    _tema(h, 2, esperados=3, bajados=3)
    assert v.mensajes_reales(h, 2) == 3
    (h / "threads" / "2.txt").write_text("POST 1 | a\nx\nPOST 2 | b\ny", encoding="utf-8")
    assert v.mensajes_reales(h, 2) == 2


def test_valida_resultado_ramas_de_error() -> None:
    assert v.valida_resultado([], 1) == ["no es un objeto JSON"]
    malos = v.valida_resultado(_res(1, clase="x", utilidad_atom="y", lectura="z", proposito="medir", razon="corta", mecanismos="no"), 1)
    texto = " | ".join(malos)
    for frag in ("clase invalida", "utilidad_atom invalida", "lectura debe ser", "proposito debe ser", "razon ausente", "mecanismos debe ser una lista"):
        assert frag in texto
    assert any("proposito debe ser" in m for m in v.valida_resultado(_res(1, proposito=["inventado"]), 1))
    assert any("clase mecanismo sin mecanismos" in m for m in v.valida_resultado(_res(1, clase="mecanismo"), 1))
    assert any("mecanismo 0" in m for m in v.valida_resultado(_res(1, mecanismos=["no dict"]), 1))
    assert any("mecanismo 0" in m for m in v.valida_resultado(_res(1, mecanismos=[{"que": "a", "como": "b", "fuente_post": "3"}]), 1))


def test_verifica_resultado_invalido_no_es_limpio(tmp_path: Path) -> None:
    h, r = tmp_path / "h", tmp_path / "r"
    _tema(h, 1)
    _guarda(r, _res(1, clase="x"))
    out = v.verifica([{"id": 1}], h, r)
    assert 1 in out["resultados_invalidos"] and out["cobertura_completa"] is False


def test_valida_triaje_ramas_de_error() -> None:
    assert v.valida_triaje("x", 1) == ["no es un objeto JSON"]
    assert v.valida_triaje(_tri(1), 1) == []  # control negativo: un triaje bueno no produce problemas
    assert any("distinto" in m for m in v.valida_triaje(_tri(9), 1))
    assert any("candidato invalido" in m for m in v.valida_triaje(_tri(1, candidato="tal vez"), 1))
    assert any("booleano" in m for m in v.valida_triaje(_tri(1, leido="si"), 1))
    assert any("sin mensajes_leidos" in m for m in v.valida_triaje(_tri(1, mensajes_leidos=0), 1))
    assert any("proposito debe ser" in m for m in v.valida_triaje(_tri(1, proposito="medir"), 1))
    assert any("senales" in m for m in v.valida_triaje(_tri(1, senales="x"), 1))
    assert any("una_frase" in m for m in v.valida_triaje(_tri(1, una_frase="corta"), 1))


def test_verifica_triaje_fallos_invalidos_y_vacio(tmp_path: Path) -> None:
    h, r = tmp_path / "h", tmp_path / "r"
    _tema(h, 1, esperados=5, bajados=3)
    _tema(h, 2)
    _tema(h, 3, error="HTTP Error 404: Not Found")
    _guarda(r, _tri(1))
    _guarda(r, _tri(2, candidato="si"))
    out = v.verifica_triaje([{"id": 1}, {"id": 2}, {"id": 3}], h, r)
    assert 1 in out["fallos_de_descarga"] and 2 in out["resultados_invalidos"]
    assert out["descarga"]["vacio_del_producto"] == 1 and 3 not in out["sin_resultado"]
    assert out["cobertura_completa"] is False


def test_verifica_triaje_ids_candidatos_excluyen_no(tmp_path: Path) -> None:
    h, r = tmp_path / "h", tmp_path / "r"
    _tema(h, 1)
    _tema(h, 2)
    _guarda(r, _tri(1, candidato="quizas", proposito=["medir"]))
    _guarda(r, _tri(2))
    out = v.verifica_triaje([{"id": 1}, {"id": 2}], h, r)
    assert out["ids_candidatos"] == {"si": [], "quizas": [1]}


def _carpetas(tmp_path: Path, inv: object) -> list[str]:
    ruta = tmp_path / "inv.json"
    ruta.write_text(json.dumps(inv), encoding="utf-8")
    return ["--inventario", str(ruta), "--hilos", str(tmp_path / "h"), "--resultados", str(tmp_path / "r")]


def test_main_sin_triaje_rc0_y_rc1(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    _tema(tmp_path / "h", 1)
    _guarda(tmp_path / "r", _res(1))
    assert v.main(_carpetas(tmp_path, [{"id": 1}])) == 0
    assert json.loads(capsys.readouterr().out)["cobertura_completa"] is True
    assert v.main(_carpetas(tmp_path, {"temas": [{"id": 1}, {"id": 2}]})) == 1  # el tema 2 no existe: fallo
    assert json.loads(capsys.readouterr().out)["cobertura_completa"] is False


def test_main_con_triaje_rc0_y_rc1(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    _tema(tmp_path / "h", 1)
    _guarda(tmp_path / "r", _tri(1))
    assert v.main([*_carpetas(tmp_path, [{"id": 1}]), "--triaje"]) == 0
    assert "ids_candidatos" in json.loads(capsys.readouterr().out)
    assert v.main([*_carpetas(tmp_path, [{"id": 1}, {"id": 2}]), "--triaje"]) == 1
    assert "ids_candidatos" in json.loads(capsys.readouterr().out)
