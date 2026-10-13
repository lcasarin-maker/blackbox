#!/usr/bin/env python3
"""`bb reloj`: detector del reloj de GPU atascado en GB10 (FEATURE-COSECHA-FORO-CATEGORIAS-722-723-01).

El estado, descrito por 8+ hilos del foro de NVIDIA (376039, 376239, 366944, 362737, 375687, 376542, 378150, 382897) y
CONFIRMADO en esta maquina el 2026-10-12: bajo carga plena el reloj SM queda en 500-800 MHz y ~10-16 W, con CERO razones de
throttle, `nvidia-smi -lgc` aceptado e ignorado, y un reinicio no lo limpia. Personal de NVIDIA lo reconoce como una limitacion
real de reloj y recomienda el ciclo de corriente. Ninguna razon de throttle lo anuncia: es una omision de NVIDIA.

Remedio reportado (sin verificar por NVIDIA; funciono a varios usuarios y a otro no le basto ni con 8 h): apagar, desconectar
el adaptador del enchufe, mantener pulsado el boton de encendido ~10 s para drenar condensadores, esperar unos minutos, volver
a conectar y arrancar. Despues volver a correr `bb reloj --prueba`.

Veredicto con tres estados: ATASCADO (mediana < 1000 MHz con carga y sin throttle), SANO (>= 1400 MHz, el umbral de la
herramienta de la comunidad del hilo 362737), INDETERMINADO (sin carga suficiente o entre ambos): nunca se afirma sano sin carga.
Limite declarado: la causa de fondo (entrega de energia / negociacion PD) no se mide aqui.
"""

from __future__ import annotations

import argparse
import json
import statistics
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

from tools import aviso_termico, interruptores
from tools import guardia_termico_predictivo as g

NOMBRE = "reloj_arranque"
UMBRAL_ATASCADO_MHZ = 1000.0
UMBRAL_SANO_MHZ = 1400.0
UTIL_CARGA = 80.0
MUESTRAS_MINIMAS = 12  # ~1 min de carga a 5 s


def _sin_throttle(t: Any) -> bool:
    return t in (None, 0, "0x0", "0x0000000000000000")


def decide(filas: list[dict[str, Any]], minimas: int = MUESTRAS_MINIMAS) -> dict[str, Any]:
    """Pura. Solo cuentan las muestras con carga; sin suficientes no se afirma nada."""
    carga = [f for f in filas if isinstance(f.get("gpu_util_pct"), (int, float)) and f["gpu_util_pct"] >= UTIL_CARGA and isinstance(f.get("sm_clk_mhz"), (int, float))]
    if len(carga) < minimas:
        return {"estado": "INDETERMINADO", "motivo": f"NOT_COLLECTED: {len(carga)} muestras con carga (hacen falta {minimas})"}
    clk = statistics.median(f["sm_clk_mhz"] for f in carga)
    pot = [f["gpu_power_w"] for f in carga if isinstance(f.get("gpu_power_w"), (int, float))]
    throttle = all(_sin_throttle(f.get("throttle")) for f in carga)
    out: dict[str, Any] = {"reloj_mediano_mhz": clk, "potencia_mediana_w": round(statistics.median(pot), 1) if pot else None, "muestras_con_carga": len(carga), "sin_throttle": throttle}
    if clk < UMBRAL_ATASCADO_MHZ and throttle:
        return {**out, "estado": "ATASCADO"}
    if clk >= UMBRAL_SANO_MHZ:
        return {**out, "estado": "SANO"}
    return {**out, "estado": "INDETERMINADO", "motivo": "reloj entre los umbrales o con razones de throttle activas"}


def inicio(ruta: Path = g.TELEMETRIA) -> dict[str, str] | None:
    """Cuando empezo: ultima muestra sana bajo carga y primera atascada posterior (recorre toda la telemetria)."""
    sana = bajo = None
    try:
        with ruta.open(encoding="utf-8", errors="ignore") as fh:
            for linea in fh:
                try:
                    f = json.loads(linea)
                except ValueError:
                    continue
                u, c = f.get("gpu_util_pct"), f.get("sm_clk_mhz")
                if not isinstance(u, (int, float)) or not isinstance(c, (int, float)) or u < 50:
                    continue
                if c >= 1500:
                    sana, bajo = f["ts"], None
                elif c < UMBRAL_ATASCADO_MHZ and bajo is None and sana is not None:
                    bajo = f["ts"]
    except OSError:
        return None
    if sana and bajo:
        return {"ultima_sana": datetime.fromisoformat(sana).astimezone().isoformat(timespec="seconds"), "primera_atascada": datetime.fromisoformat(bajo).astimezone().isoformat(timespec="seconds")}
    return None


