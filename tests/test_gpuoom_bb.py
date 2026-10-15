import json
import subprocess
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
    gpu = g.Candidato(2, "python3", 2_000_000, 0, 0, 60_000_000)
    assert gpu.anon_kib < cpu.anon_kib and gpu.puntaje() > cpu.puntaje()
    v, porque = g.elige_victima([cpu, gpu], propio_pid=999)
    assert v is not None and v.pid == 2 and "gpu 58593" in porque


def test_el_motor_vllm_no_es_victima_aunque_tenga_la_mayor_huella():
    """Lista unica (data/procesos_protegidos.json, voto de Luis 2026-10-14): antes gpuoom elegia al motor."""
    cpu = g.Candidato(1, "pytest", 5_000_000, 0, 0, 0)
    motor = g.Candidato(2, "VLLM::EngineCor", 2_000_000, 0, 0, 60_000_000)
    sesion = g.Candidato(3, "claude", 9_000_000, 0, 0, 0)
    assert motor.puntaje() > sesion.puntaje() > cpu.puntaje()
    v, _ = g.elige_victima([cpu, motor, sesion], propio_pid=999)
    assert v is not None and v.pid == 1


def test_oom_adj_escala_y_menos_mil_exime():
    base = g.Candidato(1, "a", 1000 * KIB, 0, 0, 0)
    assert g.Candidato(1, "a", 1000 * KIB, 0, 0, 0, 500).puntaje() == base.puntaje() * 3 // 2
    exento = g.Candidato(3, "x", 99_000_000, 0, 0, 0, -1000)
    elegido = g.elige_victima([exento, base], 999)[0]
    assert elegido is not None and elegido.pid == 1


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
    assert ev is not None and ev["victima"] is not None
    # la GPU es del motor (pid 11), protegido: la victima es pytest
    assert ev["procesos_omitidos"] == 3 and ev["veredicto"] == "critico" and "pytest" in ev["victima"] and ev["confirmado_por_psi"] is True
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
    assert ev is not None and ev["accion"].startswith("UNSUPPORTED")


def test_lee_proc_real_encuentra_este_proceso():
    import os
    filas, omitidos = g.lee_proc()
    assert os.getpid() in {p[0] for p in filas} and omitidos >= 0


def test_el_muestreo_corre_en_otro_hilo_y_no_bloquea_la_decision():
    import threading
    import time

    liberar = threading.Event()
    arrancado = threading.Event()
    hilos = []

    def colgado():
        hilos.append(threading.current_thread().name)
        arrancado.set()
        liberar.wait(timeout=5.0)  # simula nvidia-smi bloqueado por el cerrojo del driver
        return "1, 10\n"

    m = g.MuestreadorGpu(ejecuta=colgado)
    m.arranca(intervalo=0.01)
    assert arrancado.wait(timeout=2.0)
    t0 = time.monotonic()
    mapa, nota = m.lee(t0)  # no debe esperar al hilo colgado
    liberar.set()
    assert time.monotonic() - t0 < 1.0 and hilos[0] == "gpuoom-gpu" and nota.startswith("NOT_COLLECTED")


def test_nvidia_smi_real_ejecuta_el_binario_del_PATH_y_devuelve_su_stdout(tmp_path, monkeypatch):
    smi = tmp_path / "nvidia-smi"
    smi.write_text("#!/bin/sh\nprintf '%s\\n' \"$1 $2\" '4242, 512'\n", encoding="utf-8")
    smi.chmod(0o755)
    monkeypatch.setenv("PATH", f"{tmp_path}:/usr/bin:/bin")
    texto = g.MuestreadorGpu._nvidia_smi()
    assert "--query-compute-apps=pid,used_memory --format=csv,noheader,nounits" in texto
    assert g.parsea_gpu(texto) == {4242: 512 * KIB}
    m = g.MuestreadorGpu()  # sin `ejecuta`: usa el binario real del PATH
    m.muestrea(7.0)
    assert m.lee(7.0) == ({4242: 512 * KIB}, "")


@pytest.mark.parametrize("fallo", [OSError("sin nvidia-smi"), subprocess.TimeoutExpired("nvidia-smi", 20)])
def test_muestreo_fallido_no_deja_copia_ni_propaga(fallo):
    def roto():
        raise fallo

    m = g.MuestreadorGpu(ejecuta=roto)
    m.muestrea(1.0)
    assert m.lee(2.0) == ({}, "NOT_COLLECTED: GPU nunca muestreada")


def test_lee_proc_lee_un_arbol_falso_y_cuenta_los_ilegibles(tmp_path):
    ok = tmp_path / "100"
    ok.mkdir()
    (ok / "status").write_text("Name:\tpython3\nRssAnon:\t  2048 kB\nRssShmem:\t 64 kB\nVmSwap:\t 8 kB\n", encoding="utf-8")
    (ok / "oom_score_adj").write_text("250\n", encoding="utf-8")
    sin_adj = tmp_path / "101"  # murio durante el barrido: sin oom_score_adj
    sin_adj.mkdir()
    (sin_adj / "status").write_text("Name:\tefimero\n", encoding="utf-8")
    adj_basura = tmp_path / "102"
    adj_basura.mkdir()
    (adj_basura / "status").write_text("Name:\tx\n", encoding="utf-8")
    (adj_basura / "oom_score_adj").write_text("no-es-un-entero\n", encoding="utf-8")
    (tmp_path / "cpuinfo").write_text("no es un proceso", encoding="utf-8")
    filas, ilegibles = g.lee_proc(tmp_path)
    assert filas == [(100, "python3", 2048, 64, 8, 250)]
    assert ilegibles == 2


