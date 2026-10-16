"""Atasco de memoria confinado a una slice (DEBT-COLAPSO-CONFINADO-A-APP-SLICE-REINICIA-LA-MAQUINA-ENTERA-01).

Lo que se prueba, con su control negativo cada vez: la clasificacion pura, el interruptor `atasco_confinado`
(off / observar / actuar), el diagnostico que se captura, y el lazo real de `bb-usable` -- en `off` y en `observar`
el watchdog se retiene EXACTAMENTE como antes del cambio, y solo `actuar` con atasco confinado acaricia, y solo
hasta el tope duro."""

from __future__ import annotations

import importlib.machinery as machinery
import importlib.util as util
import json
from pathlib import Path
from typing import Any

import pytest

RUTA = Path(__file__).resolve().parent.parent / "bin" / "bb-usable"


def _cargar():
    loader = machinery.SourceFileLoader("bb_usable_confinado", str(RUTA))
    spec = util.spec_from_loader("bb_usable_confinado", loader)
    assert spec is not None
    mod = util.module_from_spec(spec)
    loader.exec_module(mod)
    return mod


def presion(full: float) -> str:
    return f"some avg10={full:.2f} avg60=0.00 avg300=0.00 total=0\nfull avg10={full:.2f} avg60=0.00 avg300=0.00 total=0\n"


def arbol(tmp_path: Path, app: float | None = 50.0, docker: float | None = 0.0, system: float | None = 0.0) -> tuple[Path, Path]:
    """CGROUP_ROOT y PROC_ROOT falsos. Una presion None no escribe el archivo (lectura imposible)."""
    cg, proc = tmp_path / "cg", tmp_path / "proc"
    a = cg / "user.slice" / "user-1000.slice" / "user@1000.service" / "app.slice"
    for d in (a, cg / "docker.slice", cg / "system.slice", proc / "pressure"):
        d.mkdir(parents=True, exist_ok=True)
    for d, v in ((a, app), (cg / "docker.slice", docker), (cg / "system.slice", system)):
        if v is not None:
            (d / "memory.pressure").write_text(presion(v), encoding="ascii")
    (a / "memory.stat").write_text("anon 1000\nfile 2000\nshmem 30\npgscan 400\npgsteal 300\nworkingset_refault_file 7\n"
                                   "workingset_refault_anon 5\n", encoding="ascii")
    (proc / "meminfo").write_text("SwapTotal:       16777212 kB\nSwapFree:        12582912 kB\n", encoding="ascii")
    (proc / "pressure" / "io").write_text(presion(37.0), encoding="ascii")
    (proc / "pressure" / "cpu").write_text("some avg10=61.00 avg60=0.00 avg300=0.00 total=0\n", encoding="ascii")
    return cg, proc


@pytest.fixture
def bbu(tmp_path, monkeypatch):
    mod = _cargar()
    monkeypatch.setenv("BLACKBOX_DATA", str(tmp_path / "datos"))
    cg, proc = arbol(tmp_path)
    monkeypatch.setattr(mod, "CGROUP_ROOT", cg)
    monkeypatch.setattr(mod, "PROC_ROOT", proc)
    return mod


def fija_modo(tmp_path: Path, modo: str | None) -> None:
    datos = tmp_path / "datos"
    datos.mkdir(parents=True, exist_ok=True)
    ruta = datos / "interruptores.json"
    if modo is None:
        ruta.unlink(missing_ok=True)
    else:
        ruta.write_text(json.dumps({"modos": {"atasco_confinado": modo}}), encoding="utf-8")


def filas(tmp_path: Path) -> list[dict[str, Any]]:
    ruta = tmp_path / "datos" / "interruptores" / "atasco_confinado.jsonl"
    return [json.loads(x) for x in ruta.read_text(encoding="utf-8").splitlines()] if ruta.exists() else []


# --------------------------------------------------------------- clasificacion pura


