"""Suite de `tools/control_racha.py`, el control de falsos positivos de la
regla de racha de `bb-usable`.

El modulo es un INSTRUMENTO, y la ley de la casa dice que un instrumento
declarado bueno solo por su caso positivo esta sin verificar. Aqui se mide en
las dos direcciones: que no dispara sobre una serie sana y que SI dispara sobre
una que debe dispararle.
"""

from __future__ import annotations

import datetime as dt
import importlib.machinery as machinery
import importlib.util as util
from pathlib import Path

import pytest

from tools import control_racha as cr

RAIZ = Path(__file__).resolve().parent.parent


def _serie(pares, base=dt.datetime(2026, 9, 15, 3, 0)):
    """[(minuto, psi)] -> [(ts, psi)]. Se ancla en el 2026-09-15, que no cae en
    ninguna ventana de incidente: si cayera, el modulo lo excluiria y el test
    mediria la exclusion en vez de la regla."""
    return [(base + dt.timedelta(minutes=m), p) for m, p in pares]


# ------------------------------------ la regla, en las dos direcciones


# Cuatro altas, una bajada suelta, cuatro altas. Las mitades se eligen para
# que NINGUNA llegue sola al corte -- 180 s y 240 s-- y juntas si: 420 s. Con
# cinco por lado la segunda mitad da 300 s exactos y el par de tests de abajo
# dejaria de distinguir el arreglo del defecto, que es todo lo que mide.
_CON_UNA_BAJADA = [(m, 99.0) for m in range(4)] + [(4, 0.0)] + \
                  [(m, 99.0) for m in range(5, 9)]


def test_una_bajada_suelta_NO_corta_la_racha_con_el_arreglo():
    """Con 2 bajas para cortar, las dos mitades cuentan como una sola racha y
    pasan del corte. Es la forma de la traza del panico del 2026-09-26."""
    s, _ = cr.max_sostenido_sano(_serie(_CON_UNA_BAJADA), bajas_para_cortar=2)
    assert s >= 300.0, "una bajada suelta no puede poner la duracion a cero"


def test_control_negativo_con_1_baja_la_misma_serie_NO_llega_al_corte():
    """El defecto, sobre la MISMA serie. Sin este par, el de arriba pasaria con
    una funcion que devolviera siempre un numero grande."""
    s, _ = cr.max_sostenido_sano(_serie(_CON_UNA_BAJADA), bajas_para_cortar=1)
    assert s < 300.0, (
        "con 1 baja para cortar la racha se parte en 180 s y 240 s, y ninguna "
        "mitad llega al corte -- ese es exactamente el defecto")


def test_dos_bajadas_seguidas_SI_cortan():
    serie = _serie([(m, 99.0) for m in range(5)]
                   + [(5, 0.0), (6, 0.0)]
                   + [(m, 99.0) for m in range(7, 11)])
    s, _ = cr.max_sostenido_sano(serie, bajas_para_cortar=2)
    assert s < 300.0, "dos bajas seguidas son una recuperacion y cortan"


def test_un_hueco_largo_no_encadena_una_racha_que_nadie_observo():
    """Dos muestras altas separadas por cuatro horas no son cuatro horas de
    colapso: son dos muestras. Es el error que invalido el primer intento de
    este control, donde el hueco de 794 s de la ventana del panico se leyo
    como continuidad."""
    serie = [(dt.datetime(2026, 9, 15, 3, 0), 99.0),
             (dt.datetime(2026, 9, 15, 7, 0), 99.0)]
    s, _ = cr.max_sostenido_sano(serie, bajas_para_cortar=2)
    assert s == 0.0, f"encadeno {s:.0f}s a traves de un hueco de 4 h"


def test_las_ventanas_de_incidente_se_excluyen():
    """Un colapso real dentro de su ventana no es un falso positivo. Si el
    modulo no lo excluyera, reportaria los tres congelamientos medidos como
    falsos positivos y el veredicto seria inservible."""
    dentro = _serie([(m, 99.0) for m in range(20)],
                    base=dt.datetime(2026, 9, 22, 6, 0))
    assert cr.max_sostenido_sano(dentro, 2)[0] == 0.0
    assert cr.es_incidente(dt.datetime(2026, 9, 22, 6, 0)) is True
    assert cr.es_incidente(dt.datetime(2026, 9, 26, 15, 30)) is True, (
        "el panico del 2026-09-26 es la cuarta ventana de verdad etiquetada")
    assert cr.es_incidente(dt.datetime(2026, 9, 15, 3, 0)) is False


# ------------------------------------ el corte, contra el sujeto real


def test_el_corte_es_el_MISMO_que_el_del_demonio():
    """`CORTE_S` se fija a mano porque `bin/bb-usable` no es importable. Un
    numero copiado a mano se desincroniza en silencio, asi que se compara con
    la fuente. Es el mismo modo de fallo que el techo de docker puesto a 16G
    mientras su close_check pinaba 32G."""
    fuente = (RAIZ / "bin" / "bb-usable").read_text(encoding="utf-8")
    loader = machinery.SourceFileLoader("bb_usable", str(RAIZ / "bin" / "bb-usable"))
    spec = util.spec_from_loader("bb_usable", loader)
    assert spec is not None, "no se pudo construir el spec de bin/bb-usable"
    bbu = util.module_from_spec(spec)
    loader.exec_module(bbu)
    assert cr.CORTE_S == bbu.PSI_ACT_SOSTENIDO_S, (
        f"el control mide contra {cr.CORTE_S}s y el demonio actua a los "
        f"{bbu.PSI_ACT_SOSTENIDO_S}s")
    assert "BAJAS_PARA_CORTAR" in fuente


