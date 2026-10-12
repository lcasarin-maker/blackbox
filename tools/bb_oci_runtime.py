#!/usr/bin/env python3
"""Envoltorio de runtime OCI de bb: todo contenedor nace con tope propio.

## Por que existe

Voto de Luis (2026-10-12): todo contenedor lleva tope propio de memoria, swap
y procesos desde su creacion, incluido vLLM, sin depender de que alguien
recuerde un `--memory` ni de un `docker update` posterior (los tres
`docker update` del 2026-10-12 se pierden si el contenedor se recrea). El
punto donde se crea el cgroup es el runtime OCI que invoca el daemon, asi que
el tope se impone ahi: el daemon apunta su runtime a este fichero, que se
invoca exactamente como `runc`.

## Que hace

- `create --bundle <dir> ... <id>`: lee `<dir>/config.json`, aplica la
  politica (`decidir`, funcion pura) y, si admite, reescribe el config.json
  corregido y hace `exec` del runtime real.
- `delete <id>`: registra la liberacion del reclamo GPU y hace `exec`.
- Cualquier otro subcomando (start, kill, state, ...): `exec` tal cual.

El runtime real es `nvidia-container-runtime` (el que `/etc/docker/daemon.json`
declara hoy) o lo que diga `BB_OCI_REAL_RUNTIME`.

## La GPU no la acota el cgroup

Medido 2026-10-12: vLLM 33.4 GiB de GPU frente a 12.2 GiB de cgroup;
`dmem.capacity` vacio. El tope GPU es el RECLAMO declarado en la anotacion
`bb.gpu_budget_gib`, sumado sobre los contenedores registrados y comparado con
el suelo de GPU. Es una cuenta, no un limite del kernel.

## Falla cerrado hacia el comportamiento de hoy

Si no puede leer o parsear el spec, o falla cualquier cosa propia, pasa el spec
intacto al runtime real y lo registra (`NO_ACTUAR` con `NOT_COLLECTED` o
`UNSUPPORTED`). Nunca bloquea un contenedor por una averia suya: solo rechaza
por politica (GPU sin reclamo, reclamo ilegible, suma desbordada).

Sin imports de Atlas: solo stdlib.
"""

from __future__ import annotations

import contextlib
import copy
import fcntl
import json
import os
import sys
import time
from pathlib import Path

GIB = 1024**3

# Topes por defecto de cada clase. Se inyectan SOLO si el spec no trae el suyo.
# Origen, medido 2026-10-12 en /sys/fs/cgroup/docker.slice/docker-<id>.scope:
#   general: 3 GiB = el mayor tope aplicado en vivo ese dia (librechat, 4x su
#     pico de 753 MiB); los picos de los demas contenedores sin GPU fueron
#     atlas-pgvector 1.34 GiB, aequitas-pg 419 MiB, mongo-librechat 408 MiB.
#     pids 2048 = el valor aplicado en vivo; el mayor pids.peak fue 71 (mongo).
#   gpu: 14 GiB = MemoryMax de docker.slice (15032385536), el padre que ya acota
#     a todo contenedor de produccion: un tope por encima no compraria nada.
#     El pico de cgroup de vLLM fue 13368209408 (12.45 GiB). pids 2048 frente a
#     un pids.peak de 211 en vLLM.
CLASES = {
    "general": {"memoria": 3 * GIB, "pids": 2048},
    "gpu": {"memoria": 14 * GIB, "pids": 2048},
}

ANOTACION_GPU = "bb.gpu_budget_gib"

# Suelo de GPU: p95 de 19 901 muestras de memoria unificada de GPU, 50.1 GiB;
# es lo que la aritmetica de techos de slice deja a la GPU
# (~/.config/systemd/user/app.slice.d/99-blackbox.conf, voto 2026-09-27, y
# tools/presupuesto_memoria.py:suelo_gpu_gib). La suma de reclamos GPU
# declarados no puede pasar de ahi.
SUELO_GPU_GIB = 50.1
SUELO_GPU_ORIGEN = "p95 de 19901 muestras de GPU (99-blackbox.conf, voto 2026-09-27)"

RUNTIME_REAL = "nvidia-container-runtime"
REGISTRO = "oci_runtime.jsonl"

