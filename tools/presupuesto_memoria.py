"""Los techos de memoria de esta maquina COMPONEN, o no son una proteccion.

## Por que existe

`DEBT-TECHOS-SIN-CALIBRAR`, abierta el 2026-09-24: los techos declarados sumaban
125G en una maquina de 121.1 GiB. No es que los numeros fueran flojos -- es que
no caben. Un conjunto de techos que no compone no protege nada: si cada dueno
reclamara lo suyo, la maquina se agota con todos los techos respetados.

La ficha no se podia cerrar porque faltaba un numero: cuanta memoria unificada
reserva de verdad la GPU, que **ningun cgroup ve**. Este modulo lo fija con
medida y comprueba la suma.

## El numero que faltaba, medido

`nvidia-smi` reporta la memoria unificada por proceso; el cgroup de ese mismo
proceso no la contabiliza. Medido el 2026-09-25 en esta caja:

    pid 20687  VLLM::EngineCore   nvidia-smi 32837 MiB   su cgroup 10.0 GB
    pid  3443  atlas-api          nvidia-smi  4522 MiB   su cgroup  5.9 GB

Un punto no es una medida, asi que el techo sale del HISTORICO que bb ya
guarda: el campo `gpu` de sus muestras lleva pid y MiB desde el 2026-09-08.
Sobre **18 733 muestras con al menos un proceso de GPU**, el maximo agregado
observado es **87 487 MiB = 85.4 GiB**, el 2026-09-21T00:33.

Eso es lo que hay que restarle al presupuesto antes de repartir el resto.

## Lo que este gate NO dice, antes de que alguien lo suponga

No dice que 85.4 GiB sea el maximo posible: dice que es el maximo OBSERVADO en
la ventana que bb lleva grabada. Por eso el gate tambien comprueba lo contrario
-- que las muestras no hayan superado ya la reserva declarada-- y falla si la
cifra se quedo vieja. Una reserva fijada una vez y nunca releida es exactamente
el techo sin calibrar que esta ficha vino a quitar.

Y no mide fragmentacion, ni el kernel, ni el page cache: mide que la suma de lo
DECLARADO quepa en lo que hay.
"""

from __future__ import annotations

import argparse
import datetime
import json
import os
import sys
from pathlib import Path

CGROUP = Path(os.environ.get("BB_CGROUP_ROOT", "/sys/fs/cgroup"))
MEMINFO = Path(os.environ.get("BB_MEMINFO", "/proc/meminfo"))
DATA_DIR = Path(os.environ.get("BLACKBOX_DATA", Path.home() / ".local/share/blackbox"))

GIB = 1024 ** 3

# Ficheros de muestras que no se pudieron leer en la ultima llamada a
# `pico_gpu_observado_mib`. Vive aqui y no como valor de retorno para no
# cambiarle la forma a una funcion que ya usan los tests por su tupla.
_ILEGIBLES: list[str] = []

# La serie completa (ts, MiB) de la ultima pasada por las muestras. Se guarda
# para no recorrer 18 000 lineas dos veces: el pico y las excursiones salen del
# mismo barrido.
_SERIE: list[tuple[str, int]] = []

