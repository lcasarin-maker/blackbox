#!/usr/bin/env python3
"""Muestreo de 1 s con fsync por linea: lo que ningun instrumento de bb mira (CPU, procesos, frecuencia, temperaturas) para ver el ultimo segundo antes de un corte duro.

Lo ejecuta bb-muestreo-corte.service. Salida: muestreo-<boot_id[:8]>.jsonl (un archivo por arranque = la rotacion).
ponytail: stdlib sola y sin argumentos, techo = una linea por segundo sin tope de tamano por arranque; disparador = un muestreo-*.jsonl de un arranque pasa de 100 MB o la unidad se reutiliza fuera de la investigacion de caidas duras."""
import glob
import csv
import json
import math
import os
import subprocess
import time

SALIDA_DIR = "~/.local/share/blackbox/incidentes/caidas-2026-10-30"


class CalidadGPU:
    """Estado monotónico de entrega y contenido; no diagnostica el dispositivo."""
    def __init__(self, reloj=time.monotonic):
        self.reloj = reloj
        self.ultima_entrega = None
        self.inicio_contenido = None
        self.contenido = None
        self.entregas_racha = 0

    def observar(self, contenido, *, estado="reciente", entrega=False):
        ahora = self.reloj()
        reloj_invalido = not math.isfinite(ahora) or (self.ultima_entrega is not None and ahora < self.ultima_entrega)
        if reloj_invalido:
            self.ultima_entrega = self.inicio_contenido = None
            self.contenido = None
            self.entregas_racha = 0
            estado = "reloj_invalido"
        if estado == "reciente" and contenido is not None:
            tenia_contenido = self.contenido is not None
            igual = contenido == self.contenido
            if not igual:
                self.contenido, self.inicio_contenido, self.entregas_racha = contenido, ahora, 1
            else:
                self.entregas_racha += 1
            self.ultima_entrega = ahora
            comparacion = "igual" if igual else ("cambio" if tenia_contenido else "inicio")
            edad_entrega = 0.0
        elif entrega and not reloj_invalido:
            self.ultima_entrega = ahora
            comparacion, edad_entrega = "no_comparable", 0.0
        else:
            comparacion = "no_comparable"
            edad_entrega = None if self.ultima_entrega is None else round(max(0, ahora-self.ultima_entrega), 3)
        edad_contenido = None if self.inicio_contenido is None else round(max(0, ahora-self.inicio_contenido), 3)
        return {"estado": estado, "edad_entrega_s": edad_entrega, "edad_contenido_s": edad_contenido,
                "entregas_racha": self.entregas_racha, "comparacion": comparacion}


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


def registro(ts, t, i, pt, pi, cp, pp, gpu, hz, gpu_calidad=None):
    """Una muestra; las claves y su orden son el formato de linea (gpu_calidad expone gpu_edad y estado para detectar gpu_congelada)."""
    dt = max(t - pt, 1)
    top = sorted(((cp[k][1] - pp[k][1], cp[k][0], k) for k in cp if k in pp), reverse=True)[:3]
    return {"ts": ts, "cpu_pct": round(100 * (1 - (i - pi) / dt), 1), "load1": (rd("/proc/loadavg") or "").split()[0],
            "top": [{"pid": k, "cmd": n, "cpu_pct_de_un_nucleo": round(100 * d / hz, 0)} for d, n, k in top],
            "freq_khz_cpu0": rd("/sys/devices/system/cpu/cpu0/cpufreq/scaling_cur_freq"),
            "temp_mc": [rd(z) for z in sorted(glob.glob("/sys/class/thermal/thermal_zone*/temp"))],
            "gpu": gpu, "psi_cpu": (rd("/proc/pressure/cpu") or "").split("\n")[0], "psi_mem": (rd("/proc/pressure/memory") or "").split("\n")[0],
            "gpu_calidad": gpu_calidad or {"estado": "desconocida", "edad_entrega_s": None, "edad_contenido_s": None, "entregas_racha": 0, "comparacion": "no_comparable"}}


