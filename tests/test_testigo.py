"""Pruebas del testigo externo `tools/testigo/bb_testigo.py`.

El testigo es UN archivo autonomo que se copia a otro equipo, asi que aqui se carga por ruta (como se usaria copiado) y no
como modulo de `tools`. Cada afirmacion lleva su control: la que dice «fallo» tiene al lado la que dice «ok» con el mismo
camino, para que una funcion que siempre devuelve lo mismo no pase. Los controles de mutacion cargan el archivo con el fsync o
el latido quitados y exigen que la prueba correspondiente falle.
"""
import base64
import configparser
import errno
import importlib.util
import json
import os
import plistlib
import socket
import sys
import threading
import time
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

RUTA = Path(__file__).resolve().parents[1] / "tools" / "testigo" / "bb_testigo.py"
NS = {"t": "http://schemas.microsoft.com/windows/2004/02/mit/task"}


def _carga(ruta=RUTA, nombre="bb_testigo_bajo_prueba"):
    spec = importlib.util.spec_from_file_location(nombre, ruta)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


bt = _carga()
CFG = bt.valida_config({"atom_host": "192.0.2.10"})


class _R:
    def __init__(self, rc, stdout=b"", stderr=""):
        self.returncode, self.stdout, self.stderr = rc, stdout, stderr


def _puerto_cerrado():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    p = s.getsockname()[1]
    s.close()
    return p


def _mutado(tmp_path, viejo, nuevo):
    src = RUTA.read_text(encoding="utf-8")
    assert src.count(viejo) == 1, f"el ancla de la mutacion debe existir una sola vez: {viejo!r}"
    p = tmp_path / "bb_testigo_mutado.py"
    p.write_text(src.replace(viejo, nuevo), encoding="utf-8")
    return _carga(p, "bb_testigo_mutado")


# --- sondeos -------------------------------------------------------------------------------------------------------------


def test_tcp_destino_inalcanzable_da_fallo_y_nunca_ok():
    nombre = bt.sondea_tcp("atom.invalid", 22, 1.0)  # .invalid no resuelve nunca (RFC 6761)
    assert nombre["ok"] is False and nombre["estado"] == "sin_nombre"
    cerrado = bt.sondea_tcp("127.0.0.1", _puerto_cerrado(), 1.0)
    assert cerrado["ok"] is True and cerrado["estado"] == "rechazado"  # un RST es la ATOM contestando: el kernel vive
    # Una IP real sin nadie detras (TEST-NET) no sirve aqui: el filtro de salida de un contenedor contesta con RST por ella. El
    # timeout y el «sin ruta» se prueban abajo inyectando el error del socket.
    # control positivo: el mismo camino con un puerto que escucha SI da ok
    srv = socket.socket()
    srv.bind(("127.0.0.1", 0))
    srv.listen(1)
    try:
        abierto = bt.sondea_tcp("127.0.0.1", srv.getsockname()[1], 1.0)
    finally:
        srv.close()
    assert abierto["ok"] is True and abierto["estado"] == "abierto"


@pytest.mark.parametrize("exc,estado", [
    (socket.timeout("timed out"), "timeout"),
    (OSError(errno.EHOSTUNREACH, "No route to host"), "inalcanzable"),  # EHOSTUNREACH: la ATOM ya no contesta ARP
    (OSError(errno.ENETUNREACH, "Network is unreachable"), "sin_red"),  # ENETUNREACH: es la red del propio testigo
    (socket.gaierror(-2, "Name or service not known"), "sin_nombre"),
])
def test_tcp_cada_fallo_de_red_es_fallo_sin_respuesta(monkeypatch, exc, estado):
    def falla(*a, **k):
        raise exc
    monkeypatch.setattr(bt.socket, "create_connection", falla)
    f = bt.sondea_tcp("192.0.2.10", 22, 0.5)
    assert f["ok"] is False and f["estado"] == estado


def test_flags_de_ping_por_sistema():
    assert bt.comando_ping("h", "linux", 2.0) == ["ping", "-c", "1", "-W", "2", "h"]  # Linux: segundos
    assert bt.comando_ping("h", "linux", 0.3) == ["ping", "-c", "1", "-W", "1", "h"]
    assert bt.comando_ping("h", "darwin", 2.0) == ["ping", "-c", "1", "-W", "2000", "h"]  # macOS: milisegundos
    assert bt.comando_ping("h", "win32", 2.0) == ["ping", "-n", "1", "-w", "2000", "h"]  # Windows: -n y -w en ms
    assert bt.comando_ping("h", "freebsd13", 2.0) is None


