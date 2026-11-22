#!/usr/bin/env python3
"""Control de FALSOS POSITIVOS de la regla de racha de `bb-usable`
(DEBT-UNA-BAJADA-MOMENTANEA-ABSUELVE-UN-COLAPSO).

Por que existe, y no como comentario en un commit
-------------------------------------------------
El arreglo de la racha se diseno sobre la traza de UN incidente -- el kernel
panic del 2026-09-26-- y ahi acierta por construccion. La pregunta que decide
si se puede desplegar es la otra: cuantas veces habria reiniciado la maquina
CUANDO NO HACIA FALTA. Un vigilante que reinicia de mas es peor que el fallo
que vigila.

Se deja versionado por lo mismo que `tools/calibra_psi.py`: cuando llegue el
cuarto incidente, el control se RE-CORRE en vez de creerse.

QUE CORPUS SIRVE PARA ESTO, Y CUAL NO -- se midio antes de usar ninguno
----------------------------------------------------------------------
El primer intento simulo el demonio entero sobre las 21 636 muestras de
`bb sample` y dio "28 reinicios, 28 aciertos, 0 falsos positivos" **identico en
las cuatro variantes**, incluida la de hoy. Una medida que no distingue el
arreglo del defecto no mide el arreglo.

La causa, medida: durante un colapso el muestreador es victima del colapso que
graba. En la ventana del panico el corpus tiene DOS muestras sobre el umbral
-- 15:22:02 y 15:35:16-- separadas por 794 s. `bin/bb` muestrea una vez por
minuto y pierde la carrera; `bb-usable` lee `/proc/pressure` cada 30 s y
conservo su traza entera en el journal.

De ahi sale el alcance de este modulo, que es su carga util:

  el corpus NO sirve para simular los COLAPSOS -- sus huecos SON el colapso;
  el corpus SI sirve para las ventanas SANAS -- intervalo mediano 60 s, p95 60 s.

Y un control de falsos positivos vive entero en las ventanas sanas. Por eso
esto no simula reinicios: mide el maximo tiempo sostenido que la regla acumula
FUERA de toda ventana de incidente, y lo compara con el corte de accion.

El journal de `bb-usable` tampoco sirve como corpus, y merece decirse: solo
emite linea de PSI cuando PSI esta ALTA, asi que las lecturas bajas existen
como silencio. Leer silencio como "no acaricio" ya produjo una vez una medida
falsa de 33 reinicios en un arranque donde no hubo ninguno.

Control negativo: `--corte 180` mete la excursion sana mas larga y el veredicto
se vuelve FALSO POSITIVO, con rc=1. Un control que no puede salir en rojo no es
un control.

Se corre `python3 -m tools.control_racha`, que es la convencion de este repo
para un modulo de `tools/` -- la misma de `tools.check_harvest_accepted`. Un
`sys.path.insert` antes del import tambien habria funcionado en tiempo de
ejecucion, y pyright lo rechaza con razon: el import no se resuelve.
"""

from __future__ import annotations

import argparse
import datetime as dt
import math
import sys
from pathlib import Path

from tools.capture_io import strict_json_loads
from tools.calibra_psi import (
    FALSOS_POSITIVOS_CONOCIDOS,
    INCIDENTES,
    MUESTRAS,
    UMBRAL_PCT,
    ventanas_exentas,
)

# El corte de accion de bb-usable, en segundos. No se importa del demonio
# porque `bin/bb-usable` no es importable (sin extension, con guarda main):
# se fija aqui y `tests/test_control_racha.py` comprueba que son el mismo.
CORTE_S = 300.0

# Un hueco mas largo que esto no es continuidad: es un arranque nuevo o el
# muestreador muerto. Encadenar a traves de el inventaria una racha que nadie
# observo. 10 min es 10x el intervalo mediano.
HUECO_MAX_S = 600.0


class EntradaInvalida(ValueError):
    """El corpus contiene una muestra incompleta o imposible de interpretar."""


