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


@pytest.fixture(autouse=True)
def _estado_termico_aislado(tmp_path, monkeypatch):
    """Ningun test puede escribir el estado termico REAL de la maquina (`estado_termico.json`).
    Medido el 2026-10-11: sin esto, `muestrear(escribir=True)` de los tests lo piso con un estado
    de fixture ('normal', sin zonas) en la carpeta de datos vivos."""
    try:
        from tools import atom_gpu_telemetry as agt
    except ImportError:  # pragma: no cover - el modulo siempre existe en este repo
        return
    monkeypatch.setattr(agt, "ESTADO_TERMICO_PATH", tmp_path / "estado_termico_de_prueba.json")
