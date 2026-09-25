#!/usr/bin/env python3
"""Sampler de vida larga que deja telemetría de GPU y térmica de la ATOM en
disco, para que el próximo crash tenga los segundos previos escritos (DGX-334,
2026-08-31).

Por qué existe: el tercer crash del 2026-08-31 (boot `f1998ed9`) murió **sin
ninguna señal de kernel** — ni OOM, ni Xid, ni térmico, ni panic — con vLLM
sirviendo, un job de re-minado por LLM y una sesión remota compitiendo por el
mismo pool unificado. `earlyoom` mide la RAM que el SO ve y no vio nada; el
pool de la GPU, que es lo que probablemente se agotó, no lo mide nadie. Sin un
registro periódico no queda evidencia de los segundos previos a la muerte, y
eso fue exactamente lo que faltó para elegir entre las dos hipótesis abiertas
del diagnóstico manual.

Diseño:

1. **Proceso de vida larga, no un oneshot por timer.** Una muestra cada 5 s
   disparada por systemd serían 17,280 arranques de intérprete al día para
   leer tres números; el loop propio con `time.sleep` cuesta un proceso.
2. **El margen de alarma se mide contra el trip point de CADA zona, no contra
   un número global.** `MARGEN_TRIP_C = 10.0` sale de una medición en vivo del
   2026-08-31 en esta máquina: bajo 93% de uso sostenido de GPU la zona más
   caliente marcaba 86.2 °C y el trip `critical` de las 7 zonas está en
   104.8 °C. Un margen de 10 °C pone el umbral en 94.8 °C — 8.6 °C por encima
   del techo medido con carga pesada real, así que el trabajo normal no
   dispara nada, y 10 °C por debajo del punto donde el kernel actúa por su
   cuenta, así que queda registro ANTES de que la máquina se apague sola. Un
   margen global fijo se rompería en cuanto una zona declarara otro trip.
3. **Debounce en las dos transiciones.** `temp_critica` se escribe una vez al
   cruzar hacia arriba y `temp_normalizada` una vez al bajar; entre medias el
   log sólo lleva muestras. Sin esto un episodio térmico de una hora escribiría
   720 líneas de alarma idénticas y el evento dejaría de ser un evento. La
   histéresis de 2 °C existe para que una zona oscilando sobre el umbral no
   emita pares de eventos en cada muestra.
4. **Toda ausencia se declara en el log, ninguna se omite.** Si `nvidia-smi`
   no está, falla, o devuelve `[N/A]`, la línea lo dice en `gpu_ausente` en vez
   de callar el campo o tumbar el sampler; si no hay zonas térmicas, lo dice en
   `zonas_ausentes`. Mismo principio que `_vmcore_para()` en
   `tools/detect_atom_crash.py`: un instrumento que no puede hablar no es
   evidencia de que no pasó nada.
5. **La misma iteración vigila el journal (DGX-336).** No hay un tercer
   proceso: el sampler ya despierta cada 5 s y ya es el log de eventos de
   hardware de esta máquina. Lo que busca son las señales de *pérdida de video
   sin caída completa del sistema*, que por definición NO deja rastro en
   `detect_atom_crash.py` — ese sólo mira boots que terminaron sucios, y el
   caso real del 2026-08-30 07:38:47 (boot `485fe3f1`) siguió corriendo 28 h
   más después de perder el video.
"""
import argparse
import json
import os
import re
import signal
import subprocess
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

# (sin sys.path: al venir de Atlas traia un solo acoplamiento, _argv_tokens,
#  y esta abajo copiado -- 8 lineas. Ver DGX-585.)

# `_argv_tokens` es la lectura token a token de /proc/<pid>/cmdline que el job
# nocturno ya endureció contra el falso positivo de `pgrep -f` (self-match y
# vecinos, pagado dos veces). Se IMPORTA aunque sea privada, exactamente como
# ya la importa `tools/liberation_watchdog.py` y por el mismo motivo: una
# segunda copia divergiría en la primera corrección. Costo medido de traerla
# aquí: +36 MB de RSS en el sampler (9,992 -> 46,660 KB de ru_maxrss) y +0.36 s
# de arranque, una sola vez -- este proceso vive semanas y muestrea cada 5 s.
def _argv_tokens(pid: str) -> list[str]:
    """argv real de un proceso desde /proc/<pid>/cmdline (separado por NUL).
    Lista vacia si el proceso murio entre el listado y la lectura.

    Copiado de `tools/nightly_kb_consolidation.py` de Atlas al traer este
    modulo el 2026-09-24 (DGX-585). Era el UNICO acoplamiento a Atlas de este
    fichero -- el dictamen de DGX-483 afirmo que importaba `tools.durable_log`
    y `tools.tool_limits`, y contra el fichero de ese mismo dia (66fb9e57) eso
    era falso: importaba esto y nada mas."""
    try:
        raw = (Path("/proc") / pid / "cmdline").read_bytes()
    except OSError:
        return []
    return [t for t in raw.decode("utf-8", "replace").split("\0") if t]

REPO = Path(__file__).resolve().parent.parent
# Los datos NO viven en el repo: van al directorio de datos de blackbox, que es
# de donde Atlas los lee ahora ("que atlas consuma lo que bb produce", Luis
# 2026-09-24). Se respeta BLACKBOX_DATA, igual que el resto de esta caja.
DATA_DIR = Path(os.environ.get("BLACKBOX_DATA", Path.home() / ".local/share/blackbox"))
JSONL_PATH = Path(os.environ.get("ATOM_TELEMETRY_JSONL", DATA_DIR / "atom_gpu_telemetry.jsonl"))
THERMAL_DIR = Path("/sys/class/thermal")

INTERVALO_DEFAULT_S = 5.0
MARGEN_TRIP_C = 10.0
HISTERESIS_C = 2.0
MAX_LINEAS = 200_000
LINEAS_A_CONSERVAR = 100_000

# Techo por BYTES para el guardia en caliente, y el número sale de medir el
# fichero real, no de la estimación que este módulo traía escrita.
#
# Medido el 2026-09-25 sobre `atom_gpu_telemetry.jsonl`: 138.3 MB en 150 040
# líneas = **966 bytes por línea**. El docstring de `rotar_si_hace_falta` decía
# "~400 bytes por línea" y por tanto "~75 MB" para las 200 000 líneas del
# anillo. Son **184 MB**: el techo declarado estaba 2.4 veces por debajo del
# real, y nadie lo habría notado porque el único momento en que se comprobaba
# era al arrancar el proceso.
#
# 192 MB deja el corte justo por encima de esas 200 000 líneas a la densidad
# medida, así que el guardia de bytes no se adelanta al de líneas: actúa cuando
# el de líneas ya debería haber actuado y no pudo, que es el hueco de esta
# ficha.
MAX_BYTES = 192 * 1024 * 1024

# Cada cuántas muestras se mira el tamaño. A 5 s son 60 minutos, y el coste de
# mirar es un `stat`: comprobarlo en cada iteración también sería barato, pero
# lo que dispara es caro -- `rotar_si_hace_falta` lee el fichero ENTERO en
# memoria-- y no hace falta detectarlo con resolución de segundos algo que
# tarda días en ocurrir.
MUESTRAS_ENTRE_REVISIONES = 720
VLLM_METRICS_URL_DEFAULT = "http://127.0.0.1:8000/metrics"
VLLM_METRICS_TIMEOUT_S = 1.0

# DGX-383 (2026-09-01): `presupuesto_termico()` decidía con UNA muestra
# instantánea -- sin debounce ni compuerta de carga-- y frena trabajo real en
# dos sitios (`liberation_watchdog` antes de tomar el job siguiente,
# `ingest_batch` antes de ingerir la URL siguiente). Medido sobre las 11,810
# muestras de `logs/atom_gpu_telemetry.jsonl`, ventana 01:53Z->19:56Z: de sus
# 63 episodios de alarma sólo 27 sobreviven una compuerta de >=60 W, o sea que
# **36 de 63 (57%) disparan con el GPU ocioso** (<20 W, 4-8% de utilización).
# El sensor `acpitz` lo explica: entre muestras consecutivas a 5 s la mediana
# del salto es 0.60°C pero el p99 es 11.2°C y el máximo 28.4°C, y hay una
# ventana literal con el GPU a 14 W donde `thermal_zone0` sube de 81.6 a
# 95.0°C en 5 s y vuelve a 83.7 en 15 s.
#
# **Los dos ingredientes atacan poblaciones DISTINTAS**, y por eso van los dos
# -- medido sobre las 63 corridas calientes de ese mismo log:
#   * el PICO AISLADO: 6 de las 19 corridas ociosas duran UNA sola muestra, y
#     ninguna compuerta de carga las toca, porque no es de carga de lo que
#     hablan. Las mata el debounce.
#   * la corrida ociosa LARGA: entre esas mismas ociosas hay una de 43 muestras
#     (3.5 min) y otra de 25, que ningún N practicable mataría. Las mata la
#     compuerta de carga, y sólo ella.
#
# `DEBOUNCE_MUESTRAS = 3` (la lectura fresca del llamador más las 2 previas del
# log, ~10 s de ventana) sale de barrer ese mismo log contando los episodios
# que BLOQUEARÍAN bajo la regla exacta de `_corroboracion`, a >=60 W:
#
#     N=1: 63   N=2: 25   N=3: 22   N=4: 21   N=5: 20   N=10: 14
#
# El techo de N no lo pone esa curva, lo pone el sujeto: el quinto crash de
# DGX-342 murió **8 s después** del último cruce, así que un debounce de N=10
# (45 s de ventana) llegaría tarde a lo único que este gate existe para ver.
# N=3 cuesta ~10 s de latencia y conserva las 21 de 26 corridas CON CARGA de
# 3 muestras o más -- las sostenidas, que en el log real duran entre 18 y 42
# muestras (1.5 a 3.5 min), o sea minutos de margen.
#
# `CARGA_MINIMA_W = 60.0` no es un número elegido: es el corte del control
# negativo del dictamen. Filtrando a las 768 muestras con el GPU >=60 W,
# `thermal_zone0` tiene mediana 94.0°C y máximo 98.3°C -- **bajo carga la
# temperatura alta SÍ es real**, y ese caso tiene que seguir bloqueando. Lo que
# deja de bloquear es el otro.
DEBOUNCE_MUESTRAS = 3
CARGA_MINIMA_W = 60.0

