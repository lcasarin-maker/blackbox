#!/usr/bin/env python3
"""Le pone NOMBRE a las victimas de las senales que `bb sample` acumula
(DEBT-DGX-438-SIN-CAUSA-RAIZ).

Por que hace falta
------------------
`auditd` no emite `type=OBJ_PID` para las reglas de senal de este repo -- medido
el 2026-09-27: 0 registros en todo el anillo contra 307 SYSCALL con la clave --
asi que la victima solo se conoce por su PID, leido de `a0`. Y un pid sin nombre
no contesta la pregunta de la ficha, que es QUE mata los procesos de fondo.

El nombre no se puede leer del sistema despues: cuando el barrido lee el
registro, la victima ya murio y `/proc/<pid>` no existe. Lo unico que puede
nombrarla es lo que ya se grabo cuando estaba viva, y eso son las muestras de
`bin/bb`: `top_rss`, `pidio`, `cpu_top` y `gpu` llevan pid + comm + unit. Es el
segundo peldano de la escalera, reusar, y no hay otro que sirva.

Por que va en Python y no en `bin/bb`
------------------------------------
El cruce lee JSON de dos sitios y `bin/bb` es bash sin lector de JSON. Meterlo
ahi seria parsear JSON con `sed`, que es como se escriben los defectos que este
repo persigue.

Lo que NO puede hacer, declarado
--------------------------------
Una victima que nunca aparecio en una muestra no se puede nombrar. Las listas de
las muestras son top-5 y van a 1/min, asi que un proceso de vida corta -- justo
el que muere por una senal -- puede no haber sido visto nunca. Medido el
2026-09-27: 18 de 227 capturas tienen victima nombrable, el 8 %. Ese 8 % no es un
defecto de este modulo: es lo que hay grabado.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from collections import Counter
from pathlib import Path

DATOS = Path.home() / ".local/share/blackbox"
CAPTURAS = DATOS / "sigterm.jsonl"
MUESTRAS = DATOS / "samples"

# Las listas de proceso de una muestra que llevan pid + comm.
LISTAS = ("top_rss", "pidio", "cpu_top", "gpu")


def normaliza_pid(v) -> int | None:
    """El entero CON SIGNO que `kill(2)` recibio, leido de un `a0` sin signo.

    Un pid negativo es un GRUPO de procesos y `kill(0, sig)` va contra el propio
    grupo del emisor. `bin/bb` conserva el signo desde el 2026-09-27, pero las
    314 capturas ya acumuladas traen la forma SIN signo -- 44 de ellas, el
    14.0 % -- y reescribir telemetria de solo-anadir para arreglar un lector es
    peor que ensenarle las dos formas.

    La conversion no es ambigua: `pid_max` en Linux llega a 2^22, asi que ningun
    pid legitimo alcanza 2^31.
    """
    try:
        n = int(v)
    except (TypeError, ValueError):
        return None
    return n - 2**32 if n >= 2**31 else n


def indice_pids(muestras: Path) -> dict[int, tuple[str, str]]:
    """pid -> (comm, unit), de todo lo que las muestras vieron vivo.

    Se queda con la PRIMERA vista de cada pid. Los pids se reciclan, pero el
    espacio de pids de esta caja llega a 2.7 millones y las muestras cubren
    dias, no meses: el reciclaje exigiria dar la vuelta entera. Si algun dia
    importa, el desempate seria por cercania temporal a la captura.
    """
    idx: dict[int, tuple[str, str]] = {}
    for f in sorted(muestras.glob("*.jsonl")):
        for linea in f.read_text(encoding="utf-8", errors="replace").splitlines():
            try:
                r = json.loads(linea)
            except ValueError:
                continue
            for clave in LISTAS:
                for e in r.get(clave) or []:
                    if not isinstance(e, dict):
                        continue
                    pid = e.get("pid")
                    if not isinstance(pid, int):
                        continue
                    idx.setdefault(pid, (str(e.get("comm") or "?"),
                                         str(e.get("unit") or "?")))
    return idx


def capturas(fichero: Path) -> list[dict]:
    if not fichero.is_file():
        return []
    out = []
    for linea in fichero.read_text(encoding="utf-8", errors="replace").splitlines():
        if not linea.strip():
            continue
        try:
            out.append(json.loads(linea))
        except ValueError:
            continue
    return out


def nombra(caps: list[dict], idx: dict[int, tuple[str, str]]) -> list[dict]:
    """Devuelve las capturas con `victima.comm`/`victima.unit` rellenos donde se
    pudo. Donde no, se deja explicito en vez de inventar un nombre."""
    out = []
    for c in caps:
        v = dict(c.get("victima") or {})
        pid = normaliza_pid(v.get("pid"))
        # Un grupo se nombra por su LIDER, cuyo pid es el del grupo: eso es lo
        # que las muestras pueden haber visto vivo. Nombrar al lider no afirma
        # que muriera el lider -- murio el grupo -- y por eso la etiqueta lo
        # dice en vez de dejarlo implicito.
        grupo = pid is not None and pid < 0
        v["grupo"] = grupo
        if grupo and pid is not None:      # el `is not None` lo pide el tipo, no la logica
            clave = -pid
        else:
            clave = pid
        comm, unit = idx.get(clave, (None, None)) if clave is not None else (None, None)
        if grupo and comm:
            comm = f"{comm} (y su grupo)"
        v["comm"] = comm or "(ninguna muestra lo vio vivo)"
        v["unit"] = unit or "?"
        v["nombrada"] = comm is not None
        out.append({**c, "victima": v})
    return out


# Herramientas que MATAN por encargo. Su nombre identifica el utensilio, no a
# quien decidio: atribuir a `kill` es como atribuir a un martillo.
ENVOLTORIOS = {"kill", "pkill", "killall", "timeout", "pgrep", "xargs"}


def es_autolimpieza(c: dict) -> bool:
    """La senal va contra el PROPIO arbol del emisor.

    Tres pruebas, las tres sobre el dato y ninguna sobre el nombre:

    1. `victima.pid == 0`: `kill(0, sig)` va contra el propio grupo del emisor
       por definicion de POSIX;
    2. la victima ES el padre del emisor (`victima.pid == emisor.ppid`), o el
       GRUPO cuyo lider es ese padre, que es el caso literal de `pkill`
       invocado por el proceso al que mata;
    3. la victima y el PADRE del emisor son el mismo pid o el mismo nombre.

    La version anterior de esta funcion comparaba el nombre del EMISOR con el de
    la victima, y eso fallaba justo en el caso que domina esta caja: `kill` y
    `pkill` matando a `rustdesk`. Reportaba 12 capturas como "sujeto de
    DGX-438" cuando eran rustdesk limpiando sus propios hijos a traves de un
    envoltorio. Lo vi en su propia salida, no en el codigo.
    """
    e = c.get("emisor") or {}
    v = c.get("victima") or {}
    vpid = normaliza_pid(v.get("pid"))
    try:
        ppid = int(e.get("ppid") or 0)
    except (TypeError, ValueError):
        ppid = 0
    # `kill(0, sig)` va contra el PROPIO grupo del emisor -- eso es POSIX, no una
    # inferencia sobre estos datos-- asi que es autolimpieza sin cruzar nada.
    # Medido el 2026-09-27: 28 de 314 capturas, el 8.9 %, y se venian contando
    # como misterio porque `0` no casaba con ningun ppid.
    if vpid == 0:
        return True
    # Un grupo cuyo LIDER es el emisor o su padre es el arbol del emisor.
    if vpid is not None and vpid < 0 and ppid and -vpid == ppid:
        return True
    if vpid is not None and ppid and vpid == ppid:
        return True
    # Mismo nombre entre victima y emisor, para el caso directo (sin envoltorio).
    ec, vc = str(e.get("comm") or ""), str(v.get("comm") or "")
    if not ec or not vc or vc.startswith("("):
        return False
    if Path(ec).name in ENVOLTORIOS:
        return False    # el nombre del envoltorio no dice nada; manda el ppid
    return Path(ec).name.split()[0] in vc or vc in Path(ec).name


def atribucion_incompleta(c: dict) -> bool:
    """El emisor es un ENVOLTORIO y su padre no se pudo nombrar.

    Estas capturas no son el sujeto de DGX-438 ni lo contrario: no se sabe quien
    decidio. Contarlas como sujeto manda a buscar un culpable llamado `kill`.
    """
    ec = Path(str((c.get("emisor") or {}).get("comm") or "")).name
    return ec in ENVOLTORIOS and not es_autolimpieza(c)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    ap.add_argument("--capturas", type=Path, default=CAPTURAS)
    ap.add_argument("--muestras", type=Path, default=MUESTRAS)
    ap.add_argument("--solo-demonios", action="store_true",
                    help="solo los emisores con auid unset, que es el sujeto de DGX-438")
    a = ap.parse_args(argv)

    caps = capturas(a.capturas)
    if not caps:
        print(f"COULD_NOT_RUN: sin capturas en {a.capturas}. Las acumula "
              f"`bb sample`; si el fichero no existe, el barrido no ha corrido.",
              file=sys.stderr)
        return 2
    idx = indice_pids(a.muestras)
    if not idx:
        print(f"COULD_NOT_RUN: sin muestras en {a.muestras}, asi que no hay con "
              f"que nombrar a nadie", file=sys.stderr)
        return 2

    ns = nombra(caps, idx)
    if a.solo_demonios:
        ns = [c for c in ns if (c.get("emisor") or {}).get("clase") == "demonio"]

    nombradas = sum(1 for c in ns if c["victima"]["nombrada"])
    auto = [c for c in ns if es_autolimpieza(c)]
    print(f"capturas: {len(ns)}   victimas nombradas: {nombradas} "
          f"({100.0 * nombradas / len(ns):.0f} %)")
    print(f"pids que las muestras vieron vivos: {len(idx)}")
    print()

    print("por emisor y victima:")
    def _clave(c):
        return ((c.get("emisor") or {}).get("clase", "?"),
                Path((c.get("emisor") or {}).get("comm") or "?").name,
                c["victima"]["comm"])
    grupos = Counter(_clave(c) for c in ns)
    # La marca cuenta CUANTAS del grupo son autolimpieza, no "alguna". Marcar el
    # grupo entero porque una fila coincide es la clase de resumen que hace que
    # dos filas distintas se lean como la misma.
    autos = Counter(_clave(c) for c in ns if es_autolimpieza(c))
    for k, n in grupos.most_common(15):
        cl, ec, vc = k
        a = autos.get(k, 0)
        marca = f"  [{a} de {n} autolimpieza]" if a else ""
        print(f"  {n:>4}  {cl:8} {ec[:22]:22} -> {vc}{marca}")
    print()

    # El sujeto de DGX-438, aislado: demonio -> proceso ajeno, no autolimpieza.
    incompletas = [c for c in ns if atribucion_incompleta(c)]
    sujeto = [c for c in ns
              if (c.get("emisor") or {}).get("clase") == "demonio"
              and not es_autolimpieza(c)
              and not atribucion_incompleta(c)
              and c["victima"]["nombrada"]]
    print(f"autolimpieza (la senal va contra el propio arbol del emisor): "
          f"{sum(1 for c in ns if es_autolimpieza(c))}")
    print(f"ATRIBUCION INCOMPLETA (emisor es un envoltorio y su padre no se "
          f"nombro): {len(incompletas)}")
    print()
    print(f"SUJETO DE DGX-438 (emisor demonio, victima ajena y nombrada): {len(sujeto)}")
    for c in sujeto[:10]:
        print(f"  {dt.datetime.fromtimestamp(c['ts']):%Y-%m-%d %H:%M:%S} "
              f"{c['senal']:8} {Path(c['emisor']['comm']).name[:20]:20} -> "
              f"{c['victima']['comm']} ({c['victima']['unit']})")
    if not sujeto:
        print("  Ninguna, y eso NO es 'no ocurre'. Es que en lo acumulado no hay")
        print("  una sola captura de un demonio matando un proceso ajeno cuyo")
        print("  emisor se pueda atribuir Y cuya victima se pueda nombrar. Lo que")
        print("  hay es autolimpieza y atribucion incompleta, contadas arriba, mas")
        print("  las victimas que ninguna muestra vio vivas.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