def escribir(f, rec):
    """Linea jsonl + flush + fsync: el fsync por segundo es la razon de ser del instrumento."""
    f.write(json.dumps(rec) + "\n")
    f.flush()
    os.fsync(f.fileno())


def consumir_filas_stream(fragmento):
    """Devuelve filas completas (identidad, valores legacy) y el sufijo parcial."""
    partes = (fragmento or "").splitlines(keepends=True)
    pendiente = ""
    if partes and not partes[-1].endswith(("\n", "\r")):
        pendiente = partes.pop()
    filas, invalida = [], False
    for parte in partes:
        if not parte.strip():
            continue
        columnas = next(csv.reader([parte]))
        if len(columnas) != 6 or not columnas[0].strip().isdigit():
            invalida = True
            continue
        valores = [c.strip() for c in columnas[1:]]
        try:
            metricas_requeridas_validas = all(math.isfinite(float(v)) for v in valores[:4])
        except ValueError:
            metricas_requeridas_validas = False
        comparable = len(valores) == 5 and metricas_requeridas_validas
        filas.append((columnas[0].strip(), ", ".join(valores), comparable))
    return filas, pendiente, invalida


def main(*, max_iteraciones=None):
    boot = (rd("/proc/sys/kernel/random/boot_id") or "")
    f = open(ruta_salida(boot), "a", buffering=1)
    smi = subprocess.Popen(["nvidia-smi", "--query-gpu=index,power.draw,utilization.gpu,clocks.sm,temperature.gpu,memory.used", "--format=csv,noheader,nounits", "-lms", "1000"], stdout=subprocess.PIPE, text=True)
    assert smi.stdout is not None
    os.set_blocking(smi.stdout.fileno(), False)
    gpu = None
    calidad = CalidadGPU()
    parcial = ""
    pt, pi = stat()
    pp = procs()
    hz = os.sysconf("SC_CLK_TCK")
    iteraciones = 0
    while max_iteraciones is None or iteraciones < max_iteraciones:
        time.sleep(1)
        estado_lectura = "ausencia"
        filas = []
        fragmento = parcial
        try:
            ln = smi.stdout.readline()
            while ln:
                fragmento += ln
                ln = smi.stdout.readline()
        except (OSError, ValueError):
            estado_lectura = "error"
        filas, parcial, invalida = consumir_filas_stream(fragmento)
        identidades = {ident for ident, _, _ in filas}
        nueva_entrega = bool(filas) and len(identidades) == 1 and not invalida
        comparable = False
        if nueva_entrega:
            gpu = filas[-1][1]
            comparable = filas[-1][2]
            estado_lectura = "reciente" if comparable else "no_comparable"
        elif len(identidades) > 1:
            estado_lectura = "ambiguo"
        elif invalida:
            estado_lectura = "error"
        elif parcial:
            estado_lectura = "parcial"
        if smi.poll() is not None and not nueva_entrega:
            estado_lectura = "eof"
        if nueva_entrega:
            # Cada fila completa del lote cuenta: A→B→A debe reiniciar la edad
            # de contenido aunque el campo legacy conserve la última fila A.
            cambio_en_lote = False
            for ident, valores, fila_comparable in filas:
                calidad_actual = calidad.observar(
                    (ident, valores) if fila_comparable else None,
                    estado="reciente" if fila_comparable else "no_comparable",
                    entrega=True)
                cambio_en_lote |= calidad_actual["comparacion"] in {"inicio", "cambio"}
            if cambio_en_lote and len(filas) > 1 and comparable:
                calidad_actual["comparacion"] = "cambio"
        else:
            calidad_actual = calidad.observar(None, estado=estado_lectura)
        t, i = stat()
        cp = procs()
        escribir(f, registro(time.time(), t, i, pt, pi, cp, pp, gpu, hz, calidad_actual))
        pt, pi, pp = t, i, cp
        iteraciones += 1


if __name__ == "__main__":
    main()
