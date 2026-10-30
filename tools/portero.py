#!/usr/bin/env python3
"""Portero de la maquina: cola FIFO y tope por trabajo pesado dentro de `app.slice` (FEATURE-PORTERO-UNIVERSAL-DE-LA-MAQUINA-01).

Los dos colapsos del 11-oct fueron una estampida de `git push` con pre-push (suite completa) lanzados a la vez
por seis sesiones, cada uno sin tope propio dentro de un `app.slice` de 42 GiB compartido. El portero detecta
esos arboles SIN que el llamador lo invoque (lee /proc), les pone un tope por clase y los hace pasar de uno en uno.

Dos mitades separadas:

* `decide(arboles, estado)` es PURA: sin I/O. Recibe lo observado y devuelve acciones (`admitir`, `congelar`,
  `descongelar`, `mover`, `esperar`, `no_actua`), cada una con su motivo. Es lo que prueban los tests de ramas.
* El resto tiene efecto y usa solo lo delegado al usuario en cgroup v2: `StartTransientUnit` del gestor de
  usuario con `PIDs` (adopta procesos vivos en un scope `bb-portero-<clase>-<pid>.scope` con sus topes),
  escribir `cgroup.procs` dentro de lo delegado y `cgroup.freeze`. Cada evento va a `$BLACKBOX_DATA/portero.jsonl`;
  lo que no se pudo medir se escribe `NOT_COLLECTED` (o `UNSUPPORTED` si el sistema no lo ofrece).

Fallo cerrado hacia el comportamiento de antes: si /proc, PSI, el cgroup de `app.slice` o el estado termico no se
pueden leer, no actua y lo declara. Nunca congela un arbol que sostiene `index.lock` (git commit/merge/rebase y su
hook pre-commit) ni actua fuera de `app.slice`. Un arbol que ya corre bajo su scope no se vuelve a congelar.

Uso: `bb portero estado` (solo lectura), `bb portero run --clase suite -- <cmd>` (pide turno a la misma cola y
lanza bajo scope con tope), `bb portero demonio` (lo corre `systemd/bb-portero.service`).

Interruptor `portero` (tools/interruptores.py, DEBT-PORTERO-IGNORA-SU-INTERRUPTOR-01). El demonio relee el modo en
cada vuelta; `decide` sigue pura y solo la capa con efecto (`aplica`) mira el modo:

* `off`: el demonio no lee /proc ni PSI ni mide cgroups y no actua; deja UNA fila `off` al entrar en ese modo.
* `observar`: mide y decide igual que en `actuar`, pero no llama a systemd ni escribe `cgroup.freeze`: registra
  `habria_<accion>` con `"modo": "observar"`, una vez por cambio de motivo (no una fila cada 2 s). Como nada se
  adopta, los arboles nunca pasan a ser nuestros: lo registrado es la primera decision, no la secuencia de `actuar`.
  Contenedores (`--contenedores`): registra `acotaria` sin `docker update`.
* `actuar`: como antes del interruptor; las filas no llevan `modo`.

Cada clase lleva ademas su techo de modo (`Clase.modo`): el modo efectivo de una accion es el mas restrictivo entre el
interruptor y ese techo (`modo_efectivo`). `suite` tiene techo `actuar`; `libreoffice` entra con techo `observar`.

Interruptor `portero_io` (DEBT-PORTERO-IO-MAX-EN-CLASE-SUITE-01, voto de Luis 2026-10-27: opt-in, apagado por defecto).
Gobierna SOLO el tope de disco (`io.max`) de las clases que lo declaran (`Clase.io_*_bps`; hoy solo `suite`), en los
dos sitios donde nace un scope: la adopcion del demonio (`crea_scope`) y `bb portero run` (`systemd-run`):

* `off` (por defecto, y lo ilegible): no deriva dispositivo, no pone propiedades IO, no escribe nada nuevo.
* `observar`: deriva el disco y registra en la fila (`"io"`) lo que habria puesto, con `"puesto": false`.
* `actuar`: pone `IOReadBandwidthMax`/`IOWriteBandwidthMax` sobre el DISCO entero (io.max no se aplica a una
  particion) y lo registra con `"puesto": true`; en la adopcion relee el `io.max` del scope y dice si lo confirmo.

Sin un disco derivable sin ambiguedad (tmpfs, overlay, dm/md/loop, nodo /dev que no cuadra) no se pone tope y la fila
dice `NOT_COLLECTED` con el motivo: un tope sobre el dispositivo equivocado es peor que ninguno.

Interruptor `portero_admision` (FEATURE-ADMISION-TODO-O-NADA-CON-HOLGURA-REAL-01; ausente, ilegible o desconocido vale
`off`). Admision de todo o nada, la idea de la carga de modelos de Athena: una clase entra solo si su tope ENTERO
(`Clase.memory_max_kb`) cabe en lo que app.slice tiene fuera de la memoria que no se recupera sin matar a nadie
(`anon + shmem` de su memory.stat); si no, se niega y la negativa dice los dos numeros, lo necesario y lo disponible.

* `off` (por defecto): no lee nada nuevo y ni `decide` ni las filas cambian.
* `observar`: decide igual que `off`; cuando el portero admitiria o descongelaria algo que no cabe, anade una fila
  `habria_negado` con `necesario_kb` y `disponible_kb` (una por cambio de motivo). Sin memory.stat legible la fila dice
  `NOT_COLLECTED` en vez de callar.
* `actuar`: la negativa entra en `decide` como motivo de puerta: la suite que no cabe se congela o sigue congelada.
  Sin medicion no niega (fallo cerrado hacia el comportamiento de antes).

Medido en samples/*.jsonl (tasks/evidence/FEATURE-ADMISION-TODO-O-NADA-CON-HOLGURA-REAL-01/medicion.txt): con la clase
`suite` (20 GiB) negaria el 0.93 % del tiempo (168 de 18 066 muestras sanas, 157 sin colapso despues) y vio 2 de 6
colapsos con dato; sobre 1168 admisiones reales de suite habria negado 10, una de ellas la unica seguida de colapso
(2026-10-21 16:36:27). Sobre la suite del 2026-10-16 no hay veredicto: la serie de ese dia no trae anon ni shmem.
Por ese ruido arranca en `off` y se decide con el registro de `observar`.

Mapa forense (FEATURE-MAPA-DE-MEMORIA-FORENSE-AL-ACTUAR-01): la fila de un `congelar` ejecutado y la de un
`habria_negado` con su medicion llevan `mapa_memoria` (`tools/mapa_memoria.py`, unidades de app.slice con clase, rango,
memory.current, anon/file/shmem, swap y dmem). Se toma con la accion ya decidida y hecha; ninguna otra fila cambia.

Lo unico que el demonio hace fuera de `actuar` es deshacer lo propio: descongela los scopes bb-portero-* que dejo
congelados (lista app.slice, nada mas). Sin eso, pasar a `off` con una suite congelada la dejaria asi para siempre.

`bb portero run` es una peticion EXPLICITA de quien lanza su propio comando, no el demonio actuando sobre un arbol
ajeno: en todo modo lanza el comando bajo su scope con el tope de la clase. Solo la cola cambia: en `actuar` espera
turno; en `observar` decide una vez, registra `habria_esperar` si le habria tocado esperar y lanza sin esperar (y
siempre en app.slice, nunca `mover`); en `off` no entra a la cola. El modo ilegible o desconocido vale `off`.

Limites declarados: la memoria ya cargada NO se mueve con el proceso en cgroup v2 (mover sirve al arrancar, no al
final); la deteccion tiene la latencia del intervalo; congelar un `git push` hace correr su `timeout`.
"""

from __future__ import annotations

import argparse
import fcntl
import importlib
import json
import os
import re
import stat
import subprocess
import sys
import time
from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterable

try:
    from tools import interruptores, mapa_memoria
except ImportError:  # como script de `bb portero` (tools/ en sys.path, no la raiz del repo)
    import interruptores
    import mapa_memoria

NOMBRE = "portero"  # su clave en interruptores.json
NOMBRE_IO = "portero_io"  # clave del tope de disco (io.max), opt-in: ausente o ilegible vale `off`
NOMBRE_ADMISION = "portero_admision"  # clave de la admision de todo o nada: ausente o ilegible vale `off`
KIB = 1024
GIB_KB = 1024 * 1024  # 1 GiB expresado en kB

# --- Constantes, cada una con su medicion --------------------------------------------------------------------
#
# Gate de PSI: `full avg10 < 5` es el corte que fija el diseno de la ficha. Medido en las 21 713 muestras de
# `samples/*.jsonl` (2026-09-27..2026-10-12) que traen `app.slice` y PSI: 62 tienen full >= 5 (0.29 %), asi que
# en operacion sana la puerta casi nunca esta cerrada por PSI.
PSI_FULL_MAX = 5.0
# Holgura minima de app.slice para dar turno: con el tope de 42 GiB, 4 GiB deja el slice por debajo de 38 GiB.
# Medido en las mismas muestras: por debajo de 38 GiB, PSI full >= 5 en 45 de 20 445 (0.22 %); entre 38 y 40,
# 16 de 1 267 (1.26 %, 5.7x); por encima de 40, 1 de 1. El codo esta en 38.
HOLGURA_MIN_KB = 4 * GIB_KB
# Un arbol con forma de suite se trata como pesado cuando su RSS sumado pasa el p95 del RSS de un proceso python
# dentro de un scope de sesion Claude: 4 873 628 kB (n=6 895, p50 3.07 GiB, p99 7.09 GiB, max 34.3 GiB -- el
# del colapso). `top_rss` guarda solo los mayores de cada muestra, asi que el p95 esta sesgado hacia arriba:
# se detecta tarde, no de mas.
UMBRAL_RSS_SUITE_KB = 4_873_628
CONTENEDORES_CADA = 30  # vueltas del demonio entre lecturas de docker (60 s): un contenedor nuevo no crece en segundos como una suite
INTERVALO_S = 2.0  # la ficha pide leer /proc cada 1-2 s; 2 s acota la latencia de deteccion declarada