# Flags globales de runc/nvidia-container-runtime que consumen el argumento
# siguiente (la forma `--flag=valor` no lo consume).
GLOBALES_CON_VALOR = {"--root", "--log", "--log-format", "--criu", "--rootless"}
CREATE_CON_VALOR = {"--bundle", "-b", "--console-socket", "--pid-file", "--preserve-fds"}
GPU_ENV_VACIO = {"", "void", "none"}


# ---------------------------------------------------------------- politica pura

def pide_gpu(spec: dict) -> str | None:
    """La evidencia de que el contenedor pide GPU, o None.

    Las tres vias por las que nvidia-container-runtime la concede: la variable
    NVIDIA_VISIBLE_DEVICES (las imagenes CUDA la traen de serie), dispositivos
    /dev/nvidia* en el spec, o un hook nvidia-container ya inyectado.
    """
    for var in (spec.get("process") or {}).get("env") or []:
        nombre, _, valor = str(var).partition("=")
        if nombre == "NVIDIA_VISIBLE_DEVICES" and valor.strip().lower() not in GPU_ENV_VACIO:
            return f"env NVIDIA_VISIBLE_DEVICES={valor}"
    for dev in (spec.get("linux") or {}).get("devices") or []:
        if str((dev or {}).get("path", "")).startswith("/dev/nvidia"):
            return f"dispositivo {dev['path']}"
    for fase, hooks in (spec.get("hooks") or {}).items():
        for h in hooks or []:
            if "nvidia-container" in str((h or {}).get("path", "")):
                return f"hook {fase} {h['path']}"
    return None


def _positivo(x: object) -> bool:
    return isinstance(x, int) and not isinstance(x, bool) and x > 0


def reclamo_gpu(spec: dict) -> tuple[float | None, str | None]:
    """(GiB, None) si la anotacion es legible; (None, motivo) si no."""
    crudo = (spec.get("annotations") or {}).get(ANOTACION_GPU)
    if crudo is None:
        return None, f"pide GPU sin anotacion {ANOTACION_GPU}"
    try:
        gib = float(crudo)
    except (TypeError, ValueError):
        return None, f"anotacion {ANOTACION_GPU}={crudo!r} no es un numero"
    if not gib > 0 or gib == float("inf"):
        return None, f"anotacion {ANOTACION_GPU}={crudo!r} no es un reclamo positivo finito"
    return gib, None


def _topes(spec: dict, clase: str) -> list[str]:
    """Inyecta en `spec` (ya copiado) los topes que falten. Devuelve los cambios."""
    defecto = CLASES[clase]
    recursos = spec["linux"].setdefault("resources", {})
    memoria = recursos.setdefault("memory", {})
    pids = recursos.setdefault("pids", {})
    cambios = []
    if not _positivo(memoria.get("limit")):
        cambios.append(f"memory.limit {memoria.get('limit')!r} -> {defecto['memoria']}")
        memoria["limit"] = defecto["memoria"]
    # swap OCI = memoria + swap; igual al limite = sin swap. -1 (ilimitado) y 0
    # (runc lo trata como no puesto) cuentan como ausentes.
    if not _positivo(memoria.get("swap")):
        cambios.append(f"memory.swap {memoria.get('swap')!r} -> {memoria['limit']}")
        memoria["swap"] = memoria["limit"]
    if not _positivo(pids.get("limit")):
        cambios.append(f"pids.limit {pids.get('limit')!r} -> {defecto['pids']}")
        pids["limit"] = defecto["pids"]
    return cambios