def test_confinado_solo_si_app_pasa_el_corte_y_las_otras_slices_estan_quietas(bbu):
    assert bbu.clasifica_atasco({"app": 50.0, "docker": 0.0, "system": 0.0}) == "confinado"
    assert bbu.clasifica_atasco({"app": 50.0, "docker": 1.0, "system": 1.0}) == "confinado"  # en el borde: cuenta quieto
    assert bbu.clasifica_atasco({"app": 50.0, "docker": 5.0, "system": 0.0}) == "general"    # el motor tambien sufre
    assert bbu.clasifica_atasco({"app": 50.0, "docker": 0.0, "system": 2.0}) == "general"
    assert bbu.clasifica_atasco({"app": 5.0, "docker": 0.0, "system": 0.0}) == "general"     # app tampoco pasa el corte
    for falta in ("app", "docker", "system"):
        p: dict[str, float | None] = {"app": 50.0, "docker": 0.0, "system": 0.0}
        p[falta] = None
        assert bbu.clasifica_atasco(p) == "sin_dato", falta  # sin lectura no se afirma que este confinado


def test_decide_cada_modo_y_el_tope_duro(bbu):
    d = bbu.decide_confinado
    assert d("off", "confinado", 1) == "retiene"
    assert d("observar", "confinado", 1) == "habria_acariciado"
    assert d("actuar", "confinado", 1) == "acaricia"
    assert d("actuar", "confinado", bbu.CONFINADO_MAX_SONDAS) == "acaricia"
    assert d("actuar", "confinado", bbu.CONFINADO_MAX_SONDAS + 1) == "retiene"  # pasado el tope duro: reinicia
    for clase in ("general", "sin_dato"):
        assert d("actuar", clase, 1) == "retiene", clase


def test_el_tope_duro_sale_del_intervalo_de_sondas(bbu):
    assert bbu.CONFINADO_MAX_SONDAS == round(bbu.CONFINADO_MAX_S / bbu.PROBE_INTERVAL) == 40


# --------------------------------------------------------------- lecturas


def test_presiones_lee_las_tres_slices_y_none_donde_no_hay_archivo(bbu, tmp_path, monkeypatch):
    assert bbu.presiones_slices() == {"app": 50.0, "docker": 0.0, "system": 0.0}
    cg, _ = arbol(tmp_path / "otra", app=None, docker=None, system=12.5)
    monkeypatch.setattr(bbu, "CGROUP_ROOT", cg)
    assert bbu.presiones_slices() == {"app": None, "docker": None, "system": 12.5}
    monkeypatch.setattr(bbu, "CGROUP_ROOT", tmp_path / "no-existe")
    assert bbu.presiones_slices() == {"app": None, "docker": None, "system": None}


def test_una_presion_sin_linea_full_o_ilegible_es_none(bbu, tmp_path):
    f = tmp_path / "memory.pressure"
    f.write_text("some avg10=1.00 avg60=0.00 avg300=0.00 total=0\n", encoding="ascii")
    assert bbu._full_avg10_de(tmp_path) is None
    f.write_text("full avg10=basura avg60=0.00 avg300=0.00 total=0\n", encoding="ascii")
    assert bbu._full_avg10_de(tmp_path) is None
    f.write_text("full avg60=0.00\n", encoding="ascii")
    assert bbu._full_avg10_de(tmp_path) is None


@pytest.mark.parametrize("contenido,esperado", [
    (None, "off"), ("no es json", "off"), ('{"modos": {}}', "off"), ('{"modos": {"atasco_confinado": "inventado"}}', "off"),
    ('{"modos": {"atasco_confinado": "observar"}}', "observar"), ('{"modos": {"atasco_confinado": "actuar"}}', "actuar"),
    ('{"modos": {"atasco_confinado": "off"}}', "off"), ('[1]', "off")])
def test_el_modo_ilegible_o_desconocido_vale_off(bbu, tmp_path, contenido, esperado):
    ruta = tmp_path / "datos" / "interruptores.json"
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.unlink(missing_ok=True)
    if contenido is not None:
        ruta.write_text(contenido, encoding="utf-8")
    assert bbu.modo_confinado() == esperado


def test_diagnostico_trae_stat_swap_y_presion_de_io_y_cpu(bbu):
    d = bbu.diagnostico_atasco()
    assert d["anon"] == 1000 and d["file"] == 2000 and d["pgsteal"] == 300 and d["workingset_refault_anon"] == 5
    assert d["swap_usado_kb"] == 16777212 - 12582912
    assert d["io_some_avg10"] == 37.0 and d["cpu_some_avg10"] == 61.0