# EL MAXIMO OBSERVADO de memoria unificada de GPU, en GiB. Ya NO es lo que la
# aritmetica resta, y el cambio no es cosmetico -- ver `suelo_gpu_gib`.
#
# ## Por que dejo de serlo (medido el 2026-09-25)
#
# Este numero es el maximo de la serie, y sumarlo junto a los techos mezclaba
# dos cosas que no son iguales:
#
#   - `app.slice = 48G` es un COMPROMISO. El kernel lo aplica.
#   - `86.0` es una OBSERVACION. No lo aplica nadie, y ningun cgroup ve esa
#     memoria (medido aqui: 7 GiB de CUDA se contabilizan como 15 MiB).
#
# Sumarlas y llamar al total "SUMA declarada" es el mismo error que este modulo
# le marca a `system.slice` -- "entra por lo que usa HOY y no por un
# compromiso"-- cometido sobre 86 GiB en vez de sobre 1.9.
#
# Y tenia una consecuencia dura, no estetica: **el check no podia salir
# positivo**. Con la reserva en 86, a los cgroups les quedan 121.1 - 86.0 =
# 35.1 GiB, y `app.slice` SOLA pico 39.8 GiB (memory.peak = 42731823104 bytes,
# leido el 2026-09-25). No hay reparto que satisfaga el criterio sin poner el
# techo del escritorio por debajo de lo que el escritorio ya uso. Un criterio
# que no puede salir positivo sin matar al sujeto no es un criterio.
#
# ## Que es el pico de verdad, ahora que se abrio
#
# Los ocho procesos del 2026-09-21T00:33 tienen nombre: son workers de
# `pytest-xdist` corriendo una suite de tests (`test_structured_chunking.py`,
# `test_scjn_delta_refresh_service.py`, `test_tfja_jurisprudence.py`...), cada
# uno con su modelo en la GPU. No es carga de servicio: es una corrida de
# tests, y duro CUATRO MINUTOS (00:30 -> 00:33).
#
# La serie entera, 19 067 muestras del 09-10 al 09-25:
#
#   p50 49.05 | p85 50.00 | p90 50.15 | p95 50.15 | p99 52.18 | max 85.40
#   por encima de 55.3 GiB: 18 episodios, 67 min EN TOTAL, el mas largo 11 min
#
# O sea: una meseta de ~50 GiB el 95 % del tiempo y una cola de 33 GiB que dura
# minutos. Reservar el maximo de forma permanente contra un transitorio de
# cuatro minutos no es reservar: es garantizar que la cuenta no cuadre nunca.
#
# Se conserva como el SUJETO de la mitad 2 del criterio: la excursion hay que
# FIRMARLA (`tasks/presupuesto_gpu.json`), porque no hay cgroup que la acote.
RESERVA_GPU_GIB = 86.0
RESERVA_MEDIDA_EL = "2026-09-25, maximo de 18 733 muestras (pico 2026-09-21T00:33)"

# Declaracion FIRMADA del presupuesto de excursion de GPU.
#
# Vive en `tasks/` y no en `.simplecode/` por lo mismo que `tasks/pii_allow.txt`:
# `.gitignore` ignora `.simplecode/*`, asi que una declaracion ahi no viajaria al
# clone y el siguiente que clonara veria un gate rojo sin ninguna firma que lo
# explique.
#
# **Su ausencia es el estado por defecto, y es ROJO a proposito.** Este modulo no
# trae una plantilla firmada: una plantilla que el gate acepte es el agujero. La
# excursion la firma una persona, con su nombre y una fecha de caducidad, o el
# criterio no pasa.
DECLARACION = Path(os.environ.get(
    "BB_PRESUPUESTO_GPU_DECL",
    str(Path(__file__).resolve().parent.parent / "tasks" / "presupuesto_gpu.json")))

# Slices cuyo techo se lee de la maquina. La ruta del gestor de usuario lleva
# el UID, que se resuelve en tiempo de ejecucion.
def _slices() -> dict[str, Path]:
    uid = os.getuid()
    return {
        "app.slice (escritorio y arneses)":
            CGROUP / "user.slice" / f"user-{uid}.slice" / f"user@{uid}.service" / "app.slice",
        "docker.slice (contenedores)": CGROUP / "docker.slice",
        "system.slice (servicios del sistema)": CGROUP / "system.slice",
    }


def mem_total_gib() -> float | None:
    """MemTotal en GiB, o None si no se puede leer -- que no es lo mismo que 0."""
    try:
        for linea in MEMINFO.read_text(encoding="utf-8").splitlines():
            if linea.startswith("MemTotal:"):
                return int(linea.split()[1]) / (1024 ** 2)
    except (OSError, ValueError, IndexError):
        return None
    return None


def techo_gib(ruta: Path) -> float | None:
    """El techo declarado de un cgroup en GiB. `None` si NO tiene techo, que es
    un hecho distinto de tener uno grande: un slice sin techo no se puede
    presupuestar, solo observar."""
    try:
        crudo = (ruta / "memory.max").read_text(encoding="utf-8").strip()
    except OSError:
        return None
    if crudo == "max":
        return None
    try:
        return int(crudo) / GIB
    except ValueError:
        return None


def uso_gib(ruta: Path) -> float:
    """Lo que un cgroup usa AHORA. Para los que no tienen techo es lo unico
    que se puede meter en la cuenta, y se dice que es una observacion."""
    try:
        return int((ruta / "memory.current").read_text(encoding="utf-8").strip()) / GIB
    except (OSError, ValueError):
        return 0.0


