"""Admision de todo o nada con la holgura real (FEATURE-ADMISION-TODO-O-NADA-CON-HOLGURA-REAL-01).

Las fixtures salen de filas reales: `portero.jsonl(.1)` da lo que midio la puerta actual al admitir y
`samples/*.jsonl` da el `anon_kb` de app.slice de la muestra mas cercana. Medicion completa y su limite en
tasks/evidence/FEATURE-ADMISION-TODO-O-NADA-CON-HOLGURA-REAL-01/medicion.txt.

Limite que estas pruebas NO esconden: la serie del 2026-10-16 no trae anon ni shmem de app.slice (el campo `reclaim`
empieza el 2026-10-17 20:36). La ventana del 16-oct se reproduce con lo que si se midio y la prueba fija que, sin esa
medicion, la puerta nueva no inventa una negativa. La ventana con anon medido en la que la puerta actual admitio una
suite y app.slice colapso dos minutos despues es la del 2026-10-21 16:36:27.
"""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import pytest

from tools import interruptores
from tools import portero as po

APP = "/user.slice/user-1000.slice/user@1000.service/app.slice"
TOPE = 44040192  # memory.max de app.slice (45097156608 B) registrado por el portero el 16, el 18 y el 21-oct
SUITE_KB = po.CLASES["suite"].memory_max_kb  # 20971520: lo necesario para la clase suite

# 2026-10-16T16:35:28Z (10:35:28 -06:00), portero.jsonl: `descongelar` raiz 91364, la suite congelada a las 10:34:57.
# anon/shmem de app.slice: NOT_COLLECTED (la serie de ese dia no lo trae).
ESTADO_16 = po.Estado(0.55, "", TOPE, 39844424, (), 3519136)
ARBOL_16 = po.Arbol(raiz=91364, clase="suite", rss_kb=5138296, procesos=3, edad_s=64.0,
                    cgroup=APP + "/bb-portero-suite-91364.scope", unidad="bb-portero-suite-91364.scope", congelado=True)

# 2026-10-21T22:36:27Z (16:36:27 -06:00), portero.jsonl.1: `admitir` raiz 41108; app.slice en colapso a las 16:38:03.
# anon de app.slice en la muestra de 16:36:03 (samples/2026-10-21.jsonl): 27267340 kB. Sin shmem en la serie: anon
# es cota inferior de anon+shmem, asi que el disponible real era igual o menor que el de la fixture.
ESTADO_21 = po.Estado(0.97, "", TOPE, 35743284, (), 4965588)
ANON_21 = 27267340
ARBOL_21 = po.Arbol(raiz=41108, clase="suite", rss_kb=5208976, procesos=14, edad_s=187.3,
                    cgroup=APP + "/app-com.anthropic.Claude-116895.scope")

# 2026-10-18T03:17:24Z (2026-10-17 21:17:24 -06:00), portero.jsonl.1: `admitir` raiz 2264921, sin colapso en los 10 min
# siguientes. anon de app.slice en la muestra de 21:17:00: 15860264 kB.
ESTADO_SANO = po.Estado(0.0, "", TOPE, 24433084, (), 3585704)
ANON_SANO = 15860264
ARBOL_SANO = po.Arbol(raiz=2264921, clase="suite", rss_kb=5148132, procesos=5, edad_s=207.4,
                      cgroup=APP + "/app-com.anthropic.Claude-69880.scope")


def con_admision(e: po.Estado, modo: str, no_recuperable: int | None) -> po.Estado:
    return replace(e, admision=modo, no_recuperable_app_kb=no_recuperable)


def tipos(acciones: list[po.Accion]) -> list[tuple[int | None, str]]:
    return [(a.raiz, a.tipo) for a in acciones]


def filas(log: Path) -> list[dict]:
    return [json.loads(x) for x in log.read_text(encoding="utf-8").splitlines()] if log.exists() else []


def efectos(tmp: Path, modo: str = "actuar") -> po.Efectos:
    def prohibido(args: list[str]) -> tuple[int, str]:
        raise AssertionError(f"no debe ejecutar nada: {args}")

    return po.Efectos(log=tmp / "portero.jsonl", cola=tmp / "cola", ejecutar=prohibido, cg_raiz=tmp / "cg",
                      proc=tmp / "proc", modo=modo)


# --- (a) la ventana real: la puerta nueva niega lo que la actual dejo pasar -----------------------------------------


@pytest.mark.unit
def test_a_ventana_21_oct_la_puerta_nueva_niega_la_suite_que_la_actual_admitio():
    acc = po.decide([ARBOL_21], con_admision(ESTADO_21, "actuar", ANON_21))
    assert tipos(acc) == [(41108, "congelar")]
    disponible = TOPE - ANON_21
    assert disponible == 16772852 and disponible < SUITE_KB
    # Como Athena: la negativa dice lo necesario y lo disponible.
    assert f"necesita {SUITE_KB} kB" in acc[0].motivo and f"hay {disponible} kB" in acc[0].motivo


