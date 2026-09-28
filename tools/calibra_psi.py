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
    # 03:28:58 -- 11 de los 11 minutos que faltan hasta el reinicio no tienen
    # ni una sola linea en samples/2026-09-28.jsonl. Por eso el clasificador de
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
]


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
            pico_max=PICO_MAX_MIN) -> dict:
    """Aplica el corte y separa lo que cae DENTRO de un incidente etiquetado de
    lo que cae fuera. Lo segundo son los falsos positivos: el control negativo."""
    vs = ventanas(incidentes)
    colapsos, picos, sin_observar = [], [], []
    for exc in excursiones(serie, umbral):
        veredicto = clasifica(duracion_min(exc), pico_max, sostenido)
        {"COLAPSO": colapsos, "PICO": picos, "SIN OBSERVAR": sin_observar}[veredicto].append(exc)

    falsos_positivos = [e for e in colapsos if not any(solapa(e, v) for v in vs)]
    # Una ventana FUERA del rango del corpus no esta "sin detectar": esta sin
    # OBSERVAR, y son cosas distintas. Contarla como no detectada mide la lista
    # INCIDENTES contra un corpus que no llega hasta ella -- el instrumento en
    # vez del sujeto. Se descubrio el 2026-09-27 al anadir el cuarto incidente:
    # los corpus sinteticos de la suite abarcan hasta el 09-24 y el cuarto es del
    # 09-26, asi que tres tests se pusieron rojos afirmando que un corte bueno
    # dejaba pasar un incidente que sus muestras no contienen.
    if serie:
        t0, t1 = serie[0][0], serie[-1][0]
        observadas = [v for v in vs if v[1] >= t0 and v[0] <= t1]
    else:
        observadas = []
    fuera_del_corpus = [v for v in vs if v not in observadas]
    no_detectados = [v for v in observadas
                     if not any(solapa(e, v) for e in colapsos)]
    return {
        "rango": (serie[0][0].strftime("%Y-%m-%d %H:%M"),
                  serie[-1][0].strftime("%Y-%m-%d %H:%M")) if serie else ("", ""),
        "muestras": len(serie),
        "cero": sum(1 for _, v in serie if v == 0.0),
        "colapsos": colapsos,
        "picos": picos,
        "sin_observar": sin_observar,
        "falsos_positivos": falsos_positivos,
        "no_detectados": no_detectados,
        "fuera_del_corpus": fuera_del_corpus,
        "umbral": umbral,
        "sostenido": sostenido,
    }


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
    ]
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
    print("\n".join(informe(r)))
    malo = len(r["falsos_positivos"]) + len(r["no_detectados"])
    print("\nVEREDICTO: %s" % ("CALIBRADO" if not malo else "CORTE INVALIDO"))
    return 1 if malo else 0


if __name__ == "__main__":  # pragma: no cover -- entry point, ejercitado via main()
    sys.exit(main())
