#!/usr/bin/env python3
"""Calibracion de los cortes de PSI de `bb scan` contra los incidentes propios
de esta maquina (DEBT-PSI-UMBRALES-SIN-CALIBRAR, satd_family BLIND_INSTRUMENT).

Existe para que los cortes se puedan RE-DERIVAR cuando lleguen mas incidentes,
en vez de quedar congelados en un comentario. Una calibracion cuya evidencia
solo vive en un mensaje de commit es el mismo instrumento ciego que esta ficha
vino a cerrar, un nivel mas arriba: nadie puede comprobar que sigue siendo
cierta.

Lo que mide, y por que asi:

  El NIVEL instantaneo de mem_full no discrimina. Medido sobre 19804 muestras
  (2026-09-08 -> 2026-09-23): seis excursiones llegaron hasta 98.53 % sin que
  la maquina se colgara, y el valor mas bajo que sostuvo un congelamiento real
  fue 48.80 %. Un corte por nivel se equivoca en las dos direcciones.

  La TASA de subida tampoco discrimina. Las dos mayores subidas de todo el
  corpus en <= 90 s (+76.30 y +68.96 puntos) son de dias SANOS; el arranque del
  congelamiento del 05:45 fue la tercera (+65.60). Un corte por tasa dispara
  dos veces en falso antes de acertar una.

  Lo que discrimina es la DURACION de la excursion. Las seis excursiones sanas
  duraron <= 2 min sobre el 10 % y se recuperaron solas; los dos congelamientos
  duraron 1042 y 292 min y solo salieron con reset duro. La separacion es de
  dos ordenes de magnitud.

Corre el control negativo, no lo argumenta: `--sostenido 0` afloja el corte
hasta que las excursiones sanas entran, el veredicto se vuelve FALSO POSITIVO y
esto sale 1. Un gate que no puede salir en rojo no es un gate.
"""

import argparse
import datetime as dt
import json
import subprocess
import sys
from pathlib import Path

# Corte de nivel. 10 % esta 4.9x por debajo del valor mas bajo que sostuvo un
# congelamiento (48.80 %, 2026-09-22 16:12) y es el punto donde la excursion
# sana mas larga se encoge a 2 min (a 5 % dura 3 min, a 1 % dura 5 min).
UMBRAL_PCT = 10.0
# Corte de duracion. 2.5x por encima de la excursion sana mas larga (2 min) y
# 58x por debajo del congelamiento mas corto (292 min).
SOSTENIDO_MIN = 5.0
# Techo de lo observado como benigno. Entre 3 y 5 min no hay NI UNA muestra en
# 15 dias: esa banda se declara sin observar en vez de asignarse a un lado.
PICO_MAX_MIN = 3.0

MUESTRAS = Path.home() / ".local/share/blackbox/samples"

# El journal de `bb-usable`, el detector REAL (lee /proc/pressure/memory cada 30 s y aplica este mismo corte: avg10
# >= 10 sostenido 300 s). Se consulta SOLO para las ventanas de incidente sin ninguna muestra de bin/bb dentro: ahi el
# muestreador se quedo ciego durante el stall y sin esta segunda fuente el instrumento no puede validar el corte
# contra los incidentes que mas importan (2026-10-11 22:02, DEBT-CALIBRA-PSI-CORTE-INVALIDO-INCIDENTE-11-OCT-22-02-NO-
# DETECTADO-01). `-u` trae tambien las lineas de systemd sobre la unidad (el watchdog que reinicia). Sin `-q`, para
# que el aviso de journal inaccesible por permisos llegue a stderr y se lea como COULD_NOT_RUN, no como silencio.
JOURNAL_CMD = ["journalctl", "-u", "bb-usable.service", "-o", "short-iso", "--no-pager"]
# WatchdogSec de systemd/bb-usable.service ("limit 6min" en el journal): el reinicio llega hasta 6 min despues de que
# bb-usable deja de acariciar el watchdog, asi que la consulta se alarga eso mas alla del fin de la ventana.
WATCHDOG_S = 360

