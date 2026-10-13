#!/usr/bin/env python3
"""Historial de la memoria de GPU por contenedor/cgroup (modulo dmem parcheado): pico por quien y motivo de fin.

Idea tomada de dgxtop (historial por proceso con pico y motivo de fin). `tools.gpumem.informe` da la foto de AHORA; esta
herramienta la guarda en el tiempo: `$BLACKBOX_DATA/gpumem_historial.jsonl`, una fila JSON por linea.

Cada ejecucion (bb-gpumem-historial.timer, cada minuto) en modo `observar` toma `informe()` y escribe UNA fila solo si
(1) algo cambio >= 0.25 GiB respecto de la ultima fila (total o cualquier hoja), aparecio o desaparecio una hoja, o cambio
el estado, o (2) pasaron 10 minutos desde la ultima fila. Eso acota el tamano: un host quieto escribe 6 filas por hora (144 por dia);
el techo absoluto es una fila por minuto (la cadencia del timer).
Fila: {ts, boot_id, estado, cobrado_total_gib, hojas:[{quien, gib}], pico_por_quien:{quien: gib maximo desde el arranque}}.
El pico vale por `boot_id` (/proc/sys/kernel/random/boot_id): cada fila acarrea el pico acumulado de su arranque, de modo
que otro boot_id empieza de cero. Cuando una hoja desaparece respecto de la fila anterior la fila lleva
`termino:[{quien, ultimo_gib, pico_gib, motivo}]`: el contenedor libero su memoria. El motivo es `desconocido` (el kernel
no dice por que), salvo que el estado SIN_REGION lo explique (el modulo dejo de dar region), y entonces es `SIN_REGION`.
Con SIN_REGION se registra una fila sin cifras de GPU (sin inventar), como mucho una cada 10 minutos.
Modos del interruptor `gpumem_historial`: `off` no hace nada; `observar` escribe; `actuar` declara UNSUPPORTED (no hay accion).
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from tools import gpumem, interruptores

NOMBRE = "gpumem_historial"
UMBRAL_GIB = 0.25
LATIDO = timedelta(minutes=10)
BOOT_ID = Path("/proc/sys/kernel/random/boot_id")


def ruta_por_defecto() -> Path:
    return Path(os.environ.get("BLACKBOX_DATA", Path.home() / ".local/share/blackbox")) / "gpumem_historial.jsonl"


def lee_filas(ruta: Path) -> list[dict[str, Any]]:
    """Filas validas del historial; lo ilegible se salta, un archivo ausente da lista vacia."""
    filas: list[dict[str, Any]] = []
    try:
        texto = ruta.read_text(encoding="utf-8")
    except OSError:
        return filas
    for linea in texto.splitlines():
        try:
            f = json.loads(linea)
        except ValueError:
            continue
        if isinstance(f, dict):
            filas.append(f)
    return filas


def _hojas(fila: dict[str, Any] | None) -> dict[str, float]:
    if not fila:
        return {}
    return {str(h["quien"]): float(h["gib"]) for h in fila.get("hojas", [])}


def _cambio(previa: dict[str, Any], hojas: dict[str, float], total: float) -> bool:
    antes = _hojas(previa)
    if set(antes) != set(hojas):
        return True
    if abs(total - float(previa.get("cobrado_total_gib", 0.0))) >= UMBRAL_GIB:
        return True
    return any(abs(g - antes[q]) >= UMBRAL_GIB for q, g in hojas.items())


def decide_fila(previa: dict[str, Any] | None, informe: dict[str, Any], ahora: datetime, boot_id: str) -> dict[str, Any] | None:
    """Pura. La fila a escribir, o None si no hay motivo (sin cambio >= 0.25 GiB y < 10 min desde `previa`)."""
    estado = str(informe.get("estado"))
    mismo_boot = previa is not None and previa.get("boot_id") == boot_id
    picos: dict[str, float] = dict(previa.get("pico_por_quien", {})) if previa is not None and mismo_boot else {}
    hojas: dict[str, float] = {}
    total: float | None = None
    if estado == "OK":
        hojas = {str(h["quien"]): float(h["gib"]) for h in informe.get("hojas", [])}
        total = float(informe.get("cobrado_total_gib", 0.0))
        for q, g in hojas.items():
            picos[q] = max(picos.get(q, 0.0), g)
    antes = _hojas(previa) if mismo_boot else {}
    motivo = "SIN_REGION" if estado == "SIN_REGION" else "desconocido"
    termino = [{"quien": q, "ultimo_gib": g, "pico_gib": picos.get(q, g), "motivo": motivo} for q, g in antes.items() if q not in hojas]
    if previa is not None:
        try:
            quieto = ahora - datetime.fromisoformat(str(previa["ts"])) < LATIDO
        except (KeyError, ValueError):
            quieto = False
        if quieto and not termino and previa.get("estado") == estado:
            if estado != "OK" or not _cambio(previa, hojas, total or 0.0):
                return None
    fila: dict[str, Any] = {"ts": ahora.isoformat(timespec="seconds"), "boot_id": boot_id, "estado": estado}
    if estado == "OK":
        fila["cobrado_total_gib"] = total
        fila["hojas"] = [{"quien": q, "gib": g} for q, g in hojas.items()]
    else:
        fila["motivo"] = informe.get("motivo")
    fila["pico_por_quien"] = picos
    if termino:
        fila["termino"] = termino
    return fila


def paso(
    modo_actual: str,
    ruta: Path | None = None,
    raiz: Path = Path("/sys/fs/cgroup"),
    ahora: datetime | None = None,
    boot_id: str | None = None,
    toma: Any = gpumem.informe,
) -> dict[str, Any] | None:
    """Un paso con E/S. `off`: nada. `actuar`: UNSUPPORTED (no hay accion que ejecutar). `observar`: escribe la fila si toca."""
    if modo_actual == "off":
        return None
    if modo_actual == "actuar":
        return {"estado": "UNSUPPORTED", "motivo": "gpumem_historial no tiene accion: solo observa"}
    ruta = ruta or ruta_por_defecto()
    ahora = ahora or datetime.now(timezone.utc)
    boot_id = boot_id or BOOT_ID.read_text(encoding="utf-8").strip()
    filas = lee_filas(ruta)
    fila = decide_fila(filas[-1] if filas else None, toma(raiz), ahora, boot_id)
    if fila is not None:
        ruta.parent.mkdir(parents=True, exist_ok=True)
        with ruta.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(fila, ensure_ascii=False) + "\n")
    return fila


def resumen(ruta: Path | None = None) -> dict[str, Any]:
    """{filas, picos_por_quien (del ultimo arranque registrado), ultimo_estado}."""
    filas = lee_filas(ruta or ruta_por_defecto())
    ultima = filas[-1] if filas else {}
    return {"filas": len(filas), "picos_por_quien": ultima.get("pico_por_quien", {}), "ultimo_estado": ultima.get("estado")}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="gpumem_historial")
    ap.add_argument("--paso", action="store_true", help="un paso segun el interruptor gpumem_historial (lo corre bb-gpumem-historial.timer)")
    a = ap.parse_args(argv)
    if a.paso:
        fila = paso(interruptores.modo(NOMBRE))
        print(json.dumps(fila, ensure_ascii=False))
    else:
        print(json.dumps(resumen(), indent=1, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
