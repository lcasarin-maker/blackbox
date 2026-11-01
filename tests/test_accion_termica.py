"""Acciones termicas: congelar lo que el consumidor declara, y solo eso. Cada rama con su caso negativo."""

import hashlib
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from tools import accion_termica as at

DORADO = Path(__file__).parent / "fixtures" / "contrato" / "carga_pausable_1.json"
SHA_DORADO = "cfe17cc51f264dce26d5fda25ea7357dd5d42e3ca6f220815aa191105a462993"


def _al_dia(**kw):
    return {"esquema": at.ESQUEMA, "actualizado": datetime.now(timezone.utc).isoformat(), "latido_s": 600, **kw}


def carga(tmp_path, unidades):
    r = tmp_path / "carga.json"
    r.write_text(json.dumps(_al_dia(unidades=unidades)), encoding="utf-8")
    return r


class Sistema:
    """Doble de systemctl: registra las llamadas."""

    def __init__(self, activas=("job.scope",), rc_freeze=0):
        self.llamadas, self.activas, self.rc_freeze = [], set(activas), rc_freeze

    def __call__(self, args):
        self.llamadas.append(tuple(args))
        if args[0] == "is-active":
            return (0 if args[1] in self.activas else 3), ""
        if args[0] == "freeze":
            return self.rc_freeze, ""
        return 0, ""


def corre(etiqueta, tmp_path, sis, unidades=None):
    c = carga(tmp_path, unidades if unidades is not None else [{"unidad": "job.scope", "pausable": True}])
    return at.aplica(etiqueta, carga=c, congeladas=tmp_path / "c.json", log=tmp_path / "l.jsonl", ejecutar=sis)


def test_sostenida_congela_la_unidad_pausable_declarada(tmp_path):
    s = Sistema()
    ev = corre("sostenida", tmp_path, s)
    assert ("freeze", "job.scope") in s.llamadas and ev[0]["accion"] == "freeze"
    assert json.loads((tmp_path / "c.json").read_text(encoding="utf-8")) == ["job.scope"]
    assert (tmp_path / "l.jsonl").read_text(encoding="utf-8").count("\n") == 1


def test_control_negativo_normal_y_desconocido_no_congelan(tmp_path):
    for et in ("normal", "desconocido"):
        s = Sistema()
        corre(et, tmp_path, s)
        assert not any(c[0] == "freeze" for c in s.llamadas), et


def test_normal_descongela_lo_que_este_modulo_congelo(tmp_path):
    s = Sistema()
    corre("sobre_100", tmp_path, s)
    corre("normal", tmp_path, s)
    assert ("thaw", "job.scope") in s.llamadas
    assert json.loads((tmp_path / "c.json").read_text(encoding="utf-8")) == []


def test_no_descongela_unidades_que_otro_congelo(tmp_path):
    s = Sistema()
    corre("normal", tmp_path, s)
    assert not any(c[0] == "thaw" for c in s.llamadas)


def test_sin_declaracion_no_actua_y_lo_dice(tmp_path):
    s = Sistema()
    ev = at.aplica("sostenida", carga=tmp_path / "no_existe.json", congeladas=tmp_path / "c.json",
                   log=tmp_path / "l.jsonl", ejecutar=s)
    assert ev[0]["accion"] == "ninguna" and "no declaro" in ev[0]["motivo"] and s.llamadas == []


def test_unidad_no_pausable_o_con_nombre_peligroso_se_descarta(tmp_path):
    s = Sistema()
    ev = corre("sostenida", tmp_path, s, [{"unidad": "job.scope", "pausable": False},
                                          {"unidad": "x; rm -rf /.scope", "pausable": True},
                                          {"unidad": "docker.service", "pausable": True}])
    assert ev[0]["accion"] == "ninguna" and s.llamadas == []


def test_unidad_inactiva_no_se_congela_y_un_freeze_fallido_no_queda_registrado(tmp_path):
    s = Sistema(activas=())
    ev = corre("sostenida", tmp_path, s)
    assert ev[0]["accion"] == "no_actua" and not any(c[0] == "freeze" for c in s.llamadas)
    s2 = Sistema(rc_freeze=1)
    corre("sostenida", tmp_path, s2)
    assert json.loads((tmp_path / "c.json").read_text(encoding="utf-8")) == []


def test_repetir_sostenida_no_congela_dos_veces(tmp_path):
    s = Sistema()
    corre("sostenida", tmp_path, s)
    corre("sostenida", tmp_path, s)
    assert [c for c in s.llamadas if c[0] == "freeze"] == [("freeze", "job.scope")]


# --- contrato neutro, legado y latido (boleta #18 A, 2026-11-01) ------------------------------------------