# Los dos congelamientos del 2026-09-22/23, ambos terminados en reset duro.
# Son la verdad etiquetada de esta calibracion. No salen de PSI -- eso seria
# circular: salen de que la maquina no respondia y hubo que resetearla, y estan
# corroborados por sar (instrumento independiente): ldavg-1 sostenido entre 100
# y 185 durante las dos ventanas enteras, con kbavail entre 32 y 47 GB LIBRES.
INCIDENTES = [
    ("2026-09-22 05:45", "2026-09-22 23:30"),
    ("2026-09-22 23:49", "2026-09-23 05:44"),
    # Tercero, 2026-09-24. Mismo origen que los dos de arriba: la maquina dejo
    # de responder y hubo que resetearla a mano. Corroborado por sar, que es
    # instrumento independiente de PSI: %system entre 99.42 y 99.54 durante la
    # ventana entera con %user en 0.13, swap al 100 % desde las 00:24, ldavg-1
    # entre 103 y 110, y 3211 procesos frente a los ~490 de una maquina sana.
    # kbavail entre 38 y 47 GB LIBRES, igual que en los dos anteriores: no fue
    # agotamiento de RAM.
    #
    # El inicio sale de las muestras de bin/bb, que esta vez si grabaron el
    # arranque: 00:00:02 mem_full 0.0 -> 00:02:03 mem_full 19.28 con la memoria
    # disponible cayendo de 47.5 GB a 3.8 GB y los procesos con GPU pasando de
    # 2 a 23 en ese minuto, 22 de ellos en app-com.anthropic.Claude-130715.scope.
    # El fin es el reset: el boot anterior termina a las 05:56:45.
    ("2026-09-24 00:02", "2026-09-24 05:56"),
    # CUARTO, 2026-09-26. Distinto de los tres de arriba en el desenlace y por eso
    # merece decirse: este NO termino en reset por el operador, termino en KERNEL
    # PANIC -- `hung_task: blocked tasks` a las 15:38:26, con ~20 tareas `python`
    # de PIDs contiguos bloqueadas mas de 123 s. La maquina se reinicio sola a las
    # 15:42:17 (`last reboot`), asi que costo 4 minutos en vez de una noche.
    #
    # Es un incidente y no una excursion sana, y eso no se deduce de PSI -- eso
    # seria circular: se deduce de que el kernel declaro que no podia seguir.
    # Corroborado por sar, instrumento independiente de PSI: mem avail 24-29 %
    # con swap al 40 % libre durante la ventana entera, o sea que NO fue
    # agotamiento de RAM, igual que en los tres anteriores.
    #
    # El inicio sale de las muestras: 15:22:02 mem_full 40.48, la primera sobre el
    # umbral. El fin es el arranque nuevo. Esta ventana es CORTA (20 min) frente a
    # las de arriba porque el panico corto el episodio; sin hung_task_panic=1 este
    # habria sido el cuarto congelamiento de horas.
    #
    # Anadido el 2026-09-27, y lo pidio el propio modulo: sin esta ventana daba
    # `falsos positivos: 1` y VEREDICTO CORTE INVALIDO, porque leia un colapso
    # real de 13 min como una excursion sana que el corte dispara.
    ("2026-09-26 15:20", "2026-09-26 15:42"),
    # QUINTO y SEXTO, 2026-09-28, el mismo dia y con el mismo origen: un solo
    # proceso `python3` bajo un scope de Claude Desktop creciendo sin freno
    # hasta 30+ GiB de RSS (ver DEBT-PROCESO-SIN-TECHO-TUMBO-LA-MAQUINA-DOS-VECES).
    # GPU y vLLM descartados con medida: atom_gpu_telemetry.jsonl da
    # gpu_util_pct=0.0 en las dos ventanas enteras, en reposo de GPU.
    #
    # QUINTO. Corroborado por sar: kbavail cae de 52.2 GB (03:25) a 29.7 GB
    # (03:29) y se queda ahi, %commit sube de 41.5 a 58.6 -- no fue
    # agotamiento de RAM, el mismo patron de los cuatro anteriores. El inicio
    # sale de las muestras de bin/bb: 03:28:28 es la primera con mem_full
    # >= 10 (35.66). El fin es el reset: `bb-usable` declaro COLAPSO sostenido
    # a las 03:34:51 y el watchdog de systemd forzo el reinicio a las 03:39:21
    # (`journalctl --list-boots`).
    #
    # LIMITE DECLARADO, y es nuevo: `bb sample` DEJA DE ESCRIBIR muestras a las
    # 03:29:02 (su ultima linea real es un burst_fin, no la muestra con datos
    # de las 03:28:58 que cierra la rafaga) -- de ahi al reinicio no hay ni
    # una sola linea mas en samples/2026-09-28.jsonl. Por eso el clasificador de
    # ESTE modulo (que solo lee ese fichero) NO corrobora esta ventana como
    # COLAPSO por su cuenta -- `calibra()` la marca `no_detectados`, y es
    # correcto que lo haga: es la verdad sobre el propio instrumento, no un
    # error de esta lista. El incidente SI esta corroborado, por TRES fuentes
    # independientes de bb sample: sar (kbavail 52.2 -> 29.7 GB), el journal de
    # `bb-usable` (que lee PSI directo de /proc/pressure/memory, no de este
    # fichero, y vio el colapso entero), y `journalctl --list-boots` (el
    # reinicio en si). Por que `bb sample` se quedo callado justo ahi no esta
    # investigado aqui -- es su propio hallazgo, no el de este modulo.
    ("2026-09-28 03:28", "2026-09-28 03:39"),
    # SEXTO, en el arranque SIGUIENTE, 46 minutos despues -- la memoria nunca
    # se recupero del quinto (kbavail se quedo en ~29 GB en vez de volver a
    # los ~65 GB de antes). Corroborado por sar: kbavail 32.1 GB (04:16) baja
    # y se estabiliza en ~29 GB, %commit sube de 48.0 a 54.8. El inicio sale
    # de las muestras: 04:18:04 es la primera con mem_full >= 10 (25.95). El
    # fin es el reset: COLAPSO sostenido declarado a las 04:21:58, watchdog
    # fuerza el reinicio a las 04:27:29.
    #
    # Anadidas el 2026-09-28 porque `test_el_gate_sale_0_sobre_el_corpus_real`
    # las leia como excursion sana sin estas ventanas: la muestra de las
    # 04:24:02, DENTRO del sexto incidente, salia FALSO POSITIVO.
    ("2026-09-28 04:18", "2026-09-28 04:27"),
    # SEPTIMO, 2026-10-05 (voto de Luis 2026-10-14, DEBT-SKIP-TEST-CONTROL-RACHA-118). Estaba
    # sin etiquetar y el control lo leia como "sano con 479 s de PSI alto". No sale de PSI:
    # `last -x` muestra la sesion grafica caida ("crash") y un arranque nuevo a las 00:31:49,
    # y sar (sa20261005) mide ldavg-1 entre 20 y 70 con 2600-5900 procesos contra 1.31 y ~1900
    # a las 23:31 -- el mismo desenlace que los anteriores, ventana de la ficha del colapso.
    ("2026-10-05 00:00", "2026-10-05 00:31"),
    # OCTAVO y NOVENO, 2026-10-11, dos arranques seguidos y el mismo mecanismo:
    # enjambre de suites pytest/pre-push sin techo de memoria dentro de
    # `app.slice` (DEBT-COLAPSOS-11-OCT-SUITES-PYTEST-SIN-TECHO-01, que atribuye
    # el origen por las transcripciones de las sesiones; etiquetarlos aqui era el
    # pendiente que dejo DEBT-REAUDITAR-LEDGER-H1-TRAS-FUSIONES-01).
    #
    # Son incidentes y no excursiones sanas, y eso no se deduce de PSI: los dos
    # arranques terminan sin cierre limpio. `journalctl -b` cierra cada uno con
    # `bb-usable.service: Watchdog timeout (limit 6min)!` -> `Failed with result
    # 'watchdog'` -> `Rebooting.`, `last -x` no registra `shutdown` para ninguno
    # de los dos, y el arranque siguiente de cada uno trae `BERT: Error records
    # from previous boot`. Corroboracion independiente de PSI: la memoria
    # disponible no se agoto -- atom_gpu_telemetry.jsonl da mem_avail_mb 22053
    # a 31617 en el septimo y 29589 a 30648 en el octavo. sar NO corrobora estas
    # dos: `sar -r -f /var/log/sysstat/sa20261011` deja de leer a las 12:12:00
    # (el reset del arranque anterior), aunque el fichero se siguio escribiendo
    # hasta las 23:59.
    #
    # SEPTIMO, arranque 5461291a. El fin es el reset: watchdog a las 22:12:33,
    # `Rebooting.` a las 22:12:46 (`journalctl --list-boots`; el arranque nuevo
    # es el de las 22:14:47). LIMITE DECLARADO, el mismo del quinto: ninguna
    # muestra de bin/bb esta sobre el umbral. `bb sample` deja de escribir a las
    # 22:00:34 (mem_full 3.34; maximo de la ventana 7.17 a las 22:00:00) y la
    # telemetria de GPU a las 22:01:43 (psi_mem_full_avg10 1.72). Por eso el
    # inicio sale del journal de `bb-usable`, que lee /proc/pressure/memory
    # directo: 22:02:07 es su primera lectura >= 10 (avg10=42.6, racha 1/10), y
    # declara COLAPSO sostenido desde las 22:07:07 (98.0, 300 s). Medido el
    # 2026-10-16: CERO muestras de bin/bb dentro de [22:02, 22:12]. Hasta esa
    # fecha `calibra()` la marcaba `no_detectados`, que afirmaba que el corte la
    # dejo pasar sobre muestras que no existen. Marcarla solo
    # `sin_muestras_en_ventana` dejaba el instrumento sin validar el corte contra
    # el incidente que mas importa; desde entonces `main()` la OBSERVA por el
    # journal de bb-usable (`lee_journal`/`observa_journal`): declara COLAPSO a
    # las 22:07:07 y el watchdog reinicia a las 22:12:33.
    ("2026-10-11 22:02", "2026-10-11 22:12"),
    # OCTAVO, arranque 7b217d8b, en el arranque SIGUIENTE al septimo. El inicio
    # sale de las muestras de bin/bb: 22:44:20 es la primera con mem_full >= 10
    # (16.54; 22:44:16 daba 9.17), maximo 72.47 a las 22:46:43, ultima muestra a
    # las 22:51:50 (59.52). `bb-usable` declara COLAPSO sostenido hasta las
    # 22:54:12 (55.3, 600 s). El fin es el reset: watchdog a las 22:54:40,
    # `Rebooting.` a las 22:54:41 (arranque nuevo a las 22:56:42).
    #
    # Anadidas el 2026-10-13: sin esta ventana el modulo daba la excursion de
    # las 22:44 (8 min, max 72.47 %) como FALSO POSITIVO, leyendo un colapso
    # real como excursion sana.
    ("2026-10-11 22:44", "2026-10-11 22:54"),
]


