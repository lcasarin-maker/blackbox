"""Pruebas de deuda abierta: se marcan xfail(strict=True) mientras su ficha siga abierta.

La linea base vive en tests/known_failures.json: nodeid -> ID de ficha, con dueno y caducidad.
- Ficha abierta (en tasks/backlog) y linea base vigente: la prueba se marca xfail. Se cuenta
  aparte en el resumen de pytest ("xfailed"), nunca como pasada.
- Ficha cerrada (sale de tasks/backlog) o linea base caducada: no se marca; la prueba corre y
  falla si su evidencia no existe.
- strict=True: si una prueba marcada pasa, pytest la reporta como fallo (XPASS). Eso indica que la
  ficha ya no es necesaria y debe quitarse de la linea base.
"""
import datetime
import json
import pathlib

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
BASELINE = ROOT / "tests" / "known_failures.json"


def pytest_collection_modifyitems(config, items):
    data = json.loads(BASELINE.read_text(encoding="utf-8"))
    if datetime.date.today() > datetime.date.fromisoformat(data["expires"]):
        return
    for item in items:
        ficha = data["entries"].get(item.nodeid)
        if ficha and (ROOT / "tasks" / "backlog" / f"{ficha}.md").is_file():
            item.add_marker(pytest.mark.xfail(
                strict=True, reason=f"ficha de deuda abierta: {ficha}"))
