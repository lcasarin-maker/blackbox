"""De extremo a extremo: los productores REALES escriben un arranque que muere y `reboot_verdict` lo lee.

Ningun archivo de entrada es una fixture escrita a mano. Cada productor corre su propio codigo:
  - adopted/system-units/etapa-marca.sh (bash) con sus costuras BB_ETAPA_*, hasta `basic`;
  - tools/ultimo_aliento.py como proceso, con /proc y /sys falsos (--raiz) y la temperatura subiendo; muere con
    SIGKILL, como en un corte: sin evento `parada`;
  - tools/testigo/bb_testigo.py (`Testigo.corre`) contra un puerto TCP de loopback que deja de contestar (cola de
    accept llena: `timeout` real, no un RST) y un Shelly Gen1 falso por la costura `abre` (sin voltaje);
  - observador_ping.trae_testigo trae esas series a `externo/testigo/` por la costura `correr` (copia local en lugar
    de scp: aqui no hay sshd).
Lo unico falso es el journal (`journalctl --list-boots` y la cola del boot), porque el contenedor no tiene los boots.
Las horas son las reales de cada productor ($EPOCHREALTIME, time.time()): el journal falso se arma alrededor de ellas.
"""

from __future__ import annotations

import fnmatch
import json
import os
import shutil
import signal
import socket
import subprocess
import sys
import threading
import time
import types
import uuid
from pathlib import Path
from typing import Any

import pytest

from tools import observador_ping, reboot_verdict as rv, ultimo_aliento
from tools.testigo import bb_testigo as bt

RAIZ_REPO = Path(__file__).resolve().parent.parent
MARCA = RAIZ_REPO / "adopted" / "system-units" / "etapa-marca.sh"
# ~7 s por escenario (los productores corren en tiempo real): fuera del carril por defecto, `pytest -m e2e` lo corre
pytestmark = [pytest.mark.e2e, pytest.mark.skipif(shutil.which("bash") is None, reason="etapa-marca.sh exige bash")]


class Atom:
    """El puerto 22 de la ATOM en loopback: contesta mientras vive y, al morir, deja de completar el handshake."""

    def __init__(self) -> None:
        self.viva = socket.socket()
        self.viva.bind(("127.0.0.1", 0))
        self.viva.listen(64)
        self.puerto = self.viva.getsockname()[1]
        threading.Thread(target=self._acepta, daemon=True).start()
        # cola de accept de 1 y llena: el kernel descarta el SYN siguiente y el sondeo acaba en timeout
        self.muerta = socket.socket()
        self.muerta.bind(("127.0.0.1", 0))
        self.muerta.listen(0)
        self._llenan = []
        for _ in range(3):
            c = socket.socket()
            c.setblocking(False)
            try:
                c.connect(self.muerta.getsockname())
            except BlockingIOError:
                pass
            self._llenan.append(c)
        time.sleep(0.2)
        self.puerto_muerto = self.muerta.getsockname()[1]

    def _acepta(self) -> None:
        while True:
            try:
                c, _ = self.viva.accept()
            except OSError:
                return
            c.close()

    def cierra(self) -> None:
        for s in (self.viva, self.muerta, *self._llenan):
            s.close()


def _raiz_falsa(raiz: Path, boot_dashed: str) -> Path:
    for rel, texto in {
        "proc/sys/kernel/random/boot_id": boot_dashed + "\n",
        "proc/uptime": "3.91 1.20\n",
        "proc/pressure/cpu": "some avg10=1.00 avg60=0.50 avg300=0.10 total=100\n",
        "proc/pressure/memory": "some avg10=0.00 avg60=0.00 avg300=0.00 total=1\nfull avg10=0.00 avg60=0.00 avg300=0.00 total=1\n",
        "proc/pressure/io": "some avg10=0.10 avg60=0.00 avg300=0.00 total=5\nfull avg10=0.00 avg60=0.00 avg300=0.00 total=1\n",
        "proc/meminfo": "MemFree: 4000000 kB\nMemAvailable: 90000000 kB\nSwapTotal: 0 kB\nSwapFree: 0 kB\nDirty: 120 kB\n",
        "proc/loadavg": "3.00 2.00 1.00 2/900 4242\n",
        "sys/class/thermal/thermal_zone0/type": "gpu-thermal\n",
        "sys/class/thermal/thermal_zone0/temp": "70000\n",
        "sys/class/thermal/thermal_zone0/trip_point_0_temp": "100000\n",
        "sys/class/thermal/thermal_zone0/trip_point_0_type": "critical\n",
    }.items():
        (raiz / rel).parent.mkdir(parents=True, exist_ok=True)
        (raiz / rel).write_text(texto, encoding="ascii")
    return raiz / "sys/class/thermal/thermal_zone0/temp"