def pico_gpu_observado_mib(samples: Path | None = None
                           ) -> tuple[int, str] | None:
    """El maximo agregado de memoria unificada en las muestras de bb.

    Devuelve (MiB, timestamp) o None si no hay muestras que leer -- y `None`
    significa "no se pudo comprobar", no "esta bien". Quien llama decide.

    Los ficheros que NO se pudieron leer no se ignoran en silencio: se cuentan
    en `_ILEGIBLES` y `main` los imprime. Un pico calculado sobre un conjunto
    incompleto puede salir mas bajo de lo real, y presentarlo como el maximo
    seria afirmar algo que la lectura no respalda. Lo cazo `zero-debt` con
    `silent_io_loop_swallow` sobre la primera version de esta funcion, que hacia
    `except OSError: continue`.
    """
    d = samples or (DATA_DIR / "samples")
    mejor: tuple[int, str] | None = None
    _ILEGIBLES.clear()
    _SERIE.clear()
    # El permiso se comprueba ANTES y a proposito. La version anterior envolvia
    # el glob en `try/except OSError`, y eso era decoracion: medido el
    # 2026-09-25, `Path.glob` NO lanza sobre un directorio sin permisos ni sobre
    # uno inexistente -- devuelve vacio. Esa rama no podia ejecutarse, y el
    # efecto real era peor que su ausencia: un directorio ilegible se habria
    # leido como "no hay muestras", que es una afirmacion sobre la maquina que
    # nadie hizo.
    if not d.is_dir():
        _ILEGIBLES.append(f"{d}: no es un directorio")
        return None
    if not os.access(d, os.R_OK | os.X_OK):
        _ILEGIBLES.append(f"{d}: sin permiso de lectura")
        return None
    for f in sorted(d.glob("*.jsonl")):
        try:
            texto = f.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            _ILEGIBLES.append(f"{f.name}: {exc}")
            continue
        for linea in texto.splitlines():
            if '"gpu"' not in linea:
                continue
            try:
                d_ = json.loads(linea)
            except ValueError:
                continue
            g = d_.get("gpu")
            if not g:
                continue
            s = sum(x.get("mib", 0) or 0 for x in g if isinstance(x, dict))
            _SERIE.append((str(d_.get("ts", "?")), s))
            if mejor is None or s > mejor[0]:
                mejor = (s, str(d_.get("ts", "?")))
    return mejor


def excursiones_gpu(umbral_gib: float) -> dict:
    """Cuantas muestras pasaron del presupuesto de GPU, y las ultimas.

    Se llama DESPUES de `pico_gpu_observado_mib`, que es quien llena la serie.
    Con la serie vacia devuelve ceros y lo dice: "no se midio" y "no hubo
    excursiones" no son lo mismo, y aqui la diferencia la lleva `muestras`.
    """
    umbral_mib = umbral_gib * 1024
    por_encima = [(ts, m) for ts, m in _SERIE if m > umbral_mib]
    return {"muestras": len(_SERIE), "por_encima": len(por_encima),
            "pct": (100.0 * len(por_encima) / len(_SERIE)) if _SERIE else 0.0,
            "ultimas": sorted(por_encima)[-3:]}


def suelo_gpu_gib() -> dict | None:
    """El SUELO COMPROMETIDO de memoria unificada: lo que la GPU tiene tomado en
    el minuto ordinario, que es contra lo que los techos tienen que componer.

    Se llama DESPUES de `pico_gpu_observado_mib`, que es quien llena la serie.
    Devuelve `None` con la serie vacia -- "no se midio" no es "el suelo es 0".

    ## Por que el p95, y por que eso no es una preferencia

    Porque en esta serie la eleccion del percentil casi no mueve el numero, y eso
    esta medido sobre las 19 067 muestras del 09-10 al 09-25:

        p50 49.05 | p75 49.48 | p85 50.00 | p90 50.15 | p95 50.15 | p99 52.18

    De p50 a p95 el suelo se mueve **1.10 GiB** sobre una maquina de 121.1; de
    p85 a p95, **0.15**. La distribucion es una meseta, no una pendiente, asi que
    el numero lo pone el sujeto y no quien elige el percentil. Lo que sigue
    despues no es meseta: de p99 al maximo hay un salto de **33.26 GiB**, y ese
    salto es justo lo que la mitad 2 obliga a firmar.

    Se toma el borde alto de la meseta (p95) y no la mediana a proposito: entre
    dos numeros que se diferencian en 1.1 GiB, el presupuesto se queda con el
    que deja menos sitio a los techos.
    """
    if not _SERIE:
        return None
    v = sorted(m / 1024 for _, m in _SERIE)
    n = len(v)

    def q(pct: float) -> float:
        return v[min(n - 1, int(pct * n))]

    return {"gib": q(0.95), "muestras": n, "p50": q(0.50), "p95": q(0.95),
            "max": v[-1]}


