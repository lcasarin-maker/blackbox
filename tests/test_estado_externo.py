"""Tests para FEATURE-ESTADO-EXTERNO-UN-SOLO-CANAL-01."""
from __future__ import annotations

import json
import shutil
from pathlib import Path
from types import SimpleNamespace

from tools.estado_externo import (
    ESQUEMA,
    construir_estado_externo,
    evaluar_vigencia,
    medir_deriva_despliegue,
    trae_estado_externo,
)


def test_construir_estado_externo_y_vigencia():
    ahora = 1764192000.0
    doc = construir_estado_externo(
        ts=ahora - 15.0,
        ahora=ahora,
        intervalo_s=30.0,
        procesos={"testigo": {"vivo": True, "edad_s": 4.0}, "alarma": {"vivo": True, "edad_s": 5.0}, "receptor_netconsole": {"vivo": True, "edad_s": 2.0}},
        alarma_caminos={"ssh_casa": True, "ssh_tailscale": True, "rustdesk": True},
        filas_ping=[
            {"fuente": "tcp", "epoch": ahora - 10.0, "ok": True, "rtt_ms": 15.0},
            {"fuente": "icmp", "epoch": ahora - 10.0, "ok": True, "rtt_ms": 12.0},
        ],
        filas_energia=[
            {"epoch": ahora - 60.0, "ok": True, "potencia_w": 50.0, "voltaje_v": 120.0, "corriente_a": 0.42},
            {"epoch": ahora - 10.0, "ok": True, "potencia_w": 50.0, "voltaje_v": 120.0, "corriente_a": 0.42},
        ],
        disco_externo={"ok": True, "volumenes": [{"nombre": "C:", "total_bytes": 1000, "usado_bytes": 400, "libre_bytes": 600}]},
    )
    assert doc["esquema"] == ESQUEMA
    assert doc["vigente"] is True
    assert doc["alarma_caminos"]["completa"] is True
    assert doc["sondeos_5m"]["tcp"]["ok_pct"] == 100.0
    assert doc["sondeos_5m"]["icmp"]["rtt_p50_ms"] == 12.0
    assert doc["enchufe"]["energia_fuente"] == "integrada"

    # Vencido si supera 3 * intervalo_s
    vencido = evaluar_vigencia(doc, ahora=ahora + 120.0)
    assert vencido["vigente"] is False
    assert "vencido" in vencido["motivo_vigencia"]


def test_control_negativo_alarma_incompleta_campos_ausentes_y_scp_cortado(tmp_path):
    ahora = 1764192000.0
    doc = construir_estado_externo(
        ts=ahora - 100.0,
        ahora=ahora,
        intervalo_s=30.0,
        alarma_caminos={"ssh_casa": True, "ssh_tailscale": False, "rustdesk": True},
    )
    assert doc["vigente"] is False
    assert doc["alarma_caminos"]["completa"] is False
    assert doc["enchufe"]["potencia_w"] == "NOT_COLLECTED"
    assert doc["enchufe"]["potencia_w"] != 0

    deriva = medir_deriva_despliegue({"bb_testigo.py": "aaa"}, {"bb_testigo.py": "bbb"}, edad_lectura_s=1.0)
    assert deriva["divergente"] is True

    # SCP cortado conserva archivo bueno previo
    destino = tmp_path / "estado_externo.json"
    destino.write_text(json.dumps({"esquema": ESQUEMA, "ts": "previo"}) + "\n", encoding="utf-8")
    cfg = tmp_path / "testigo.json"
    cfg.write_text(json.dumps({"origen": "user@192.0.2.10", "ruta_estado": "/tmp/e.json"}), encoding="utf-8")

    def _scp_fail(cmd, *a, **kw):
        Path(cmd[-1]).write_text("{corrupto", encoding="utf-8")
        return SimpleNamespace(returncode=1, stdout="", stderr="lost connection")

    res = trae_estado_externo(cfg, destino, correr=_scp_fail, ahora=ahora)
    assert res["estado"] == "COULD_NOT_RUN"
    assert json.loads(destino.read_text(encoding="utf-8"))["ts"] == "previo"

    # SCP valido reemplaza atomicamente
    def _scp_ok(cmd, *a, **kw):
        Path(cmd[-1]).write_text(json.dumps(doc), encoding="utf-8")
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    res_ok = trae_estado_externo(cfg, destino, correr=_scp_ok, ahora=ahora)
    assert res_ok["estado"] == "OK"
    assert json.loads(destino.read_text(encoding="utf-8"))["esquema"] == ESQUEMA
