#!/usr/bin/env python3
"""Lector unico del historial solo-anexar de `reboots.jsonl`.

Una rectificacion se registra como otra linea con `anula: true` y
`corrige_linea`: la linea previa, del mismo `boot_id`, que sigue vigente. La
linea anulada no se borra; una linea normal posterior repone el veredicto. Una
relacion invalida se ignora y se deja constancia en `avisos`.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Iterable


class LedgerReadError(RuntimeError):
    """El escritor no puede decidir que un boot ya fue escrito."""


def normaliza_id(boot_id: str) -> str:
    """Normaliza un boot id sin alterar el valor que se conserva en la fila."""
    return str(boot_id).strip().replace("-", "").lower()


def _aviso(avisos: list[str], ruta: Path, linea: int, detalle: str) -> None:
    avisos.append(f"{ruta.name}:{linea} ilegible ({detalle})")


def _lee_archivo(
    ruta: Path,
    actuales: dict[str, dict[str, Any]],
    avisos: list[str],
    campos_requeridos: tuple[str, ...],
) -> None:
    try:
        lineas = ruta.read_text(encoding="utf-8").splitlines()
    except FileNotFoundError:
        avisos.append(f"veredictos no existe: {ruta}")
        return
    except (OSError, UnicodeError) as e:
        avisos.append(f"veredictos no se pudo leer: {ruta} ({e!r})")
        return

    # La referencia es local al archivo y 1-based. `actuales` se comparte para
    # conservar la regla existente: si se pasan varios archivos, el ultimo
    # registro valido recibido gana.
    vigentes: dict[str, tuple[int, dict[str, Any]]] = {}
    vistos: dict[int, dict[str, Any]] = {}
    for numero, linea in enumerate(lineas, 1):
        if not linea.strip():
            continue
        try:
            fila = json.loads(linea)
        except (TypeError, ValueError) as e:
            _aviso(avisos, ruta, numero, repr(e))
            continue
        if not isinstance(fila, dict):
            _aviso(avisos, ruta, numero, "la fila no es un objeto JSON")
            continue
        raw_id = fila.get("boot_id")
        if not isinstance(raw_id, str) or not raw_id.strip():
            _aviso(avisos, ruta, numero, "falta boot_id")
            continue
        boot_id = normaliza_id(raw_id)
        if not boot_id:
            _aviso(avisos, ruta, numero, "falta boot_id tras normalizar")
            continue

        if fila.get("anula") is True:
            referencia = fila.get("corrige_linea")
            anterior = vigentes.get(boot_id)
            objetivo = vistos.get(referencia) if isinstance(referencia, int) and not isinstance(referencia, bool) else None
            valido = (
                isinstance(referencia, int)
                and not isinstance(referencia, bool)
                and 1 <= referencia < numero
                and objetivo is not None
                and normaliza_id(str(objetivo.get("boot_id", ""))) == boot_id
                and anterior is not None
                and anterior[0] == referencia
            )
            if not valido:
                _aviso(avisos, ruta, numero, "anulacion con corrige_linea sin referencia vigente del mismo boot")
                continue
            vigentes.pop(boot_id)
            actuales.pop(boot_id, None)
            continue

        if "anula" in fila and type(fila["anula"]) is not bool:
            _aviso(avisos, ruta, numero, "anula debe ser booleano true solo en una rectificacion")
            continue
        if "corrige_linea" in fila:
            _aviso(avisos, ruta, numero, "corrige_linea solo puede acompañar a anula: true")
            continue
        faltan = [campo for campo in campos_requeridos if campo not in fila]
        if faltan:
            _aviso(avisos, ruta, numero, f"falta {', '.join(faltan)}")
            continue

        vigentes[boot_id] = (numero, fila)
        vistos[numero] = fila
        actuales[boot_id] = fila


def leer_filas(
    rutas: Iterable[Path],
    avisos: list[str] | None = None,
    *,
    campos_requeridos: tuple[str, ...] = (),
    estricta: bool = False,
) -> dict[str, dict[str, Any]]:
    """Devuelve filas vigentes y aplica solo rectificaciones validas."""
    salida: dict[str, dict[str, Any]] = {}
    reportes = avisos if avisos is not None else []
    for ruta in rutas:
        inicio = len(reportes)
        _lee_archivo(Path(ruta), salida, reportes, campos_requeridos)
        if estricta and len(reportes) != inicio:
            raise LedgerReadError("; ".join(reportes[inicio:]))
    return salida


def tiene_sucesor(ruta: Path, boot_id_siguiente: str, avisos: list[str] | None = None) -> bool:
    """Indica si el historial vigente contiene un sucesor para `boot_id_siguiente`."""
    filas = leer_filas([ruta], avisos)
    esperado = normaliza_id(boot_id_siguiente)
    return bool(esperado) and any(
        normaliza_id(str(fila.get("boot_id_siguiente", ""))) == esperado
        for fila in filas.values()
    )


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="lee el historial vigente de reboots.jsonl")
    ap.add_argument("accion", choices=("tiene-sucesor",))
    ap.add_argument("ruta", type=Path)
    ap.add_argument("boot_id_siguiente")
    args = ap.parse_args(argv)
    avisos: list[str] = []
    resultado = tiene_sucesor(args.ruta, args.boot_id_siguiente, avisos)
    for aviso in avisos:
        print(f"COULD_NOT_READ: {aviso}", file=sys.stderr)
    if avisos:
        return 2
    return 0 if resultado else 1


if __name__ == "__main__":
    raise SystemExit(main())