def declaracion_excursion(hoy: str | None = None) -> tuple[dict | None, str]:
    """La firma que autoriza la excursion de GPU, o el motivo por el que no vale.

    Devuelve `(declaracion, "")` si es valida, o `(None, motivo)` si no. El motivo
    se imprime literal: un gate que dice "FAIL" sin decir que le falta obliga a
    adivinar, y se acaba adivinando mal.

    Exige las cuatro cosas porque las cuatro han fallado antes en esta flota:
    `excursion_gib` (que es lo que se autoriza), `owner` (una suspension sin
    dueno no la restaura nadie), `expires` (una sin caducidad se vuelve
    permanente en silencio -- los 59 hooks de Cerberus), y `reason` (una firma
    sin porque no se puede discutir cuando caduque).
    """
    try:
        crudo = DECLARACION.read_text(encoding="utf-8")
    except OSError:
        return None, (f"nadie ha firmado el presupuesto de excursion: no existe "
                      f"{DECLARACION}. Mientras no exista, esto es ROJO a proposito")
    try:
        d = json.loads(crudo)
    except ValueError as exc:
        return None, f"{DECLARACION} no es JSON valido: {exc}"
    if not isinstance(d, dict):
        return None, f"{DECLARACION} no es un objeto JSON"
    faltan = [k for k in ("excursion_gib", "expires", "owner", "reason") if not d.get(k)]
    if faltan:
        return None, f"{DECLARACION} no declara: {', '.join(faltan)}"
    try:
        gib = float(d["excursion_gib"])
    except (TypeError, ValueError):
        return None, f"excursion_gib no es un numero: {d['excursion_gib']!r}"
    try:
        vence = datetime.date.fromisoformat(str(d["expires"]))
    except ValueError:
        return None, f"expires no es una fecha ISO: {d['expires']!r}"
    ahora = (datetime.date.fromisoformat(hoy) if hoy else datetime.date.today())
    if vence < ahora:
        return None, (f"la firma de {DECLARACION} CADUCO el {vence} "
                      f"(hoy es {ahora}): se vuelve a discutir, no se renueva sola")
    return {"excursion_gib": gib, "expires": str(vence),
            "owner": str(d["owner"]), "reason": str(d["reason"])}, ""


