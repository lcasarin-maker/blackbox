"""Arbitro de memoria por rango (FEATURE-ARBITRO-MEMORIA-UNIFICADA-POR-PRIORIDAD-01).

`vigilante_memavail.elige_culpable` elige entre las unidades elegibles la de MENOR rango (`data/rangos_memoria.json`)
y, dentro de ese rango, la de mayor memoria. Solo el rango: la accion (ceder, congelar, detener) es de
FEATURE-ESCALERA-CEDER-CONGELAR-DETENER-VERIFICADA-01. Todo con fixtures: ninguna prueba toca una unidad real.

Control del control: el codigo de antes (elige solo por memoria), sacado de git a un directorio temporal, elige la
unidad EQUIVOCADA en el caso principal; asi la prueba de rango puede salir roja.
"""

from __future__ import annotations

import importlib.util as util
import json
import shutil
import subprocess
from pathlib import Path

import pytest

from tools import vigilante_memavail as v

RAIZ = Path(__file__).resolve().parent.parent
DATOS = RAIZ / "data" / "rangos_memoria.json"
GIB = 1 << 30
# Ultimo commit de tools/vigilante_memavail.py antes del rango: elige la elegible de mayor memoria, sin rango.
COMMIT_VIEJO = "c891d9a2987a0d72291afcf342c45003b0d794b9"

LAB = v.Unidad("bb-lab-acaparador-1.scope", "/cg/lab", 1 * GIB)
SUITE = v.Unidad("bb-portero-suite-4242.scope", "/cg/suite", 9 * GIB)
TODO = ("*",)


class _Efectos:
    def __init__(self, unidades):
        self.lista, self.detenidas = unidades, []

    def ctx(self):
        return v.Contexto(v.LINEA_GIB, v.ELEGIBLES, lambda: self.lista, lambda cg: [{"cgroup": cg, "pid": 7}],
                          lambda n: (self.detenidas.append(n), {"rc": 0, "salida": ""})[1])


# ------------------------------------------------------------------ (a) el de menor rango gana aunque tenga menos


def test_el_acaparador_de_menor_rango_es_el_elegido_aunque_otro_de_mayor_rango_tenga_mas_memoria(tmp_path):
    fx = _Efectos([SUITE, LAB])
    ev = v.paso("actuar", 1 * 1048576, 0.0, tmp_path, fx.ctx())  # MemAvailable 1 GiB: sobre la linea
    assert ev is not None and fx.detenidas == [LAB.nombre]  # el codigo viejo detenia la suite (9 GiB)
    c = v.elige_culpable([SUITE, LAB])
    assert c["veredicto"] == "DETENER" and c["unidad"]["nombre"] == LAB.nombre and c["rango"] == 0
    assert v.RANGOS.rango(LAB.nombre) < v.RANGOS.rango(SUITE.nombre)


def test_cuatro_clases_eligen_la_de_menor_rango_y_no_la_mayor():
    app = v.Unidad("app-firefox-9.scope", "/cg/ff", 40 * GIB)  # sesion, no protegida
    assert v.elige_culpable([app, SUITE, LAB], elegibles=TODO)["unidad"]["nombre"] == LAB.nombre
    assert v.elige_culpable([app, SUITE], elegibles=TODO)["unidad"]["nombre"] == SUITE.nombre


def test_mismo_rango_elige_por_memoria_como_antes():
    grande = v.Unidad("bb-lab-grande-2.scope", "/cg/g", 3 * GIB)
    assert v.elige_culpable([LAB, grande])["unidad"]["nombre"] == grande.nombre


# ------------------------------------------------------------------ (b) control negativo: nunca se detiene


def test_control_negativo_la_unica_elegible_es_de_rango_alto_y_protegida_refused(tmp_path):
    claude = v.Unidad("app-com.anthropic.Claude-1.scope", "/cg/claude", 40 * GIB)
    assert v.RANGOS.rango(claude.nombre) == 3
    assert v.elige_culpable([claude], elegibles=TODO)["veredicto"] == "REFUSED"
    fx = _Efectos([claude])
    fx_ctx = fx.ctx()._replace(elegibles=TODO)
    ev = v.paso("actuar", 1 * 1048576, 0.0, tmp_path, fx_ctx)
    assert ev is not None and fx.detenidas == [] and ev["accion"].startswith("REFUSED")


def test_control_negativo_sin_elegibles_not_collected_y_nada_se_detiene(tmp_path):
    claude = v.Unidad("app-com.anthropic.Claude-1.scope", "/cg/claude", 40 * GIB)
    for lista in ([claude], [], None):  # claude no casa con ELEGIBLES por defecto
        fx = _Efectos(lista)
        ev = v.paso("actuar", 1 * 1048576, 0.0, tmp_path, fx.ctx())
        assert ev is not None and fx.detenidas == [] and ev["accion"].startswith("NOT_COLLECTED"), lista


# ------------------------------------------------------------------ (c) el motor sigue sin ser elegible


@pytest.mark.parametrize("nombre", ["vllm-engine.service", "docker-abc.scope", "containerd.service"])
def test_el_motor_sigue_sin_ser_elegible(nombre):
    motor = v.Unidad(nombre, "/cg/m", 60 * GIB)
    assert v.RANGOS.rango(nombre) == 4
    assert v.elige_culpable([motor])["veredicto"] == "NOT_COLLECTED"  # fuera de ELEGIBLES por defecto
    assert v.elige_culpable([motor], elegibles=TODO)["veredicto"] == "REFUSED"  # protegido aunque casara
    # con un acaparador de menor rango, el elegido es el acaparador, nunca el motor
    c = v.elige_culpable([motor, LAB], elegibles=TODO)
    assert c["veredicto"] == "DETENER" and c["unidad"]["nombre"] == LAB.nombre