# El sampler escribe cada `INTERVALO_DEFAULT_S` (5 s), así que 30 s son seis
# intervalos de margen. Pasado ese punto la telemetría no describe el presente
# y NO se usa para absolver: se cae al criterio de una sola muestra, que
# bloquea, y el motivo lo dice. Un gate que se vuelve permisivo cuando su
# instrumento se cae es exactamente el fallo que la política de reporte de la
# casa prohíbe -- cero capturas es defecto del instrumento, nunca evidencia de
# que el sujeto esté limpio.
MUESTRA_MAX_ANTIGUEDAD_S = 30.0

# Cola del jsonl que se lee para reconstruir el historial. A ~560 bytes por
# línea (medido: 6,765,620 bytes / 12,106 líneas) son ~117 muestras, de sobra
# para cualquier `DEBOUNCE_MUESTRAS` razonable. Se lee la COLA y no el archivo:
# `MAX_LINEAS` lo deja crecer a 200,000 líneas (~75 MB) y `ingest_batch` lo
# consulta cada 30 s mientras dura un lote.
COLA_BYTES = 64 * 1024

# DGX-342 (2026-09-01): el quinto crash del día tuvo 6 cruces de temp_critica
# en los 27 minutos previos, coincidiendo con GPU al 92-96% sostenido -- la
# alarma detectaba y logueaba pero no hacía nada, y la máquina murió 8s
# después del último cruce. Estos son los ÚNICOS procesos que la mitigación
# puede pausar: lotes por lote propios de Atlas, medidos esta noche como la
# carga sostenida real (build_incremental.py con ~14 núcleos, remine_harvest_lens.py
# llamando al LLM local en bucle). NUNCA vLLM ni nada fuera de esta lista --
# vLLM es infraestructura compartida de toda la flota (CLAUDE.md), pausarlo
# rompería a cualquier otro consumidor sin que la mitigación lo supiera.
PROCESOS_MITIGABLES = ("remine_harvest_lens.py", "build_incremental.py",
                       "tools/ingest.py")

# Raíz del listado de procesos. Es constante de módulo y no una ruta literal
# dentro de la función para que el test pueda apuntarla a un /proc de mentira y
# no dependa de qué corra en la máquina.
PROC_DIR = Path("/proc")

# Ventana de deduplicación de alertas de journal, en segundos de RELOJ DE LA
# ENTRADA (no del muestreo). Sale de la ráfaga real del 2026-08-30 07:38:47 en
# esta máquina, boot `485fe3f1`: 144 líneas `Xid ...: 13` más una `Xid ...: 43`,
# TODAS con el mismo sello de segundo. Con 2.0 s esa ráfaga cuenta como dos
# eventos (uno por Xid distinto) en vez de 145 alertas.
VENTANA_DEDUPE_S = 2.0

# El número de Xid viene DESPUÉS del paréntesis con la dirección PCI en el
# formato que este driver emite -- `NVRM: Xid (PCI:000f:01:00): 13, ...` -- así
# que el patrón obvio `Xid\s+\d+` matchea CERO de las 145 líneas reales de la
# ráfaga del 2026-08-30 (medido). El paréntesis es opcional porque otras
# versiones del driver sí escriben `Xid 79:` pelado.
_RE_XID = re.compile(r"\bXid\s*(?:\([^)]*\))?\s*:?\s*(\d+)")
_RE_PID = re.compile(r"\bpid=(\d+)")

# Catálogo de "video/GPU en problemas SIN caída completa del sistema". Cada
# entrada es (tipo, patrón, transporte exigido). El orden importa: gana el
# primer patrón que matchea, así que lo específico va antes que lo genérico. El
# número de Xid y el pid se extraen aparte y viajan en el evento aunque el tipo
# lo haya decidido otro patrón.
#
# **El transporte es parte del patrón, no un adorno.** Xid, DRM y "fallen off
# the bus" los emite el KERNEL; aceptarlos desde cualquier transporte convierte
# el detector en algo que cualquier proceso del sistema puede disparar
# escribiendo una cadena a syslog. No es hipotético: el control negativo del
# 2026-08-31 lo cazó con un `logger` de prueba de esta misma sesión, cuyo texto
# entró como `gpu_fuera_del_bus` legítimo. `gdm_caido` es el caso contrario —
# lo reporta `systemd[1]`, que no es transporte kernel — así que ahí no se
# exige ninguno.
#
# Los Xid que más importan para pérdida de video, por si aparecen en el log:
#   43 = "GPU stopped processing" / reset robusto de canal -- el driver mata el
#        contexto del proceso ofensor sin tumbar el sistema. ES el que cerró la
#        ráfaga real del 2026-08-30 (`pid=39320, name=python3`).
#   62 = "internal micro-controller halt".
#   79 = "GPU has fallen off the bus" -- el más severo de los tres.
#
# Controles negativos MEDIDOS el 2026-08-31 contra el journal real de esta
# máquina, no razonados:
#   - Los patrones de DRM exigen la etiqueta `[drm]`/`[drm:funcion]` que pone el
#     propio subsistema, o el nombre del driver `nvidia-drm`. El `drm.*(reset|
#     hang|timeout)` suelto da 0 matches en las 14,901 líneas de kernel de los
#     últimos 6 boots, pero UNO por boot en el journal completo: la línea de
#     `kdump-tools` que repite la línea de comandos del kernel, donde conviven
#     `plymouth.use-simpledrm` y `reset_devices` sin ninguna relación entre sí.
#     Con la etiqueta exigida ese falso positivo desaparece y las líneas
#     `[drm] Initialized ...` / `[drm] Registered 1 planes with drm panic` de
#     todo arranque sano siguen fuera, que es la trampa que
#     `PATRONES_DIAGNOSTICO` ya había pisado en DGX-326.
#   - `gdm_caido` mira al `systemd[1]` que reporta la unidad, NO al proceso
#     `gdm3[pid]`: el patrón intuitivo `gdm3?\[.*\]:.*(crash|core dump|failed)`
#     da 73 falsos positivos sobre 348 líneas de historia de gdm (son
#     `assertion 'GDM_IS_REMOTE_DISPLAY (display)' failed` y `Session never
#     registered, failing`, ruido de cada logout normal). La forma estricta da
#     2 matches, y son la caída real del 2026-08-01 01:17:21.
_ETIQUETA_DRM = r"(?:\[drm[^\]]*\]|nvidia-drm)"

PATRONES_VIDEO: tuple[tuple[str, re.Pattern, str | None], ...] = (
    ("gpu_fuera_del_bus",
     re.compile(r"GPU has fallen off the bus", re.IGNORECASE), "kernel"),
    ("xid", _RE_XID, "kernel"),
    ("drm_reset",
     re.compile(_ETIQUETA_DRM + r".*(?:reset|hang|timeout)", re.IGNORECASE),
     "kernel"),
    ("drm_error", re.compile(_ETIQUETA_DRM + r".*error", re.IGNORECASE), "kernel"),
    ("gdm_caido",
     re.compile(r"gdm\.service:\s*(?:Main process exited|Failed with result)"),
     None),
)


def _ahora() -> str:
    return datetime.now(timezone.utc).isoformat()


def _correr(*args: str) -> str:
    return subprocess.run(list(args), capture_output=True, text=True,
                          check=False).stdout


def _a_float(texto) -> float | None:
    """`nvidia-smi` devuelve `[N/A]` en campos que esta plataforma no expone
    (`memory.used` es el caso conocido del GB10), y un `temp` de sysfs puede
    venir vacío si la zona desapareció entre el glob y la lectura."""
    try:
        return float(texto)
    except (TypeError, ValueError):
        return None


def _leer_texto(ruta: Path) -> str | None:
    try:
        return ruta.read_text(encoding="utf-8").strip()
    except OSError:
        return None


def _zonas_ordenadas() -> list[Path]:
    """Orden natural: `thermal_zone10` va después de `thermal_zone9`, no entre
    el 1 y el 2 como haría el orden lexicográfico."""
    try:
        zonas = [p for p in THERMAL_DIR.glob("thermal_zone*") if p.is_dir()]
    except OSError:
        return []
    return sorted(zonas, key=lambda p: (len(p.name), p.name))