def decidir(spec: object, reclamos: dict[str, float], suelo_gib: float,
            contenedor: str) -> dict:
    """La politica, sin I/O. `reclamos`: id -> GiB de los contenedores registrados.

    Devuelve `decision` (ADMITIR | CORREGIR | RECHAZAR | NO_ACTUAR), `motivo`,
    `spec` (el corregido, o None si no hay que reescribir), `cambios`, `clase`,
    `gpu` (evidencia) y `gpu_gib` (reclamo admitido).
    """
    base = {"spec": None, "cambios": [], "clase": None, "gpu": None, "gpu_gib": None}
    if not isinstance(spec, dict) or not isinstance(spec.get("linux"), dict):
        return {**base, "decision": "NO_ACTUAR",
                "motivo": "UNSUPPORTED: el spec no es un objeto con seccion linux"}
    gpu = pide_gpu(spec)
    clase = "gpu" if gpu else "general"
    base.update(gpu=gpu, clase=clase)
    if gpu:
        gib, error = reclamo_gpu(spec)
        if error:
            return {**base, "decision": "RECHAZAR", "motivo": f"{error} ({gpu})"}
        otros = sum(v for k, v in reclamos.items() if k != contenedor)
        if otros + gib > suelo_gib:
            return {**base, "decision": "RECHAZAR", "motivo": (
                f"reclamo GPU {gib} GiB + {otros:.1f} GiB ya registrados = "
                f"{otros + gib:.1f} GiB supera el suelo de GPU {suelo_gib} GiB")}
        base["gpu_gib"] = gib
    nuevo = copy.deepcopy(spec)
    cambios = _topes(nuevo, clase)
    if not cambios:
        return {**base, "decision": "ADMITIR", "motivo": "ya trae tope propio de memoria, swap y pids"}
    return {**base, "decision": "CORREGIR", "spec": nuevo, "cambios": cambios,
            "motivo": f"faltaban topes; inyectados los de la clase {clase}"}


def reclamos_vigentes(lineas: list[str]) -> tuple[dict[str, float], int]:
    """Repliega el registro: reclamos GPU admitidos menos los liberados por delete.

    Devuelve (id -> GiB, lineas ilegibles). Una linea ilegible se cuenta y se
    salta: el registro es de bb, y una averia suya no bloquea contenedores.
    """
    vivos: dict[str, float] = {}
    ilegibles = 0
    for linea in lineas:
        if not linea.strip():
            continue
        try:
            r = json.loads(linea)
            evento, cid = r["evento"], r["contenedor"]
        except (ValueError, TypeError, KeyError):
            ilegibles += 1
            continue
        if evento == "delete":
            vivos.pop(cid, None)
        elif evento == "create" and r.get("decision") in ("ADMITIR", "CORREGIR") and r.get("gpu_gib"):
            vivos[cid] = float(r["gpu_gib"])
    return vivos, ilegibles


# ---------------------------------------------------------------- argv de runc

def subcomando(argv: list[str]) -> int | None:
    """Indice del subcomando en argv, saltando flags globales; None si no hay."""
    i = 0
    while i < len(argv):
        if not argv[i].startswith("-"):
            return i
        i += 2 if argv[i] in GLOBALES_CON_VALOR else 1
    return None


def args_create(resto: list[str]) -> tuple[Path, str | None]:
    """(bundle, id) de los argumentos que siguen a `create`. Bundle por defecto: cwd."""
    bundle, cid, i = Path.cwd(), None, 0
    while i < len(resto):
        a = resto[i]
        nombre, igual, valor = a.partition("=")
        if nombre in ("--bundle", "-b"):
            if igual:
                bundle = Path(valor)
            elif i + 1 < len(resto):
                bundle = Path(resto[i + 1])
        if a in CREATE_CON_VALOR:
            i += 2
            continue
        if not a.startswith("-") and cid is None:
            cid = a
        i += 1
    return bundle, cid


# ---------------------------------------------------------------- I/O

def _dir_datos() -> Path:
    return Path(os.environ.get("BLACKBOX_DATA", Path.home() / ".local/share/blackbox"))


def _suelo() -> tuple[float, str]:
    crudo = os.environ.get("BB_OCI_GPU_FLOOR_GIB")
    if crudo is None:
        return SUELO_GPU_GIB, SUELO_GPU_ORIGEN
    try:
        return float(crudo), "BB_OCI_GPU_FLOOR_GIB"
    except ValueError:
        return SUELO_GPU_GIB, f"BB_OCI_GPU_FLOOR_GIB={crudo!r} ilegible; {SUELO_GPU_ORIGEN}"


def _avisa(texto: str) -> None:
    print(f"bb-oci-runtime: {texto}", file=sys.stderr)


def _escribe_spec(ruta: Path, spec: dict) -> None:
    tmp = ruta.with_name(ruta.name + ".bb-tmp")
    tmp.write_text(json.dumps(spec), encoding="utf-8")
    os.replace(tmp, ruta)


def _leer_spec(bundle: Path) -> tuple[object, str | None]:
    try:
        return json.loads((bundle / "config.json").read_text(encoding="utf-8")), None
    except (OSError, ValueError) as e:
        return None, f"NOT_COLLECTED: no se pudo leer o parsear {bundle}/config.json: {e}"


