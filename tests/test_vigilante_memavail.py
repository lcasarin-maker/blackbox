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


LAB = v.Unidad("bb-lab-acaparador-1.scope", "/cg/lab", 900 * 1024 * 1024)
CHICO = v.Unidad("bb-lab-chico-2.scope", "/cg/chico", 10 * 1024 * 1024)
CLAUDE = v.Unidad("app-com.anthropic.Claude-1.scope", "/cg/claude", 40 * GIB * 1024)


class _Efectos:
    def __init__(self, unidades):
        self.lista, self.detenidas = unidades, []

    def ctx(self, linea_gib=v.LINEA_GIB):
        return v.Contexto(linea_gib, v.ELEGIBLES, lambda: self.lista, lambda cg: [{"cgroup": cg, "pid": 7}],
                          lambda n: (self.detenidas.append(n), {"rc": 0, "salida": ""})[1])


def test_actuar_detiene_solo_el_culpable_elegible_y_registra_su_origen(tmp_path):
    fx = _Efectos([CLAUDE, CHICO, LAB])
    ev = v.paso("actuar", 1 * GIB, 0.0, tmp_path, fx.ctx())
    assert fx.detenidas == ["bb-lab-acaparador-1.scope"]  # ni Claude (mayor, no elegible) ni el chico
    assert ev is not None and ev["accion"]["detenida"] == LAB.nombre and ev["origen"] == [{"cgroup": "/cg/lab", "pid": 7}]
    fila = json.loads((tmp_path / "memavail.jsonl").read_text(encoding="utf-8"))
    assert fila["culpable"]["unidad"]["nombre"] == LAB.nombre and fila["origen"][0]["pid"] == 7


def test_control_negativo_sobre_la_linea_no_actua(tmp_path):
    fx = _Efectos([LAB])
    assert v.paso("actuar", 20 * GIB, 90.0, tmp_path, fx.ctx(8.0)) is None
    assert fx.detenidas == [] and not list(tmp_path.iterdir())


def test_control_negativo_unidad_protegida_rechazada(tmp_path):
    vllm = v.Unidad("bb-lab-vllm-motor.scope", "/cg/vllm", 50 * GIB * 1024)
    fx = _Efectos([vllm, LAB])
    ev = v.paso("actuar", 1 * GIB, 0.0, tmp_path, fx.ctx())
    assert fx.detenidas == [] and ev is not None and ev["accion"].startswith("REFUSED")
    docker = v.Unidad("docker-abc.scope", "/cg/d", 1)
    assert v.elige_culpable([docker], elegibles=("*.scope",))["veredicto"] == "REFUSED"


def test_control_negativo_culpable_desconocido_no_mata(tmp_path):
    for lista in ([CLAUDE], [], None):
        fx = _Efectos(lista)
        ev = v.paso("actuar", 1 * GIB, 0.0, tmp_path, fx.ctx())
        assert fx.detenidas == [] and ev is not None and ev["accion"].startswith("NOT_COLLECTED")


def test_observar_nombra_lo_que_detendria_sin_detener(tmp_path):
    fx = _Efectos([LAB])
    ev = v.paso("observar", 1 * GIB, 0.0, tmp_path, fx.ctx())
    assert fx.detenidas == [] and ev is not None and "accion" not in ev
    assert ev["culpable"]["veredicto"] == "DETENER" and ev["origen"][0]["pid"] == 7


def test_lee_unidades_de_un_arbol_propio(tmp_path):
    assert v.lee_unidades(tmp_path / "no") is None
    s = tmp_path / "app.slice" / "bb-lab-x.scope"
    s.mkdir(parents=True)
    (s / "memory.current").write_text("4096\n", encoding="ascii")
    (tmp_path / "app.slice" / "roto.service").mkdir()  # sin memory.current: salio durante el barrido
    leidas = sorted(v.lee_unidades(tmp_path) or [])
    assert leidas == [v.Unidad("bb-lab-x.scope", str(s), 4096), v.Unidad("roto.service", str(tmp_path / "app.slice/roto.service"), None)]
    c = v.elige_culpable([v.Unidad("bb-lab-roto.scope", "/cg/r", None)])
    assert c["veredicto"] == "NOT_COLLECTED" and c["elegibles_ilegibles"] == ["bb-lab-roto.scope"]
    sin = v.origen_de(str(tmp_path / "no"))
    assert isinstance(sin, str) and sin.startswith("NOT_COLLECTED")


def test_lecturas_reales_o_none(tmp_path):
    assert v.lee_meminfo(tmp_path / "no") is None
    assert v.lee_psi_full(tmp_path / "no") is None
    (tmp_path / "p").write_text("some avg10=1.00 avg60=0 avg300=0 total=0\nfull avg10=12.50 avg60=0 avg300=0 total=0\n", encoding="utf-8")
    assert v.lee_psi_full(tmp_path / "p") == 12.5


def test_suite_del_portero_es_elegible_y_el_resto_de_bb_sigue_protegido(tmp_path):
    """Voto de Luis 2026-10-14: `actuar` alcanza las suites bajo el portero, nada mas de bb ni de la sesion."""
    suite = v.Unidad("bb-portero-suite-4242.scope", "/cg/suite", 9 * GIB * 1024)
    assert v.elige_culpable([suite, CLAUDE])["veredicto"] != "REFUSED"
    fx = _Efectos([suite, CLAUDE])
    ev = v.paso("actuar", 1 * GIB, 0.0, tmp_path, fx.ctx())
    assert ev is not None and fx.detenidas == ["bb-portero-suite-4242.scope"]
    # control negativo: otras unidades bb-* y la sesion de Claude, aunque casen con un patron amplio, no se detienen
    for nombre in ("bb-portero-contenedor-7.scope", "bb-usable.service", "bb-guardia-proceso.service",
                   "app-com.anthropic.Claude-1.scope"):
        u = v.Unidad(nombre, "/cg/x", 50 * GIB * 1024)
        assert v.elige_culpable([u], elegibles=("*",))["veredicto"] == "REFUSED", nombre