def leer_umbrales() -> dict:
    """Se leen UNA vez al arrancar el proceso: los trip points de una zona son
    fijos, releerlos en cada muestra sería I/O por nada.

    El techo de una zona es el trip point MÁS BAJO que declara, que es el
    primero ante el que el kernel actuaría. Medido en vivo el 2026-08-31 en
    esta máquina: las 7 zonas son `acpitz` y cada una declara exactamente un
    trip point, `trip_point_0_temp` = 104.8 °C de tipo `critical`.
    """
    umbrales = {}
    for zona in _zonas_ordenadas():
        trips = [_a_float(_leer_texto(p))
                 for p in sorted(zona.glob("trip_point_*_temp"))]
        trips = [t / 1000.0 for t in trips if t is not None]
        trip_c = min(trips) if trips else None
        umbrales[zona.name] = {
            "type": _leer_texto(zona / "type") or "desconocido",
            "trip_c": trip_c,
            "umbral_c": None if trip_c is None else round(trip_c - MARGEN_TRIP_C, 1),
        }
    return umbrales


def leer_zonas() -> list[dict]:
    """Lista, no dict: los 7 `type` de esta máquina son el mismo string
    (`acpitz`), y un dict tecleado por tipo pisaría 6 de 7 lecturas."""
    zonas = []
    for zona in _zonas_ordenadas():
        temp = _a_float(_leer_texto(zona / "temp"))
        zonas.append({
            "zona": zona.name,
            "type": _leer_texto(zona / "type") or "desconocido",
            "temp_c": None if temp is None else round(temp / 1000.0, 1),
        })
    return zonas


def leer_gpu() -> dict:
    """`memory.used`/`memory.total` NO se piden a propósito: en el GB10 la
    memoria es unificada y esos campos devuelven `[N/A]`, así que pedirlos
    sería registrar un hueco con forma de dato. La memoria de GPU que sí
    existe se obtiene en `leer_procesos_gpu()`, sumando los procesos de cómputo.

    `sm_clk`, `pstate` y `throttle` se piden en ESTA misma invocación y no en
    otra: son tres columnas más del mismo `nvidia-smi`, coste cero. Venían de
    `/srv/ai/gpu_governance/gpu_sampler.sh`, retirado el 2026-09-07 al
    consolidar aquí las dos telemetrías de GPU que se solapaban.
    """
    campos_vacios = {"gpu_temp_c": None, "gpu_util_pct": None, "gpu_power_w": None,
                     "sm_clk_mhz": None, "pstate": None, "throttle": None}
    try:
        salida = _correr("nvidia-smi",
                         "--query-gpu=temperature.gpu,utilization.gpu,power.draw,"
                         "clocks.current.sm,pstate,clocks_throttle_reasons.active",
                         "--format=csv,noheader,nounits")
    except OSError as exc:
        return {**campos_vacios, "gpu_ausente": f"nvidia-smi no ejecutable: {exc}"}

    linea = next((ln for ln in salida.splitlines() if ln.strip()), "")
    valores = [c.strip() for c in linea.split(",")]
    if len(valores) != 6:
        return {**campos_vacios,
                "gpu_ausente": f"nvidia-smi no devolvió 6 columnas: {linea!r}"}

    lectura: dict[str, float | str | None] = {
        "gpu_temp_c": _a_float(valores[0]),
        "gpu_util_pct": _a_float(valores[1]),
        "gpu_power_w": _a_float(valores[2]),
        "sm_clk_mhz": _a_float(valores[3]),
        # `pstate` (P0..P12) y `throttle` (máscara hex) son categóricos, no
        # números: se guardan tal cual y no pasan por `_a_float`.
        "pstate": valores[4] or None,
        "throttle": valores[5] or None,
    }
    # Sólo los numéricos cuentan como "faltantes": un pstate vacío ya se ve
    # como None y no debe disparar `gpu_ausente` sobre los otros campos.
    faltantes = [k for k in ("gpu_temp_c", "gpu_util_pct", "gpu_power_w", "sm_clk_mhz")
                 if lectura[k] is None]
    if faltantes:
        lectura["gpu_ausente"] = f"campos no numéricos: {', '.join(faltantes)}"
    return lectura


def leer_memoria_sistema() -> dict:
    """MemFree además de MemAvailable. En el cuelgue del 2026-09-07
    MemAvailable decía 28 GB mientras MemFree estaba en 4.6 GB: mirar sólo el
    primero oculta la presión real, y con memoria unificada la GPU compite por
    esa misma bolsa. Lee `/proc/meminfo`, sin subproceso."""
    try:
        crudo = Path("/proc/meminfo").read_text(encoding="utf-8")
    except OSError as exc:
        return {"mem_free_mb": None, "mem_avail_mb": None,
                "mem_ausente": f"/proc/meminfo ilegible: {exc}"}
    campos: dict[str, float | str | None] = {"mem_free_mb": None, "mem_avail_mb": None}
    for linea in crudo.splitlines():
        partes = linea.split()
        if len(partes) >= 2 and partes[0] == "MemFree:":
            campos["mem_free_mb"] = round(int(partes[1]) / 1024.0)
        elif len(partes) >= 2 and partes[0] == "MemAvailable:":
            campos["mem_avail_mb"] = round(int(partes[1]) / 1024.0)
    faltantes = [k for k, v in campos.items() if v is None]
    if faltantes:
        campos["mem_ausente"] = f"no encontrados en /proc/meminfo: {', '.join(faltantes)}"
    return campos


# Los procesos de cómputo son una invocación aparte de `nvidia-smi`, así que no
# se piden en cada muestra de 5 s: 1 de cada 3 deja la misma cadencia de 15 s
# que tenía `gpu_sampler.sh`, cuyo trabajo absorbe.
PROCESOS_GPU_CADA = 3


def leer_procesos_gpu() -> dict:
    """La ÚNICA vía fiable de memoria de GPU en el GB10: `--query-gpu` devuelve
    `[N/A]`, pero `--query-compute-apps` sí reporta por proceso. Se suma para
    el agregado (medido 2026-09-07: vLLM 33813 MiB + aequitas_os 10251 MiB)."""
    try:
        salida = _correr("nvidia-smi",
                         "--query-compute-apps=pid,process_name,used_memory",
                         "--format=csv,noheader,nounits")
    except OSError as exc:
        return {"gpu_procs": None, "gpu_mem_total_mib": None,
                "gpu_procs_ausente": f"nvidia-smi no ejecutable: {exc}"}

    procs, total = [], 0.0
    for linea in salida.splitlines():
        if not linea.strip():
            continue
        partes = [c.strip() for c in linea.split(",")]
        if len(partes) != 3:
            continue
        mib = _a_float(partes[2])
        procs.append({"pid": partes[0], "nombre": partes[1].rsplit("/", 1)[-1],
                      "mem_mib": mib})
        if mib is not None:
            total += mib
    # Cero procesos es un dato válido (GPU ociosa), no una ausencia.
    return {"gpu_procs": procs, "gpu_mem_total_mib": round(total)}


def _procesar_linea_vllm(linea: str, res: dict) -> None:
    parts = linea.rsplit(maxsplit=1)
    if len(parts) != 2:
        return
    metric_spec, val_str = parts
    val = _a_float(val_str)
    if val is None:
        return

    if metric_spec.startswith("vllm:num_requests_running"):
        res["vllm_num_requests_running"] = val
    elif metric_spec.startswith("vllm:num_requests_waiting_by_reason"):
        m = re.search(r'reason="([^"]+)"', metric_spec)
        reason = m.group(1) if m else "desconocido"
        by_reason = res["vllm_num_requests_waiting_by_reason"]
        if isinstance(by_reason, dict):
            by_reason[reason] = val
    elif metric_spec.startswith("vllm:num_requests_waiting"):
        res["vllm_num_requests_waiting"] = val
    elif metric_spec.startswith("vllm:kv_cache_usage_perc"):
        res["vllm_kv_cache_usage_perc"] = val
    elif metric_spec.startswith("vllm:num_preemptions_total"):
        res["vllm_num_preemptions_total"] = val


def leer_vllm_metrics(url: str = VLLM_METRICS_URL_DEFAULT,
                      timeout_s: float = VLLM_METRICS_TIMEOUT_S) -> dict:
    """Scrape de `/metrics` de vLLM (DGX-335).

    Si vLLM no está corriendo o la petición falla, los campos numéricos devuelven
    `None` y la causa se declara en `vllm_ausente`. Toda ausencia se declara en
    el log, ninguna se omite.
    """
    campos_vacios: dict[str, float | dict[str, float] | str | None] = {
        "vllm_num_requests_running": None,
        "vllm_num_requests_waiting": None,
        "vllm_num_requests_waiting_by_reason": {},
        "vllm_kv_cache_usage_perc": None,
        "vllm_num_preemptions_total": None,
    }
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Atlas-Telemetry/1.0"})
        with urllib.request.urlopen(req, timeout=timeout_s) as resp:
            if resp.status != 200:
                return {**campos_vacios, "vllm_ausente": f"HTTP status {resp.status}"}
            texto = resp.read().decode("utf-8", errors="replace")
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        return {**campos_vacios, "vllm_ausente": f"vllm /metrics no alcanzable: {exc}"}

    res: dict[str, float | dict[str, float] | str | None] = {
        "vllm_num_requests_running": None,
        "vllm_num_requests_waiting": None,
        "vllm_num_requests_waiting_by_reason": {},
        "vllm_kv_cache_usage_perc": None,
        "vllm_num_preemptions_total": None,
    }

    for linea in texto.splitlines():
        linea = linea.strip()
        if linea and not linea.startswith("#"):
            _procesar_linea_vllm(linea, res)

    return res