def test_icmp_fallo_y_trampa_de_windows():
    assert bt.sondea_icmp("h", "linux", 1.0, lambda *a, **k: _R(1))["ok"] is False
    assert bt.sondea_icmp("h", "linux", 1.0, lambda *a, **k: _R(0))["ok"] is True  # control
    inaccesible = "Respuesta desde 192.0.2.254: Host de destino inaccesible.".encode("cp850")
    assert bt.sondea_icmp("h", "win32", 1.0, lambda *a, **k: _R(0, inaccesible))["ok"] is False
    eco = b"Respuesta desde 192.0.2.10: bytes=32 tiempo<1m TTL=64"
    assert bt.sondea_icmp("h", "win32", 1.0, lambda *a, **k: _R(0, eco))["ok"] is True

    def sin_ping(*a, **k):
        raise FileNotFoundError("ping")
    f = bt.sondea_icmp("h", "linux", 1.0, sin_ping)
    assert f["ok"] is False and f["estado"] == "error"


def test_datagrama_udp_real_se_registra_con_su_origen(tmp_path):
    t = bt.Testigo(bt.valida_config({"atom_host": "127.0.0.1"}), tmp_path)
    llegaron = threading.Event()
    escribe, vistas = t.diarios["netconsole"].escribe, []

    def escribe_y_cuenta(fila):
        escribe(fila)
        vistas.append(fila)
        if len(vistas) >= 2:
            llegaron.set()
    t.diarios["netconsole"].escribe = escribe_y_cuenta
    sock = bt.abre_udp("127.0.0.1", 0)
    hilo = threading.Thread(target=t._escucha, args=(sock,), daemon=True)
    hilo.start()
    tx = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    tx.bind(("127.0.0.1", 0))
    antes = time.time()
    try:
        tx.sendto(b"<4>netconsole: ultima palabra\n", sock.getsockname())
        tx.sendto(b"\xff\xfe\x00", sock.getsockname())
        assert llegaron.wait(5.0), "los dos datagramas no llegaron en 5 s"
    finally:
        t.parar.set()
        hilo.join(3.0)
        sock.close()
        origen = tx.getsockname()
        tx.close()
    filas = bt.lee_filas(tmp_path / "netconsole.jsonl")
    assert len(filas) == 2
    assert filas[0]["origen"] == "127.0.0.1" and filas[0]["puerto_origen"] == origen[1]
    assert filas[0]["texto"] == "<4>netconsole: ultima palabra" and filas[0]["bytes"] == 30
    assert antes <= filas[0]["epoch"] <= time.time()
    assert "texto" not in filas[1] and base64.b64decode(filas[1]["b64"]) == b"\xff\xfe\x00"  # binario: no se pierde


def test_lee_enchufe_por_fabricante_sin_inventar_ceros():
    pedidas = []

    def abre(respuesta):
        def _abre(url):
            pedidas.append(url)
            return json.dumps(respuesta).encode()
        return _abre
    gen1 = bt.lee_enchufe("shelly1", "http://192.0.2.60/", abre({"meters": [{"power": 31.5, "is_valid": True}]}))
    assert gen1 == {"ok": True, "voltaje_v": None, "potencia_w": 31.5, "corriente_a": None}  # Plug Gen1 no mide voltaje
    gen2 = bt.lee_enchufe("shelly2", "http://192.0.2.60", abre({"apower": 30.1, "voltage": 121.2, "current": 0.25}))
    assert gen2 == {"ok": True, "voltaje_v": 121.2, "potencia_w": 30.1, "corriente_a": 0.25}
    tas = bt.lee_enchufe("tasmota", "http://192.0.2.60", abre({"StatusSNS": {"ENERGY": {"Power": 28, "Voltage": 120, "Current": 0.2}}}))
    assert tas["ok"] is True and tas["potencia_w"] == 28.0 and tas["voltaje_v"] == 120.0
    assert pedidas == ["http://192.0.2.60/status", "http://192.0.2.60/rpc/Switch.GetStatus?id=0", "http://192.0.2.60/cm?cmnd=Status%2010"]
    sin_potencia = bt.lee_enchufe("shelly1", "http://192.0.2.60", abre({"meters": [{}]}))
    assert sin_potencia["ok"] is False and "potencia_w" not in sin_potencia
    cero = bt.lee_enchufe("shelly2", "http://192.0.2.60", abre({"apower": 0, "voltage": 120.0}))
    assert cero["ok"] is True and cero["potencia_w"] == 0.0  # control: un cero MEDIDO si es un cero

    def mudo(url):
        raise OSError("timed out")
    assert bt.lee_enchufe("shelly2", "http://192.0.2.60", mudo) == {"ok": False, "error": "OSError"}


