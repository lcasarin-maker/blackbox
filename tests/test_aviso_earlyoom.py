"""Pruebas de `tools/aviso_earlyoom.py`. Las lineas son las que earlyoom escribio de verdad el 2026-11-06 en el diario.

Cada afirmacion de «avisa» lleva al lado la de «no avisa» con el mismo camino.
"""
import subprocess
from types import SimpleNamespace

from tools import aviso_earlyoom as ae

K1 = 'sending SIGTERM to process 347967 uid 1000 "ChatGPT": badness 868, VmRSS 448 MiB'
K2 = 'sending SIGKILL to process 3704 uid 0 "fusermount3": badness 800, VmRSS 1 MiB'
BAJA = "mem avail: 12381 of 123970 MiB ( 9.99%), swap free: 11619 of 16383 MiB (70.92%)"
BAJA2 = "mem avail:  7196 of 123970 MiB ( 5.81%), swap free: 9044 of 16383 MiB (55.20%)"
RUIDO = ["low memory! at or below SIGTERM limits: mem 10.00%, swap 100.00%", "process exited after 0.1 seconds",
         "memory situation has recovered while selecting victim", "Preferring to kill process names that match regex '(pytest)'"]


def test_parsea_una_muerte_y_una_linea_de_memoria():
    assert ae.parsea(K1) == {"senal": "SIGTERM", "pid": 347967, "uid": 1000, "nombre": "ChatGPT", "badness": 868, "rss_mib": 448}
    assert ae.parsea(BAJA) == {"avail_pct": 9.99}


def test_el_ruido_del_diario_no_es_una_muerte():
    assert all(ae.parsea(r) is None for r in RUIDO)  # control: ninguna de estas lineas cuenta


def test_sin_senales_no_hay_rafaga_aunque_baje_la_memoria():
    r = ae.Rafaga()
    r.alimenta(BAJA, 0.0)
    assert not r.lista(1000.0) and r.min_pct is None  # control: la memoria sola no abre una rafaga


def test_la_rafaga_se_cierra_tras_20_s_quietos_y_resume():
    r = ae.Rafaga()
    for t, l in [(0, K1), (1, BAJA), (2, K1), (3, K2), (4, BAJA2)]:
        r.alimenta(l, float(t))
    assert not r.lista(10.0)  # solo 6 s desde la ultima senal: sigue abierta
    assert r.lista(30.0)
    res = r.cierra()
    assert res["senales"] == 3 and res["sigkill"] == 1 and res["nombres"][0] == ("ChatGPT", 2) and res["min_pct"] == 5.81
    assert r.kills == [] and not r.lista(9999.0)  # cerrada: vuelve a empezar


def test_el_texto_nombra_quien_murio_y_el_mayor_en_gpu():
    res = {"senales": 54, "sigkill": 9, "nombres": [("ChatGPT", 21), ("python3", 6)], "min_pct": 5.8}
    gpu = [{"nombre": "gpt-oss-runtime", "gib": 87.5, "lanzado_por": "sisifo-launch"}]
    t = ae.texto(res, gpu)
    assert "54 procesos" in t and "ChatGPTx21" in t and "5.8 %" in t and "gpt-oss-runtime 87.5 GiB (lanzado_por=sisifo-launch)" in t
    assert "sin consumidores legibles" in ae.texto(res, [])  # control: sin GPU legible lo dice


def _salida(texto):
    return SimpleNamespace(stdout=texto)


def test_culpables_gpu_resuelve_el_contenedor_y_su_etiqueta():
    cid = "c992f7c4438e"
    cg = lambda pid: f"0::/sisifo.slice/docker-{cid}eeeeeeeeeeeeeeeeeeeeee.scope"  # noqa: E731

    def run(cmd, **kw):
        if cmd[0] == "nvidia-smi":
            return _salida("361085, 89577\n139583, 222\n")
        assert cmd[:2] == ["docker", "inspect"] and cmd[-1] == cid
        return _salida("/gpt-oss-runtime|sisifo-launch\n")

    out = ae.culpables_gpu(run, cg)
    assert out[0] == {"nombre": "gpt-oss-runtime", "gib": 89577 / 1024, "lanzado_por": "sisifo-launch"}
    assert len(out) == 2


def test_culpables_gpu_sin_nvidia_smi_devuelve_vacio_y_sin_docker_marca_pid():
    def sin_smi(cmd, **kw):
        raise FileNotFoundError

    assert ae.culpables_gpu(sin_smi) == []  # control: instrumento caido no inventa culpables
    out = ae.culpables_gpu(lambda cmd, **kw: _salida("42, 2048\n"), lambda pid: "0::/user.slice/app.scope")
    assert out == [{"nombre": "pid 42", "gib": 2.0, "lanzado_por": "?"}]  # control: sin contenedor, el pid


def test_culpables_gpu_ignora_filas_ilegibles_y_errores_de_docker():
    def run(cmd, **kw):
        if cmd[0] == "nvidia-smi":
            return _salida("basura\n7, 1024\n")
        raise subprocess.SubprocessError

    out = ae.culpables_gpu(run, lambda pid: "0::/system.slice/docker-aaaaaaaaaaaa.scope")
    assert out == [{"nombre": "pid 7", "gib": 1.0, "lanzado_por": "?"}]


RES = {"senales": 3, "sigkill": 0, "nombres": [("ChatGPT", 3)], "min_pct": 9.0}


def test_procesa_actuar_envia_y_registra():
    enviados, filas = [], []
    f = ae.procesa(RES, [], "actuar", "https://ntfy.sh/x", lambda u, m: enviados.append((u, m)) or True, lambda n, e: filas.append((n, e)))
    assert f["enviado"] is True and len(enviados) == 1 and filas[0][0] == "aviso_earlyoom"


def test_procesa_observar_registra_pero_no_envia():
    enviados, filas = [], []
    f = ae.procesa(RES, [], "observar", "https://ntfy.sh/x", lambda u, m: enviados.append(m) or True, lambda n, e: filas.append(e))
    assert f["enviado"] is False and enviados == [] and filas and f["habria_avisado"] is True  # control del caso anterior


def test_procesa_off_no_hace_nada():
    enviados, filas = [], []
    f = ae.procesa(RES, [], "off", "https://ntfy.sh/x", lambda u, m: enviados.append(m) or True, lambda n, e: filas.append(e))
    assert enviados == [] and filas == [] and f["habria_avisado"] is False


def test_procesa_sin_url_o_con_ntfy_caido_lo_deja_en_el_registro():
    filas = []
    f = ae.procesa(RES, [], "actuar", None, lambda u, m: True, lambda n, e: filas.append(e))
    assert f["enviado"] is False and "ntfy_url" in f["error"]

    def cae(u, m):
        raise OSError

    f2 = ae.procesa(RES, [], "actuar", "https://ntfy.sh/x", cae, lambda n, e: filas.append(e))
    assert f2["enviado"] is False and f2["error"] == "OSError" and len(filas) == 2  # no tumba al vigilante


def test_url_ntfy_exige_https(tmp_path, monkeypatch):
    monkeypatch.setattr(ae.Path, "home", classmethod(lambda cls: tmp_path))
    assert ae.url_ntfy() is None  # control: sin archivo
    (tmp_path / ".config/blackbox").mkdir(parents=True)
    (tmp_path / ".config/blackbox/ntfy_url").write_text("http://ntfy.sh/x\n")
    assert ae.url_ntfy() is None
    (tmp_path / ".config/blackbox/ntfy_url").write_text("https://ntfy.sh/x\n")
    assert ae.url_ntfy() == "https://ntfy.sh/x"
