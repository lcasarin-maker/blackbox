#!/usr/bin/env python3
"""Observador externo de ping (interruptor `observador_ping`): FEATURE-OBSERVADOR-EXTERNO-DE-REINICIOS-01, parte construible aqui.

Una lectura por ejecucion (la repeticion de 1 s es de `systemd/bb-observador-ping.timer`, sin bucles ni `sleep`): un ping a la ATOM
desde OTRO equipo, con una fila en `$BLACKBOX_DATA/externo/ping.jsonl`. Un ping que corre en la ATOM muere con ella y no prueba nada.
Aporta la hora de la ULTIMA respuesta de la maquina con precision de ~1 s, independiente del journal (que se corta sin cierre), y separa
"la maquina murio" de "el journal calla pero la red responde". `ultima_respuesta` la lee quien cruce el hueco de un corte.
Configuracion: `$BLACKBOX_DATA/externo/observador.json` = {"destino": "<ip o nombre de la ATOM>"}.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
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


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="observador_ping")
    ap.add_argument("--paso", action="store_true", help="un ping segun el interruptor observador_ping (lo repite bb-observador-ping.timer)")
    a = ap.parse_args(argv)
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