def test_lee_proc_sin_nombre_ni_campos_usa_signo_de_interrogacion_y_ceros(tmp_path):
    d = tmp_path / "7"
    d.mkdir()
    (d / "status").write_text("Pid:\t7\n", encoding="utf-8")
    (d / "oom_score_adj").write_text("0\n", encoding="utf-8")
    assert g.lee_proc(tmp_path) == ([(7, "?", 0, 0, 0, 0)], 0)


def test_paso_en_calma_devuelve_el_nuevo_desde_y_ningun_evento(tmp_path):
    gpu = g.MuestreadorGpu(ejecuta=lambda: "")
    assert g.paso("observar", 50.0, 0.0, 10.0, 5.0, _cands, gpu, tmp_path) == (None, None)
    # pendiente: dentro de la zona pero antes de SOSTENIDO_S; el inicio se conserva y no hay evento
    assert g.paso("observar", 6.0, 20.0, 100.0, None, _cands, gpu, tmp_path) == (100.0, None)
    assert not list(tmp_path.iterdir())


def _redirige_path(monkeypatch, tmp_path, contenido=None):
    """`/proc/...` -> tmp_path/<nombre>; con `contenido` el archivo existe, sin el no existe (OSError real)."""
    if contenido is not None:
        for nombre, texto in contenido.items():
            (tmp_path / nombre).write_text(texto, encoding="utf-8")
    monkeypatch.setattr(g, "Path", lambda p: tmp_path / Path(p).name)


def test_meminfo_y_psi_leen_su_valor_y_declaran_la_ausencia(tmp_path, monkeypatch):
    _redirige_path(monkeypatch, tmp_path, {"meminfo": "MemTotal:  1000 kB\nMemAvailable:   250 kB\n",
                                           "memory": "some avg10=12.50 avg60=1.00 avg300=0.00 total=5\nfull avg10=3.00 avg60=0 avg300=0 total=1\n"})
    assert g._meminfo_kib("MemTotal") == 1000 and g._meminfo_kib("MemAvailable") == 250
    assert g._meminfo_kib("Inexistente") is None
    assert g._psi_some() == 12.5
    (tmp_path / "memory").write_text("full avg10=3.00\n", encoding="utf-8")
    assert g._psi_some() is None  # sin linea `some`
    (tmp_path / "meminfo").unlink()
    (tmp_path / "memory").unlink()
    assert g._meminfo_kib("MemTotal") is None and g._psi_some() is None  # archivos ausentes: OSError real


def test_principal_lee_el_host_decide_y_registra_hasta_que_el_sueno_lo_corta(tmp_path, monkeypatch):
    class Alto(Exception):
        pass

    ciclos = []

    def duerme(segundos):
        ciclos.append(segundos)
        if len(ciclos) == 2:
            raise Alto

    monkeypatch.setenv("BLACKBOX_DATA", str(tmp_path))
    (tmp_path / "interruptores.json").write_text(json.dumps({"modos": {"gpuoom": "observar"}}), encoding="utf-8")
    monkeypatch.setattr(g.MuestreadorGpu, "arranca", lambda self, intervalo=0: None)  # sin hilo de nvidia-smi
    monkeypatch.setattr(g, "_meminfo_kib", lambda clave: 1000 if clave == "MemTotal" else 10)  # 1 % disponible: critico
    monkeypatch.setattr(g, "_psi_some", lambda: 40.0)
    monkeypatch.setattr(g, "lee_proc", lambda: ([(1, "hambriento", 9_000_000, 0, 0, 0)], 0))
    monkeypatch.setattr(g.time, "sleep", duerme)
    with pytest.raises(Alto):
        g.principal()
    assert ciclos == [1, 1]
    assert interruptores.resumen("gpuoom", tmp_path / "interruptores") == {"disparos": 2, "confirmados": 2, "falsos_positivos": 0}
    filas = [json.loads(x) for x in (tmp_path / "interruptores" / "gpuoom.jsonl").read_text(encoding="utf-8").splitlines()]
    assert all(f["veredicto"] == "critico" and "hambriento" in f["victima"] for f in filas)


def test_script_entrypoint_llama_a_principal(tmp_path, monkeypatch):
    import runpy
    import threading

    class Alto(Exception):
        pass

    def duerme(_segundos):
        if threading.current_thread() is threading.main_thread():
            raise Alto
        threading.Event().wait()  # el hilo demonio de muestreo queda aparcado

    monkeypatch.setenv("BLACKBOX_DATA", str(tmp_path))  # modo off: no registra nada
    monkeypatch.setenv("PATH", str(tmp_path))  # sin nvidia-smi: el hilo recibe un OSError real y sigue
    monkeypatch.setattr(g.time, "sleep", duerme)
    with pytest.raises(Alto):
        runpy.run_path(g.__file__, run_name="__main__")
    assert not (tmp_path / "interruptores").exists()
