#!/usr/bin/env python3
"""Registro temprano, una linea por arranque, del modulo nvidia que ESTE arranque cargo.

Por que existe: `modinfo -n nvidia` y `/sys/module/nvidia/` solo se pueden leer EN VIVO. El 2026-11-02 no constaba si
los arranques del bucle de 7.0.0-1024 corrieron con el modulo parchado (`.../updates/`) o con el de fabrica, y los
arranques pasados no se pueden reconstruir (DEBT-NVRM-GSP-TIMEOUT-XID154-KERNEL-7-0-SIN-ALARMA-01). Esta herramienta
anota la respuesta mientras el arranque esta vivo; `tools/reboot_verdict.py` la lee y copia `modulo_nvidia_*` a la fila.

Uso: sin argumentos IMPRIME la linea y no escribe nada (solo lectura). Con `--escribe` la anade a
`$BLACKBOX_DATA/modulo_nvidia_por_arranque.jsonl`: solo-anexar e idempotente por boot_id (una segunda corrida del
mismo arranque no escribe). Si el modulo aun no esta cargado no escribe (rc 1): la linea quedaria fijada con la
srcversion en blanco y la corrida siguiente ya no podria corregirla.

Linea: {esquema, ts, boot_id (sin guiones), ruta, sha256, version, srcversion, srcversion_archivo, parchado}.
`parchado` es true si la ruta contiene `/updates/`, false si no. Un valor ilegible es "NOT_COLLECTED: <motivo>".

rc: 0 linea impresa o escrita o ya anotada; 1 modulo no cargado (nada escrito); 2 COULD_NOT_RUN (sin boot_id).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

DATOS = Path(os.environ.get("BLACKBOX_DATA", Path.home() / ".local/share/blackbox"))
SALIDA = DATOS / "modulo_nvidia_por_arranque.jsonl"
BOOT_ID = Path("/proc/sys/kernel/random/boot_id")
SYS_MODULO = Path("/sys/module/nvidia")
ESQUEMA = "bb-modulo-nvidia/1"


def _nc(motivo: str) -> str:
    return f"NOT_COLLECTED: {motivo}"


def _lee(ruta: Path) -> str:
    try:
        return ruta.read_text(encoding="utf-8", errors="replace").strip() or _nc(f"{ruta} vacio")
    except OSError as e:
        return _nc(f"{ruta} ilegible ({type(e).__name__})")


def _modinfo(campo: str) -> str:
    """campo "-n" pide la ruta del archivo; cualquier otro es `modinfo -F <campo>`."""
    args = ["-n"] if campo == "-n" else ["-F", campo]
    try:
        r = subprocess.run(["modinfo", *args, "nvidia"], capture_output=True, text=True, check=False, timeout=10)
    except (OSError, subprocess.SubprocessError) as e:
        return _nc(f"modinfo {campo} no corrio ({type(e).__name__})")
    out = r.stdout.strip()
    return out if r.returncode == 0 and out else _nc(f"modinfo {campo} rc={r.returncode} sin salida")


def _sha256(ruta: str) -> str:
    h = hashlib.sha256()
    try:
        with open(ruta, "rb") as fh:
            for bloque in iter(lambda: fh.read(1 << 20), b""):
                h.update(bloque)
    except OSError as e:
        return _nc(f"{ruta} ilegible ({type(e).__name__})")
    return h.hexdigest()


def lee_modulo() -> dict[str, Any]:
    ruta = _modinfo("-n")
    legible = not ruta.startswith("NOT_COLLECTED")
    return {
        "ruta": ruta,
        "sha256": _sha256(ruta) if legible else _nc("sin ruta del modulo"),
        "version": _lee(SYS_MODULO / "version"),
        "srcversion": _lee(SYS_MODULO / "srcversion"),
        "srcversion_archivo": _modinfo("srcversion"),
        "parchado": ("/updates/" in ruta) if legible else _nc("sin ruta del modulo"),
    }


def boot_id() -> str | None:
    try:
        return BOOT_ID.read_text(encoding="ascii").strip().replace("-", "") or None
    except OSError:
        return None


def ya_anotados(salida: Path | None = None) -> set[str]:
    salida = salida or SALIDA
    if not salida.exists():
        return set()
    ids = set()
    for ln in salida.read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            ids.add(str(json.loads(ln)["boot_id"]))
        except (ValueError, KeyError, TypeError):
            continue  # una linea rota no impide anotar el arranque
    return ids


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=(__doc__ or "").split("\n")[0])
    ap.add_argument("--escribe", action="store_true", help="anade la linea al jsonl (idempotente por boot_id)")
    a = ap.parse_args(argv)
    bid = boot_id()
    if bid is None:
        print(f"COULD_NOT_RUN: {BOOT_ID} ilegible", file=sys.stderr)
        return 2
    linea = {
        "esquema": ESQUEMA,
        "ts": datetime.now().astimezone().isoformat(timespec="seconds"),
        "boot_id": bid,
        **lee_modulo(),
    }
    print(json.dumps(linea, ensure_ascii=False))
    if not a.escribe:
        return 0
    if not SYS_MODULO.exists():
        print("# nvidia aun no esta cargado: nada escrito", file=sys.stderr)
        return 1
    if bid in ya_anotados():
        print(f"# {bid[:8]} ya anotado", file=sys.stderr)
        return 0
    SALIDA.parent.mkdir(parents=True, exist_ok=True)
    with SALIDA.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(linea, ensure_ascii=False) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
