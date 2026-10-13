#!/usr/bin/env python3
"""Calibracion del detector de calor sostenido (`temp_sostenida`, `tools/atom_gpu_telemetry.py`) contra los
finales de boot de esta maquina (FEATURE-CALIBRAR-CALOR-SOSTENIDO-01, satd_family BLIND_INSTRUMENT).

Existe porque las constantes del detector (banda umbral-5 C, 80 % de 60 lecturas) salieron de UN boot de 22 h.
Esta herramienta es de SOLO LECTURA: lee la telemetria (`atom_gpu_telemetry.jsonl`) y los veredictos por boot que
escribe `tools/reboot_verdict.py` (`reboots.jsonl`, o su salida sin `--escribe` guardada en otro archivo), y por
cada boot:

  - cuanto tiempo estuvo la zona mas caliente en/sobre cada umbral candidato (todo el boot y su ultima hora);
  - re-ejecuta el detector con cada (banda, fraccion) candidata, con la MISMA logica que `_alarmas_sostenidas`
    (ventana de `SOSTENIDA_MUESTRAS` lecturas por zona, histeresis `SOSTENIDA_FIN_FRACCION`, la ventana se vacia
    cuando el servicio se reinicia -- evento `arranque` --, porque el estado vivo no se persiste);
  - lo cruza con la etiqueta del boot.

Etiquetas: `corte` = CORTE_ABRUPTO / CORTE_DE_RED / APAGADO_INTERNO / PANIC_KERNEL; `sano` = CIERRE_ORDENADO_*;
`colapso` = COLAPSO_MEMORIA (no es un corte termico y no cuenta ni como acierto ni como falso positivo);
cualquier otra, o un boot sin veredicto (el vivo), queda `sin_etiqueta` y sale listado como could_not_run.

  acierto        boot `corte` donde un episodio estaba activo en la ultima muestra o empezo en los ultimos
                 `ANTICIPO_MIN` minutos.
  no_detectado   boot `corte` sin eso.
  falso_positivo boot `sano` con al menos un episodio.

Las constantes vigentes NO se tocan aqui: se importan para que el reporte diga cual es la configuracion actual.
"""

from __future__ import annotations

import argparse
import collections
import json
import math
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from tools import atom_gpu_telemetry as agt

ANTICIPO_MIN = 60.0
DT_MAX_S = 30.0  # una muestra no cuenta mas de esto: un hueco de telemetria no es tiempo caliente medido
CARGA_MEDIANA_W = 20.0  # boot "cargado": mediana de gpu_power_w >= esto (ver medicion: hueco 14.2 -> 26.4 W)
UMBRALES_C = (85.0, 88.0, 89.8, 90.0, 92.0, 92.8, 94.0, 94.8, 96.0, 98.0, 100.0)
BANDAS_C = (2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0)
FRACCIONES = (0.6, 0.7, 0.8, 0.9)
CORTES = {"CORTE_ABRUPTO", "CORTE_DE_RED", "APAGADO_INTERNO", "PANIC_KERNEL"}


@dataclass
class Muestra:
    t: float
    zonas: dict[str, float]
    potencia_w: float | None
    reinicio: bool = False  # primera muestra tras un `arranque` del servicio


@dataclass
class Boot:
    boot_id: str
    muestras: list[Muestra] = field(default_factory=list)
    vivos: list[tuple[float, str]] = field(default_factory=list)  # `temp_sostenida` que emitio el servicio vivo


def norm_id(boot_id: str) -> str:
    return boot_id.replace("-", "").lower()


def _epoch(ts: str) -> float:
    return datetime.fromisoformat(ts).timestamp()


