#!/usr/bin/env python3
"""Muestreo de 1 s con fsync por linea: lo que ningun instrumento de bb mira (CPU, procesos, frecuencia, temperaturas) para ver el ultimo segundo antes de un corte duro.

Lo ejecuta bb-muestreo-corte.service. Salida: muestreo-<boot_id[:8]>.jsonl (un archivo por arranque = la rotacion).
ponytail: stdlib sola y sin argumentos, techo = una linea por segundo sin tope de tamano por arranque; disparador = un muestreo-*.jsonl de un arranque pasa de 100 MB o la unidad se reutiliza fuera de la investigacion de caidas duras."""
import glob
import json
import os
import subprocess
import time

SALIDA_DIR = "~/.local/share/blackbox/incidentes/caidas-2026-10-30"


def ruta_salida(boot_id, base=SALIDA_DIR):
    return os.path.join(os.path.expanduser(base), f"muestreo-{boot_id[:8]}.jsonl")


def rd(p):
    try:
        with open(p) as fh:
            return fh.read().strip()
    except Exception:
        return None


def stat():
    with open("/proc/stat") as fh:
        c = fh.readline().split()[1:]
    v = list(map(int, c))
    return sum(v), v[3] + v[4]


def procs():
    r = {}
    for p in glob.glob("/proc/[0-9]*/stat"):
        try:
            with open(p) as fh:
                s = fh.read()
            i = s.rindex(")")
            n = s[s.index("(") + 1:i]
            x = s[i + 2:].split()
            r[int(p.split("/")[2])] = (n, int(x[11]) + int(x[12]))
        except Exception:
            pass
    return r


def registro(ts, t, i, pt, pi, cp, pp, gpu, hz):
    """Una muestra; las claves y su orden son el formato de linea."""
    dt = max(t - pt, 1)
    top = sorted(((cp[k][1] - pp[k][1], cp[k][0], k) for k in cp if k in pp), reverse=True)[:3]
    return {"ts": ts, "cpu_pct": round(100 * (1 - (i - pi) / dt), 1), "load1": (rd("/proc/loadavg") or "").split()[0],
            "top": [{"pid": k, "cmd": n, "cpu_pct_de_un_nucleo": round(100 * d / hz, 0)} for d, n, k in top],
            "freq_khz_cpu0": rd("/sys/devices/system/cpu/cpu0/cpufreq/scaling_cur_freq"),
            "temp_mc": [rd(z) for z in sorted(glob.glob("/sys/class/thermal/thermal_zone*/temp"))],
            "gpu": gpu, "psi_cpu": (rd("/proc/pressure/cpu") or "").split("\n")[0], "psi_mem": (rd("/proc/pressure/memory") or "").split("\n")[0]}


def escribir(f, rec):
    """Linea jsonl + flush + fsync: el fsync por segundo es la razon de ser del instrumento."""
    f.write(json.dumps(rec) + "\n")
    f.flush()
    os.fsync(f.fileno())


def main():
    boot = (rd("/proc/sys/kernel/random/boot_id") or "")
    f = open(ruta_salida(boot), "a", buffering=1)
    smi = subprocess.Popen(["nvidia-smi", "--query-gpu=power.draw,utilization.gpu,clocks.sm,temperature.gpu,memory.used", "--format=csv,noheader,nounits", "-lms", "1000"], stdout=subprocess.PIPE, text=True)
    assert smi.stdout is not None
    os.set_blocking(smi.stdout.fileno(), False)
    gpu = None
    pt, pi = stat()
    pp = procs()
    hz = os.sysconf("SC_CLK_TCK")
    while True:
        time.sleep(1)
        try:
            ln = smi.stdout.readline()
            while ln:
                gpu = ln.strip()
                ln = smi.stdout.readline()
        except Exception:
            pass
        t, i = stat()
        cp = procs()
        escribir(f, registro(time.time(), t, i, pt, pi, cp, pp, gpu, hz))
        pt, pi, pp = t, i, cp


if __name__ == "__main__":
    main()
