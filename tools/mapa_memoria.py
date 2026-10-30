#!/usr/bin/env python3
"""Mapa de memoria por unidad duena, capturado en el instante en que una guardia ACTUA
(FEATURE-MAPA-DE-MEMORIA-FORENSE-AL-ACTUAR-01; la idea es el `GET /internal/memory` de Athena's Engine).

Por que existe: el 2026-10-16 `bb-usable` actuo sin que quedara ni `memory.stat` (anon, file, shmem) ni el swap de
las unidades de `app.slice`, y la causa quedo "inferida, no medida". Cada guardia que actua (escalon de
`bin/bb-usable`, `tools/vigilante_memavail.py`, `tools/portero.py` al congelar o al negar) mete este mapa en la MISMA
fila de su evento, bajo la clave `mapa_memoria`.

FORENSE PURO: la guardia ya decidio cuando lo pide; el mapa no entra en ninguna decision. Cada guardia lo pide
dentro de su propio try/except y `captura` tampoco lanza: un fallo deja `{"estado": "NOT_COLLECTED", "motivo": ...}`
y la guardia actua igual.

Por unidad: nombre, cgroup, clase y rango (`data/rangos_memoria.json`, la regla de `vigilante_memavail.Rangos`:
la clase de MENOR rango que casa; sin ninguna, `sin_clase` con el rango mas bajo declarado), `memory.current`,
`anon`/`file`/`shmem` de `memory.stat`, `memory.swap.current` y `gpu_dmem` (`dmem.current` por region, el mismo dato
que `tools/gpumem.py`, parseado con su `_pares`). Lo ilegible es `NOT_COLLECTED`, nunca 0: un cero es una afirmacion.
`gpu_dmem` vale `SIN_REGION` si el kernel da el fichero vacio (modulo NVIDIA sin el parche dmem).

TOPE por fila: las `TOPE_UNIDADES` (10) unidades de mayor `memory.current`, MAS las `obligatorias` (la unidad sobre
la que actua la guardia, una por guardia), y del resto solo el recuento (`omitidas`), los bytes legibles que suman
(`omitidas_bytes_legibles`) y cuantas no se pudieron leer (`omitidas_ilegibles`). Medido el 2026-10-30 en esta
maquina: 67 unidades bajo `user@1000.service`; las 10 mayores suman 17.54 de 18.05 GiB y las 57 restantes 0.51 GiB.
Solo se lee `memory.stat`, swap y dmem de las elegidas: el coste es `memory.current` de todas mas 4 ficheros por
unidad elegida, todo de cgroupfs (no toca el `mmap_lock` de ningun proceso, a diferencia de `origen_proceso`).

Sin dependencias fuera de la biblioteca estandar: `bin/bb-usable` (root, FailureAction=reboot) lo carga por ruta,
igual que `tools/origen_proceso.py`, y `tools/portero.py` corre tambien como script con `tools/` en `sys.path`.

LIMITE DECLARADO: la memoria CUDA que no se cobra al cgroup queda fuera salvo la que ve `dmem` (con el modulo
parcheado). Pinned y managed no se cobran nunca (ver `tools/gpumem.py`).
"""

from __future__ import annotations

import fnmatch
import importlib.util
import json
from pathlib import Path
from typing import Any, Callable, Iterable

NOT_COLLECTED = "NOT_COLLECTED"
SIN_REGION = "SIN_REGION"
ESQUEMA = "mapa_memoria/1"
TOPE_UNIDADES = 10
CAMPOS_STAT = ("anon", "file", "shmem")
SUFIJOS_UNIDAD = (".scope", ".service", ".slice")
RANGOS_RUTA = Path(__file__).resolve().parent.parent / "data" / "rangos_memoria.json"
Clases = tuple[tuple[str, int, tuple[str, ...]], ...]


def _carga_pares() -> tuple[Callable[[str], dict[str, int]] | None, str | None]:
    """`gpumem._pares` (lector de `dmem.current`), cargado por ruta: este modulo no puede depender de `tools` en sys.path."""
    ruta = Path(__file__).resolve().parent / "gpumem.py"
    try:
        spec = importlib.util.spec_from_file_location("mapa_memoria_gpumem", ruta)
        if spec is None or spec.loader is None:
            raise ImportError(f"sin cargador para {ruta}")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod._pares, None
    except Exception as exc:  # sin gpumem el mapa sale igual, con gpu_dmem NOT_COLLECTED y el motivo
        return None, f"{type(exc).__name__}: {exc}"


_PARES, _PARES_ERROR = _carga_pares()


def _lee(ruta: Path) -> str | None:
    try:
        return ruta.read_text(encoding="ascii")
    except (OSError, UnicodeDecodeError):
        return None


def _entero(ruta: Path) -> int | str:
    texto = _lee(ruta)
    return int(texto) if texto is not None and texto.strip().isdigit() else NOT_COLLECTED