def _correr_journalctl(*args: str) -> str:
    """Runner propio, separado del de `nvidia-smi`, aunque la línea de
    `subprocess.run` sea casi la misma: son dos instrumentos con contratos de
    salida distintos (un CSV de una línea contra un JSON por entrada), y
    compartir el punto de sustitución haría que la salida —o la falla— de uno
    se pudiera leer como dato del otro."""
    return subprocess.run(["journalctl", *args], capture_output=True,
                          text=True, check=False).stdout


def cursor_actual() -> str | None:
    """`journalctl -n 0 --show-cursor` imprime el cursor de la COLA sin emitir
    ninguna entrada. Es la semilla que hace que la primera iteración empiece a
    mirar desde *ahora*: sin ella el sampler recorrería los 24 boots que este
    journal guarda y alarmaría por crashes ya diagnosticados."""
    for linea in _correr_journalctl("-n", "0", "--show-cursor",
                                    "--no-pager").splitlines():
        if linea.startswith("-- cursor: "):
            return linea[len("-- cursor: "):].strip()
    return None


def leer_journal_nuevo(cursor: str) -> tuple[list[dict], str | None]:
    """Entradas posteriores a `cursor`, más el cursor de la última.

    **`--after-cursor` y no `--since <timestamp>`**: `--since` tiene
    granularidad de UN segundo y la ráfaga real del 2026-08-30 07:38:47 cae
    entera dentro de un solo tick; con un borde de segundo ese tramo se releería
    completo en la muestra siguiente o se saltaría completo, según cómo se
    redondeara. El cursor identifica la ENTRADA, no el instante, así que no hay
    borde que redondear ni solape que compensar.

    **El journal completo y no sólo `-k`**: la caída del display manager la
    reporta `systemd[1]`, cuyo transporte no es `kernel`, y `journalctl -k -u
    gdm.service` devuelve `-- No entries --` porque las dos condiciones se
    combinan con AND (medido el 2026-08-31). El costo de leerlo todo también
    está medido en esta máquina: 21 líneas por minuto.
    """
    salida = _correr_journalctl(
        "--after-cursor", cursor, "-o", "json", "--no-pager",
        "--output-fields=MESSAGE,SYSLOG_IDENTIFIER,_TRANSPORT")
    entradas: list[dict] = []
    ultimo = None
    for linea in salida.splitlines():
        if not linea.strip():
            continue
        try:
            entrada = json.loads(linea)
        except json.JSONDecodeError:
            continue  # journalctl puede intercalar notas propias; no son datos
        entradas.append(entrada)
        ultimo = entrada.get("__CURSOR") or ultimo
    return entradas, ultimo


def _linea_de(entrada: dict) -> str:
    """`-o json` entrega `MESSAGE` SIN el prefijo `gdm3[2806]:` que sí lleva la
    salida de texto, y el patrón de `gdm_caido` se ancla justamente en ese
    identificador. Se reconstruye `ident: mensaje`, que es la forma que
    `detect_atom_crash.py` ya ve cuando lee el journal como texto.

    `MESSAGE` puede venir como lista de enteros cuando el mensaje no es UTF-8
    válido; ahí se arma el texto a mano, porque un `str(list)` metería corchetes
    y comas dentro de la línea que van a ver los patrones."""
    msg = entrada.get("MESSAGE")
    if isinstance(msg, list):
        msg = bytes(b & 0xFF for b in msg).decode("utf-8", "replace")
    elif not isinstance(msg, str):
        msg = "" if msg is None else str(msg)
    ident = entrada.get("SYSLOG_IDENTIFIER") or ""
    return f"{ident}: {msg}" if ident else msg


def clasificar_linea(linea: str, transporte: str | None = None) -> dict | None:
    """Devuelve el hallazgo de una línea, o None si no matchea el catálogo.

    `transporte` es el `_TRANSPORT` de la entrada del journal. Un patrón que
    exige `kernel` NO matchea una línea que vino por syslog aunque el texto
    coincida: ver el bloque de `PATRONES_VIDEO`."""
    for tipo, patron, exigido in PATRONES_VIDEO:
        if exigido is not None and transporte != exigido:
            continue
        if patron.search(linea):
            m_xid = _RE_XID.search(linea)
            m_pid = _RE_PID.search(linea)
            return {"tipo": tipo,
                    "xid": int(m_xid.group(1)) if m_xid else None,
                    "pid": int(m_pid.group(1)) if m_pid else None,
                    "linea_cruda": linea}
    return None


def vigilar_journal(estado: dict) -> tuple[list[dict], str | None]:
    """Lee lo NUEVO del journal y devuelve (alertas, motivo_de_ausencia).

    El debounce agrupa por `(tipo, xid, pid)` dentro de `VENTANA_DEDUPE_S`
    medidos sobre el reloj de la ENTRADA, no sobre el del muestreo: las 145
    líneas de la ráfaga real llegan en la misma lectura, así que un debounce
    por muestra no las distinguiría de una sola. Lo suprimido no se pierde: se
    cuenta y viaja en `lineas_suprimidas` del evento que sí se emitió.

    El ancla NO se mueve con cada línea suprimida. Una falla que siga emitiendo
    más allá de la ventana vuelve a alertar — la ventana calla la ráfaga, no el
    fenómeno.
    """
    cursor = estado.get("cursor")
    if not cursor:
        cursor = cursor_actual()
        estado["cursor"] = cursor
        if not cursor:
            return [], "journalctl no devolvió cursor de cola"
        return [], None  # la primera iteración sólo fija la línea base

    entradas, ultimo = leer_journal_nuevo(cursor)
    if ultimo:
        estado["cursor"] = ultimo

    anclas: dict = estado.setdefault("anclas", {})
    eventos: list[dict] = []
    emitido_por_clave: dict = {}
    ts_max = 0.0

    for entrada in entradas:
        hallazgo = clasificar_linea(_linea_de(entrada),
                                    entrada.get("_TRANSPORT"))
        if hallazgo is None:
            continue
        ts_entrada = float(entrada.get("__REALTIME_TIMESTAMP") or 0) / 1_000_000
        ts_max = max(ts_max, ts_entrada)
        clave = (hallazgo["tipo"], hallazgo["xid"], hallazgo["pid"])
        ancla = anclas.get(clave)
        if ancla is not None and 0 <= ts_entrada - ancla <= VENTANA_DEDUPE_S:
            if clave in emitido_por_clave:
                emitido_por_clave[clave]["lineas_suprimidas"] += 1
            continue
        anclas[clave] = ts_entrada
        evento = {"ts": _ahora(), "evento": "hardware_alerta",
                  "ts_journal": (datetime.fromtimestamp(ts_entrada, tz=timezone.utc)
                                 .isoformat() if ts_entrada else None),
                  **hallazgo, "lineas_suprimidas": 0}
        emitido_por_clave[clave] = evento
        eventos.append(evento)

    # Poda: sin esto, un pid distinto por incidente haría crecer el dict sin
    # techo en un proceso que vive semanas. Una clave más vieja que la ventana
    # ya no puede suprimir nada.
    if ts_max:
        for clave in [k for k, v in anclas.items()
                      if ts_max - v > VENTANA_DEDUPE_S]:
            del anclas[clave]
    return eventos, None


def _escribir(evento: dict) -> None:
    """`flush` + `fsync` en cada línea, y no es paranoia: el propósito entero
    del sampler es sobrevivir a una muerte dura de la máquina, y lo que quede
    en el page cache muere con ella. Son ~400 bytes cada 5 s."""
    JSONL_PATH.parent.mkdir(parents=True, exist_ok=True)
    with JSONL_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(evento, ensure_ascii=False) + "\n")
        f.flush()
        os.fsync(f.fileno())


def rotar_si_hace_falta() -> int | None:
    """Ring buffer de pobre, sin logrotate ni dependencias: al arrancar, si el
    jsonl pasa de MAX_LINEAS se deja sólo la cola. Devuelve cuántas líneas se
    recortaron, o None si no hizo falta.

    Los números: a 5 s por muestra son 17,280 líneas/día, así que 200,000
    líneas son ~11.6 días de historia. Se conserva la mitad para que el recorte
    no se repita en cada arranque.

    CORRECCIÓN 2026-09-25: este docstring decía "~75 MB a ~400 bytes por
    línea". Medido sobre el fichero real -- 138.3 MB en 150,040 líneas -- son
    **966 bytes por línea**, así que las 200,000 del anillo son **184 MB**, no
    75. El número estaba 2.4 veces por debajo y nadie lo habría notado: era una
    estimación escrita al lado del código, nunca contrastada con el fichero que
    el código produce.

    Y sigue habiendo un límite, que `rotar_en_caliente()` cubre: esta función
    se llama UNA vez, al arrancar el proceso.
    """
    if not JSONL_PATH.exists():
        return None
    lineas = JSONL_PATH.read_text(encoding="utf-8").splitlines()
    if len(lineas) <= MAX_LINEAS:
        return None
    conservadas = lineas[-LINEAS_A_CONSERVAR:]
    JSONL_PATH.write_text("\n".join(conservadas) + "\n", encoding="utf-8")
    return len(lineas) - len(conservadas)