def gobernar_create(resto: list[str], registro, suelo: tuple[float, str]) -> dict:
    """Decide sobre un create y, si corrige, reescribe el config.json.

    `registro` es el fichero del registro ya abierto y bloqueado, o None si no
    se pudo abrir (entonces la suma GPU es NOT_COLLECTED y no bloquea).
    """
    bundle, cid = args_create(resto)
    fila = {"evento": "create", "contenedor": cid, "bundle": str(bundle),
            "suelo_gpu_gib": suelo[0], "suelo_origen": suelo[1]}
    spec, error = _leer_spec(bundle)
    if error:
        return {**fila, "decision": "NO_ACTUAR", "motivo": error}
    if registro is None:
        reclamos, ilegibles, nota = {}, 0, "NOT_COLLECTED: registro no disponible, suma GPU sin historia"
    else:
        registro.seek(0)
        reclamos, ilegibles = reclamos_vigentes(registro.read().splitlines())
        nota = None
    d = decidir(spec, reclamos, suelo[0], cid or "")
    if d["spec"] is not None:
        _escribe_spec(bundle / "config.json", d["spec"])
    fila.update({k: d[k] for k in ("decision", "motivo", "cambios", "clase", "gpu", "gpu_gib")})
    fila.update(reclamos_previos_gib=round(sum(reclamos.values()), 3),
                registro_lineas_ilegibles=ilegibles, registro_nota=nota)
    return fila


def _abrir_registro(pila: contextlib.ExitStack):
    """El registro abierto y bloqueado (lo cierra `pila`), o None si no se puede."""
    try:
        d = _dir_datos()
        d.mkdir(parents=True, exist_ok=True)
        registro = pila.enter_context(open(d / REGISTRO, "a+", encoding="utf-8"))
        fcntl.flock(registro, fcntl.LOCK_EX)
        return registro
    except OSError as e:
        _avisa(f"registro no disponible ({e}); se sigue sin historia")
        return None


def _anotar(registro, fila: dict) -> None:
    fila = {"ts": time.strftime("%Y-%m-%dT%H:%M:%S%z"), **fila}
    try:
        if registro is None:
            raise OSError("registro no abierto")
        registro.seek(0, os.SEEK_END)
        registro.write(json.dumps(fila, ensure_ascii=False) + "\n")
        registro.flush()
    except OSError as e:
        _avisa(f"no se pudo registrar la decision ({e}): {json.dumps(fila)}")


def gobernar(argv: list[str]) -> int | None:
    """Aplica la politica. Devuelve un codigo de salida si hay que rechazar."""
    i = subcomando(argv)
    sub = argv[i] if i is not None else None
    if sub not in ("create", "delete"):
        return None
    with contextlib.ExitStack() as pila:
        registro = _abrir_registro(pila)
        if sub == "delete":
            resto = [a for a in argv[i + 1:] if not a.startswith("-")]
            _anotar(registro, {"evento": "delete", "contenedor": resto[0] if resto else None,
                               "decision": "NO_ACTUAR", "motivo": "libera el reclamo GPU si lo habia"})
            return None
        try:
            fila = gobernar_create(argv[i + 1:], registro, _suelo())
        except Exception as e:  # falla cerrado: una averia propia nunca bloquea
            fila = {"evento": "create", "decision": "NO_ACTUAR",
                    "motivo": f"NOT_COLLECTED: averia del envoltorio {type(e).__name__}: {e}"}
        _anotar(registro, fila)
        if fila["decision"] == "RECHAZAR":
            _avisa(f"RECHAZADO {fila.get('contenedor')}: {fila['motivo']}")
            return 3
        return None


def main(argv: list[str]) -> int:
    try:
        rc = gobernar(argv)
    except Exception as e:  # falla cerrado: el contenedor sigue como hoy
        _avisa(f"NOT_COLLECTED: averia del envoltorio {type(e).__name__}: {e}; se pasa intacto")
        rc = None
    if rc is not None:
        return rc
    real = os.environ.get("BB_OCI_REAL_RUNTIME", RUNTIME_REAL)
    os.execvp(real, [real, *argv])
    return 127  # inalcanzable: execvp no vuelve o lanza OSError


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
