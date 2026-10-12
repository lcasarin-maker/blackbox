import json

from tools import interruptores, vigilante_memavail as v

GIB = 1048576


def test_modo_por_defecto_off_y_ilegible(tmp_path):
    assert interruptores.modo("memavail", tmp_path / "no.json") == "off"
    (tmp_path / "x.json").write_text("{", encoding="utf-8")
    assert interruptores.modo("memavail", tmp_path / "x.json") == "off"
    (tmp_path / "y.json").write_text(json.dumps({"modos": {"memavail": "raro"}}), encoding="utf-8")
    assert interruptores.modo("memavail", tmp_path / "y.json") == "off"


def test_modo_observar_leido(tmp_path):
    (tmp_path / "i.json").write_text(json.dumps({"modos": {"memavail": "observar"}}), encoding="utf-8")
    assert interruptores.modo("memavail", tmp_path / "i.json") == "observar"


def test_decide_umbral_y_sin_dato():
    assert v.decide(7 * GIB, 0.0)["dispara"] is True
    assert v.decide(9 * GIB, 50.0)["dispara"] is False
    assert v.decide(None, 50.0)["motivo"].startswith("NOT_COLLECTED")


def test_off_no_registra(tmp_path):
    assert v.paso("off", 1 * GIB, 0.0, tmp_path) is None
    assert not list(tmp_path.iterdir())


def test_observar_registra_y_cuenta_falso_positivo(tmp_path):
    v.paso("observar", 2 * GIB, 0.0, tmp_path)   # falso positivo: PSI sano
    v.paso("observar", 2 * GIB, 40.0, tmp_path)  # acierto
    v.paso("observar", 20 * GIB, 40.0, tmp_path)  # no dispara
    assert interruptores.resumen("memavail", tmp_path) == {"disparos": 2, "confirmados": 1, "falsos_positivos": 1}


def test_actuar_declara_unsupported(tmp_path):
    ev = v.paso("actuar", 1 * GIB, 0.0, tmp_path)
    assert ev is not None and ev["accion"].startswith("UNSUPPORTED")


def test_lecturas_reales_o_none(tmp_path):
    assert v.lee_meminfo(tmp_path / "no") is None
    assert v.lee_psi_full(tmp_path / "no") is None
    (tmp_path / "p").write_text("some avg10=1.00 avg60=0 avg300=0 total=0\nfull avg10=12.50 avg60=0 avg300=0 total=0\n", encoding="utf-8")
    assert v.lee_psi_full(tmp_path / "p") == 12.5