def test_diagnostico_declara_none_donde_no_puede_leer(bbu, monkeypatch, tmp_path):
    monkeypatch.setattr(bbu, "CGROUP_ROOT", tmp_path / "vacio")
    monkeypatch.setattr(bbu, "PROC_ROOT", tmp_path / "vacio")
    d = bbu.diagnostico_atasco()
    assert d["memory_stat"] is None and d["swap_usado_kb"] is None
    assert d["io_some_avg10"] is None and d["cpu_some_avg10"] is None


# --------------------------------------------------------------- paso_confinado


def test_en_off_no_lee_ni_escribe_nada(bbu, tmp_path, monkeypatch):
    fija_modo(tmp_path, "off")
    monkeypatch.setattr(bbu, "presiones_slices", lambda: pytest.fail("en off no se leen las slices"))
    assert bbu.paso_confinado(7) == ("retiene", 0)
    assert filas(tmp_path) == []


def test_en_actuar_con_atasco_confinado_acaricia_cuenta_y_registra(bbu, tmp_path):
    fija_modo(tmp_path, "actuar")
    accion, n = bbu.paso_confinado(0)
    assert (accion, n) == ("acaricia", 1)
    fila = filas(tmp_path)[0]
    assert fila["clase"] == "confinado" and fila["accion"] == "acaricia" and fila["sondas_confinadas"] == 1
    assert fila["diagnostico"]["anon"] == 1000  # la primera sonda confinada captura el diagnostico
    bbu.paso_confinado(1)
    assert "diagnostico" not in filas(tmp_path)[1]  # las siguientes no, hasta CONFINADO_DIAG_CADA


def test_el_diagnostico_se_repite_cada_confinado_diag_cada_sondas(bbu, tmp_path):
    fija_modo(tmp_path, "observar")
    n = 0
    for _ in range(bbu.CONFINADO_DIAG_CADA + 1):
        _, n = bbu.paso_confinado(n)
    con = [i for i, f in enumerate(filas(tmp_path)) if "diagnostico" in f]
    assert con == [0, bbu.CONFINADO_DIAG_CADA]


def test_en_observar_registra_pero_no_acaricia(bbu, tmp_path):
    fija_modo(tmp_path, "observar")
    assert bbu.paso_confinado(0) == ("habria_acariciado", 1)
    assert filas(tmp_path)[0]["accion"] == "habria_acariciado"


def test_si_el_motor_tambien_sufre_retiene_y_el_contador_vuelve_a_cero(bbu, tmp_path, monkeypatch):
    fija_modo(tmp_path, "actuar")
    cg, _ = arbol(tmp_path / "otra", app=50.0, docker=20.0, system=0.0)
    monkeypatch.setattr(bbu, "CGROUP_ROOT", cg)
    assert bbu.paso_confinado(5) == ("retiene", 0)
    assert filas(tmp_path)[0]["clase"] == "general"


def test_un_fallo_interno_cae_al_comportamiento_de_siempre(bbu, tmp_path, monkeypatch, capsys):
    fija_modo(tmp_path, "actuar")

    def roto():
        raise RuntimeError("boom")

    monkeypatch.setattr(bbu, "presiones_slices", roto)
    assert bbu.paso_confinado(3) == ("retiene", 0)
    assert "se retiene como siempre" in capsys.readouterr().err


# --------------------------------------------------------------- el lazo real


def correr(bbu, monkeypatch, serie: list[float]) -> tuple[int, str]:
    """Como `_correr` de test_bb_usable.py: devuelve (caricias sin la de arranque, salida)."""
    caricias: list[str] = []
    lineas: list[str] = []
    monkeypatch.setattr(bbu, "notify", lambda s: caricias.append(s))
    monkeypatch.setattr(bbu, "probe", lambda: 0.001)
    monkeypatch.setattr(bbu.time, "sleep", lambda s: None)
    it = iter(serie)

    def leer():
        try:
            return next(it)
        except StopIteration:
            raise SystemExit from None

    monkeypatch.setattr(bbu, "psi_memory_full_avg10", leer)
    monkeypatch.setattr(bbu.sys, "stderr", type("F", (), {"write": lambda _s, m: lineas.append(m), "flush": lambda _s: None})())
    with pytest.raises(SystemExit):
        bbu.main()
    return sum(1 for c in caricias if c == "WATCHDOG=1") - 1, "".join(lineas)


