"""Alarma de GPU en Reset Required: deteccion con control negativo, idempotencia por boot_id, reintento sin sesion."""

import json

import pytest

from tools import aviso_gpu_reset as ag

pytestmark = pytest.mark.unit

CON = [
    "[   24.390647] host kernel: NVRM: _issueRpcAndWait: rpcRecvPoll timedout",
    "[   38.100000] host kernel: NVRM: Xid (PCI:000f:01:00): 154, GPU recovery action changed from 0x0 (None) to 0x1 (GPU Reset Required)",
]
SIN = [
    "[    1.000000] host kernel: NVRM: loading NVIDIA UNIX Open Kernel Module",
    "[   30.0] host kernel: NVRM: Xid (PCI:000f:01:00): 13, graphics exception",
]


def test_detecta_la_secuencia_y_no_otros_xid():
    assert ag.hechos(CON)["detectado"] is True
    assert ag.hechos(CON[:1])["detectado"] is True  # solo el timeout
    assert ag.hechos(CON[1:])["detectado"] is True  # solo el Xid 154
    assert ag.hechos(SIN)["detectado"] is False  # el control: Xid 13 no es 154
    assert ag.hechos([])["detectado"] is False


def _corre(monkeypatch, tmp_path, lineas, envia=True):
    monkeypatch.setattr(ag, "RUTA", tmp_path / "a.jsonl")
    monkeypatch.setattr(ag, "lee_journal", lambda b: lineas)
    enviados = []
    monkeypatch.setattr(
        ag.aviso_termico, "enviar", lambda av: enviados.append(av) or envia
    )
    return ag.main([]), enviados


def test_una_vez_por_arranque(monkeypatch, tmp_path):
    assert _corre(monkeypatch, tmp_path, CON)[1] != []
    rc, enviados = _corre(monkeypatch, tmp_path, CON)
    assert rc == 0 and enviados == []  # segunda corrida: ya anotado
    filas = [json.loads(ln) for ln in (tmp_path / "a.jsonl").read_text().splitlines()]
    assert len(filas) == 1 and filas[0]["xid154"] is True


def test_sin_secuencia_no_avisa_ni_anota(monkeypatch, tmp_path):
    rc, enviados = _corre(monkeypatch, tmp_path, SIN)
    assert rc == 0 and enviados == [] and not (tmp_path / "a.jsonl").exists()


def test_aviso_fallido_no_anota_y_reintenta(monkeypatch, tmp_path):
    rc, _ = _corre(monkeypatch, tmp_path, CON, envia=False)
    assert rc == 1 and not (tmp_path / "a.jsonl").exists()
    assert (
        _corre(monkeypatch, tmp_path, CON)[0] == 0 and (tmp_path / "a.jsonl").exists()
    )


def test_journal_caido_es_could_not_run_no_limpio(monkeypatch, tmp_path):
    rc, enviados = _corre(monkeypatch, tmp_path, None)
    assert rc == 2 and enviados == []