def leer_telemetria(ruta: Path, avisos: list[str]) -> dict[str, Boot]:
    """Muestras por boot, en orden de archivo. Una linea ilegible se cuenta en `avisos`, no se calla."""
    boots: dict[str, Boot] = {}
    reiniciar = False
    malas = 0
    with ruta.open(encoding="utf-8") as fh:
        for linea in fh:
            try:
                d = json.loads(linea)
            except json.JSONDecodeError:
                malas += 1
                continue  # contada arriba y reportada abajo en `avisos`
            evento = d.get("evento")
            if evento == "arranque":
                reiniciar = True
            if evento == "temp_sostenida" and d.get("boot_id"):
                vb = boots.setdefault(norm_id(d["boot_id"]), Boot(norm_id(d["boot_id"])))
                vb.vivos.append((_epoch(d["ts"]), str(d["zona"])))
            if evento != "muestra" or not d.get("boot_id"):
                continue
            zonas = {z["zona"]: float(z["temp_c"]) for z in d.get("zonas") or [] if z.get("temp_c") is not None}
            b = boots.setdefault(norm_id(d["boot_id"]), Boot(norm_id(d["boot_id"])))
            pw = d.get("gpu_power_w")
            b.muestras.append(Muestra(_epoch(d["ts"]), zonas, None if pw is None else float(pw), reiniciar))
            reiniciar = False
    if malas:
        avisos.append(f"{malas} lineas de telemetria no son JSON")
    return boots


def leer_veredictos(rutas: list[Path], avisos: list[str]) -> dict[str, str]:
    """boot_id normalizado -> etiqueta. Si dos archivos traen el mismo boot, gana el ultimo pasado."""
    out: dict[str, str] = {}
    for ruta in rutas:
        if not ruta.exists():
            avisos.append(f"veredictos no existe: {ruta}")
            continue
        for n, linea in enumerate(ruta.read_text(encoding="utf-8").splitlines(), 1):
            if not linea.strip():
                continue
            try:
                d = json.loads(linea)
                out[norm_id(d["boot_id"])] = str(d["etiqueta"])
            except (json.JSONDecodeError, KeyError) as e:
                avisos.append(f"{ruta.name}:{n} ilegible ({e!r})")
    return out


def clase(etiqueta: str | None) -> str:
    if etiqueta is None:
        return "sin_etiqueta"
    if etiqueta in CORTES:
        return "corte"
    if etiqueta.startswith("CIERRE_ORDENADO"):
        return "sano"
    if etiqueta == "COLAPSO_MEMORIA":
        return "colapso"
    return "sin_etiqueta"