# FALSOS POSITIVOS CONOCIDOS -- anadido el 2026-10-16 en tools/control_racha.py y movido aqui el mismo dia para que
# haya UNA sola fuente (control_racha la importa). Una ventana donde la regla REINICIO la maquina y el control, con
# datos reales, dice que no hubo un incidente que lo justificara. NO es un incidente: no entra en `INCIDENTES` ni
# afirma que el reinicio estuviera justificado. `calibra()` la saca de `falsos_positivos` y la devuelve en
# `falsos_positivos_conocidos`, que `informe()` IMPRIME como deuda con su ficha. Cada una nombra su ficha ABIERTA;
# `tests/test_control_racha.py` falla en cuanto esa ficha sale de `tasks/backlog/` (voto de Luis, 2026-10-16:
# excepcion con fecha de caducidad atada a la ficha, no supresion).
FALSOS_POSITIVOS_CONOCIDOS = [
    {"ventana": ("2026-10-16 10:37", "2026-10-16 10:55"),
     "ficha": "DEBT-COLAPSO-CONFINADO-A-APP-SLICE-REINICIA-LA-MAQUINA-ENTERA-01",
     "motivo": "17 min de PSI full 45-57 confinado a app.slice (docker.slice y system.slice en 0.0, MemAvailable 20-24 GB); "
               "el watchdog reinicio la maquina con el motor sano"},
    {"ventana": ("2026-10-16 13:44", "2026-10-16 13:52"),
     "ficha": "DEBT-COLAPSO-CONFINADO-A-APP-SLICE-REINICIA-LA-MAQUINA-ENTERA-01",
     "motivo": "5 min de PSI full 57-69 confinado a app.slice (docker.slice y system.slice en 0.0) con el slice pegado a su memory.high de "
               "38G; bb-usable declaro COLAPSO (racha 17/10) y se corto a ~30 s de reiniciar la maquina con el motor sano"},
]


