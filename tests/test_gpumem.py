"""bb gpumem: hojas de dmem.current, etiquetas de contenedor, SIN_REGION y el asesor cabe."""

from __future__ import annotations

from pathlib import Path

from tools import gpumem as g

REGION = "nvidia/0000000F:01:00.0/vidmem"
ID = "a" * 64


def _cg(raiz: Path, rel: str, bytes_: int) -> None:
    d = raiz / rel
    d.mkdir(parents=True, exist_ok=True)
    (d / "dmem.current").write_text(f"{REGION} {bytes_}\n", encoding="utf-8")


def _arbol(tmp: Path) -> Path:
    (tmp / "dmem.capacity").write_text(f"{REGION} 53794045952\n", encoding="utf-8")
    _cg(tmp, "", 3 * g.GIB)  # el padre suma a sus hijos
    _cg(tmp, "docker.slice", 2 * g.GIB)
    _cg(tmp, f"docker.slice/docker-{ID}.scope", 2 * g.GIB)
    _cg(tmp, "user.slice", 1 * g.GIB)
    return tmp


def test_solo_las_hojas_y_sin_doble_conteo(tmp_path: Path) -> None:
    r = g.informe(_arbol(tmp_path), docker={ID: "vllm"})
    assert r["estado"] == "OK"
    hojas = r["hojas"]
    assert isinstance(hojas, list)
    assert [(f["quien"], f["gib"]) for f in hojas] == [("contenedor vllm", 2.0), ("user.slice", 1.0)]
    assert r["cobrado_total_gib"] == 3.0 and r["sin_atribuir_gib"] == 0.0


def test_sin_region_se_declara_y_no_inventa(tmp_path: Path) -> None:
    r = g.informe(tmp_path, docker={})
    assert r["estado"] == "SIN_REGION" and "hojas" not in r


def test_sin_nombre_de_docker_se_usa_el_id_corto(tmp_path: Path) -> None:
    r = g.informe(_arbol(tmp_path), docker={})
    hojas = r["hojas"]
    assert isinstance(hojas, list)
    assert hojas[0]["quien"] == f"contenedor {ID[:12]}"


def test_cabe_y_no_cabe() -> None:
    assert g.cabe(20, 78 * 1048576)["cabe"] is True  # 78 GiB libres
    assert g.cabe(90, 78 * 1048576)["cabe"] is False
    assert g.cabe(70, 78 * 1048576)["cabe"] is True and g.cabe(71, 78 * 1048576)["cabe"] is False  # el margen de 8 GiB cuenta


def test_cabe_sin_meminfo_no_dice_que_si() -> None:
    assert g.cabe(1, None)["cabe"] is False