def _dts(muestras: list[Muestra]) -> list[float]:
    """Duracion atribuida a cada muestra: el hueco hasta la siguiente, con techo DT_MAX_S; la ultima, la mediana."""
    gaps = [min(DT_MAX_S, max(0.0, b.t - a.t)) for a, b in zip(muestras, muestras[1:])]
    cola = sorted(gaps)[len(gaps) // 2] if gaps else 0.0
    return gaps + [cola] if muestras else []


def minutos_sobre(muestras: list[Muestra], umbral_c: float, desde: float | None = None) -> float:
    """Minutos con la zona mas caliente en/sobre `umbral_c` (mismo `>=` que el detector)."""
    total = 0.0
    for m, dt in zip(muestras, _dts(muestras)):
        if (desde is None or m.t >= desde) and m.zonas and max(m.zonas.values()) >= umbral_c:
            total += dt
    return total / 60.0


@dataclass
class Episodio:
    zona: str
    inicio: float
    fin: float | None  # None: activo en la ultima muestra


def detector(muestras: list[Muestra], umbrales: dict[str, float], banda_c: float, fraccion: float,
             fin_fraccion: float = agt.SOSTENIDA_FIN_FRACCION, n: int = agt.SOSTENIDA_MUESTRAS) -> list[Episodio]:
    """Re-ejecucion de `_alarmas_sostenidas` (solo la parte `temp_sostenida`) con banda y fraccion libres."""
    eps: list[Episodio] = []
    ventanas: dict[str, collections.deque[bool]] = {}
    activos: dict[str, Episodio] = {}
    for m in muestras:
        if m.reinicio:  # el servicio vivo pierde ventana y episodio al reiniciarse
            ventanas.clear()
            for e in activos.values():
                e.fin = m.t
            activos.clear()
        for zona, t in m.zonas.items():
            umbral = umbrales.get(zona)
            if umbral is None:
                continue
            v = ventanas.setdefault(zona, collections.deque(maxlen=n))
            v.append(t >= umbral - banda_c)
            f = sum(v) / len(v)
            if len(v) == n and f >= fraccion and zona not in activos:
                activos[zona] = Episodio(zona, m.t, None)
                eps.append(activos[zona])
            elif zona in activos and f < fin_fraccion:
                activos.pop(zona).fin = m.t
    return eps


def evalua_boot(b: Boot, umbrales: dict[str, float], banda_c: float, fraccion: float) -> dict[str, Any]:
    """`dispara_al_final`: algun episodio sigue activo en la ultima muestra o estuvo vivo en los ultimos
    `ANTICIPO_MIN` minutos. `anticipo_min`: desde el inicio del primero de esos episodios hasta la ultima muestra."""
    eps = detector(b.muestras, umbrales, banda_c, fraccion)
    fin = b.muestras[-1].t
    finales = [e for e in eps if e.fin is None or e.fin >= fin - ANTICIPO_MIN * 60]
    anticipo = (fin - min(e.inicio for e in finales)) / 60.0 if finales else None
    return {"episodios": len(eps), "dispara_al_final": bool(finales),
            "anticipo_min": None if anticipo is None else round(anticipo, 1),
            "min_marcados": round(sum(((e.fin or fin) - e.inicio) for e in eps) / 60.0, 1)}


def contraste_vivo(boots: dict[str, Boot], umbrales: dict[str, float], banda_c: float = agt.SOSTENIDA_BANDA_C,
                   fraccion: float = agt.SOSTENIDA_FRACCION, tolerancia_s: float = 30.0) -> tuple[int, int]:
    """(reproducidos, emitidos): cuantos `temp_sostenida` del servicio vivo reproduce `detector` en la misma zona a
    +-`tolerancia_s`. Valida la re-ejecucion contra produccion; con otra banda debe bajar (control negativo)."""
    ok = tot = 0
    for b in boots.values():
        if not b.vivos or not b.muestras:
            continue
        rep = detector(b.muestras, umbrales, banda_c, fraccion)
        tot += len(b.vivos)
        ok += sum(1 for t, z in b.vivos if any(e.zona == z and abs(e.inicio - t) <= tolerancia_s for e in rep))
    return ok, tot


def resumen_boot(b: Boot, etiqueta: str | None) -> dict[str, Any]:
    ms = b.muestras
    pws = sorted(m.potencia_w for m in ms if m.potencia_w is not None)
    fin = ms[-1].t
    temps = [max(m.zonas.values()) for m in ms if m.zonas]
    mediana = pws[len(pws) // 2] if pws else None
    return {
        "boot_id": b.boot_id[:8], "etiqueta": etiqueta, "clase": clase(etiqueta), "muestras": len(ms),
        "horas": round((fin - ms[0].t) / 3600, 2), "zona_max_c": max(temps) if temps else None,
        "potencia_mediana_w": mediana, "potencia_p90_w": pws[int(len(pws) * 0.9)] if pws else None,
        "cargado": mediana is not None and mediana >= CARGA_MEDIANA_W,
        "min_sobre": {f"{u:g}": round(minutos_sobre(ms, u), 1) for u in UMBRALES_C},
        "min_sobre_ultima_hora": {f"{u:g}": round(minutos_sobre(ms, u, fin - 3600), 1) for u in UMBRALES_C},
    }


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float] | None:
    """Intervalo de Wilson al 95 % para k/n; None si n == 0 (no hay nada que estimar)."""
    if n == 0:
        return None
    p = k / n
    den = 1 + z * z / n
    centro = (p + z * z / (2 * n)) / den
    medio = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return (round(max(0.0, centro - medio), 2), round(min(1.0, centro + medio), 2))


def calibra(boots: dict[str, Boot], veredictos: dict[str, str], umbrales: dict[str, float],
            bandas: tuple[float, ...] = BANDAS_C, fracciones: tuple[float, ...] = FRACCIONES) -> dict[str, Any]:
    pares = [(resumen_boot(b, veredictos.get(bid)), b) for bid, b in boots.items() if b.muestras]
    filas = [f for f, _ in pares]
    could_not_run = [f"{f['boot_id']}: sin veredicto de reboot_verdict (vivo o fuera de rango)"
                     for f in filas if f["clase"] == "sin_etiqueta"]
    configs = []
    for banda in bandas:
        for fr in fracciones:
            c: dict[str, Any] = {"banda_c": banda, "fraccion": fr,
                                 "actual": banda == agt.SOSTENIDA_BANDA_C and fr == agt.SOSTENIDA_FRACCION,
                                 "aciertos": [], "no_detectados": [], "falsos_positivos": [], "sanos_limpios": []}
            for f, b in pares:
                ev = evalua_boot(b, umbrales, banda, fr)
                f.setdefault("detector", {})[f"{banda:g}/{fr:g}"] = ev
                if f["clase"] == "corte":
                    c["aciertos" if ev["dispara_al_final"] else "no_detectados"].append(f["boot_id"])
                elif f["clase"] == "sano":
                    c["falsos_positivos" if ev["episodios"] else "sanos_limpios"].append(f["boot_id"])
            n_c, n_s = len(c["aciertos"]) + len(c["no_detectados"]), len(c["falsos_positivos"]) + len(c["sanos_limpios"])
            c["tasa_acierto_ic95"] = wilson(len(c["aciertos"]), n_c)
            c["tasa_fp_ic95"] = wilson(len(c["falsos_positivos"]), n_s)
            configs.append(c)
    vivo_ok, vivo_tot = contraste_vivo(boots, umbrales)
    return {"boots": filas, "configs": configs, "could_not_run": could_not_run,
            "contraste_vivo": {"reproducidos": vivo_ok, "emitidos": vivo_tot}}


def recomienda(configs: list[dict[str, Any]]) -> dict[str, Any] | None:
    """Mayor (aciertos - falsos positivos); empate -> la mas cercana a la vigente (no se mueve sin evidencia)."""
    if not configs:
        return None
    def clave(c: dict[str, Any]) -> tuple[int, float]:
        dist = abs(c["banda_c"] - agt.SOSTENIDA_BANDA_C) + abs(c["fraccion"] - agt.SOSTENIDA_FRACCION) * 10
        return (len(c["aciertos"]) - len(c["falsos_positivos"]), -dist)
    return max(configs, key=clave)


def informe(r: dict[str, Any], umbrales: dict[str, float]) -> str:
    out = [f"umbral por zona (trip - {agt.MARGEN_TRIP_C:g} C): {sorted(set(umbrales.values()))}",
           f"vigente: banda {agt.SOSTENIDA_BANDA_C:g} C, fraccion {agt.SOSTENIDA_FRACCION:g}, "
           f"ventana {agt.SOSTENIDA_MUESTRAS} muestras, fin {agt.SOSTENIDA_FIN_FRACCION:g}; anticipo {ANTICIPO_MIN:g} min",
           "", "boot      clase        etiqueta                  horas  zmax  pw_med  carg  min>=89.8  min>=94.8  ult_h>=89.8"]
    for f in r["boots"]:
        out.append(f"{f['boot_id']}  {f['clase']:<12} {str(f['etiqueta']):<25} {f['horas']:>5}  {f['zona_max_c']}  "
                   f"{f['potencia_mediana_w']!s:>6}  {'si' if f['cargado'] else 'no':<4}  {f['min_sobre']['89.8']:>9}  "
                   f"{f['min_sobre']['94.8']:>9}  {f['min_sobre_ultima_hora']['89.8']:>11}")
    out += ["", "banda frac  aciertos  no_det  fp/sanos  IC95_acierto  IC95_fp     fp(cargados)"]
    cargados = {f["boot_id"] for f in r["boots"] if f["cargado"]}
    for c in r["configs"]:
        n_c = len(c["aciertos"]) + len(c["no_detectados"])
        n_s = len(c["falsos_positivos"]) + len(c["sanos_limpios"])
        fpc = [b for b in c["falsos_positivos"] if b in cargados]
        n_sc = len([b for b in c["falsos_positivos"] + c["sanos_limpios"] if b in cargados])
        out.append(f"{c['banda_c']:>4g}  {c['fraccion']:>4g}  {len(c['aciertos'])}/{n_c:<6} {len(c['no_detectados']):>5}"
                   f"   {len(c['falsos_positivos'])}/{n_s:<6} {c['tasa_acierto_ic95']!s:<13} {c['tasa_fp_ic95']!s:<11}"
                   f" {len(fpc)}/{n_sc}{'   <- vigente' if c['actual'] else ''}")
    cv = r["contraste_vivo"]
    out += ["", f"contraste con produccion: el detector re-ejecutado (config vigente) reproduce {cv['reproducidos']} de "
            f"{cv['emitidos']} eventos temp_sostenida que emitio el servicio vivo (misma zona, +-30 s)"]
    rec = recomienda(r["configs"])
    if rec is not None:
        out += ["", f"recomendacion (max aciertos-fp, empate -> la mas cercana a la vigente): banda {rec['banda_c']:g} C, "
                f"fraccion {rec['fraccion']:g}; aciertos {rec['aciertos']}, no detectados {rec['no_detectados']}, "
                f"falsos positivos {rec['falsos_positivos']}"]
    out += ["", f"could_not_run: {len(r['could_not_run'])}"] + [f"  {x}" for x in r["could_not_run"]]
    return "\n".join(out)


def _floats(s: str) -> tuple[float, ...]:
    return tuple(float(x) for x in s.split(","))


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=(__doc__ or "").split("\n")[0])
    ap.add_argument("--telemetria", type=Path, default=agt.JSONL_PATH)
    ap.add_argument("--veredictos", type=Path, action="append",
                    help="jsonl de reboot_verdict (repetible); por defecto reboots.jsonl")
    ap.add_argument("--umbral", type=float, help="umbral unico para todas las zonas (por defecto: el de sysfs)")
    ap.add_argument("--bandas", type=_floats, default=BANDAS_C)
    ap.add_argument("--fracciones", type=_floats, default=FRACCIONES)
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    avisos: list[str] = []
    if not a.telemetria.exists():
        print(f"COULD_NOT_RUN: no existe la telemetria {a.telemetria}", file=sys.stderr)
        return 2
    boots = leer_telemetria(a.telemetria, avisos)
    zonas = sorted({z for b in boots.values() for m in b.muestras for z in m.zonas})
    if a.umbral is not None:
        umbrales = {z: a.umbral for z in zonas}
    else:
        umbrales = {z: u["umbral_c"] for z, u in agt.leer_umbrales().items() if u.get("umbral_c") is not None}
    if not umbrales:
        print("COULD_NOT_RUN: sin umbral por zona (sysfs ilegible); pasa --umbral", file=sys.stderr)
        return 2
    veredictos = leer_veredictos(a.veredictos or [agt.DATA_DIR / "reboots.jsonl"], avisos)
    r = calibra(boots, veredictos, umbrales, a.bandas, a.fracciones)
    r["could_not_run"] += avisos
    print(json.dumps(r, ensure_ascii=False) if a.json else informe(r, umbrales))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
