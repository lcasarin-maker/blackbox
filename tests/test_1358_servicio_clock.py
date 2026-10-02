"""Controles negativos para la sonda opcional y la evidencia de clock lock."""

from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

from tools.service_probe import probe

ROOT = Path(__file__).resolve().parent.parent
BB = ROOT / "bin" / "bb"


def _muestra_con_sonda(tmp_path: Path):
    sample = next((tmp_path / "data" / "samples").glob("*.jsonl"))
    records = [json.loads(line) for line in sample.read_text(encoding="utf-8").splitlines()]
    return next(record for record in reversed(records) if "servicio_ssh" in record)


class _SocketFalso:
    def __init__(self, chunks=(), wait=False, drip=False, clock=None):
        self.clock = clock
        self.chunks = list(chunks)
        self.wait = wait
        self.drip = drip
        self.timeout = 0

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def settimeout(self, value):
        self.timeout = value

    def recv(self, _size):
        if self.drip:
            self.clock[0] += min(0.08, self.timeout / 2)
            return b"x"
        if self.wait:
            self.clock[0] += self.timeout
            raise socket.timeout("no banner")
        if self.chunks:
            return self.chunks.pop(0)
        return b""


def test_puerto_tcp_abierto_sin_banner_ssh_expira_con_timeout_total(monkeypatch):
    clock = [0.0]
    monkeypatch.setattr("tools.service_probe.time.monotonic", lambda: clock[0])
    monkeypatch.setattr("tools.service_probe.socket.create_connection",
                        lambda *_a, **_kw: _SocketFalso(wait=True, clock=clock))
    ini = time.monotonic()
    result = probe("127.0.0.1", "22", "0.2")
    elapsed = time.monotonic() - ini
    assert result["estado"] == "TIMEOUT", result
    assert elapsed < 0.8, elapsed


def test_servidor_que_envia_bytes_lentos_no_extiende_el_timeout_total(monkeypatch):
    clock = [0.0]
    monkeypatch.setattr("tools.service_probe.time.monotonic", lambda: clock[0])
    monkeypatch.setattr("tools.service_probe.socket.create_connection",
                        lambda *_a, **_kw: _SocketFalso(drip=True, clock=clock))
    ini = time.monotonic()
    result = probe("127.0.0.1", "22", "0.2")
    elapsed = time.monotonic() - ini
    assert result["estado"] == "TIMEOUT", result
    assert elapsed < 0.4, elapsed


def test_banner_ssh_completo_es_respuesta_util(monkeypatch):
    monkeypatch.setattr("tools.service_probe.socket.create_connection",
                        lambda *_a, **_kw: _SocketFalso([b"SSH-2.0-test-server\r\n"]))
    result = probe("127.0.0.1", "22", "1")
    assert result["estado"] == "OK", result


def test_prefijo_ssh_sin_terminador_no_se_acepta(monkeypatch):
    monkeypatch.setattr("tools.service_probe.socket.create_connection",
                        lambda *_a, **_kw: _SocketFalso([b"SSH-2.0-test-server"]))
    result = probe("127.0.0.1", "22", "1")
    assert result["estado"] == "ERROR", result


def test_destino_externo_se_rechaza_antes_de_conectar():
    result = probe("192.0.2.1", "22", "1")
    assert result["estado"] == "ERROR"
    assert "loopback" in result["motivo"]


def test_configuracion_no_finita_o_fuera_de_rango_se_rechaza():
    assert probe("127.0.0.1", "22", "nan")["estado"] == "ERROR"
    assert probe("127.0.0.1", "22", "inf")["estado"] == "ERROR"
    assert probe("127.0.0.1", "65536", "1")["estado"] == "ERROR"


def test_identificacion_demasiado_larga_se_rechaza(monkeypatch):
    monkeypatch.setattr("tools.service_probe.socket.create_connection",
                        lambda *_a, **_kw: _SocketFalso([b"SSH-2.0-" + b"a" * 248 + b"\r\n"]))
    assert probe("127.0.0.1", "22", "1")["estado"] == "ERROR"


def test_bb_sample_declara_sonda_desactivada_sin_intentar_red(tmp_path):
    env = dict(os.environ, BLACKBOX_DATA=str(tmp_path / "data"))
    env.pop("BB_SSH_PROBE_PORT", None)
    run = subprocess.run([str(BB), "sample"], env=env, text=True,
                         capture_output=True, timeout=30)
    assert run.returncode == 0, run.stderr
    record = _muestra_con_sonda(tmp_path)
    assert record["servicio_ssh"]["estado"] == "DESACTIVADO"