def test_el_dorado_es_el_mismo_que_fija_el_productor():
    """El mismo sha256 se fija en el test del productor, en su repo: el fixture se copia, no se importa."""
    assert hashlib.sha256(DORADO.read_bytes()).hexdigest() == SHA_DORADO


def test_el_dorado_se_lee_y_su_latido_se_juzga_contra_su_propio_sello():
    d = json.loads(DORADO.read_text(encoding="utf-8"))
    unidades, motivo, latido, doc = at.lee_declaracion(DORADO, ahora=datetime.fromisoformat(d["actualizado"]))
    assert (unidades, motivo, latido) == (["cola_job.scope"], "", "") and doc["esquema"] == at.ESQUEMA
    tarde = datetime.fromisoformat(d["actualizado"]) + timedelta(seconds=d["latido_s"] + 1)
    assert at.lee_declaracion(DORADO, ahora=tarde)[2].startswith("latido viejo")


def _datos(tmp_path, monkeypatch, neutro=None, legado=None):
    monkeypatch.setattr(at, "CARGA", tmp_path / "carga_pausable.json")
    monkeypatch.setattr(at, "CARGA_LEGADO", tmp_path / at.LEGADO_ARCHIVO)
    if neutro is not None:
        at.CARGA.write_text(neutro if isinstance(neutro, str) else json.dumps(neutro), encoding="utf-8")
    if legado is not None:
        at.CARGA_LEGADO.write_text(json.dumps(legado), encoding="utf-8")


def test_sin_ruta_prefiere_el_neutro_al_legado(tmp_path, monkeypatch):
    _datos(tmp_path, monkeypatch, neutro=_al_dia(unidades=[{"unidad": "nuevo.scope", "pausable": True}]),
           legado={"esquema": at.LEGADO_ESQUEMA, "unidades": [{"unidad": "viejo.scope", "pausable": True}]})
    assert at.lee_declaracion()[:3] == (["nuevo.scope"], "", "")


def test_solo_el_legado_se_sigue_leyendo_y_se_anota_que_no_late(tmp_path, monkeypatch):
    _datos(tmp_path, monkeypatch,
           legado={"esquema": at.LEGADO_ESQUEMA, "unidades": [{"unidad": "job.scope", "pausable": True}]})
    unidades, motivo, latido, _ = at.lee_declaracion()
    assert unidades == ["job.scope"] and motivo == ""
    assert "ausente o ilegible" in latido and "sin latido declarado" in latido  # por que no se uso el neutro


def test_un_neutro_roto_cae_al_legado_y_dice_por_que(tmp_path, monkeypatch):
    _datos(tmp_path, monkeypatch, neutro="{roto",
           legado={"esquema": at.LEGADO_ESQUEMA, "unidades": [{"unidad": "job.scope", "pausable": True}]})
    unidades, _m, latido, _ = at.lee_declaracion()
    assert unidades == ["job.scope"] and "carga_pausable.json ausente o ilegible" in latido


def test_control_negativo_sin_ninguno_de_los_dos_no_actua(tmp_path, monkeypatch):
    _datos(tmp_path, monkeypatch)
    unidades, motivo, _l, _ = at.lee_declaracion()
    assert unidades == [] and motivo.count("ausente o ilegible") == 2


def test_latido_viejo_congela_igual_y_lo_anota(tmp_path):
    """Falla abierto: el reloj viejo no quita la defensa termica; queda escrito en el evento."""
    r = tmp_path / "carga.json"
    viejo = (datetime.now(timezone.utc) - timedelta(seconds=700)).isoformat()
    r.write_text(json.dumps(_al_dia(actualizado=viejo, unidades=[{"unidad": "job.scope", "pausable": True}])),
                 encoding="utf-8")
    s = Sistema()
    ev = at.aplica("sostenida", carga=r, congeladas=tmp_path / "c.json", log=tmp_path / "l.jsonl", ejecutar=s)
    assert ("freeze", "job.scope") in s.llamadas and ev[0]["latido"].startswith("latido viejo")
    assert "latido viejo" in (tmp_path / "l.jsonl").read_text(encoding="utf-8")


def test_control_negativo_latido_al_dia_no_anota_nada(tmp_path):
    ev = corre("sostenida", tmp_path, Sistema())
    assert ev[0]["accion"] == "freeze" and "latido" not in ev[0]


def test_latido_ilegible_se_nombra_sin_inventar_una_edad():
    base = _al_dia(unidades=[])
    assert at.estado_latido({**base, "latido_s": "600"}).startswith("latido_s ilegible")
    assert at.estado_latido({**base, "latido_s": True}).startswith("latido_s ilegible")
    assert at.estado_latido({**base, "actualizado": "ayer"}).startswith("actualizado ilegible")
    assert at.estado_latido({**base, "actualizado": "2026-11-01T10:00:00"}).startswith("actualizado sin zona")
    assert at.estado_latido(base) == ""