@dataclass(frozen=True)
class Clase:
    """Topes de un trabajo de la clase y cuantos corren a la vez (turnos)."""

    memory_max_kb: int
    memory_high_kb: int
    tasks_max: int
    turnos: int
    umbral_rss_kb: int
    # Techo del modo para esta clase: el efectivo es el mas restrictivo entre el interruptor `portero` y este campo
    # (`modo_efectivo`). `suite` queda en `actuar` (solo manda el interruptor, como antes); una clase nueva entra en
    # `observar` hasta que su registro justifique `actuar` (voto de Luis 2026-10-17).
    modo: str = "actuar"
    # Tope de disco en bytes/s (base 1000, como systemd), o None = la clase no lleva io.max. Solo se pone con el
    # interruptor `portero_io` en `actuar` (ver docstring del modulo).
    io_read_bps: int | None = None
    io_write_bps: int | None = None


# Tope de disco de `suite`: PROVISIONAL, SIN CALIBRAR (DEBT-PORTERO-IO-MAX-EN-CLASE-SUITE-01). Lo unico medido
# (2026-10-27, nvme0n1, planificador `none`): `dd oflag=direct` de 1 GiB dio 4.0 GB/s sin tope y 509 MB/s con
# IOWriteBandwidthMax=500M. Escritura 1 GB/s es la cuarta parte de lo medido sin tope; lectura 2 GB/s no tiene
# medicion propia. Se calibran con el io_some y la duracion del pre-push medidos con `portero_io=actuar`.
IO_SUITE_READ_BPS = 2_000_000_000
IO_SUITE_WRITE_BPS = 1_000_000_000


# Clase `suite` (pytest, hooks pre-push/pre-commit). MemoryMax=20G con swap 0 y MemoryHigh al 90 % es el tope que
# fija la ficha (propuesto por la sesion de proyecto-D; supera el p99 de 7.09 GiB de un python de sesion y queda por
# debajo de los 26-34 GiB del colapso). turnos=1: con una sola suite no hubo colapso (pushes de proyecto-A de 19:40,
# 20:20 y 21:00 del 11-oct); los dos colapsos coincidieron con dos o mas. TasksMax=1230 es `pids.peak` de
# app.slice en este arranque (medido 2026-10-12): una suite no puede tener mas tareas que el slice entero tuvo.
CLASES: dict[str, Clase] = {
    "suite": Clase(
        memory_max_kb=20 * GIB_KB,
        memory_high_kb=18 * GIB_KB,
        tasks_max=1230,
        turnos=1,
        umbral_rss_kb=UMBRAL_RSS_SUITE_KB,
        io_read_bps=IO_SUITE_READ_BPS,
        io_write_bps=IO_SUITE_WRITE_BPS,
    ),
    # Clase `libreoffice` (DEBT-PORTERO-NO-CLASIFICA-TANDAS-DE-LIBREOFFICE-DE-OTROS-PROYECTOS-01): una conversion
    # `soffice --headless --convert-to` es un arbol oosplash -> soffice.bin. Medido 2026-10-17 en /proc sobre una tanda
    # viva de otro proyecto (30 s, 116 muestras): 545 pids distintos, hasta 10 soffice.bin a la vez, RSS de un
    # soffice.bin <= 236 220 kB, suma de la tanda <= 1 916 156 kB, cada conversion vive ~1 s (p50 1.04 s, max 1.57 s);
    # hilos de un soffice.bin <= 4 (427 lecturas en 10 s). MemoryMax 1 GiB es 4.4x el mayor medido, MemoryHigh al
    # 90 % como `suite`; TasksMax 64 es 16x los hilos medidos. umbral 0: el riesgo es cuantas corren a la vez, no una
    # pesada (ninguna se acerca al umbral de `suite`). turnos=1: la ficha pide admitirlas de una en una. 20 + 1 GiB
    # caben en el app.slice de 42 GiB (`presupuesto_desbordado`). Entra en `observar`: no congela ni adopta nada.
    "libreoffice": Clase(
        memory_max_kb=GIB_KB,
        memory_high_kb=GIB_KB * 9 // 10,
        tasks_max=64,
        turnos=1,
        umbral_rss_kb=0,
        modo="observar",
    ),
}


def modo_efectivo(modo_global: str, clase: str | None, clases: dict[str, Clase] | None = None) -> str:
    """El mas restrictivo (off < observar < actuar) entre el interruptor y el techo de la clase; sin clase, el global."""
    c = (CLASES if clases is None else clases).get(clase or "")
    if c is None or modo_global not in interruptores.MODOS or c.modo not in interruptores.MODOS:
        return modo_global
    return min(modo_global, c.modo, key=interruptores.MODOS.index)

PREFIJO_UNIDAD = "bb-portero-"


# --- Modelo -------------------------------------------------------------------------------------------------


@dataclass(frozen=True)
class Arbol:
    """Un arbol de procesos observado. `ancestros` son las lineas de comando de la raiz y de sus ancestros."""

    raiz: int
    clase: str | None
    rss_kb: int
    procesos: int
    edad_s: float
    cgroup: str
    ancestros: tuple[str, ...] = ()
    unidad: str | None = None  # scope bb-portero-* donde ya vive (None si aun no es nuestro)
    congelado: bool = False
    virtual: bool = False  # peticion de `bb portero run` que aun no lanzo su comando
    pids: tuple[int, ...] = ()
    tope_propio_kb: int | None = None  # memory.max finito mas estricto de su cgroup bajo app.slice (None = max)
    inicio: int | None = None  # ticks de arranque de la raiz: distingue la raiz observada de un pid reusado

    @property
    def nuestro(self) -> bool:
        return self.unidad is not None


@dataclass(frozen=True)
class SliceAlterno:
    nombre: str
    tope_kb: int
    comprometido_kb: int  # suma de MemoryMax de los trabajos ya puestos ahi


@dataclass(frozen=True)
class Estado:
    """Lo medido de la maquina. `None` = NOT_COLLECTED. `freno_termico` es "" si admite carga, el motivo si frena."""

    psi_full_avg10: float | None
    freno_termico: str | None
    tope_app_kb: int | None
    uso_app_kb: int | None
    alternos: tuple[SliceAlterno, ...] = ()
    consumo_con_tope_propio_kb: int = 0  # memory.current de los scopes de app.slice con tope propio (jobs de Atlas, bb cap)
    admision: str = "off"  # interruptor `portero_admision`
    no_recuperable_app_kb: int | None = None  # anon + shmem de app.slice (memory.stat); None = NOT_COLLECTED

    @property
    def holgura_app_kb(self) -> int | None:
        if self.tope_app_kb is None or self.uso_app_kb is None:
            return None
        return self.tope_app_kb - self.uso_app_kb


@dataclass(frozen=True)
class Accion:
    tipo: str  # admitir | congelar | descongelar | mover | esperar | no_actua
    motivo: str
    raiz: int | None = None
    clase: str | None = None
    slice: str = "app.slice"
    topes: dict[str, int] = field(default_factory=dict)
    objetivo: str = ""  # contenedor, cuando la accion es `acotar`


# --- Clasificacion (pura) -----------------------------------------------------------------------------------

GIT_BLOQUEA_INDICE = {"commit", "merge", "rebase", "cherry-pick", "revert", "am"}


def _subcomando_git(argv: list[str]) -> str | None:
    if not argv or Path(argv[0]).name != "git":
        return None
    i = 1
    while i < len(argv):
        a = argv[i]
        if a in ("-C", "-c", "--git-dir", "--work-tree", "--namespace"):
            i += 2
            continue
        if a.startswith("-"):
            i += 1
            continue
        return a
    return None


def _marca_hook(argv: list[str], hook: str) -> bool:
    """El proceso es (o ejecuta) el hook de git `hook`: por ruta `.../hooks/<hook>` o por `--hook[-stage] <hook>`."""
    for i, a in enumerate(argv):
        if a.endswith("hooks/" + hook):
            return True
        if a in ("--hook", "--hook-stage", "--hook-type") and i + 1 < len(argv) and argv[i + 1] == hook:
            return True
        if a in (f"--hook={hook}", f"--hook-stage={hook}", f"--hook-type={hook}"):
            return True
    return False


LIBREOFFICE_EJECUTABLES = ("soffice", "soffice.bin", "oosplash")


def clasifica(argv: list[str]) -> str | None:
    """Clase por la FORMA del comando, no por el nombre del repo: pytest o un hook pre-push/pre-commit -> suite;
    soffice/soffice.bin/oosplash (o un shell que lo lanza) con --headless y --convert-to -> libreoffice."""
    for i, a in enumerate(argv):
        base = Path(a).name
        if base in ("pytest", "py.test") or (a == "-m" and i + 1 < len(argv) and argv[i + 1] == "pytest"):
            return "suite"
    if _marca_hook(argv, "pre-push") or _marca_hook(argv, "pre-commit"):
        return "suite"
    if any(Path(a).name in LIBREOFFICE_EJECUTABLES for a in argv[:2]) and "--headless" in argv and "--convert-to" in argv:
        return "libreoffice"
    return None


def sostiene_index_lock(ancestros: Iterable[str]) -> bool:
    """Algun ancestro (o la raiz) es git commit/merge/rebase... o su hook pre-commit: congelarlo deja `index.lock`."""
    for linea in ancestros:
        argv = linea.split("\0") if "\0" in linea else linea.split()
        if _subcomando_git(argv) in GIT_BLOQUEA_INDICE:
            return True
        if _marca_hook(argv, "pre-commit") or _marca_hook(argv, "pre-merge-commit"):
            return True
    return False


def en_app_slice(cgroup: str) -> bool:
    return "/app.slice/" in cgroup and "/user@" in cgroup


# Exclusion explicita (regla del coordinador, 2026-10-12, por choque confirmado con la cola de Atlas): cada job de
# Atlas corre en su propio `systemd-run --scope` con MemoryMax (`liberation_job.scope` y variantes). Moverlo lo
# sacaria de ese tope. Docker no se cerca: crea su propio cgroup y queda fuera de app.slice.
EXCLUIDOS_CGROUP = re.compile(r"/(liberation_job[^/]*\.scope|docker[^/]*\.scope|bb-cap-[^/]*\.scope)(/|$)")
EXCLUIDOS_ANCESTRO = ("liberation_watchdog",)


def excluido(a: "Arbol", c: "Clase") -> str:
    """Motivo por el que el portero NO toca este arbol aunque sea pesado; '' si es candidato."""
    if EXCLUIDOS_CGROUP.search(a.cgroup):
        return f"excluido: cgroup con dueno propio ({a.cgroup})"
    if any(x in linea for linea in a.ancestros for x in EXCLUIDOS_ANCESTRO):
        return "excluido: ancestro del watchdog de Atlas"
    if a.tope_propio_kb is not None and a.tope_propio_kb <= c.memory_max_kb:
        return f"no actua: ya tiene tope propio (memory.max {a.tope_propio_kb} kB <= {c.memory_max_kb} kB de la clase)"
    return ""