def ventanas_exentas(conocidos=None) -> list[tuple[dt.datetime, dt.datetime]]:
    return [(dt.datetime.strptime(f["ventana"][0], "%Y-%m-%d %H:%M"),
             dt.datetime.strptime(f["ventana"][1], "%Y-%m-%d %H:%M"))
            for f in (FALSOS_POSITIVOS_CONOCIDOS if conocidos is None else conocidos)]


def _naive(t: dt.datetime) -> dt.datetime:
    """Sin tz: las ventanas de incidente se escribieron en hora local, que es la
    misma en la que muestrea bin/bb. Comparar aware contra naive lanza."""
    return t.replace(tzinfo=None)


def carga(directorio: Path) -> list[tuple[dt.datetime, float]]:
    """-> [(ts, mem_full)] ordenado. Ignora lineas sin psi o sin ts parseable:
    el corpus es de produccion y una linea truncada por un corte de luz no debe
    tumbar la calibracion."""
    serie = []
    for fichero in sorted(directorio.glob("*.jsonl")):
        for linea in fichero.read_text(encoding="utf-8", errors="replace").splitlines():
            try:
                d = json.loads(linea)
            except ValueError:
                continue
            psi = d.get("psi")
            if not isinstance(psi, dict):
                continue
            try:
                t = dt.datetime.strptime(d.get("ts", ""), "%Y-%m-%dT%H:%M:%S%z")
            except ValueError:
                continue
            serie.append((_naive(t), float(psi.get("mem_full", 0) or 0)))
    serie.sort(key=lambda r: r[0])
    return serie


