#!/usr/bin/env python3
"""Estado de Tailscale y RustDesk (FEATURE-ESTADO-ENLACES-TAILSCALE-Y-RUSTDESK-01).

Sólo lectura. Sanitiza nombres de red y omite IPs privadas, usuarios e identificadores
de RustDesk. Ante fallo de lectura devuelve `COULD_NOT_RUN`, nunca `"sana"`.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Callable

Correr = Callable[..., Any]
UMBRAL_OFFLINE_S_DEFECTO = 7 * 86400.0


def lee_tailscale(
    correr: Correr = subprocess.run,
    umbral_offline_s: float = UMBRAL_OFFLINE_S_DEFECTO,
    ahora: float | None = None,
) -> dict[str, Any]:
    try:
        r = correr(["tailscale", "status", "--json"], capture_output=True, text=True, check=False, timeout=10)
    except (OSError, subprocess.SubprocessError) as e:
        return {"estado": "COULD_NOT_RUN", "malla_estado": "COULD_NOT_RUN", "causa": type(e).__name__, "dispositivos": []}
    if r.returncode != 0:
        return {
            "estado": "COULD_NOT_RUN",
            "malla_estado": "COULD_NOT_RUN",
            "causa": f"tailscale rc={r.returncode}",
            "dispositivos": [],
        }
    try:
        data = json.loads(r.stdout or "{}")
    except ValueError as e:
        return {"estado": "COULD_NOT_RUN", "malla_estado": "COULD_NOT_RUN", "causa": f"json invalido: {e}", "dispositivos": []}

    dispositivos: list[dict[str, Any]] = []
    degradada = False

    self_node = data.get("Self")
    if isinstance(self_node, dict):
        dispositivos.append(
            {
                "etiqueta": "nodo-local",
                "online": bool(self_node.get("Online", True)),
                "camino": "local",
                "rx_bytes": int(self_node.get("RxBytes") or 0),
                "tx_bytes": int(self_node.get("TxBytes") or 0),
            }
        )

    peers = data.get("Peer") or {}
    for idx, (_key, peer) in enumerate(sorted(peers.items()), start=1):
        if not isinstance(peer, dict):
            continue
        online = bool(peer.get("Online", False))
        cur_addr = str(peer.get("CurAddr") or "").strip()
        relay = str(peer.get("Relay") or "").strip()
        if not online:
            camino = "offline"
        elif cur_addr:
            camino = "direct"
        elif relay:
            camino = "relay"
            degradada = True
        else:
            camino = "inactivo"

        last_seen_s = peer.get("LastSeen")
        if not online:
            degradada = True

        dispositivos.append(
            {
                "etiqueta": f"par-{idx}",
                "online": online,
                "camino": camino,
                "last_seen": last_seen_s,
                "rx_bytes": int(peer.get("RxBytes") or 0),
                "tx_bytes": int(peer.get("TxBytes") or 0),
            }
        )

    return {
        "estado": "OK",
        "malla_estado": "degradada" if degradada else "sana",
        "dispositivos": dispositivos,
    }


def lee_rustdesk(
    correr: Correr = subprocess.run,
    puerto_control: int = 21118,
    alarma_ok: bool | None = None,
) -> dict[str, Any]:
    try:
        r_svc = correr(
            ["systemctl", "is-active", "rustdesk"],
            capture_output=True,
            text=True,
            check=False,
            timeout=5,
        )
        servicio_activo = r_svc.returncode == 0 and (r_svc.stdout or "").strip() == "active"
    except (OSError, subprocess.SubprocessError) as e:
        return {"estado": "COULD_NOT_RUN", "causa": f"systemctl: {type(e).__name__}", "servicio_activo": False, "puerto_escucha": False}

    try:
        r_ss = correr(
            ["ss", "-ltnH", f"sport = :{puerto_control}"],
            capture_output=True,
            text=True,
            check=False,
            timeout=5,
        )
        if r_ss.returncode != 0:
            return {"estado": "COULD_NOT_RUN", "causa": f"ss rc={r_ss.returncode}", "servicio_activo": servicio_activo, "puerto_escucha": False}
        puerto_escucha = bool((r_ss.stdout or "").strip())
    except (OSError, subprocess.SubprocessError) as e:
        return {"estado": "COULD_NOT_RUN", "causa": f"ss: {type(e).__name__}", "servicio_activo": servicio_activo, "puerto_escucha": False}

    return {
        "estado": "OK",
        "servicio_activo": servicio_activo,
        "puerto_escucha": puerto_escucha,
        "alarma_ok": alarma_ok,
    }


def evaluar_alertas_enlaces(
    estado: dict[str, Any],
    estado_path: Path | None = None,
) -> list[str]:
    prev: dict[str, Any] = {}
    if estado_path and estado_path.is_file():
        try:
            prev = json.loads(estado_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            prev = {}

    alertas: list[str] = []
    ts_info = estado.get("tailscale", {})
    relevo_actual = any(d.get("camino") == "relay" for d in ts_info.get("dispositivos", []))
    if relevo_actual and not prev.get("relevo_alertado"):
        alertas.append("tailscale_relay: camino cayó a relevo")

    rd_info = estado.get("rustdesk", {})
    rd_caido = rd_info.get("estado") == "OK" and (not rd_info.get("servicio_activo") or not rd_info.get("puerto_escucha"))
    if rd_caido and not prev.get("rustdesk_alertado"):
        alertas.append("rustdesk_sin_puerto: servicio inactivo o puerto cerrado")

    if estado_path:
        estado_path.parent.mkdir(parents=True, exist_ok=True)
        estado_path.write_text(
            json.dumps({"relevo_alertado": relevo_actual, "rustdesk_alertado": rd_caido}) + "\n",
            encoding="utf-8",
        )
    return alertas


def recolectar_enlaces(correr: Correr = subprocess.run, estado_path: Path | None = None) -> dict[str, Any]:
    ts = lee_tailscale(correr=correr)
    rd = lee_rustdesk(correr=correr)
    res = {"tailscale": ts, "rustdesk": rd}
    res["alertas"] = evaluar_alertas_enlaces(res, estado_path=estado_path)
    return res


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="estado_enlaces")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
    res = recolectar_enlaces()
    print(json.dumps(res, ensure_ascii=False, indent=2 if not args.json else None))
    return 0


if __name__ == "__main__":
    sys.exit(main())