def prueba(segundos: int = 15) -> dict[str, Any]:
    """Prueba activa (la del hilo 366944): matmul fp16 8192x8192 durante `segundos`, reloj y potencia cada segundo."""
    import torch  # importado aqui: el detector pasivo no lo necesita

    n = 8192
    a = torch.randn(n, n, device="cuda", dtype=torch.float16)
    b = torch.randn(n, n, device="cuda", dtype=torch.float16)
    torch.cuda.synchronize()
    inicio_t = time.time()
    fin = inicio_t + segundos
    proxima = inicio_t + 1.0
    hechos = 0
    filas: list[dict[str, Any]] = []
    while time.time() < fin:  # un solo bucle: carga y muestreo juntos, sin hilos
        for _ in range(8):
            a @ b
        torch.cuda.synchronize()
        hechos += 8
        if time.time() >= proxima:
            proxima += 1.0
            o = subprocess.run(["nvidia-smi", "--query-gpu=clocks.sm,power.draw,utilization.gpu,clocks_throttle_reasons.active", "--format=csv,noheader,nounits"], capture_output=True, text=True, check=False, timeout=10).stdout.strip().split(", ")
            if len(o) == 4:
                filas.append({"sm_clk_mhz": float(o[0]), "gpu_power_w": float(o[1]), "gpu_util_pct": float(o[2]), "throttle": o[3].strip()})  # `throttle` como en la telemetria
    v = decide(filas[2:], minimas=8)  # descarta los 2 s de arranque; la prueba dura segundos, no minutos
    return {**v, "tflops": round(hechos * 2 * n**3 / segundos / 1e12, 1), "segundos": segundos}


def evento_arranque(r: dict[str, Any], boot_id: str) -> dict[str, Any]:
    """Pura. Lo que se registra tras la prueba de arranque: el veredicto y las cifras que lo sostienen."""
    return {"boot_id": boot_id, "estado": r.get("estado"), "reloj_mediano_mhz": r.get("reloj_mediano_mhz"), "tflops": r.get("tflops"), "motivo": r.get("motivo")}


def arranque(modo_actual: str, r: dict[str, Any], boot_id: str, directorio: Path | None = None, avisa: Any = aviso_termico.enviar) -> dict[str, Any] | None:
    """Tras el arranque: en `observar` registra el veredicto y, si es ATASCADO, avisa en pantalla (el reloj atascado
    sobrevive a los reinicios y solo lo limpia un ciclo de corriente; esta vez costo ~8 h notarlo). `off` no hace nada."""
    if modo_actual == "off":
        return None
    ev = {"modo": modo_actual, **evento_arranque(r, boot_id)}
    if r.get("estado") == "ATASCADO":
        ev["habria_actuado"] = True
        avisa(aviso_termico.Aviso("critical", "GPU con el reloj atascado", f"{r.get('reloj_mediano_mhz')} MHz y {r.get('tflops')} TFLOPS tras el arranque: apagar, desconectar el adaptador de la pared y esperar (hilos 376039/370304). `bb reloj --prueba` para repetir."))
    interruptores.registra(NOMBRE, ev, directorio)
    return ev


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="bb reloj")
    ap.add_argument("--prueba", action="store_true", help="prueba activa de ~15 s con carga en la GPU")
    ap.add_argument("--arranque", action="store_true", help="prueba activa y registra el veredicto segun el interruptor reloj_arranque (lo corre bb-reloj-arranque.timer)")
    a = ap.parse_args(argv)
    r = prueba() if (a.prueba or a.arranque) else decide(g.lee_cola(filas=60))
    if a.arranque:
        boot = Path("/proc/sys/kernel/random/boot_id").read_text(encoding="utf-8").strip()
        arranque(interruptores.modo(NOMBRE), r, boot)
    if r.get("estado") == "ATASCADO":
        r["desde"] = inicio()
        r["remedio"] = "apagar, desconectar el adaptador del enchufe, boton de encendido ~10 s, esperar, reconectar (hilos 376039/376239)"
    print(json.dumps(r, indent=1, ensure_ascii=False))
    return {"SANO": 0, "ATASCADO": 1}.get(str(r.get("estado")), 2)


if __name__ == "__main__":
    sys.exit(main())
