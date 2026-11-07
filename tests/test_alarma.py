"""Pruebas de la alarma externa `tools/testigo/bb_alarma.py` (un archivo autonomo que se copia a la Dell).

Se carga por ruta, como se usa copiado. Cada afirmacion de «avisa» lleva al lado la de «no avisa» con el mismo camino, para que una
funcion que siempre avisa, o que nunca avisa, no pase.
"""
import importlib.util
import json
from pathlib import Path

import pytest

RUTA = Path(__file__).resolve().parents[1] / "tools" / "testigo" / "bb_alarma.py"
spec = importlib.util.spec_from_file_location("bb_alarma", RUTA)
al = importlib.util.module_from_spec(spec)
spec.loader.exec_module(al)

CFG = {"umbral": 3, "intervalo_s": 30, "recordatorio_s": 3600, "latido_diario_s": 86400, "timeout_s": 1.0,
       "checks": [{"nombre": "ssh-casa", "host": "h1", "puerto": 22}, {"nombre": "ssh-tailscale", "host": "h2", "puerto": 22}],
       "ntfy_url": "https://ntfy.sh/x"}
VACIO = {"fallos": {}, "avisado": {}, "desde": {}, "ultimo_latido": 1}  # latido reciente: aisla lo que se prueba


def corre(estado, secuencia, t0=1000.0, paso=30.0):
    """Aplica una lista de resultados ciclo a ciclo (confirmando todo envio) y devuelve (estado, mensajes por ciclo)."""
    por_ciclo = []
    for i, res in enumerate(secuencia):
        estado, msgs = al.decide(estado, res, t0 + i * paso, CFG)
        for clave, _ in msgs:
            estado = al.confirma(estado, clave, t0 + i * paso)
        por_ciclo.append([t for _, t in msgs])
    return estado, por_ciclo


def test_no_avisa_si_todo_responde():
    _, m = corre(VACIO, [{"ssh-casa": True, "ssh-tailscale": True}] * 5)
    assert m == [[]] * 5  # control negativo: nada que avisar


def test_avisa_al_llegar_al_umbral_y_no_antes():
    caido = {"ssh-casa": True, "ssh-tailscale": False}
    _, m = corre(VACIO, [caido] * 3)
    assert m[0] == [] and m[1] == []  # 1 y 2 fallos: aun no
    assert len(m[2]) == 1 and "ssh-tailscale caido" in m[2][0] and "responden: ssh-casa" in m[2][0]


def test_no_repite_el_aviso_hasta_el_recordatorio():
    caido = {"ssh-casa": True, "ssh-tailscale": False}
    _, m = corre(VACIO, [caido] * 6)
    assert sum(len(x) for x in m) == 1  # un solo aviso en 6 ciclos seguidos caidos
    est, m2 = corre(VACIO, [caido] * 3)
    est, m3 = al.decide(est, caido, 1000.0 + 3600 + 100, CFG)
    assert len(m3) == 1  # pasado el recordatorio, repite


def test_avisa_la_recuperacion_y_solo_una_vez():
    caido = {"ssh-casa": True, "ssh-tailscale": False}
    bien = {"ssh-casa": True, "ssh-tailscale": True}
    _, m = corre(VACIO, [caido] * 3 + [bien, bien])
    assert "volvio" in m[3][0] and m[4] == []


def test_dice_que_ningun_camino_responde():
    todo = {"ssh-casa": False, "ssh-tailscale": False}
    _, m = corre(VACIO, [todo] * 3)
    assert any("no responde ningun camino" in t for t in m[2])


def test_un_fallo_aislado_reinicia_la_cuenta():
    caido = {"ssh-casa": True, "ssh-tailscale": False}
    bien = {"ssh-casa": True, "ssh-tailscale": True}
    _, m = corre(VACIO, [caido, caido, bien, caido, caido])
    assert all(x == [] for x in m)  # nunca llega a 3 seguidos


def test_latido_diario_se_envia_una_vez_y_no_antes_de_tiempo():
    nuevo = {"fallos": {}, "avisado": {}, "desde": {}, "ultimo_latido": 0}
    bien = {"ssh-casa": True, "ssh-tailscale": True}
    t0 = 1.7e9  # un epoch real: con epoch chico, "hace un dia" no se cumpliria nunca
    est, m = corre(nuevo, [bien, bien], t0=t0)
    assert len(m[0]) == 1 and "viva" in m[0][0] and m[1] == []
    _, m2 = al.decide(est, bien, t0 + 86400 + 1, CFG)
    assert len(m2) == 1  # y al dia siguiente, otra vez


def test_un_envio_fallido_se_reintenta_en_el_ciclo_siguiente():
    caido = [{"nombre": "ssh-casa", "host": "h1", "puerto": 22}]
    cfg = dict(CFG, checks=caido, umbral=1)
    estado = dict(VACIO, avisado={}, desde={}, fallos={})
    intentos = []

    def manda(url, texto):
        intentos.append(texto)
        if len(intentos) == 1:
            raise OSError("ntfy caido")
        return True

    estado, f1 = al.ciclo(estado, cfg, 1000.0, sonda=lambda *a: False, manda=manda)
    assert f1["enviados"] == [] and f1["errores"]  # fallo el envio y quedo registrado
    estado, f2 = al.ciclo(estado, cfg, 1030.0, sonda=lambda *a: False, manda=manda)
    assert len(f2["enviados"]) == 1 and len(intentos) == 2  # control: el segundo si salio


def test_carga_exige_https_y_checks(tmp_path):
    (tmp_path / "alarma.json").write_text(json.dumps({"checks": CFG["checks"], "ntfy_url": "http://ntfy.sh/x"}))
    with pytest.raises(SystemExit):
        al.carga(tmp_path)
    (tmp_path / "alarma.json").write_text(json.dumps({"checks": CFG["checks"], "ntfy_url": "https://ntfy.sh/x"}))
    assert al.carga(tmp_path)["umbral"] == 3  # control: con https carga y trae los defectos


def test_tcp_ok_distingue_abierto_de_cerrado():
    import socket
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    s.listen(1)
    puerto = s.getsockname()[1]
    assert al.tcp_ok("127.0.0.1", puerto, 1.0) is True
    s.close()
    assert al.tcp_ok("127.0.0.1", puerto, 1.0) is False  # control negativo: cerrado