def test_una_unidad_protegida_en_el_rango_mas_bajo_sigue_rechazada():
    """Como antes: si la elegida es protegida, REFUSED, aunque haya otra elegible de su mismo rango."""
    vllm = v.Unidad("bb-lab-vllm-motor.scope", "/cg/vllm", 50 * GIB)
    assert v.RANGOS.rango(vllm.nombre) == 0  # casa con laboratorio y motor: toma el MENOR
    assert v.elige_culpable([vllm, LAB])["veredicto"] == "REFUSED"


def test_unidad_sin_rango_declarado_cae_en_el_mas_bajo_nunca_en_uno_alto():
    atlas = v.Unidad("liberation_job.scope", "/cg/a", 2 * GIB)  # Atlas aun no declara su rango
    assert v.RANGOS.rango(atlas.nombre) == min(r for _, r, _ in v.RANGOS.clases) == 0
    assert v.elige_culpable([atlas, LAB], elegibles=TODO)["unidad"]["nombre"] == atlas.nombre  # mas memoria, mismo rango


# ------------------------------------------------------------------ (d) respaldo identico al fichero


def test_el_respaldo_es_identico_al_fichero():
    d = json.loads(DATOS.read_text(encoding="utf-8"))
    assert v.RESPALDO_RANGOS == tuple((e["clase"], e["rango"], tuple(e["patrones"])) for e in d["clases"])
    assert v.RANGOS.error is None and v.RANGOS.clases == v.RESPALDO_RANGOS


def test_las_clases_de_la_ficha_en_orden_ascendente():
    assert [c for c, _, _ in sorted(v.RESPALDO_RANGOS, key=lambda x: x[1])] == [
        "laboratorio", "suites", "atlas", "sesion", "motor"]


# ------------------------------------------------------------------ (e) fichero ausente o roto: respaldo, sin lanzar


ROTOS = {
    "falta": None,
    "json_roto": "{no es json",
    "lista_en_vez_de_objeto": "[]",
    "sin_clases": "{}",
    "clases_vacias": '{"clases": []}',
    "rango_no_entero": '{"clases": [{"clase": "x", "rango": "0", "patrones": ["*"]}]}',
    "rango_bool": '{"clases": [{"clase": "x", "rango": true, "patrones": ["*"]}]}',
    "patrones_texto": '{"clases": [{"clase": "x", "rango": 0, "patrones": "bb-lab-*"}]}',
    "patron_vacio": '{"clases": [{"clase": "x", "rango": 0, "patrones": [""]}]}',
    "clase_vacia": '{"clases": [{"clase": "", "rango": 0, "patrones": ["*"]}]}',
}


@pytest.mark.parametrize("caso", sorted(ROTOS))
def test_fichero_roto_usa_el_respaldo_avisa_y_no_lanza(caso, tmp_path, caplog):
    ruta = tmp_path / "rangos_memoria.json"
    if ROTOS[caso] is not None:
        ruta.write_text(ROTOS[caso], encoding="utf-8")
    r = v.cargar_rangos(ruta)
    assert r.error is not None and r.clases == v.RESPALDO_RANGOS
    assert any("rangos_memoria" in rec.getMessage() and "respaldo" in rec.getMessage() for rec in caplog.records)


def test_un_fichero_valido_si_se_usa(tmp_path, caplog):
    """Control negativo de la de arriba: si el lector devolviera siempre el respaldo, esto falla."""
    ruta = tmp_path / "rangos_memoria.json"
    ruta.write_text('{"clases": [{"clase": "a", "rango": 5, "patrones": ["bb-portero-suite-*"]},'
                    ' {"clase": "b", "rango": 9, "patrones": ["bb-lab-*"]}]}', encoding="utf-8")
    r = v.cargar_rangos(ruta)
    assert r.error is None and r.rango(SUITE.nombre) == 5 and r.rango(LAB.nombre) == 9 and not caplog.records
    # con los rangos invertidos, la eleccion se invierte: el rango manda, no el orden de la lista
    assert v.elige_culpable([SUITE, LAB], rangos=r)["unidad"]["nombre"] == SUITE.nombre


# ------------------------------------------------------------------ (f) control del control: el codigo viejo falla


def test_control_del_control_el_codigo_viejo_elige_la_unidad_equivocada(tmp_path):
    fuente = subprocess.run(["git", "-C", str(RAIZ), "show", f"{COMMIT_VIEJO}:tools/vigilante_memavail.py"],
                            capture_output=True, text=True, timeout=30, check=True).stdout
    assert "rangos" not in fuente  # de verdad es el codigo de antes
    (tmp_path / "tools").mkdir()
    (tmp_path / "data").mkdir()
    shutil.copy2(RAIZ / "data" / "procesos_protegidos.json", tmp_path / "data" / "procesos_protegidos.json")
    ruta = tmp_path / "tools" / "vigilante_memavail_viejo.py"
    ruta.write_text(fuente, encoding="utf-8")
    spec = util.spec_from_file_location("vigilante_memavail_viejo", ruta)
    assert spec is not None and spec.loader is not None
    viejo = util.module_from_spec(spec)
    spec.loader.exec_module(viejo)
    assert viejo.PROTEGIDOS.error is None  # leyo la lista real, no el respaldo
    u = [viejo.Unidad(*SUITE), viejo.Unidad(*LAB)]
    assert viejo.elige_culpable(u)["unidad"]["nombre"] == SUITE.nombre  # el viejo: la de mas memoria, rango alto
    assert v.elige_culpable([SUITE, LAB])["unidad"]["nombre"] == LAB.nombre  # el nuevo: la de menor rango
