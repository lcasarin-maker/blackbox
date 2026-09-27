#!/usr/bin/env python3
"""Calibra el corte de latencia del escritorio contra episodios ETIQUETADOS.

Sirve a DOS fichas con una sola calibracion, y por eso existe como modulo:
`DEBT-SLUGGISH-SIN-CAUSA-PROBADA` necesita el corte para probar la causa, y
`DEBT-BB-USABLE-CIEGO-A-LA-LATENCIA` lo necesita en su PASO 3 para que
`bb-usable` pueda actuar sobre la latencia. Tener el numero en dos sitios seria
tener dos cortes.

SE NIEGA MIENTRAS NO HAYA ETIQUETA, Y ESA ES SU CARGA UTIL
----------------------------------------------------------
`bb-usable` actua con `FailureAction=reboot-immediate`. Un corte de latencia sin
calibrar le daria permiso para reiniciar la maquina por un numero inventado --
el mismo error que el encabezado de `bin/bb-usable` ya documenta haber cometido
con la sonda de 64 MiB, que volvia en 18 ms mientras la maquina llevaba cinco
horas inservible.

Asi que este modulo no propone un corte a partir de «muestras con latencia
alta». Eso es lo que parece la respuesta y no lo es, medido el 2026-09-27:

  muestras con x.ms >= 100 ms (2026-09-24 -> 27):            41
  de esas, con smi.ms >= 40 ms (bb desalojado, artefacto):   38
  correlacion x.ms vs smi.ms sobre 2234 muestras:            r = 0.631

Cuando el muestreador es desalojado, x.ms y smi.ms se inflan JUNTOS. Un corte
sobre x.ms solo esta contaminado por el estado del muestreador, y el 40 de ese
filtro me lo invente yo: el peor caso «real» que reporte el 2026-09-26 tenia
smi = 41, al otro lado de mi propio corte. La respuesta se volteaba con un
numero sin calibrar.

QUE CUENTA COMO ETIQUETA
------------------------
Un episodio en que una PERSONA declaro la maquina inusable. No se deduce de la
telemetria -- eso seria circular, igual que deducir un congelamiento de PSI en
`calibra_psi`. Dos fuentes, las dos externas a x.ms:

1. `bb snapshot "<motivo>"`, que ya existe y escribe `reason.txt` + `when.txt`.
   El motivo que cuenta lo declara MOTIVO_RE abajo. La escalera manda reusar:
   no hace falta un subcomando nuevo para marcar «ahora».
2. `EPISODIOS_DECLARADOS`, para los que ocurrieron antes de que hubiera sonda y
   se reconstruyeron a mano, con la misma disciplina que `calibra_psi.INCIDENTES`.

EL ESTADO HOY, MEDIDO Y NO SUPUESTO
-----------------------------------
  episodios etiquetados con muestras de x.ms:   0
  snapshots en la maquina:                      0
  el unico episodio declarado (2026-09-25 05:08, reinicio a mano porque
  "casi no se podia escribir") tiene 0 muestras con x: la sonda empezo a
  grabar a las 05:40, 32 min DESPUES del reinicio.

Por eso sale 2 (COULD_NOT_RUN) y dice que le falta. No sale 1: «no pude medir»
y «el corte esta mal» son cosas distintas.

Control negativo: `--etiqueta-de-prueba` inyecta un episodio sintetico sobre la
ventana mas lenta del corpus y el modulo TIENE que producir un veredicto. Un
calibrador que solo sabe negarse no se distingue de uno roto.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys
from pathlib import Path

MUESTRAS = Path.home() / ".local/share/blackbox/samples"
SNAPSHOTS = Path.home() / ".local/share/blackbox/snapshots"

# Un snapshot cuenta como etiqueta cuando su motivo dice que el ESCRITORIO no
# respondia. "manual" (el motivo por defecto) NO cuenta: un volcado forense
# puede tomarse por cualquier razon, y tratarlo como etiqueta de inusabilidad
# metería ruido en el lado positivo, que es el lado caro.
MOTIVO_RE = re.compile(r"inusable|sluggish|no.?responde|congel|lento|teclear",
                       re.IGNORECASE)

# Episodios declarados a mano, para los anteriores a la sonda. Cada uno lleva
# de donde sale, y ninguno sale de x.ms.
EPISODIOS_DECLARADOS = [
    # El dueno reinicio la ATOM a mano a las 05:08 porque estaba "sumamente
    # sluggish, casi no se podia escribir" (DEBT-SLUGGISH-SIN-CAUSA-PROBADA).
    # `last reboot`: el arranque anterior termina 05:08 y el nuevo entra 05:10.
    # La ventana se abre 60 min antes del reinicio porque nadie registro cuando
    # empezo -- es una COTA, y por eso este episodio no puede calibrar solo.
    ("2026-09-25 04:08", "2026-09-25 05:08",
     "reinicio a mano; 'casi no se podia escribir'"),
]

# Lo que se considera sano para el muestreador. Medido el 2026-09-27 sobre 2234
# muestras con los dos canales OK: smi.ms mediana 21, p95 43. El p95 es el corte
# porque por encima de el el muestreador esta compitiendo por CPU y su medida de
# x.ms ya no habla solo del escritorio.
SMI_SANO_MS = 43.0


def _lineas(directorio: Path):
    """Las lineas de todos los .jsonl. La lectura vive FUERA del bucle que
    parsea: mezclarlas hacia que un `except` de parseo cubriera tambien los
    errores de E/S, y `zero-debt` lo caza con `silent_io_loop_swallow` -- con
    razon, porque un fichero ilegible y una linea corrupta son cosas distintas
    y solo una de las dos se puede ignorar."""
    for f in sorted(directorio.glob("*.jsonl")):
        texto = f.read_text(encoding="utf-8", errors="replace")
        for linea in texto.splitlines():
            yield linea


def carga(directorio: Path, contador: dict | None = None):
    """-> [(ts, x_ms, smi_ms)] con los DOS canales en OK. Una muestra sin smi no
    sirve: sin ella no se puede saber si x.ms habla del escritorio o del
    muestreador.

    `contador` recibe, si se le pasa, POR QUE se descarto cada linea. No es
    adorno: el corpus es de produccion y "0 muestras utiles" tiene que poder
    distinguirse de "20 000 lineas descartadas por una razon que nadie miro".
    """
    c = contador if contador is not None else {}
    serie = []
    for linea in _lineas(directorio):
        if not linea.strip():
            continue
        try:
            r = json.loads(linea)
        except ValueError:
            c["json invalido"] = c.get("json invalido", 0) + 1
            continue
        x, s = r.get("x"), r.get("smi")
        if not (isinstance(x, dict) and isinstance(s, dict)):
            c["sin x o sin smi"] = c.get("sin x o sin smi", 0) + 1
            continue
        if x.get("estado") != "OK" or s.get("estado") != "OK":
            c["un canal no OK"] = c.get("un canal no OK", 0) + 1
            continue
        if not (isinstance(x.get("ms"), (int, float))
                and isinstance(s.get("ms"), (int, float))):
            c["ms no numerico"] = c.get("ms no numerico", 0) + 1
            continue
        try:
            t = dt.datetime.strptime(r.get("ts", ""), "%Y-%m-%dT%H:%M:%S%z")
        except ValueError:
            c["ts no parseable"] = c.get("ts no parseable", 0) + 1
            continue
        # El `.replace(tzinfo=None)` va FUERA del try, y no es estilo: el
        # detector `silent_io_loop_swallow` de zero-debt tiene `replace` en su
        # lista de llamadas de E/S -- por `Path.replace`, que mueve ficheros -- y
        # empareja por nombre de atributo, asi que `datetime.replace` dentro de
        # un try en un bucle lo dispara. Es un falso positivo del detector y esta
        # reportado aguas arriba; sacarlo del try lo evita sin apagar nada y deja
        # el try cubriendo solo lo que puede lanzar, que es mejor de todas formas.
        sin_tz = t.replace(tzinfo=None)
        serie.append((sin_tz, float(x["ms"]), float(s["ms"])))
    serie.sort(key=lambda p: p[0])
    return serie


def _snapshots_crudos(snapshots: Path):
    """(razon, cuando) de cada snapshot completo. La E/S va aqui y el juicio
    fuera, por lo mismo que `_lineas`."""
    for d in sorted(snapshots.iterdir()):
        razon_f, cuando_f = d / "reason.txt", d / "when.txt"
        if not (razon_f.is_file() and cuando_f.is_file()):
            continue
        yield (razon_f.read_text(encoding="utf-8", errors="replace").strip(),
               cuando_f.read_text(encoding="utf-8", errors="replace").strip())


def etiquetas(snapshots: Path = SNAPSHOTS):
    """-> [(inicio, fin, de_donde)]. Los snapshots son instantes, no ventanas;
    se les da +-2 min porque el muestreador va a 1/min y un instante solo no
    contiene ninguna muestra garantizada."""
    out = [(dt.datetime.strptime(a, "%Y-%m-%d %H:%M"),
            dt.datetime.strptime(b, "%Y-%m-%d %H:%M"), f"declarado: {q}")
           for a, b, q in EPISODIOS_DECLARADOS]
    if snapshots.is_dir():
        for razon, cuando in _snapshots_crudos(snapshots):
            if not MOTIVO_RE.search(razon):
                continue
            try:
                bruto = dt.datetime.fromisoformat(cuando)
            except ValueError:
                continue
            t = bruto.replace(tzinfo=None)
            out.append((t - dt.timedelta(minutes=2), t + dt.timedelta(minutes=2),
                        f"snapshot: {razon}"))
    return out


def dentro(t, vs):
    return any(a <= t <= b for a, b, _ in vs)


def con_muestras(vs, serie):
    """Las etiquetas que de verdad tienen muestras. Una etiqueta sin muestras no
    es un positivo: es una ventana sin observar, y contarla como positivo
    inventa el lado caro de la calibracion."""
    return [v for v in vs if any(dentro(t, [v]) for t, _, _ in serie)]


def evalua(serie, vs, corte_ms: float, sostenido: int = 1,
           smi_sano: float = SMI_SANO_MS):
    """Cuenta los dos errores para (corte, sostenido).

    La regla es de TRES partes, y cada una esta ahi por una medida:

    1. `x.ms >= corte`             -- el nivel.
    2. `smi.ms <= smi_sano`        -- el muestreador sano. Sin esto el estado
       del propio muestreador se lee como lentitud del escritorio: r = 0.631
       entre los dos canales sobre 2234 muestras.
    3. `sostenido` muestras seguidas cumpliendo 1 y 2 -- la DURACION.

    La tercera se anadio el 2026-09-27 porque el nivel NO separa. Medido con la
    etiqueta sintetica sobre la peor muestra con muestreador sano (x=773 ms):
    los cortes de 50 a 500 la detectan y dejan entre 21 y 3 falsos positivos; el
    de 800 deja 0 falsos positivos y la pierde. No hay nivel que separe.

    Es la misma leccion que `calibra_psi` ya pago en este repo con PSI: seis
    excursiones sanas llegaron al 98.53 % y un congelamiento real bajo al
    48.80 %, asi que el nivel se equivoca en las dos direcciones y lo que
    discrimina es cuanto DURA.
    """
    fp, cubiertos = [], set()
    racha = 0
    for t, x, s in serie:
        if x >= corte_ms and s <= smi_sano:
            racha += 1
        else:
            racha = 0
            continue
        if racha < sostenido:
            continue
        adentro = False
        for i, v in enumerate(vs):
            if dentro(t, [v]):
                cubiertos.add(i); adentro = True
        if not adentro:
            fp.append((t, x, s))
    no_detectados = [v for i, v in enumerate(vs) if i not in cubiertos]
    return fp, no_detectados


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    ap.add_argument("--muestras", type=Path, default=MUESTRAS)
    ap.add_argument("--snapshots", type=Path, default=SNAPSHOTS)
    ap.add_argument("--smi-sano", type=float, default=SMI_SANO_MS)
    ap.add_argument("--etiqueta-de-prueba", action="store_true",
                    help="control negativo: inyecta un episodio sintetico sobre "
                         "la ventana mas lenta del corpus, para comprobar que "
                         "este modulo PUEDE producir un veredicto")
    a = ap.parse_args(argv)

    descartadas: dict = {}
    serie = carga(a.muestras, descartadas)
    if descartadas:
        print("lineas descartadas: " + ", ".join(
            f"{v} por {k}" for k, v in sorted(descartadas.items())))
    if not serie:
        print(f"COULD_NOT_RUN: sin muestras con x.ms y smi.ms en {a.muestras}",
              file=sys.stderr)
        return 2

    vs = etiquetas(a.snapshots)
    if a.etiqueta_de_prueba:
        # La etiqueta sintetica se pone sobre la muestra mas lenta CON EL
        # MUESTREADOR SANO, no sobre la mas lenta del corpus. La diferencia es
        # lo que este modulo mide: la mas lenta de todas (1234 ms) tenia
        # smi = 1818, o sea el muestreador desalojado, y la regla conjunta se
        # niega a llamarla lentitud del escritorio -- correctamente. Poner la
        # etiqueta ahi hacia que el control solo pudiera llegar a rc=1, y un
        # control que no alcanza el camino del exito no prueba que exista.
        sanas = [p for p in serie if p[2] <= a.smi_sano]
        if not sanas:
            print("COULD_NOT_RUN: ni una muestra con el muestreador sano",
                  file=sys.stderr)
            return 2
        peor = max(sanas, key=lambda p: p[1])
        vs = vs + [(peor[0] - dt.timedelta(minutes=1),
                    peor[0] + dt.timedelta(minutes=1),
                    f"SINTETICA sobre la peor muestra con muestreador sano "
                    f"(x={peor[1]:.0f} ms, smi={peor[2]:.0f} ms) -- control "
                    f"negativo, no es un episodio real")]

    utiles = con_muestras(vs, serie)
    print(f"corpus: {len(serie)} muestras con los dos canales OK  "
          f"{serie[0][0]} -> {serie[-1][0]}")
    print(f"corte de muestreador sano: smi.ms <= {a.smi_sano:.0f}")
    print()
    print(f"etiquetas declaradas:        {len(vs)}")
    for i, (x0, x1, q) in enumerate(vs):
        tiene = "CON muestras" if (x0, x1, q) in utiles else "SIN muestras"
        print(f"  {x0} -> {x1}  [{tiene}]  {q}")
    print(f"etiquetas utilizables:       {len(utiles)}")
    print()

    if not utiles:
        print("COULD_NOT_RUN: no hay un solo episodio ETIQUETADO con muestras de",
              file=sys.stderr)
        print("  x.ms, asi que no existe lado positivo contra el que calibrar.",
              file=sys.stderr)
        print("  Un corte derivado solo de 'muestras con latencia alta' mide el",
              file=sys.stderr)
        print("  filtro que uno elige, no el escritorio.", file=sys.stderr)
        print("  COMO SE CONSIGUE UNA: durante el proximo episodio, correr")
        print("    bb snapshot \"el escritorio no responde\"")
        print("  Eso graba reason.txt + when.txt y este modulo lo lee como etiqueta.")
        return 2

    print(f"{'corte x.ms':>11} {'sostenido':>10} {'falsos+':>8} "
          f"{'no detectados':>14}  veredicto")
    mejor = None
    for sostenido in (1, 2, 3, 5):
        for corte in (50, 100, 150, 200, 300, 500, 800):
            fp, nd = evalua(serie, utiles, corte, sostenido, a.smi_sano)
            ok = not fp and not nd
            if ok and mejor is None:
                mejor = (corte, sostenido)
            print(f"{corte:>11} {sostenido:>10} {len(fp):>8} {len(nd):>14}  "
                  f"{'CALIBRADO' if ok else 'INVALIDO'}")
    print()
    if mejor is None:
        print("VEREDICTO: NINGUN CORTE SEPARA -- ni una combinacion de nivel y")
        print("duracion de las probadas deja falsos positivos y no detectados")
        print("en cero. Con UNA etiqueta eso no es raro: una ventana no fija dos")
        print("parametros. Hacen falta mas episodios etiquetados.")
        return 1
    corte, sostenido = mejor
    print(f"VEREDICTO: CALIBRADO con x.ms >= {corte} durante {sostenido} "
          f"muestra(s) seguidas y smi.ms <= {a.smi_sano:.0f}")
    return 0


if __name__ == "__main__":  # pragma: no cover -- entry point, ejercitado via main()
    raise SystemExit(main())
