#!/usr/bin/env python3
"""Guardia termico predictivo (interruptor `termico_predictivo`): FEATURE-COSECHA-FORO-ENERGIA-Y-DGXTOP-01, paso 1.

Idea cosechada del hilo 384499 (solo la idea; su codigo es CC BY-NC): un guardia que no espera a cruzar el tope sino
que predice la zona unos segundos adelante con la tendencia reciente, y que lee de un unico muestreador (aqui
`atom_gpu_telemetry.jsonl`, cada ~5 s) en vez de leer el hardware por su cuenta.

En `observar` registra "habria actuado" con la causa probable (GPU o CPU/SoC) y el load average. En `actuar` NO hay
accion cableada: declara UNSUPPORTED hasta decidir con el registro. La repasada (`--repasa`) aplica la misma
decision al historial para medir cuantas alarmas habria dado y con cuanta antelacion antes de cada corte.
Limite declarado (medido 2026-10-12): el nivel de temperatura solo no separa los cortes de los arranques que
sobrevivieron (un arranque paso 260 min a >=95 C y no murio); este guardia mide, no demuestra que evite un corte.
"""

from __future__ import annotations

import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

from tools import interruptores

NOMBRE = "termico_predictivo"
TOPE_C = 96.0  # tope de aborto de zona del repo de djmad; el trip del kernel es 104.8 (aviso_termico.TRIP_C)
HORIZONTE_S = 30.0  # con muestreo de 5 s, 2 s (el del repo ajeno) no cabe: 6 muestras de tendencia
VENTANA = 8  # muestras (~40 s) para la pendiente
ZONA_ALTA_C = 94.0
SUBIDA_C_MIN = 3.0
FRESCURA_S = 30.0
ACUM_VENTANA = 120  # muestras (~10 min): acumulacion lenta de calor, la firma del ultimo corte (60 -> 94 C en 30 min con la GPU a 6-12 W)
ACUM_ZONA_C = 85.0
ACUM_SUBIDA_C_MIN = 0.8
GPU_OCIOSA_W = 25.0  # por debajo, el calor no es de la GPU (medido: arranque 0b00a7c2 subio 60->94 C con la GPU a 6-12 W)
TELEMETRIA = Path(os.environ.get("BLACKBOX_DATA", Path.home() / ".local/share/blackbox")) / "atom_gpu_telemetry.jsonl"


def zona_max(fila: dict[str, Any]) -> float | None:
    """Temperatura de la zona mas caliente de una fila de telemetria (`zonas` es lista o dict de {temp_c})."""
    z = fila.get("zonas")
    vals = z.values() if isinstance(z, dict) else (z or [])
    temps = [v["temp_c"] for v in vals if isinstance(v, dict) and isinstance(v.get("temp_c"), (int, float))]
    return float(max(temps)) if temps else None


def pendiente_c_min(serie: list[tuple[float, float]]) -> float | None:
    """Minimos cuadrados de (t_s, temp) en grados por minuto. Menos de 4 puntos o sin variacion de tiempo: None."""
    if len(serie) < 4:
        return None
    n = len(serie)
    mt = sum(t for t, _ in serie) / n
    mv = sum(v for _, v in serie) / n
    den = sum((t - mt) ** 2 for t, _ in serie)
    if den == 0:
        return None
    return 60.0 * sum((t - mt) * (v - mv) for t, v in serie) / den


def decide(serie: list[tuple[float, float]], gpu_w: float | None = None) -> dict[str, Any]:
    """Pura. Dispara si la prediccion a HORIZONTE_S llega al tope, o si ya esta en zona alta y sube rapido."""
    if len(serie) < 4:
        return {"dispara": False, "motivo": "NOT_COLLECTED: menos de 4 muestras de zona"}
    zona = serie[-1][1]
    pend = pendiente_c_min(serie)
    if pend is None:
        return {"dispara": False, "motivo": "NOT_COLLECTED: pendiente sin tiempo"}
    pred = zona + pend * HORIZONTE_S / 60.0
    regla = None
    if pred >= TOPE_C:
        regla = "prediccion>=tope"
    elif zona >= ZONA_ALTA_C and pend >= SUBIDA_C_MIN:
        regla = "alta_y_subiendo"
    causa = None
    if gpu_w is not None:
        causa = "gpu" if gpu_w >= GPU_OCIOSA_W else "cpu_o_soc (GPU casi ociosa)"
    return {
        "dispara": regla is not None,
        "regla": regla,
        "zona_c": round(zona, 1),
        "pendiente_c_min": round(pend, 2),
        "prediccion_c": round(pred, 1),
        "causa_probable": causa,
    }


def decide_acumulacion(serie: list[tuple[float, float]]) -> dict[str, Any]:
    """Pura. Dispara si la zona ya esta alta y la pendiente de ~10 min sigue subiendo (acumulacion lenta de calor)."""
    if len(serie) < ACUM_VENTANA:
        return {"dispara": False, "motivo": "NOT_COLLECTED: menos de %d muestras" % ACUM_VENTANA}
    ven = serie[-ACUM_VENTANA:]
    pend = pendiente_c_min(ven)
    if pend is None:
        return {"dispara": False, "motivo": "NOT_COLLECTED: pendiente sin tiempo"}
    dispara = ven[-1][1] >= ACUM_ZONA_C and pend >= ACUM_SUBIDA_C_MIN
    return {"dispara": dispara, "regla": "acumulacion_de_calor" if dispara else None, "zona_c": round(ven[-1][1], 1), "pendiente10_c_min": round(pend, 2)}