def _marca(etapa: str, raiz: Path, etapas_dir: Path) -> None:
    env = {**os.environ, "BB_ETAPA_DIR": str(etapas_dir), "BB_ETAPA_KMSG": str(raiz / "kmsg"),
           "BB_ETAPA_BOOT_ID": str(raiz / "proc/sys/kernel/random/boot_id"), "BB_ETAPA_UPTIME": str(raiz / "proc/uptime")}
    r = subprocess.run(["bash", str(MARCA), etapa], env=env, capture_output=True, text=True, timeout=30, check=False)
    assert r.returncode == 0 and r.stderr == "", r.stderr


def _scp_local(cmd: list[str], **kw: Any) -> Any:
    """La costura de transporte de trae_testigo: hace lo que scp haria, con los mismos argumentos."""
    origen, destino = cmd[-2], Path(cmd[-1])
    directorio, patron = origen.split(":", 1)[1].rsplit("/", 1)
    for p in Path(directorio).iterdir():
        if fnmatch.fnmatch(p.name, patron):
            shutil.copy2(p, destino / p.name)
    return types.SimpleNamespace(returncode=0, stdout="", stderr="")


def _produce(tmp_path: Path, escenario: str) -> dict[str, Any]:
    """Corre los productores para un arranque `A` que muere segun `escenario` (corte, cuelgue o fallo)."""
    boot_a = str(uuid.uuid4())
    raiz = tmp_path / "raiz"
    temp = _raiz_falsa(raiz, boot_a)
    etapas_dir = tmp_path / "var/lib/blackbox/arranque"
    etapas_dir.parent.parent.mkdir(parents=True)  # /var/lib existe; los dos niveles de abajo los crea etapa-marca.sh
    inicio = time.time() - 1.0
    for etapa in ("local-fs", "basic"):
        _marca(etapa, raiz, etapas_dir)
    anillo = tmp_path / "var/lib/bb-ultimo-aliento/anillo.bin"
    aliento = subprocess.Popen(
        [sys.executable, "-I", str(RAIZ_REPO / "tools/ultimo_aliento.py"), "--raiz", str(raiz), "--anillo", str(anillo),
         "--estado-ruta", str(tmp_path / "run/estado_maquina.json"), "--intervalo", "0.25"],
        stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True,
    )
    vivo = threading.Event()
    vivo.set()

    def calienta() -> None:  # la zona sube 1 C cada 250 ms mientras la ATOM vive
        c = 70
        while vivo.is_set():
            temp.write_text(f"{c * 1000}\n", encoding="ascii")
            c += 1
            time.sleep(0.25)

    threading.Thread(target=calienta, daemon=True).start()
    atom = Atom()
    enchufe = {"w": 30.0}  # Shelly Gen1: solo `meters[].power`, sin voltaje
    cfg = bt.valida_config({"atom_host": "127.0.0.1", "atom_puerto": atom.puerto_muerto if escenario == "fallo" else atom.puerto,
                            "tcp_timeout_s": 0.3, "sondeo_s": 0.2, "icmp": False, "udp_bind": "127.0.0.1", "udp_puerto": 0,
                            "enchufe_tipo": "shelly1", "enchufe_url": "http://192.0.2.30", "enchufe_s": 0.2, "latido_s": 0.5})
    datos = tmp_path / "equipo-testigo/bb-testigo"
    testigo = bt.Testigo(cfg, datos, sistema="linux", abre=lambda url: json.dumps({"meters": [{"power": enchufe["w"]}]}).encode())
    hilo = threading.Thread(target=testigo.corre, daemon=True)
    hilo.start()
    time.sleep(2.0)  # el arranque vive: TCP contesta, 30 W, el anillo muestrea
    fin = time.time() - 0.1  # la ultima linea del journal, justo antes de morir
    if escenario == "corte":
        enchufe["w"] = 0.0  # se va la energia: el enchufe mide ~0 W un instante antes de que caiga el TCP
        time.sleep(0.3)
    aliento.send_signal(signal.SIGKILL)  # muere como en un corte: sin evento `parada`
    vivo.clear()
    testigo.cfg["atom_puerto"] = atom.puerto_muerto
    muerte = time.time()
    time.sleep(2.5)  # el testigo sigue: fallas de TCP, el enchufe (30 W o 0 W) y su latido
    testigo.parar.set()
    hilo.join(timeout=10)
    atom.cierra()
    aliento.wait(timeout=10)
    siguiente = time.time() + 0.5
    datos_atom = tmp_path / "blackbox-data"
    (datos_atom / "externo").mkdir(parents=True)
    cfg_trae = datos_atom / "externo" / "testigo.json"
    cfg_trae.write_text(json.dumps({"origen": "luis@127.0.0.1", "ruta": str(datos)}), encoding="utf-8")
    traido = observador_ping.trae_testigo(cfg_trae, datos_atom / "externo" / "testigo", correr=_scp_local)
    assert traido["estado"] == "OK" and {"ping.jsonl", "energia.jsonl", "latido.jsonl"} <= set(traido["archivos"])
    return {"boot": boot_a.replace("-", ""), "inicio": inicio, "fin": fin, "muerte": muerte, "siguiente": siguiente,
            "etapas": etapas_dir / "etapas.jsonl", "anillo": anillo, "externo": datos_atom / "externo", "tmp": tmp_path}


