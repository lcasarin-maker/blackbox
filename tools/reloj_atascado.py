#!/usr/bin/env python3
"""`bb reloj`: detector del reloj de GPU atascado en GB10 (FEATURE-COSECHA-FORO-CATEGORIAS-722-723-01).

El estado, descrito por 8+ hilos del foro de NVIDIA (376039, 376239, 366944, 362737, 375687, 376542, 378150, 382897) y
CONFIRMADO en esta maquina el 2026-10-12: bajo carga plena el reloj SM queda en 500-800 MHz y ~10-16 W, con CERO razones de
throttle, `nvidia-smi -lgc` aceptado e ignorado, y un reinicio no lo limpia. Personal de NVIDIA lo reconoce como una limitacion
real de reloj y recomienda el ciclo de corriente. Ninguna razon de throttle lo anuncia: es una omision de NVIDIA.

Remedio reportado (sin verificar por NVIDIA; funciono a varios usuarios y a otro no le basto ni con 8 h): `REMEDIO`, alineado
con el post de `gb10_clockcheck.py` (hilo 387029): minimo 5 min desconectado, tambien los USB, y reconexion en orden pared ->
adaptador -> equipo. Despues volver a correr `bb reloj --prueba`.

Veredicto con tres estados: ATASCADO (mediana < 1000 MHz con carga y sin throttle; o, con TFLOP/s medidos por `--prueba`,
mediana < 1400 MHz sin throttle y TFLOP/s < `UMBRAL_TFLOPS`, la firma del hilo 387029), SANO (>= 1400 MHz, el umbral de la
herramienta de la comunidad del hilo 362737, y TFLOP/s no bajos si se midieron), INDETERMINADO: nunca se afirma sano sin carga.
INDETERMINADO lleva un motivo que dice donde mirar: `NOT_COLLECTED` (sin carga o sin consulta), `GPU_OCUPADA` (otros procesos
de computo en la GPU durante `--prueba`), `THROTTLE_ACTIVO` (con las razones: calor o potencia, no la firma del reloj
atascado), `RELOJ_EN_BANDA` (mediana entre 1000 y 1400 MHz sin TFLOP/s bajos) y `RELOJ_ALTO_RENDIMIENTO_BAJO`.
Limite declarado: la causa de fondo (entrega de energia / negociacion PD) no se mide aqui.
"""

from __future__ import annotations

import argparse
import json
import os
import statistics
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

from tools import aviso_termico, interruptores
from tools import guardia_termico_predictivo as g
from tools import verifica_proveedor_gpu as vpg

NOMBRE = "reloj_arranque"
UMBRAL_ATASCADO_MHZ = 1000.0
UMBRAL_SANO_MHZ = 1400.0
UTIL_CARGA = 80.0
MUESTRAS_MINIMAS = 12  # ~1 min de carga a 5 s
# ponytail: corte PROVISIONAL de TFLOP/s fp16 8192x8192; techo: viene de GX10 (gb10_clockcheck.py, hilo 387029), no de esta
# ATOM, cuya unica lectura propia es posterior al arreglo (77.4 TFLOPS, hilo 386060 post 1), no una linea base; disparador:
# una corrida sana propia con la GPU libre (`bb reloj --prueba`) o una segunda ATOM, antes de fijarlo.
UMBRAL_TFLOPS = 60.0
UMBRAL_TFLOPS_ESTADO = "PROVISIONAL: corte de GX10 (hilo 387029), sin linea base sana medida en esta ATOM"
REMEDIO = ("apagar, desconectar el adaptador del enchufe y tambien los USB, boton de encendido ~10 s, minimo 5 min desconectado, "
           "reconectar en orden pared -> adaptador -> equipo y arrancar; algunas unidades necesitaron mas tiempo o no se "
           "recuperaron (reportes de usuarios sin verificar por NVIDIA, hilos 376039/376239/387029)")
SIN_CONSULTA = "NOT_COLLECTED: nvidia-smi --query-compute-apps no se pudo leer; sin saber si la GPU esta libre no hay veredicto"


def _sin_throttle(t: Any) -> bool:
    return t in (None, 0, "0x0", "0x0000000000000000")


