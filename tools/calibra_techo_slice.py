"""Un techo de cgroup sale de una SERIE, o no sale.

## Por que existe

`DEBT-TECHOS-SIN-CALIBRAR` se quedo trabada el 2026-09-25 en su ultimo eslabon:
`system.slice` es el unico slice sin techo, ponerle uno hace que el presupuesto
componga -- hay 5.3 GiB de holgura en la mitad 1-- y no habia con que elegir el
numero. Lo unico disponible era su `memory.peak` de UN arranque: 2.8 GiB en
8 h 19 min.

Un techo sacado de un arranque es exactamente el techo sin calibrar que esa
ficha vino a quitar. El de `docker.slice` salio de 18 944 muestras, y ese es el
liston.

Asi que `bb sample` guarda un bloque `slices`, y esto es lo que lo lee. **El
unico que impedia que el numero se eligiera a ojo el dia que hubiera serie era
la buena voluntad de quien lo hiciera.** Este modulo lo impide: se NIEGA a
emitir un techo mientras la serie no lo sostenga, y dice exactamente que le
falta.

## Las DOS condiciones, y por que la segunda es la que vale

1. **Un minimo de muestras.** 18 944, el liston que fijo `docker.slice`. Es un
   PRECEDENTE, no una derivacion: nadie ha demostrado que 18 944 sea el numero
   correcto, solo que un techo sacado de esa serie se acepto y uno sacado de un
   arranque se rechazo. Se declara como lo que es.

2. **Que el maximo haya DEJADO DE CRECER.** Esta si sale del sujeto. Un maximo
   que sigue subiendo dice que la serie todavia no ha visto el peor caso, y un
   techo puesto sobre un maximo que crece se queda corto por construccion --
   mata procesos la primera vez que el slice hace lo que siempre iba a hacer.
   Se mide comparando el maximo del ultimo tercio de la ventana contra el de los
   dos primeros: si el ultimo tercio trae un maximo nuevo, la serie aun no esta
   madura.

La segunda es la que puede decir "todavia no" con 100 000 muestras, y por eso es
la que de verdad protege. La primera solo evita el caso burdo.

## El factor, y de donde sale

`docker.slice` quedo en 16G sobre un pico agregado de 11.2 GiB: **1.4x**. Se
reutiliza ese factor por precedente explicito del propio repo, no porque 1.4
tenga nada de especial. Queda declarado para que se pueda discutir.

## Lo que este modulo NO hace

No escribe el drop-in ni toca la maquina: eso pide `sudo` y vive en
`enable-privileged.sh`. Propone un numero con su derivacion delante, o se niega.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

DATA_DIR = Path(os.environ.get("BLACKBOX_DATA", Path.home() / ".local/share/blackbox"))

# Liston de muestras. PRECEDENTE, no derivacion -- ver el docstring.
MINIMO_MUESTRAS = 18_944
MINIMO_VIENE_DE = "el liston que fijo docker.slice (16G sobre 18 944 muestras)"

# Factor sobre el maximo observado. Precedente de docker.slice: 16G / 11.2 GiB.
FACTOR = 1.4
FACTOR_VIENE_DE = "docker.slice quedo en 16G sobre un pico agregado de 11.2 GiB"

# Fraccion final de la ventana que se compara contra el resto para decidir si el
# maximo ya se estabilizo. Un tercio: con menos, un solo pico tardio no tendria
# con que compararse; con mas, se descartaria media serie.
COLA = 1 / 3

SLICES = ("app", "docker", "system")

# Ficheros de muestras que no se pudieron leer. Igual que en
# `presupuesto_memoria`: un techo calculado sobre un conjunto incompleto puede
# salir MAS BAJO de lo real, y eso es un techo que mata procesos.
_ILEGIBLES: list[str] = []


def serie(nombre: str, samples: Path | None = None) -> list[tuple[str, float, float | None]]:
    """(ts, cur_gib, peak_gib) de un slice, en orden. Lista vacia si no aparece.

    `peak_gib` es `None` cuando el kernel no da `memory.peak`: "no lo da" y "fue
    cero" no son lo mismo, y solo uno de los dos se puede promediar.
    """
    d = samples or (DATA_DIR / "samples")
    _ILEGIBLES.clear()
    if not d.is_dir():
        _ILEGIBLES.append(f"{d}: no es un directorio")
        return []
    if not os.access(d, os.R_OK | os.X_OK):
        _ILEGIBLES.append(f"{d}: sin permiso de lectura")
        return []
    out: list[tuple[str, float, float | None]] = []
    for f in sorted(d.glob("*.jsonl")):
        try:
            texto = f.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            _ILEGIBLES.append(f"{f.name}: {exc}")
            continue
        for linea in texto.splitlines():
            if '"slices"' not in linea:
                continue
            try:
                o = json.loads(linea)
            except ValueError:
                continue
            for s in o.get("slices") or []:
                if not isinstance(s, dict) or s.get("slice") != nombre:
                    continue
                cur = s.get("cur_kb")
                if cur is None:
                    continue
                pk = s.get("peak_kb")
                out.append((str(o.get("ts", "?")), cur / 1024 ** 2,
                            None if pk is None else pk / 1024 ** 2))
    out.sort()
    return out


def maximo_ya_se_estabilizo(v: list[float]) -> tuple[bool, dict]:
    """El maximo del ultimo tercio contra el de los dos primeros.

    Si la cola trae un maximo NUEVO, la serie todavia no ha visto el peor caso y
    un techo puesto ahora se queda corto por construccion. Devuelve el veredicto
    y los dos numeros, porque un "todavia no" sin cifras no se puede discutir.
    """
    n = len(v)
    corte = int(n * (1 - COLA))
    # Con menos de dos muestras por lado no hay comparacion que hacer, y decir
    # "estable" sobre una sola observacion seria inventar la estabilidad.
    if n < 4 or corte < 2 or n - corte < 2:
        return False, {"cabeza": None, "cola": None, "muestras": n,
                       "porque": "serie demasiado corta para comparar dos tramos"}
    cabeza, cola = max(v[:corte]), max(v[corte:])
    return cola <= cabeza, {"cabeza": cabeza, "cola": cola, "muestras": n,
                            "corte": corte, "porque": ""}


def calibra(nombre: str, samples: Path | None = None) -> dict:
    """Propone un techo, o dice que le falta. Nunca las dos cosas."""
    s = serie(nombre, samples)
    cur = [c for _, c, _ in s]
    picos = [p for _, _, p in s if p is not None]
    # El sujeto del techo es el MAXIMO que el slice llego a tener, y `memory.peak`
    # lo sabe mejor que el muestreo de `current`: un pico entre dos muestras no
    # deja rastro en `current` y si en `peak`. Se toma el mayor de los dos para
    # no proponer un techo por debajo de algo que ya ocurrio.
    observado = max([*cur, *picos], default=None)
    estable, detalle = maximo_ya_se_estabilizo(picos or cur)

    faltas = []
    if _ILEGIBLES:
        faltas.append(f"{len(_ILEGIBLES)} fichero(s) de muestras ilegibles: el maximo "
                      "esta calculado sobre un conjunto incompleto y un techo sacado de "
                      "ahi puede quedarse CORTO")
    if not s:
        faltas.append(f"el slice '{nombre}' no aparece en ninguna muestra: no hay serie, "
                      "y eso no es un maximo de 0")
    elif len(s) < MINIMO_MUESTRAS:
        faltas.append(f"{len(s)} muestras, y el minimo declarado es {MINIMO_MUESTRAS} "
                      f"({MINIMO_VIENE_DE})")
    if s and not estable:
        if detalle["cola"] is None:
            faltas.append(f"el maximo no se puede declarar estable: {detalle['porque']}")
        else:
            faltas.append(
                f"el maximo TODAVIA CRECE: el ultimo tercio llego a "
                f"{detalle['cola']:.2f} GiB y los dos primeros se quedaron en "
                f"{detalle['cabeza']:.2f}. Una serie que aun sube no ha visto el peor "
                f"caso, y un techo puesto sobre ella se queda corto por construccion")

    propuesto = None
    if not faltas and observado is not None:
        propuesto = round(observado * FACTOR, 1)
    return {"slice": nombre, "muestras": len(s), "observado_gib": observado,
            "estable": estable, "estabilidad": detalle, "faltas": faltas,
            "propuesto_gib": propuesto, "ilegibles": list(_ILEGIBLES)}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("slice", nargs="?", default="system", choices=SLICES,
                    help="el slice a calibrar (por defecto system, el que falta)")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)

    r = calibra(args.slice)
    if args.json:
        print(json.dumps(r, ensure_ascii=False, indent=1))
        return 0 if r["propuesto_gib"] is not None else 1

    print(f"[calibra] slice:     {r['slice']}")
    print(f"[calibra] muestras:  {r['muestras']}  (minimo {MINIMO_MUESTRAS})")
    if r["observado_gib"] is None:
        print("[calibra] maximo:    COULD_NOT_RUN (sin serie)")
    else:
        print(f"[calibra] maximo:    {r['observado_gib']:.2f} GiB"
              "   (el mayor de `current` muestreado y `memory.peak`)")
    d = r["estabilidad"]
    if d.get("cola") is not None:
        print(f"[calibra] estable:   {'SI' if r['estable'] else 'NO'}"
              f"   (cola {d['cola']:.2f} vs cabeza {d['cabeza']:.2f} GiB)")
    for x in r["ilegibles"]:
        print(f"[calibra]   ilegible: {x}")

    if r["faltas"]:
        print("[calibra] SIN TECHO QUE PROPONER, y esto es lo que falta:", file=sys.stderr)
        for x in r["faltas"]:
            print(f"  - {x}", file=sys.stderr)
        print("[calibra] Un techo que no sale de una serie no es un techo calibrado: "
              "es un numero con una unidad detras.", file=sys.stderr)
        return 1

    assert r["propuesto_gib"] is not None and r["observado_gib"] is not None
    print(f"[calibra] PROPUESTO:  {r['propuesto_gib']:.1f} GiB"
          f"   = {r['observado_gib']:.2f} x {FACTOR}")
    print(f"[calibra] el factor {FACTOR} sale de: {FACTOR_VIENE_DE}")
    print("[calibra] Esto NO toca la maquina. El drop-in y su aplicacion viven en "
          "adopted/system-config/ y enable-privileged.sh, que piden sudo.")
    return 0


if __name__ == "__main__":  # pragma: no cover -- entry point, ejercitado via main()
    sys.exit(main())
