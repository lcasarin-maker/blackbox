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


def _leer_muestras_cpu(sample_paths: list[Path], inicio: float,
                        fin: float) -> tuple[list[tuple[float, dict]], list[str]]:
    muestras = []
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
                muestras.append((marca, dato))
        if invalidas:
            razones.append(f"correlación GPU/CPU: {invalidas} línea(s) JSONL inválidas en {ruta}")
    muestras.sort(key=lambda par: par[0])
    return muestras, razones


def _procesos_gpu_actuales(dato: dict, marca: float | None,
                           cache: list | None, cache_ts: float | None
                           ) -> tuple[list | None, list | None, float | None]:
    if "gpu_procs" in dato:
        procesos = dato["gpu_procs"]
        if isinstance(procesos, list) and procesos:
            return procesos, procesos, marca
        return procesos, None, None
    if (marca is not None and cache_ts is not None and
            marca - cache_ts <= 30):
        return cache, cache, cache_ts
    return None, None, None


def _atribuir_procesos_cpu(dato: dict, marca: float | None,
                           procesos: list | None,
                           muestras_cpu: list[tuple[float, dict]]) -> bool:
    dato["scan_cpu_work_pids"] = []
    if (dato.get("gpu_util_pct") != 0 or
            not isinstance(dato.get("vllm_num_requests_running"), (int, float)) or
            dato.get("vllm_num_requests_running", 0) <= 0 or not procesos):
        return False
    boot = dato.get("boot_id")
    if marca is None or not boot:
        return True
    candidato = next((m for t, m in reversed(muestras_cpu)
                      if m.get("boot_id") == boot and 0 <= marca - t <= 90), None)
    if candidato is None:
        return True
    cpu_pids = {str(proceso.get("pid")) for proceso in candidato.get("cpu_top", [])
                if isinstance(proceso, dict) and
                isinstance(proceso.get("cpu_s"), (int, float)) and
                proceso["cpu_s"] > 0}
    dato["scan_cpu_work_pids"] = sorted(
        str(proceso.get("pid")) for proceso in procesos
        if isinstance(proceso, dict) and str(proceso.get("pid")) in cpu_pids)
    return not dato["scan_cpu_work_pids"]


def asociar_cpu_gpu(thermal: list[dict], sample_paths: list[Path],
                    inicio: float, fin: float) -> list[str]:
    """Anota actividad CPU del PID GPU solo si boot y tiempo coinciden."""
    muestras_cpu, razones = _leer_muestras_cpu(sample_paths, inicio, fin)
    sin_correlacion = False
    procesos_cache = None
    procesos_cache_ts = None
    for dato in thermal:
        marca = _epoch(dato.get("ts"))
        procesos, procesos_cache, procesos_cache_ts = _procesos_gpu_actuales(
            dato, marca, procesos_cache, procesos_cache_ts)
        if _atribuir_procesos_cpu(dato, marca, procesos, muestras_cpu):
            sin_correlacion = True
    if sin_correlacion:
        razones.append("fallback GPU/CPU: carga GPU presente sin atribución CPU temporal y por PID")
    return razones


def _leer_archivo_ventana(ruta: Path, inicio: float, fin: float
                         ) -> tuple[list[tuple[float, dict]], str | None, int, int]:
    try:
        lineas = ruta.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeError) as exc:
        return [], f"{ruta}: no se pudo leer: {exc}", 0, 0
    filas = []
    invalidas = 0
    ts_invalidos = 0
    for linea in lineas:
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
        elif inicio <= marca <= fin:
            filas.append((marca, dato))
    return filas, None, invalidas, ts_invalidos


def _leer_ventana(rutas: list[Path], inicio: float, fin: float
                  ) -> tuple[list[dict], list[str]]:
    filas: list[tuple[float, dict]] = []
    razones = []
    invalidas = 0
    ts_invalidos = 0
    for ruta in rutas:
        del_archivo, error, invalidas_archivo, ts_archivo = _leer_archivo_ventana(
            ruta, inicio, fin)
        filas.extend(del_archivo)
        invalidas += invalidas_archivo
        ts_invalidos += ts_archivo
        if error:
            razones.append(error)
    filas.sort(key=lambda par: par[0])
    if invalidas:
        razones.append(f"{invalidas} línea(s) JSONL inválidas")
    if ts_invalidos:
        razones.append(f"{ts_invalidos} objeto(s) sin timestamp ISO válido")
    datos = [dato for _, dato in filas]
    if not datos:
        razones.append("ninguna muestra JSON válida dentro de la ventana")
    return datos, razones


