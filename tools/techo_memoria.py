#!/usr/bin/env python3
"""`bb techo`: el techo de memoria que el kernel aplica al cgroup de un proceso (DGX-483, DGX-585).

Frontera votada: blackbox gobierna el comportamiento fisico de la ATOM y el consumidor de conocimiento consume lo que bb produce. Leer
`memory.max` y `memory.swap.max` del cgroup es leer los techos de memoria del kernel, asi que vive aqui y quien lo
necesita (el worker de `tools/idle_skill_candidates.py` del consumidor, que se niega a correr sin techo) pregunta a bb.

    bb techo --pid N [--max-gib G] [--sin-swap]

Salida: una linea JSON `bb-techo-memoria/1` en stdout. `memory_max_bytes` y `memory_swap_max_bytes` son el entero del
kernel, o la cadena literal `max` (sin tope), o `NOT_COLLECTED: <motivo>` si no se pudieron leer: lo ilegible nunca es
0 ni `max`. `veredicto` solo existe si se pidio una exigencia (`--max-gib`, `--sin-swap`):
  ACOTADO         rc 0: `memory.max` finito y <= G GiB y, con `--sin-swap`, `memory.swap.max` = 0.
  NO_ACOTADO      rc 1: se leyo y no cumple (sin tope, tope mayor, o swap permitido).
  NOT_COLLECTED   rc 2: falta un dato que la exigencia necesitaba. Quien consume trata rc != 0 como "no corras".
Sin exigencia solo informa y sale 0 si pudo leer el cgroup, 2 si no.

Mismo criterio que la guarda propia del consumidor (`_bounded`: `memory.max` finito, <= 2 GiB, `memory.swap.max` 0), leido
del cgroup HOJA del proceso, no del mas estricto de sus ancestros: un tope heredado de un padre no lo da por acotado.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Sequence

FORMATO = "bb-techo-memoria/1"
GIB = 1024**3


def _lee(p: Path) -> str | None:
    try:
        return p.read_text(encoding="utf-8").strip()
    except OSError:
        return None


def _valor(texto: str | None, motivo: str) -> int | str:
    if texto == "max":
        return "max"
    if texto is not None and texto.isdigit():
        return int(texto)
    return f"NOT_COLLECTED: {motivo}"


def lee(pid: int, proc: Path = Path("/proc"), raiz: Path = Path("/sys/fs/cgroup")) -> dict[str, Any]:
    """Pura salvo por leer `proc` y `raiz`. Nunca lanza: un pid sin cgroup legible da NOT_COLLECTED."""
    fila: dict[str, Any] = {"formato": FORMATO, "pid": pid, "cgroup": None}
    lineas = (_lee(proc / str(pid) / "cgroup") or "").splitlines()
    ruta = next((l.split(":", 2)[2] for l in lineas if l.startswith("0::") and l.count(":") >= 2), None)
    if not ruta:
        sin = f"NOT_COLLECTED: no hay linea cgroup v2 de /proc/{pid}/cgroup"
        return {**fila, "memory_max_bytes": sin, "memory_swap_max_bytes": sin}
    d = raiz / ruta.lstrip("/")
    return {**fila, "cgroup": ruta,
            "memory_max_bytes": _valor(_lee(d / "memory.max"), f"{d}/memory.max ilegible"),
            "memory_swap_max_bytes": _valor(_lee(d / "memory.swap.max"), f"{d}/memory.swap.max ilegible")}


def veredicto(fila: dict[str, Any], max_gib: float | None, sin_swap: bool) -> str | None:
    """None si no se pidio exigencia. Una exigencia con un dato ilegible no es NO_ACOTADO: es NOT_COLLECTED."""
    if max_gib is None and not sin_swap:
        return None
    mem, swap = fila["memory_max_bytes"], fila["memory_swap_max_bytes"]
    if max_gib is not None:
        if isinstance(mem, str) and mem.startswith("NOT_COLLECTED"):
            return "NOT_COLLECTED"
        if mem == "max" or mem > max_gib * GIB:
            return "NO_ACOTADO"
    if sin_swap:
        if isinstance(swap, str) and swap.startswith("NOT_COLLECTED"):
            return "NOT_COLLECTED"
        if swap != 0:
            return "NO_ACOTADO"
    return "ACOTADO"


def main(argv: Sequence[str] | None = None, proc: Path = Path("/proc"), raiz: Path = Path("/sys/fs/cgroup")) -> int:
    ap = argparse.ArgumentParser(prog="bb techo", description="techo de memoria del cgroup de un proceso")
    ap.add_argument("--pid", type=int, required=True)
    ap.add_argument("--max-gib", type=float, default=None, help="exige memory.max finito y <= G GiB")
    ap.add_argument("--sin-swap", action="store_true", help="exige memory.swap.max == 0")
    a = ap.parse_args(argv)
    fila = lee(a.pid, proc, raiz)
    v = veredicto(fila, a.max_gib, a.sin_swap)
    if v is not None:
        fila["veredicto"] = v
    print(json.dumps(fila, ensure_ascii=False))
    if v is None:
        return 2 if fila["cgroup"] is None else 0
    return {"ACOTADO": 0, "NO_ACOTADO": 1}.get(v, 2)


if __name__ == "__main__":
    sys.exit(main())
