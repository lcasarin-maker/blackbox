"""Cierre de DEBT-GUARDIA-PROCESO-NO-FRENA-SIN-UID-01.

Si /proc/<pid>/status no es legible pero el dueno se puede leer de /proc/<pid> (stat), el guardia
debe poder actuar sobre un proceso del mismo usuario. Antes se negaba: "no se pudo leer ... no se toca".
Las pruebas de abajo son los controles negativos: root, PID 1, pid inexistente y otro usuario siguen
intocables por la via de respaldo.
"""
import importlib.machinery
import importlib.util
import os
import pathlib
import signal
import subprocess
import sys

from unittest import mock

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
GUARDIA = ROOT / "bin" / "bb-guardia-proceso"
_KILL_REAL = os.kill  # el fixture `hijo` se desmonta mientras os.kill sigue espiado


def _cargar():
    # @dataclass resuelve su modulo en sys.modules: sin registrarlo, exec_module revienta con
    # AttributeError y la prueba falla por el cargador, no por el guardia.
    loader = importlib.machinery.SourceFileLoader("bb_guardia_proceso", str(GUARDIA))
    spec = importlib.util.spec_from_loader("bb_guardia_proceso", loader)
    modulo = importlib.util.module_from_spec(spec)
    sys.modules["bb_guardia_proceso"] = modulo
    try:
        loader.exec_module(modulo)
    finally:
        del sys.modules["bb_guardia_proceso"]
    return modulo


@pytest.fixture
def guardia(tmp_path, monkeypatch):
    monkeypatch.delenv("BB_GUARDIA_DRY_RUN", raising=False)
    monkeypatch.setenv("BLACKBOX_DATA", str(tmp_path))
    modulo = _cargar()
    monkeypatch.setattr(modulo, "EVIDENCIA", tmp_path / "guardia_proceso.jsonl")
    return modulo


@pytest.fixture
def hijo():
    """Proceso real del mismo usuario, para que el stat de /proc/<pid> sea el de verdad."""
    proc = subprocess.Popen(["sleep", "30"])
    yield proc.pid
    _KILL_REAL(proc.pid, signal.SIGKILL)
    proc.wait()


def _pid_inexistente():
    pid_max = int(pathlib.Path("/proc/sys/kernel/pid_max").read_text(encoding="ascii"))
    return pid_max + 1  # el kernel nunca asigna un pid por encima de pid_max


def test_guardia_resuelve_dueno_sin_status_legible():
    guardia = _cargar()
    pid_ajeno = os.getppid()
    with mock.patch.object(guardia, "_uid_de", return_value=None):
        motivo = guardia._es_intocable(pid_ajeno, "python3")
    assert motivo is None or "no se pudo leer" not in motivo


def test_mismo_usuario_sin_status_es_tocable_por_stat_real(guardia, monkeypatch, hijo):
    """El caso que DEBE actuar: status ilegible, dueno resuelto por el stat real de /proc/<pid>."""
    monkeypatch.setattr(guardia, "_uid_de", lambda pid: None)
    assert guardia._es_intocable(hijo, "sleep") is None


def test_mismo_usuario_sin_status_recibe_la_senal(guardia, monkeypatch, hijo):
    monkeypatch.setattr(guardia, "_uid_de", lambda pid: None)
    espia = mock.MagicMock()
    monkeypatch.setattr(os, "kill", espia)
    guardia._enviar_senal(guardia.Proceso(hijo, "sleep", 1024), "prueba", "term", signal.SIGTERM)
    espia.assert_called_once_with(hijo, signal.SIGTERM)


# ------------------------------------------------ (a) root sigue intocable, con y sin status


def test_root_con_status_legible_sigue_intocable(guardia, monkeypatch):
    monkeypatch.setattr(guardia, "_uid_de", lambda pid: 0)
    monkeypatch.setattr(guardia, "_uid_por_stat", lambda pid: os.getuid())
    motivo = guardia._es_intocable(999999, "python3")
    assert motivo is not None and "root" in motivo


def test_root_sin_status_sigue_intocable_por_stat(guardia, monkeypatch):
    monkeypatch.setattr(guardia, "_uid_de", lambda pid: None)
    monkeypatch.setattr(guardia, "_uid_por_stat", lambda pid: 0)
    motivo = guardia._es_intocable(999999, "python3")
    assert motivo is not None and "root" in motivo


def test_root_real_sin_status_sigue_intocable(guardia, monkeypatch):
    """kthreadd (pid 2) es de root; su stat real tiene que dar uid 0 y bloquear."""
    if not os.path.isdir("/proc/2") or os.stat("/proc/2").st_uid != 0:
        pytest.skip("no hay pid 2 de root en este espacio de pids")
    monkeypatch.setattr(guardia, "_uid_de", lambda pid: None)
    motivo = guardia._es_intocable(2, "kthreadd")
    assert motivo is not None and "root" in motivo


# ------------------------------------------------ (b) PID 1 y el propio guardian


@pytest.mark.parametrize("uid_status", [None, 1000])
def test_pid_1_sigue_intocable(guardia, monkeypatch, uid_status):
    monkeypatch.setattr(guardia, "_uid_de", lambda pid: uid_status)
    monkeypatch.setattr(guardia, "_uid_por_stat", lambda pid: os.getuid())
    assert guardia._es_intocable(1, "python3") == "PID 1 o el propio guardian"


def test_propio_guardian_sigue_intocable_sin_status(guardia, monkeypatch):
    monkeypatch.setattr(guardia, "_uid_de", lambda pid: None)
    assert guardia._es_intocable(os.getpid(), "python3") == "PID 1 o el propio guardian"


# ------------------------------------------------ (c) pid inexistente: no se toca


def test_pid_inexistente_no_se_toca(guardia):
    """Sin mocks: status y stat reales fallan los dos."""
    motivo = guardia._es_intocable(_pid_inexistente(), "python3")
    assert motivo is not None and "no se pudo leer" in motivo


def test_pid_inexistente_no_recibe_senal(guardia, monkeypatch):
    espia = mock.MagicMock()
    monkeypatch.setattr(os, "kill", espia)
    guardia._enviar_senal(guardia.Proceso(_pid_inexistente(), "python3", 1024),
                          "prueba", "kill", signal.SIGKILL)
    espia.assert_not_called()


# ------------------------------------------------ otro usuario por la via de respaldo


def test_otro_usuario_por_stat_no_se_toca(guardia, monkeypatch):
    monkeypatch.setattr(guardia, "_uid_de", lambda pid: None)
    monkeypatch.setattr(guardia, "_uid_por_stat", lambda pid: os.getuid() + 1)
    motivo = guardia._es_intocable(999999, "python3")
    assert motivo is not None and "no es el usuario del guardian" in motivo
