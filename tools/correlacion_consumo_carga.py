#!/usr/bin/env python3
"""Log alineado cada 5s y correlación consumo-carga (FEATURE-METRICAS-LOG-Y-CORRELACION-CONSUMO-CARGA-01)."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import math
import os
from pathlib import Path
import sys
from typing import Any, Sequence

MAX_LOG_BYTES_DEFECTO = 16 * 1024 * 1024
ROTACIONES_MAX = 5
MIN_MUESTRAS_CORRELACION = 5


def _num(v: Any) -> float | None:
    return float(v) if isinstance(v, (int, float)) and not isinstance(v, bool) else None


def clasificar_regimen(fila: dict[str, Any], *, umbral_cpu: float = 0.25, umbral_gpu: float = 15.0) -> str:
    cpu = _num(fila.get("psi_cpu"))
    gpu = _num(fila.get("gpu_util_pct"))
    reqs = _num(fila.get("vllm_reqs_activas"))
    cpu_alta = (cpu is not None and cpu >= umbral_cpu)
    gpu_alta = (gpu is not None and gpu >= umbral_gpu) or (reqs is not None and reqs > 0)
    if cpu_alta and gpu_alta:
        return "mixto"
    if gpu_alta:
        return "gpu"
    if cpu_alta:
        return "cpu"
    return "reposo"


def construir_fila_alineada(
    ts: float,
    *,
    enchufe: dict[str, Any] | None = None,
    gpu: dict[str, Any] | None = None,
    host: dict[str, Any] | None = None,
    inferencia: dict[str, Any] | None = None,
) -> dict[str, Any]:
    e = enchufe or {}
    g = gpu or {}
    h = host or {}
    inf = inferencia or {}
    fila: dict[str, Any] = {
        "ts": datetime.fromtimestamp(ts, timezone.utc).isoformat(),
        "epoch": ts,
        "potencia_w": _num(e.get("potencia_w")) if _num(e.get("potencia_w")) is not None else "NOT_COLLECTED",
        "voltaje_v": _num(e.get("voltaje_v")) if _num(e.get("voltaje_v")) is not None else "NOT_COLLECTED",
        "corriente_a": _num(e.get("corriente_a")) if _num(e.get("corriente_a")) is not None else "NOT_COLLECTED",
        "gpu_potencia_w": _num(g.get("gpu_potencia_w")) if _num(g.get("gpu_potencia_w")) is not None else "NOT_COLLECTED",
        "gpu_util_pct": _num(g.get("gpu_util_pct")) if _num(g.get("gpu_util_pct")) is not None else "NOT_COLLECTED",
        "gpu_reloj_mhz": _num(g.get("gpu_reloj_mhz")) if _num(g.get("gpu_reloj_mhz")) is not None else "NOT_COLLECTED",
        "psi_cpu": _num(h.get("psi_cpu")) if _num(h.get("psi_cpu")) is not None else "NOT_COLLECTED",
        "psi_mem": _num(h.get("psi_mem")) if _num(h.get("psi_mem")) is not None else "NOT_COLLECTED",
        "psi_io": _num(h.get("psi_io")) if _num(h.get("psi_io")) is not None else "NOT_COLLECTED",
        "mem_available_mb": _num(h.get("mem_available_mb")) if _num(h.get("mem_available_mb")) is not None else "NOT_COLLECTED",
        "temp_max_c": _num(h.get("temp_max_c")) if _num(h.get("temp_max_c")) is not None else "NOT_COLLECTED",
        "vllm_reqs_activas": _num(inf.get("reqs_activas")) if _num(inf.get("reqs_activas")) is not None else "NOT_COLLECTED",
        "vllm_reqs_espera": _num(inf.get("reqs_espera")) if _num(inf.get("reqs_espera")) is not None else "NOT_COLLECTED",
        "vllm_kv_pct": _num(inf.get("kv_pct")) if _num(inf.get("kv_pct")) is not None else "NOT_COLLECTED",
        "vllm_tok_s": _num(inf.get("tok_s")) if _num(inf.get("tok_s")) is not None else "NOT_COLLECTED",
    }
    fila["regimen"] = clasificar_regimen(fila)
    return fila


def anexar_log_con_tope(
    ruta: Path,
    fila: dict[str, Any],
    *,
    max_bytes: int = MAX_LOG_BYTES_DEFECTO,
    copias: int = ROTACIONES_MAX,
) -> None:
    ruta.parent.mkdir(parents=True, exist_ok=True)
    linea = json.dumps(fila, ensure_ascii=False, separators=(",", ":")) + "\n"
    if ruta.exists() and ruta.stat().st_size + len(linea.encode("utf-8")) > max_bytes:
        for i in range(copias, 0, -1):
            src = ruta if i == 1 else ruta.with_name(f"{ruta.name}.{i - 1}")
            dst = ruta.with_name(f"{ruta.name}.{i}")
            if src.exists():
                os.replace(src, dst)
    with ruta.open("a", encoding="utf-8") as fh:
        fh.write(linea)


def _pearson(xs: list[float], ys: list[float]) -> float | None:
    n = len(xs)
    if n < 2:
        return None
    mx = sum(xs) / n
    my = sum(ys) / n
    vx = sum((x - mx) ** 2 for x in xs)
    vy = sum((y - my) ** 2 for y in ys)
    if vx <= 0 or vy <= 0:
        return None
    cov = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    return round(cov / math.sqrt(vx * vy), 4)


def _ranks(vals: list[float]) -> list[float]:
    orden = sorted((v, i) for i, v in enumerate(vals))
    ranks = [0.0] * len(vals)
    i = 0
    while i < len(orden):
        j = i
        while j + 1 < len(orden) and orden[j + 1][0] == orden[i][0]:
            j += 1
        avg_r = (i + j) / 2.0 + 1.0
        for k in range(i, j + 1):
            ranks[orden[k][1]] = avg_r
        i = j + 1
    return ranks


def _spearman(xs: list[float], ys: list[float]) -> float | None:
    return _pearson(_ranks(xs), _ranks(ys))


def informe_correlacion(
    filas: Sequence[dict[str, Any]],
    *,
    metrica_carga: str = "gpu_util_pct",
    desfases_pasos: Sequence[int] = (-2, -1, 0, 1, 2),
    min_muestras: int = MIN_MUESTRAS_CORRELACION,
) -> dict[str, Any]:
    ordenadas = sorted((f for f in filas if _num(f.get("epoch")) is not None), key=lambda f: float(f["epoch"]))
    reposo_w = [
        float(f["potencia_w"]) for f in ordenadas
        if clasificar_regimen(f) == "reposo" and _num(f.get("potencia_w")) is not None
    ]
    base_reposo_w = round(min(reposo_w), 2) if len(reposo_w) >= min_muestras else "NOT_COLLECTED"

    por_regimen: dict[str, Any] = {}
    for reg in ("reposo", "cpu", "gpu", "mixto"):
        sub = [f for f in ordenadas if clasificar_regimen(f) == reg]
        mejor: dict[str, Any] | None = None
        for lag in desfases_pasos:
            xs, ys = [], []
            for i, f in enumerate(sub):
                j = i + lag
                if 0 <= j < len(sub):
                    p = _num(sub[j].get("potencia_w"))
                    c = _num(f.get(metrica_carga))
                    if p is not None and c is not None:
                        xs.append(c)
                        ys.append(p)
            if len(xs) < min_muestras:
                continue
            r_p = _pearson(xs, ys)
            r_s = _spearman(xs, ys)
            if r_p is None or r_s is None:
                continue
            cand = {
                "estado": "OK",
                "n": len(xs),
                "lag_pasos": lag,
                "pearson": r_p,
                "spearman": r_s,
            }
            if mejor is None or abs(cand["pearson"]) > abs(mejor["pearson"]):
                mejor = cand
        if mejor is None:
            por_regimen[reg] = {"estado": "COULD_NOT_RUN", "n": len(sub), "motivo": f"muestras insuficientes (< {min_muestras}) o varianza nula"}
        else:
            por_regimen[reg] = mejor

    return {
        "metrica_carga": metrica_carga,
        "consumo_reposo_w": base_reposo_w,
        "confusores_declarados": ["temp_max_c", "ventiladores"],
        "por_regimen": por_regimen,
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="correlacion_consumo_carga")
    ap.add_argument("log", type=Path)
    ap.add_argument("--metrica", default="gpu_util_pct")
    args = ap.parse_args(argv)
    if not args.log.is_file():
        print(json.dumps({"estado": "COULD_NOT_RUN", "motivo": f"no existe {args.log}"}))
        return 2
    filas = [json.loads(ln) for ln in args.log.read_text(encoding="utf-8", errors="replace").splitlines() if ln.strip()]
    print(json.dumps(informe_correlacion(filas, metrica_carga=args.metrica), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