# ------------------------------------ el gate, de punta a punta


def test_el_gate_sale_0_sobre_el_corpus_real(capsys):
    """Sobre las muestras de esta maquina. Si no hay corpus, COULD_NOT_RUN y
    se dice -- no se llama limpio a lo que no se pudo medir."""
    rc = cr.main([])
    if rc == 2:
        pytest.skip(
            f"COULD_NOT_RUN: corpus real ausente en {cr.MUESTRAS}; "
            "owner=Blackbox; trigger=restaurar el corpus registrado"
        )
    salida = capsys.readouterr().out
    assert rc == 0, f"el control reporta falsos positivos:\n{salida}"
    assert "VEREDICTO: LIMPIO" in salida


def test_control_negativo_el_gate_SI_sale_1_con_el_corte_bajado(capsys):
    """La otra direccion, y es la que da valor al test de arriba. Con el corte
    en 180 s entra la excursion sana mas larga del corpus y el veredicto se
    tiene que volver rojo."""
    rc = cr.main(["--corte", "180"])
    if rc == 2:
        pytest.skip(
            f"COULD_NOT_RUN: corpus real ausente en {cr.MUESTRAS}; "
            "owner=Blackbox; trigger=restaurar el corpus registrado"
        )
    salida = capsys.readouterr().out
    assert rc == 1, (
        "el control no puede salir negativo, asi que su 'LIMPIO' no verifica "
        f"nada:\n{salida}")
    assert "FALSO POSITIVO" in salida


def test_sin_corpus_es_COULD_NOT_RUN_y_no_limpio(tmp_path, capsys):
    """rc=2, y lo dice. Un control que no encuentra su corpus y devuelve 0 seria
    la peor de las tres salidas: afirma que no hay falsos positivos sobre una
    serie que no leyo. Es el primer modo de fallo de la lista de la casa -- un
    instrumento caido indistinguible de un sujeto limpio."""
    rc = cr.main(["--muestras", str(tmp_path / "no-existe")])
    assert rc == 2, "sin corpus, ni 0 ni 1: la tercera salida"
    assert "COULD_NOT_RUN" in capsys.readouterr().err


# --- falsos positivos conocidos: excepcion con caducidad atada a su ficha (2026-10-16) ---

RAIZ = Path(__file__).resolve().parent.parent


def _serie_sostenida(desde: dt.datetime, minutos: int, psi: float = 50.0):
    return [(desde + dt.timedelta(minutes=m), psi) for m in range(minutos)]


def test_cada_falso_positivo_conocido_apunta_a_una_ficha_ABIERTA():
    """La caducidad: cuando la ficha se cierra (sale de tasks/backlog/) esta excepcion tiene que borrarse, y este
    test es el que obliga. Una excepcion sin ficha abierta es una supresion."""
    assert cr.FALSOS_POSITIVOS_CONOCIDOS, "si ya no hay ninguno, borra tambien esta prueba"
    for f in cr.FALSOS_POSITIVOS_CONOCIDOS:
        ficha = RAIZ / "tasks" / "backlog" / f"{f['ficha']}.md"
        assert ficha.is_file(), f"la ficha {f['ficha']} ya no esta abierta: quita la excepcion de calibra_psi.FALSOS_POSITIVOS_CONOCIDOS"
        assert "status: open" in ficha.read_text(encoding="utf-8")
        assert f["motivo"].strip()


def test_las_excepciones_NO_son_incidentes_ni_entran_a_la_calibracion():
    from tools.calibra_psi import INCIDENTES
    for f in cr.FALSOS_POSITIVOS_CONOCIDOS:
        assert f["ventana"] not in INCIDENTES, "un falso positivo no se declara incidente"
    assert len(cr.ventanas()) == len(INCIDENTES)


def test_control_negativo_sin_la_excepcion_el_stall_conocido_SI_es_falso_positivo():
    f = cr.FALSOS_POSITIVOS_CONOCIDOS[0]
    ini = dt.datetime.strptime(f["ventana"][0], "%Y-%m-%d %H:%M")
    serie = _serie_sostenida(ini, 15)  # 15 min sostenidos dentro de la ventana
    con, _ = cr.max_sostenido_sano(serie, 2)
    sin, instante = cr.max_sostenido_sano(serie, 2, exentas=[])
    assert con == 0.0, "dentro de la excepcion no cuenta"
    assert sin >= cr.CORTE_S and instante is not None, "sin la excepcion, el control SI dispara"


def test_la_excepcion_no_tapa_un_stall_igual_FUERA_de_su_ventana():
    f = cr.FALSOS_POSITIVOS_CONOCIDOS[0]
    fin = dt.datetime.strptime(f["ventana"][1], "%Y-%m-%d %H:%M")
    serie = _serie_sostenida(fin + dt.timedelta(hours=3), 15)
    peor, _ = cr.max_sostenido_sano(serie, 2)
    assert peor >= cr.CORTE_S, "un stall nuevo, fuera de la ventana exenta, tiene que seguir bloqueando"


def test_el_gate_imprime_el_falso_positivo_conocido_como_deuda(capsys):
    rc = cr.main([])
    if rc == 2:
        pytest.skip("COULD_NOT_RUN: corpus real ausente; owner=Blackbox; trigger=restaurar el corpus registrado")
    salida = capsys.readouterr().out
    assert "falso positivo CONOCIDO excluido (deuda abierta DEBT-COLAPSO-CONFINADO" in salida
