#!/usr/bin/env python3
"""Aviso en pantalla cuando la ATOM entra en calor sostenido o pasa de 100 C.

Lee `estado_termico.json` (lo escribe `atom_gpu_telemetry.py` en cada muestra) y manda una notificacion de
escritorio SOLO cuando el estado CAMBIA, mas un recordatorio cada 10 min mientras siga por encima de 100 C.
Es un proceso aparte del sampler a proposito: si `notify-send` falla (sin sesion grafica, sin bus), el
instrumento que mide no se entera.

Que debe hacer quien recibe el aviso (el texto de la notificacion lo dice):

* `sostenida`: no es una emergencia, es el estado en que estaba la ATOM antes de sus cuatro cortes
  medidos. Correr `bb who` y detener lo que no sea esencial.
* `sobre_100`: la zona esta a menos de 5 C del apagado automatico del kernel (trip 104.8 C). Bajar la carga
  ya; si no hay nada que quitar, detener vLLM.

Un estado con latido viejo (`actualizado` de hace mas de 60 s) es DESCONOCIDO, nunca `normal`: se avisa una
vez de que no hay datos termicos. En el primer arranque no se avisa de `normal` ni de `desconocido`.

Esto NO frena trabajos: el freno de Atlas ya existe (`tools/bb_consulta.py` llama a `--gate-termico`) y
bloqueo entre el 93 y el 100 % de las lecturas calientes del 2026-10-11.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from tools import accion_termica

RUTA = (
    Path(os.environ.get("BLACKBOX_DATA", Path.home() / ".local/share/blackbox"))
    / "estado_termico.json"
)
LATIDO_MAX_S = 60.0
RECORDATORIO_S = 600.0
INTERVALO_S = 10.0
TRIP_C = 104.8


@dataclass(frozen=True)
class Aviso:
    urgencia: str  # low | normal | critical (los de notify-send)
    titulo: str
    cuerpo: str


def lee(ruta: Path = RUTA) -> dict[str, Any] | None:
    try:
        d = json.loads(ruta.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return d if isinstance(d, dict) else None


def etiqueta(dato: dict[str, Any] | None, ahora: datetime) -> str:
    """normal | sostenida | sobre_100 | desconocido. Sin dato, ilegible o con latido viejo = desconocido."""
    if not dato:
        return "desconocido"
    try:
        edad = (ahora - datetime.fromisoformat(dato["actualizado"])).total_seconds()
    except (KeyError, ValueError, TypeError):
        return "desconocido"
    if edad > LATIDO_MAX_S or dato.get("estado") not in (
        "normal",
        "sostenida",
        "sobre_100",
    ):
        return "desconocido"
    return str(dato["estado"])


def _hora(iso: str | None) -> str:
    try:
        return datetime.fromisoformat(iso or "").astimezone().strftime("%H:%M")
    except ValueError:
        return "?"


def decide(
    previo: str | None,
    dato: dict[str, Any] | None,
    ahora: datetime,
    ultimo_recordatorio: float | None = None,
    monotono: float = 0.0,
) -> tuple[list[Aviso], str, float | None]:
    """Funcion pura: (estado previo, estado leido) -> (avisos, estado nuevo, marca del ultimo recordatorio)."""
    actual = etiqueta(dato, ahora)
    avisos: list[Aviso] = []
    t = (dato or {}).get("temp_c")
    zona = (dato or {}).get("zona_mas_caliente") or "?"
    desde = _hora((dato or {}).get("desde"))
    if actual != previo:
        if actual == "sostenida":
            avisos.append(
                Aviso(
                    "normal",
                    "ATOM: calor sostenido",
                    f"Zona {zona} a {t} C (desde las {desde}). No es una emergencia: es el estado en que estaba la ATOM antes de sus "
                    "4 cortes medidos. Corre `bb who` y detén lo que no sea esencial.",
                )
            )
        elif actual == "sobre_100":
            margen = (
                f"{TRIP_C - t:.1f}" if isinstance(t, (int, float)) else "menos de 5"
            )
            avisos.append(
                Aviso(
                    "critical",
                    "ATOM: zona sobre 100 C",
                    f"{zona} a {t} C, a {margen} C del apagado automático ({TRIP_C} C). Baja la carga ahora: `bb who` dice quién pesa; "
                    "si no hay nada que quitar, detén vLLM.",
                )
            )
            ultimo_recordatorio = monotono
        elif actual == "normal" and previo in ("sostenida", "sobre_100"):
            avisos.append(
                Aviso(
                    "low",
                    "ATOM: calor normalizado",
                    "La zona salió del calor sostenido.",
                )
            )
        elif actual == "desconocido" and previo in ("normal", "sostenida", "sobre_100"):
            avisos.append(
                Aviso(
                    "normal",
                    "ATOM: sin datos térmicos",
                    f"El estado térmico no se actualiza hace más de {int(LATIDO_MAX_S)} s: ¿se paró atom-gpu-telemetry? Mientras tanto no se sabe si hay calor.",
                )
            )
        elif actual in ("normal",) and previo == "desconocido":
            avisos.append(
                Aviso(
                    "low",
                    "ATOM: datos térmicos de vuelta",
                    "El estado térmico se actualiza otra vez.",
                )
            )
    elif (
        actual == "sobre_100"
        and ultimo_recordatorio is not None
        and monotono - ultimo_recordatorio >= RECORDATORIO_S
    ):
        avisos.append(
            Aviso(
                "critical",
                "ATOM: sigue sobre 100 C",
                f"{zona} a {t} C. Baja la carga: `bb who`.",
            )
        )
        ultimo_recordatorio = monotono
    return avisos, actual, ultimo_recordatorio


def enviar(a: Aviso) -> bool:
    """notify-send. Un fallo se dice por stderr (queda en el journal del servicio) y no tumba el vigilante."""
    try:
        r = subprocess.run(
            ["notify-send", "-u", a.urgencia, "-a", "blackbox", a.titulo, a.cuerpo],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as e:
        print(f"COULD_NOT_NOTIFY: {e}", file=sys.stderr)
        return False
    if r.returncode != 0:
        print(
            f"COULD_NOT_NOTIFY: notify-send rc={r.returncode}: {r.stderr.strip()[:200]}",
            file=sys.stderr,
        )
        return False
    return True


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=(__doc__ or "").split("\n")[0])
    ap.add_argument(
        "--una-vez",
        action="store_true",
        help="una lectura, imprime el estado y sale (diagnostico)",
    )
    a = ap.parse_args(argv)
    if a.una_vez:
        d = lee()
        print(
            json.dumps(
                {"etiqueta": etiqueta(d, datetime.now(timezone.utc)), "dato": d},
                ensure_ascii=False,
            )
        )
        return 0
    previo: str | None = None
    recordatorio: float | None = None
    while True:
        antes = previo
        avisos, previo, recordatorio = decide(
            previo, lee(), datetime.now(timezone.utc), recordatorio, time.monotonic()
        )
        if previo != antes or previo in accion_termica.ESTADOS_CALIENTES:
            try:  # congelar/descongelar la carga que Atlas declara; un fallo no tumba el vigilante
                accion_termica.aplica(previo)
            except OSError as e:
                print(f"COULD_NOT_ACT: {e}", file=sys.stderr)
        for av in avisos:
            enviar(av)
        time.sleep(INTERVALO_S)  # blocking-sleep: intervalo del vigilante de vida larga, no hay I/O a esperar -- DEBT-TERMICA-CORROBORACION-DE-ALARMA-SIEMPRE-DESCARTA-01  # sunset-reviewed: 3.7 -- re-revisado 2026-10-13 contra 3.6 (`git log -L` de la linea: ultimo cambio anterior a la revision 3.6, 7674fc13); re-revisado 2026-10-13 contra 3.5: `git blame` de la linea 216 (7280a6a4) es anterior al bump 3.5.0 (b99560e8), la linea no cambio desde su revision anterior; la razon sigue valiendo: re-revisado 2026-10-13 contra 3.4: `git blame` de la linea 216 (095c3a35) es anterior al bump 3.4.1 (eb89c383), la linea no cambio desde su revision anterior; la razon sigue valiendo: re-revisado 2026-10-13 contra 3.3: `git blame` de la linea 216 (b008b6ee) es anterior al bump 3.3.0 (3512a16a), la linea no cambio desde su revision anterior; la razon sigue valiendo: re-revisado 2026-10-13 contra 3.2: `git blame` de la linea 216 (804713d5) es anterior al bump 3.2.0 (e8e5aa8d), la linea no cambio desde su revision anterior; la razon sigue valiendo: re-revisado 2026-10-13 contra 3.1: `git blame` de la linea 216 (93850773) es anterior al bump 3.1.0 (7a5bd48b), la linea no cambio desde su revision anterior; la razon sigue valiendo: re-revisado 2026-10-12 contra 3.0: `git blame` de la linea 216 (92598b79) es anterior al bump 2.9.1 (ab63e2b), la linea no cambio desde su revision anterior; la razon sigue valiendo: re-revisado 2026-10-12 contra 2.9: `git blame` de la linea 216 (a38d1570) no cambio desde su revision anterior; la razon sigue valiendo: revalidado 2026-10-11: demonio de usuario sin otro hilo; el intervalo acota la latencia del aviso ; re-revisado 2026-10-13 contra 3.1: la linea no cambio desde 20256295 (git blame de esta linea)


if __name__ == "__main__":
    raise SystemExit(main())