def rotar_en_caliente() -> int | None:
    """El anillo, pero SIN esperar a que el proceso vuelva a arrancar.

    `rotar_si_hace_falta()` se llama una sola vez, en `main()`. Este servicio
    corre en bucle cada 5 s y sólo se reinicia con la máquina, así que entre que
    el fichero pasa del corte y el siguiente arranque no hay cota ninguna.
    Medido el 2026-09-25: 138.3 MB y 150 040 líneas, creciendo 15.9 MB al día.
    Con quince días en pie serían ~400 000 líneas y ~390 MB, y el recorte no
    llegaría hasta el siguiente reinicio.

    Se mira el TAMAÑO y no las líneas, que es la diferencia entera: contar
    líneas exige leer el fichero, y leer 138 MB cada hora para descubrir que no
    hay nada que hacer sería cambiar un problema por otro. Un `stat` cuesta lo
    mismo con 1 MB que con 400.

    Devuelve cuántas líneas se recortaron, o `None` si no hizo falta.
    """
    try:
        if JSONL_PATH.stat().st_size <= MAX_BYTES:
            return None
    except OSError:
        return None
    return rotar_si_hace_falta()


def _muestras_recientes(cuantas: int, ruta: Path | None = None) -> list[dict]:
    """Las últimas `cuantas` muestras del jsonl del sampler, de la más vieja a
    la más nueva. `[]` si no hay archivo, no hay nada legible, o no alcanzan --
    nunca una excepción: quien pregunta está decidiendo si frena trabajo, y un
    instrumento ausente no puede tumbar al que lo consulta.

    Rung 2 de la escalera (reuso): el sampler ya corre como servicio y ya
    escribe estas muestras cada 5 s con `gpu_power_w` y `gpu_util_pct` dentro.
    Leer su cola da historial Y carga por el precio de un `seek`, contra la
    alternativa de que cada llamador muestreara N veces por su cuenta --
    `ingest_batch` tardaría `DEBOUNCE_MUESTRAS * 5 s` en cada poll y arrancaría
    un `nvidia-smi` por muestra.

    `ruta` se resuelve AQUÍ ADENTRO y no como default del parámetro, por la
    misma razón que `mitigar()` documenta para `listar_pids`/`enviar_senal`: un
    default se liga una sola vez, al importar, y dejaría `JSONL_PATH` fuera del
    alcance de cualquier sustitución posterior.
    """
    ruta = ruta or JSONL_PATH
    if cuantas <= 0:
        return []
    try:
        with ruta.open("rb") as f:
            f.seek(0, os.SEEK_END)
            f.seek(max(0, f.tell() - COLA_BYTES))
            cola = f.read().decode("utf-8", errors="replace")
    except OSError:
        return []
    muestras = []
    for linea in cola.splitlines():
        # La PRIMERA línea puede venir partida a la mitad por el `seek`, y una
        # línea a medio escribir puede cerrar la cola: `json` rechaza las dos y
        # se descartan solas, sin caso especial que mantener.
        try:
            evento = json.loads(linea)
        except (json.JSONDecodeError, TypeError):
            continue
        if isinstance(evento, dict) and evento.get("evento") == "muestra":
            muestras.append(evento)
    return muestras[-cuantas:]


def _muestra_caliente(muestra: dict, umbrales: dict) -> bool:
    """¿Alguna zona de esta muestra del log está en/sobre su umbral?

    Mismo operador `>=` y los MISMOS `umbrales` que la lectura fresca de
    `presupuesto_termico`: si el debounce comparara el pasado contra otro
    criterio, no estaría corroborando el presente sino midiendo otra cosa.
    """
    for z in muestra.get("zonas") or []:
        umbral = (umbrales.get(z.get("zona")) or {}).get("umbral_c")
        if (umbral is not None and z.get("temp_c") is not None
                and z["temp_c"] >= umbral):
            return True
    return False


def _antiguedad_s(muestra: dict) -> float | None:
    """Segundos entre el sello de la muestra y ahora, o None si no hay sello
    legible -- que NO es lo mismo que cero, y por eso no se devuelve 0.0."""
    ts = muestra.get("ts")
    if not isinstance(ts, str):
        return None
    try:
        sello = datetime.fromisoformat(ts)
    except ValueError:
        return None
    if sello.tzinfo is None:
        sello = sello.replace(tzinfo=timezone.utc)
    return (datetime.now(timezone.utc) - sello).total_seconds()


def _pierna_de_carga(ventana: list[dict]) -> tuple[str, float | None]:
    """La pierna de CARGA de `_corroboracion`, aislada -- devuelve
    `(veredicto, pico_w)` con `con_carga` | `ocioso` | `sin_datos`.

    Existe para poder EXPONER esa pierna sin escribir una segunda lectura de
    la potencia (DGX-396 seguimiento, condición pegada al voto de Luis del
    2026-09-01). `_corroboracion` la llama y nadie más lee `gpu_power_w` para
    decidir: si mañana se re-mide `CARGA_MINIMA_W`, el gate y el campo del
    evento se mueven juntos porque el número lo compara UNA sola línea.

    `sin_datos` no es `ocioso`: un sampler que dejó de escribir `gpu_power_w`
    no dice que el GPU esté quieto, dice que no se sabe -- misma distinción que
    `_corroboracion` hace arriba, y por eso el pico sale `None` y no `0.0`.
    """
    vatios = [m["gpu_power_w"] for m in ventana
              if isinstance(m.get("gpu_power_w"), (int, float))]
    if not vatios:
        return ("sin_datos", None)
    pico = max(vatios)
    return (("con_carga" if pico >= CARGA_MINIMA_W else "ocioso"), pico)


def _corroboracion(historial: list[dict],
                   umbrales: dict) -> tuple[str, str, str, float | None]:
    """¿La telemetría reciente sostiene que el calor de AHORA es real?
    Devuelve `(veredicto, detalle, carga, pico_w)`, y el detalle viaja al
    motivo para que el log del watchdog diga por qué frenó o por qué no.

    Veredictos:
      `sin_datos`  -- no hay historial fresco suficiente para pronunciarse. El
                      llamador cae al criterio conservador de una muestra.
      `descarta`   -- hay datos y dicen que NO: el calor no se sostiene (ruido
                      del sensor) o el GPU está ocioso.
      `corrobora`  -- hay datos y sostienen el bloqueo.

    `sin_datos` y `descarta` son deliberadamente distintos: colapsarlos en un
    booleano haría que "el sampler está muerto" y "la máquina está fría" se
    leyeran igual, que es justo la confusión que DGX-383 vino a deshacer.

    `carga`/`pico_w` son la pierna de `_pierna_de_carga` SOLA, y salen aunque
    el veredicto ya se haya decidido por debounce. Ese es el punto: en el
    flanco de subida que emite `_alarmas` las muestras previas están bajo el
    umbral **por construcción**, así que la pierna de debounce corta primero y
    la de carga -- la única de las dos que sí es conocible ahí -- nunca llegaba
    a verse. Con el historial inválido (vacío, corto o viejo) valen
    `("sin_datos", None)`: leer los vatios de una ventana que ya se declaró no
    fresca sería afirmar sobre el presente con datos del pasado.

    El ORDEN de los veredictos no cambia por esto -- debounce antes que carga,
    y `sin_datos` por falta de `gpu_power_w` antes que `descarta` por ocioso --
    porque `presupuesto_termico` gatea con él y moverlo sería otra ficha.
    """
    previas = DEBOUNCE_MUESTRAS - 1
    # `DEBOUNCE_MUESTRAS <= 1` es "debounce apagado", y sin este corte la
    # rebanada `historial[-0:]` devolvería la lista ENTERA (no las 0 últimas) y
    # `ventana[-1]` reventaría con IndexError sobre un historial vacío. La
    # constante se toca cuando se re-mide -- su bloque de evidencia trae el
    # barrido-- así que el caso es alcanzable, y un IndexError dentro del gate
    # que decide si corre trabajo no es una falla aceptable.
    if previas <= 0:
        return ("sin_datos",
                (f"el debounce está apagado (DEBOUNCE_MUESTRAS={DEBOUNCE_MUESTRAS}"
                 "): no hay historial que corroborar"),
                "sin_datos", None)
    if len(historial) < previas:
        return ("sin_datos",
                (f"el sampler sólo dejó {len(historial)} de las {previas} "
                 "muestras previas que exige el debounce"),
                "sin_datos", None)
    ventana = historial[-previas:]

    edad = _antiguedad_s(ventana[-1])
    if edad is None:
        return ("sin_datos",
                "la muestra más reciente del sampler no trae sello legible",
                "sin_datos", None)
    if edad > MUESTRA_MAX_ANTIGUEDAD_S:
        return ("sin_datos",
                (f"la muestra más reciente del sampler tiene {edad:.0f}s "
                 f"(tope {MUESTRA_MAX_ANTIGUEDAD_S:.0f}s)"),
                "sin_datos", None)

    # La carga se resuelve ANTES de los cortes por debounce -- no para que
    # decida antes, sino para que se pueda informar aunque el debounce corte.
    carga, pico = _pierna_de_carga(ventana)

    frias = [m for m in ventana if not _muestra_caliente(m, umbrales)]
    if frias:
        return ("descarta",
                (f"{len(frias)} de las {previas} muestras previas están bajo "
                 "el umbral: pico aislado del sensor, no evento térmico"),
                carga, pico)

    if carga == "sin_datos":
        return ("sin_datos",
                ("ninguna de las muestras previas trae `gpu_power_w`, así que "
                 "no se puede afirmar que el GPU esté ocioso"),
                carga, pico)
    if carga == "ocioso":
        return ("descarta",
                (f"el GPU está ocioso ({pico:.1f} W de pico, compuerta "
                 f"{CARGA_MINIMA_W:.0f} W)"),
                carga, pico)
    return ("corrobora",
            f"sostenido {DEBOUNCE_MUESTRAS} muestras con el GPU a {pico:.1f} W",
            carga, pico)