# --- Decision (pura) ----------------------------------------------------------------------------------------


def presupuesto_desbordado(tope_slice_kb: int, clases: dict[str, Clase]) -> str:
    """'' si slice -> clase -> trabajo cabe; el motivo si no. Suma de (turnos x MemoryMax) <= tope del slice."""
    total = 0
    for nombre, c in clases.items():
        if c.memory_high_kb > c.memory_max_kb:
            return f"clase {nombre}: MemoryHigh {c.memory_high_kb} kB > MemoryMax {c.memory_max_kb} kB"
        if c.turnos < 1 or c.memory_max_kb <= 0:
            return f"clase {nombre}: turnos o MemoryMax no positivos"
        total += c.turnos * c.memory_max_kb
    if total > tope_slice_kb:
        return f"presupuesto desbordado: las clases comprometen {total} kB sobre un tope de app.slice de {tope_slice_kb} kB"
    return ""


def _topes(c: Clase) -> dict[str, int]:
    return {"MemoryMax": c.memory_max_kb * KIB, "MemoryHigh": c.memory_high_kb * KIB, "MemorySwapMax": 0, "TasksMax": c.tasks_max}


def _no_medido(arboles: list[Arbol] | None, e: Estado) -> list[str]:
    faltan = []
    if arboles is None:
        faltan.append("/proc")
    if e.psi_full_avg10 is None:
        faltan.append("PSI memory")
    if e.freno_termico is None:
        faltan.append("estado termico")
    if e.tope_app_kb is None or e.uso_app_kb is None:
        faltan.append("cgroup de app.slice")
    return faltan


def _puerta(e: Estado) -> str:
    """'' si se puede dar turno; el motivo si no."""
    if e.psi_full_avg10 is not None and e.psi_full_avg10 >= PSI_FULL_MAX:
        return f"PSI memory full avg10={e.psi_full_avg10} >= {PSI_FULL_MAX}"
    if e.freno_termico:
        return f"freno termico: {e.freno_termico}"
    h = e.holgura_app_kb
    if h is not None and h < HOLGURA_MIN_KB:
        return f"holgura de app.slice {h} kB < {HOLGURA_MIN_KB} kB"
    return ""


def admision_niega(e: Estado, c: Clase) -> tuple[int, int] | None:
    """(necesario_kb, disponible_kb) si el tope entero de la clase no cabe fuera de anon+shmem de app.slice; None si
    cabe o si no se midio (sin medicion no se niega)."""
    if e.tope_app_kb is None or e.no_recuperable_app_kb is None:
        return None
    disponible = e.tope_app_kb - e.no_recuperable_app_kb
    return (c.memory_max_kb, disponible) if disponible < c.memory_max_kb else None


def motivo_admision(necesario_kb: int, disponible_kb: int) -> str:
    return (f"holgura real de app.slice (todo o nada): la clase necesita {necesario_kb} kB y fuera de anon+shmem "
            f"hay {disponible_kb} kB")


def _alterno_que_cabe(e: Estado, c: Clase) -> SliceAlterno | None:
    for s in e.alternos:
        if s.comprometido_kb + c.memory_max_kb <= s.tope_kb:
            return s
    return None


def _candidatos(propios: list[Arbol], c: Clase, nombre: str, acciones: list[Accion]) -> list[Arbol]:
    """Los que compiten por turno, del mas antiguo al mas nuevo. Anota en `acciones` los que no se tocan y por que."""
    pendientes: list[Arbol] = []
    for a in propios:
        if a.nuestro and not a.congelado:
            continue  # ya admitido: no se vuelve a congelar
        if a.virtual or a.nuestro:
            pendientes.append(a)
            continue
        if a.rss_kb < c.umbral_rss_kb:
            continue  # aun no es pesado
        fuera = f"fuera de app.slice ({a.cgroup})" if not en_app_slice(a.cgroup) else excluido(a, c)
        if fuera:
            acciones.append(Accion("no_actua", fuera, a.raiz, nombre))
            continue
        pendientes.append(a)
    return sorted(pendientes, key=lambda a: (-a.edad_s, a.raiz))  # FIFO: el mas antiguo primero


def _sin_turno(a: Arbol, motivo: str, c: Clase, nombre: str) -> Accion:
    if a.congelado or a.virtual:
        return Accion("esperar", motivo, a.raiz, nombre)
    if sostiene_index_lock(a.ancestros):
        return Accion("admitir", f"{motivo}; sostiene index.lock: no se congela, solo se le pone tope", a.raiz, nombre, topes=_topes(c))
    return Accion("congelar", motivo, a.raiz, nombre, topes=_topes(c))


def _decide_clase(arboles: list[Arbol], estado: Estado, nombre: str, c: Clase, puerta: str) -> list[Accion]:
    assert estado.tope_app_kb is not None
    acciones: list[Accion] = []
    propios = [a for a in arboles if a.clase == nombre]
    corriendo = sum(1 for a in propios if a.nuestro and not a.congelado)
    libres = c.turnos - corriendo
    comprometido = estado.consumo_con_tope_propio_kb + corriendo * c.memory_max_kb
    for a in _candidatos(propios, c, nombre, acciones):
        motivo = puerta
        if not motivo and estado.admision == "actuar" and (niega := admision_niega(estado, c)):
            motivo = motivo_admision(*niega)
        if not motivo and comprometido + c.memory_max_kb > estado.tope_app_kb:
            motivo = (f"presupuesto: {comprometido} kB comprometidos (scopes con tope propio + admitidos) + "
                      f"{c.memory_max_kb} kB > tope de app.slice {estado.tope_app_kb} kB")
        if libres > 0 and not motivo:
            comprometido += c.memory_max_kb
            libres -= 1
            tipo = "descongelar" if a.nuestro else "admitir"
            acciones.append(Accion(tipo, "turno libre y puerta abierta", a.raiz, nombre, topes=_topes(c)))
            continue
        alterno = _alterno_que_cabe(estado, c) if motivo.startswith(("holgura", "presupuesto")) and not a.nuestro else None
        if libres > 0 and alterno is not None:
            libres -= 1
            acciones.append(Accion("mover", f"{motivo}; {alterno.nombre} tiene holgura", a.raiz, nombre, alterno.nombre, _topes(c)))
            continue
        acciones.append(_sin_turno(a, motivo or f"sin turno: {corriendo} de {c.turnos} ocupados", c, nombre))
    return acciones


def decide(arboles: list[Arbol] | None, estado: Estado, clases: dict[str, Clase] | None = None) -> list[Accion]:
    """Acciones para lo observado. Sin I/O: todo lo que necesita llega por argumento."""
    clases = CLASES if clases is None else clases
    faltan = _no_medido(arboles, estado)
    if faltan:
        return [Accion("no_actua", "NOT_COLLECTED: " + ", ".join(faltan) + "; sin medir no se decide")]
    assert arboles is not None and estado.tope_app_kb is not None  # garantizado por _no_medido
    desborde = presupuesto_desbordado(estado.tope_app_kb, clases)
    if desborde:
        return [Accion("no_actua", desborde)]
    puerta = _puerta(estado)
    return [ac for nombre, c in clases.items() for ac in _decide_clase(arboles, estado, nombre, c, puerta)]


# --- Efecto: medir ------------------------------------------------------------------------------------------

DATOS = Path(os.environ.get("BLACKBOX_DATA", Path.home() / ".local/share/blackbox"))
LOG = DATOS / "portero.jsonl"
# Tope por generacion del log; `_registra` guarda la viva y UNA anterior (`.1`), asi que en disco son <= 2x esto.
# Medido 2026-10-17 (DEBT-PORTERO-LOG-SIN-ROTACION-CON-OBSERVAR-DE-LIBREOFFICE-01): la clase libreoffice en observar
# escribe 3.4 kB/s mientras corre un lote (una generacion = ~41 min de lote continuo, dos = ~82 min); fuera de lotes
# el log crecio 2.53 MB en 5.6 dias (12 al 18-oct), ~450 kB/dia: una generacion = ~18 dias. El unico lector en codigo,
# `bb portero estado`, muestra los ultimos 10 eventos y lee tambien `.1`.
LOG_TOPE_BYTES = 8 * 1024 * 1024
COLA = DATOS / "portero_cola"
CGROUP_RAIZ = Path("/sys/fs/cgroup")
NOMBRE_UNIDAD = re.compile(r"^bb-portero-([a-z]+)-(\d+)\.scope$")


def _lee(p: Path) -> str | None:
    try:
        return p.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None


def lee_psi(ruta: Path = Path("/proc/pressure/memory")) -> float | None:
    texto = _lee(ruta)
    m = re.search(r"^full avg10=([0-9.]+)", texto or "", re.M)
    return float(m.group(1)) if m else None


def cgroup_app(uid: int | None = None, raiz: Path = CGROUP_RAIZ) -> Path:
    uid = os.getuid() if uid is None else uid
    return raiz / f"user.slice/user-{uid}.slice/user@{uid}.service/app.slice"


def lee_slice(d: Path) -> tuple[int | None, int | None]:
    """(tope_kb, uso_kb) de un cgroup; None si no se puede leer o el tope es `max` (sin tope no hay holgura)."""
    tope, uso = _lee(d / "memory.max"), _lee(d / "memory.current")
    if tope is None or uso is None or not tope.strip().isdigit() or not uso.strip().isdigit():
        return None, None
    # memoria de trabajo: la cache de archivos inactiva se recupera sin costo y no es presion (medido 2026-10-17:
    # 15.6 GiB de 38.7 en app.slice; contarla daba una holgura de 3.3 GiB cuando habia 19 reales)
    return int(tope) // KIB, max(0, int(uso) - _inactive_file_bytes(d)) // KIB


def _inactive_file_bytes(d: Path) -> int:
    for linea in (_lee(d / "memory.stat") or "").splitlines():
        campo, _, valor = linea.partition(" ")
        if campo == "inactive_file" and valor.strip().isdigit():
            return int(valor)
    return 0