# --- veredicto de ventana ------------------------------------------------------------------------------------------------


def _ping(desde, ok_hasta, hasta, paso=1.0, vuelve=None):
    """Filas TCP de `desde` a `hasta`: responden hasta `ok_hasta` (y desde `vuelve`, si se da)."""
    filas, t = [], desde
    while t <= hasta:
        r = t <= ok_hasta or (vuelve is not None and t >= vuelve)
        filas.append({"epoch": t, "fuente": "tcp", "ok": r, "estado": "abierto" if r else "timeout"})
        t += paso
    return filas


def _energia(tramos, desde, hasta, voltaje=120.0, paso=1.0):
    """Lecturas del enchufe: `tramos` = [(hasta_epoch, potencia_w), ...] en orden."""
    filas, t = [], desde
    while t <= hasta:
        w = next(w for limite, w in tramos if t <= limite)
        filas.append({"epoch": t, "ok": True, "potencia_w": w, "voltaje_v": voltaje, "corriente_a": None})
        t += paso
    return filas


AHORA = 1000.0
FRESCO = [{"epoch": 995.0, "evento": "latido"}]
SILENCIO = _ping(900.0, 950.0, 999.0)  # la ATOM responde hasta 950 y calla de 951 en adelante


def test_sin_latido_status_no_concluye_atom_caida():
    for latido in ([], [{"epoch": 600.0, "evento": "latido"}],
                   [{"epoch": 990.0, "evento": "latido"}, {"epoch": 992.0, "evento": "parada"}]):
        v = bt.veredicto(SILENCIO, [], latido, CFG, AHORA)
        assert v["codigo"] == "testigo_sin_latido", latido
        assert "desde_epoch" not in v and "causa" not in v
    # control: las MISMAS filas con latido fresco si concluyen que la ATOM callo, y desde cuando
    v = bt.veredicto(SILENCIO, [], FRESCO, CFG, AHORA)
    assert v["codigo"] == "atom_callada" and v["desde_epoch"] == 951.0 and v["causa"] == "sin_enchufe"


def test_enchufe_que_cae_a_0_w_antes_de_perder_tcp_es_corte_de_energia_no_cuelgue():
    energia = _energia([(950.0, 31.0), (2000.0, 0.4)], 890.0, 999.0, paso=0.5)  # 0 W desde 950.5; TCP calla en 951
    v = bt.veredicto(SILENCIO, energia, FRESCO, CFG, AHORA)
    assert v["codigo"] == "atom_callada"
    assert v["causa"] == "corte_energia" and v["origen"] == "atom_o_adaptador" and v["epoch"] == 950.5
    assert "cuelgue" not in v["causa"]


def test_potencia_que_sigue_tras_el_silencio_es_cuelgue_y_si_cae_despues_es_apagado():
    sigue = _energia([(2000.0, 31.0)], 890.0, 999.0)
    v = bt.veredicto(SILENCIO, sigue, FRESCO, CFG, AHORA)
    assert v["causa"] == "cuelgue" and v["potencia_w"] == 31.0
    cae_luego = _energia([(980.0, 31.0), (2000.0, 0.0)], 890.0, 999.0)
    assert bt.veredicto(SILENCIO, cae_luego, FRESCO, CFG, AHORA)["causa"] == "apagado_tras_silencio"


