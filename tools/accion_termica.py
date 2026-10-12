#!/usr/bin/env python3
"""Acciones automaticas ante calor sostenido: congelar la carga pausable que Atlas DECLARA, y descongelarla.

Lo corre el vigilante `aviso_termico.py` en cada cambio de estado. Relacion de informacion con Atlas: bb no
sabe nombres de unidades de Atlas; Atlas publica `$BLACKBOX_DATA/atlas_carga.json` (`atlas-carga/1`) y bb
actua sobre lo que ese archivo dice. Sin archivo, sin accion (y el hecho queda en el log).

    {"esquema": "atlas-carga/1", "unidades": [{"unidad": "liberation_job.scope", "pausable": true}],
     "actualizado": "<iso utc>"}

Politica:
* `sostenida` o `sobre_100`: `systemctl --user freeze` de cada unidad pausable y activa. Reversible.
* `normal`: `thaw` de lo que ESTE modulo congelo (lista persistida, para que un reinicio del vigilante no
  deje una unidad congelada para siempre).
* `desconocido`: no toca nada (sin datos no se decide).
* Cada decision, incluso "no actuo", se escribe en `acciones_termicas.jsonl`.

Riesgo conocido: un job congelado sigue consumiendo su `timeout`; al descongelar puede morir de inmediato.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

DATOS = Path(os.environ.get("BLACKBOX_DATA", Path.home() / ".local/share/blackbox"))
CARGA = DATOS / "atlas_carga.json"
CONGELADAS = DATOS / "acciones_termicas_congeladas.json"
LOG = DATOS / "acciones_termicas.jsonl"
UNIDAD_VALIDA = re.compile(r"^[A-Za-z0-9_.@-]{1,120}\.scope$")
ESTADOS_CALIENTES = ("sostenida", "sobre_100")

Ejecutor = Callable[[list[str]], tuple[int, str]]


def _systemctl(args: list[str]) -> tuple[int, str]:
    try:
        r = subprocess.run(
            ["systemctl", "--user", *args],
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as e:
        return 127, str(e)
    return r.returncode, (r.stdout + r.stderr).strip()


def lee_carga(ruta: Path | None = None) -> tuple[list[str], str]:
    """(unidades pausables, motivo si no hay). Una unidad con nombre invalido se descarta y se declara."""
    ruta = ruta or CARGA
    try:
        d: Any = json.loads(ruta.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return [], f"{ruta} ausente o ilegible: Atlas no declaro su carga"
    if not isinstance(d, dict) or d.get("esquema") != "atlas-carga/1":
        return [], "atlas_carga.json no es atlas-carga/1"
    unidades, descartadas = [], 0
    for u in d.get("unidades", []):
        nombre = u.get("unidad") if isinstance(u, dict) else None
        if (
            isinstance(nombre, str)
            and UNIDAD_VALIDA.match(nombre)
            and u.get("pausable") is True
        ):
            unidades.append(nombre)
        else:
            descartadas += 1
    motivo = "" if unidades else f"ninguna unidad pausable declarada ({descartadas} descartadas)"
    return unidades, motivo


def _cargar_congeladas(ruta: Path) -> list[str]:
    try:
        d = json.loads(ruta.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    return [u for u in d if isinstance(u, str) and UNIDAD_VALIDA.match(u)] if isinstance(d, list) else []


def _guardar_congeladas(ruta: Path, unidades: list[str]) -> None:
    ruta.parent.mkdir(parents=True, exist_ok=True)
    tmp = ruta.with_suffix(".tmp")
    tmp.write_text(json.dumps(sorted(unidades)), encoding="utf-8")
    tmp.replace(ruta)


def _registra(evento: dict[str, Any], log: Path) -> None:
    evento = {"ts": datetime.now(timezone.utc).isoformat(), **evento}
    try:
        log.parent.mkdir(parents=True, exist_ok=True)
        with log.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(evento, ensure_ascii=False) + "\n")
    except OSError:
        pass  # el log de acciones no debe tumbar al vigilante; el fallo se ve por su ausencia en el archivo


def _congela(etiqueta, declaracion, congeladas, ejecutar, anota) -> None:
    unidades, motivo = declaracion
    ya = _cargar_congeladas(congeladas)
    if not unidades:
        anota({"accion": "ninguna", "estado": etiqueta, "motivo": motivo})
        return
    for u in unidades:
        if u in ya:
            continue
        if ejecutar(["is-active", u])[0] != 0:
            anota({"accion": "no_actua", "unidad": u, "estado": etiqueta, "motivo": "unidad inactiva"})
            continue
        ya.append(u)  # se anota ANTES de congelar: si no se puede persistir, no se congela
        _guardar_congeladas(congeladas, ya)
        rc, salida = ejecutar(["freeze", u])
        if rc != 0:
            ya.remove(u)
            _guardar_congeladas(congeladas, ya)
        anota({"accion": "freeze", "unidad": u, "estado": etiqueta, "rc": rc, "salida": salida[:200]})


def _descongela(etiqueta, congeladas, ejecutar, anota) -> None:
    ya = _cargar_congeladas(congeladas)
    for u in list(ya):
        rc, salida = ejecutar(["thaw", u])
        if rc == 0 or "not loaded" in salida or "not found" in salida:
            ya.remove(u)
        anota({"accion": "thaw", "unidad": u, "estado": etiqueta, "rc": rc, "salida": salida[:200]})
    _guardar_congeladas(congeladas, ya)


def aplica(
    etiqueta: str,
    *,
    carga: Path | None = None,
    congeladas: Path | None = None,
    log: Path | None = None,
    ejecutar: Ejecutor = _systemctl,
) -> list[dict[str, Any]]:
    """Aplica la politica para el estado `etiqueta`. Devuelve los eventos registrados (los tests los inspeccionan)."""
    congeladas = congeladas or CONGELADAS
    log = log or LOG
    eventos: list[dict[str, Any]] = []

    def anota(ev: dict[str, Any]) -> None:
        eventos.append(ev)
        _registra(ev, log)

    if etiqueta in ESTADOS_CALIENTES:
        _congela(etiqueta, lee_carga(carga), congeladas, ejecutar, anota)
    elif etiqueta == "normal":
        _descongela(etiqueta, congeladas, ejecutar, anota)
    return eventos