def presupuesto_termico(zonas: list[dict], umbrales: dict, *,
                        historial: list[dict] | None = None) -> str:
    """Motivo por el que la temperatura ACTUAL debería bloquear trabajo nuevo,
    o "" si está sana. Público (sin `_`) porque DGX-342 lo consume desde otros
    módulos, no sólo desde este sampler.

    DGX-342: el quinto crash del día tuvo 6 cruces de esta misma alarma en los
    27 minutos previos, coincidiendo con el propio `liberation_watchdog`
    encadenando jobs de re-minado/reindexado sin pausa -- el drenador de la
    cola era la fuente de la carga sostenida que subió la temperatura, y nadie
    se lo preguntaba antes de tomar el job siguiente ni antes de ingerir la
    URL siguiente de un lote grande. Mismo umbral que `_alarmas` (94.8°C, 10°C
    bajo el trip de 104.8°C) -- dos números para "temperatura alta" en el
    mismo repo podrían desacordar.

    DGX-383: la lectura instantánea ya no basta para BLOQUEAR -- 57% de los
    episodios de alarma medidos ocurrían con el GPU ocioso. Sigue bastando
    para ABSOLVER: una zona bajo su umbral no necesita corroboración de nadie,
    y cortar ahí deja el camino sano sin tocar disco. Sobre una lectura
    caliente se le pregunta al historial del sampler si el calor se sostiene
    (`DEBOUNCE_MUESTRAS`) y si el GPU está consumiendo (`CARGA_MINIMA_W`).

    Recibe `zonas`/`umbrales` YA MEDIDOS -- quien mide es el llamador
    (`leer_zonas()`/`leer_umbrales()`), esta función sólo decide, para poder
    probarse sin tocar `/sys/class/thermal`. `historial` sigue esa misma
    doctrina un paso más: con `None` se lee solo del jsonl del sampler, así que
    los dos llamadores de DGX-342 mejoran su veredicto SIN cambiar su llamada,
    y un test puede fijar el pasado en vez de heredar la temperatura ambiente
    de la máquina donde corre la suite."""
    calientes = [z for z in zonas
                if z.get("temp_c") is not None
                and (umbrales.get(z["zona"]) or {}).get("umbral_c") is not None
                and z["temp_c"] >= umbrales[z["zona"]]["umbral_c"]]
    if not calientes:
        return ""
    peor = max(calientes, key=lambda z: z["temp_c"])
    umbral = umbrales[peor["zona"]]["umbral_c"]
    base = (f"{peor['zona']} a {peor['temp_c']}°C, sobre el umbral de "
            f"{umbral}°C (DGX-342)")

    if historial is None:
        historial = _muestras_recientes(DEBOUNCE_MUESTRAS - 1)
    # La pierna de carga no se usa aquí: este gate decide con el veredicto
    # completo, y las dos piernas ya están dentro de él.
    veredicto, detalle, _carga, _pico = _corroboracion(historial, umbrales)

    if veredicto == "descarta":
        return ""
    if veredicto == "sin_datos":
        return (f"{base}, pero {detalle} -- se bloquea con el criterio de una "
                "sola muestra (DGX-383: sin telemetría fresca el gate NO se "
                "relaja)")
    return (f"{base}, {detalle} -- se espera a que baje antes de sumar más "
            "carga")


def _alarmas(zonas: list[dict], umbrales: dict, estado: dict, *,
             historial: list[dict] | None = None) -> list[dict]:
    """Debounce por zona: el evento se emite en la TRANSICIÓN sano→crítico y
    en la de vuelta, nunca en cada muestra mientras siga arriba — mismo
    principio de "un boot limpio no genera ruido" del detector de crashes.

    DGX-396: `temp_critica` sale MARCADO con lo que el gate de DGX-383 diría
    de él en ese mismo instante, en dos campos nuevos:

      `corroboracion`          `corrobora` | `descarta` | `sin_datos`
      `corroboracion_detalle`  la prosa de `_corroboracion`, que nombra la
                               causa (cuántas previas frías, cuántos vatios de
                               pico, o por qué no hay datos)

    DGX-396 seguimiento (2026-09-01): dos campos más, con la pierna de CARGA
    sola -- lo que Luis votó al ver que la marca completa mide otra cosa en el
    flanco (el porqué está más abajo):

      `carga_gpu`         `con_carga` | `ocioso` | `sin_datos`
      `carga_gpu_pico_w`  el pico de `gpu_power_w` de la ventana, o `None`

    Los dos salen de `_pierna_de_carga` **a través del mismo
    `_corroboracion`**, no de una segunda lectura de la potencia: era la
    condición pegada al voto, porque un criterio nuevo suelto reabriría
    exactamente la divergencia que DGX-396 vino a cerrar. Mover
    `CARGA_MINIMA_W` mueve el gate y el campo a la vez.

    `carga_gpu_pico_w` va junto al veredicto y no en su lugar por una razón de
    archivo: el veredicto se calcula contra la `CARGA_MINIMA_W` **del día en
    que se escribió**, así que sin el número crudo un evento viejo dejaría de
    poder releerse si la constante se re-mide. Con él, se re-deriva.

    **El evento se emite SIEMPRE; la marca es un campo más, nunca una
    condición de emisión.** Es lo que Luis votó el 2026-09-01 y el argumento
    que lo decidió: el sampler es el registro CRUDO del sensor, y suprimir el
    pico impediría volver a estudiar el ruido — que es exactamente lo que
    permitió medir DGX-383. Un evento marcado admite las dos lecturas; uno
    suprimido admite una sola.

    **La marca no es un criterio nuevo: es `_corroboracion` misma** (rung 2 de
    la escalera). DGX-383 le puso debounce y compuerta de carga a
    `presupuesto_termico` y no tocó esta función, y el repo quedó con dos
    criterios de "temperatura alta" sobre el mismo sensor dando veredictos
    opuestos. Llamando a la misma función, si mañana se re-mide
    `DEBOUNCE_MUESTRAS` o `CARGA_MINIMA_W`, la marca se mueve sola con el gate
    y no pueden volver a divergir.

    **La ausencia de un campo NO significa «corroborado» ni «ocioso».** El
    esquema del jsonl es contrato: añadir un campo es seguro, renombrar o
    quitar no. Los `temp_critica` escritos antes de DGX-396 no traen ninguno
    de los cuatro, y los escritos entre DGX-396 y su seguimiento traen los dos
    primeros y no los dos de carga. `evento.get("corroboracion")` o
    `evento.get("carga_gpu")` devolviendo `None` significa **«este evento es
    anterior a ese campo, no se sabe»** — que no es ninguno de los tres
    veredictos, y en particular no es `corrobora` ni `con_carga`. `None` en
    `carga_gpu_pico_w` es ambiguo por sí solo (evento viejo, o ventana sin
    `gpu_power_w`) y **se desambigua con `carga_gpu`**, que distingue los dos
    casos: ausente el uno, `"sin_datos"` el otro.

    **Cómo se lee `descarta` AQUÍ, que NO es como se lee en
    `presupuesto_termico`.** Esta función emite en el FLANCO de subida, y en el
    flanco las muestras previas están por debajo del umbral por construcción
    (si estuvieran arriba la zona ya estaría en `en_alarma` y no habría
    evento). O sea que la pierna de debounce de `_corroboracion` casi siempre
    dirá que no, y su prosa hablará de "pico aislado". Medido sobre el log real
    (122 eventos, 2026-09-01): **3 `corrobora` contra 119 `descarta`**, y los
    3 lo son por un accidente entre zonas —el flanco de `thermal_zone4` cayó
    con `thermal_zone0` ya caliente—, no porque su propio calor se sostuviera.
    Aquí `descarta` se lee **«en este instante el gate todavía no bloquearía»**,
    nunca «esto fue ruido»: si el calor se sostiene, quien bloquea es
    `presupuesto_termico` en las muestras siguientes. Está en
    `docs/agent_findings/2026-09-01_marca_de_alarma_no_corroborada.md`.

    **Y por eso existe `carga_gpu`.** La pierna de debounce es falsa en el
    flanco por construcción; la de carga NO lo es -- los vatios del pasado
    inmediato son un hecho que el flanco no distorsiona. Medido sobre el
    mismo log: 34 eventos con el GPU ≥60 W contra 88 ociosos, o sea el 28% de
    señal que la mitigación de DGX-342 necesita leer y que la marca completa
    enterraba bajo su 97.5% de `descarta`. Los **10 de 12 precursores del
    quinto crash** que salen `descarta` (61 a 90 W, calor real) son
    exactamente el caso: `carga_gpu` los separa de los picos ociosos y
    `corroboracion` no puede.

    Quien mitigue lee `carga_gpu`; quien audite si el gate habría frenado lee
    `corroboracion`. Son preguntas distintas y por eso son campos distintos —
    colapsarlos volvería a perder una de las dos.

    `historial` sigue la doctrina de `presupuesto_termico`: con `None` se lee
    solo de la cola del jsonl, así que `muestrear()` no cambia su llamada, y un
    test puede fijar el pasado en vez de heredar la máquina donde corre la
    suite. La lectura es perezosa y se cachea en la variable: sólo toca disco
    si de verdad hay un flanco de subida, y una sola vez aunque crucen varias
    zonas en la misma muestra.
    """
    eventos = []
    en_alarma = estado.setdefault("en_alarma", set())
    inicio = estado.setdefault("inicio", {})
    for z in zonas:
        umbral = (umbrales.get(z["zona"]) or {}).get("umbral_c")
        if umbral is None or z["temp_c"] is None:
            continue
        nombre = z["zona"]
        base = {"ts": _ahora(), "zona": nombre, "type": z["type"],
                "temp_c": z["temp_c"], "umbral_c": umbral,
                "trip_c": umbrales[nombre]["trip_c"]}
        if z["temp_c"] >= umbral and nombre not in en_alarma:
            en_alarma.add(nombre)
            inicio[nombre] = time.monotonic()
            if historial is None:
                historial = _muestras_recientes(DEBOUNCE_MUESTRAS - 1)
            veredicto, detalle, carga, pico = _corroboracion(historial,
                                                             umbrales)
            eventos.append({**base, "evento": "temp_critica",
                            "corroboracion": veredicto,
                            "corroboracion_detalle": detalle,
                            "carga_gpu": carga,
                            "carga_gpu_pico_w": pico})
        elif z["temp_c"] < umbral - HISTERESIS_C and nombre in en_alarma:
            en_alarma.discard(nombre)
            arranco = inicio.pop(nombre, None)
            eventos.append({
                **base, "evento": "temp_normalizada",
                "segundos_en_alarma": (None if arranco is None
                                       else round(time.monotonic() - arranco, 1)),
            })
    return eventos


