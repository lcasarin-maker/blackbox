#!/usr/bin/env python3
"""FEATURE-RESIDENTES-INACTIVOS-CONTRA-CALOR-01: cruza residencia x inactividad x temperatura. SOLO LECTURA.

Entradas (nunca se escriben):
  $BLACKBOX_DATA/gpumem_historial.jsonl  -> quien tiene memoria de GPU (residencia). Una fila por cambio o latido de 10 min.
  $BLACKBOX_DATA/atom_gpu_telemetry.jsonl -> una muestra cada 5 s: temperatura, potencia, reloj, peticiones del motor vLLM.

Senal de INACTIVIDAD elegida: peticiones del motor vLLM (vllm_num_requests_running == 0 y vllm_num_requests_waiting == 0),
sostenida >= 10 min seguidos. Por que: (1) es de ese residente y no de otros procesos (gpu_util_pct de nvidia-smi es global
y en GB10 con memoria unificada no hay utilizacion por proceso en esta telemetria); (2) ya se mide cada 5 s; (3) es la
definicion natural de "reposo" para un servicio que Athena descargaria. gpu_util_pct se usa como corroboracion cruzada.

Residencia: la ultima fila de gpumem_historial del mismo boot_id con ts <= la muestra y a no mas de 13 min (latido 10 min +
margen); fuera de eso la residencia es DESCONOCIDA y la muestra no entra en ningun contraste de residencia.
Salida: texto en stdout. Sin dependencias fuera de la libreria estandar.
"""
from __future__ import annotations

import bisect
import json
import os
import random
import statistics
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

DATA = Path(os.environ.get("BLACKBOX_DATA", Path.home() / ".local/share/blackbox"))
TOL_HISTORIAL_S = 13 * 60  # latido de 10 min + margen
REPOSO_S = 10 * 60  # inactividad sostenida
REPOSO_LARGO_S = 60 * 60
GAP_MAX_S = 30  # mas que esto entre muestras contiguas rompe la racha (el sampler corta cada 5 s)
OTRO_CLIENTE_GIB = 2.0  # memoria de GPU de hojas NO contenedor, por encima de esto hay otro cliente de GPU


def ts(s: str) -> float:
    return datetime.fromisoformat(s).timestamp()


def carga_historial() -> dict[str, tuple[list[float], list[dict]]]:
    por_boot: dict[str, list[dict]] = defaultdict(list)
    malas = 0
    for linea in (DATA / "gpumem_historial.jsonl").read_text(encoding="utf-8").splitlines():
        try:
            r = json.loads(linea)
        except ValueError:
            malas += 1
            continue
        hojas = r.get("hojas", [])
        por_boot[r["boot_id"]].append({
            "t": ts(r["ts"]),
            "residentes": frozenset(h["quien"] for h in hojas if h["quien"].startswith("contenedor")),
            "otros_gib": sum(h["gib"] for h in hojas if not h["quien"].startswith("contenedor")),
        })
    out = {}
    for b, filas in por_boot.items():
        filas.sort(key=lambda f: f["t"])
        out[b] = ([f["t"] for f in filas], filas)
    print(f"historial: {sum(len(v[1]) for v in out.values())} filas, {len(out)} boots, {malas} ilegibles")
    return out


def residencia(hist, boot: str, t: float):
    if boot not in hist:
        return None
    tiempos, filas = hist[boot]
    i = bisect.bisect_right(tiempos, t) - 1
    if i < 0 or t - tiempos[i] > TOL_HISTORIAL_S:
        return None
    return filas[i]


def muestras():
    """Muestras de telemetria (evento == 'muestra') con los campos que usa el cruce."""
    for linea in open(DATA / "atom_gpu_telemetry.jsonl", encoding="utf-8"):
        try:
            r = json.loads(linea)
        except ValueError:
            yield None
            continue
        if r.get("evento") != "muestra":
            continue
        zonas = [z["temp_c"] for z in r.get("zonas", []) if isinstance(z.get("temp_c"), (int, float))]
        yield {
            "t": ts(r["ts"]), "boot": r["boot_id"],
            "run": r.get("vllm_num_requests_running"), "wait": r.get("vllm_num_requests_waiting"),
            "util": r.get("gpu_util_pct"), "pot": r.get("gpu_power_w"), "tgpu": r.get("gpu_temp_c"),
            "clk": r.get("sm_clk_mhz"), "pstate": r.get("pstate"),
            "tmax": max(zonas) if zonas else None, "tmed": statistics.fmean(zonas) if zonas else None,
        }


