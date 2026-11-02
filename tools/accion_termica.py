#!/usr/bin/env python3
"""Acciones automaticas ante calor sostenido: congelar la carga pausable que el consumidor DECLARA, y descongelarla.

Lo corre el vigilante `aviso_termico.py` en cada cambio de estado. Relacion de informacion: bb no sabe nombres
de unidades ajenas; el consumidor que encola trabajo publica `$BLACKBOX_DATA/carga_pausable.json`
(`carga-pausable/1`) y bb actua sobre lo que ese archivo dice. Sin archivo, sin accion (y el hecho queda en el log).

    {"esquema": "carga-pausable/1", "unidades": [{"unidad": "cola_job.scope", "pausable": true}],
     "actualizado": "<iso con zona>", "latido_s": 16200, "bitacora": "<ruta opcional de su bitacora>"}

Latido: `actualizado` es la ultima escritura y `latido_s` el plazo en que el productor promete reescribirla.
Pasado ese plazo bb lo ANOTA en cada evento (`latido`) y sigue actuando como antes de tener la comprobacion:
falla abierto, porque congelar una unidad inactiva no hace nada (`is-active` va antes) y no congelar una carga
viva por un reloj viejo seria perder la unica defensa termica. Contrato fijado con un fixture dorado
(`tests/fixtures/contrato/carga_pausable_1.json`, el mismo sha256 en los dos repos).

Transicion: mientras el productor desplegado escriba el nombre y el esquema LEGADOS (`LEGADO_*`), bb lee los dos
y prefiere el neutro. El legado se retira cuando el productor de la ATOM escriba el neutro.

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
CARGA = DATOS / "carga_pausable.json"
ESQUEMA = "carga-pausable/1"
# Legado de la transicion (boleta #18 A, 2026-11-01): el nombre que el productor usaba antes del contrato neutro.
# Unico sitio de bb donde sobrevive; se borra junto con su test cuando el productor desplegado escriba el neutro.
LEGADO_ARCHIVO = "atlas_carga.json"
LEGADO_ESQUEMA = "atlas-carga/1"
CARGA_LEGADO = DATOS / LEGADO_ARCHIVO
ESQUEMAS = (ESQUEMA, LEGADO_ESQUEMA)
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


def _lee_una(ruta: Path) -> tuple[list[str] | None, str, dict[str, Any]]:
    """(unidades o None si el archivo no sirve, motivo, documento). Una unidad con nombre invalido se descarta."""
    try:
        d: Any = json.loads(ruta.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None, f"{ruta} ausente o ilegible: el consumidor no declaro su carga", {}
    if not isinstance(d, dict) or d.get("esquema") not in ESQUEMAS:
        return None, f"{ruta.name} no es {' ni '.join(ESQUEMAS)}", {}
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
    return unidades, motivo, d


def estado_latido(d: dict[str, Any], ahora: datetime | None = None) -> str:
    """'' si el latido esta al dia; si no, por que no se puede afirmar. No decide nada: lo anota quien actua."""
    if d.get("esquema") != ESQUEMA:
        return f"esquema {d.get('esquema')!r} sin latido declarado"
    plazo = d.get("latido_s")
    if type(plazo) is not int or plazo <= 0:
        return f"latido_s ilegible ({plazo!r})"
    try:
        sello = datetime.fromisoformat(str(d.get("actualizado")))
    except ValueError:
        return f"actualizado ilegible ({d.get('actualizado')!r})"
    if sello.tzinfo is None:
        return f"actualizado sin zona horaria ({d.get('actualizado')!r})"
    edad = ((ahora or datetime.now(timezone.utc)) - sello).total_seconds()
    if edad > plazo:
        return f"latido viejo: {int(edad)} s desde la ultima declaracion, plazo {plazo} s"
    return ""


def lee_declaracion(
    ruta: Path | None = None, ahora: datetime | None = None
) -> tuple[list[str], str, str, dict[str, Any]]:
    """(unidades pausables, motivo si no hay, aviso de latido, documento leido).

    Con `ruta` lee solo ese archivo (en cualquiera de los dos esquemas). Sin ella, el neutro y, si el neutro no
    sirve, el legado: se prefiere el nuevo, y el motivo de un neutro roto viaja aunque el legado salve la lectura.
    """
    candidatos = [ruta] if ruta else [CARGA, CARGA_LEGADO]
    motivos = []
    for c in candidatos:
        unidades, motivo, d = _lee_una(c)
        if unidades is None:
            motivos.append(motivo)
            continue
        previos = "; ".join(motivos)
        return unidades, motivo, "; ".join(x for x in (previos, estado_latido(d, ahora)) if x), d
    return [], "; ".join(motivos), "", {}


def lee_carga(ruta: Path | None = None) -> tuple[list[str], str]:
    """(unidades pausables, motivo si no hay). La vista corta de `lee_declaracion`."""
    unidades, motivo, _latido, _d = lee_declaracion(ruta)
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
    unidades, motivo, latido, _d = declaracion
    extra = {"latido": latido} if latido else {}
    ya = _cargar_congeladas(congeladas)
    if not unidades:
        anota({"accion": "ninguna", "estado": etiqueta, "motivo": motivo})
        return
    for u in unidades:
        if u in ya:
            continue
        if ejecutar(["is-active", u])[0] != 0:
            anota({"accion": "no_actua", "unidad": u, "estado": etiqueta, "motivo": "unidad inactiva", **extra})
            continue
        ya.append(u)  # se anota ANTES de congelar: si no se puede persistir, no se congela
        _guardar_congeladas(congeladas, ya)
        rc, salida = ejecutar(["freeze", u])
        if rc != 0:
            ya.remove(u)
            _guardar_congeladas(congeladas, ya)
        anota({"accion": "freeze", "unidad": u, "estado": etiqueta, "rc": rc, "salida": salida[:200], **extra})


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
        _congela(etiqueta, lee_declaracion(carga), congeladas, ejecutar, anota)
    elif etiqueta == "normal":
        _descongela(etiqueta, congeladas, ejecutar, anota)
    return eventos