def test_voltaje_perdido_enchufe_mudo_y_lecturas_incoherentes():
    pared = _energia([(950.0, 31.0), (2000.0, 0.0)], 890.0, 999.0)
    for f in pared:
        if f["epoch"] > 950.0:
            f["voltaje_v"] = 3.0
    v = bt.veredicto(SILENCIO, pared, FRESCO, CFG, AHORA)
    assert v["causa"] == "corte_energia" and v["origen"] == "pared"
    mudo = [{"epoch": t, "ok": False, "error": "OSError"} for t in range(900, 1000)]
    assert bt.veredicto(SILENCIO, mudo, FRESCO, CFG, AHORA)["causa"] == "enchufe_mudo"
    cero_siempre = _energia([(2000.0, 0.0)], 890.0, 999.0)  # 0 W mientras la ATOM respondia: mide otro aparato
    assert bt.veredicto(SILENCIO, cero_siempre, FRESCO, CFG, AHORA)["causa"] == "no_concluyente"
    calla_y_vuelve = [f if f["epoch"] <= 950.0 or f["epoch"] >= 970.0 else {"epoch": f["epoch"], "ok": False, "error": "OSError"}
                      for f in _energia([(2000.0, 31.0)], 890.0, 999.0)]  # el enchufe calla con la ATOM y vuelve consumiendo
    volvio = _ping(900.0, 950.0, 999.0, vuelve=990.0)
    assert bt.veredicto(volvio, calla_y_vuelve, FRESCO, CFG, AHORA)["episodio_anterior"]["causa"] == "enchufe_mudo"
    bajon_viejo = _energia([(2000.0, 31.0)], 890.0, 999.0)
    bajon_viejo[5]["voltaje_v"] = 60.0  # un bajon a 895, 55 s antes del silencio, que la ATOM sobrevivio
    assert bt.veredicto(SILENCIO, bajon_viejo, FRESCO, CFG, AHORA)["causa"] == "cuelgue"
    gen1 = [{**f, "voltaje_v": None} for f in _energia([(950.0, 31.0), (2000.0, 0.0)], 890.0, 999.0)]
    v = bt.veredicto(SILENCIO, gen1, FRESCO, CFG, AHORA)
    assert v["causa"] == "corte_energia" and v["origen"] == "sin_voltaje"


def test_silencio_cerrado_sin_respuesta_red_propia_y_paquetes_sueltos():
    volvio = _ping(900.0, 950.0, 999.0, vuelve=980.0)
    energia = _energia([(950.0, 31.0), (979.0, 0.0), (2000.0, 33.0)], 890.0, 999.0)
    v = bt.veredicto(volvio, energia, FRESCO, CFG, AHORA)
    assert v["codigo"] == "atom_responde"
    assert v["episodio_anterior"]["desde"] == 951.0 and v["episodio_anterior"]["hasta"] == 980.0
    assert v["episodio_anterior"]["causa"] == "corte_energia"
    nunca = _ping(900.0, 0.0, 999.0)
    v = bt.veredicto(nunca, _energia([(2000.0, 1.2)], 890.0, 999.0), FRESCO, CFG, AHORA)
    assert v["codigo"] == "sin_respuesta_registrada" and "no consume" in v["texto"]
    sin_red = SILENCIO + [{"epoch": 999.5, "fuente": "tcp", "ok": False, "estado": "sin_red"}]
    assert bt.veredicto(sin_red, [], FRESCO, CFG, AHORA)["codigo"] == "red_del_testigo"
    sueltos = [{**f, "ok": False} if f["epoch"] in (960.0, 961.0) else f for f in _ping(900.0, 999.0, 999.0)]
    assert bt.veredicto(sueltos, [], FRESCO, CFG, AHORA)["codigo"] == "atom_responde"  # 2 fallos no son un corte
    assert bt.veredicto(SILENCIO, [], FRESCO, CFG, 1100.0)["codigo"] == "testigo_sin_latido"  # el latido envejece
    detenido = bt.veredicto(_ping(900.0, 950.0, 960.0), [], FRESCO, CFG, AHORA)
    assert detenido["codigo"] == "sondeo_detenido"


def test_filas_de_observador_ping_y_del_nas_se_leen_igual():
    viejas = [{"epoch": float(t), "ok": t <= 950} for t in range(900, 1000)]
    v = bt.veredicto(viejas, [], FRESCO, CFG, AHORA)
    assert v["codigo"] == "atom_callada" and v["desde_epoch"] == 951.0


def test_estado_lee_los_archivos_reales(tmp_path):
    d = {n: bt.Diario(tmp_path / f"{n}.jsonl", 10**6, 2) for n in bt.ARCHIVOS}
    for f in SILENCIO:
        d["ping"].escribe(f)
    for f in _energia([(950.0, 31.0), (2000.0, 0.0)], 890.0, 999.0):
        d["energia"].escribe(f)
    d["latido"].escribe(FRESCO[0])
    d["netconsole"].escribe({"epoch": 950.9, "origen": "192.0.2.10", "puerto_origen": 6665, "texto": "<0>Kernel panic"})
    e = bt.estado(tmp_path, ahora=AHORA)
    assert e["veredicto"]["causa"] == "corte_energia" and e["ultimos_datagramas"][-1]["texto"] == "<0>Kernel panic"
    txt = bt.texto_estado(e)
    assert "VEREDICTO: ATOM_CALLADA" in txt and "Kernel panic" in txt and "corte de energia" in txt


# --- diario: fsync, rotacion, latido y mutaciones -----------------------------------------------------------------------


