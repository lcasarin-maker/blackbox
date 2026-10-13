"""Atribucion de un enjambre de procesos con las muestras de bb, solo lectura.

DEBT-COLAPSO-05-OCT-ENJAMBRE-DE-PROCESOS-SIN-TECHO-01. Responde dos preguntas
con las muestras por minuto de `~/.local/share/blackbox/samples`:

1. QUIEN crecio en la ventana: por `comm`, cuantos pids distintos y cuanto
   creci el mayor (`pidio.crecio_kb` es crecimiento de tamano VIRTUAL, no RSS:
   un `java` de 34 GiB virtuales no son 34 GiB de RAM). Las muestras no llevan
   scope por pid, asi que la atribucion a un scope es solo por pid coincidente
   con el nombre `...Claude-<pid>.scope`; el resto queda `sin_scope`.
2. QUE TECHO habria avisado a tiempo: para cada serie de memoria (el scope de
   Claude si existe `claude_scopes`, y `app.slice`), el instante en que cruza
   cada candidato frente al primer PSI memory-full >= corte, y el MAXIMO que la
   misma serie alcanzo con PSI sano. Un techo por debajo de ese maximo sano
   mataria carga legitima; por encima del pico del incidente no habria
   avisado. Si no hay hueco entre ambos, `separable` es false: la memoria
   sola no discrimina y eso es el hallazgo, no un fallo del instrumento.

Nunca envia senales ni cambia limites. Lo que no se pudo leer se cuenta
(`lineas_ilegibles`, `registros_sin_psi`); si no hay muestras en la ventana el
resultado es `could_not_run`, jamas un informe vacio con aspecto de limpio.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path

CORTE_PSI = 10.0  # el corte calibrado de bb-usable / bb sample
KIB_GIB = 1024 * 1024
_PID_EN_UNIDAD = re.compile(r"Claude-(\d+)\.scope$")
SAMPLES = Path.home() / ".local/share/blackbox/samples"


def cargar(rutas: list[Path]) -> tuple[list[dict], int]:
    """Registros validos y cuantas lineas no se pudieron leer (se cuentan)."""
    registros: list[dict] = []
    ilegibles = 0
    for ruta in rutas:
        for linea in ruta.read_text(encoding="utf-8").splitlines():
            if not linea.strip():
                continue
            try:
                r = json.loads(linea)
            except json.JSONDecodeError:
                ilegibles += 1  # anotado, no silenciado
                continue
            if isinstance(r, dict) and isinstance(r.get("ts"), str):
                registros.append(r)
            else:
                ilegibles += 1
    return registros, ilegibles


def _t(r: dict) -> datetime:
    return datetime.fromisoformat(r["ts"])


def ventana(registros: list[dict], desde: str, hasta: str) -> list[dict]:
    d, h = datetime.fromisoformat(desde), datetime.fromisoformat(hasta)
    return sorted((r for r in registros if d <= _t(r) <= h), key=_t)


def _psi(r: dict) -> float | None:
    v = (r.get("psi") or {}).get("mem_full")
    return float(v) if isinstance(v, (int, float)) else None


def quien_crecio(regs: list[dict]) -> list[dict]:
    """Por comm: pids distintos vistos (cota inferior: solo los top por muestra)."""
    por: dict[str, dict] = {}
    for r in regs:
        for p in r.get("pidio") or []:
            c = por.setdefault(p["comm"], {"comm": p["comm"], "pids": set(),
                                           "max_crecio_kb": 0, "primero": r["ts"]})
            c["pids"].add(p["pid"])
            c["max_crecio_kb"] = max(c["max_crecio_kb"], p["crecio_kb"])
    out = [{**c, "pids": len(c["pids"])} for c in por.values()]
    return sorted(out, key=lambda c: c["max_crecio_kb"], reverse=True)


def scopes_por_pid(regs: list[dict]) -> dict[int, str]:
    """pid -> unidad, cuando un scope `Claude-<pid>` aparece en `claude_scopes`
    o el pid de `pidio` coincide con el de una unidad vista en la ventana."""
    pids: dict[int, str] = {}
    for r in regs:
        for s in r.get("claude_scopes") or []:
            m = _PID_EN_UNIDAD.search(s.get("unit", ""))
            if m:
                pids[int(m.group(1))] = s["unit"]
    return pids


def series(regs: list[dict]) -> dict[str, list[tuple[datetime, int, float | None]]]:
    """nombre -> [(ts, memoria_kb, psi_full)]: app.slice y cada scope Claude."""
    out: dict[str, list] = {}
    for r in regs:
        psi = _psi(r)
        for s in r.get("slices") or []:
            if s.get("slice") == "app" and isinstance(s.get("cur_kb"), int):
                out.setdefault("app.slice", []).append((_t(r), s["cur_kb"], psi))
        for s in r.get("claude_scopes") or []:
            if s.get("state") == "ok" and isinstance(s.get("memory_current_kb"), int):
                out.setdefault(s["unit"], []).append((_t(r), s["memory_current_kb"], psi))
    return out


def _gib(kb: float) -> float:
    return round(kb / KIB_GIB, 2)


def techo(serie: list, sano: list, candidatos_gib: list[float]) -> dict:
    """`serie`: puntos del incidente; `sano`: puntos con PSI sano (toda la
    historia). Para cada candidato: cruza o no, y cuantos segundos antes del
    primer PSI >= corte."""
    t_psi = next((t for t, _, p in serie if p is not None and p >= CORTE_PSI), None)
    pico = max((m for _, m, _ in serie), default=0)
    sano_max = max((m for _, m, p in sano if p is not None and p < CORTE_PSI), default=0)
    filas = []
    for g in candidatos_gib:
        t_cruce = next((t for t, m, _ in serie if m >= g * KIB_GIB), None)
        adelanto = None
        if t_cruce is not None and t_psi is not None:
            adelanto = round((t_psi - t_cruce).total_seconds())
        filas.append({"techo_gib": g, "cruza": t_cruce is not None,
                      "adelanto_s": adelanto,
                      "mataria_carga_sana": g * KIB_GIB <= sano_max})
    return {"pico_incidente_gib": _gib(pico), "maximo_sano_gib": _gib(sano_max),
            "primer_psi_alto": t_psi.isoformat() if t_psi else None,
            "separable": pico > sano_max, "margen_gib": _gib(pico - sano_max),
            "candidatos": filas}


def analizar(registros: list[dict], desde: str, hasta: str, ilegibles: int = 0,
             candidatos_gib: list[float] | None = None) -> dict:
    regs = ventana(registros, desde, hasta)
    if not regs:
        return {"veredicto": "could_not_run", "porque": "sin muestras en la ventana",
                "lineas_ilegibles_corpus": ilegibles}
    cand = candidatos_gib or [30.0, 34.0, 36.0, 38.0, 40.0]
    todas = series(registros)
    en_ventana = series(regs)
    pid2u = scopes_por_pid(regs)
    crecio = quien_crecio(regs)
    for c in crecio:
        c["scope"] = "sin_scope"
    for r in regs:
        for p in r.get("pidio") or []:
            if p["pid"] in pid2u:
                for c in crecio:
                    if c["comm"] == p["comm"]:
                        c["scope"] = pid2u[p["pid"]]
    return {
        "veredicto": "ok",
        "ventana": [desde, hasta],
        "muestras": len(regs),
        "registros_sin_psi": sum(1 for r in regs if _psi(r) is None),
        "lineas_ilegibles_corpus": ilegibles,
        "psi_max": max((p for r in regs if (p := _psi(r)) is not None), default=None),
        "quien_crecio": [{**c, "max_crecio_gib_virtual": _gib(c["max_crecio_kb"])}
                         for c in crecio[:10]],
        "series_sin_datos": [] if en_ventana else ["ni app.slice ni claude_scopes en la ventana"],
        "techos": {n: techo(s, todas[n], cand) for n, s in en_ventana.items()},
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=(__doc__ or "").split("\n")[0])
    ap.add_argument("--desde", required=True, help="ISO con zona, p.ej. 2026-10-05T00:00:00-06:00")
    ap.add_argument("--hasta", required=True)
    ap.add_argument("--samples", type=Path, default=SAMPLES)
    ap.add_argument("--techo-gib", type=float, action="append", default=None)
    a = ap.parse_args(argv)
    rutas = sorted(a.samples.glob("*.jsonl"))
    if not rutas:
        print(json.dumps({"veredicto": "could_not_run", "porque": "sin archivos de muestras"}))
        return 2
    registros, ilegibles = cargar(rutas)
    res = analizar(registros, a.desde, a.hasta, ilegibles, a.techo_gib)
    print(json.dumps(res, indent=2, ensure_ascii=False))
    return 0 if res["veredicto"] == "ok" else 2


if __name__ == "__main__":
    sys.exit(main())
