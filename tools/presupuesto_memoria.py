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

# Reserva de memoria unificada de GPU, en GiB.
#
# EL NUMERO NO ES EL QUE EL vLLM DECLARA, y eso se comprobo antes de fijarlo.
# El gateway corre con `--gpu-memory-utilization 0.3`, que sobre 121.1 GiB son
# 36.3 GiB, y seria tentador presupuestar contra eso. Los picos DIARIOS medidos
# sobre las muestras de bb dicen otra cosa -- lo superan TODOS los dias:
#
#   09-10  70.3   09-13  53.3   09-16  50.2   09-19  49.1   09-22  57.4
#   09-11  53.5   09-14  54.8   09-17  49.5   09-20  66.6   09-23  38.0  <- minimo
#   09-12  74.2   09-15  50.1   09-18  49.1   09-21  85.4   09-24  67.0
#
# El pico del 2026-09-21 (85.4 GiB) no era el vLLM: eran 33.6 GiB suyos mas
# **ocho procesos de GPU simultaneos en `cov-solo.scope` sumando 48 GiB**, con
# `mem_avail` en 0.2 GB y load1 en 18.4. Un abanico de trabajo sin techo de
# memoria unificada, que ningun cgroup ve -- medido en esta caja: 7 GiB de CUDA
# se contabilizan como 15 MiB.
#
# Asi que la reserva se fija en el MAXIMO OBSERVADO y no en lo configurado:
# 85.4 GiB redondeado al GiB de arriba. Presupuestar contra el numero bonito
# habria dado un gate que falla todos los dias, que no es vigilancia sino ruido.
RESERVA_GPU_GIB = 86.0
RESERVA_MEDIDA_EL = "2026-09-25, maximo de 18 733 muestras (pico 2026-09-21T00:33)"

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


def presupuesto() -> dict:
    """La cuenta entera, en un dict. Sin veredicto: eso lo pone `main`."""
    total = mem_total_gib()
    filas = []
    for nombre, ruta in _slices().items():
        t = techo_gib(ruta)
        filas.append({"nombre": nombre, "techo_gib": t, "uso_gib": uso_gib(ruta),
                      "existe": (ruta / "memory.max").exists()})
    pico = pico_gpu_observado_mib()
    # Lo que se gasta: la reserva de GPU + el techo de cada slice que lo tenga.
    # Un slice SIN techo entra por lo que usa, y eso se marca, porque un numero
    # observado no es un compromiso: manana puede ser otro.
    gasto = RESERVA_GPU_GIB
    sin_techo = []
    for f in filas:
        if not f["existe"]:
            continue
        if f["techo_gib"] is None:
            gasto += f["uso_gib"]
            sin_techo.append(f["nombre"])
        else:
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
    print(f"[presupuesto] reserva de GPU:      {p['reserva_gpu_gib']:8.1f} GiB"
          f"   (memoria unificada que ningun cgroup ve; medida {RESERVA_MEDIDA_EL})")
    for f in p["slices"]:
        if not f["existe"]:
            print(f"[presupuesto]   {f['nombre']:<38} AUSENTE")
        elif f["techo_gib"] is None:
            print(f"[presupuesto]   {f['nombre']:<38} SIN TECHO"
                  f"  (usa {f['uso_gib']:.1f} GiB ahora, y eso es una observacion)")
        else:
            print(f"[presupuesto]   {f['nombre']:<38} {f['techo_gib']:8.1f} GiB"
                  f"  (usa {f['uso_gib']:.1f})")
    print(f"[presupuesto] SUMA declarada:      {p['gasto_gib']:8.1f} GiB")
    if p["presupuesto_gpu_gib"] is not None:
        print(f"[presupuesto] presupuesto de GPU:   {p['presupuesto_gpu_gib']:8.1f} GiB"
              f"   (lo que le queda si TODOS los techos se honran -- el umbral del abanico)")
        ex = excursiones_gpu(p["presupuesto_gpu_gib"])
        if ex["muestras"] == 0:
            print("[presupuesto] excursiones del abanico: COULD_NOT_RUN (serie vacia)")
        else:
            print(f"[presupuesto] excursiones del abanico: {ex['por_encima']} de "
                  f"{ex['muestras']} muestras ({ex['pct']:.1f} %) por encima del presupuesto")
            for ts, m in ex["ultimas"]:
                print(f"                 {ts}  {m/1024:.1f} GiB")

    if p["pico_gpu_observado_mib"] is None:
        print("[presupuesto] pico de GPU observado: COULD_NOT_RUN (sin muestras que leer)")
    else:
        print(f"[presupuesto] pico de GPU observado: {p['pico_gpu_observado_mib']/1024:6.1f} GiB"
              f"   ({p['pico_gpu_ts']})")

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
    if p["gasto_gib"] > total:
        problemas.append(
            f"los techos NO componen: {p['gasto_gib']:.1f} GiB declarados sobre "
            f"{total:.1f} GiB de maquina, {p['gasto_gib'] - total:.1f} GiB de mas")
    if p["pico_gpu_observado_mib"] is not None:
        pico_gib = p["pico_gpu_observado_mib"] / 1024
        if pico_gib > p["reserva_gpu_gib"]:
            problemas.append(
                f"la reserva de GPU quedo VIEJA: se observaron {pico_gib:.1f} GiB "
                f"y la declarada es {p['reserva_gpu_gib']:.1f} GiB")
    if p["sin_techo"]:
        problemas.append(
            "slice(s) sin techo, que entran en la cuenta por lo que usan HOY y no "
            "por un compromiso: " + ", ".join(p["sin_techo"]))

    if problemas:
        print("[presupuesto] FAIL:", file=sys.stderr)
        for x in problemas:
            print(f"  - {x}", file=sys.stderr)
        print("[presupuesto] Un conjunto de techos que no compone no es una proteccion: "
              "es aritmetica que nadie hizo.", file=sys.stderr)
        return 1
    print("[presupuesto] OK: lo declarado cabe en lo que hay.")
    return 0


if __name__ == "__main__":  # pragma: no cover -- entry point, ejercitado via main()
    sys.exit(main())
