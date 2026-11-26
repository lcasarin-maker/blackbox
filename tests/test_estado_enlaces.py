"""Tests para FEATURE-ESTADO-ENLACES-TAILSCALE-Y-RUSTDESK-01."""
from __future__ import annotations

import json
import subprocess
from types import SimpleNamespace

from tools.estado_enlaces import evaluar_alertas_enlaces, lee_rustdesk, lee_tailscale


def _runner(mapping: dict[str, tuple[int, str]]):
    def _run(cmd, *a, **kw):
        key = cmd[0]
        rc, out = mapping[key]
        return SimpleNamespace(returncode=rc, stdout=out, stderr="")
    return _run


def test_tailscale_y_rustdesk_sanitizan_y_detectan_degradacion(tmp_path):
    payload = {
        "Self": {"HostName": "host-real-privado", "Online": True, "RxBytes": 100, "TxBytes": 200},
        "Peer": {
            "p1": {"HostName": "equipo-privado", "Online": True, "CurAddr": "", "Relay": "dfw", "RxBytes": 10, "TxBytes": 20},
            "p2": {"HostName": "portatil", "Online": False, "CurAddr": "", "Relay": "", "RxBytes": 0, "TxBytes": 0},
        },
    }
    ts = lee_tailscale(correr=_runner({"tailscale": (0, json.dumps(payload))}))
    assert ts["estado"] == "OK"
    assert ts["malla_estado"] == "degradada"
    texto = json.dumps(ts)
    assert "host-real-privado" not in texto
    assert "equipo-privado" not in texto
    assert any(d["camino"] == "relay" for d in ts["dispositivos"])
    assert any(d["online"] is False for d in ts["dispositivos"])

    rd = lee_rustdesk(correr=_runner({"systemctl": (0, "active\n"), "ss": (0, "LISTEN 0 128 0.0.0.0:21118\n")}))
    assert rd["estado"] == "OK"
    assert rd["servicio_activo"] is True
    assert rd["puerto_escucha"] is True

    # Rafaga unica de alertas
    st_file = tmp_path / "enlaces_alertas.json"
    estado = {"tailscale": ts, "rustdesk": rd}
    assert len(evaluar_alertas_enlaces(estado, st_file)) == 1
    assert evaluar_alertas_enlaces(estado, st_file) == []


def test_control_negativo_fallo_nunca_es_sana():
    def _boom(*a, **kw):
        raise subprocess.TimeoutExpired(cmd="tailscale", timeout=5)

    ts = lee_tailscale(correr=_boom)
    assert ts["estado"] == "COULD_NOT_RUN"
    assert ts["malla_estado"] == "COULD_NOT_RUN"

    rd = lee_rustdesk(correr=_runner({"systemctl": (3, "inactive\n"), "ss": (1, "")}))
    assert rd["estado"] == "COULD_NOT_RUN"