def presupuesto() -> dict:
    """La cuenta entera, en un dict. Sin veredicto: eso lo pone `main`."""
    total = mem_total_gib()
    filas = []
    for nombre, ruta in _slices().items():
        t = techo_gib(ruta)
        filas.append({"nombre": nombre, "techo_gib": t, "uso_gib": uso_gib(ruta),
                      "existe": (ruta / "memory.max").exists()})
    pico = pico_gpu_observado_mib()
    suelo = suelo_gpu_gib()
    decl, decl_motivo = declaracion_excursion()
    # MITAD 1 -- la suma de COMPROMISOS. Entra el suelo comprometido de GPU (lo
    # que tiene tomado en el minuto ordinario), no su maximo: el maximo es un
    # transitorio de cuatro minutos y no lo aplica nadie. Ver `RESERVA_GPU_GIB`.
    #
    # Un slice SIN techo entra por lo que usa, y eso se marca, porque un numero
    # observado no es un compromiso: manana puede ser otro.
    sin_techo = []
    gasto = None if suelo is None else suelo["gib"]
    for f in filas:
        if not f["existe"]:
            continue
        if f["techo_gib"] is None:
            sin_techo.append(f["nombre"])
            if gasto is not None:
                gasto += f["uso_gib"]
        elif gasto is not None:
            gasto += f["techo_gib"]
    # Lo que le queda a la GPU si todos los techos declarados se honran. Es el
    # mismo reparto visto por el otro lado, y es EL UMBRAL de la alarma del
    # abanico: por encima de aqui, la memoria unificada esta comprometiendo
    # memoria que algun cgroup tiene derecho a reclamar.
    #
    # No se elige: se resta. Medido el 2026-09-25 sobre 18 944 muestras, con
    # docker.slice en 16G el corte cae en 53.1 GiB y se supera el 0.9 % del
    # tiempo; con docker.slice en 32G caeria en 37.1 y se superaria el 75.4 %,
    # o sea dentro del estado estacionario (mediana 49.0, p90 50.1). Que el
    # corte derivado caiga justo por encima del p90 observado es lo que valida
    # el reparto: el presupuesto y la conducta coinciden.
    techos = sum(f["techo_gib"] for f in filas
                 if f["existe"] and f["techo_gib"] is not None)
    usados_sin_techo = sum(f["uso_gib"] for f in filas
                           if f["existe"] and f["techo_gib"] is None)
    presupuesto_gpu = (total - techos - usados_sin_techo) if total is not None else None
    return {"mem_total_gib": total, "reserva_gpu_gib": RESERVA_GPU_GIB,
            "presupuesto_gpu_gib": presupuesto_gpu,
            "suelo_gpu": suelo,
            "declaracion": decl, "declaracion_motivo": decl_motivo,
            "slices": filas, "gasto_gib": gasto, "sin_techo": sin_techo,
            "pico_gpu_observado_mib": pico[0] if pico else None,
            "pico_gpu_ts": pico[1] if pico else None,
            "muestras_ilegibles": list(_ILEGIBLES)}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--check", action="store_true",
                    help="sale 1 si los techos no componen o la reserva quedo vieja")
    ap.add_argument("--json", action="store_true", help="la cuenta en JSON")
    args = ap.parse_args(argv)

    p = presupuesto()
    if args.json:
        print(json.dumps(p, ensure_ascii=False, indent=1))
        return 0

    total = p["mem_total_gib"]
    print(f"[presupuesto] MemTotal:            {total:8.1f} GiB"
          if total is not None else "[presupuesto] MemTotal:            COULD_NOT_RUN")
    print("[presupuesto] -- mitad 1: COMPROMISOS (lo que el kernel aplica) --")
    s = p["suelo_gpu"]
    if s is None:
        print("[presupuesto]   suelo comprometido de GPU        COULD_NOT_RUN (serie vacia)")
    else:
        print(f"[presupuesto]   suelo comprometido de GPU   {s['gib']:8.1f} GiB"
              f"  (p95 de {s['muestras']} muestras; con el p50 serian"
              f" {s['p50']:.1f} -- la meseta mueve {s['p95'] - s['p50']:.1f})")
    for f in p["slices"]:
        if not f["existe"]:
            print(f"[presupuesto]   {f['nombre']:<38} AUSENTE")
        elif f["techo_gib"] is None:
            print(f"[presupuesto]   {f['nombre']:<38} SIN TECHO"
                  f"  (usa {f['uso_gib']:.1f} GiB ahora, y eso es una observacion)")
        else:
            print(f"[presupuesto]   {f['nombre']:<38} {f['techo_gib']:8.1f} GiB"
                  f"  (usa {f['uso_gib']:.1f})")
    if p["gasto_gib"] is None:
        print("[presupuesto]   SUMA comprometida           COULD_NOT_RUN")
    else:
        holgura = None if total is None else total - p["gasto_gib"]
        print(f"[presupuesto]   SUMA comprometida           {p['gasto_gib']:8.1f} GiB"
              + ("" if holgura is None else
                 f"  sobre {total:.1f} -> holgura {holgura:.1f}"))
    print("[presupuesto] -- mitad 2: EXCURSION (lo que NADIE aplica, y por eso se firma) --")
    if p["pico_gpu_observado_mib"] is None:
        print("[presupuesto]   maximo observado             COULD_NOT_RUN (sin muestras)")
    else:
        print(f"[presupuesto]   maximo observado            "
              f"{p['pico_gpu_observado_mib'] / 1024:8.1f} GiB  ({p['pico_gpu_ts']})")
    d = p["declaracion"]
    if d is None:
        print(f"[presupuesto]   presupuesto firmado          SIN FIRMAR"
              f"  ({p['declaracion_motivo']})")
    else:
        print(f"[presupuesto]   presupuesto firmado         {d['excursion_gib']:8.1f} GiB"
              f"  (firma {d['owner']}, caduca {d['expires']})")
    if p["presupuesto_gpu_gib"] is not None:
        print("[presupuesto] -- vista de operacion: la alarma del abanico --")
        print(f"[presupuesto]   umbral del abanico          {p['presupuesto_gpu_gib']:8.1f} GiB"
              f"  (lo que le queda a la GPU si TODOS los techos se honran)")
        ex = excursiones_gpu(p["presupuesto_gpu_gib"])
        if ex["muestras"] == 0:
            print("[presupuesto] excursiones del abanico: COULD_NOT_RUN (serie vacia)")
        else:
            print(f"[presupuesto]   excursiones: {ex['por_encima']} de "
                  f"{ex['muestras']} muestras ({ex['pct']:.1f} %) por encima del presupuesto")
            for ts, m in ex["ultimas"]:
                print(f"                 {ts}  {m/1024:.1f} GiB")

    if not args.check:
        return 0

    if p["muestras_ilegibles"]:
        print(f"[presupuesto] could_not_run: {len(p['muestras_ilegibles'])} fichero(s) "
              f"de muestras ilegibles -- el pico puede salir MAS BAJO de lo real:")
        for x in p["muestras_ilegibles"]:
            print(f"                 {x}")

    problemas = []
    if p["muestras_ilegibles"]:
        problemas.append(
            f"{len(p['muestras_ilegibles'])} fichero(s) de muestras ilegibles: el pico "
            "de GPU esta calculado sobre un conjunto incompleto y no puede sostener "
            "la reserva declarada")
    if total is None:
        print("[presupuesto] COULD_NOT_RUN: no se pudo leer MemTotal", file=sys.stderr)
        return 2
    if p["gasto_gib"] is None:
        problemas.append(
            "COULD_NOT_RUN: sin serie de GPU no hay suelo comprometido que restar, "
            "y una suma sin el no dice nada")
    elif p["gasto_gib"] > total:
        problemas.append(
            f"MITAD 1 -- los compromisos NO componen: {p['gasto_gib']:.1f} GiB sobre "
            f"{total:.1f} GiB de maquina, {p['gasto_gib'] - total:.1f} GiB de mas")
    # MITAD 2. La excursion no la acota ningun cgroup, asi que no se puede
    # presupuestar: solo se puede FIRMAR. Sin firma es rojo, y eso es el estado
    # por defecto a proposito -- ver `DECLARACION`.
    if p["declaracion"] is None:
        problemas.append(f"MITAD 2 -- {p['declaracion_motivo']}")
    elif p["pico_gpu_observado_mib"] is not None:
        pico_gib = p["pico_gpu_observado_mib"] / 1024
        firmado = p["declaracion"]["excursion_gib"]
        if pico_gib > firmado:
            problemas.append(
                f"MITAD 2 -- la excursion se PASO de lo firmado: se observaron "
                f"{pico_gib:.1f} GiB ({p['pico_gpu_ts']}) y la firma autoriza "
                f"{firmado:.1f} GiB. Se vuelve a firmar con el numero nuevo delante, "
                f"o se acota el abanico")
    if p["sin_techo"]:
        problemas.append(
            "slice(s) sin techo, que entran en la cuenta por lo que usan HOY y no "
            "por un compromiso: " + ", ".join(p["sin_techo"]))

    if problemas:
        print("[presupuesto] FAIL:", file=sys.stderr)
        for x in problemas:
            print(f"  - {x}", file=sys.stderr)
        print("[presupuesto] Un conjunto de techos que no compone no es una proteccion: "
              "es aritmetica que nadie hizo. Y una excursion que nadie firma no es "
              "un riesgo aceptado: es uno que nadie miro.", file=sys.stderr)
        return 1
    print("[presupuesto] OK: lo declarado cabe en lo que hay.")
    return 0


if __name__ == "__main__":  # pragma: no cover -- entry point, ejercitado via main()
    sys.exit(main())
