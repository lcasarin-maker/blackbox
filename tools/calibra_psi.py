#!/usr/bin/env python3
"""Calibracion de los cortes de PSI de `bb scan` contra los incidentes propios
de esta maquina (DEBT-PSI-UMBRALES-SIN-CALIBRAR, satd_family BLIND_INSTRUMENT).

Existe para que los cortes se puedan RE-DERIVAR cuando lleguen mas incidentes,
en vez de quedar congelados en un comentario. Una calibracion cuya evidencia
solo vive en un mensaje de commit es el mismo instrumento ciego que esta ficha
vino a cerrar, un nivel mas arriba: nadie puede comprobar que sigue siendo
cierta.

Lo que mide, y por que asi:

  El NIVEL instantaneo de mem_full no discrimina. Medido sobre 19797 muestras
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
    no_detectados = [v for v in vs if not any(solapa(e, v) for e in colapsos)]
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