def _es_el_script_invocado(tokens: list[str], i: int) -> bool:
    """¿`tokens[i]` es el script que se está ejecutando, y no un argumento?

    Cierto si es `argv[0]` (invocación por shebang) o si hacia atrás sólo hay
    banderas hasta dar con un intérprete `python*`. Ver `argv_es_mitigable`,
    que es donde está el motivo medido.
    """
    if i == 0:
        return True
    for anterior in reversed(tokens[:i]):
        if os.path.basename(anterior).startswith("python"):
            return True
        if not anterior.startswith("-"):
            return False
    return False


def argv_es_mitigable(tokens: list[str],
                      patrones: tuple[str, ...] = PROCESOS_MITIGABLES) -> str | None:
    """El patrón de `patrones` que este argv satisface, o None.

    EL CRITERIO, y por qué no es el de `pgrep -f`. `pgrep -f` matchea contra la
    cmdline APLANADA, así que cualquier substring basta: un `less
    docs/agent_findings/algo_remine_harvest_lens.py.md` o un dictamen abierto en
    un editor cuentan como «el lote de re-minado está corriendo». Aquí no se
    mira la cmdline sino argv, token por token, y un token satisface un patrón
    sólo cuando sus ÚLTIMOS segmentos de ruta son EXACTAMENTE los del patrón:
    `tools/ingest.py` matchea `/home/lcasarin/projects/Atlas/tools/ingest.py`
    pero no un `ingest.py` de otro directorio, y `remine_harvest_lens.py` no
    matchea `algo_remine_harvest_lens.py.md`.

    POR QUÉ IGUALDAD DE SEGMENTO Y NO EL `startswith` DE `matches_heavy_job`
    (`tools/nightly_kb_consolidation.py`), que es el precedente del repo para
    esta misma pregunta: ahí los specs son PREFIJOS deliberados
    (`finetune_relevance_grader` tiene que alcanzar al `.py`), mientras que los
    tres de `PROCESOS_MITIGABLES` ya son nombres de archivo completos -- no les
    queda nada de lo que ser prefijo, y con `startswith` un `build_incremental.py.bak`
    o un `ingest.py.orig` entrarían a la lista de blancos de SIGSTOP. Lo que sí
    se reusa literal de aquel precedente es el descarte de tokens CON ESPACIOS:
    un `bash -c '<script>'` mete el script entero en un solo argv y ese blob
    nunca es una invocación real.

    LA SEGUNDA MITAD DEL CRITERIO: EL TOKEN TIENE QUE SER EL SCRIPT QUE SE
    INVOCÓ, no un argumento cualquiera. Sin esto, `grep -rn tools/ingest.py
    docs/` —un token EXACTAMENTE igual al patrón— entraba a la lista de blancos,
    y ese comando lo teclea cualquiera que esté investigando justo este bug. Se
    exige que el token sea `argv[0]` (un `./tools/ingest.py` por shebang) o que
    hacia atrás sólo haya banderas hasta llegar a un intérprete `python*`, que
    es la forma real de las tres invocaciones: `.venv/bin/python3 -u
    tools/ingest.py <url>`, con o sin `systemd-run --scope -p MemoryMax=8G`
    delante. Lo que este segundo filtro deja fuera son falsos NEGATIVOS que
    `pgrep -f` tampoco atrapaba (un `python -m tools.ingest` no existe hoy como
    forma de llamada), así que no se pierde cobertura frente a lo que había.

    Es pura a propósito -- separada del recorrido de /proc, igual que
    `matches_heavy_job` -- porque es la mitad que se puede interrogar sin
    procesos vivos.

    Sigue sin poder elegir `vllm`/`nemotron`, y por el mismo motivo que antes:
    no están en `PROCESOS_MITIGABLES`. Este cambio sólo ESTRECHA lo que matchea,
    así que esa garantía queda igual de intacta que con `pgrep -f`.
    """
    for i, token in enumerate(tokens):
        if any(c.isspace() for c in token) or not _es_el_script_invocado(tokens, i):
            continue
        segmentos = token.split("/")
        for patron in patrones:
            objetivo = patron.split("/")
            if segmentos[-len(objetivo):] == objetivo:
                return patron
    return None


def pids_mitigables(patrones: tuple[str, ...] = PROCESOS_MITIGABLES) -> list[int]:
    """PIDs vivos cuyo argv satisface alguno de `patrones` (ver
    `argv_es_mitigable`). Son los blancos del SIGSTOP de `mitigar()`, así que un
    falso positivo aquí no reporta mal: congela un proceso real.

    NUNCA se elige a sí mismo ni a su padre -- se excluyen por PID antes de leer
    nada, que es la misma guarda de `running_heavy_jobs()`. El self-match es el
    bug original de `pgrep -f`: el patrón viaja en la propia cmdline del que
    pregunta.

    Un proceso que muere entre el listado y la lectura no revienta nada:
    `_argv_tokens` devuelve lista vacía ante el OSError.
    """
    propios = {str(os.getpid()), str(os.getppid())}
    pids: list[int] = []
    for entrada in PROC_DIR.iterdir():
        if not entrada.name.isdigit() or entrada.name in propios:
            continue
        if argv_es_mitigable(_argv_tokens(entrada.name), patrones):
            pids.append(int(entrada.name))
    return sorted(pids)