def _verifica_fsync_por_linea(mod, tmp_path, monkeypatch):
    llamadas, real = [], os.fsync

    def cuenta(fd):
        llamadas.append(fd)
        real(fd)
    monkeypatch.setattr(mod.os, "fsync", cuenta)
    d = mod.Diario(tmp_path / "f.jsonl", 10**6, 1)
    for i in range(3):
        d.escribe({"epoch": float(i)})
    assert len(llamadas) == 3, "cada fila debe ir con su propio fsync"


def test_cada_fila_va_con_fsync(tmp_path, monkeypatch):
    _verifica_fsync_por_linea(bt, tmp_path, monkeypatch)


def test_mutacion_sin_fsync_hace_fallar_la_prueba(tmp_path, monkeypatch):
    mod = _mutado(tmp_path, "os.fsync(fh.fileno())", "pass")
    with pytest.raises(AssertionError, match="fsync"):
        _verifica_fsync_por_linea(mod, tmp_path, monkeypatch)


def test_rotacion_por_tamano_sin_partir_lineas(tmp_path):
    d = bt.Diario(tmp_path / "x.jsonl", 300, 2)
    for i in range(40):
        d.escribe({"epoch": float(i), "relleno": "x" * 20})
    for nombre in ("x.jsonl", "x.jsonl.1", "x.jsonl.2"):
        datos = (tmp_path / nombre).read_bytes()
        assert 0 < len(datos) <= 300 and datos.endswith(b"\n")
        assert all(json.loads(ln) for ln in datos.splitlines())
    assert not (tmp_path / "x.jsonl.3").exists()  # quedan exactamente `copias` rotaciones
    epochs = [f["epoch"] for f in bt.lee_filas(tmp_path / "x.jsonl")]
    assert epochs == [float(i) for i in range(40 - len(epochs), 40)] and len(epochs) > 10  # cola continua, sin huecos
    corta = [f["epoch"] for f in bt.lee_filas(tmp_path / "x.jsonl", max_bytes=100)]
    assert corta and corta[-1] == 39.0 and len(corta) < 4  # ventana corta: la linea partida se descarta


def _corre_breve(mod, datos, duracion=1.2):
    cfg = {"atom_host": "atom.invalid", "atom_puerto": 22, "udp_bind": "127.0.0.1", "udp_puerto": 0,
           "latido_s": 0.2, "sondeo_s": 0.2, "icmp": False}
    (datos / "testigo.json").write_text(json.dumps(cfg), encoding="utf-8")
    return mod.main(["run", "--datos", str(datos), "--duracion", str(duracion)])


def _verifica_latido(mod, datos):
    assert _corre_breve(mod, datos) == 0
    latidos = [f for f in mod.lee_filas(datos / "latido.jsonl") if f.get("evento") == "latido"]
    assert len(latidos) >= 3, "el testigo debe latir mientras corre"
    assert mod.lee_filas(datos / "latido.jsonl")[-1]["evento"] == "parada"
    return latidos


@pytest.mark.integration
def test_run_real_late_y_un_destino_inalcanzable_solo_deja_filas_de_fallo(tmp_path):
    _verifica_latido(bt, tmp_path)
    ping = bt.lee_filas(tmp_path / "ping.jsonl")
    assert len(ping) >= 3 and all(f["ok"] is False and f["estado"] == "sin_nombre" for f in ping)
    assert bt.estado(tmp_path)["veredicto"]["codigo"] == "testigo_sin_latido"  # se paro limpio: ya no es testigo


@pytest.mark.integration
def test_mutacion_sin_latido_hace_fallar_la_prueba(tmp_path):
    mod = _mutado(tmp_path, 'self.diarios["latido"].escribe(fila_latido)', "pass")
    datos = tmp_path / "datos"
    datos.mkdir()
    with pytest.raises(AssertionError, match="latir"):
        _verifica_latido(mod, datos)


def test_instancia_unica_y_puerto_udp_ocupado(tmp_path):
    fh = bt.toma_bloqueo(tmp_path / "testigo.lock")
    assert fh is not None and bt.toma_bloqueo(tmp_path / "testigo.lock") is None
    (tmp_path / "testigo.json").write_text(json.dumps({"atom_host": "127.0.0.1"}), encoding="utf-8")
    assert bt.main(["run", "--datos", str(tmp_path), "--duracion", "0.1"]) == 3
    fh.close()
    assert bt.toma_bloqueo(tmp_path / "testigo.lock") is not None
    ocupado = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    ocupado.bind(("127.0.0.1", 0))
    try:
        cfg = {"atom_host": "127.0.0.1", "udp_bind": "127.0.0.1", "udp_puerto": ocupado.getsockname()[1]}
        (tmp_path / "testigo.json").write_text(json.dumps(cfg), encoding="utf-8")
        assert bt.main(["run", "--datos", str(tmp_path), "--duracion", "0.1"]) == 2
    finally:
        ocupado.close()
    assert not (tmp_path / "ping.jsonl").exists()  # sin puerto UDP no arranca ningun sondeo


