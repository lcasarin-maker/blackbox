import json
from pathlib import Path

import pytest

from tools import gpuoom_bb as g
from tools import interruptores

KIB = 1024


def test_evalua_calma_sin_psi_alto():
    # MemAvailable bajo pero PSI sano: es cache llena, no thrashing
    assert g.evalua(5.0, 1.0, 100.0, None)[0] == "calma"


def test_evalua_sin_dato_si_psi_ilegible():
    assert g.evalua(1.0, None, 100.0, None)[0] == "sin_dato"


def test_evalua_critico_inmediato_aunque_psi_bajo():
    assert g.evalua(1.5, 0.0, 100.0, None)[0] == "critico"


def test_evalua_sostenido_exige_tiempo():
    v, desde, _ = g.evalua(6.0, 20.0, 100.0, None)
    assert v == "pendiente" and desde == 100.0
    v, desde2, _ = g.evalua(6.0, 20.0, 102.0, desde)
    assert v == "pendiente" and desde2 == 100.0
    assert g.evalua(6.0, 20.0, 103.5, desde)[0] == "sostenido"


def test_evalua_se_reinicia_al_salir_de_la_zona():
    _, desde, _ = g.evalua(6.0, 20.0, 100.0, None)
    assert g.evalua(30.0, 20.0, 101.0, desde) == ("calma", None, g.evalua(30.0, 20.0, 101.0, desde)[2])


def test_la_gpu_decide_la_victima():
    cpu = g.Candidato(1, "pytest", 5_000_000, 0, 0, 0)
    gpu = g.Candidato(2, "VLLM::EngineCor", 2_000_000, 0, 0, 60_000_000)
    assert gpu.anon_kib < cpu.anon_kib and gpu.puntaje() > cpu.puntaje()
    v, porque = g.elige_victima([cpu, gpu], propio_pid=999)
    assert v.pid == 2 and "gpu 58593" in porque


def test_oom_adj_escala_y_menos_mil_exime():
    base = g.Candidato(1, "a", 1000 * KIB, 0, 0, 0)
    assert g.Candidato(1, "a", 1000 * KIB, 0, 0, 0, 500).puntaje() == base.puntaje() * 3 // 2
    exento = g.Candidato(3, "x", 99_000_000, 0, 0, 0, -1000)
    assert g.elige_victima([exento, base], 999)[0].pid == 1


def test_protegidos_propio_y_minimo_no_son_victimas():
    cs = [g.Candidato(1, "systemd", 9_000_000, 0, 0, 0), g.Candidato(2, "yo", 9_000_000, 0, 0, 0),
          g.Candidato(3, "chico", 1000, 0, 0, 0)]
    v, porque = g.elige_victima(cs, propio_pid=2)
    assert v is None and "ninguno elegible" in porque


def test_parsea_gpu_suma_por_pid_e_ignora_basura():
    assert g.parsea_gpu("123, 2048\nxx\n123, 1024\n5, 7\n") == {123: 3072 * KIB, 5: 7 * KIB}


def test_muestreador_viejo_y_nunca():
    m = g.MuestreadorGpu(ejecuta=lambda: "1, 10\n")
    assert m.lee(0)[1].startswith("NOT_COLLECTED")
    m.muestrea(100.0)
    assert m.lee(110.0) == ({1: 10 * KIB}, "")
    assert "vieja" in m.lee(200.0)[1]


def _cands():
    return [(10, "pytest", 8_000_000, 0, 0, 0), (11, "VLLM::EngineCor", 2_000_000, 0, 0, 0)], 3


def test_paso_off_no_registra(tmp_path):
    gpu = g.MuestreadorGpu(ejecuta=lambda: "")
    assert g.paso("off", 1.0, 50.0, 0, None, _cands, gpu, tmp_path) == (None, None)
    assert not list(tmp_path.iterdir())


def test_paso_observar_registra_victima_con_gpu_y_confirma_psi(tmp_path):
    gpu = g.MuestreadorGpu(ejecuta=lambda: "11, 60000\n")
    gpu.muestrea(0.0)
    _, ev = g.paso("observar", 1.0, 50.0, 1.0, None, _cands, gpu, tmp_path)
    assert ev["procesos_omitidos"] == 3 and ev["veredicto"] == "critico" and "VLLM::EngineCor" in ev["victima"] and ev["confirmado_por_psi"] is True
    assert interruptores.resumen("gpuoom", tmp_path) == {"disparos": 1, "confirmados": 1, "falsos_positivos": 0}


def test_paso_critico_con_psi_sano_cuenta_falso_positivo(tmp_path):
    gpu = g.MuestreadorGpu(ejecuta=lambda: "")
    g.paso("observar", 1.0, 0.0, 1.0, None, _cands, gpu, tmp_path)
    assert interruptores.resumen("gpuoom", tmp_path)["falsos_positivos"] == 1


def test_paso_sin_meminfo_no_actua(tmp_path):
    gpu = g.MuestreadorGpu(ejecuta=lambda: "")
    assert g.paso("observar", None, 50.0, 0, None, _cands, gpu, tmp_path) == (None, None)


def test_actuar_declara_unsupported(tmp_path):
    gpu = g.MuestreadorGpu(ejecuta=lambda: "")
    _, ev = g.paso("actuar", 1.0, 50.0, 1.0, None, _cands, gpu, tmp_path)
    assert ev["accion"].startswith("UNSUPPORTED")


def test_lee_proc_real_encuentra_este_proceso():
    import os
    filas, omitidos = g.lee_proc()
    assert os.getpid() in {p[0] for p in filas} and omitidos >= 0