def _serie(filas: list[dict[str, Any]]) -> list[tuple[float, float]]:
    out = []
    for f in filas:
        z = zona_max(f)
        try:
            t = datetime.fromisoformat(f["ts"]).timestamp()
        except (KeyError, ValueError, TypeError):
            continue
        if z is not None:
            out.append((t, z))
    return out


def lee_cola(ruta: Path = TELEMETRIA, filas: int = ACUM_VENTANA) -> list[dict[str, Any]]:
    """Ultimas `filas` filas legibles de la telemetria; lee solo la cola del archivo (el archivo crece sin tope)."""
    try:
        with ruta.open("rb") as fh:
            fh.seek(0, os.SEEK_END)
            fh.seek(max(0, fh.tell() - 524288))
            texto = fh.read().decode("utf-8", errors="ignore")
    except OSError:
        return []
    out: list[dict[str, Any]] = []
    for linea in texto.splitlines()[-4 * filas :]:
        try:
            out.append(json.loads(linea))
        except ValueError:
            continue
    return [f for f in out if zona_max(f) is not None][-filas:]


def lee_carga(ruta: Path = Path("/proc/loadavg")) -> float | None:
    try:
        return float(ruta.read_text(encoding="utf-8").split()[0])
    except (OSError, ValueError, IndexError):
        return None


def paso(
    modo_actual: str,
    filas: list[dict[str, Any]],
    carga: float | None = None,
    directorio: Path | None = None,
    ahora: float | None = None,
) -> dict[str, Any] | None:
    if modo_actual == "off":
        return None
    serie = _serie(filas)
    ahora = time.time() if ahora is None else ahora
    if not serie or ahora - serie[-1][0] > FRESCURA_S:
        return None  # sin muestra fresca no se decide (un dato viejo no es "normal")
    gpu_w = filas[-1].get("gpu_power_w") if filas else None
    corta = decide(serie[-VENTANA:], gpu_w if isinstance(gpu_w, (int, float)) else None)
    larga = decide_acumulacion(serie)
    if not (corta["dispara"] or larga["dispara"]):
        return None
    reglas = [d["regla"] for d in (corta, larga) if d["dispara"]]
    ev = {"modo": modo_actual, "habria_actuado": True, "load1": carga, "reglas": reglas, **corta,
          "pendiente10_c_min": larga.get("pendiente10_c_min")}
    if modo_actual == "actuar":
        ev["accion"] = "UNSUPPORTED: sin accion cableada; ver FEATURE-COSECHA-FORO-ENERGIA-Y-DGXTOP-01"
    interruptores.registra(NOMBRE, ev, directorio)
    return ev


def repasa(ruta: Path = TELEMETRIA, min_muestras: int = 300) -> dict[str, Any]:
    """Aplica `decide` al historial por arranque: episodios, minutos disparados y antelacion antes del fin del arranque."""
    por: dict[str, list[dict[str, Any]]] = {}
    with ruta.open(encoding="utf-8", errors="ignore") as fh:
        for linea in fh:
            try:
                f = json.loads(linea)
            except ValueError:
                continue
            if zona_max(f) is not None and f.get("boot_id"):
                por.setdefault(f["boot_id"], []).append(f)
    informe: dict[str, Any] = {}
    for boot, filas in por.items():
        if len(filas) < min_muestras:
            continue
        serie = _serie(filas)
        informe[boot[:8]] = {"muestras": len(serie), "horas": round((serie[-1][0] - serie[0][0]) / 3600, 1),
                             "zona_ultima_c": round(serie[-1][1], 1)}
        for regla, ventana, f in (("corta", VENTANA, decide), ("acumulacion", ACUM_VENTANA, decide_acumulacion)):
            disparos = [serie[i - 1][0] for i in range(ventana, len(serie) + 1) if f(serie[i - ventana : i])["dispara"]]
            episodios, previo = 0, None
            for t in disparos:
                if previo is None or t - previo > 120:
                    episodios += 1
                previo = t
            ultima_hora = [t for t in disparos if serie[-1][0] - t <= 3600]
            informe[boot[:8]][regla] = {
                "episodios": episodios,
                "minutos_disparado": round(len(disparos) * 5 / 60, 1),
                "primer_disparo_de_la_ultima_hora_antes_del_fin_min": round((serie[-1][0] - ultima_hora[0]) / 60, 1) if ultima_hora else None,
                "ultimo_disparo_antes_del_fin_s": round(serie[-1][0] - disparos[-1]) if disparos else None,
            }
    return informe


def main() -> None:
    if "--repasa" in sys.argv:
        print(json.dumps(repasa(), indent=1))
        return
    while True:
        paso(interruptores.modo(NOMBRE), lee_cola(), lee_carga())
        time.sleep(5)  # blocking-sleep: muestreo a 5 s, el mismo ritmo que escribe atom_gpu_telemetry; demonio de usuario sin otro hilo -- DEBT-COLAPSOS-11-OCT-SUITES-PYTEST-SIN-TECHO-01  # sunset-reviewed: 3.2 -- re-revisado 2026-10-13 contra 3.1: `git blame` de la linea 207 (93850773) es anterior al bump 3.1.0 (7a5bd48b), la linea no cambio desde su revision anterior; la razon sigue valiendo: re-revisado 2026-10-12 contra 3.0: la linea 207 es NUEVA en este ciclo (0023430b, despues de ab63e2b); se releyo hoy: el muestreo de 5 s es el mismo ritmo con que atom_gpu_telemetry escribe su archivo y el demonio de usuario no tiene otro hilo ni E/S que esperar; nuevo 2026-10-12 con la misma razon que vigilante_memavail: intervalo del vigilante de vida larga, sin I/O que esperar ; re-revisado 2026-10-13 contra 3.1: la linea no cambio desde 20256295 (git blame de esta linea)


if __name__ == "__main__":
    main()