def test_config_valida_y_rechaza_lo_invalido():
    assert CFG["atom_puerto"] == 22 and CFG["udp_puerto"] == 6666 and CFG["sondeo_s"] == 1.0
    for malo, motivo in (({}, "atom_host"), ({"atom_host": "a b"}, "atom_host"), ({"atom_host": "h", "atom_puerto": 0}, "atom_puerto"),
                         ({"atom_host": "h", "enchufe_tipo": "shelly2"}, "enchufe_url"), ({"atom_host": "h", "sondeo_s": 0}, "sondeo_s"),
                         ({"atom_host": "h", "enchufe_tipo": "x"}, "enchufe_tipo"), ({"atom_host": "h", "otra": 1}, "desconocidas")):
        with pytest.raises(ValueError, match=motivo):
            bt.valida_config(malo)
    assert bt.valida_config({"atom_host": "h", "enchufe_tipo": "tasmota", "enchufe_url": "http://192.0.2.60"})["enchufe_tipo"] == "tasmota"


def test_dir_datos_por_plataforma():
    env = {"HOME": "/h"}
    assert bt.dir_datos("linux", env) == Path("/h/.local/share/bb-testigo")
    assert bt.dir_datos("linux", {**env, "XDG_DATA_HOME": "/x"}) == Path("/x/bb-testigo")
    assert bt.dir_datos("darwin", env) == Path("/h/Library/Application Support/bb-testigo")
    assert bt.dir_datos("win32", {"USERPROFILE": "C:/U", "LOCALAPPDATA": "C:/U/AppData/Local"}) == Path("C:/U/AppData/Local/bb-testigo")
    assert bt.dir_datos("win32", {"USERPROFILE": "C:/U"}) == Path("C:/U/AppData/Local/bb-testigo")
    assert bt.dir_datos("darwin", {**env, "BB_TESTIGO_DATA": "/d"}) == Path("/d")


# --- install / uninstall -------------------------------------------------------------------------------------------------

PY, SCRIPT, DATOS = "/usr/bin/python3", "/h/.local/share/bb-testigo/bb_testigo.py", "/h/.local/share/bb-testigo"


def test_unidad_systemd_correcta_y_con_rutas_escapadas():
    u = bt.unidad_systemd(PY, SCRIPT, DATOS)
    ini = configparser.ConfigParser(interpolation=None, strict=True)
    ini.optionxform = str
    ini.read_string(u)
    assert ini.sections() == ["Unit", "Service", "Install"]
    assert ini["Service"]["ExecStart"] == f'"{PY}" "{SCRIPT}" run --datos "{DATOS}"'
    assert ini["Service"]["Restart"] == "always" and ini["Unit"]["StartLimitIntervalSec"] == "0"
    assert ini["Service"]["MemoryMax"] == "256M" and ini["Install"]["WantedBy"] == "default.target"
    raro = bt.unidad_systemd("/opt/py 3/python3", '/d/50%/$HOME/"s".py', "/d")
    assert '"/opt/py 3/python3" "/d/50%%/$$HOME/\\"s\\".py" run --datos "/d"' in raro


def test_plist_launchd_correcto():
    p = plistlib.loads(bt.plist_launchd(PY, SCRIPT, DATOS))
    assert p["Label"] == "local.bb-testigo"
    assert p["ProgramArguments"] == [PY, SCRIPT, "run", "--datos", DATOS]
    assert p["RunAtLoad"] is True and p["KeepAlive"] is True
    assert p["StandardErrorPath"] == DATOS + "/launchd.log"


def test_tarea_windows_sin_las_trampas_de_schtasks():
    py, sc, d = r"C:\Py\pythonw.exe", r"C:\U\AppData\Local\bb-testigo\bb_testigo.py", r"C:\U\AppData\Local\bb-testigo"
    raiz = ET.fromstring(bt.tarea_windows_xml(py, sc, d, "PC\\A&B").encode("utf-16"))
    v = lambda ruta: raiz.find(ruta, NS).text  # noqa: E731
    assert v("t:Settings/t:ExecutionTimeLimit") == "PT0S"  # schtasks /SC ONLOGON la mataria a las 72 h
    assert v("t:Settings/t:DisallowStartIfOnBatteries") == "false" and v("t:Settings/t:StopIfGoingOnBatteries") == "false"
    assert v("t:Triggers/t:LogonTrigger/t:UserId") == "PC\\A&B"  # escapado en el XML, literal al leerlo
    assert v("t:Actions/t:Exec/t:Command") == py
    assert v("t:Actions/t:Exec/t:Arguments") == f'"{sc}" run --datos "{d}"'


