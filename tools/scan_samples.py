"""Filtra muestras JSONL para bb scan y declara datos imposibles de analizar."""

from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path
from typing import Any


def _epoch(valor: Any) -> float | None:
    if not isinstance(valor, str):
        return None
    try:
        fecha = dt.datetime.fromisoformat(valor)
    except ValueError:
        return None
    if fecha.tzinfo is None:
        fecha = fecha.astimezone().astimezone(dt.timezone.utc)
    return fecha.timestamp()


def _pares(valor: Any, ancho: int) -> dict[str, tuple[int, ...]]:
    salida: dict[str, tuple[int, ...]] = {}
    if not isinstance(valor, str):
        return salida
    try:
        for token in valor.split(","):
            partes = token.split(":")
            if len(partes) != ancho or not partes[0]:
                return {}
            salida[partes[0]] = tuple(int(n) for n in partes[1:])
    except ValueError:
        return {}
    return salida


def asociar_cpu_gpu(thermal: list[dict], sample_paths: list[Path],
                    inicio: float, fin: float) -> list[str]:
    """Anota actividad CPU del PID GPU solo si boot y tiempo coinciden."""
    muestras_cpu = []
    razones = []
    for ruta in sample_paths:
        try:
            lineas = ruta.read_text(encoding="utf-8").splitlines()
        except (OSError, UnicodeError) as exc:
            razones.append(f"correlación GPU/CPU: no se pudo leer {ruta}: {exc}")
            continue
        invalidas = 0
        for linea in lineas:
            try:
                dato = json.loads(linea)
            except (json.JSONDecodeError, UnicodeError):
                invalidas += 1
                continue
            if not isinstance(dato, dict):
                continue
            marca = _epoch(dato.get("ts"))
            if marca is not None and inicio <= marca <= fin and dato.get("boot_id"):
                muestras_cpu.append((marca, dato))
        if invalidas:
            razones.append(f"correlación GPU/CPU: {invalidas} línea(s) JSONL inválidas en {ruta}")
    muestras_cpu.sort(key=lambda par: par[0])
    sin_correlacion = False
    procesos_cache = None
    procesos_cache_ts = None
    for dato in thermal:
        dato["scan_cpu_work_pids"] = []
        marca = _epoch(dato.get("ts"))
        if "gpu_procs" in dato:
            procesos = dato["gpu_procs"]
            if isinstance(procesos, list) and procesos:
                procesos_cache = procesos
                procesos_cache_ts = marca
            else:
                procesos_cache = None
                procesos_cache_ts = None
        elif (marca is not None and procesos_cache_ts is not None and
              marca - procesos_cache_ts <= 30):
            procesos = procesos_cache
        else:
            procesos_cache = None
            procesos_cache_ts = None
            procesos = None
        if (dato.get("gpu_util_pct") != 0 or
                not isinstance(dato.get("vllm_num_requests_running"), (int, float)) or
                dato.get("vllm_num_requests_running", 0) <= 0 or not procesos):
            continue
        boot = dato.get("boot_id")
        if marca is None or not boot:
            sin_correlacion = True
            continue
        candidato = next((m for t, m in reversed(muestras_cpu)
                          if m.get("boot_id") == boot and 0 <= marca - t <= 90), None)
        if candidato is None:
            sin_correlacion = True
            continue
        cpu_pids = {str(p.get("pid")) for p in candidato.get("cpu_top", [])
                    if isinstance(p, dict) and isinstance(p.get("cpu_s"), (int, float))
                    and p["cpu_s"] > 0}
        dato["scan_cpu_work_pids"] = sorted(
            str(p.get("pid")) for p in procesos
            if isinstance(p, dict) and str(p.get("pid")) in cpu_pids)
        if not dato["scan_cpu_work_pids"]:
            sin_correlacion = True
    if sin_correlacion:
        razones.append("fallback GPU/CPU: carga GPU presente sin atribución CPU temporal y por PID")
    return razones