def _veredicto(monkeypatch: pytest.MonkeyPatch, p: dict[str, Any], boot: str | None = None,
               desplaza_s: float = 0.0) -> list[dict[str, Any]]:
    """Las filas de `reboot_verdict.main` sobre los archivos producidos. `boot`/`desplaza_s` cambian SOLO el journal falso."""
    tmp = p["tmp"]
    boots = [
        {"index": -1, "boot_id": boot or p["boot"], "first_entry": int((p["inicio"] - desplaza_s) * 1e6),
         "last_entry": int((p["fin"] - desplaza_s) * 1e6)},
        {"index": 0, "boot_id": uuid.uuid4().hex, "first_entry": int((p["siguiente"] - desplaza_s) * 1e6),
         "last_entry": int((p["siguiente"] + 60) * 1e6)},
    ]
    cola = time.strftime("%Y-%m-%dT%H:%M:%S+0000", time.gmtime(p["fin"] - desplaza_s)) + " atom kernel: linea normal\n"

    def journal(*args: str) -> Any:
        if "--list-boots" in args:
            return types.SimpleNamespace(returncode=0, stdout=json.dumps(boots), stderr="")
        return types.SimpleNamespace(returncode=0, stdout=cola if "500" in args else "", stderr="")

    salida = tmp / f"reboots-{boot or 'propio'}-{desplaza_s:g}.jsonl"
    for nombre, valor in {"ETAPAS": p["etapas"], "ANILLO": p["anillo"], "EXTERNO": p["externo"], "SALIDA": salida,
                          "PSTORE_DIR": tmp / "sin_pstore", "TELEMETRIA": tmp / "sin_telemetria.jsonl",
                          "CRASH_DIR": tmp / "sin_crash", "WATCHDOG_BOOTSTATUS": tmp / "sin_bootstatus",
                          "_journal": journal, "_correr_con_codigo": lambda *a: (1, "smartctl ausente"),
                          "_publica_hallazgos": lambda filas: None}.items():
        monkeypatch.setattr(rv, nombre, valor)
    assert rv.main(["--ultimos", "1", "--escribe"]) == 0
    return [json.loads(x) for x in salida.read_text(encoding="utf-8").splitlines()]


def _comunes(f: dict[str, Any], p: dict[str, Any], techo: str = "ping", incertidumbre_max_s: float = 3.5) -> None:
    """Lo que todo escenario debe traer: etapas reales, curva termica del anillo real y hora de muerte acotada."""
    assert f["boot_id"] == p["boot"] and f["esquema"] == "bb-reboot/1"
    et = f["etapas"]
    assert et["alcanzadas"] == ["local-fs", "basic"] and et["fuente"] == f"{p['etapas']}:2"
    assert et["monotonic"] == {"local-fs": 3.91, "basic": 3.91}  # los segundos de /proc/uptime, tal cual
    assert p["inicio"] <= et["ultima_epoch"] <= p["fin"]  # realtime: $EPOCHREALTIME en segundos epoch
    curva = f["curva_termica_previa"]
    assert curva and len(curva) >= 2 and curva[0]["termica"]["0"] < curva[-1]["termica"]["0"]
    assert f["ultimo_aliento"]["boot"] == p["boot"] and f["ultimo_aliento"]["tipo"] == "muestra"
    assert f["ultimo_aliento"]["temp_c"] == curva[-1]["termica"]
    h = f["hora_muerte"]
    assert h["cota_superior_epoch"] is not None and h["ultima_senal_epoch"] <= p["muerte"] + 0.5
    assert h["cota_superior_fuente"] == techo and h["cota_superior_epoch"] >= p["muerte"] - 0.5
    assert h["incertidumbre_s"] < incertidumbre_max_s
    sin_leer = " | ".join(f["could_not_run"])
    for fuente in ("anillo_ultimo_aliento", "etapas_arranque", "observador_externo"):
        assert fuente not in sin_leer, f["could_not_run"]


