"""Causas de las caidas del motor de inferencia local, desde el journal.

Lee tres textos ya capturados (journal de la unidad del motor, journal del
kernel, bitacora del vigilante) y un directorio de volcados CUDA. No consulta
la maquina: `bb scan` le pasa lo que ya leyo, asi que es determinista y se
prueba con texto sintetico.

Une tres senales que hasta aqui vivian separadas: la caida fatal del EngineCore
con su clase de error CUDA, los Xid del kernel en la misma ventana, y los
cuelgues (el servidor responde /v1/models pero no el chat) que reinicio el
vigilante. No atribuye causa: nombra lo que paso y cuando.
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
from collections import Counter
from datetime import datetime
from pathlib import Path

FATAL = "EngineCore encountered a fatal error"
CUDA_ERR = re.compile(r"CUDA error: (?:an )?(.+?)(?: was encountered)?\s*$")
XID = re.compile(r"NVRM: Xid \([^)]*\): (\d+)")
TS = re.compile(r"^(\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d[+-]\d\d:\d\d)")
VENTANA_XID_S = 30
VENTANA_CLASE_S = 5


def _ts(linea: str) -> datetime | None:
    m = TS.match(linea)
    return datetime.fromisoformat(m.group(1)) if m else None


def caidas(unidad: list[str]) -> list[dict]:
    """Una entrada por caida fatal: hora y clase del error CUDA mas cercano."""
    errores = [(t, m.group(1)) for ln in unidad
               if "CUDA error:" in ln and (t := _ts(ln)) and (m := CUDA_ERR.search(ln))]
    vistas, salida = set(), []
    for ln in unidad:
        t = _ts(ln)
        if t is None or FATAL not in ln or t in vistas:
            continue
        vistas.add(t)
        clase = next((c for te, c in errores if 0 <= (te - t).total_seconds() <= VENTANA_CLASE_S), "sin clase CUDA")
        salida.append({"ts": t, "clase": clase})
    return salida


def xid_cerca(kernel: list[str], t: datetime) -> Counter:
    c: Counter = Counter()
    for ln in kernel:
        te, m = _ts(ln), XID.search(ln)
        if te and m and -VENTANA_XID_S <= (te - t).total_seconds() <= VENTANA_XID_S:
            c[m.group(1)] += 1
    return c


def cuelgues(bitacora: list[str]) -> list[str]:
    return [ln.strip() for ln in bitacora if "REINICIA" in ln]


def atascos(muestras: list[str], minimo: int = 3) -> list[tuple[datetime, datetime, int]]:
    """Episodios en que el motor tiene peticiones corriendo y ni los tokens
    generados ni los de prompt avanzan, entre muestras seguidas del mismo boot.

    Es la firma de los cuelgues del 2026-10-09/10: el log del motor dice
    "Running: 22-31 reqs" con 0.0 tokens/s de entrada y de salida mientras
    /v1/models sigue en 200. Un motor ocioso (run=0) o que avanza no cuenta.
    """
    eps, prev, ini, n, ult = [], None, None, 0, None
    for ln in muestras:
        try:
            d = json.loads(ln)
            p = d["gw_salud"].split(",")
            fila = (datetime.strptime(d["ts"][:19], "%Y-%m-%dT%H:%M:%S"), float(p[0]),
                    float(p[4]), float(p[5]), d.get("boot_id", ""))
        except (ValueError, KeyError, IndexError, AttributeError):
            continue
        if prev and fila[4] == prev[4] and fila[1] > 0 and fila[2] == prev[2] and fila[3] == prev[3]:
            if ini is None:
                ini, n = prev[0], 1
            n, ult = n + 1, fila[0]
        else:
            if ini and n >= minimo:
                eps.append((ini, ult, n))
            ini, n = None, 0
        prev = fila
    if ini and n >= minimo:
        eps.append((ini, ult, n))
    return eps


def volcados(directorio: Path) -> list[Path]:
    """Solo los reales (vllm_*): los prueba_* son el control positivo del armado."""
    return sorted(directorio.glob("vllm_*")) if directorio.is_dir() else []


def kernel_del_volcado(archivo: Path, cuda_gdb: str | None) -> str:
    if not cuda_gdb:
        return "cuda-gdb no disponible"
    try:
        r = subprocess.run([cuda_gdb, "-batch", "-ex", f"target cudacore {archivo}", "-ex", "info cuda kernels"],
                           capture_output=True, text=True, timeout=90)
    except (OSError, subprocess.TimeoutExpired) as e:
        return f"COULD_NOT_RUN: {type(e).__name__}"
    cuerpo = [ln for ln in r.stdout.splitlines() if ln.strip()]
    return " | ".join(cuerpo[-3:]) if cuerpo else f"COULD_NOT_RUN: cuda-gdb rc={r.returncode} sin salida"


def informe(unidad, kernel, bitacora, dir_volcados: Path, cuda_gdb=None, muestras=()) -> str:
    out = []
    cs = caidas(unidad)
    out.append(f"  caidas fatales del EngineCore:   {len(cs)}")
    for k, n in Counter(c["clase"] for c in cs).most_common():
        out.append(f"    {n:3d} x {k}")
    sin_xid = 0
    for c in cs:
        x = xid_cerca(kernel, c["ts"])
        sin_xid += not x
        det = ", ".join(f"Xid{k}x{n}" for k, n in sorted(x.items())) or "SIN Xid en +-30 s"
        out.append(f"    {c['ts'].strftime('%m-%d %H:%M:%S')}  {c['clase']:<28} {det}")
    if cs:
        out.append(f"  caidas sin Xid cercano:          {sin_xid}")
    ch = cuelgues(bitacora)
    out.append(f"  cuelgues (chat mudo, reiniciado): {len(ch)}")
    out += [f"    {ln}" for ln in ch[-5:]]
    at = atascos(list(muestras))
    out.append(f"  atascos (peticiones corriendo, 0 tokens): {len(at)}")
    out += [f"    {a.strftime('%m-%d %H:%M')} -> {b.strftime('%H:%M')}  {n} muestras" for a, b, n in at[-5:]]
    vs = volcados(dir_volcados)
    out.append(f"  volcados CUDA reales (vllm_*):   {len(vs)}  en {dir_volcados}")
    if cs and not vs:
        out.append("    AVISO: hubo caidas y no hay un solo volcado; el armado no ha disparado "
                   "o las caidas son anteriores a el")
    for v in vs[-3:]:
        out.append(f"    {v.name}: {kernel_del_volcado(v, cuda_gdb)}")
    return "\n".join(out)


def _leer(p: str) -> list[str]:
    try:
        return Path(p).read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return []


def main(argv=None) -> int:
    a = argparse.ArgumentParser()
    a.add_argument("--unidad", required=True)
    a.add_argument("--kernel", required=True)
    a.add_argument("--bitacora", required=True)
    a.add_argument("--volcados", required=True)
    a.add_argument("--muestras", default="")
    a = a.parse_args(argv)
    cuda_gdb = shutil.which("cuda-gdb") or ("/usr/local/cuda/bin/cuda-gdb" if Path("/usr/local/cuda/bin/cuda-gdb").exists() else None)
    print(informe(_leer(a.unidad), _leer(a.kernel), _leer(a.bitacora), Path(a.volcados), cuda_gdb,
                  _leer(a.muestras) if a.muestras else ()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