def q(xs, p):
    xs = sorted(xs)
    return xs[min(len(xs) - 1, int(p * len(xs)))]


def resumen(nombre, filas, campos=("tmax", "tmed", "tgpu", "pot")):
    if not filas:
        print(f"  {nombre:<44} n=0")
        return
    partes = []
    for c in campos:
        v = [f[c] for f in filas if f[c] is not None]
        partes.append(f"{c} p50={q(v, .5):.1f} [p10={q(v, .1):.1f} p90={q(v, .9):.1f}]" if v else f"{c} sin dato")
    print(f"  {nombre:<44} n={len(filas):>6} ({len(filas) * 5 / 3600:6.1f} h)  " + "  ".join(partes))


def delta(a, b, campo):
    """mediana(a)-mediana(b) sobre todas las muestras; None si algun lado trae menos de 30 (no se concluye con eso).
    Sin valor p: las muestras vecinas estan autocorrelacionadas y una permutacion por muestra dio p=0.0025 en el placebo
    (medido en la primera corrida de este script), es decir, un p optimista. En su lugar se compara contra el piso de
    ruido a nivel de VENTANA (ver piso_ruido)."""
    va = [f[campo] for f in a if f[campo] is not None]
    vb = [f[campo] for f in b if f[campo] is not None]
    if len(va) < 30 or len(vb) < 30:
        return None
    return statistics.median(va) - statistics.median(vb), len(va), len(vb)


def piso_ruido(ventanas, campo, veces=300, semilla=11):
    """Placebo: parte las ventanas de reposo (enteras) al azar en dos mitades `veces` veces y devuelve p50 y p95 de
    |mediana(A)-mediana(B)|. Es lo que se mueve la mediana sin que ninguna condicion cambie."""
    rng = random.Random(semilla)
    claves = list(ventanas)
    ds = []
    for _ in range(veces):
        a, b = [], []
        for k in claves:
            (a if rng.random() < .5 else b).extend(ventanas[k])
        d = delta(a, b, campo)
        if d is not None:
            ds.append(abs(d[0]))
    return (q(ds, .5), q(ds, .95), len(ds)) if ds else None