def _rutas(sistema, home):
    env = {"HOME": str(home), "USERPROFILE": str(home), "LOCALAPPDATA": str(home / "AppData" / "Local")}
    return bt.rutas_servicio(sistema, bt.dir_datos(sistema, env), env), env


def test_plan_de_cada_plataforma(tmp_path):
    r, env = _rutas("win32", tmp_path)
    plan = bt.plan_install("win32", CFG, r, "C:/Py/pythonw.exe", RUTA, {**env, "USERDOMAIN": "PC", "USERNAME": "u"})
    cmds = [a[1] for a in plan if a[0] == "ejecuta"]
    assert ["schtasks", "/Create", "/TN", "bb-testigo", "/XML", str(r["xml"]), "/F"] in cmds
    assert ["netsh", "advfirewall", "firewall", "add", "rule", "name=bb-testigo-udp-6666", "dir=in", "action=allow",
            "protocol=UDP", "localport=6666"] in cmds
    assert cmds[-1] == ["schtasks", "/Run", "/TN", "bb-testigo"]
    assert any(a[0] == "aviso" and "ADMINISTRADOR" in a[1] for a in plan)
    xml = next(a[2] for a in plan if a[0] == "escribe" and a[1] == r["xml"])
    assert xml[:2] == b"\xff\xfe" and "PC\\u" in xml.decode("utf-16")  # UTF-16 con BOM, lo que pide schtasks /XML
    r, env = _rutas("darwin", tmp_path)
    cmds = [a[1] for a in bt.plan_install("darwin", CFG, r, PY, RUTA, env, uid=501) if a[0] == "ejecuta"]
    assert cmds == [["launchctl", "bootout", "gui/501/local.bb-testigo"], ["launchctl", "bootstrap", "gui/501", str(r["plist"])]]
    assert r["plist"] == tmp_path / "Library" / "LaunchAgents" / "local.bb-testigo.plist"
    r, env = _rutas("linux", tmp_path)
    cmds = [a[1] for a in bt.plan_install("linux", CFG, r, PY, RUTA, env, which=lambda _: None) if a[0] == "ejecuta"]
    assert cmds[-1] == ["systemctl", "--user", "restart", "bb-testigo.service"]
    with pytest.raises(ValueError):
        bt.plan_install("freebsd13", CFG, r, PY, RUTA, env)


def test_wsl_avisa_que_no_recibe_udp(tmp_path):
    r, env = _rutas("linux", tmp_path)
    wsl = bt.plan_install("linux", CFG, r, PY, RUTA, env, osrelease="5.15.153.1-microsoft-standard-WSL2\n", which=lambda _: None)
    assert any(a[0] == "aviso" and "WSL2" in a[1] and "NATIVO de Windows" in a[1] for a in wsl)
    nativo = bt.plan_install("linux", CFG, r, PY, RUTA, env, osrelease="6.8.0-48-generic\n", which=lambda _: None)
    assert not any("WSL" in a[1] for a in nativo if a[0] == "aviso")


@pytest.mark.parametrize("sistema", ["linux", "darwin", "win32"])
def test_dry_run_no_escribe_ni_ejecuta_nada(tmp_path, capsys, sistema):
    home = tmp_path / "home"
    home.mkdir()
    env = {"HOME": str(home), "USERPROFILE": str(home), "LOCALAPPDATA": str(home / "AppData" / "Local"), "USERNAME": "u"}
    antes = sorted(tmp_path.rglob("*"))

    def prohibido(*a, **k):
        raise AssertionError(f"--dry-run ejecuto {a}")
    for orden in (["install", "--host", "192.0.2.10", "--no-preguntar", "--python", PY], ["uninstall", "--borrar-datos"]):
        assert bt.main(orden + ["--dry-run", "--sistema", sistema], env=env, correr=prohibido) == 0
    assert sorted(tmp_path.rglob("*")) == antes
    out = capsys.readouterr().out
    servicio = {"linux": "bb-testigo.service", "darwin": "local.bb-testigo.plist", "win32": "bb-testigo-tarea.xml"}[sistema]
    assert f"[dry-run] escribiria {bt.dir_datos(sistema, env) / 'testigo.json'}" in out and servicio in out
    assert '"atom_host": "192.0.2.10"' in out and "[dry-run] borraria" in out


