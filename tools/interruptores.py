#!/usr/bin/env python3
"""Interruptores de soluciones: cada solucion candidata corre en `off`, `observar` o `actuar`.

Decision de Luis 2026-10-12: no descartar una solucion por una medicion indirecta; implementarla como interruptor
y decidir con su registro (aciertos, falsos positivos, dano). `observar` registra "habria actuado" sin tocar nada.
Estado en `$BLACKBOX_DATA/interruptores.json` (`bb-interruptores/1`); lo ilegible o desconocido vale `off`.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

MODOS = ("off", "observar", "actuar")


def _datos() -> Path:
    return Path(os.environ.get("BLACKBOX_DATA", Path.home() / ".local/share/blackbox"))


def modo(nombre: str, ruta: Path | None = None) -> str:
    ruta = ruta or _datos() / "interruptores.json"
    try:
        m = json.loads(ruta.read_text(encoding="utf-8")).get("modos", {}).get(nombre, "off")
    except (OSError, ValueError, AttributeError):
        return "off"
    return m if m in MODOS else "off"


def registra(nombre: str, evento: dict[str, Any], directorio: Path | None = None) -> None:
    d = (directorio or _datos() / "interruptores")
    d.mkdir(parents=True, exist_ok=True)
    fila = {"ts": datetime.now(timezone.utc).isoformat(), **evento}
    with (d / f"{nombre}.jsonl").open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(fila, ensure_ascii=False) + "\n")


def resumen(nombre: str, directorio: Path | None = None) -> dict[str, int]:
    """Cuenta disparos, confirmados por PSI (aciertos) y falsos positivos de un interruptor."""
    ruta = (directorio or _datos() / "interruptores") / f"{nombre}.jsonl"
    n = ok = 0
    try:
        for linea in ruta.read_text(encoding="utf-8").splitlines():
            try:
                e = json.loads(linea)
            except ValueError:
                continue
            if e.get("habria_actuado"):
                n += 1
                ok += 1 if e.get("confirmado_por_psi") else 0
    except OSError:
        pass
    return {"disparos": n, "confirmados": ok, "falsos_positivos": n - ok}