def main() -> int:
    hist = carga_historial()
    cont = Counter()
    todas = []
    racha: dict[str, tuple[float, float] | None] = {}  # boot -> (inicio de racha de inactividad, ultima muestra)
    for m in muestras():
        if m is None:
            cont["telemetria_ilegible"] += 1
            continue
        cont["muestras"] += 1
        h = residencia(hist, m["boot"], m["t"])
        if h is None:
            m["res"] = None
        else:
            m["res"] = len(h["residentes"])
            m["otros"] = h["otros_gib"]
            m["quien"] = tuple(sorted(h["residentes"]))
        # racha de inactividad del motor
        if m["run"] is None or m["wait"] is None:
            racha[m["boot"]] = None
            m["inact_s"] = None
        else:
            quieto = m["run"] == 0 and m["wait"] == 0
            r = racha.get(m["boot"])
            if not quieto:
                racha[m["boot"]] = None
                m["inact_s"] = 0.0
            else:
                if r is None or m["t"] - r[1] > GAP_MAX_S:
                    r = (m["t"], m["t"])
                racha[m["boot"]] = (r[0], m["t"])
                m["inact_s"] = m["t"] - r[0]
        todas.append(m)

    print(f"telemetria: {cont['muestras']} muestras ({todas[0]['t'] and datetime.fromtimestamp(todas[0]['t']).isoformat()[:19]} "
          f"a {datetime.fromtimestamp(todas[-1]['t']).isoformat()[:19]} hora local), {len({m['boot'] for m in todas})} boots, "
          f"{cont['telemetria_ilegible']} lineas ilegibles")

    # ---- 1. cobertura: cuanta residencia e inactividad hay para cruzar
    print("\n[1] COBERTURA")
    desconocida = [m for m in todas if m["res"] is None]
    print(f"  residencia DESCONOCIDA (sin fila de historial a <=13 min en su boot): {len(desconocida)} muestras")
    conocidas = [m for m in todas if m["res"] is not None]
    por_quien = Counter(m["quien"] for m in conocidas)
    for k, v in por_quien.most_common():
        print(f"  residentes {list(k) or 'NINGUNO'}: {v} muestras ({v * 5 / 3600:.1f} h)")
    sin_res = [m for m in conocidas if m["res"] == 0]
    print(f"  CONTROL sin residentes: {len(sin_res)} muestras ({len(sin_res) * 5 / 3600:.2f} h) de {len(conocidas)} con residencia conocida")
    sin_vllm = [m for m in conocidas if m["inact_s"] is None]
    print(f"  inactividad DESCONOCIDA (vllm sin dato): {len(sin_vllm)} muestras")

    # ---- 2. estratos de inactividad (con el residente presente)
    pres = [m for m in conocidas if m["res"] >= 1 and m["inact_s"] is not None]
    activo = [m for m in pres if m["inact_s"] == 0]
    transicion = [m for m in pres if 0 < m["inact_s"] < REPOSO_S]
    reposo = [m for m in pres if m["inact_s"] >= REPOSO_S]
    largo = [m for m in pres if m["inact_s"] >= REPOSO_LARGO_S]
    limpio = [m for m in reposo if m["otros"] <= OTRO_CLIENTE_GIB and (m["util"] or 0) < 10]
    print("\n[2] ESTRATOS CON RESIDENTE PRESENTE (inactividad = motor sin peticiones corriendo ni en cola)")
    resumen("ACTIVO (>=1 peticion corriendo)", activo)
    resumen("TRANSICION (inactivo < 10 min)", transicion)
    resumen("REPOSO >= 10 min", reposo)
    resumen("REPOSO >= 60 min", largo)
    resumen("REPOSO >= 10 min LIMPIO (sin otro cliente GPU, util<10)", limpio)
    resumen("SIN RESIDENTES (control)", [m for m in sin_res if m["inact_s"] is not None])
    # ventanas de reposo (rachas maximas) y su tamano
    ventanas = defaultdict(list)
    for m in reposo:
        ventanas[(m["boot"], m["t"] - m["inact_s"])].append(m)
    dur = sorted(len(v) * 5 / 60 for v in ventanas.values())
    print(f"  ventanas de reposo >=10 min: {len(ventanas)}; con residente presente: {len(ventanas)}; "
          f"SIN residente: 0 (por construccion: solo se cuentan con residente presente)")
    if dur:
        print(f"  duracion (min, tras los primeros 10) p50={statistics.median(dur):.0f} max={dur[-1]:.0f}")
    reposo_sin_res = [m for m in sin_res if m["inact_s"] is not None and m["inact_s"] >= REPOSO_S]
    print(f"  muestras de reposo >=10 min SIN residente: {len(reposo_sin_res)}")

    # ---- 3. corroboracion de la senal de inactividad
    print("\n[3] CORROBORACION: gpu_util_pct y estado de reloj durante el reposo del motor")
    if reposo:
        u = [m["util"] for m in reposo if m["util"] is not None]
        print(f"  util en reposo: p50={q(u, .5):.0f}% p90={q(u, .9):.0f}% max={max(u):.0f}%; muestras con util>=10%: "
              f"{sum(x >= 10 for x in u)} de {len(u)}")
        print(f"  pstate en reposo: {dict(Counter(m['pstate'] for m in reposo))}")
        c = [m["clk"] for m in reposo if m["clk"] is not None]
        print(f"  reloj SM en reposo (MHz): p10={q(c, .1):.0f} p50={q(c, .5):.0f} p90={q(c, .9):.0f}")
    if activo:
        u = [m["util"] for m in activo if m["util"] is not None]
        print(f"  util en ACTIVO: p50={q(u, .5):.0f}% p90={q(u, .9):.0f}%")

    # ---- 4. controles del instrumento
    print("\n[4] CONTROLES DEL INSTRUMENTO")
    print("  control positivo: ACTIVO vs REPOSO (debe dar efecto grande si el instrumento ve diferencias reales)")
    positivo = {}
    for c in ("tmax", "tgpu", "pot"):
        d = delta(activo, reposo, c)
        positivo[c] = d
        print(f"    {c}: " + ("sin datos suficientes" if d is None else f"mediana(activo)-mediana(reposo) = {d[0]:+.2f}, n={d[1]}/{d[2]}"))
    print("  control placebo: las ventanas de reposo >=10 min se parten ENTERAS al azar en dos mitades, 300 veces; |delta| debe ser chico")
    for c in ("tmax", "tgpu", "pot"):
        r = piso_ruido(ventanas, c)
        print(f"    {c}: " + ("sin datos suficientes" if r is None else f"|delta| placebo p50={r[0]:.2f} p95={r[1]:.2f} ({r[2]} particiones)"))
        if r and positivo[c]:
            print(f"        el control positivo ({abs(positivo[c][0]):.2f}) es {abs(positivo[c][0]) / max(r[1], 1e-9):.1f} veces el p95 del placebo")

    # ---- 5. el cruce que importa: costo del residente inactivo
    print("\n[5] COSTO DEL RESIDENTE INACTIVO: REPOSO con residente vs REPOSO sin residente")
    d = delta(reposo, reposo_sin_res, "tmax")
    if d is None:
        print(f"  NO CALCULABLE: reposo con residente n={len(reposo)}, reposo sin residente n={len(reposo_sin_res)} (se piden >=30 de cada lado).")
        print("  No hay control: el residente estuvo presente en todo el periodo de telemetria. No se puede concluir ni efecto ni ausencia de efecto.")
    else:
        r = piso_ruido(ventanas, "tmax")
        print(f"  tmax: {d[0]:+.2f} C, n={d[1]}/{d[2]}; piso de ruido p95={r[1] if r else float('nan'):.2f} C")

    # ---- 6. lo que SI se puede medir: piso de reposo y su variabilidad (cota del efecto detectable)
    print("\n[6] PISO DE REPOSO DEL RESIDENTE Y VARIABILIDAD (limite de lo detectable)")
    print("  por duracion del reposo (la caida tras la carga se enfria; un residente que cueste calor mostraria meseta, no caida a ambiente):")
    for lo, hi, n in ((600, 1800, "10-30 min"), (1800, 3600, "30-60 min"), (3600, 10800, "1-3 h"), (10800, 1e9, ">3 h")):
        resumen(f"reposo {n}", [m for m in reposo if lo <= m["inact_s"] < hi])
    print("  por boot (reposo >=10 min):")
    for b in sorted({m["boot"] for m in reposo}):
        resumen(f"boot {b[:8]}", [m for m in reposo if m["boot"] == b])
    print("  por bloque horario UTC (reposo >=10 min; ambiente no se mide, la hora lo aproxima):")
    for h0 in range(0, 24, 6):
        resumen(f"{h0:02d}-{h0 + 6:02d} UTC", [m for m in reposo if h0 <= datetime.fromtimestamp(m["t"], timezone.utc).hour < h0 + 6])
    por_boot = {}
    for b in {m["boot"] for m in reposo}:
        v = [m["tmax"] for m in reposo if m["boot"] == b and m["tmax"] is not None]
        if len(v) >= 100:
            por_boot[b] = statistics.median(v)
    if len(por_boot) >= 2:
        print(f"  dispersion entre boots de la mediana de tmax en reposo: min={min(por_boot.values()):.1f} max={max(por_boot.values()):.1f} "
              f"(rango {max(por_boot.values()) - min(por_boot.values()):.1f} C): cualquier efecto menor que esto queda tapado por el ambiente/boot.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
