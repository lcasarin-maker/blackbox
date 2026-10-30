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
INDETERMINADO lleva un motivo que dice donde mirar: `NOT_COLLECTED` (sin carga o sin consulta), `CARGA_NO_PUDO_CORRER` (la
carga de `--prueba` fallo, p. ej. sin memoria porque el motor ocupa la GPU), `THROTTLE_ACTIVO` (con las razones: calor o potencia,
no la firma del reloj atascado), `RELOJ_EN_BANDA` (mediana entre 1000 y 1400 MHz sin TFLOP/s bajos) y
`RELOJ_ALTO_RENDIMIENTO_BAJO`. Con otros procesos de computo en la GPU, `--prueba` juzga solo por reloj y potencia y marca los
TFLOP/s `tflops_valido: false` (DEBT-RELOJ-ARRANQUE-GPU-OCUPADA-POR-EL-MOTOR-01).
Todo ATASCADO adjunta `firmware`: pd0/pd1/ec/bios de la ultima fila de `arranque.jsonl`, o `NOT_COLLECTED: <motivo>`.
Todo ATASCADO arma tambien la carpeta de incidente que NVIDIA pide ANTES de quitar la corriente (zneill, hilo 386060/6;
FEATURE-RELOJ-CAPTURA-DE-INCIDENTE-ANTES-DE-QUITAR-AC-01), una por arranque: `captura_incidente`.
Limite declarado: la causa de fondo (entrega de energia / negociacion PD) no se mide aqui.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import statistics
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable

from tools import aviso_termico, interruptores
from tools import bb_root_run as rr
from tools import guardia_termico_predictivo as g
from tools import origen_proceso as op
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
# La fila por arranque de `bb-root-run arranque-forense` (root, 0644); BB_ARRANQUE_JSONL la sustituye, como en bin/bb.
ARRANQUE_JSONL = "/var/lib/blackbox/pstore/arranque.jsonl"
CAMPOS_FIRMWARE = ("pd0", "pd1", "ec", "bios")


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


def _lista(ajenos: list[dict[str, Any]]) -> str:
    return ", ".join(f"pid {o['pid']} ({o['nombre']}, {o['mib']} MiB)" for o in ajenos)