def test_bb_sample_incluye_resultado_cuando_sonda_loopback_esta_habilitada(tmp_path):
    bindir = tmp_path / "bin"
    bindir.mkdir()
    fake_python = bindir / "python3"
    fake_python.write_text("#!/bin/sh\nprintf '%s\\n' '{\"estado\":\"TIMEOUT\",\"ms\":100}'\n",
                           encoding="utf-8")
    fake_python.chmod(0o755)
    env = dict(os.environ, BLACKBOX_DATA=str(tmp_path / "data"),
               BB_SSH_PROBE_PORT="2222", PATH=f"{bindir}:{os.environ['PATH']}")
    run = subprocess.run([str(BB), "sample"], env=env, text=True,
                         capture_output=True, timeout=30)
    assert run.returncode == 0, run.stderr
    record = _muestra_con_sonda(tmp_path)
    assert record["servicio_ssh"]["estado"] == "TIMEOUT"


def _clock_status(tmp_path: Path, *, declared="300,2800", confirmed="300,2800",
                  confirm_ts: float | None = None, start_offset=0):
    bindir = tmp_path / "bin"
    bindir.mkdir()
    now = time.time()
    start = datetime.fromtimestamp(now + start_offset).strftime("%a %Y-%m-%d %H:%M:%S %Z")
    (bindir / "systemctl").write_text(
        "#!/bin/sh\ncase \"$*\" in\n"
        f"  *ExecStart*) printf '%s\\n' 'ExecStart=/usr/bin/nvidia-smi -lgc {declared}' ;;\n"
        f"  *ExecMainStartTimestamp*) printf '%s\\n' '{start}' ;;\n"
        "esac\n", encoding="utf-8")
    (bindir / "journalctl").write_text(
        "#!/bin/sh\n" + (f"printf '%s\\n' '{confirm_ts:.3f} host atom-clock-lock: "
                           f"GPU clocks set to (gpuClkMin {confirmed.split(',')[0]}, "
                           f"gpuClkMax {confirmed.split(',')[1]})'\n" if confirmed else ""),
        encoding="utf-8")
    for command in ("systemctl", "journalctl"):
        (bindir / command).chmod(0o755)
    env = dict(os.environ, PATH=f"{bindir}:{os.environ['PATH']}")
    run = subprocess.run([str(BB), "status", "clock", "lock"], env=env,
                         text=True, capture_output=True, timeout=10)
    return run


def test_clock_lock_detecta_confirmacion_ausente(tmp_path):
    run = _clock_status(tmp_path, confirmed="", confirm_ts=None)
    assert run.returncode == 1
    assert "FALTA" in run.stdout and "sin declaración o confirmación" in run.stdout


def test_clock_lock_detecta_rango_discrepante(tmp_path):
    run = _clock_status(tmp_path, confirmed="300,2600", confirm_ts=time.time())
    assert run.returncode == 1
    assert "declarado '300,2800', confirmado '300,2600'" in run.stdout


def test_clock_lock_detecta_confirmacion_vieja_tras_reinicio_de_unit(tmp_path):
    run = _clock_status(tmp_path, confirm_ts=time.time() - 120, start_offset=-60)
    assert run.returncode == 1
    assert "anterior al inicio actual" in run.stdout


def test_clock_lock_confirma_aplicacion_tras_inicio_sin_prometer_clock_actual(tmp_path):
    now = time.time()
    run = _clock_status(tmp_path, confirm_ts=now + 30)
    assert run.returncode == 0
    assert "ARMADO" in run.stdout
    assert "no mide el clock actual" in run.stdout


def test_bb_sample_symlink_resolves_probe_from_real_repository(tmp_path):
    alias = tmp_path / "bb"
    alias.symlink_to(BB)
    env = dict(os.environ, BLACKBOX_DATA=str(tmp_path / "data"),
               BB_SSH_PROBE_PORT="invalid")
    run = subprocess.run([str(alias), "sample"], env=env, text=True,
                         capture_output=True, timeout=30)
    assert run.returncode == 0, run.stderr
    assert _muestra_con_sonda(tmp_path)["servicio_ssh"]["motivo"] == "dirección, puerto o timeout inválido"
