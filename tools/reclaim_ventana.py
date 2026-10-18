"""Deltas por minuto del reclamo de memoria de un slice, leidos de las muestras de `bb sample`.

## Por que existe

DEBT-APP-SLICE-TOPE-42G-ESTRANGULA-LA-CACHE-DE-ARCHIVOS-01: el 2026-10-17 app.slice
tenia 15.6 GiB de cache inactiva bajo un tope de 42 GiB, 99 % de su escaneo era
reclamo DIRECTO (lo pagan los procesos que piden memoria, en su propio tiempo) y
releia unos 182 GB de cache en 3 h, con 60 GiB libres en la maquina. Luis voto
medir antes de tocar el tope. `bb sample` guarda en cada slice un bloque
`reclaim` con los contadores ACUMULADOS de `memory.stat`; esto los convierte en
deltas entre muestras consecutivas para cruzarlos con "la maquina iba lenta a
las HH:MM".

## Reglas

- Un contador que BAJA (o un `boot_id` que cambia) es un reinicio del contador:
  el delta es el valor nuevo (partio de 0), nunca una tasa negativa.
- `NOT_COLLECTED` en cualquiera de las dos muestras deja ese delta en
  `NOT_COLLECTED`; no se vuelve 0.
- La parte de reclamo directo es `pgscan_direct / (pgscan_direct + pgscan_kswapd)`
  del intervalo; sin escaneo es `None` ("-"), no 0 %.

Uso: `python3 -m tools.reclaim_ventana --desde 2026-10-17T18:00 --hasta 2026-10-17T19:00`
(por defecto el slice `app` y `$BLACKBOX_DATA/samples`). Sale 0 con filas, 2
(`COULD_NOT_RUN`) si la ventana no tiene dos muestras con `reclaim`. Solo lee.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

DATA_DIR = Path(os.environ.get("BLACKBOX_DATA", Path.home() / ".local/share/blackbox"))
NC = "NOT_COLLECTED"
CONTADORES = ("refault_file", "pgscan_direct", "pgscan_kswapd", "pgsteal_direct")
# memory.stat -> campo de `reclaim`, el mismo mapa que `cg_reclaim` de bin/bb.
CAMPOS_STAT = {"workingset_refault_file": "refault_file", "pgscan_direct": "pgscan_direct",
               "pgscan_kswapd": "pgscan_kswapd", "pgsteal_direct": "pgsteal_direct",
               "inactive_file": "inactive_file_kb", "anon": "anon_kb", "file": "file_kb"}


def lee_memory_stat(ruta: Path) -> dict[str, int | str]:
    """Los siete campos de `reclaim` leidos de un memory.stat vivo; ilegible -> NOT_COLLECTED."""
    vals: dict[str, str] = {}
    try:
        for linea in ruta.read_text(encoding="ascii", errors="replace").splitlines():
            k, _, v = linea.partition(" ")
            vals[k] = v.strip()
    except OSError:
        pass
    out: dict[str, int | str] = {}
    for k, campo in CAMPOS_STAT.items():
        v = vals.get(k, "")
        if not v.isdigit():
            out[campo] = NC
        else:
            out[campo] = int(v) // 1024 if campo.endswith("_kb") else int(v)
    return out


def parte_directo(r: dict) -> float | None:
    d, k = r.get("pgscan_direct"), r.get("pgscan_kswapd")
    if not isinstance(d, int) or not isinstance(k, int) or d + k == 0:
        return None
    return round(d / (d + k), 4)


def _hora(ts: str) -> datetime | None:
    try:
        return datetime.strptime(ts, "%Y-%m-%dT%H:%M:%S%z")
    except ValueError:
        return None


def serie(samples: Path, nombre: str = "app") -> list[tuple[str, str, dict]]:
    """(ts, boot_id, reclaim) del slice, en orden de ts; solo muestras que traen `reclaim`."""
    out: list[tuple[str, str, dict]] = []
    for f in sorted(samples.glob("*.jsonl")):
        for linea in f.read_text(encoding="utf-8", errors="replace").splitlines():
            if '"reclaim"' not in linea:
                continue
            try:
                o = json.loads(linea)
            except ValueError:
                continue
            for s in o.get("slices") or []:
                if isinstance(s, dict) and s.get("slice") == nombre and isinstance(s.get("reclaim"), dict):
                    out.append((str(o.get("ts", "")), str(o.get("boot_id", "")), s["reclaim"]))
    out.sort(key=lambda x: x[0])
    return out


def deltas(s: list[tuple[str, str, dict]]) -> list[dict]:
    """Una fila por par de muestras consecutivas: delta de cada contador y parte directa."""
    filas = []
    for (ts0, b0, r0), (ts1, b1, r1) in zip(s, s[1:]):
        nums = [(r0.get(c), r1.get(c)) for c in CONTADORES]
        reinicio = b0 != b1 or any(isinstance(a, int) and isinstance(b, int) and b < a for a, b in nums)
        fila: dict = {"ts": ts1, "reinicio": reinicio}
        for c, (a, b) in zip(CONTADORES, nums):
            if not isinstance(a, int) or not isinstance(b, int):
                fila[c] = NC
            else:
                fila[c] = b if reinicio else b - a
        h0, h1 = _hora(ts0), _hora(ts1)
        fila["minutos"] = None if h0 is None or h1 is None else (h1 - h0).total_seconds() / 60
        fila["parte_directo"] = parte_directo(fila)
        filas.append(fila)
    return filas


def _en_ventana(ts: str, desde: str | None, hasta: str | None) -> bool:
    # Comparacion por prefijo de texto: `ts` es ISO local y `--desde/--hasta` tambien.
    return (desde is None or ts[:len(desde)] >= desde) and (hasta is None or ts[:len(hasta)] <= hasta)


def _fmt(v) -> str:
    return "-" if v is None else f"{v:.1f}" if isinstance(v, float) else str(v)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--samples", type=Path, default=DATA_DIR / "samples")
    ap.add_argument("--slice", default="app", choices=("app", "docker", "system"))
    ap.add_argument("--desde", help="prefijo ISO local, p. ej. 2026-10-17T18:00")
    ap.add_argument("--hasta", help="prefijo ISO local, inclusivo")
    a = ap.parse_args(argv)

    s = [x for x in serie(a.samples, a.slice) if _en_ventana(x[0], a.desde, a.hasta)]
    if len(s) < 2:
        print(f"COULD_NOT_RUN: {len(s)} muestra(s) con `reclaim` del slice {a.slice} en la ventana; "
              "hacen falta dos", file=sys.stderr)
        return 2
    filas = deltas(s)
    print(f"{'ts':25} {'min':>5} {'refault_file':>13} {'pgscan_direct':>14} {'pgscan_kswapd':>14} {'directo':>8}")
    for f in filas:
        p = f["parte_directo"]
        print(f"{f['ts']:25} {_fmt(f['minutos']):>5} {_fmt(f['refault_file']):>13} "
              f"{_fmt(f['pgscan_direct']):>14} {_fmt(f['pgscan_kswapd']):>14} "
              f"{'-' if p is None else f'{p:.1%}':>8}{'  REINICIO' if f['reinicio'] else ''}")
    tot = {c: sum(f[c] for f in filas if isinstance(f[c], int)) for c in CONTADORES}
    nc = {c: sum(1 for f in filas if f[c] == NC) for c in CONTADORES}
    p = parte_directo(tot)
    # El refault cuenta paginas; el tamano de pagina de ESTA maquina lo traduce a volumen releido.
    print(f"ventana: {len(filas)} intervalos | refault_file {tot['refault_file']} "
          f"(~{tot['refault_file'] * os.sysconf('SC_PAGE_SIZE') / 1024 ** 3:.1f} GiB releidos) | pgscan_direct {tot['pgscan_direct']} "
          f"| pgscan_kswapd {tot['pgscan_kswapd']} | directo {'-' if p is None else f'{p * 100:.1f} %'} "
          f"| NOT_COLLECTED {sum(nc.values())}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