def _union(*listas: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Ocupantes de las dos consultas, uno por pid (gana la primera vez que se vio)."""
    vistos: dict[int, dict[str, Any]] = {}
    for lista in listas:
        for o in lista:
            vistos.setdefault(o["pid"], o)
    return [vistos[k] for k in sorted(vistos)]


def firmware(ruta: Path | None = None) -> dict[str, Any] | str:
    """Versiones pd0/pd1/ec/bios de la ULTIMA fila de `arranque.jsonl` (la escribe `bb-root-run arranque-forense`), o
    `NOT_COLLECTED: <motivo>`: sin archivo, sin permiso, ilegible o fila vieja (anterior a
    FEATURE-RELOJ-CAPTURA-PD-FIRMWARE-Y-TRANSICION-01) que solo nombra la fuente. Nunca un campo vacio."""
    ruta = Path(os.environ.get("BB_ARRANQUE_JSONL", ARRANQUE_JSONL)) if ruta is None else ruta
    try:
        filas = [x for x in ruta.read_text(encoding="utf-8", errors="replace").splitlines() if x.strip()]
    except FileNotFoundError:
        return f"NOT_COLLECTED: {ruta} no existe (bb-root-run arranque-forense no ha escrito ninguna fila)"
    except OSError as e:
        return f"NOT_COLLECTED: {ruta} ilegible ({e.strerror})"
    if not filas:
        return f"NOT_COLLECTED: {ruta} sin filas"
    try:
        fila = json.loads(filas[-1])
    except ValueError:
        fila = None
    if not isinstance(fila, dict):
        return f"NOT_COLLECTED: la ultima fila de {ruta} no es un objeto JSON"
    if not any(k in fila for k in CAMPOS_FIRMWARE):
        return (f"NOT_COLLECTED: la ultima fila de {ruta} ({fila.get('ts')}) no trae valores, solo la fuente "
                f"firmware={fila.get('firmware')!r}; falta reinstalar arranque-forense (ver la ficha FEATURE-RELOJ-CAPTURA-PD-FIRMWARE-Y-TRANSICION-01)")
    vals = {k: fila[k] if isinstance(fila.get(k), str) and fila[k].strip() else "NOT_COLLECTED: campo ausente o vacio en la fila"
            for k in CAMPOS_FIRMWARE}
    return {**vals, "ts": fila.get("ts"), "boot_id": fila.get("boot_id"), "fuente": str(ruta)}


def _local(ts: str | None) -> str | None:
    return datetime.fromisoformat(ts).astimezone().isoformat(timespec="seconds") if ts else None


def _persiste(episodios: list[dict[str, str | None]], ruta: Path) -> None:
    """Anade a `ruta` los episodios que aun no estan (idempotente: la misma tupla de ts no se escribe dos veces). El
    abierto se guarda tambien: es el que se pierde si la telemetria rota antes de recuperarse; al cerrarse entra su fila
    cerrada (otra tupla). Fallar al escribir no anula el veredicto."""
    try:
        vistos = {(e.get("ultima_sana"), e.get("primera_atascada"), e.get("primera_recuperada"))
                  for e in (json.loads(x) for x in ruta.read_text(encoding="utf-8").splitlines() if x.strip())}
    except FileNotFoundError:
        vistos = set()
    except (OSError, ValueError, AttributeError) as e:
        print(f"bb reloj: {ruta} ilegible ({e}); no se anade nada para no duplicar", file=sys.stderr)
        return
    try:
        for ep in episodios:
            if (ep["ultima_sana"], ep["primera_atascada"], ep["primera_recuperada"]) not in vistos:
                op.anexar_jsonl(ruta, ep)
    except OSError as e:
        print(f"bb reloj: no se pudo escribir {ruta} ({e.strerror})", file=sys.stderr)


def inicio(ruta: Path = g.TELEMETRIA, episodios: Path | None = None) -> dict[str, Any] | None:
    """Cuando empezo: ultima muestra sana bajo carga y primera atascada posterior (recorre toda la telemetria en streaming).
    Con una recuperacion posterior (muestra sana con carga) el episodio se cierra: va en `ultimo_episodio_cerrado` con su
    `primera_recuperada`, en vez de perderse. Cada episodio (abierto o cerrado, ts tal como estan en la telemetria) se copia
    a `episodios` (por defecto `episodios_reloj.jsonl` junto a la telemetria) para que sobreviva a la rotacion."""
    sana = bajo = None
    cerrados: list[dict[str, str | None]] = []
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
                    if bajo is not None:
                        cerrados.append({"ultima_sana": sana, "primera_atascada": bajo, "primera_recuperada": f["ts"]})
                    sana, bajo = f["ts"], None
                elif c < UMBRAL_ATASCADO_MHZ and bajo is None and sana is not None:
                    bajo = f["ts"]
    except OSError:
        return None
    abierto = [{"ultima_sana": sana, "primera_atascada": bajo, "primera_recuperada": None}] if sana and bajo else []
    if not cerrados and not abierto:
        return None
    _persiste(cerrados + abierto, episodios or ruta.parent / "episodios_reloj.jsonl")
    out: dict[str, Any] = {k: _local(v) for k, v in abierto[0].items() if v} if abierto else {}
    if cerrados:
        out["ultimo_episodio_cerrado"] = {k: _local(v) for k, v in cerrados[-1].items()}
    return out


def _carga(segundos: int, n: int, calentamiento: int = 0) -> tuple[int, list[dict[str, Any]]]:
    """Matmul fp16 n x n durante `segundos`, con una muestra de reloj/potencia/util/throttle cada segundo. Los `calentamiento`
    matmuls (y su sincronizacion) van ANTES del cronometro y fuera de `hechos` (FEATURE-RELOJ-PRUEBA-CALENTAMIENTO-ANTES-DE-MEDIR-01)."""
    import torch  # importado aqui: el detector pasivo no lo necesita

    a = torch.randn(n, n, device="cuda", dtype=torch.float16)
    b = torch.randn(n, n, device="cuda", dtype=torch.float16)
    for _ in range(calentamiento):
        a @ b
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
    return hechos, filas


def prueba(segundos: int = 15, calentamiento: int = 0) -> dict[str, Any]:
    """`_prueba` con `calentamiento` declarado en la salida: una medicion sin calentar se distingue de una calentada.
    Por defecto 0, la medicion de siempre: el sesgo del arranque en frio es una hipotesis hasta que `ab` lo mida
    (FEATURE-RELOJ-PRUEBA-CALENTAMIENTO-ANTES-DE-MEDIR-01)."""
    return {**_prueba(segundos, calentamiento), "calentamiento": calentamiento}


def _prueba(segundos: int, calentamiento: int) -> dict[str, Any]:
    """Prueba activa (la del hilo 366944): matmul fp16 8192x8192 durante `segundos`, reloj y potencia cada segundo.

    Ocupacion (hilo 387029; DEBT-RELOJ-ARRANQUE-GPU-OCUPADA-POR-EL-MOTOR-01): consulta los procesos de computo ANTES de cargar y
    al final con los tensores vivos; consulta fallida en cualquiera => NOT_COLLECTED. Con ajenos en alguna de las dos la carga
    corre igual y el veredicto sale SOLO de reloj y potencia observados durante ella (`decide` sin segundo eje): la competencia
    baja los TFLOP/s, no el reloj. Los TFLOP/s se miden y se marcan `tflops_valido: false` con el motivo. Con la GPU libre,
    `tflops_valido: true` y el segundo eje se aplica como siempre. Si la carga no puede correr (sin memoria porque el motor
    ocupa la GPU, sin torch, sin CUDA) => INDETERMINADO `CARGA_NO_PUDO_CORRER: <causa>`, nunca un traceback.
    Limite: un proceso que entre y salga entre las dos consultas no se ve; sus TFLOP/s contarian como validos."""
    antes = ocupantes()
    if antes is None:
        return {"estado": "INDETERMINADO", "motivo": SIN_CONSULTA, "segundos": segundos}
    n = 8192
    try:
        hechos, filas = _carga(segundos, n, calentamiento)
    except Exception as e:  # torch.cuda.OutOfMemoryError es RuntimeError; ImportError si falta torch
        causa = f"{type(e).__name__}: {(str(e).splitlines() or [''])[0][:200]}"
        motivo = f"CARGA_NO_PUDO_CORRER: {causa}" + (f"; GPU ocupada por {_lista(antes)}" if antes else "; GPU libre")
        return {"estado": "INDETERMINADO", "motivo": motivo, "ocupantes": antes, "segundos": segundos}
    tflops = round(hechos * 2 * n**3 / segundos / 1e12, 1)
    despues = ocupantes()  # con los tensores vivos: el propio proceso sale en la lista y se excluye por pid
    if despues is None:
        v = decide(filas[2:], minimas=8, tflops=tflops)
        return {**v, "tflops": tflops, "segundos": segundos, "estado": "INDETERMINADO", "motivo": SIN_CONSULTA}
    ajenos = _union(antes, despues)
    if not ajenos:
        v = decide(filas[2:], minimas=8, tflops=tflops)  # descarta los 2 s de arranque; la prueba dura segundos, no minutos
        return {**v, "tflops": tflops, "tflops_valido": True, "segundos": segundos}
    v = decide(filas[2:], minimas=8)  # sin segundo eje: con competencia los TFLOP/s no dicen nada del estado de energia
    return {**v, "tflops": tflops, "tflops_valido": False,
            "tflops_motivo": f"COMPETENCIA: {_lista(ajenos)} en la GPU durante la carga; los TFLOP/s salen bajos por competencia, no por el estado de energia",
            "ocupantes": ajenos, "segundos": segundos}


CALENTAMIENTO_MATMULS = 10  # el script del hilo 387029: 10 matmuls con sincronizacion antes de cronometrar
AB_MINIMO = 3  # con menos corridas por brazo el rango no es una dispersion


def ab(n: int, mide: Callable[..., dict[str, Any]] | None = None) -> dict[str, Any]:
    """El A/B que pide FEATURE-RELOJ-PRUEBA-CALENTAMIENTO-ANTES-DE-MEDIR-01: `n` corridas de `prueba` sin calentamiento y `n`
    con `CALENTAMIENTO_MATMULS`, alternando el orden dentro de cada par (la deriva termica cae en los dos brazos). Solo cuentan
    los TFLOP/s con `tflops_valido: true` (GPU libre): toda corrida que no lo sea va a `no_corrio` y entonces el veredicto es
    COULD_NOT_RUN, nunca una cifra. Con todo valido: SESGO_MEDIDO si la diferencia de medianas supera el mayor rango
    (max - min) de los dos brazos, DENTRO_DE_LA_DISPERSION si no. Carga la GPU ~2n x 15 s."""
    mide = prueba if mide is None else mide
    brazos: dict[str, list[float]] = {"sin": [], "con": []}
    no_corrio: list[dict[str, Any]] = []
    for i in range(n):
        orden = (("sin", 0), ("con", CALENTAMIENTO_MATMULS))
        for brazo, cal in orden if i % 2 == 0 else orden[::-1]:
            v = mide(calentamiento=cal)
            if v.get("tflops_valido") is True and isinstance(v.get("tflops"), (int, float)):
                brazos[brazo].append(float(v["tflops"]))
            else:
                no_corrio.append({"corrida": i + 1, "brazo": brazo, "estado": v.get("estado"), "motivo": v.get("tflops_motivo") or v.get("motivo")})
    out: dict[str, Any] = {"n": n, "calentamiento_matmuls": CALENTAMIENTO_MATMULS, "could_not_run": len(no_corrio), "no_corrio": no_corrio}
    for brazo, xs in brazos.items():
        out[brazo] = {"tflops": xs, "mediana": statistics.median(xs) if xs else None, "rango": round(max(xs) - min(xs), 2) if xs else None}
    if n < AB_MINIMO:
        return {**out, "veredicto": f"COULD_NOT_RUN: n={n} < {AB_MINIMO}; sin dispersion medible"}
    if no_corrio:
        return {**out, "veredicto": f"COULD_NOT_RUN: {len(no_corrio)} de {2 * n} corridas sin TFLOP/s validos (GPU ocupada o carga que no corrio)"}
    dif = round(out["con"]["mediana"] - out["sin"]["mediana"], 2)
    tope = max(out["sin"]["rango"], out["con"]["rango"])
    return {**out, "diferencia_medianas": dif, "rango_mayor": tope,
            "veredicto": "SESGO_MEDIDO" if abs(dif) > tope else "DENTRO_DE_LA_DISPERSION"}


def evento_arranque(r: dict[str, Any], boot_id: str) -> dict[str, Any]:
    """Pura. Lo que se registra tras la prueba de arranque: el veredicto y las cifras que lo sostienen (y el firmware si el
    veredicto lo trae, que solo pasa con ATASCADO)."""
    ev = {"boot_id": boot_id, "estado": r.get("estado"), "reloj_mediano_mhz": r.get("reloj_mediano_mhz"), "tflops": r.get("tflops"),
          "tflops_valido": r.get("tflops_valido"), "motivo": r.get("motivo"), "ocupantes": r.get("ocupantes")}
    if "tflops_motivo" in r:
        ev["tflops_motivo"] = r["tflops_motivo"]
    if "captura_incidente" in r:  # solo ATASCADO la trae: ruta, si esta completa y que falta
        c = r["captura_incidente"]
        ev["captura_incidente"] = {k: c[k] for k in ("carpeta", "completa", "could_not_run", "faltan", "motivo") if k in c}
    return {**ev, "firmware": r["firmware"]} if "firmware" in r else ev


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


# --- FEATURE-RELOJ-CAPTURA-DE-INCIDENTE-ANTES-DE-QUITAR-AC-01: el paquete que NVIDIA pide ante una recurrencia ---
# Piezas: `nvidia-smi -q` (sin root), la telemetria de 5 s de las 2 h previas y alrededor del paso sano->atascado, el
# `dmidecode -t 45` y el `nvidia-bug-report.sh`. Las dos de root se PIDEN a `bb-root-run` (scripts sellados por hash, sudoers
# NOPASSWD de un argumento); `sudo -n` nunca pregunta, y ningun camino de este modulo corre nada como root fuera de bb-root-run.
NVSMI_Q = ["nvidia-smi", "-q", "-d", "CLOCK,POWER,TEMPERATURE,PERFORMANCE"]
VENTANA_TELEMETRIA = timedelta(hours=2)
MARGEN_TRANSICION = timedelta(minutes=10)
FORENSE_DIR = Path("/var/lib/blackbox")  # root:root 0755; lo escriben los scripts sellados arranque-forense y nvidia-bug-report
SELLADO_T45 = "arranque-forense"  # ya instalado: deja dmidecode-t45.txt (y anade una fila a arranque.jsonl)
SELLADO_BUG_REPORT = "nvidia-bug-report"  # adopted/root-scripts/nvidia-bug-report.sh; lo instala Luis (INSTALAR_SELLADO)
BUG_REPORT_GZ = "nvidia-bug-report.log.gz"
EN_CURSO = "EN_CURSO"
EN_CURSO_MAX_S = 900  # bb-root-run mata a los 600 s (TIMEOUT_TECHO): mas alla, el completador murio sin cerrar la pieza
INSTALAR_SELLADO = ("Luis, desde el checkout principal: `python3 -m tools.bb_root_manifest --propose`, leer nvidia-bug-report.sh "
                    "en la salida y correr el `sudo sh -c '...'` de su ultima linea (adopted/pendiente-de-despliegue/LEEME.txt)")
PIEZAS = ("nvidia_smi_q", "telemetria_2h", "telemetria_transicion", "dmidecode_t45", "nvidia_bug_report")
RAIZ = Path(__file__).resolve().parents[1]
_TS = re.compile(rb'"ts": ?"([^"]{10,40})"')

Ejecuta = Callable[[list[str], int], tuple[int, str, str]]


def _ejecuta(argv: list[str], timeout: int) -> tuple[int, str, str]:
    """(rc, stdout, stderr); un instrumento ausente es 127 y un timeout 124, nunca una excepcion."""
    try:
        p = subprocess.run(argv, capture_output=True, text=True, check=False, timeout=timeout)
    except FileNotFoundError as e:
        return 127, "", str(e)
    except subprocess.TimeoutExpired:
        return 124, "", f"timeout de {timeout} s"
    return p.returncode, p.stdout, p.stderr


def _cola(texto: str) -> str:
    return " | ".join(texto.strip().splitlines()[-3:])[:300]


def _ok(archivo: str, **extra: Any) -> dict[str, Any]:
    return {"estado": "ok", "archivo": archivo, **extra}


def _cnr(motivo: str, **extra: Any) -> dict[str, Any]:
    return {"estado": "could_not_run", "motivo": motivo, **extra}


def _nvsmi_q(carpeta: Path, ejecuta: Ejecuta) -> dict[str, Any]:
    rc, out, err = ejecuta(NVSMI_Q, 60)
    if rc != 0 or not out.strip():
        return _cnr(f"`{' '.join(NVSMI_Q)}` rc={rc}: {_cola(err or out) or 'sin salida'}")
    (carpeta / "nvidia-smi-q.txt").write_text(out, encoding="utf-8")
    return _ok("nvidia-smi-q.txt")


def _instante(ts: str | None) -> datetime | None:
    try:
        t = datetime.fromisoformat(ts) if ts else None
    except ValueError:
        return None
    return t if t is not None and t.tzinfo is not None else None  # sin zona no se compara: se descarta, no se supone UTC


def _telemetria(carpeta: Path, origen: Path, ahora: datetime, desde: dict[str, Any] | None) -> dict[str, dict[str, Any]]:
    """Copia literal (las filas tal cual) de la telemetria de 5 s: las 2 h previas a `ahora` y, si `inicio` encontro el paso
    sano->atascado, 10 min a cada lado de el (puede ser anterior a las 2 h). Cada ventana es su propia pieza."""
    t0 = ahora - VENTANA_TELEMETRIA
    sana, atascada = _instante((desde or {}).get("ultima_sana")), _instante((desde or {}).get("primera_atascada"))
    paso = (sana - MARGEN_TRANSICION, atascada + MARGEN_TRANSICION) if sana and atascada else None
    destino = carpeta / "telemetria.jsonl"
    n_2h = n_paso = 0
    try:
        with origen.open("rb") as fh, destino.open("wb") as out:
            for linea in fh:
                m = _TS.search(linea, 0, 120)
                t = _instante(m.group(1).decode("ascii", "replace")) if m else None
                if t is None:
                    continue
                en_2h, en_paso = t0 <= t <= ahora, paso is not None and paso[0] <= t <= paso[1]
                if en_2h or en_paso:
                    out.write(linea)
                    n_2h += en_2h
                    n_paso += en_paso
    except OSError as e:
        destino.unlink(missing_ok=True)
        motivo = f"{origen} ilegible ({e.strerror})"
        return {"telemetria_2h": _cnr(motivo), "telemetria_transicion": _cnr(motivo)}
    if not n_2h and not n_paso:
        destino.unlink(missing_ok=True)
    p2h = _ok("telemetria.jsonl", filas=n_2h, desde=t0.isoformat(timespec="seconds")) if n_2h else _cnr(
        f"{origen} sin filas entre {t0.isoformat(timespec='seconds')} y {ahora.isoformat(timespec='seconds')}")
    if paso is None:
        ptr = _cnr("NOT_COLLECTED: inicio() no encontro en la telemetria el paso sano->atascado (sin ultima_sana/primera_atascada)")
    elif n_paso:
        ptr = _ok("telemetria.jsonl", filas=n_paso, ultima_sana=(desde or {}).get("ultima_sana"), primera_atascada=(desde or {}).get("primera_atascada"))
    else:
        ptr = _cnr(f"{origen} ya no tiene filas alrededor del paso {sana} -> {atascada} (rotada)")
    return {"telemetria_2h": p2h, "telemetria_transicion": ptr}


def _dmidecode_t45(carpeta: Path, forense: Path, arranque_s: float, ejecuta: Ejecuta) -> dict[str, Any]:
    """La copia de `arranque-forense` vale si es de ESTE arranque (el firmware solo cambia al reiniciar tras actualizar).
    Si no lo es, se pide el script sellado una vez y se vuelve a mirar; una copia de otro arranque nunca se adjunta."""
    origen = forense / "dmidecode-t45.txt"

    def de_este_arranque() -> bool:
        try:
            return origen.stat().st_mtime >= arranque_s
        except OSError:
            return False

    pedido = ""
    if not de_este_arranque():
        rc, out, err = ejecuta(["sudo", "-n", "bb-root-run", SELLADO_T45], 120)
        pedido = f"; pedido `sudo -n bb-root-run {SELLADO_T45}`: rc={rc} {_cola(err or out)}"
        if not de_este_arranque():
            return _cnr(f"{origen} ausente o anterior a este arranque{pedido}")
    try:
        shutil.copyfile(origen, carpeta / "dmidecode-t45.txt")
    except OSError as e:
        return _cnr(f"{origen} ilegible ({e.strerror}){pedido}")
    return _ok("dmidecode-t45.txt")


def _sellado_instalado(nombre: str, manifiesto: Path) -> str | None:
    """None si `nombre` esta en el manifiesto instalado de bb-root-run; si no, el motivo (con el paso de root de Luis)."""
    try:
        m = json.loads(manifiesto.read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        return f"{manifiesto} ilegible ({e}); {INSTALAR_SELLADO}"
    return None if isinstance(m, dict) and nombre in m else f"el script sellado `{nombre}` no esta en {manifiesto}; {INSTALAR_SELLADO}"


def _pide_bug_report(carpeta: Path, ahora_s: float, manifiesto: Path, ejecuta: Ejecuta) -> dict[str, Any]:
    """Lanza en segundo plano `--completar-bug-report` en una unidad transitoria de usuario (`systemd-run --user`): sobrevive
    al fin de este proceso y al de la unit oneshot de `--arranque`. La pieza queda EN_CURSO, que NO es ok."""
    falta = _sellado_instalado(SELLADO_BUG_REPORT, manifiesto)
    if falta:
        return _cnr(f"NO_INSTALADO: {falta}")
    unidad = f"bb-reloj-bug-report-{int(ahora_s)}"
    rc, out, err = ejecuta(["systemd-run", "--user", "--collect", "--quiet", f"--unit={unidad}", f"--working-directory={RAIZ}",
                            sys.executable, "-m", "tools.reloj_atascado", "--completar-bug-report", str(carpeta)], 30)
    if rc != 0:
        return _cnr(f"systemd-run rc={rc}: {_cola(err or out)}")
    return _cnr(f"{EN_CURSO}: `sudo -n bb-root-run {SELLADO_BUG_REPORT}` lanzado en la unidad {unidad}; tarda minutos y la "
                f"captura NO esta completa hasta que esta pieza diga ok (journalctl --user -u {unidad})", lanzado_s=ahora_s)


def _resumen(piezas: dict[str, dict[str, Any]]) -> dict[str, Any]:
    faltan = [k for k in PIEZAS if (piezas.get(k) or {}).get("estado") != "ok"]
    return {"completa": not faltan, "could_not_run": len(faltan), "faltan": faltan}


def _escribe_captura(carpeta: Path, datos: dict[str, Any]) -> None:
    tmp = carpeta / "captura.json.nuevo"
    tmp.write_text(json.dumps(datos, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    os.replace(tmp, carpeta / "captura.json")


def _lee_captura(carpeta: Path) -> dict[str, Any]:
    try:
        d = json.loads((carpeta / "captura.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return d if isinstance(d, dict) else {}


def _boot_id() -> str:
    return Path("/proc/sys/kernel/random/boot_id").read_text(encoding="utf-8").strip()


def _arranque_s() -> float:
    return time.time() - float(Path("/proc/uptime").read_text(encoding="utf-8").split()[0])


def captura_incidente(desde: dict[str, Any] | None, *, base: Path | None = None, telemetria: Path | None = None,
                      forense: Path = FORENSE_DIR, manifiesto: Path | None = None, ejecuta: Ejecuta = _ejecuta,
                      ahora: Callable[[], float] = time.time, boot_id: str | None = None, arranque_s: float | None = None) -> dict[str, Any]:
    """Arma (o completa) `incidentes/reloj-<boot_id>/` junto a la telemetria: una carpeta por arranque, porque el estado atascado
    dura todo el arranque y el bug-report pesa. Una pieza ya `ok`, o EN_CURSO desde hace menos de `EN_CURSO_MAX_S`, no se
    repite; las demas se reintentan. `captura.json` lista cada pieza (`ok` con su archivo o `could_not_run` con su motivo) y
    `completa` solo es true con las cinco en ok. El bug-report se pide al final, con captura.json ya escrito, para que su
    completador (`completar_bug_report`) sea el unico escritor despues."""
    telemetria = g.TELEMETRIA if telemetria is None else telemetria
    manifiesto = Path(rr.MANIFEST) if manifiesto is None else manifiesto
    boot = _boot_id() if boot_id is None else boot_id
    carpeta = (telemetria.parent / "incidentes" if base is None else base) / f"reloj-{boot}"
    carpeta.mkdir(parents=True, exist_ok=True)
    previo = _lee_captura(carpeta)
    piezas: dict[str, dict[str, Any]] = dict(previo.get("piezas") or {})
    t = ahora()

    def falta(k: str) -> bool:
        p = piezas.get(k) or {}
        if p.get("estado") == "ok":
            return False
        return not (str(p.get("motivo", "")).startswith(EN_CURSO) and t - float(p.get("lanzado_s", 0)) < EN_CURSO_MAX_S)

    if falta("nvidia_smi_q"):
        piezas["nvidia_smi_q"] = _nvsmi_q(carpeta, ejecuta)
    if falta("telemetria_2h") or falta("telemetria_transicion"):
        piezas.update(_telemetria(carpeta, telemetria, datetime.fromtimestamp(t, timezone.utc), desde))
    if falta("dmidecode_t45"):
        piezas["dmidecode_t45"] = _dmidecode_t45(carpeta, forense, _arranque_s() if arranque_s is None else arranque_s, ejecuta)
    pedir = falta("nvidia_bug_report")
    if pedir:
        piezas["nvidia_bug_report"] = _cnr(f"{EN_CURSO}: por lanzar", lanzado_s=t)
    datos = {"carpeta": str(carpeta), "boot_id": boot, "creada": previo.get("creada") or datetime.fromtimestamp(t, timezone.utc).isoformat(timespec="seconds"),
             "actualizada": datetime.fromtimestamp(t, timezone.utc).isoformat(timespec="seconds"), "piezas": piezas}
    _escribe_captura(carpeta, {**datos, **_resumen(piezas)})
    if pedir:
        piezas["nvidia_bug_report"] = _pide_bug_report(carpeta, t, manifiesto, ejecuta)
        _escribe_captura(carpeta, {**datos, **_resumen(piezas)})
    return {**datos, **_resumen(piezas)}


def completar_bug_report(carpeta: Path, *, forense: Path = FORENSE_DIR, ejecuta: Ejecuta = _ejecuta,
                         ahora: Callable[[], float] = time.time) -> int:
    """Lo corre la unidad transitoria: pide el bug-report a bb-root-run, guarda su salida, copia el .log.gz SOLO si es de esta
    corrida (rc 0 y mtime posterior al inicio) y cierra la pieza en captura.json. 0 si quedo ok, 2 si no."""
    t0 = ahora()
    rc, out, err = ejecuta(["sudo", "-n", "bb-root-run", SELLADO_BUG_REPORT], rr.TIMEOUT_TECHO + 60)
    (carpeta / "nvidia-bug-report.salida.txt").write_text(out + err, encoding="utf-8")
    origen = forense / BUG_REPORT_GZ
    try:
        nuevo = origen.stat().st_mtime >= t0 - 2  # 2 s: los sellos de tiempo del sistema de archivos van con reloj grueso
    except OSError:
        nuevo = False
    if rc != 0 or not nuevo:
        pieza = _cnr(f"`sudo -n bb-root-run {SELLADO_BUG_REPORT}` rc={rc}" + ("" if nuevo else f", sin {origen} de esta corrida")
                     + f": {_cola(err or out)} (salida completa en nvidia-bug-report.salida.txt)")
    else:
        try:
            shutil.copyfile(origen, carpeta / BUG_REPORT_GZ)
            pieza = _ok(BUG_REPORT_GZ)
        except OSError as e:
            pieza = _cnr(f"{origen} ilegible ({e.strerror})")
    d = _lee_captura(carpeta)
    piezas = {**(d.get("piezas") or {}), "nvidia_bug_report": pieza}
    _escribe_captura(carpeta, {**d, "piezas": piezas, "actualizada": datetime.fromtimestamp(ahora(), timezone.utc).isoformat(timespec="seconds"),
                               **_resumen(piezas)})
    return 0 if pieza["estado"] == "ok" else 2


def linea_captura(c: dict[str, Any]) -> str:
    """Pura. La linea final para quien esta a punto de quitar la corriente: ruta, completa o no, y que falta y por que."""
    if "carpeta" not in c:
        return f"bb reloj: captura de incidente could_not_run: {c.get('motivo')}"
    faltan = "; ".join(f"{k}: {(c['piezas'].get(k) or {}).get('motivo')}" for k in c["faltan"])
    return (f"bb reloj: captura de incidente en {c['carpeta']}: {'COMPLETA' if c['completa'] else 'INCOMPLETA'}, "
            f"could_not_run={c['could_not_run']} de {len(PIEZAS)}" + (f" -- {faltan}" if faltan else ""))


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="bb reloj")
    ap.add_argument("--prueba", action="store_true", help="prueba activa de ~15 s con carga en la GPU")
    ap.add_argument("--arranque", action="store_true", help="prueba activa y registra el veredicto segun el interruptor reloj_arranque (lo corre bb-reloj-arranque.timer)")
    ap.add_argument("--completar-bug-report", metavar="CARPETA", help="uso interno: lo lanza la captura de incidente en una unidad transitoria")
    ap.add_argument("--ab", type=int, metavar="N", help="A/B del calentamiento: N corridas de --prueba sin y N con calentamiento; carga la GPU ~2N x 15 s, solo con la GPU libre")
    a = ap.parse_args(argv)
    if a.completar_bug_report:
        return completar_bug_report(Path(a.completar_bug_report))
    if a.ab is not None:
        res = ab(a.ab)
        print(json.dumps(res, indent=1, ensure_ascii=False))
        return 2 if res["veredicto"].startswith("COULD_NOT_RUN") else 0
    r = prueba() if (a.prueba or a.arranque) else decide(g.lee_cola(filas=60))
    atascado = r.get("estado") == "ATASCADO"
    if atascado:
        r["firmware"] = firmware()
    # `--arranque` (una vez por boot) recorre la telemetria aunque salga SANO: asi el episodio cerrado se copia a
    # episodios_reloj.jsonl antes de que la telemetria rote (~1 s sobre 235 MB, medido 2026-10-26).
    desde = inicio() if (atascado or a.arranque) else None
    if atascado:
        # BB_RELOJ_CAPTURA=off solo existe para pruebas que corren el modulo como script; se declara, nunca se calla.
        if os.environ.get("BB_RELOJ_CAPTURA") == "off":
            r["captura_incidente"] = _cnr("desactivada por BB_RELOJ_CAPTURA=off")
        else:
            try:
                r["captura_incidente"] = captura_incidente(desde)
            except OSError as e:  # sin carpeta no hay captura, pero el veredicto ATASCADO se imprime igual
                r["captura_incidente"] = _cnr(f"no se pudo escribir la carpeta de incidente ({e})")
    if a.arranque:
        boot = Path("/proc/sys/kernel/random/boot_id").read_text(encoding="utf-8").strip()
        arranque(interruptores.modo(NOMBRE), r, boot)
    if atascado:
        r["desde"] = desde
        r["remedio"] = REMEDIO
    print(json.dumps(r, indent=1, ensure_ascii=False))
    if "captura_incidente" in r:
        print(linea_captura(r["captura_incidente"]), file=sys.stderr)
    return codigo(r, a.arranque)


def codigo(r: dict[str, Any], es_arranque: bool = False) -> int:
    """Pura. 0 sano, 1 atascado, 2 indeterminado. Unica excepcion, solo en `--arranque`: INDETERMINADO porque la carga no pudo
    correr con la GPU ocupada por otros procesos sale 0. Es el entorno (el motor arranca solo con la maquina), no el instrumento,
    y la fila de `reloj_arranque.jsonl` ya lo dice; con 2 systemd marcaba `Failed` cada boot. CARGA_NO_PUDO_CORRER con la GPU
    libre (sin torch, sin CUDA) y NOT_COLLECTED siguen en 2: eso es el instrumento roto y debe verse."""
    estado = str(r.get("estado"))
    if es_arranque and estado == "INDETERMINADO" and str(r.get("motivo")).startswith("CARGA_NO_PUDO_CORRER") and r.get("ocupantes"):
        return 0
    return {"SANO": 0, "ATASCADO": 1}.get(estado, 2)


if __name__ == "__main__":
    sys.exit(main())