def excursiones(serie, umbral=UMBRAL_PCT):
    """Rachas maximas de muestras consecutivas con mem_full >= umbral."""
    fuera, actual = [], []
    for muestra in serie:
        if muestra[1] >= umbral:
            actual.append(muestra)
        elif actual:
            fuera.append(actual)
            actual = []
    if actual:
        fuera.append(actual)
    return fuera


def duracion_min(exc) -> float:
    """Minutos entre la primera y la ultima muestra de la excursion.

    Es una COTA INFERIOR de la excursion real, nunca una superior: durante un
    congelamiento el propio muestreador se queda sin CPU y sus intervalos pasan
    de 1 min a 17-66 min, asi que los bordes caen donde alcanzo a correr."""
    return (exc[-1][0] - exc[0][0]).total_seconds() / 60.0


def clasifica(dur: float, pico_max=PICO_MAX_MIN, sostenido=SOSTENIDO_MIN) -> str:
    """COLAPSO se comprueba PRIMERO, y eso es carga util, no estilo. Con la
    banda de PICO delante, aflojar `sostenido` por debajo de `pico_max` no
    cambiaba ni una clasificacion: `--sostenido 0` salia CALIBRADO igual que el
    corte bueno. O sea el control negativo de este mismo fichero no podia salir
    en rojo, que es justo el defecto que la ficha vino a cerrar. Medido antes de
    invertir el orden: `--sostenido 0` -> falsos positivos 0, rc=0."""
    if dur >= sostenido:
        return "COLAPSO"
    if dur <= pico_max:
        return "PICO"
    return "SIN OBSERVAR"


def ventanas(incidentes=None):
    fmt = "%Y-%m-%d %H:%M"
    return [
        (dt.datetime.strptime(a, fmt), dt.datetime.strptime(b, fmt))
        for a, b in (incidentes if incidentes is not None else INCIDENTES)
    ]


def solapa(exc, ventana) -> bool:
    return not (exc[-1][0] < ventana[0] or exc[0][0] > ventana[1])