def _stat(cg: Path) -> dict[str, int | str]:
    """anon, file y shmem de `memory.stat`; cada uno ausente o ilegible queda NOT_COLLECTED por separado."""
    campos: dict[str, int] = {}
    for linea in (_lee(cg / "memory.stat") or "").splitlines():
        k, _, v = linea.partition(" ")
        if k in CAMPOS_STAT and v.strip().isdigit():
            campos[k] = int(v)
    return {k: campos.get(k, NOT_COLLECTED) for k in CAMPOS_STAT}


def _gpu(cg: Path) -> dict[str, int] | str:
    if _PARES is None:
        return f"{NOT_COLLECTED}: tools/gpumem.py no cargado ({_PARES_ERROR})"
    texto = _lee(cg / "dmem.current")
    if texto is None:
        return NOT_COLLECTED
    return _PARES(texto) or SIN_REGION


def lee_clases(ruta: Path = RANGOS_RUTA) -> Clases | None:
    """Las clases de `data/rangos_memoria.json`; None si el fichero no se lee o esta mal formado (clase y rango
    quedan NOT_COLLECTED: este mapa no inventa un rango)."""
    try:
        clases = tuple((e["clase"], e["rango"], tuple(e["patrones"]))
                       for e in json.loads(ruta.read_text(encoding="utf-8"))["clases"])
    except (OSError, ValueError, KeyError, TypeError):
        return None
    ok = clases and all(isinstance(c, str) and type(r) is int and all(isinstance(p, str) for p in pats)
                        for c, r, pats in clases)
    return clases if ok else None


def clase_de(nombre: str, clases: Clases | None) -> tuple[str, int | str]:
    """La regla de `vigilante_memavail.Rangos.rango`, devolviendo tambien el nombre de la clase."""
    if not clases:
        return NOT_COLLECTED, NOT_COLLECTED
    n = nombre.lower()
    casan = [(r, c) for c, r, pats in clases if any(fnmatch.fnmatchcase(n, p.lower()) for p in pats)]
    if casan:
        r, c = min(casan)
        return c, r
    return "sin_clase", min(r for _, r, _ in clases)


def unidades_de(raiz: Path) -> list[Path] | None:
    """Hijas directas de un slice que son unidad (.scope, .service, .slice). None si la raiz no se lista."""
    try:
        return sorted(d for d in raiz.iterdir() if d.name.endswith(SUFIJOS_UNIDAD) and d.is_dir())
    except OSError:
        return None


def _unidad(cg: Path, actual: int | str, clases: Clases | None) -> dict[str, Any]:
    clase, rango = clase_de(cg.name, clases)
    return {"unidad": cg.name, "cgroup": str(cg), "clase": clase, "rango": rango, "memory.current": actual,
            **_stat(cg), "memory.swap.current": _entero(cg / "memory.swap.current"), "gpu_dmem": _gpu(cg)}


def mapa(rutas: Iterable[str | Path], clases: Clases | None = None, obligatorias: Iterable[str | Path] = (),
         tope: int = TOPE_UNIDADES) -> dict[str, Any]:
    """Las `tope` unidades de mayor memory.current (ilegibles al final) mas las obligatorias, y el resumen del resto."""
    todas = list(dict.fromkeys(Path(r) for r in rutas))
    forzadas = [Path(r) for r in obligatorias]
    actual = {cg: _entero(cg / "memory.current") for cg in dict.fromkeys([*todas, *forzadas])}
    orden = sorted(todas, key=lambda cg: (isinstance(actual[cg], int), actual[cg] if isinstance(actual[cg], int) else 0),
                   reverse=True)
    elegidas = list(dict.fromkeys([*orden[:tope], *forzadas]))
    resto = [cg for cg in orden if cg not in elegidas]
    return {
        "esquema": ESQUEMA, "tope": tope, "vistas": len(todas),
        "unidades": [_unidad(cg, actual[cg], clases) for cg in elegidas],
        "omitidas": len(resto),
        "omitidas_bytes_legibles": sum(v for cg in resto if isinstance(v := actual[cg], int)),
        "omitidas_ilegibles": sum(1 for cg in resto if not isinstance(actual[cg], int)),
    }


def captura(rutas: Iterable[str | Path] | None, clases: Clases | None = None,
            obligatorias: Iterable[str | Path] = (), tope: int = TOPE_UNIDADES) -> dict[str, Any]:
    """`mapa` que nunca lanza. `rutas` None (la guardia no pudo listar sus unidades) es NOT_COLLECTED, no un mapa vacio."""
    try:
        if rutas is None:
            return {"esquema": ESQUEMA, "estado": NOT_COLLECTED, "motivo": "lista de unidades ilegible"}
        return mapa(rutas, clases, obligatorias, tope)
    except Exception as exc:  # forense puro: un fallo aqui no puede llegar a la guardia
        return {"esquema": ESQUEMA, "estado": NOT_COLLECTED, "motivo": f"{type(exc).__name__}: {exc}"}