def preparar(rutas: list[Path], inicio: float, fin: float,
             tipo: str = "muestras") -> tuple[list[dict], list[str]]:
    filas: list[tuple[float, dict]] = []
    razones: list[str] = []
    invalidas = 0
    ts_invalidos = 0
    for ruta in rutas:
        try:
            lineas = ruta.read_text(encoding="utf-8").splitlines()
        except (OSError, UnicodeError) as exc:
            razones.append(f"{ruta}: no se pudo leer: {exc}")
            continue
        for n, linea in enumerate(lineas, 1):
            if not linea.strip():
                continue
            try:
                dato = json.loads(linea)
            except (json.JSONDecodeError, UnicodeError):
                invalidas += 1
                continue
            if not isinstance(dato, dict):
                invalidas += 1
                continue
            marca = _epoch(dato.get("ts"))
            if marca is None:
                ts_invalidos += 1
                continue
            if inicio <= marca <= fin:
                filas.append((marca, dato))
    filas.sort(key=lambda par: par[0])
    if invalidas:
        razones.append(f"{invalidas} línea(s) JSONL inválidas")
    if ts_invalidos:
        razones.append(f"{ts_invalidos} objeto(s) sin timestamp ISO válido")
    datos = [dato for _, dato in filas]
    if not datos:
        razones.append("ninguna muestra JSON válida dentro de la ventana")
        return datos, razones

    if tipo == "muestras":
        campos_validos = {
            "mem_free_kb": lambda v: isinstance(v, (int, float)),
            "zombies": lambda v: isinstance(v, int),
            "apps": lambda v: isinstance(v, list),
            "psi": lambda v: isinstance(v, dict) and any(
                isinstance(v.get(k), (int, float))
                for k in ("mem_full", "mem_some", "cpu_some", "io_some")),
            "gateway": lambda v: isinstance(v, str) and bool(v),
            "gw_salud": lambda v: isinstance(v, str) and len(v.split(",")) >= 7,
            "py_bg": lambda v: isinstance(v, list),
            "top_rss": lambda v: isinstance(v, list),
        }
        for campo, valida in campos_validos.items():
            if not any(valida(dato.get(campo)) for dato in datos):
                razones.append(f"{campo}: ninguna muestra trae dato utilizable")
        boots = [d.get("boot_id") for d in datos if d.get("boot_id")]
        boot_actual = boots[-1] if boots else None
        if boots:
            # Tasas acumulativas solo se calculan dentro del boot más reciente.
            for dato in datos:
                if dato.get("boot_id") != boot_actual:
                    dato.pop("cpu_jiffies", None)
                    dato.pop("red", None)
        else:
            for dato in datos:
                dato.pop("cpu_jiffies", None)
                dato.pop("red", None)
        for campo, ancho in (("cpu_jiffies", 3), ("red", 3)):
            candidatos = [d for d in datos
                          if d.get("boot_id") == boot_actual and
                          _pares(d.get(campo), ancho)]
            por_boot: dict[str, list[dict]] = {}
            for d in candidatos:
                boot = d.get("boot_id")
                if boot:
                    por_boot.setdefault(boot, []).append(d)
            if len(candidatos) >= 2 and not por_boot:
                razones.append(f"{campo}: no se puede cruzar boot sin boot_id")
            elif not any(len(grupo) >= 2 for grupo in por_boot.values()):
                razones.append(f"{campo}: faltan dos muestras utilizables del mismo boot")
            grupo = por_boot.get(boot_actual or "", [])
            for anterior, actual in zip(grupo, grupo[1:]):
                a = _pares(anterior.get(campo), ancho)
                b = _pares(actual.get(campo), ancho)
                if _epoch(actual.get("ts")) == _epoch(anterior.get("ts")):
                    razones.append(f"{campo}: timestamps duplicados; tasa no calculable")
                    break
                if any(k in a and any(x < y for x, y in zip(b[k], a[k])) for k in b):
                    razones.append(f"{campo}: contador retrocedió; tasa no calculable")
                    break
        if not boots:
            razones.append("tasas CPU/red: el histórico no registra boot_id")
    else:
        validadores = {
            "evento": lambda v: isinstance(v, str) and bool(v),
            "gpu_temp_c": lambda v: isinstance(v, (int, float)),
            "sm_clk_mhz": lambda v: isinstance(v, (int, float)),
            "gpu_util_pct": lambda v: isinstance(v, (int, float)),
            "throttle": lambda v: isinstance(v, str) and bool(v),
            "gpu_procs": lambda v: isinstance(v, list),
            "vllm_num_requests_running": lambda v: isinstance(v, (int, float)),
        }
        for campo, valida in validadores.items():
            if not any(valida(dato.get(campo)) for dato in datos):
                razones.append(f"termica/{campo}: falta dato utilizable para el análisis")

    return datos, razones


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--since", type=float, required=True, help="inicio UTC, epoch")
    parser.add_argument("--until", type=float, required=True, help="fin UTC, epoch")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--status", type=Path, required=True)
    parser.add_argument("--kind", choices=("muestras", "termica"), default="muestras")
    parser.add_argument("--cpu-input", action="append", type=Path, default=[])
    parser.add_argument("inputs", nargs="+", type=Path)
    args = parser.parse_args(argv)
    if args.since > args.until:
        parser.error("--since debe ser anterior a --until")
    datos, razones = preparar(args.inputs, args.since, args.until, args.kind)
    if args.kind == "termica" and args.cpu_input:
        razones.extend(asociar_cpu_gpu(datos, args.cpu_input, args.since, args.until))
    args.output.write_text("".join(json.dumps(d, ensure_ascii=False) + "\n"
                                      for d in datos), encoding="utf-8")
    status = {"input_files": len(args.inputs), "in_window": len(datos),
              "could_not_run": len(razones), "reasons": razones}
    args.status.write_text(json.dumps(status, ensure_ascii=False), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