@pytest.mark.unit
def test_a_actuar_mantiene_congelada_la_suite_que_no_cabe():
    """La suite ya congelada por el portero sigue esperando mientras no quepa (no se descongela)."""
    congelada = replace(ARBOL_21, unidad="bb-portero-suite-41108.scope", congelado=True)
    acc = po.decide([congelada], con_admision(ESTADO_21, "actuar", ANON_21))
    assert tipos(acc) == [(41108, "esperar")] and acc[0].motivo.startswith("holgura real")


# --- (c) control negativo del control: con la puerta actual, el mismo caso pasa ------------------------------------


@pytest.mark.unit
@pytest.mark.parametrize("modo", ["off", "observar"])
def test_c_con_la_puerta_actual_la_ventana_21_oct_admite_la_suite(modo):
    """Lo mismo que registro el portero real a las 16:36:27: `admitir`. En `observar` decide igual que en `off`."""
    acc = po.decide([ARBOL_21], con_admision(ESTADO_21, modo, ANON_21))
    assert tipos(acc) == [(41108, "admitir")] and acc[0].motivo == "turno libre y puerta abierta"
    assert po.decide([ARBOL_21], ESTADO_21) == acc  # y sin los campos nuevos, identico


@pytest.mark.unit
def test_c_la_ventana_16_oct_reproduce_lo_que_hizo_la_puerta_actual():
    """Con lo medido el 16-oct la puerta actual descongela la suite 91364, como dice portero.jsonl de 10:35:28."""
    acc = po.decide([ARBOL_16], ESTADO_16)
    assert tipos(acc) == [(91364, "descongelar")]
    assert ESTADO_16.holgura_app_kb == 4195768 and ESTADO_16.holgura_app_kb - po.HOLGURA_MIN_KB == 1464  # paso por 1464 kB


# --- (b) control negativo: una ventana sana que la puerta nueva admite -----------------------------------------------


@pytest.mark.unit
def test_b_ventana_sana_la_puerta_nueva_admite(tmp_path):
    estado = con_admision(ESTADO_SANO, "actuar", ANON_SANO)
    assert TOPE - ANON_SANO == 28179928 >= SUITE_KB
    assert tipos(po.decide([ARBOL_SANO], estado)) == [(2264921, "admitir")]
    # y en observar no deja fila `habria_negado`
    fx = efectos(tmp_path)
    po.aplica(po.decide([ARBOL_SANO], replace(estado, admision="observar")), [], replace(estado, admision="observar"), fx, {})
    assert [f["accion"] for f in filas(fx.log)] == ["admitir"]


# --- la ventana del 16-oct sin anon medido: la puerta nueva no inventa ---------------------------------------------


@pytest.mark.unit
def test_ventana_16_oct_sin_anon_medido_actuar_no_niega_y_observar_lo_declara(tmp_path):
    assert tipos(po.decide([ARBOL_16], con_admision(ESTADO_16, "actuar", None))) == [(91364, "descongelar")]
    estado = con_admision(ESTADO_16, "observar", None)
    fx = efectos(tmp_path)
    po.aplica(po.decide([ARBOL_16], estado), [], estado, fx, {})
    neg = [f for f in filas(fx.log) if f["accion"] == "habria_negado"]
    assert len(neg) == 1 and neg[0]["motivo"].startswith("NOT_COLLECTED") and "disponible_kb" not in neg[0]


@pytest.mark.unit
@pytest.mark.parametrize(("no_recuperable", "esperado"), [
    (37269116, "esperar"),  # anon+shmem medido en el atasco confinado de 13:46 del mismo dia (atasco_confinado.jsonl)
    (int(16.7 * po.GIB_KB), "descongelar"),  # "hoy: anon 16.7 GiB" de la ficha DEBT-COLAPSO, tarde del mismo dia
])
def test_ventana_16_oct_el_veredicto_depende_de_un_numero_que_no_se_midio(no_recuperable, esperado):
    """Las dos mediciones de composicion del 16-oct dan veredictos opuestos: por eso no se reclama el de las 10:35."""
    assert tipos(po.decide([ARBOL_16], con_admision(ESTADO_16, "actuar", no_recuperable))) == [(91364, esperado)]


# --- interruptor: off no cambia un byte, observar registra ambos numeros ------------------------------------------


@pytest.mark.unit
def test_off_no_cambia_ni_decide_ni_las_filas(tmp_path):
    antes, despues = tmp_path / "antes", tmp_path / "off"
    for d, estado in ((antes, ESTADO_21), (despues, con_admision(ESTADO_21, "off", ANON_21))):
        po.aplica(po.decide([ARBOL_21], estado), [], estado, efectos(d), {})
    sin_ts = [[{k: v for k, v in f.items() if k != "ts"} for f in filas(d / "portero.jsonl")] for d in (antes, despues)]
    assert sin_ts[0] == sin_ts[1] and len(sin_ts[0]) == 1
    assert "admision" not in sin_ts[1][0]["medicion"]


