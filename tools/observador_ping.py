#!/usr/bin/env python3
"""Observador externo de ping (interruptor `observador_ping`): FEATURE-OBSERVADOR-EXTERNO-DE-REINICIOS-01, parte construible aqui.

Una lectura por ejecucion (la repeticion de 1 s es de `systemd/bb-observador-ping.timer`, sin bucles ni `sleep`): un ping a la ATOM
desde OTRO equipo, con una fila en `$BLACKBOX_DATA/externo/ping.jsonl`. Un ping que corre en la ATOM muere con ella y no prueba nada.
Aporta la hora de la ULTIMA respuesta de la maquina con precision de ~1 s, independiente del journal (que se corta sin cierre), y separa
"la maquina murio" de "el journal calla pero la red responde". `ultima_respuesta` la lee quien cruce el hueco de un corte.
Configuracion: `$BLACKBOX_DATA/externo/observador.json` = {"destino": "<ip o nombre de la ATOM>"}.

Variante NAS (`--sync`): el observador es `adopted/nas/bb-ping-atom.sh` en el QNAP (una linea `<epoch> ok|fail` por segundo). `sync` TRAE ese
log con `smbclient` y lo mezcla en `ping.jsonl` (fuente "nas", clave epoch: repetir el sync no duplica). Configuracion:
`$BLACKBOX_DATA/externo/nas.json` = {"host", "share", "ruta", "credenciales": "<archivo con usuario y clave, modo 600>"}; la clave nunca se lee
aqui (la lee smbclient con `-A`) ni se imprime. Tres estados: OK, OBSOLETO (el log del NAS no avanza) y NOT_COLLECTED (nada se pudo traer:
`ping.jsonl` queda intacto); un log ausente nunca se lee como "sin huecos". Estado de la ultima corrida en `externo/sync.json`.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import stat
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from tools import interruptores

NOMBRE = "observador_ping"
Correr = Callable[..., Any]


def _datos() -> Path:
    return Path(os.environ.get("BLACKBOX_DATA", Path.home() / ".local/share/blackbox")) / "externo"


def sondea(destino: str, correr: Correr = subprocess.run) -> dict[str, Any]:
    """Un ping de 1 intento y 1 s de espera. `ok` es rc 0; no se interpreta nada mas (un fallo puede ser la red del observador)."""
    try:
        r = correr(["ping", "-c", "1", "-W", "1", destino], capture_output=True, text=True, check=False, timeout=5)
    except (OSError, subprocess.SubprocessError) as e:
        return {"ok": False, "error": type(e).__name__}
    return {"ok": r.returncode == 0}


def paso(modo_actual: str, destino: str, ruta: Path, correr: Correr = subprocess.run, ahora: float | None = None) -> dict[str, Any] | None:
    """Una fila en `ping.jsonl`. `off` no sondea."""
    if modo_actual == "off":
        return None
    t = datetime.now(timezone.utc).timestamp() if ahora is None else ahora
    fila = {"ts": datetime.fromtimestamp(t, timezone.utc).isoformat(), "epoch": t, **sondea(destino, correr)}
    ruta.parent.mkdir(parents=True, exist_ok=True)
    with ruta.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(fila) + "\n")
    return fila


def ultima_respuesta(ruta: Path, hasta: float) -> float | None:
    """Epoch de la ultima fila `ok` anterior o igual a `hasta`; None si no hay ninguna (sin cobertura, no concluyente)."""
    try:
        lineas = ruta.read_text(encoding="utf-8").splitlines()
    except OSError:
        return None
    mejor: float | None = None
    for ln in lineas:
        try:
            f = json.loads(ln)
        except ValueError:
            continue
        if isinstance(f, dict) and f.get("ok") is True and isinstance(f.get("epoch"), (int, float)) and f["epoch"] <= hasta:
            mejor = max(mejor or 0.0, float(f["epoch"]))
    return mejor


LINEA_NAS = re.compile(r"(\d{10}) (ok|fail)")
OBSOLETO_S = 900.0
CLAVES_NAS = ("host", "share", "ruta", "credenciales")


def _trae(cfg: dict[str, Any], destino: Path, correr: Correr) -> str | None:
    """Baja el log del NAS a `destino` con smbclient; None si lo logro, o el motivo (sin credenciales ni salida de smbclient)."""
    for k in CLAVES_NAS:
        if not isinstance(cfg.get(k), str) or not cfg[k] or '"' in cfg[k] or "\n" in cfg[k]:
            return f"nas.json: falta o es invalido '{k}'"
    cred = Path(cfg["credenciales"])
    try:
        modo = stat.S_IMODE(cred.stat().st_mode)
    except OSError:
        return "archivo de credenciales ilegible"
    if modo & 0o077:
        return f"credenciales con modo {modo:o}: exige 600"
    cmd = ["smbclient", f"//{cfg['host']}/{cfg['share']}", "-A", str(cred), "-c", f'get "{cfg["ruta"]}" "{destino}"']
    try:
        r = correr(cmd, capture_output=True, text=True, check=False, timeout=60)
    except (OSError, subprocess.SubprocessError) as e:
        return f"smbclient: {type(e).__name__}"
    if r.returncode != 0:
        return f"smbclient rc {r.returncode}"
    if not destino.exists():
        return "smbclient rc 0 sin archivo"
    return None


def _epochs_nas(ruta: Path) -> set[int]:
    vistos: set[int] = set()
    try:
        lineas = ruta.read_text(encoding="utf-8").splitlines()
    except OSError:
        return vistos
    for ln in lineas:
        try:
            f = json.loads(ln)
        except ValueError:
            continue
        if isinstance(f, dict) and f.get("fuente") == "nas" and isinstance(f.get("epoch"), (int, float)):
            vistos.add(int(f["epoch"]))
    return vistos


def sync(cfg_ruta: Path, ruta: Path, correr: Correr = subprocess.run, ahora: float | None = None) -> dict[str, Any]:
    """Trae el log del NAS y anade a `ruta` solo las filas cuyo epoch no esta; devuelve {estado, nuevas, descartadas, ...} y lo guarda en sync.json."""
    t = datetime.now(timezone.utc).timestamp() if ahora is None else ahora
    res: dict[str, Any] = {"estado": "NOT_COLLECTED", "nuevas": 0, "descartadas": 0, "epoch": t}
    try:
        cfg = json.loads(cfg_ruta.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        cfg = None
    lineas: list[str] = []
    with tempfile.TemporaryDirectory() as d:
        bajado = Path(d) / "nas.log"
        motivo = _trae(cfg, bajado, correr) if isinstance(cfg, dict) else "falta o es ilegible nas.json"
        if motivo is None:
            try:
                lineas = bajado.read_text(encoding="utf-8", errors="replace").splitlines()
            except OSError:
                motivo = "log bajado ilegible"
    if motivo is None:
        buenas = {int(m.group(1)): m.group(2) == "ok" for ln in lineas if (m := LINEA_NAS.fullmatch(ln.strip()))}
        res["descartadas"] = sum(1 for ln in lineas if ln.strip() and not LINEA_NAS.fullmatch(ln.strip()))
        if not buenas:
            motivo = "log del NAS sin una sola linea valida"
        else:
            vistos = _epochs_nas(ruta)
            nuevas = sorted(e for e in buenas if e not in vistos)
            if nuevas:
                ruta.parent.mkdir(parents=True, exist_ok=True)
                with ruta.open("a", encoding="utf-8") as fh:
                    for e in nuevas:
                        iso = datetime.fromtimestamp(e, timezone.utc).isoformat()
                        fh.write(json.dumps({"ts": iso, "epoch": e, "ok": buenas[e], "fuente": "nas"}) + "\n")
            res["nuevas"] = len(nuevas)
            res["ultima_epoch_nas"] = max(buenas)
            res["estado"] = "OBSOLETO" if t - max(buenas) > OBSOLETO_S else "OK"
    if motivo is not None:
        res["motivo"] = motivo
    ruta.parent.mkdir(parents=True, exist_ok=True)
    (ruta.parent / "sync.json").write_text(json.dumps(res) + "\n", encoding="utf-8")
    return res


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="observador_ping")
    ap.add_argument("--paso", action="store_true", help="un ping segun el interruptor observador_ping (lo repite bb-observador-ping.timer)")
    ap.add_argument("--sync", action="store_true", help="trae el log del NAS (nas.json) y lo mezcla en ping.jsonl; lo repite bb-observador-ping-sync.timer")
    a = ap.parse_args(argv)
    if a.sync:
        if interruptores.modo(NOMBRE) == "off":
            print(json.dumps({"estado": "off"}))
            return 0
        r = sync(_datos() / "nas.json", _datos() / "ping.jsonl")
        print(json.dumps(r, ensure_ascii=False))
        return 0 if r["estado"] == "OK" else 1
    if not a.paso:
        ap.print_help()
        return 2
    try:
        destino = str(json.loads((_datos() / "observador.json").read_text(encoding="utf-8"))["destino"])
    except (OSError, ValueError, KeyError):
        print("NOT_COLLECTED: falta $BLACKBOX_DATA/externo/observador.json con {destino}", file=sys.stderr)
        return 1
    print(json.dumps(paso(interruptores.modo(NOMBRE), destino, _datos() / "ping.jsonl"), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
