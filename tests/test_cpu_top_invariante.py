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


def test_muestras_descarta_los_marcadores_de_rafaga(tmp_path):
    """Un marcador `burst_fin` como ultima linea no es una muestra: no lleva cpu_top."""
    import json
    carpeta = tmp_path / "samples"
    carpeta.mkdir()
    lineas = [
        {"ts": "t1", "cpu_top": [{"pid": 1}]},
        {"ts": "t2", "burst": True, "load1": 9},
        {"ts": "t3", "burst_inicio": True, "motivo": "x"},
        {"ts": "t4", "burst_fin": True},
    ]
    (carpeta / "2026-10-10.jsonl").write_text("\n".join(json.dumps(x) for x in lineas) + "\n", encoding="utf-8")
    assert [m["ts"] for m in bash_tests.muestras(tmp_path)] == ["t1"]


def test_control_negativo_una_muestra_completa_posterior_SI_se_conserva(tmp_path):
    import json
    carpeta = tmp_path / "samples"
    carpeta.mkdir()
    lineas = [{"ts": "t1", "burst_fin": True}, {"ts": "t2", "cpu_top": []}]
    (carpeta / "2026-10-10.jsonl").write_text("\n".join(json.dumps(x) for x in lineas) + "\n", encoding="utf-8")
    assert [m["ts"] for m in bash_tests.muestras(tmp_path)] == ["t2"]
