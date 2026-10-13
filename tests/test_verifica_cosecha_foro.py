"""verifica_cosecha_foro: la completitud se prueba sobre el sujeto (texto bajado + resultado valido), con tres estados."""

from __future__ import annotations

import json
from pathlib import Path

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