def decide(filas: list[dict[str, Any]], minimas: int = MUESTRAS_MINIMAS, tflops: float | None = None) -> dict[str, Any]:
    """Pura. Solo cuentan las muestras con carga; sin suficientes no se afirma nada. `tflops` (de `prueba`) es el segundo eje."""
    carga = [f for f in filas if isinstance(f.get("gpu_util_pct"), (int, float)) and f["gpu_util_pct"] >= UTIL_CARGA and isinstance(f.get("sm_clk_mhz"), (int, float))]
    if len(carga) < minimas:
        return {"estado": "INDETERMINADO", "motivo": f"NOT_COLLECTED: {len(carga)} muestras con carga (hacen falta {minimas})"}
    clk = statistics.median(f["sm_clk_mhz"] for f in carga)
    pot = [f["gpu_power_w"] for f in carga if isinstance(f.get("gpu_power_w"), (int, float))]
    razones = sorted({str(f.get("throttle")) for f in carga if not _sin_throttle(f.get("throttle"))})
    sin_thr = not razones
    out: dict[str, Any] = {"reloj_mediano_mhz": clk, "potencia_mediana_w": round(statistics.median(pot), 1) if pot else None, "muestras_con_carga": len(carga), "sin_throttle": sin_thr}
    bajo = tflops is not None and tflops < UMBRAL_TFLOPS
    if tflops is not None:
        out.update({"tflops": tflops, "umbral_tflops": UMBRAL_TFLOPS, "umbral_tflops_estado": UMBRAL_TFLOPS_ESTADO})
    if sin_thr and (clk < UMBRAL_ATASCADO_MHZ or (bajo and clk < UMBRAL_SANO_MHZ)):
        return {**out, "estado": "ATASCADO"}
    if clk >= UMBRAL_SANO_MHZ and not bajo:
        return {**out, "estado": "SANO"}
    if not sin_thr:
        motivo = f"THROTTLE_ACTIVO: razones {', '.join(razones)}; revisar calor y potencia, no es la firma del reloj atascado"
    elif clk >= UMBRAL_SANO_MHZ:
        motivo = f"RELOJ_ALTO_RENDIMIENTO_BAJO: mediana {clk} MHz con {tflops} TFLOP/s < {UMBRAL_TFLOPS}; no es la firma del reloj atascado, revisar refrigeracion"
    else:
        motivo = f"RELOJ_EN_BANDA: mediana {clk} MHz entre {UMBRAL_ATASCADO_MHZ} y {UMBRAL_SANO_MHZ} sin TFLOP/s bajos"
    return {**out, "estado": "INDETERMINADO", "motivo": motivo}


def ocupantes(runner: vpg.Runner = vpg._docker_runner, propio: int | None = None, proc: Path = Path("/proc")) -> list[dict[str, Any]] | None:
    """Procesos de computo AJENOS en la GPU, con la consulta y el parser de `verifica_proveedor_gpu` (`_APPS_CMD`,
    `parse_apps`). None si la consulta falla o sale ilegible: eso es NOT_COLLECTED, nunca 'libre'. Excluye el pid propio."""
    rc, salida = runner(vpg._APPS_CMD)
    apps = vpg.parse_apps(salida) if rc == 0 else None
    if apps is None:
        return None
    propio = os.getpid() if propio is None else propio
    ajenos = []
    for pid, mib in sorted(apps.items()):
        if pid == propio:
            continue
        try:
            nombre: str | None = (proc / str(pid) / "comm").read_text(encoding="utf-8").strip() or None
        except OSError:
            nombre = None  # el pid se lista igual: no poder nombrarlo no lo vuelve ausente
        ajenos.append({"pid": pid, "nombre": nombre, "mib": mib})
    return ajenos


def _ocupada(ajenos: list[dict[str, Any]]) -> dict[str, Any]:
    lista = ", ".join(f"pid {o['pid']} ({o['nombre']}, {o['mib']} MiB)" for o in ajenos)
    return {"estado": "INDETERMINADO", "motivo": f"GPU_OCUPADA: {lista}; los TFLOP/s saldrian bajos por competencia, no por el estado de energia", "ocupantes": ajenos}


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
    """Prueba activa (la del hilo 366944): matmul fp16 8192x8192 durante `segundos`, reloj y potencia cada segundo.

    Guarda de GPU ocupada (hilo 387029): consulta los procesos de computo ANTES de cargar (si hay ajenos no carga) y al final
    de la carga con los tensores vivos; ajenos en cualquiera de las dos => INDETERMINADO/GPU_OCUPADA, consulta fallida =>
    NOT_COLLECTED. Limite: un proceso que entre y salga entre las dos consultas no se ve.
    En el temporizador de arranque (6 min tras el boot) con el motor de modelos ya arriba, la prueba sale GPU_OCUPADA sin
    cargar la GPU y `arranque` registra esa fila con los ocupantes, sin avisar y SIN reintentar (el motor no se va solo y un
    reintento competiria con el): el detector de arranque queda ciego en ese boot y la fila lo dice."""
    antes = ocupantes()
    if antes is None:
        return {"estado": "INDETERMINADO", "motivo": SIN_CONSULTA, "segundos": segundos}
    if antes:
        return {**_ocupada(antes), "segundos": segundos}
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
    tflops = round(hechos * 2 * n**3 / segundos / 1e12, 1)
    despues = ocupantes()  # con los tensores vivos: el propio proceso sale en la lista y se excluye por pid
    v = decide(filas[2:], minimas=8, tflops=tflops)  # descarta los 2 s de arranque; la prueba dura segundos, no minutos
    medido = {**v, "tflops": tflops, "segundos": segundos}
    if despues is None:
        return {**medido, "estado": "INDETERMINADO", "motivo": SIN_CONSULTA}
    return {**medido, **_ocupada(despues)} if despues else medido


def evento_arranque(r: dict[str, Any], boot_id: str) -> dict[str, Any]:
    """Pura. Lo que se registra tras la prueba de arranque: el veredicto y las cifras que lo sostienen."""
    return {"boot_id": boot_id, "estado": r.get("estado"), "reloj_mediano_mhz": r.get("reloj_mediano_mhz"), "tflops": r.get("tflops"), "motivo": r.get("motivo"), "ocupantes": r.get("ocupantes")}


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
        r["remedio"] = REMEDIO
    print(json.dumps(r, indent=1, ensure_ascii=False))
    return {"SANO": 0, "ATASCADO": 1}.get(str(r.get("estado")), 2)


if __name__ == "__main__":
    sys.exit(main())
