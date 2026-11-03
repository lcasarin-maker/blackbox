#!/usr/bin/env python3
"""Aviso, una vez por arranque, de que el controlador NVIDIA declaro la GPU en `Reset Required`.

Lee el journal de kernel del arranque ACTUAL (solo lectura) y busca la secuencia medida el 2026-11-02 en los
arranques con 7.0.0-1024-nvidia: `NVRM: _issueRpcAndWait: rpcRecvPoll timedout` o `Xid ...: 154`. Si aparece, anota
una fila en `$BLACKBOX_DATA/aviso_gpu_reset.jsonl` (idempotente por boot_id) y avisa por el canal de
`aviso_termico` (notify-send). La fila solo se escribe cuando el aviso salio: si no habia sesion grafica, la
corrida siguiente del timer reintenta. Reusa el parser de `reboot_verdict.gpu_del_boot`; no escribe nada mas.

`--boot <id>` evalua otro arranque (control negativo/positivo) y solo imprime, sin anotar ni avisar.
DEBT-NVRM-GSP-TIMEOUT-XID154-KERNEL-7-0-SIN-ALARMA-01 punto 2.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from tools import aviso_termico, reboot_verdict

RUTA = reboot_verdict.DATOS / "aviso_gpu_reset.jsonl"


def hechos(lineas: list[str]) -> dict[str, Any]:
    h = reboot_verdict.gpu_del_boot(lineas)
    return {**h, "detectado": bool(h["gsp_timeout"] or h["xid154"])}


def lee_journal(boot_id: str) -> list[str] | None:
    """Lineas de `journalctl -k -b <boot_id>`; None si journalctl falla (no se sabe, nunca 'sin secuencia')."""
    r = reboot_verdict._journal("-k", "-b", boot_id, "-o", "short-monotonic")
    return r.stdout.splitlines() if r.returncode == 0 else None


def ya_anotado(boot_id: str, ruta: Path | None = None) -> bool:
    try:
        with (ruta or RUTA).open(encoding="utf-8") as f:
            return any(
                json.loads(ln).get("boot_id") == boot_id for ln in f if ln.strip()
            )
    except (OSError, ValueError):
        return False


def aviso(h: dict[str, Any]) -> aviso_termico.Aviso:
    t = h["gsp_timeout_monotonic_s"]
    return aviso_termico.Aviso(
        "critical",
        "GPU: el controlador pide reinicio",
        f"Este arranque registro timeout del GSP (a {t} s) / Xid 154 y {h['gpu_fullchip_reset_asserts']} asserts de reset: "
        "la GPU esta en 'Reset Required' y el motor sigue sirviendo sobre ella. Guarda el trabajo y reinicia.",
    )


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=(__doc__ or "").split("\n")[0])
    ap.add_argument("--boot", help="boot_id a evaluar (solo imprime)")
    a = ap.parse_args(argv)
    actual = reboot_verdict.BOOT_ID_ACTUAL.read_text().strip().replace("-", "")
    boot_id = a.boot or actual
    lineas = lee_journal(boot_id)
    if lineas is None:
        print("COULD_NOT_RUN: journalctl fallo", file=sys.stderr)
        return 2
    h = hechos(lineas)
    print(
        json.dumps({"boot_id": boot_id, "lineas": len(lineas), **h}, ensure_ascii=False)
    )
    if a.boot or not h["detectado"] or ya_anotado(boot_id):
        return 0
    if not aviso_termico.enviar(aviso(h)):
        return 1  # sin fila: la siguiente corrida del timer reintenta
    RUTA.parent.mkdir(parents=True, exist_ok=True)
    with RUTA.open("a", encoding="utf-8") as f:
        f.write(
            json.dumps(
                {
                    "boot_id": boot_id,
                    "visto_en": datetime.now(timezone.utc).isoformat(),
                    **h,
                }
            )
            + "\n"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