def calibra(serie, incidentes=None, umbral=UMBRAL_PCT, sostenido=SOSTENIDO_MIN,
            conocidos=None) -> dict:
    """Aplica el corte y coteja el instante medido de disparo con las etiquetas.

    Una excursión que solo empieza dentro de un incidente, pero alcanza la
    duración exigida después de su fin, no demuestra que el corte lo detectó.

    `conocidos`: falsos positivos conocidos (deuda con ficha abierta); None = los
    declarados en FALSOS_POSITIVOS_CONOCIDOS, [] = ninguno (el control negativo).
    """
    vs = ventanas(incidentes)
    colapsos, picos, sin_observar = [], [], []
    for exc in excursiones(serie, umbral):
        veredicto = clasifica(duracion_min(exc), PICO_MAX_MIN, sostenido)
        {"COLAPSO": colapsos, "PICO": picos, "SIN OBSERVAR": sin_observar}[veredicto].append(exc)

    disparos = [
        (exc, next((ts for ts, _ in exc
                    if (ts - exc[0][0]).total_seconds() / 60.0 >= sostenido), None))
        for exc in colapsos
    ]
    conocidos = FALSOS_POSITIVOS_CONOCIDOS if conocidos is None else conocidos
    falsos_positivos, falsos_positivos_conocidos = [], []
    for exc, disparo in disparos:
        if disparo is not None and any(a <= disparo <= b for a, b in vs):
            continue
        # La excepcion casa por el instante de DISPARO, igual que un incidente:
        # un stall que dispara fuera de la ventana exenta sigue siendo falso positivo.
        ficha = next((f for f, (a, b) in zip(conocidos, ventanas_exentas(conocidos))
                      if disparo is not None and a <= disparo <= b), None)
        if ficha is None:
            falsos_positivos.append(exc)
        else:
            falsos_positivos_conocidos.append((exc, ficha))
    # Una ventana FUERA del rango del corpus no esta "sin detectar": esta sin
    # OBSERVAR, y son cosas distintas. Contarla como no detectada mide la lista
    # INCIDENTES contra un corpus que no llega hasta ella -- el instrumento en
    # vez del sujeto. Se descubrio el 2026-09-27 al anadir el cuarto incidente:
    # los corpus sinteticos de la suite abarcan hasta el 09-24 y el cuarto es del
    # 09-26, asi que tres tests se pusieron rojos afirmando que un corte bueno
    # dejaba pasar un incidente que sus muestras no contienen.
    #
    # Y estar DENTRO del rango tampoco basta (2026-10-16): la ventana del
    # 2026-10-11 22:02 cae entre la primera y la ultima muestra del corpus pero
    # no tiene NI UNA muestra dentro -- bb sample dejo de escribir a las
    # 22:00:34 --, y contarla como no detectada era el mismo error un nivel mas
    # abajo. Una ventana esta OBSERVADA si al menos UNA muestra cae en
    # [inicio, fin]. Basta una y no se exige cobertura minima porque cualquier
    # minimo mayor RECLASIFICA mas ventanas como sin observar, que es la
    # direccion que tapa; y sobre el corpus real no hay caso intermedio que lo
    # pida: las ventanas dentro del rango tienen 47 (10-05), 0 (10-11 22:02) y
    # 43 (10-11 22:44) muestras. Una ventana CON muestras y sin disparo sigue
    # siendo `no_detectados`.
    if serie:
        t0, t1 = serie[0][0], serie[-1][0]
        en_rango = [v for v in vs if v[1] >= t0 and v[0] <= t1]
    else:
        en_rango = []
    observadas = [v for v in en_rango if any(v[0] <= ts <= v[1] for ts, _ in serie)]
    sin_muestras_en_ventana = [v for v in en_rango if v not in observadas]
    fuera_del_corpus = [v for v in vs if v not in en_rango]
    no_detectados = [
        v for v in observadas
        if not any(disparo is not None and v[0] <= disparo <= v[1]
                   for _, disparo in disparos)
    ]
    return {
        "rango": (serie[0][0].strftime("%Y-%m-%d %H:%M"),
                  serie[-1][0].strftime("%Y-%m-%d %H:%M")) if serie else ("", ""),
        "muestras": len(serie),
        "cero": sum(1 for _, v in serie if v == 0.0),
        "colapsos": colapsos,
        "picos": picos,
        "sin_observar": sin_observar,
        "falsos_positivos": falsos_positivos,
        "falsos_positivos_conocidos": falsos_positivos_conocidos,
        "no_detectados": no_detectados,
        "fuera_del_corpus": fuera_del_corpus,
        "sin_muestras_en_ventana": sin_muestras_en_ventana,
        "por_journal": [],
        "journal_could_not_run": [],
        "umbral": umbral,
        "sostenido": sostenido,
    }