@pytest.mark.unit
def test_observar_registra_habria_negado_con_lo_necesario_y_lo_disponible_una_vez(tmp_path):
    fx = efectos(tmp_path)
    ultimo: dict = {}
    for anon in (ANON_21, ANON_21 + 1000):  # dos vueltas: los kB cambian, la negativa es la misma
        estado = con_admision(ESTADO_21, "observar", anon)
        acc = po.decide([ARBOL_21], estado)
        assert tipos(acc) == [(41108, "admitir")]  # observar no cambia la decision
        po.aplica(acc, [], estado, fx, ultimo)
    neg = [f for f in filas(fx.log) if f["accion"] == "habria_negado"]
    assert len(neg) == 1
    assert (neg[0]["modo"], neg[0]["interruptor"], neg[0]["raiz"]) == ("observar", "portero_admision", 41108)
    assert (neg[0]["necesario_kb"], neg[0]["disponible_kb"]) == (SUITE_KB, 16772852)
    assert neg[0]["medicion"]["no_recuperable_app_kb"] == ANON_21 and neg[0]["medicion"]["admision"] == "observar"


@pytest.mark.unit
def test_turno_en_observar_registra_habria_negado_y_concede(tmp_path):
    estado = con_admision(ESTADO_21, "observar", ANON_21)
    peticion = po.Arbol(raiz=4242, clase="suite", rss_kb=0, procesos=0, edad_s=1.0, cgroup="", virtual=True)
    fx = efectos(tmp_path)
    mia = po.turno(4242, "suite", fuente=lambda: (estado, [peticion]), espera=lambda: pytest.fail("no espera"), fx=fx)
    assert mia.tipo == "admitir"
    neg = [f for f in filas(fx.log) if f["accion"] == "habria_negado"]
    assert len(neg) == 1 and neg[0]["disponible_kb"] == 16772852


@pytest.mark.unit
@pytest.mark.parametrize("contenido", [None, "{no es json", json.dumps({"modos": {"portero_admision": "a_medias"}}),
                                       json.dumps({"modos": {"portero": "actuar"}})])
def test_interruptor_ausente_ilegible_o_desconocido_vale_off(tmp_path, contenido):
    ruta = tmp_path / "interruptores.json"
    if contenido is not None:
        ruta.write_text(contenido, encoding="utf-8")
    assert interruptores.modo(po.NOMBRE_ADMISION, ruta) == "off"


@pytest.mark.unit
def test_control_interruptor_legible_si_cambia_de_modo(tmp_path):
    ruta = tmp_path / "interruptores.json"
    ruta.write_text(json.dumps({"modos": {"portero_admision": "observar"}}), encoding="utf-8")
    assert interruptores.modo(po.NOMBRE_ADMISION, ruta) == "observar"


def _app_slice(tmp: Path, stat: str) -> Path:
    d = tmp / "app.slice"
    d.mkdir(parents=True)
    (d / "memory.max").write_text(f"{TOPE * 1024}\n", encoding="utf-8")
    (d / "memory.current").write_text(f"{35743284 * 1024}\n", encoding="utf-8")
    (d / "memory.stat").write_text(stat, encoding="utf-8")
    return d


@pytest.mark.unit
def test_lee_no_recuperable_suma_anon_y_shmem_y_sin_uno_es_none(tmp_path):
    d = _app_slice(tmp_path / "ok", f"anon {ANON_21 * 1024}\nfile 1\nshmem {1000 * 1024}\ninactive_file 0\n")
    assert po.lee_no_recuperable_kb(d) == ANON_21 + 1000
    sin_shmem = _app_slice(tmp_path / "mal", f"anon {ANON_21 * 1024}\nfile 1\n")
    assert po.lee_no_recuperable_kb(sin_shmem) is None


@pytest.mark.unit
@pytest.mark.parametrize(("modo", "esperado"), [("off", None), ("observar", ANON_21 + 1000), ("actuar", ANON_21 + 1000)])
def test_lee_estado_solo_mide_anon_shmem_fuera_de_off(tmp_path, monkeypatch, modo, esperado):
    datos = tmp_path / "datos"
    datos.mkdir()
    if modo != "off":
        (datos / "interruptores.json").write_text(json.dumps({"modos": {"portero_admision": modo}}), encoding="utf-8")
    monkeypatch.setenv("BLACKBOX_DATA", str(datos))
    d = _app_slice(tmp_path, f"anon {ANON_21 * 1024}\nshmem {1000 * 1024}\n")
    monkeypatch.setattr(po, "cgroup_app", lambda uid=None, raiz=po.CGROUP_RAIZ: d)
    e = po.lee_estado()
    assert (e.admision, e.no_recuperable_app_kb, e.tope_app_kb) == (modo, esperado, TOPE)