def _validar_campos_muestras(datos: list[dict]) -> list[str]:
    campos_validos = {
        "mem_free_kb": lambda valor: isinstance(valor, (int, float)),
        "zombies": lambda valor: isinstance(valor, int),
        "apps": lambda valor: isinstance(valor, list),
        "psi": lambda valor: isinstance(valor, dict) and any(
            isinstance(valor.get(k), (int, float))
            for k in ("mem_full", "mem_some", "cpu_some", "io_some")),
        "gateway": lambda valor: isinstance(valor, str) and bool(valor),
        "gw_salud": lambda valor: isinstance(valor, str) and len(valor.split(",")) >= 7,
        "py_bg": lambda valor: isinstance(valor, list),
        "top_rss": lambda valor: isinstance(valor, list),
    }
    return [f"{campo}: ninguna muestra trae dato utilizable"
            for campo, valida in campos_validos.items()
            if not any(valida(dato.get(campo)) for dato in datos)]


def _validar_contadores(datos: list[dict], campo: str, ancho: int,
                        boot_actual: str | None) -> list[str]:
    if not boot_actual:
        return [f"{campo}: faltan dos muestras utilizables del mismo boot"]
    candidatos = [dato for dato in datos
                  if dato.get("boot_id") == boot_actual and
                  _pares(dato.get(campo), ancho)]
    por_boot: dict[str, list[dict]] = {}
    for dato in candidatos:
        por_boot.setdefault(boot_actual, []).append(dato)
    razones = []
    if not any(len(grupo) >= 2 for grupo in por_boot.values()):
        razones.append(f"{campo}: faltan dos muestras utilizables del mismo boot")
    grupo = por_boot.get(boot_actual, [])
    for anterior, actual in zip(grupo, grupo[1:]):
        a = _pares(anterior.get(campo), ancho)
        b = _pares(actual.get(campo), ancho)
        if _epoch(actual.get("ts")) == _epoch(anterior.get("ts")):
            razones.append(f"{campo}: timestamps duplicados; tasa no calculable")
            break
        if any(k in a and any(x < y for x, y in zip(b[k], a[k])) for k in b):
            razones.append(f"{campo}: contador retrocedió; tasa no calculable")
            break
    return razones


def _validar_muestras(datos: list[dict]) -> list[str]:
    razones = _validar_campos_muestras(datos)
    boots = [dato["boot_id"] for dato in datos
             if isinstance(dato.get("boot_id"), str) and dato["boot_id"]]
    boot_actual = boots[-1] if boots else None
    if boots:
        for dato in datos:
            if dato.get("boot_id") != boot_actual:
                dato.pop("cpu_jiffies", None)
                dato.pop("red", None)
    else:
        for dato in datos:
            dato.pop("cpu_jiffies", None)
            dato.pop("red", None)
    for campo, ancho in (("cpu_jiffies", 3), ("red", 3)):
        razones.extend(_validar_contadores(datos, campo, ancho, boot_actual))
    if not boots:
        razones.append("tasas CPU/red: el histórico no registra boot_id")
    return razones


def _validar_termica(datos: list[dict]) -> list[str]:
    validadores = {
        "evento": lambda valor: isinstance(valor, str) and bool(valor),
        "gpu_temp_c": lambda valor: isinstance(valor, (int, float)),
        "sm_clk_mhz": lambda valor: isinstance(valor, (int, float)),
        "gpu_util_pct": lambda valor: isinstance(valor, (int, float)),
        "throttle": lambda valor: isinstance(valor, str) and bool(valor),
        "gpu_procs": lambda valor: isinstance(valor, list),
        "vllm_num_requests_running": lambda valor: isinstance(valor, (int, float)),
    }
    return [f"termica/{campo}: falta dato utilizable para el análisis"
            for campo, valida in validadores.items()
            if not any(valida(dato.get(campo)) for dato in datos)]


def preparar(rutas: list[Path], inicio: float, fin: float,
             tipo: str = "muestras") -> tuple[list[dict], list[str]]:
    datos, razones = _leer_ventana(rutas, inicio, fin)
    if not datos:
        return datos, razones
    if tipo == "muestras":
        razones.extend(_validar_muestras(datos))
    else:
        razones.extend(_validar_termica(datos))
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