def carga_control(directorio: Path) -> list[tuple[dt.datetime, float]]:
    """Lee muestras PSI sin convertir una ausencia en cero observado.

    Sólo se ignoran los metadatos reconocidos de burst. Se tolera una última
    línea JSON truncada por archivo si quedan muestras utilizables. Una muestra
    PSI parseable debe traer ts y mem_full numérico y finito.
    """
    serie = []
    ficheros = sorted(directorio.glob("*.jsonl"))
    if not ficheros:
        raise EntradaInvalida(f"sin archivos JSONL en {directorio}")
    for fichero in ficheros:
        try:
            lineas = fichero.read_text(encoding="utf-8", errors="replace").splitlines(keepends=True)
        except OSError as exc:
            raise EntradaInvalida(f"no se pudo leer {fichero}: {exc}") from exc
        for indice, linea in enumerate(lineas):
            try:
                d = strict_json_loads(linea)
            except ValueError as exc:
                contenido = linea.rstrip("\r\n")
                error = getattr(exc, "msg", "")
                truncada = (
                    indice == len(lineas) - 1
                    and not linea.endswith(("\n", "\r"))
                    and (error.startswith("Unterminated string starting at")
                         or (bool(contenido) and contenido[-1] not in "}]"
                             and getattr(exc, "pos", -1) >= len(contenido)))
                )
                if truncada:
                    continue
                raise EntradaInvalida(f"JSON inválido en {fichero}:{indice + 1}") from exc
            if not isinstance(d, dict):
                raise EntradaInvalida(f"fila JSON no es objeto en {fichero}:{indice + 1}")
            if "burst_inicio" in d or "burst_fin" in d:
                es_inicio = (set(d) == {"ts", "burst_inicio", "motivo"}
                             and d["burst_inicio"] is True
                             and isinstance(d["motivo"], str) and bool(d["motivo"].strip()))
                es_fin = set(d) == {"ts", "burst_fin"} and d["burst_fin"] is True
                if not (es_inicio or es_fin):
                    raise EntradaInvalida(f"marcador de burst híbrido o inválido en {fichero}:{indice + 1}")
                try:
                    dt.datetime.strptime(d.get("ts", ""), "%Y-%m-%dT%H:%M:%S%z")
                except (TypeError, ValueError) as exc:
                    raise EntradaInvalida(f"timestamp inválido en {fichero}:{indice + 1}") from exc
                continue
            if "psi" not in d:
                raise EntradaInvalida(f"objeto PSI ausente en {fichero}:{indice + 1}")
            if not isinstance(d["psi"], dict):
                raise EntradaInvalida(f"objeto PSI inválido en {fichero}:{indice + 1}")
            try:
                t = dt.datetime.strptime(d.get("ts", ""), "%Y-%m-%dT%H:%M:%S%z")
            except (TypeError, ValueError) as exc:
                raise EntradaInvalida(f"timestamp inválido en {fichero}:{indice + 1}") from exc
            psi = d["psi"]
            if "mem_full" not in psi or psi["mem_full"] is None or isinstance(psi["mem_full"], bool):
                raise EntradaInvalida(f"psi.mem_full ausente o inválido en {fichero}:{indice + 1}")
            try:
                valor = float(psi["mem_full"])
            except (TypeError, ValueError, OverflowError) as exc:
                raise EntradaInvalida(f"psi.mem_full inválido en {fichero}:{indice + 1}") from exc
            if not math.isfinite(valor):
                raise EntradaInvalida(f"psi.mem_full no finito en {fichero}:{indice + 1}")
            if not 0 <= valor <= 100:
                raise EntradaInvalida(f"psi.mem_full fuera de [0, 100] en {fichero}:{indice + 1}")
            serie.append((t.replace(tzinfo=None), valor))
    serie.sort(key=lambda r: r[0])
    if not serie:
        raise EntradaInvalida(f"sin muestras PSI utilizables en {directorio}")
    return serie


# FALSOS_POSITIVOS_CONOCIDOS y ventanas_exentas viven en `tools.calibra_psi` desde el 2026-10-16 (una sola fuente:
# los dos instrumentos excluyen la misma ventana atada a la misma ficha) y se reexportan aqui con su nombre de siempre.


def ventanas() -> list[tuple[dt.datetime, dt.datetime]]:
    # Las ventanas las declara `calibra_psi.INCIDENTES` y no este modulo. Hasta el
    # 2026-09-27 aqui se anadia la del kernel panic aparte, porque aquel no la
    # tenia; en cuanto la tuvo, tenerla en dos sitios eran dos verdades que se
    # podian desincronizar. La escalera manda reusar.
    return [(dt.datetime.strptime(a, "%Y-%m-%d %H:%M"),
             dt.datetime.strptime(b, "%Y-%m-%d %H:%M"))
            for a, b in INCIDENTES]