def mitigar(eventos: list[dict], estado: dict, *,
           listar_pids=None, enviar_senal=None) -> list[dict]:
    """DGX-342: `temp_critica` hasta ahora sólo se logueaba -- el quinto crash
    del día tuvo 6 cruces en 27 min y murió 8s después del último. Pausa
    (SIGSTOP) los procesos de `PROCESOS_MITIGABLES` mientras haya una zona en
    alarma **con carga real en el GPU**, y los reanuda (SIGCONT) sólo cuando
    TODAS se normalizaron -- nunca toca vLLM ni nada fuera de esa lista corta
    y con nombre.

    DGX-408 (2026-09-01): la condición de disparo dejó de ser el evento crudo.
    Antes bastaba `hay_critica`, y la alarma cruda es **ruido 3 de cada 4
    veces** (72% del log; 34 de 34 en el arranque anterior). Ya hay observación
    en vivo del daño: 90 s después del reinicio de las 18:41:52 el primer cruce
    salió `descarta / ocioso / 14.11 W de pico` a 95.2 °C declarados -- un pico
    de sensor con el GPU casi apagado-- y esta función lo habría atendido. No
    se mandó ningún SIGSTOP en toda su vida sólo porque nunca coincidió un
    blanco vivo; con un `remine_harvest_lens.py` corriendo, lo habría parado
    por ruido. Desde aquí la compuerta es `carga_gpu == "con_carga"`, el campo
    que `_alarmas` escribe en cada `temp_critica` desde DGX-396.

    **La ausencia del campo NO se lee como permiso ni como veto silencioso.**
    `e.get("carga_gpu")` devuelve `None` en un evento anterior a DGX-396, y
    `"sin_datos"` cuando el sampler no dejó `gpu_power_w` fresco. En ambos
    casos la condición no se cumple, así que una compuerta muda dejaría la
    mitigación **desactivada pareciendo arreglada**: cero `mitigacion_pausa`,
    idéntico al cero de "filtró bien". Por eso esos dos casos emiten su propio
    evento `mitigacion_sin_datos` con la zona y el motivo -- el síntoma de
    "funciona" y el de "no corre" no pueden ser el mismo cero (política de
    reporte de la casa: un instrumento sin capturas es defecto del instrumento,
    nunca evidencia de que el sujeto esté limpio).

    **Límite declarado de la compuerta, no escondido.** Los 2 precursores del
    cruce de las 02:59:27 del quinto crash de DGX-342 tienen el GPU a **40.0 W**,
    por debajo de `CARGA_MINIMA_W = 60.0`: salen `ocioso` y **no pausarían**,
    aunque precedieron al mismo crash que los otros diez (que sí salen
    `con_carga`, de 61.5 a 90.2 W). No es un bug de esta función -- es dónde
    quedó puesta la compuerta, medida en
    `docs/agent_findings/2026-09-01_pierna_de_carga_en_el_flanco.md`.
    `carga_gpu_pico_w` viaja en el evento precisamente para poder re-mirar esos
    dos si `CARGA_MINIMA_W` se re-mide.

    `listar_pids`/`enviar_senal` se resuelven AQUÍ ADENTRO y no como default
    del parámetro: un default `=pids_mitigables`/`=os.kill` se liga una sola
    vez al definir la función, y un `monkeypatch.setattr(agt, "pids_mitigables",
    ...)` posterior nunca lo alcanzaría -- éste es exactamente el llamador sin
    override que usa `muestrear()`, así que sin esto la mitigación real quedaría
    imposible de probar de punta a punta.

    Idempotente por diseño: `estado['mitigados']` es el conjunto de PIDs que
    ESTA función ya pausó, así que una segunda muestra en alarma no manda un
    SIGSTOP repetido (inofensivo en sí, pero ensuciaría el jsonl con un evento
    por muestra en vez de uno por transición, rompiendo el mismo principio de
    debounce que ya tiene `_alarmas`)."""
    listar_pids = listar_pids or pids_mitigables
    enviar_senal = enviar_senal or os.kill
    mitigados: set[int] = estado.setdefault("mitigados", set())
    criticas = [e for e in eventos if e.get("evento") == "temp_critica"]
    con_carga = [e for e in criticas if e.get("carga_gpu") == "con_carga"]
    # `None` (evento anterior a DGX-396) y `"sin_datos"` (sampler sin
    # `gpu_power_w` fresco) son las dos formas de "no se sabe". `"ocioso"` NO
    # está aquí: ése es un veredicto, y su silencio es la compuerta haciendo
    # su trabajo.
    opacas = [e for e in criticas
              if e.get("carga_gpu") in (None, "sin_datos")]
    resultado: list[dict] = []

    if con_carga and not mitigados:
        objetivo = sorted(listar_pids())
        pausados: list[int] = []
        for pid in objetivo:
            try:
                enviar_senal(pid, signal.SIGSTOP)
                pausados.append(pid)
            except ProcessLookupError:
                continue  # murió entre el listado y el kill -- no es un pid que pausar
        if pausados:
            mitigados.update(pausados)
            resultado.append({"ts": _ahora(), "evento": "mitigacion_pausa",
                              "pids": pausados, "patrones": list(PROCESOS_MITIGABLES)})

    elif mitigados and not estado.get("en_alarma"):
        reanudados: list[int] = []
        for pid in sorted(mitigados):
            try:
                enviar_senal(pid, signal.SIGCONT)
                reanudados.append(pid)
            except ProcessLookupError:
                continue  # murió mientras estaba pausado -- nada que reanudar
        mitigados.clear()
        resultado.append({"ts": _ahora(), "evento": "mitigacion_reanuda",
                          "pids": reanudados})

    # Se emite AUNQUE otra zona sí haya pausado: lo que registra es que ESA
    # alarma quedó sin clasificar, no el desenlace global de la muestra. Y va
    # después de la pausa para que el jsonl lea primero la acción y luego los
    # huecos.
    for evento in opacas:
        resultado.append({
            "ts": _ahora(), "evento": "mitigacion_sin_datos",
            "zona": evento.get("zona"), "carga_gpu": evento.get("carga_gpu"),
            "motivo": ("el evento de alarma no trae `carga_gpu` (anterior a "
                       "DGX-396): la compuerta de carga no puede decidir y no "
                       "se pausó"
                       if evento.get("carga_gpu") is None else
                       "`carga_gpu` es `sin_datos`: el sampler no dejó "
                       "`gpu_power_w` fresco, la compuerta no puede decidir y "
                       "no se pausó"),
        })

    return resultado


def muestrear(umbrales: dict, estado: dict, *, escribir: bool = True) -> list[dict]:
    """Una iteración: la muestra siempre, más las alarmas que hayan cambiado
    de estado, más la mitigación si corresponde. Devuelve todo lo emitido
    para que los tests lo inspeccionen."""
    zonas = leer_zonas()
    muestra = {"ts": _ahora(), "evento": "muestra", **leer_gpu(),
               **leer_memoria_sistema(), **leer_vllm_metrics(), "zonas": zonas}
    # Los procesos de GPU cuestan una invocación extra de nvidia-smi: 1 de
    # cada PROCESOS_GPU_CADA muestras, no todas.
    ciclo = estado.get("ciclo_procs_gpu", 0)
    if ciclo % PROCESOS_GPU_CADA == 0:
        muestra.update(leer_procesos_gpu())
    estado["ciclo_procs_gpu"] = ciclo + 1
    if not zonas:
        muestra["zonas_ausentes"] = f"sin zonas térmicas en {THERMAL_DIR}"
    alertas, journal_ausente = vigilar_journal(estado)
    if journal_ausente:
        muestra["journal_ausente"] = journal_ausente
    alarmas = _alarmas(zonas, umbrales, estado)
    eventos = [muestra, *alarmas, *alertas, *mitigar(alarmas, estado)]
    if escribir:
        for evento in eventos:
            _escribir(evento)
    return eventos


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--interval-seconds", type=float, default=INTERVALO_DEFAULT_S,
                    help="segundos entre muestras (default: %(default)s)")
    ap.add_argument("--once", action="store_true",
                    help="una sola muestra y salir, sin loop")
    ap.add_argument("--dry-run", action="store_true",
                    help="imprime los eventos, no escribe el jsonl")
    ap.add_argument("--procesos-gpu", action="store_true",
                    help=("imprime quien tiene memoria de GPU ahora mismo, en "
                          "JSON. Es el HECHO fisico; la politica de quien puede "
                          "usarla es de quien encola trabajo (DGX-585)."))
    ap.add_argument("--gate-termico", action="store_true",
                    help=("imprime {bloquea, motivo} y sale 1 si NO se le debe "
                          "sumar carga a la maquina. Es la via por la que Atlas "
                          "consulta esta decision sin importar codigo de aqui "
                          "(contrato de los dos repos, DGX-585)."))
    args = ap.parse_args()

    if args.procesos_gpu:
        # El HECHO fisico -- quien tiene memoria de GPU ahora mismo -- separado
        # de la POLITICA, que es de quien encola trabajo. Atlas preguntaba esto
        # invocando `nvidia-smi` por su cuenta; con la frontera de DGX-585 el
        # driver lo interroga quien gobierna el hardware, y Atlas decide con la
        # respuesta. Sale 1 si NO se pudo averiguar: quien no sabe, no pasa.
        datos = leer_procesos_gpu()
        print(json.dumps(datos, ensure_ascii=False))
        return 1 if datos.get("gpu_procs") is None else 0

    if args.gate_termico:
        # Una sola fuente para el 94.8 C. Atlas llamaba a `presupuesto_termico`
        # por import; ahora llama a este proceso. El numero no se copia, y la
        # ausencia de telemetria fresca sigue BLOQUEANDO (DGX-383): quien no
        # sabe, no pasa.
        umbrales = leer_umbrales()
        motivo = presupuesto_termico(leer_zonas(), umbrales)
        print(json.dumps({"bloquea": bool(motivo), "motivo": motivo},
                         ensure_ascii=False))
        return 1 if motivo else 0

    escribir = not args.dry_run
    recortadas = rotar_si_hace_falta() if escribir else None
    umbrales = leer_umbrales()
    estado: dict = {"en_alarma": set(), "inicio": {},
                    "cursor": None, "anclas": {}}

    arranque = {"ts": _ahora(), "evento": "arranque",
                "intervalo_s": args.interval_seconds,
                "margen_trip_c": MARGEN_TRIP_C, "histeresis_c": HISTERESIS_C,
                "ventana_dedupe_s": VENTANA_DEDUPE_S,
                "tipos_vigilados": [t for t, _, _ in PATRONES_VIDEO],
                "lineas_recortadas": recortadas, "umbrales": umbrales}
    if not umbrales:
        arranque["zonas_ausentes"] = f"sin zonas térmicas en {THERMAL_DIR}"
    if escribir:
        _escribir(arranque)
    else:
        print(json.dumps(arranque, ensure_ascii=False))

    try:
        desde_revision = 0
        while True:
            eventos = muestrear(umbrales, estado, escribir=escribir)
            # El anillo, también en caliente. Sin esto el recorte sólo ocurre al
            # arrancar el proceso, que en este servicio significa "al reiniciar
            # la máquina": el hueco que abre DEBT-TELEMETRIA-GPU-SIN-COTA-EN-CALIENTE.
            desde_revision += 1
            if escribir and desde_revision >= MUESTRAS_ENTRE_REVISIONES:
                desde_revision = 0
                recortadas_ahora = rotar_en_caliente()
                if recortadas_ahora:
                    _escribir({"ts": _ahora(), "evento": "rotacion",
                               "lineas_recortadas": recortadas_ahora,
                               "motivo": f"jsonl por encima de {MAX_BYTES} bytes"})
            if args.dry_run or args.once:
                for evento in eventos:
                    print(json.dumps(evento, ensure_ascii=False))
            if args.once:
                return 0
            time.sleep(args.interval_seconds)  # blocking-sleep: intervalo del sampler de vida larga, no I/O a esperar -- DGX-334  # sunset-reviewed: 1.5 -- SE QUEDA, y sigue siendo el caso mas claro: es el intervalo de un sampler de vida larga. No espera a nadie, decide cada cuanto mirar. Sustituirlo por un evento seria pedirle a la maquina que avise de que ha pasado el tiempo.
    except KeyboardInterrupt:
        return 0


if __name__ == "__main__":  # pragma: no cover -- entry point, ejercitado via main()
    sys.exit(main())
