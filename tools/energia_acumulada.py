#!/usr/bin/env python3
"""Cálculo de energía acumulada por hora y por día (FEATURE-ENERGIA-ACUMULADA-DEL-ENCHUFE-01).

Integra potencia por trapecio sobre lecturas `ok: true` o lee contador acumulado si existe,
declarando `energia_fuente` ("contador" | "integrada" | "NOT_COLLECTED"). Nunca rellena huecos
mayores a `max_hueco_s` ni trata lecturas `ok: false` como 0 W.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

MAX_HUECO_S_DEFECTO = 300.0


def _num(v: Any) -> float | None:
    return float(v) if isinstance(v, (int, float)) and not isinstance(v, bool) else None


def _integrar_ventana(
    filas: list[dict[str, Any]],
    inicio: float,
    fin: float,
    max_hueco_s: float,
) -> dict[str, Any]:
    en_ventana = sorted(
        (f for f in filas if _num(f.get("epoch")) is not None and inicio <= float(f["epoch"]) <= fin),
        key=lambda f: float(f["epoch"]),
    )
    buenas = [f for f in en_ventana if f.get("ok") is True and _num(f.get("potencia_w")) is not None]
    if not buenas:
        return {
            "wh": None,
            "energia_fuente": "NOT_COLLECTED",
            "huecos": len(en_ventana),
            "cobertura_pct": 0.0,
            "potencia_media_w": None,
            "potencia_min_w": None,
            "potencia_max_w": None,
            "muestras_ok": 0,
        }

    # Si todas las filas buenas traen contador monótono `energia_total_wh`, se usa el contador.
    contadores = [_num(f.get("energia_total_wh")) for f in buenas]
    tiene_contador = all(c is not None for c in contadores) and len(buenas) >= 2 and contadores[-1] >= contadores[0]  # type: ignore[operator]

    wh = 0.0
    huecos = 0
    cubierto_s = 0.0
    # Detectar si hubo fallas ok=false entre dos muestras buenas consecutivas.
    idx_buenas = [i for i, f in enumerate(en_ventana) if f.get("ok") is True and _num(f.get("potencia_w")) is not None]

    for k in range(len(idx_buenas) - 1):
        i1, i2 = idx_buenas[k], idx_buenas[k + 1]
        f1, f2 = en_ventana[i1], en_ventana[i2]
        t1, t2 = float(f1["epoch"]), float(f2["epoch"])
        dt = t2 - t1
        hay_falla_intermedia = any(en_ventana[j].get("ok") is False for j in range(i1 + 1, i2))
        if dt <= 0 or dt > max_hueco_s or hay_falla_intermedia:
            huecos += 1
            continue
        cubierto_s += dt
        if tiene_contador:
            wh += float(f2["energia_total_wh"]) - float(f1["energia_total_wh"])
        else:
            p1, p2 = float(f1["potencia_w"]), float(f2["potencia_w"])
            wh += ((p1 + p2) * 0.5) * (dt / 3600.0)

    if any(f.get("ok") is False for f in en_ventana) and huecos == 0:
        huecos = sum(1 for f in en_ventana if f.get("ok") is False)

    span = max(fin - inicio, 1.0)
    cobertura_pct = round(min(100.0, max(0.0, (cubierto_s / span) * 100.0)), 2)
    pots = [float(f["potencia_w"]) for f in buenas]
    return {
        "wh": round(wh, 3) if len(buenas) >= 2 else None,
        "energia_fuente": ("contador" if tiene_contador else "integrada") if len(buenas) >= 2 else "NOT_COLLECTED",
        "huecos": huecos,
        "cobertura_pct": cobertura_pct,
        "potencia_media_w": round(sum(pots) / len(pots), 2),
        "potencia_min_w": round(min(pots), 2),
        "potencia_max_w": round(max(pots), 2),
        "muestras_ok": len(buenas),
    }


def resumen_energia(
    filas: Iterable[dict[str, Any]],
    ahora: float | None = None,
    max_hueco_s: float = MAX_HUECO_S_DEFECTO,
) -> dict[str, Any]:
    lista = list(filas)
    t = datetime.now(timezone.utc).timestamp() if ahora is None else ahora
    dt_utc = datetime.fromtimestamp(t, timezone.utc)
    inicio_hoy = datetime(dt_utc.year, dt_utc.month, dt_utc.day, tzinfo=timezone.utc).timestamp()
    inicio_ayer = inicio_hoy - 86400.0

    hora = _integrar_ventana(lista, t - 3600.0, t, max_hueco_s)
    hoy = _integrar_ventana(lista, inicio_hoy, t, max_hueco_s)
    ayer = _integrar_ventana(lista, inicio_ayer, inicio_hoy, max_hueco_s)

    return {
        "ts": dt_utc.isoformat(),
        "epoch": t,
        "wh_ultima_hora": hora["wh"],
        "wh_hoy": hoy["wh"],
        "wh_ayer": ayer["wh"],
        "energia_fuente": hoy["energia_fuente"] if hoy["wh"] is not None else hora["energia_fuente"],
        "potencia_media_w": hoy["potencia_media_w"],
        "potencia_min_w": hoy["potencia_min_w"],
        "potencia_max_w": hoy["potencia_max_w"],
        "cobertura_pct": hoy["cobertura_pct"],
        "huecos": hoy["huecos"],
        "ultima_hora": hora,
        "hoy": hoy,
        "ayer": ayer,
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="energia_acumulada")
    ap.add_argument("archivo", type=Path, help="Serie energia.jsonl")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
    if not args.archivo.is_file():
        print(json.dumps({"estado": "COULD_NOT_RUN", "motivo": f"no existe {args.archivo}"}))
        return 2
    filas = []
    for ln in args.archivo.read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            f = json.loads(ln)
            if isinstance(f, dict):
                filas.append(f)
        except ValueError:
            continue
    res = resumen_energia(filas)
    print(json.dumps(res, ensure_ascii=False, indent=2 if not args.json else None))
    return 0


if __name__ == "__main__":
    sys.exit(main())
