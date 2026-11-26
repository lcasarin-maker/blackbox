"""Tests para FEATURE-TESTIGO-RTT-EN-FILAS-ICMP-01."""
from __future__ import annotations

import subprocess
from types import SimpleNamespace

from tools.testigo.bb_testigo import sondea_icmp


def _run_ok(stdout: str):
    return lambda *a, **kw: SimpleNamespace(returncode=0, stdout=stdout.encode("utf-8"), stderr=b"")


def _run_fail(stdout: str = ""):
    return lambda *a, **kw: SimpleNamespace(returncode=1, stdout=stdout.encode("utf-8"), stderr=b"")


def test_sondea_icmp_con_rtt_linux_y_windows():
    f_linux = sondea_icmp(
        "192.0.2.10",
        "linux",
        1.0,
        correr=_run_ok("64 bytes from 192.0.2.10: icmp_seq=1 ttl=64 time=14.6 ms\n"),
    )
    assert f_linux["ok"] is True
    assert f_linux["rtt_ms"] == 14.6
    assert "rtt_motivo" not in f_linux

    f_win = sondea_icmp(
        "192.0.2.10",
        "win32",
        1.0,
        correr=_run_ok("Respuesta desde 192.0.2.10: bytes=32 tiempo<1ms TTL=64\n"),
    )
    assert f_win["ok"] is True
    assert f_win["rtt_ms"] == 0.5


def test_sondea_icmp_sin_rtt_parseable_devuelve_none_nunca_cero():
    f = sondea_icmp("192.0.2.10", "linux", 1.0, correr=_run_ok("1 packets transmitted, 1 received\n"))
    assert f["ok"] is True
    assert f["rtt_ms"] is None
    assert f["rtt_ms"] != 0
    assert f["rtt_motivo"] == "sin_rtt_en_salida"


def test_sondea_icmp_fallido_y_error_sin_rtt_inventado():
    f_fail = sondea_icmp("192.0.2.10", "linux", 1.0, correr=_run_fail(""))
    assert f_fail["ok"] is False
    assert f_fail["rtt_ms"] is None

    def _boom(*a, **kw):
        raise subprocess.TimeoutExpired(cmd="ping", timeout=1)

    f_err = sondea_icmp("192.0.2.10", "linux", 1.0, correr=_boom)
    assert f_err["ok"] is False
    assert f_err["rtt_ms"] is None
