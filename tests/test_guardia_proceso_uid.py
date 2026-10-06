"""Cierre de DEBT-GUARDIA-PROCESO-NO-FRENA-SIN-UID-01.

Si /proc/<pid>/status no es legible pero el dueno se puede leer de /proc/<pid> (stat), el guardia
debe poder actuar sobre un proceso del mismo usuario. Hoy se niega: "no se pudo leer ... no se toca".
"""
import importlib.machinery
import importlib.util
import os
import pathlib

from unittest import mock

ROOT = pathlib.Path(__file__).resolve().parents[1]
GUARDIA = ROOT / "bin" / "bb-guardia-proceso"


def _cargar():
    loader = importlib.machinery.SourceFileLoader("bb_guardia_proceso", str(GUARDIA))
    spec = importlib.util.spec_from_loader("bb_guardia_proceso", loader)
    modulo = importlib.util.module_from_spec(spec)
    loader.exec_module(modulo)
    return modulo


def test_guardia_resuelve_dueno_sin_status_legible():
    guardia = _cargar()
    pid_ajeno = os.getppid()
    with mock.patch.object(guardia, "_uid_de", return_value=None):
        motivo = guardia._es_intocable(pid_ajeno, "python3")
    assert motivo is None or "no se pudo leer" not in motivo