def es_incidente(t: dt.datetime, vs=None) -> bool:
    return any(a <= t <= b for a, b in (vs or ventanas()))


def max_sostenido_sano(serie, bajas_para_cortar: int, umbral=UMBRAL_PCT, exentas=None):
    """-> (segundos, instante) del peor caso FUERA de un incidente.

    Acumula segundos REALES entre muestras, no numero de muestras: contar
    muestras mediria la cadencia del instrumento, que es justo lo que se
    rompe cuando hace falta. Carga el intervalo que ENTRA en la primera
    muestra alta, lo que sobreestima la racha en un intervalo -- el lado
    conservador para un control de falsos positivos.
    """
    # `exentas`: falsos positivos conocidos (deuda con ficha abierta); None = los declarados arriba, [] = ninguno.
    vs = ventanas() + (ventanas_exentas() if exentas is None else exentas)
    prev = None
    sostenido = 0.0
    bajas = 0
    peor = (0.0, None)
    for t, psi in serie:
        if es_incidente(t, vs):
            prev, sostenido, bajas = None, 0.0, 0
            continue
        dts = (t - prev).total_seconds() if prev else 0.0
        prev = t
        if dts > HUECO_MAX_S:
            sostenido, bajas = 0.0, 0
            continue
        if psi >= umbral:
            bajas = 0
            sostenido += dts
            if sostenido > peor[0]:
                peor = (sostenido, t)
        else:
            bajas += 1
            if bajas >= bajas_para_cortar:
                sostenido, bajas = 0.0, 0
    return peor


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    ap.add_argument("--muestras", type=Path, default=MUESTRAS)
    ap.add_argument("--corte", type=float, default=CORTE_S,
                    help="corte de accion en segundos; bajarlo es el control negativo")
    ap.add_argument("--bajas", type=int, nargs="+", default=[1, 2, 3, 6],
                    help="reglas a comparar: 1 es el defecto, 2 el arreglo")
    a = ap.parse_args(argv)

    if not math.isfinite(a.corte) or a.corte <= 0:
        print("COULD_NOT_RUN: --corte debe ser finito y mayor que cero", file=sys.stderr)
        return 2
    if any(b <= 0 for b in a.bajas):
        print("COULD_NOT_RUN: cada valor de --bajas debe ser mayor que cero", file=sys.stderr)
        return 2
    try:
        serie = carga_control(a.muestras)
    except EntradaInvalida as exc:
        print(f"COULD_NOT_RUN: {exc}", file=sys.stderr)
        return 2

    print(f"corpus {len(serie)} muestras  {serie[0][0]} -> {serie[-1][0]}")
    print(f"ventanas de incidente excluidas: {len(ventanas())}  "
          f"corte de accion: {a.corte:.0f}s  umbral: {UMBRAL_PCT:.0f}%")
    for f in FALSOS_POSITIVOS_CONOCIDOS:
        print(f"falso positivo CONOCIDO excluido (deuda abierta {f['ficha']}): "
              f"{f['ventana'][0]} -> {f['ventana'][1]}: {f['motivo']}")
    print()
    print(f"{'regla':40} {'max sostenido sano':>19}  veredicto")
    rc = 0
    for b in a.bajas:
        s, t = max_sostenido_sano(serie, b)
        malo = s >= a.corte
        rc |= int(malo)
        que = "defecto" if b == 1 else ("ARREGLO" if b == 2 else "mas flojo")
        print(f"  {f'{b} baja(s) para cortar ({que})':38} {s:10.0f} s"
              f"{'':8}{f'FALSO POSITIVO en {t}' if malo else 'no dispara'}")
    print()
    if rc:
        print("VEREDICTO: FALSO POSITIVO -- alguna regla reiniciaria la maquina "
              "fuera de todo incidente conocido.")
    else:
        mejor = max(max_sostenido_sano(serie, b)[0] for b in a.bajas)
        print(f"VEREDICTO: LIMPIO -- ninguna regla llega al corte. Margen del "
              f"corte contra el peor caso sano: {a.corte / max(mejor, 1e-9):.2f}x")
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
