"""El invariante de `cpu_top` cuando el proceso del test no sale en el top 5.

`mio` se mide desde antes de la primera muestra y el campo `cpu_s` de bb solo
cubre el intervalo entre las dos: con la maquina cargada la primera muestra
tarda segundos y esa diferencia se leia como "otros mas frios" (fallo medido el
2026-10-10, load 37). La holgura es el tiempo que tardo esa primera muestra.
Cada caso que debe pasar tiene su gemelo que debe caer: el instrumento no puede
quedar mudo.
"""
import pytest

import test_bb_bash as bash_tests

HELPER = bash_tests._no_esta_pero_los_cinco_queman_mas


def _lista(*segundos):
    return [{"pid": i, "comm": "x", "cpu_s": s, "pct_nucleo": s * 10.0} for i, s in enumerate(segundos)]


def test_sin_holgura_otros_a_un_segundo_del_mio_se_leen_como_mas_frios():
    with pytest.raises(AssertionError, match="MAS FRIOS"):
        HELPER(_lista(9, 8, 7, 6, 6), "cpu_s", 10, "cpu_top")


def test_con_holgura_igual_a_lo_que_tardo_la_primera_muestra_no_cae():
    assert HELPER(_lista(9, 8, 7, 6, 6), "cpu_s", 10, "cpu_top", holgura=4) is None


def test_control_negativo_con_holgura_uno_realmente_mas_frio_SI_cae():
    with pytest.raises(AssertionError, match="MAS FRIOS"):
        HELPER(_lista(9, 8, 7, 6, 1), "cpu_s", 10, "cpu_top", holgura=4)


def test_control_negativo_lista_incompleta_cae_aunque_haya_holgura():
    with pytest.raises(AssertionError, match="NO esta llena"):
        HELPER(_lista(9, 8, 7), "cpu_s", 10, "cpu_top", holgura=4)
