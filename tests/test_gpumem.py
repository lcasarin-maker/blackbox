"""bb gpumem: hojas de dmem.current, etiquetas de contenedor, SIN_REGION y el asesor cabe."""

from __future__ import annotations

import json
import subprocess
from collections.abc import Callable
from pathlib import Path

import pytest

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


def test_capacidad_ausente_da_vacio_y_presente_da_pares(tmp_path: Path) -> None:
    assert g.capacidad(tmp_path) == {}
    assert g.capacidad(_arbol(tmp_path)) == {REGION: 53794045952}


def test_pares_ignora_lineas_que_no_son_region_bytes() -> None:
    assert g._pares(f"{REGION} 5\nbasura\n{REGION}x abc\na b c\n") == {REGION: 5}


def test_escanea_respeta_profundidad_y_cgroup_sin_archivo(tmp_path: Path) -> None:
    _cg(tmp_path, "a/b/c", g.GIB)
    (tmp_path / "a" / "vacio").mkdir()  # sin dmem.current: OSError, cuenta 0
    assert g.escanea(tmp_path, REGION) == [("a/b/c", g.GIB)]
    assert g.escanea(tmp_path, REGION, profundidad=1) == []  # control negativo: la hoja esta bajo el limite


def test_escanea_raiz_hoja_y_raiz_inexistente(tmp_path: Path) -> None:
    _cg(tmp_path, "", g.GIB)
    assert g.escanea(tmp_path, REGION) == [("", g.GIB)]
    assert g.escanea(tmp_path / "no_existe", REGION) == []  # iterdir falla: sin hojas, sin excepcion


def test_informe_sin_dmem_current_en_la_raiz_cobra_cero(tmp_path: Path) -> None:
    (tmp_path / "dmem.capacity").write_text(f"{REGION} {g.GIB}\n", encoding="utf-8")
    r = g.informe(tmp_path, docker={})
    assert r["estado"] == "OK" and r["cobrado_total_gib"] == 0.0 and r["hojas"] == []


def test_informe_sin_atribuir_cuando_el_total_supera_las_hojas(tmp_path: Path) -> None:
    _arbol(tmp_path)
    _cg(tmp_path, "", 5 * g.GIB)
    assert g.informe(tmp_path, docker={})["sin_atribuir_gib"] == 2.0


def test_etiqueta_contenedor_nombrado_ruta_y_raiz() -> None:
    assert g.etiqueta(f"docker.slice/docker-{ID}.scope", {ID: "vllm"}) == "contenedor vllm"
    assert g.etiqueta("user.slice/x", {}) == "user.slice/x"  # control negativo: no es scope de docker
    assert g.etiqueta("docker-corto.scope", {}) == "docker-corto.scope"
    assert g.etiqueta("", {}) == "(raiz)"


def _falso_run(salida: str) -> Callable[..., subprocess.CompletedProcess[str]]:
    def run(*_a: object, **_k: object) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess([], 0, stdout=salida, stderr="")

    return run


def test_nombres_docker_parsea_id_y_nombre(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(g.subprocess, "run", _falso_run(f"{ID} vllm\nsinespacio\n"))
    assert g.nombres_docker() == {ID: "vllm"}


@pytest.mark.parametrize("exc", [FileNotFoundError("docker"), subprocess.TimeoutExpired("docker", 5)])
def test_nombres_docker_sin_docker_o_con_timeout_da_vacio(monkeypatch: pytest.MonkeyPatch, exc: Exception) -> None:
    def run(*_a: object, **_k: object) -> None:
        raise exc

    monkeypatch.setattr(g.subprocess, "run", run)
    assert g.nombres_docker() == {}


def test_informe_sin_docker_pasado_consulta_nombres_docker(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(g, "nombres_docker", lambda: {ID: "desde_docker"})
    hojas = g.informe(_arbol(tmp_path))["hojas"]
    assert isinstance(hojas, list)
    assert hojas[0]["quien"] == "contenedor desde_docker"


def test_lee_mem_available(tmp_path: Path) -> None:
    ok = tmp_path / "meminfo"
    ok.write_text("MemTotal: 1 kB\nMemAvailable:   2048 kB\n", encoding="utf-8")
    assert g.lee_mem_available_kb(ok) == 2048
    sin = tmp_path / "otro"
    sin.write_text("MemTotal: 1 kB\n", encoding="utf-8")
    assert g.lee_mem_available_kb(sin) is None
    assert g.lee_mem_available_kb(tmp_path / "no_existe") is None


def test_main_cabe_si_y_no(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    monkeypatch.setattr(g, "lee_mem_available_kb", lambda: 78 * 1048576)
    assert g.main(["--cabe", "20", "--json"]) == 0
    assert json.loads(capsys.readouterr().out)["cabe"] is True
    assert g.main(["--cabe", "90"]) == 1
    assert capsys.readouterr().out.startswith("NO CABE")
    assert g.main(["--cabe", "1"]) == 0
    assert capsys.readouterr().out.startswith("CABE")


def test_main_informe_texto(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    monkeypatch.setattr(g, "nombres_docker", lambda: {ID: "vllm"})
    assert g.main(["--raiz", str(_arbol(tmp_path))]) == 0
    out = capsys.readouterr().out
    assert "contenedor vllm" in out and "user.slice" in out and "sin atribuir" in out


def test_main_informe_json_y_sin_region(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    monkeypatch.setattr(g, "nombres_docker", lambda: {})
    ok = tmp_path / "ok"
    ok.mkdir()
    assert g.main(["--raiz", str(_arbol(ok)), "--json"]) == 0
    assert json.loads(capsys.readouterr().out)["estado"] == "OK"
    vacio = tmp_path / "vacio"
    vacio.mkdir()
    assert g.main(["--raiz", str(vacio)]) == 3  # control negativo: sin region sale 3
    assert capsys.readouterr().out.startswith("SIN_REGION:")
    assert g.main(["--raiz", str(vacio), "--json"]) == 3