def test_corte_de_energia_el_enchufe_cae_a_0_w_antes_que_el_tcp(tmp_path, monkeypatch):
    p = _produce(tmp_path, "corte")
    [f] = _veredicto(monkeypatch, p)
    _comunes(f, p)
    assert f["etiqueta"] == "CORTE_ABRUPTO" and f["causa"] == "CORTE_DE_ENERGIA"
    testigo = p["externo"] / "testigo"
    assert f"{testigo / 'energia.jsonl'}:" in f["causa_fuente"] and str(testigo / "ping.jsonl") in f["causa_fuente"]
    enc = f["tiempos_externos"]["enchufe"]
    assert enc["falla_por"] == "potencia" and enc["primera_falla"] <= f["tiempos_externos"]["ping"]["primera_falla"]
    assert any("sin voltaje medido" in r for r in f["razones"])  # se decidio por potencia y lo dice
    assert any("decidido por potencia" in r for r in f["razones"])  # el medidor de la ventana tambien
    assert f["tiempos_externos"]["latido"]["en_el_hueco"] > 0  # el testigo siguio vivo: su silencio no es suyo


def test_cuelgue_el_tcp_cae_y_el_enchufe_sigue_en_30_w(tmp_path, monkeypatch):
    p = _produce(tmp_path, "cuelgue")
    [f] = _veredicto(monkeypatch, p)
    _comunes(f, p)
    assert f["etiqueta"] == "CORTE_ABRUPTO" and f["causa"] == "CUELGUE"
    testigo = p["externo"] / "testigo"
    assert str(testigo / "ping.jsonl") in f["causa_fuente"] and str(testigo / "energia.jsonl") in f["causa_fuente"]
    tras = f["tiempos_externos"]["enchufe"]["tras_caida_tcp"]
    assert tras and all(r["potencia_w"] == 30.0 and r["voltaje_v"] is None for r in tras)
    assert any("sin voltaje: decide la potencia" in r for r in f["razones"])
    # control negativo: el mismo veredicto sobre un arranque distinto (otro boot_id, una hora antes) no ve nada de esto
    [otro] = _veredicto(monkeypatch, p, boot=uuid.uuid4().hex, desplaza_s=3600)
    assert (otro["etiqueta"], otro["causa"], otro["causa_fuente"]) == ("CORTE_ABRUPTO", "INDETERMINADO", None)
    assert otro["etapas"] is None and otro["curva_termica_previa"] is None and otro["hora_muerte"]["fuente"] == "journal"
    assert "observador_externo" in otro["could_not_run"]


def test_fallo_de_arranque_en_basic_sin_red_y_con_consumo(tmp_path, monkeypatch):
    p = _produce(tmp_path, "fallo")
    [f] = _veredicto(monkeypatch, p)
    _comunes(f, p, techo="arranque_siguiente", incertidumbre_max_s=10.0)
    assert f["etiqueta"] == "CORTE_ABRUPTO" and f["causa"] == "FALLO_DE_ARRANQUE_EN_BASIC"
    assert f["causa_fuente"].startswith(f"{p['etapas']}:2")
    assert f["tiempos_externos"]["ping"]["ultima_respuesta"] is None  # la ATOM no contesto nunca en este arranque
    assert any("nunca a 'multi-user'" in r for r in f["razones"])
    # control negativo: la MISMA ventana con otro boot_id en el journal. Las etapas y el anillo son de A, no de ese
    # boot: el sale INDETERMINADO, y A (con etapas y sin journal) aparece como arranque fantasma con SU causa.
    otro_id = uuid.uuid4().hex
    otro, fantasma = _veredicto(monkeypatch, p, boot=otro_id)
    assert otro["boot_id"] == otro_id and otro["boot_id_siguiente"] == p["boot"]
    assert otro["causa"] == "INDETERMINADO" and otro["etapas"] is None and otro["curva_termica_previa"] is None
    assert "etapas_arranque (sin filas para este boot)" in otro["could_not_run"]
    assert fantasma["boot_id"] == p["boot"] and fantasma["arranque_fantasma"] is True and fantasma["boot_idx"] is None
    assert fantasma["causa"] == "FALLO_DE_ARRANQUE_EN_BASIC" and fantasma["curva_termica_previa"]