@pytest.mark.skipif(not sys.platform.startswith("linux"), reason="instalacion real solo en la plataforma nativa")
def test_install_real_y_uninstall_deshacen_todo_salvo_la_evidencia(tmp_path):
    env = {"HOME": str(tmp_path)}
    llamadas = []

    def correr(argv, **k):
        llamadas.append(argv)
        return _R(0, "", "")
    assert bt.main(["install", "--host", "192.0.2.10", "--no-preguntar", "--python", PY], env=env, correr=correr) == 0
    datos, unidad = tmp_path / ".local/share/bb-testigo", tmp_path / ".config/systemd/user/bb-testigo.service"
    assert json.loads((datos / "testigo.json").read_text())["atom_host"] == "192.0.2.10"
    assert (datos / "bb_testigo.py").read_bytes() == RUTA.read_bytes() and unidad.is_file()
    assert ["systemctl", "--user", "restart", "bb-testigo.service"] in llamadas
    assert bt.main(["install", "--no-preguntar", "--python", PY], env=env, correr=correr) == 0  # reinstalar conserva el host
    (datos / "ping.jsonl").write_text('{"epoch": 1.0, "ok": true}\n')
    assert bt.main(["uninstall"], env=env, correr=correr) == 0
    assert not unidad.exists() and not (datos / "bb_testigo.py").exists() and not (datos / "testigo.json").exists()
    assert (datos / "ping.jsonl").exists() and ["systemctl", "--user", "disable", "--now", "bb-testigo.service"] in llamadas
    assert bt.main(["uninstall", "--borrar-datos"], env=env, correr=correr) == 0
    assert not datos.exists()
    llamadas.clear()

    def falla_reload(argv, **k):
        llamadas.append(argv)
        return _R(1 if "daemon-reload" in argv else 0, "", "Failed to connect to bus")
    assert bt.main(["install", "--host", "192.0.2.10", "--no-preguntar", "--python", PY], env=env, correr=falla_reload) == 1
    assert llamadas == [["systemctl", "--user", "daemon-reload"]]  # el primer fallo no tolerado para el plan


def test_install_pregunta_el_host_si_falta(tmp_path, monkeypatch, capsys):
    respuestas = iter(["192.0.2.10", "shelly2", "http://192.0.2.60"])
    monkeypatch.setattr("builtins.input", lambda _p="": next(respuestas))
    monkeypatch.setattr(bt.sys.stdin, "isatty", lambda: True, raising=False)
    env = {"HOME": str(tmp_path)}
    assert bt.main(["install", "--dry-run", "--sistema", "linux", "--python", PY], env=env, correr=None) == 0
    out = capsys.readouterr().out
    assert '"enchufe_tipo": "shelly2"' in out and '"enchufe_url": "http://192.0.2.60"' in out
    monkeypatch.setattr(bt.sys.stdin, "isatty", lambda: False, raising=False)
    assert bt.main(["install", "--dry-run", "--sistema", "linux"], env=env, correr=None) == 2  # sin terminal ni --host


@pytest.mark.integration
def test_run_con_icmp_y_enchufe_escribe_sus_series(tmp_path):
    cfg = bt.valida_config({"atom_host": "atom.invalid", "udp_bind": "127.0.0.1", "udp_puerto": 0, "icmp": True, "sondeo_s": 0.2,
                            "latido_s": 0.2, "enchufe_tipo": "shelly2", "enchufe_url": "http://192.0.2.60", "enchufe_s": 0.2})
    pings = []

    def ping_falso(cmd, **k):
        pings.append(cmd)
        return _R(1)
    t = bt.Testigo(cfg, tmp_path, sistema="darwin", correr=ping_falso, abre=lambda url: b'{"apower": 31.5, "voltage": 120.5}')
    t.corre(0.7)
    icmp = [f for f in bt.lee_filas(tmp_path / "ping.jsonl") if f["fuente"] == "icmp"]
    assert icmp and all(f["ok"] is False and f["estado"] == "sin_eco" for f in icmp)
    assert pings[0] == ["ping", "-c", "1", "-W", "2000", "atom.invalid"]  # flags de macOS, del sistema declarado
    energia = bt.lee_filas(tmp_path / "energia.jsonl")
    assert energia and energia[0]["ok"] is True and energia[0]["potencia_w"] == 31.5 and energia[0]["tipo"] == "shelly2"
    assert bt.lee_filas(tmp_path / "latido.jsonl")[-1]["cuentas"]["enchufe"] == len(energia)