def lee_journal(desde: dt.datetime, hasta: dt.datetime) -> list[str] | str:
    """-> las lineas del journal de bb-usable en [desde, hasta], o un str con el motivo de COULD_NOT_RUN.

    Un journal que no se pudo leer NUNCA vuelve como lista vacia: la lista vacia significa "el journal se leyo y no
    tiene nada ahi", y confundir las dos cosas es leer el instrumento caido como sujeto sano."""
    fmt = "%Y-%m-%d %H:%M:%S"
    try:
        p = subprocess.run(JOURNAL_CMD + ["--since", desde.strftime(fmt), "--until", hasta.strftime(fmt)],
                           capture_output=True, text=True, encoding="utf-8", errors="replace",
                           timeout=60, check=False)
    except (OSError, subprocess.TimeoutExpired) as e:
        return "%s: %s" % (JOURNAL_CMD[0], e)
    if p.returncode != 0 or "permission" in p.stderr.lower():
        return "%s rc=%d: %s" % (JOURNAL_CMD[0], p.returncode, " ".join(p.stderr.split())[:200])
    return p.stdout.splitlines()


def eventos_journal(lineas: list[str]) -> list[tuple[dt.datetime, str]]:
    """-> [(ts, tipo)] con tipo 'colapso' (bb-usable DECLARA COLAPSO: el corte disparo), 'reinicio' (systemd mata la
    unidad por watchdog: la maquina reinicia) o 'vivo' (cualquier otra linea de bb-usable: estaba corriendo, y como
    solo escribe PSI cuando PSI esta alta, su silencio mientras vive es PSI baja). Ignora lo que no tiene ts."""
    out = []
    for linea in lineas:
        try:
            t = _naive(dt.datetime.strptime(linea.split(" ", 1)[0], "%Y-%m-%dT%H:%M:%S%z"))
        except ValueError:
            continue
        if "[bb-usable] COLAPSO:" in linea:
            out.append((t, "colapso"))
        elif "bb-usable.service: Watchdog timeout" in linea:
            out.append((t, "reinicio"))
        elif "[bb-usable]" in linea:
            out.append((t, "vivo"))
    return out


def observa_journal(r: dict, ventana, eventos: list[tuple[dt.datetime, str]]) -> None:
    """Mueve una ventana de `sin_muestras_en_ventana` a OBSERVADA si el journal tiene alguna linea de bb-usable dentro.

    Detectada = bb-usable DECLARA COLAPSO dentro de [inicio, fin], la misma regla de disparo que las muestras. Si
    bb-usable estaba vivo y no lo declaro, va a `no_detectados` y el veredicto sale rojo. Que REINICIE es aparte y se
    imprime aparte: declarar colapso es el corte; reiniciar es el desenlace (watchdog hasta WATCHDOG_S despues)."""
    a, b = ventana
    dentro = [(t, k) for t, k in eventos if a <= t <= b]
    if not dentro:
        return
    r["sin_muestras_en_ventana"].remove(ventana)
    colapso = next((t for t, k in dentro if k == "colapso"), None)
    reinicio = None if colapso is None else next(
        (t for t, k in eventos if k == "reinicio" and colapso <= t <= b + dt.timedelta(seconds=WATCHDOG_S)), None)
    r["por_journal"].append((ventana, colapso, reinicio))
    if colapso is None:
        r["no_detectados"].append(ventana)


