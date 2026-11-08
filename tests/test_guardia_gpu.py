"""Pruebas de `tools/guardia_gpu.py`. Cada afirmacion de «detiene» lleva al lado la de «no detiene» con el mismo camino."""
import subprocess
from types import SimpleNamespace

from tools import guardia_gpu as gg

CID = "c992f7c4438e"
CID2 = "3be89e9310fe"


def _cg(pid):
    return {100: f"0::/sisifo.slice/docker-{CID}eeeeeeeeeeeeeeeeeeeeee.scope", 101: f"0::/sisifo.slice/docker-{CID}eeeeeeeeeeeeeeeeeeeeee.scope",
            200: f"0::/system.slice/docker-{CID2}eeeeeeeeeeeeeeeeeeeeee.scope", 300: "0::/user.slice/app.scope"}[pid]


def _run(cmd, **kw):
    if cmd[0] == "nvidia-smi":
        return SimpleNamespace(stdout="100, 80000\n101, 9577\n200, 35000\n300, 500\nbasura\n", returncode=0)
    nombre = {CID: "/gpt-oss-runtime|sisifo-launch", CID2: "/nemotron-server|"}[cmd[-1]]
    return SimpleNamespace(stdout=nombre + "\n", returncode=0)


def test_contenedores_gpu_suma_por_contenedor_y_omite_lo_que_no_es_docker():
    cs = gg.contenedores_gpu(_run, _cg)
    assert [c["nombre"] for c in cs] == ["gpt-oss-runtime", "nemotron-server"]  # mayor primero; el pid 300 (no docker) y la basura se omiten
    assert round(cs[0]["gib"], 2) == round((80000 + 9577) / 1024, 2) and cs[0]["lanzado_por"] == "sisifo-launch"
    assert cs[1]["lanzado_por"] == ""


def test_contenedores_gpu_sin_nvidia_smi_devuelve_vacio():
    def sin(cmd, **kw):
        raise FileNotFoundError

    assert gg.contenedores_gpu(sin, _cg) == []  # control: instrumento caido no inventa contenedores


def test_elige_exige_etiqueta_y_tamano():
    g = {"nombre": "a", "gib": 87.5, "lanzado_por": "sisifo"}
    n = {"nombre": "nemotron-server", "gib": 34.0, "lanzado_por": ""}
    chico = {"nombre": "c", "gib": 2.0, "lanzado_por": "x"}
    assert gg.elige([n, g])["nombre"] == "a"  # el mayor ELEGIBLE aunque el de chat este antes en la lista
    assert gg.elige([n]) is None  # control: sin etiqueta nunca se elige, por grande que sea
    assert gg.elige([chico]) is None  # control: con etiqueta pero bajo MIN_GPU_GIB tampoco


def test_decide_pide_leer_la_gpu_solo_tras_muestras_seguidas():
    est = {}
    for i in range(gg.MUESTRAS - 1):
        est, leer = gg.decide(est, gg.LINEA_MB - 1, 1000.0 + i)
        assert leer is False  # aun no
    est, leer = gg.decide(est, gg.LINEA_MB - 1, 2000.0)
    assert leer is True
    est, leer = gg.decide(est, gg.LINEA_MB + 5000, 2001.0)  # se recupera: la cuenta vuelve a cero
    assert est["bajas"] == 0 and leer is False


def test_decide_respeta_el_enfriamiento():
    est = {"bajas": 99, "ultimo_paro": 5000.0}
    _, leer = gg.decide(est, 1000, 5000.0 + gg.ENFRIAMIENTO_S - 1)
    assert leer is False
    _, leer2 = gg.decide(est, 1000, 5000.0 + gg.ENFRIAMIENTO_S + 1)
    assert leer2 is True  # control: pasado el enfriamiento si


CONTS = [{"id": CID, "nombre": "gpt-oss-runtime", "gib": 87.5, "lanzado_por": "sisifo"},
         {"id": CID2, "nombre": "nemotron-server", "gib": 34.0, "lanzado_por": ""}]


def test_actuar_detiene_registra_y_avisa():
    llamadas, filas, avisos = [], [], []
    run = lambda cmd, **kw: llamadas.append(cmd) or SimpleNamespace(returncode=0, stdout="")  # noqa: E731
    f = gg.actua("actuar", 12000, CONTS, run, "https://ntfy.sh/x", lambda u, m: avisos.append(m) or True, lambda n, e: filas.append(e))
    assert llamadas == [["docker", "stop", "-t", "15", "gpt-oss-runtime"]] and f["paro"] is True
    assert filas and "gpt-oss-runtime" in avisos[0] and "detenido" in avisos[0]


def test_observar_no_detiene_pero_registra_lo_que_habria_hecho():
    llamadas, filas = [], []
    run = lambda cmd, **kw: llamadas.append(cmd) or SimpleNamespace(returncode=0, stdout="")  # noqa: E731
    f = gg.actua("observar", 12000, CONTS, run, "https://ntfy.sh/x", lambda u, m: True, lambda n, e: filas.append(e))
    assert llamadas == [] and f["paro"] is False and f["habria_actuado"] is True and filas  # control del caso anterior


def test_off_no_hace_ni_registra_nada():
    filas, llamadas = [], []
    gg.actua("off", 12000, CONTS, lambda cmd, **kw: llamadas.append(cmd), None, lambda u, m: True, lambda n, e: filas.append(e))
    assert filas == [] and llamadas == []


def test_sin_elegible_no_detiene_a_nadie_y_lo_dice():
    llamadas, filas = [], []
    run = lambda cmd, **kw: llamadas.append(cmd) or SimpleNamespace(returncode=0, stdout="")  # noqa: E731
    f = gg.actua("actuar", 12000, [CONTS[1]], run, None, lambda u, m: True, lambda n, e: filas.append(e))
    assert llamadas == [] and f["habria_actuado"] is False and "ningun contenedor" in f["motivo"]  # el motor de chat sobrevive


def test_un_docker_stop_fallido_se_registra_como_no_detenido():
    filas, avisos = [], []
    run = lambda cmd, **kw: SimpleNamespace(returncode=1, stdout="")  # noqa: E731
    f = gg.actua("actuar", 12000, CONTS, run, "https://ntfy.sh/x", lambda u, m: avisos.append(m) or True, lambda n, e: filas.append(e))
    assert f["paro"] is False and "docker stop rc=1" in f["error"] and "NO se pudo detener" in avisos[0]


def test_docker_inaccesible_o_ntfy_caido_no_tumban_la_guardia():
    def cae(cmd, **kw):
        raise subprocess.SubprocessError

    f = gg.actua("actuar", 12000, CONTS, cae, "https://ntfy.sh/x", lambda u, m: (_ for _ in ()).throw(OSError()), lambda n, e: None)
    assert f["paro"] is False and f["error"] == "SubprocessError" and f["avisado"] is False and f["error_aviso"] == "OSError"