SONDAS_AL_CORTE = 9  # PSI_ACT_SONDAS - 1 caricias antes de declarar el COLAPSO


def test_por_defecto_el_comportamiento_no_cambio_off_y_sin_archivo(bbu, tmp_path, monkeypatch):
    fija_modo(tmp_path, None)
    caricias, salida = correr(bbu, monkeypatch, [99.0] * 15)
    assert caricias == SONDAS_AL_CORTE and "NO se acaricia el watchdog" in salida
    fija_modo(tmp_path, "off")
    caricias, _ = correr(bbu, monkeypatch, [99.0] * 15)
    assert caricias == SONDAS_AL_CORTE and filas(tmp_path) == []


def test_en_observar_sigue_reteniendo_exactamente_igual_y_deja_registro(bbu, tmp_path, monkeypatch):
    fija_modo(tmp_path, "observar")
    caricias, salida = correr(bbu, monkeypatch, [99.0] * 15)
    assert caricias == SONDAS_AL_CORTE
    assert "habria acariciado el watchdog" in salida and "NO se acaricia el watchdog" in salida
    assert {f["accion"] for f in filas(tmp_path)} == {"habria_acariciado"} and len(filas(tmp_path)) == 6


def test_en_actuar_con_atasco_confinado_acaricia_pasado_el_corte(bbu, tmp_path, monkeypatch):
    fija_modo(tmp_path, "actuar")
    caricias, salida = correr(bbu, monkeypatch, [99.0] * 15)
    assert caricias == 15, "las 9 de siempre mas las 6 sondas confinadas"
    assert "ATASCO CONFINADO a app.slice" in salida and "se acaricia el watchdog (6/40" in salida
    assert "NO se acaricia el watchdog" not in salida


def test_control_negativo_en_actuar_si_el_motor_tambien_sufre_reinicia_como_siempre(bbu, tmp_path, monkeypatch):
    fija_modo(tmp_path, "actuar")
    cg, _ = arbol(tmp_path / "otra", app=50.0, docker=30.0, system=0.0)
    monkeypatch.setattr(bbu, "CGROUP_ROOT", cg)
    caricias, salida = correr(bbu, monkeypatch, [99.0] * 15)
    assert caricias == SONDAS_AL_CORTE and "NO se acaricia el watchdog" in salida


def test_control_negativo_en_actuar_sin_lectura_de_slices_reinicia_como_siempre(bbu, tmp_path, monkeypatch):
    fija_modo(tmp_path, "actuar")
    monkeypatch.setattr(bbu, "CGROUP_ROOT", tmp_path / "no-existe")
    caricias, _ = correr(bbu, monkeypatch, [99.0] * 15)
    assert caricias == SONDAS_AL_CORTE


def test_el_tope_duro_corta_las_caricias_y_el_reinicio_vuelve(bbu, tmp_path, monkeypatch):
    fija_modo(tmp_path, "actuar")
    monkeypatch.setattr(bbu, "CONFINADO_MAX_SONDAS", 3)
    caricias, salida = correr(bbu, monkeypatch, [99.0] * 15)
    assert caricias == SONDAS_AL_CORTE + 3, "9 de siempre + 3 del tope duro, y despues se retiene"
    assert "NO se acaricia el watchdog" in salida


def test_tras_recuperarse_el_contador_del_tope_duro_vuelve_a_cero(bbu, tmp_path, monkeypatch):
    fija_modo(tmp_path, "actuar")
    monkeypatch.setattr(bbu, "CONFINADO_MAX_SONDAS", 3)
    serie = [99.0] * 12 + [0.0] * 2 + [99.0] * 12  # colapso, recuperacion de 2 bajas, segundo colapso
    caricias, _ = correr(bbu, monkeypatch, serie)
    # episodio 1: 9 + 3 exentas; de las 2 bajas solo la SEGUNDA acaricia (la primera no absuelve: la racha sigue
    # declarada, regla de siempre); episodio 2: 9 + 3 exentas -- el contador del tope duro se reinicio
    assert caricias == (SONDAS_AL_CORTE + 3) + 1 + (SONDAS_AL_CORTE + 3)