def informe(r: dict) -> list[str]:
    n = r["muestras"] or 1
    out = [
        "corte:  mem_full >= %g %% sostenido >= %g min" % (r["umbral"], r["sostenido"]),
        "corpus: %s -> %s" % r["rango"],
        "muestras con PSI:            %d" % r["muestras"],
        "linea base (mem_full 0.00):  %d  (%.2f %%)" % (r["cero"], 100.0 * r["cero"] / n),
        "",
        "excursiones sobre el %g %%:" % r["umbral"],
    ]
    for etiq, clave in (("PICO        (<= %g min)" % PICO_MAX_MIN, "picos"),
                        ("SIN OBSERVAR", "sin_observar"),
                        ("COLAPSO     (>= %g min)" % SOSTENIDO_MIN, "colapsos")):
        excs = r[clave]
        out.append("  %-24s %3d%s" % (etiq, len(excs), "" if not excs else "   " + ", ".join(
            "%s (%.0f min, max %.2f %%)" % (e[0][0].strftime("%m-%d %H:%M"), duracion_min(e),
                                            max(v for _, v in e)) for e in excs[:3])))
    out += [
        "",
        "control negativo (lo que DEBE salir en cero):",
        "  falsos positivos:          %d" % len(r["falsos_positivos"]),
        "  incidentes no detectados:  %d" % len(r["no_detectados"]),
        "  (incidentes fuera del corpus, sin observar: %d)"
        % len(r.get("fuera_del_corpus", [])),
        "",
        "deuda (no cuenta para el veredicto, y por eso se imprime entera):",
        "  ventanas de incidente sin muestras dentro:  %d" % len(r["sin_muestras_en_ventana"]),
    ]
    fmt = "%Y-%m-%d %H:%M"
    out += ["    %s -> %s: hueco de muestreo, ni las muestras ni el journal de bb-usable dicen si el corte la detecta"
            % (a.strftime(fmt), b.strftime(fmt)) for a, b in r["sin_muestras_en_ventana"]]
    out.append("  COULD_NOT_RUN, journal de bb-usable:  %d" % len(r["journal_could_not_run"]))
    out += ["    %s -> %s: %s" % (a.strftime(fmt), b.strftime(fmt), motivo)
            for (a, b), motivo in r["journal_could_not_run"]]
    out.append("  falsos positivos conocidos (excepcion atada a ficha abierta):  %d"
               % len(r["falsos_positivos_conocidos"]))
    out += ["    %s (%.0f min, max %.2f %%) -- deuda abierta %s"
            % (e[0][0].strftime("%m-%d %H:%M"), duracion_min(e), max(v for _, v in e), f["ficha"])
            for e, f in r["falsos_positivos_conocidos"]]
    out += ["", "ventanas sin muestras observadas por el journal de bb-usable:  %d" % len(r["por_journal"])]
    out += ["  %s -> %s: %s, %s" % (
        a.strftime(fmt), b.strftime(fmt),
        "declara COLAPSO %s" % colapso.strftime("%H:%M:%S") if colapso else "NO declara COLAPSO (bb-usable vivo)",
        "reinicia %s (watchdog)" % reinicio.strftime("%H:%M:%S") if reinicio else "no reinicia")
        for (a, b), colapso, reinicio in r["por_journal"]]
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="calibra y verifica los cortes de PSI de bb scan")
    ap.add_argument("--muestras", type=Path, default=MUESTRAS)
    ap.add_argument("--umbral", type=float, default=UMBRAL_PCT)
    ap.add_argument("--sostenido", type=float, default=SOSTENIDO_MIN)
    args = ap.parse_args(argv)

    if not args.muestras.is_dir():
        print("COULD_NOT_RUN: no existe %s" % args.muestras)
        return 2
    serie = carga(args.muestras)
    if not serie:
        print("COULD_NOT_RUN: 0 muestras con PSI en %s" % args.muestras)
        return 2

    r = calibra(serie, umbral=args.umbral, sostenido=args.sostenido)
    for v in list(r["sin_muestras_en_ventana"]):
        lineas = lee_journal(v[0], v[1] + dt.timedelta(seconds=WATCHDOG_S))
        if isinstance(lineas, str):
            r["journal_could_not_run"].append((v, lineas))
        else:
            observa_journal(r, v, eventos_journal(lineas))
    print("\n".join(informe(r)))
    malo = len(r["falsos_positivos"]) + len(r["no_detectados"])
    deuda = len(r["sin_muestras_en_ventana"]) + len(r["falsos_positivos_conocidos"])
    cnr = len(r["journal_could_not_run"])
    print("\nVEREDICTO: %s%s" % ("CORTE INVALIDO" if malo else
                                 "CALIBRADO, con deuda impresa arriba" if deuda else "CALIBRADO",
                                 " -- COULD_NOT_RUN: %d ventana(s) sin muestras y sin journal legible" % cnr
                                 if cnr else ""))
    # Un informe con COULD_NOT_RUN no es limpio aunque nada salga rojo: rc 2, la tercera salida.
    return 1 if malo else 2 if cnr else 0


if __name__ == "__main__":
    sys.exit(main())