def lee_no_recuperable_kb(d: Path) -> int | None:
    """anon + shmem del memory.stat de `d` en kB: lo que no se recupera soltando cache. None si falta alguno."""
    campos: dict[str, int] = {}
    for linea in (_lee(d / "memory.stat") or "").splitlines():
        campo, _, valor = linea.partition(" ")
        if campo in ("anon", "shmem") and valor.strip().isdigit():
            campos[campo] = int(valor)
    return (campos["anon"] + campos["shmem"]) // KIB if len(campos) == 2 else None


def tope_propio_kb(cg: str, cg_raiz: Path = CGROUP_RAIZ) -> int | None:
    """El memory.max finito mas estricto entre el cgroup del proceso y app.slice (exclusivo). None = sin tope propio."""
    partes = cg.strip("/").split("/")
    if "app.slice" not in partes:
        return None
    base = partes.index("app.slice")
    topes = []
    for i in range(len(partes), base + 1, -1):
        t = (_lee(cg_raiz.joinpath(*partes[:i]) / "memory.max") or "").strip()
        if t.isdigit():
            topes.append(int(t) // KIB)
    return min(topes) if topes else None


def consumo_con_tope_propio_kb(app: Path) -> int | None:
    """Suma de memory.current de los cgroups de app.slice con memory.max finito (el mas alto de cada rama), sin los
    scopes del portero. Es lo que ya esta comprometido fuera de su cola: jobs de Atlas, `bb cap`. None si no se lee."""
    total = 0
    try:
        pila = [d for d in app.iterdir() if d.is_dir()]
    except OSError:
        return None
    while pila:
        d = pila.pop()
        if NOMBRE_UNIDAD.match(d.name):
            continue
        tope, uso = (_lee(d / "memory.max") or "").strip(), (_lee(d / "memory.current") or "").strip()
        if tope.isdigit() and uso.isdigit():
            total += int(uso) // KIB
            continue
        try:
            pila.extend(x for x in d.iterdir() if x.is_dir())
        except OSError:
            continue
    return total


def freno_termico() -> str | None:
    """'' si admite carga; el motivo si frena; None si no se sabe (archivo ausente, viejo o `desconocido`).

    Consulta lo mismo que `atom_gpu_telemetry.py --gate-termico` (una sola fuente para los umbrales), pero separa
    'no se sabe' de 'frena': el gate de Atlas bloquea ante la duda; el portero, ante la duda, no actua.
    """
    # Como modulo (`tools.`) o como script de `bb portero` (tools/ en sys.path).
    for modulo in ("tools.atom_gpu_telemetry", "atom_gpu_telemetry"):
        try:
            agt = importlib.import_module(modulo)
            break
        except ImportError:
            continue
    else:
        return None
    try:
        d = json.loads(agt.ESTADO_TERMICO_PATH.read_text(encoding="utf-8"))
        edad = (datetime.now(timezone.utc) - datetime.fromisoformat(d["actualizado"])).total_seconds()
        estado = d["estado"]
    except (OSError, ValueError, KeyError, TypeError):
        return None
    if edad > agt.ESTADO_TERMICO_LATIDO_S or estado == "desconocido":
        return None
    if estado != "normal":
        return f"estado termico '{estado}'"
    return agt.presupuesto_termico(agt.leer_zonas(), agt.leer_umbrales())


def lee_estado() -> Estado:
    app = cgroup_app()
    tope, uso = lee_slice(app)
    consumo = consumo_con_tope_propio_kb(app)
    if consumo is None:
        tope = None  # sin saber lo comprometido fuera de la cola no se puede cuadrar el presupuesto: NOT_COLLECTED
    admision = interruptores.modo(NOMBRE_ADMISION)
    return Estado(psi_full_avg10=lee_psi(), freno_termico=freno_termico(), tope_app_kb=tope, uso_app_kb=uso,
                  consumo_con_tope_propio_kb=consumo or 0, admision=admision,
                  no_recuperable_app_kb=lee_no_recuperable_kb(app) if admision != "off" else None)


@dataclass
class _Proc:
    pid: int
    ppid: int
    inicio: int  # ticks desde el arranque
    argv: list[str]
    cgroup: str
    rss_kb: int


def _lee_proc(d: Path) -> _Proc | None:
    stat = _lee(d / "stat")
    if not stat:
        return None
    try:
        resto = stat[stat.rindex(")") + 2 :].split()
        ppid, inicio = int(resto[1]), int(resto[19])
    except (ValueError, IndexError):
        return None
    crudo = _lee(d / "cmdline") or ""
    argv = [a for a in crudo.split("\0") if a]
    cg = (_lee(d / "cgroup") or "").strip()
    cg = cg.split("::", 1)[1] if cg.startswith("0::") else cg
    m = re.search(r"^VmRSS:\s+(\d+)", _lee(d / "status") or "", re.M)
    return _Proc(int(d.name), ppid, inicio, argv, cg, int(m.group(1)) if m else 0)


def _congelado(unidad_cg: Path) -> bool:
    return "frozen 1" in (_lee(unidad_cg / "cgroup.events") or "")


@dataclass
class _Tabla:
    """Foto de /proc de los procesos del usuario: quien es hijo de quien, para armar arboles."""

    procs: dict[int, _Proc]
    uptime: float
    hz: int
    hijos: dict[int, list[int]] = field(default_factory=dict)

    @classmethod
    def lee(cls, proc: Path = Path("/proc")) -> _Tabla | None:
        try:
            dirs = [d for d in proc.iterdir() if d.name.isdigit()]
            uptime = float((proc / "uptime").read_text(encoding="utf-8").split()[0])
        except (OSError, ValueError, IndexError):
            return None
        uid = os.getuid()
        procs: dict[int, _Proc] = {}
        for d in dirs:
            try:
                propio = d.stat().st_uid == uid
            except OSError:
                continue
            p = _lee_proc(d) if propio else None
            if p is not None:
                procs[p.pid] = p
        t = cls(procs, uptime, os.sysconf("SC_CLK_TCK"))
        for p in procs.values():
            t.hijos.setdefault(p.ppid, []).append(p.pid)
        return t

    def descendientes(self, pid: int) -> list[int]:
        out, pila = [], [pid]
        while pila:
            x = pila.pop()
            out.append(x)
            pila.extend(self.hijos.get(x, []))
        return [x for x in out if x in self.procs]

    def ancestros(self, pid: int) -> tuple[str, ...]:
        out, x, vistos = [], pid, set()
        while x in self.procs and x not in vistos:
            vistos.add(x)
            out.append(" ".join(self.procs[x].argv))
            x = self.procs[x].ppid
        return tuple(out)

    def edad(self, p: _Proc) -> float:
        return max(0.0, self.uptime - p.inicio / self.hz)


def _arboles_nuestros(t: _Tabla, cg_raiz: Path) -> list[Arbol]:
    """Un arbol por scope bb-portero-* (lo que corre dentro, aunque la forma haya cambiado)."""
    por_unidad: dict[str, list[_Proc]] = {}
    for p in t.procs.values():
        if NOMBRE_UNIDAD.match(Path(p.cgroup).name):
            por_unidad.setdefault(p.cgroup, []).append(p)
    out = []
    for cg, miembros in por_unidad.items():
        m = NOMBRE_UNIDAD.match(Path(cg).name)
        assert m is not None
        raiz = min(miembros, key=lambda p: (p.inicio, p.pid))
        out.append(Arbol(
            raiz=raiz.pid, clase=m.group(1), rss_kb=sum(p.rss_kb for p in miembros), procesos=len(miembros),
            edad_s=t.edad(raiz), cgroup=cg, ancestros=t.ancestros(raiz.pid), unidad=Path(cg).name,
            congelado=_congelado(cg_raiz / cg.lstrip("/")), pids=tuple(sorted(p.pid for p in miembros)), inicio=raiz.inicio,
        ))
    return out


def _arboles_por_forma(t: _Tabla, cg_raiz: Path) -> list[Arbol]:
    """Arboles con forma de clase que aun no son nuestros: la raiz es el ancestro mas alto con la misma forma."""
    clase_de = {pid: clasifica(p.argv) for pid, p in t.procs.items()}
    out = []
    for pid, p in t.procs.items():
        c = clase_de[pid]
        if c is None or NOMBRE_UNIDAD.match(Path(p.cgroup).name) or clase_de.get(p.ppid) == c:
            continue  # sin forma, ya nuestro, o no es raiz (su padre tiene la misma forma)
        miembros = [t.procs[x] for x in t.descendientes(pid)]
        out.append(Arbol(
            raiz=pid, clase=c, rss_kb=sum(m.rss_kb for m in miembros), procesos=len(miembros), edad_s=t.edad(p),
            cgroup=p.cgroup, ancestros=t.ancestros(pid), pids=tuple(sorted(m.pid for m in miembros)),
            tope_propio_kb=tope_propio_kb(p.cgroup, cg_raiz), inicio=p.inicio,
        ))
    return out


def observar(proc: Path = Path("/proc"), cg_raiz: Path = CGROUP_RAIZ, cola: Path | None = None) -> list[Arbol] | None:
    """Arboles de trabajo: scopes bb-portero-*, arboles con forma de clase y peticiones de `run`. None si /proc no se lee."""
    t = _Tabla.lee(proc)
    if t is None:
        return None
    return _arboles_nuestros(t, cg_raiz) + _arboles_por_forma(t, cg_raiz) + _peticiones(t.procs, time.time(), cola)


def _peticiones(procs: dict[int, Any], ahora: float, cola: Path | None = None) -> list[Arbol]:
    """Peticiones de `bb portero run` aun vivas: entran a la misma cola FIFO como arboles virtuales."""
    cola = cola or COLA
    out = []
    try:
        archivos = sorted(cola.glob("*.json"))
    except OSError:
        return out
    for f in archivos:
        try:
            d = json.loads(f.read_text(encoding="utf-8"))
            pid, clase, ts = int(d["pid"]), str(d["clase"]), float(d["ts"])
        except (OSError, ValueError, KeyError, TypeError) as e:
            print(f"[portero] peticion ilegible {f.name}, no entra a la cola: {e}", file=sys.stderr)
            continue
        if pid not in procs:
            continue  # el que pedia turno ya no existe
        concedido = bool(d.get("concedido"))
        out.append(
            Arbol(
                raiz=pid,
                clase=clase,
                rss_kb=0,
                procesos=0,
                edad_s=max(0.0, ahora - ts),
                cgroup="",
                unidad="(concedido)" if concedido else None,
                virtual=not concedido,
            )
        )
    return out


# --- Efecto: actuar -----------------------------------------------------------------------------------------

Ejecutor = Callable[[list[str]], tuple[int, str]]
Origen = Callable[[int], dict[str, Any]]


def _ejecuta(args: list[str]) -> tuple[int, str]:
    try:
        r = subprocess.run(args, capture_output=True, text=True, timeout=15, check=False)
    except (OSError, subprocess.TimeoutExpired) as e:
        return 127, str(e)
    return r.returncode, (r.stdout + r.stderr).strip()


def origen_no_integrado(pid: int) -> dict[str, Any]:
    """Costura para `bb origen` (quien lanzo el arbol). Hasta que exista: NOT_COLLECTED, nunca un dato inventado."""
    return {"estado": "NOT_COLLECTED", "motivo": "registro de origen (bb origen) aun no integrado"}


def nombre_unidad(clase: str, raiz: int) -> str:
    return f"{PREFIJO_UNIDAD}{clase}-{raiz}.scope"


@dataclass(frozen=True)
class Disco:
    """Disco entero (no particion) que respalda un sistema de archivos: lo que `io.max` acepta."""

    ruta: str  # nodo en /dev, p. ej. /dev/nvme0n1
    maj_min: str  # p. ej. 259:0, la clave de la linea de io.max


Stat = Callable[[Path], os.stat_result]
MAJ_MIN = re.compile(r"^\d+:\d+$")


def _maj_min(dev: int) -> str:
    return f"{os.major(dev)}:{os.minor(dev)}"


def disco_de(objetivo: Path, sys_raiz: Path = Path("/sys"), dev_raiz: Path = Path("/dev"), stat_: Stat = os.stat) -> Disco | str:
    """El disco entero que respalda `objetivo`, o el motivo por el que no se sabe sin ambiguedad (solo lectura).

    st_dev del objetivo -> /sys/dev/block/<maj:min> -> si es particion, su padre -> `dev` del disco -> el nodo /dev
    con ese nombre tiene que ser de bloques y con ese mismo maj:min. Dispositivos apilados (dm, md, loop) se rechazan:
    su io.max no es el del disco fisico y elegir uno de sus esclavos seria adivinar."""
    try:
        origen = _maj_min(stat_(objetivo).st_dev)
    except OSError as e:
        return f"stat de {objetivo}: {e}"
    nodo = sys_raiz / "dev" / "block" / origen
    try:
        real = nodo.resolve(strict=True)
    except (OSError, RuntimeError):
        return f"{objetivo} esta en {origen} sin {nodo}: no es un dispositivo de bloques (tmpfs, overlay, btrfs...)"
    disco = real.parent if (real / "partition").exists() else real
    if (disco / "partition").exists():
        return f"{disco} es particion y tambien lo es su hijo {real.name}: no se adivina el disco"
    apilado = [x for x in ("dm", "md", "loop") if (disco / x).exists()]
    try:
        apilado += [f"slaves/{x.name}" for x in (disco / "slaves").iterdir()]
    except OSError:
        pass  # sin directorio slaves: no esta apilado sobre otro
    if apilado:
        return f"{disco.name} es un dispositivo apilado ({', '.join(apilado)}): io.max no se pone sobre el disco fisico"
    maj_min = (_lee(disco / "dev") or "").strip()
    if not MAJ_MIN.match(maj_min):
        return f"{disco / 'dev'} ilegible ({maj_min!r})"
    if disco == real and maj_min != origen:
        return f"{disco / 'dev'} dice {maj_min} y {objetivo} esta en {origen}"
    try:
        vuelta = (sys_raiz / "dev" / "block" / maj_min).resolve(strict=True)
    except (OSError, RuntimeError):
        vuelta = None
    if vuelta != disco:
        return f"/sys/dev/block/{maj_min} no resuelve a {disco} ({vuelta})"
    ruta = dev_raiz / disco.name
    try:
        st = stat_(ruta)
    except OSError as e:
        return f"stat de {ruta}: {e}"
    if not stat.S_ISBLK(st.st_mode) or _maj_min(st.st_rdev) != maj_min:
        return f"{ruta} no es el nodo de bloques {maj_min} (modo {oct(st.st_mode)}, rdev {_maj_min(st.st_rdev)})"
    return Disco(str(ruta), maj_min)


TopesIO = dict[str, tuple[str, int]]  # propiedad systemd -> (dispositivo, bytes/s)


def topes_io(clase: str | None, objetivo: Path, fx: Efectos) -> tuple[TopesIO, dict[str, Any] | None]:
    """(propiedades IO a poner, bloque `io` de la fila) para un scope de `clase` cuyo trabajo escribe en `objetivo`.

    Propiedades solo con `portero_io` efectivo en `actuar`; el bloque es None en `off` o si la clase no declara tope
    (la fila queda como antes del interruptor)."""
    c = CLASES.get(clase or "")
    if c is None or (c.io_read_bps is None and c.io_write_bps is None):
        return {}, None
    modo = modo_efectivo(fx.modo_io, clase)
    if modo not in ("observar", "actuar"):
        return {}, None
    d = disco_de(objetivo, fx.sys_raiz, fx.dev_raiz, fx.stat)
    if isinstance(d, str):
        return {}, {"modo": modo, "estado": "NOT_COLLECTED", "motivo": d, "objetivo": str(objetivo), "puesto": False}
    topes = {k: (d.ruta, v) for k, v in (("IOReadBandwidthMax", c.io_read_bps), ("IOWriteBandwidthMax", c.io_write_bps))
             if v is not None}
    ev = {"modo": modo, "dispositivo": d.ruta, "maj_min": d.maj_min, "objetivo": str(objetivo),
          **{k: v for k, (_, v) in topes.items()}, "puesto": modo == "actuar"}
    return (topes if modo == "actuar" else {}), ev


def confirma_io_max(cg: Path, ev: dict[str, Any]) -> dict[str, Any]:
    """Relee `io.max` del scope recien creado: `confirmado` solo si la linea del disco trae los bytes pedidos."""
    texto = _lee(cg / "io.max")
    if texto is None:
        return {"io_max": "NOT_COLLECTED: io.max ilegible", "confirmado": False}
    linea = next((x for x in texto.splitlines() if x.split(" ", 1)[0] == ev["maj_min"]), "")
    campos = dict(p.split("=", 1) for p in linea.split()[1:] if "=" in p)
    pedido = {"rbps": ev.get("IOReadBandwidthMax"), "wbps": ev.get("IOWriteBandwidthMax")}
    ok = bool(linea) and all(campos.get(k) == str(v) for k, v in pedido.items() if v is not None)
    return {"io_max": texto.strip(), "confirmado": ok}


def crea_scope(nombre: str, pids: Iterable[int], slice_: str, topes: dict[str, int], ejecutar: Ejecutor = _ejecuta,
               io: TopesIO | None = None) -> tuple[int, str]:
    """Adopta procesos vivos en un scope transitorio del gestor de usuario, con sus topes, en una sola llamada."""
    pids_txt = [str(p) for p in pids]
    props: list[str] = ["PIDs", "au", str(len(pids_txt)), *pids_txt, "Slice", "s", slice_]
    for k in ("MemoryMax", "MemoryHigh", "MemorySwapMax", "TasksMax"):
        if k in topes:
            props += [k, "t", str(topes[k])]
    io = io or {}
    for k, (dev, bps) in io.items():
        props += [k, "a(st)", "1", dev, str(bps)]
    n_props = 2 + sum(1 for k in ("MemoryMax", "MemoryHigh", "MemorySwapMax", "TasksMax") if k in topes) + len(io)
    return ejecutar(
        ["busctl", "--user", "call", "org.freedesktop.systemd1", "/org/freedesktop/systemd1",
         "org.freedesktop.systemd1.Manager", "StartTransientUnit", "ssa(sv)a(sa(sv))",
         nombre, "fail", str(n_props), *props, "0"]
    )


def mueve_pid(pid: int, destino_cg: Path) -> str:
    """Escribe el pid en `cgroup.procs` del destino. '' si lo movio; el error si el kernel lo niega."""
    try:
        (destino_cg / "cgroup.procs").write_text(str(pid), encoding="utf-8")
    except OSError as e:
        return f"{type(e).__name__}: {e}"
    return ""


def congela(destino_cg: Path, si: bool) -> str:
    try:
        (destino_cg / "cgroup.freeze").write_text("1" if si else "0", encoding="utf-8")
    except OSError as e:
        return f"{type(e).__name__}: {e}"
    return ""


def _cg_de(pid: int, proc: Path = Path("/proc")) -> str | None:
    t = (_lee(proc / str(pid) / "cgroup") or "").strip()
    return t.split("::", 1)[1] if t.startswith("0::") else None


def raiz_se_fue(a: Arbol, proc: Path = Path("/proc")) -> str:
    """'' si la raiz observada sigue viva; el motivo si salio o su pid ya es otro proceso (otro instante de arranque)."""
    p = _lee_proc(proc / str(a.raiz))
    if p is None:
        return f"la raiz {a.raiz} ya no existe"
    if a.inicio is not None and p.inicio != a.inicio:
        return f"el pid {a.raiz} ya es otro proceso (arranque {p.inicio} != {a.inicio} observado)"
    return ""


def estado_unidad(nombre: str, ejecutar: Ejecutor) -> str:
    """'' si systemd dejo la unidad `active` con `Result=success`; el motivo si no, o si no se pudo leer.

    Medido 2026-10-14 (DEBT-PORTERO-ADOPCION-CHOCA-CON-PIDS-QUE-SALEN-01): con un pid que sale justo despues de la
    llamada, `StartTransientUnit` devuelve rc=0, la raiz SI queda en el cgroup del scope, y aun asi la unidad queda
    `failed` con `Result=resources`. Mirar solo el cgroup de la raiz daba rc=0 falso."""
    rc, txt = ejecutar(["systemctl", "--user", "show", nombre, "-p", "ActiveState", "-p", "Result"])
    props = dict(linea.split("=", 1) for linea in txt.splitlines() if "=" in linea)
    activo, resultado = props.get("ActiveState"), props.get("Result")
    if rc != 0 or activo is None or resultado is None:
        return f"estado de {nombre} NOT_COLLECTED (rc={rc}): {txt[:120]}"
    if (activo, resultado) != ("active", "success"):
        return f"systemd dejo {nombre} en ActiveState={activo} Result={resultado}"
    return ""


def _adopta(a: Arbol, accion: Accion, ejecutar: Ejecutor, cg_raiz: Path, proc: Path = Path("/proc"),
            io: TopesIO | None = None) -> tuple[int, str, Path | None]:
    nombre = nombre_unidad(accion.clase or "x", a.raiz)
    # Un pid que ya salio hace fallar la llamada entera ("No such process"): se pasan solo los que siguen vivos. La
    # raiz va siempre (aplica acaba de comprobarla); si sale ahora, el fallo lo resuelve aplica como `no_actua`.
    pids = sorted({a.raiz, *(p for p in a.pids if (proc / str(p)).is_dir())})
    rc, salida = crea_scope(nombre, pids, accion.slice, accion.topes, ejecutar, io)
    if rc != 0:
        return rc, salida, None
    # StartTransientUnit devuelve un job: la adopcion termina despues. Se espera acotado (medido 2026-10-12 con un
    # scope desechable: el job vuelve antes de que /proc/<pid>/cgroup cambie).
    cg = _cg_de(a.raiz, proc)
    for _ in range(40):
        if cg is None or Path(cg).name == nombre:
            break
        time.sleep(0.05)  # blocking-sleep: espera acotada (2 s) a que systemd complete el job de adopcion -- DEBT-COLAPSOS-11-OCT-SUITES-PYTEST-SIN-TECHO-01
        cg = _cg_de(a.raiz, proc)
    if cg is None or Path(cg).name != nombre:
        return 1, f"{salida}; la raiz no quedo en {nombre} (cgroup {cg})", None
    falla = estado_unidad(nombre, ejecutar)
    if falla:
        return 1, f"{salida}; {falla}", None
    destino = cg_raiz / cg.lstrip("/")
    # Hijos que nacieron entre la observacion y la adopcion: se mueven escribiendo cgroup.procs (dentro de lo delegado).
    errores = [e for p in observar_pids(a.raiz, proc) if _cg_de(p, proc) != cg and (e := mueve_pid(p, destino))]
    return (0 if not errores else 1), "; ".join([salida, *errores[:3]]), destino


def observar_pids(raiz: int, proc: Path = Path("/proc")) -> list[int]:
    t = _Tabla.lee(proc)
    return t.descendientes(raiz) if t else []


def _anterior(log: Path) -> Path:
    """La unica generacion vieja que se guarda del log (`portero.jsonl.1`)."""
    return log.with_name(log.name + ".1")


def _registra(evento: dict[str, Any], log: Path) -> None:
    """Anexa una fila; nunca lanza hacia el demonio. Pasado `LOG_TOPE_BYTES`, el log vivo pasa a `.1` (pisando la
    anterior) con os.replace: un lector ve el archivo viejo entero o el nuevo, y una caida no deja sin log vivo.
    El flock serializa a los escritores (demonio y `bb portero run`): la fila entra entera y solo quien sostiene el
    candado sobre el archivo que sigue en `log` lo rota, asi dos rotaciones a la vez no pisan una generacion."""
    evento = {"ts": datetime.now(timezone.utc).isoformat(), **evento}
    try:
        log.parent.mkdir(parents=True, exist_ok=True)
        for intento in range(3):  # acotado: el demonio no se queda girando si alguien rota sin parar
            with log.open("a", encoding="utf-8") as fh:
                fcntl.flock(fh, fcntl.LOCK_EX)
                try:
                    vivo = os.stat(log).st_ino == os.fstat(fh.fileno()).st_ino
                except FileNotFoundError:
                    vivo = False
                if not vivo and intento < 2:
                    continue  # otro escritor lo roto entre el open y el candado: anexar al archivo nuevo
                fh.write(json.dumps(evento, ensure_ascii=False) + "\n")
                fh.flush()
                if vivo and os.fstat(fh.fileno()).st_size > LOG_TOPE_BYTES:
                    try:
                        os.replace(log, _anterior(log))
                    except OSError as e:
                        print(f"[portero] no se pudo rotar {log}: {e}", file=sys.stderr)
                return
    except OSError as e:
        print(f"[portero] no se pudo escribir {log}: {e}", file=sys.stderr)


def _medicion(estado: Estado) -> dict[str, Any]:
    def v(x: Any) -> Any:
        return "NOT_COLLECTED" if x is None else x

    m = {
        "psi_full_avg10": v(estado.psi_full_avg10),
        "freno_termico": v(estado.freno_termico),
        "tope_app_kb": v(estado.tope_app_kb),
        "uso_app_kb": v(estado.uso_app_kb),
        "consumo_con_tope_propio_kb": estado.consumo_con_tope_propio_kb,
    }
    if estado.admision != "off":  # en `off` la fila queda byte a byte como antes del interruptor
        m.update(admision=estado.admision, no_recuperable_app_kb=v(estado.no_recuperable_app_kb))
    return m


def habria_negado(ac: Accion, estado: Estado, clases: dict[str, Clase] | None = None) -> dict[str, Any] | None:
    """Fila `habria_negado` de `portero_admision` en `observar` para una admision que no cabe; None si no aplica.

    Solo admitir/descongelar en app.slice (mover va a otro slice con su propio presupuesto). Sin la medicion de
    anon+shmem la fila dice NOT_COLLECTED: un `observar` que calla cuando no puede medir no distingue "cabe" de "ciego"."""
    c = (CLASES if clases is None else clases).get(ac.clase or "")
    if estado.admision != "observar" or c is None or ac.tipo not in ("admitir", "descongelar"):
        return None
    base = {"accion": "habria_negado", "interruptor": NOMBRE_ADMISION, "modo": "observar", "raiz": ac.raiz,
            "clase": ac.clase, "decidida": ac.tipo}
    if estado.tope_app_kb is None or estado.no_recuperable_app_kb is None:
        return {**base, "motivo": "NOT_COLLECTED: anon+shmem de app.slice ilegible; sin medir no se sabe si cabe"}
    niega = admision_niega(estado, c)
    if niega is None:
        return None
    return {**base, "motivo": motivo_admision(*niega), "necesario_kb": niega[0], "disponible_kb": niega[1]}


@dataclass(frozen=True)
class Efectos:
    """Donde y con que actua la parte con efecto. Los tests la sustituyen entera."""

    log: Path = LOG
    cola: Path = COLA
    ejecutar: Ejecutor = _ejecuta
    origen: Origen = origen_no_integrado
    cg_raiz: Path = CGROUP_RAIZ
    proc: Path = Path("/proc")
    modo: str = "actuar"  # interruptor `portero`: fuera de `actuar` aplica y turno solo registran (ver docstring)
    modo_io: str = "off"  # interruptor `portero_io`: solo en `actuar` lleva io.max el scope (ver docstring)
    sys_raiz: Path = Path("/sys")
    dev_raiz: Path = Path("/dev")
    stat: Stat = os.stat


def _adopta_y_congela(a: Arbol, ac: Accion, fx: Efectos) -> dict[str, Any]:
    """Campos del evento de una adopcion. La raiz que salio (antes o durante) es `no_actua`, no un fallo."""
    se_fue = raiz_se_fue(a, fx.proc)
    if se_fue:  # salio entre la observacion y ahora: no hay nada que adoptar
        return {"accion": "no_actua", "decidida": ac.tipo, "motivo": f"{se_fue}: no se adopta (decidido: {ac.motivo})"}
    # El disco es el del directorio de trabajo de la raiz (stat sigue el enlace /proc/<pid>/cwd).
    io, io_ev = topes_io(ac.clase, fx.proc / str(a.raiz) / "cwd", fx)
    rc, salida, destino = _adopta(a, ac, fx.ejecutar, fx.cg_raiz, fx.proc, io)
    if io_ev is not None and io:  # `puesto` = iba en la llamada a systemd; `confirmado` = io.max releido lo trae
        io_ev.update(confirma_io_max(destino, io_ev) if destino is not None else {"confirmado": False})
    if rc == 0 and ac.tipo == "congelar" and destino is not None:
        err = congela(destino, True)
        rc, salida = (1, f"{salida}; {err}") if err else (rc, salida)
    ev = {"rc": rc, "salida": salida[:300], "unidad": nombre_unidad(ac.clase or "x", a.raiz), "slice": ac.slice, "topes": ac.topes}
    if io_ev is not None:
        ev["io"] = io_ev
    se_fue = raiz_se_fue(a, fx.proc) if rc != 0 else ""
    if se_fue:  # salio DURANTE la adopcion: el fallo de systemd es por eso, no un fallo del portero
        del ev["rc"]
        ev.update(accion="no_actua", decidida=ac.tipo, motivo=f"{se_fue} durante la adopcion (decidido: {ac.motivo})")
    return ev


def mapa_al_actuar(fx: Efectos, obligatoria: Path | None) -> dict[str, Any]:
    """Mapa forense de las unidades de app.slice (tools/mapa_memoria.py) al congelar o negar. Se pide con la decision
    ya tomada y ejecutada; nunca lanza: un fallo deja NOT_COLLECTED en la fila y nada mas."""
    try:
        return mapa_memoria.captura(mapa_memoria.unidades_de(cgroup_app(raiz=fx.cg_raiz)), mapa_memoria.lee_clases(),
                                    [obligatoria] if obligatoria is not None else ())
    except Exception as exc:  # forense puro: no puede cambiar lo que el portero hizo ni tumbar al demonio
        return {"estado": "NOT_COLLECTED", "motivo": f"{type(exc).__name__}: {exc}"}


def _cg_arbol(fx: Efectos, a: Arbol | None) -> Path | None:
    return fx.cg_raiz / a.cgroup.lstrip("/") if a is not None and a.cgroup else None


def _habria(ac: Accion, modo: str) -> dict[str, Any]:
    """Fuera de `actuar`: el modo, y la accion con efecto renombrada `habria_<accion>` (no se ejecuta nada)."""
    if modo == "actuar":
        return {}
    if ac.tipo in ("esperar", "no_actua"):
        return {"modo": modo}
    return {"modo": modo, "accion": f"habria_{ac.tipo}", "topes": ac.topes, "slice": ac.slice}


def aplica(
    acciones: list[Accion], arboles: list[Arbol], estado: Estado, fx: Efectos | None = None, ultimo: dict[Any, str] | None = None
) -> list[dict[str, Any]]:
    """Ejecuta las acciones con efecto y registra cada una. `esperar`/`no_actua` se registran solo al cambiar.

    Con `fx.modo` fuera de `actuar` (interruptor en `observar`) no ejecuta nada: cada accion con efecto se registra
    como `habria_<accion>` con `modo`, y tambien solo al cambiar su motivo."""
    fx = fx or Efectos()
    log, origen, cg_raiz = fx.log, fx.origen, fx.cg_raiz
    por_raiz = {a.raiz: a for a in arboles}
    ultimo = {} if ultimo is None else ultimo
    eventos = []
    for ac in acciones:
        a = por_raiz.get(ac.raiz) if ac.raiz is not None else None
        modo = modo_efectivo(fx.modo, ac.clase)  # una clase en `observar` no actua aunque el interruptor diga `actuar`
        ev: dict[str, Any] = {"accion": ac.tipo, "motivo": ac.motivo, "raiz": ac.raiz, "clase": ac.clase}
        if a is not None:
            ev.update(rss_kb=a.rss_kb, procesos=a.procesos, edad_s=round(a.edad_s, 1), cgroup=a.cgroup)
        ev.update(_habria(ac, modo))
        if modo != "actuar" or ac.tipo in ("esperar", "no_actua") or (a is not None and a.virtual):
            clave = (ac.raiz, ev["accion"])
            if ultimo.get(clave) == ac.motivo:
                continue
            ultimo[clave] = ac.motivo
        elif a is None:
            ev.update(rc=1, salida="arbol no observado")
        elif ac.tipo in ("admitir", "congelar", "mover"):
            ev.update(_adopta_y_congela(a, ac, fx))
        elif ac.tipo == "descongelar":
            err = congela(cg_raiz / a.cgroup.lstrip("/"), False)
            ev.update(rc=1 if err else 0, salida=err, unidad=a.unidad)
        if ac.raiz is not None:
            ev["origen"] = origen(ac.raiz)
        ev["medicion"] = _medicion(estado)
        if ev["accion"] == "congelar" and a is not None and not a.virtual:  # congelo (o lo intento) de verdad
            ev["mapa_memoria"] = mapa_al_actuar(fx, cgroup_app(raiz=cg_raiz) / ev["unidad"] if ev.get("unidad") else None)
        eventos.append(ev)
        _registra(ev, log)
        neg = habria_negado(ac, estado)
        clase_neg = neg["motivo"].split(":", 1)[0] if neg else ""  # sin los kB, que cambian en cada vuelta
        if neg is not None and ultimo.get((ac.raiz, "habria_negado")) != clase_neg:
            ultimo[(ac.raiz, "habria_negado")] = clase_neg
            neg["medicion"] = ev["medicion"]
            if "necesario_kb" in neg:  # una negativa medida; la fila NOT_COLLECTED no es una accion
                neg["mapa_memoria"] = mapa_al_actuar(fx, _cg_arbol(fx, a))
            eventos.append(neg)
            _registra(neg, log)
    if arboles:  # sin lectura de /proc (lista vacia) no se sabe que murio: se conserva la memoria
        for clave in [c for c in ultimo if c[0] is not None and c[0] not in por_raiz]:
            del ultimo[clave]  # un lote de conversiones de ~1 s dejaba una clave por cada una, sin cota
    return eventos


# --- Contenedores (docker.slice) ---------------------------------------------------------------------------
#
# Medido 2026-10-12 (tasks/evidence/FEATURE-PORTERO-UNIVERSAL-DE-LA-MAQUINA-01/validaciones.md): el daemon de Docker
# usa cgroup-parent=docker.slice (MemoryMax 14 GiB; 16 GiB votado el 2026-10-13, pendiente de desplegar) y `docker update --memory X --memory-swap X` acota un contenedor
# EN VIVO (memory.max de max a X, swap 0). Tres contenedores corren sin tope propio. La memoria GPU NO la ve el cgroup
# (vLLM 33.4 GB de GPU frente a 12.2 GiB de cgroup): esto acota RAM ordinaria, no GPU.
#
# El numero NO es un umbral elegido: sale de restar. Tope de un contenedor sin tope = tope de docker.slice - topes
# propios mas estrictos que el slice - picos medidos (memory.peak) de los demas contenedores sin tope mas estricto. Si ese
# contenedor llega a su tope, lo que los demas ya demostraron necesitar sigue cabiendo. Si el reparto queda por
# debajo de su propio pico, no se acota (lo mataria) y se registra. No lo corre el demonio por defecto: solo
# `bb portero contenedores --aplicar` (o `demonio --contenedores`), porque es una politica sobre servicios.

CONTENEDORES_EXCLUIDOS = ("nemotron-server", "atlas-pgvector")  # ya tienen tope propio (regla del coordinador)


@dataclass(frozen=True)
class Contenedor:
    nombre: str
    tope_kb: int | None  # memory.max de su cgroup; None = max
    pico_kb: int | None  # memory.peak; None = NOT_COLLECTED


def decide_contenedores(conts: list[Contenedor] | None, tope_slice_kb: int | None) -> list[Accion]:
    """Pura. `acotar` los contenedores sin tope cuando el reparto medido cabe sobre su pico; si no, `no_actua`."""
    if conts is None or tope_slice_kb is None:
        return [Accion("no_actua", "NOT_COLLECTED: docker o docker.slice ilegibles; sin medir no se acota")]
    acciones = []
    estrictos = sum(c.tope_kb for c in conts if c.tope_kb is not None and c.tope_kb < tope_slice_kb)
    for c in conts:
        if c.nombre in CONTENEDORES_EXCLUIDOS or c.tope_kb is not None:
            acciones.append(Accion("no_actua", f"ya tiene tope propio ({c.tope_kb} kB) o esta excluido", objetivo=c.nombre))
            continue
        # Los demas cuyo tope no es mas estricto que el slice (sin tope, o con uno mayor, como nemotron-server): su pico
        # medido es lo que necesitan y tiene que seguir cabiendo.
        otros = [o for o in conts if o.nombre != c.nombre and not (o.tope_kb is not None and o.tope_kb < tope_slice_kb)]
        if c.pico_kb is None or any(o.pico_kb is None for o in otros):
            acciones.append(Accion("no_actua", "NOT_COLLECTED: memory.peak ilegible", objetivo=c.nombre))
            continue
        reparto = tope_slice_kb - estrictos - sum(o.pico_kb or 0 for o in otros)
        if reparto < c.pico_kb:
            acciones.append(Accion("no_actua", f"reparto {reparto} kB < su pico {c.pico_kb} kB: acotarlo lo mataria", objetivo=c.nombre))
            continue
        acciones.append(Accion(
            "acotar", f"sin tope; reparto = {tope_slice_kb} slice - {estrictos} topes estrictos - picos de los demas",
            slice="docker.slice", topes={"MemoryMax": reparto * KIB, "MemorySwapMax": 0}, objetivo=c.nombre,
        ))
    return acciones


def _entero_o_none(t: str | None) -> int | None:
    t = (t or "").strip()
    return int(t) // KIB if t.isdigit() else None


def observar_contenedores(ejecutar: Ejecutor = _ejecuta, cg_raiz: Path = CGROUP_RAIZ) -> list[Contenedor] | None:
    rc, salida = ejecutar(["docker", "ps", "--no-trunc", "--format", "{{.ID}} {{.Names}}"])
    if rc != 0:
        return None
    out = []
    for linea in salida.splitlines():
        partes = linea.split()
        if len(partes) != 2 or not re.fullmatch(r"[0-9a-f]{64}", partes[0]):
            continue
        d = cg_raiz / "docker.slice" / f"docker-{partes[0]}.scope"
        if not d.is_dir():
            return None  # el contenedor no esta donde dice validaciones.md: no se adivina
        out.append(Contenedor(partes[1], _entero_o_none(_lee(d / "memory.max")), _entero_o_none(_lee(d / "memory.peak"))))
    return out


def aplica_contenedores(acciones: list[Accion], fx: Efectos | None = None, aplicar: bool = False) -> list[dict[str, Any]]:
    """Registra cada decision; con `aplicar`, ejecuta `docker update` sobre los que hay que acotar."""
    fx = fx or Efectos()
    eventos = []
    for ac in acciones:
        ev: dict[str, Any] = {"accion": ac.tipo, "contenedor": ac.objetivo, "motivo": ac.motivo, "topes": ac.topes}
        if ac.tipo == "acotar":
            if aplicar:
                b = str(ac.topes["MemoryMax"])
                rc, salida = fx.ejecutar(["docker", "update", "--memory", b, "--memory-swap", b, ac.objetivo])
                ev.update(rc=rc, salida=salida[:300])
            else:
                ev["accion"] = "acotaria"
        eventos.append(ev)
        _registra(ev, fx.log)
    return eventos


# --- CLI ----------------------------------------------------------------------------------------------------


def descongela_propios(fx: Efectos, modo: str) -> list[dict[str, Any]]:
    """Fuera de `actuar`, deshace la congelacion que el propio portero dejo (scopes bb-portero-* con `frozen 1`).

    Sin esto, pasar el interruptor de `actuar` a `off`/`observar` con una suite congelada la dejaria congelada para
    siempre: nadie volveria a darle turno. Volver al comportamiento de antes del portero es descongelarla. Solo
    lista app.slice (un directorio); no lee /proc."""
    try:
        propios = [d for d in cgroup_app(raiz=fx.cg_raiz).iterdir() if NOMBRE_UNIDAD.match(d.name) and _congelado(d)]
    except OSError:
        return []
    eventos = []
    for d in sorted(propios):
        err = congela(d, False)
        ev = {"accion": "descongelar", "modo": modo, "unidad": d.name, "rc": 1 if err else 0, "salida": err,
              "motivo": f"interruptor {NOMBRE}={modo}: se deshace la congelacion que dejo el propio portero"}
        _registra(ev, fx.log)
        eventos.append(ev)
    return eventos


def _ciclo(ultimo: dict[Any, str], modo: str = "actuar", modo_io: str = "off") -> list[dict[str, Any]]:
    deshechos = descongela_propios(Efectos(), modo) if modo != "actuar" else []
    if modo == "off":
        # Sin leer /proc, PSI ni medir cgroups: una sola fila al entrar en off, ninguna mientras siga en off.
        if ultimo.get((None, "off")) == "off":
            return deshechos
        ultimo[(None, "off")] = "off"
        ev: dict[str, Any] = {"accion": "off", "modo": "off", "motivo": f"interruptor {NOMBRE}=off: no observa ni actua"}
        _registra(ev, Efectos().log)
        return [*deshechos, ev]
    ultimo.pop((None, "off"), None)  # al volver a off se vuelve a anunciar
    estado = lee_estado()
    arboles = observar()
    fx = replace(Efectos(), modo=modo, modo_io=modo_io)
    return [*deshechos, *aplica(decide(arboles, estado), arboles or [], estado, fx, ultimo)]


def _ciclo_contenedores(aplicar: bool) -> list[dict[str, Any]]:
    tope, _uso = lee_slice(CGROUP_RAIZ / "docker.slice")
    return aplica_contenedores(decide_contenedores(observar_contenedores(), tope), aplicar=aplicar)


def cmd_contenedores(args: argparse.Namespace) -> int:
    for ev in _ciclo_contenedores(args.aplicar):
        print(json.dumps(ev, ensure_ascii=False))
    return 0


def cmd_demonio(args: argparse.Namespace) -> int:
    ultimo: dict[Any, str] = {}
    vueltas = 0
    while True:
        modo = interruptores.modo(NOMBRE)  # cada vuelta: cambiar el interruptor no exige reiniciar el servicio
        _ciclo(ultimo, modo, interruptores.modo(NOMBRE_IO))
        if args.contenedores and modo != "off" and vueltas % CONTENEDORES_CADA == 0:
            _ciclo_contenedores(aplicar=modo == "actuar")
        vueltas += 1
        if args.una_vez:
            return 0
        time.sleep(INTERVALO_S)  # blocking-sleep: intervalo del demonio de vida larga entre lecturas de /proc, no hay I/O a esperar -- DEBT-COLAPSOS-11-OCT-SUITES-PYTEST-SIN-TECHO-01


def cmd_estado(_args: argparse.Namespace) -> int:
    estado = lee_estado()
    arboles = observar()
    acciones = decide(arboles, estado)
    ultimos = []
    texto = (_lee(_anterior(LOG)) or "") + (_lee(LOG) or "")  # justo tras rotar, el vivo tiene < 10 filas
    if texto:
        ultimos = [json.loads(linea) for linea in texto.splitlines()[-10:] if linea.strip().startswith("{")]
    print(json.dumps(
        {
            "modo": interruptores.modo(NOMBRE),
            "medicion": _medicion(estado),
            "arboles": None if arboles is None else [
                {"raiz": a.raiz, "clase": a.clase, "rss_kb": a.rss_kb, "procesos": a.procesos,
                 "edad_s": round(a.edad_s, 1), "unidad": a.unidad, "congelado": a.congelado, "virtual": a.virtual}
                for a in arboles
            ],
            "decidiria": [{"accion": x.tipo, "raiz": x.raiz, "clase": x.clase, "motivo": x.motivo} for x in acciones],
            "ultimos_eventos": ultimos,
        },
        ensure_ascii=False, indent=2,
    ))
    return 0


def _escribe_peticion(ruta: Path, d: dict[str, Any]) -> None:
    ruta.parent.mkdir(parents=True, exist_ok=True)
    tmp = ruta.with_suffix(".tmp")
    tmp.write_text(json.dumps(d), encoding="utf-8")
    tmp.replace(ruta)


Fuente = Callable[[], tuple[Estado, "list[Arbol] | None"]]


def _fuente_real() -> tuple[Estado, list[Arbol] | None]:
    return lee_estado(), observar()


def turno(pid: int, clase: str, fuente: Fuente = _fuente_real, espera: Callable[[], None] | None = None,
          fx: Efectos | None = None) -> Accion:
    """Pide turno en la cola compartida y espera hasta tenerlo. Devuelve la accion concedida (admitir/mover/no_actua).

    Con `fx.modo` fuera de `actuar` no espera: si le habria tocado esperar lo registra (`habria_esperar`) y concede
    `no_actua`."""
    fx = fx or Efectos()
    cola, log, modo = fx.cola, fx.log, modo_efectivo(fx.modo, clase)
    ruta = cola / f"{pid}.json"
    peticion = {"pid": pid, "clase": clase, "ts": time.time()}
    _escribe_peticion(ruta, peticion)
    ultimo: str | None = None
    while True:
        estado, arboles = fuente()
        acciones = decide(arboles, estado)
        mia = next((x for x in acciones if x.raiz == pid), None)
        if mia is None and len(acciones) == 1 and acciones[0].raiz is None:
            mia = acciones[0]  # NOT_COLLECTED o presupuesto desbordado: fallo cerrado = lanzar como antes, con tope
        if mia is not None and mia.tipo in ("admitir", "mover", "no_actua"):
            _escribe_peticion(ruta, {**peticion, "concedido": True})
            _registra({"accion": "turno", "raiz": pid, "clase": clase, "concedido": mia.tipo, "motivo": mia.motivo,
                       "medicion": _medicion(estado), **({"modo": modo} if modo != "actuar" else {})}, log)
            neg = habria_negado(mia, estado)
            if neg is not None:
                mapa = {"mapa_memoria": mapa_al_actuar(fx, None)} if "necesario_kb" in neg else {}
                _registra({**neg, "medicion": _medicion(estado), **mapa}, log)
            return mia
        motivo = mia.motivo if mia else "sin decision para esta peticion"
        if modo != "actuar":
            _escribe_peticion(ruta, {**peticion, "concedido": True})
            _registra({"accion": "habria_esperar", "modo": modo, "raiz": pid, "clase": clase, "motivo": motivo,
                       "medicion": _medicion(estado)}, log)
            return Accion("no_actua", f"interruptor {NOMBRE}={modo}: habria esperado ({motivo}); lanza sin esperar", pid, clase)
        if motivo != ultimo:
            print(f"[bb portero] esperando turno ({clase}): {motivo}", file=sys.stderr)
            _registra({"accion": "esperar", "raiz": pid, "clase": clase, "motivo": motivo, "medicion": _medicion(estado)}, log)
            ultimo = motivo
        if espera is not None:
            espera()
        else:
            time.sleep(INTERVALO_S)  # blocking-sleep: espera de turno en la cola del portero, sondeo de /proc -- DEBT-COLAPSOS-11-OCT-SUITES-PYTEST-SIN-TECHO-01


def _cwd() -> Path:
    """El directorio de trabajo; si su ruta ya no se lee, `/proc/self/cwd` (stat sigue el enlace; si tampoco se lee,
    `disco_de` devuelve el motivo y el tope queda en NOT_COLLECTED)."""
    try:
        return Path.cwd()
    except OSError:
        return Path("/proc/self/cwd")


def cmd_run(args: argparse.Namespace) -> int:
    cmd = args.cmd[1:] if args.cmd[:1] == ["--"] else args.cmd
    if not cmd:
        print("uso: bb portero run --clase suite -- <comando...>", file=sys.stderr)
        return 2
    c = CLASES[args.clase]
    pid = os.getpid()
    modo = modo_efectivo(interruptores.modo(NOMBRE), args.clase)
    # Peticion explicita: el tope de la clase va en todo modo; el interruptor solo gobierna la cola (ver docstring).
    if modo == "off":
        concedida = Accion("no_actua", f"interruptor {NOMBRE}=off: sin cola, lanza con el tope de su clase", pid, args.clase)
    else:
        concedida = turno(pid, args.clase, fx=replace(Efectos(), modo=modo))
    topes = _topes(c)
    unidad = nombre_unidad(args.clase, pid)
    slice_ = concedida.slice if concedida.tipo == "mover" and modo == "actuar" else "app.slice"
    # Tope de disco: lo gobierna SOLO `portero_io` (apagado por defecto), sobre el disco del directorio de trabajo.
    io, io_ev = topes_io(args.clase, _cwd(), replace(Efectos(), modo_io=interruptores.modo(NOMBRE_IO)))
    print(f"[bb portero] {cmd[0]} bajo {unidad} en {slice_}: MemoryMax={c.memory_max_kb // GIB_KB}G "
          f"MemoryHigh={c.memory_high_kb // GIB_KB}G sin swap, TasksMax={c.tasks_max}", file=sys.stderr)
    if io_ev is not None:
        print(f"[bb portero] io ({NOMBRE_IO}={io_ev['modo']}): {json.dumps(io_ev, ensure_ascii=False)}", file=sys.stderr)
    try:
        rc = subprocess.run(
            ["systemd-run", "--user", "--scope", "--quiet", f"--unit={unidad}", f"--slice={slice_}",
             "-p", f"MemoryMax={topes['MemoryMax']}", "-p", f"MemoryHigh={topes['MemoryHigh']}",
             "-p", "MemorySwapMax=0", "-p", f"TasksMax={topes['TasksMax']}",
             *(x for k, (dev, bps) in io.items() for x in ("-p", f"{k}={dev} {bps}")), "--", *cmd],
            check=False,
        ).returncode
    finally:
        try:
            (COLA / f"{pid}.json").unlink()
        except OSError:
            pass
    _registra({"accion": "fin", "raiz": pid, "clase": args.clase, "rc": rc, "unidad": unidad,
               **({"modo": modo} if modo != "actuar" else {}), **({"io": io_ev} if io_ev is not None else {})}, LOG)
    return rc


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="bb portero", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="orden", required=True)
    sub.add_parser("estado", help="que ve y que decidiria, solo lectura").set_defaults(fn=cmd_estado)
    r = sub.add_parser("run", help="pide turno y lanza el comando bajo scope con tope")
    r.add_argument("--clase", choices=sorted(CLASES), default="suite")
    r.add_argument("cmd", nargs=argparse.REMAINDER)
    r.set_defaults(fn=cmd_run)
    d = sub.add_parser("demonio", help="bucle de vigilancia (lo corre bb-portero.service)")
    d.add_argument("--una-vez", action="store_true", help="un solo ciclo y salir")
    d.add_argument("--contenedores", action="store_true", help="acota tambien contenedores sin tope (docker update)")
    k = sub.add_parser("contenedores", help="contenedores sin tope y el tope que se les pondria (docker.slice)")
    k.add_argument("--aplicar", action="store_true", help="ejecuta docker update; sin esto solo registra 'acotaria'")
    k.set_defaults(fn=cmd_contenedores)
    d.set_defaults(fn=cmd_demonio)
    args = ap.parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
