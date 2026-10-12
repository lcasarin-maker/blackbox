"""Acciones termicas: congelar lo que Atlas declara, y solo eso. Cada rama con su caso negativo."""

import json

from tools import accion_termica as at


def carga(tmp_path, unidades):
    r = tmp_path / "carga.json"
    r.write_text(json.dumps({"esquema": "atlas-carga/1", "unidades": unidades}), encoding="utf-8")
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


def test_sin_declaracion_de_atlas_no_actua_y_lo_dice(tmp_path):
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
