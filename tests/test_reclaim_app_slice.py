"""El reclamo de app.slice debe hacerlo kswapd, no los procesos que piden memoria.

Cierre de DEBT-APP-SLICE-TOPE-42G-ESTRANGULA-LA-CACHE-DE-ARCHIVOS-01. Mide el equipo
real (memory.stat vivo, acumulado desde el arranque): mientras la ficha siga abierta
`tests/conftest.py` marca el test xfail (tests/known_failures.json). Medido el
2026-10-17: 99 % de reclamo directo contra el tope de 42 GiB.
"""
from __future__ import annotations

import os
from pathlib import Path

import pytest

from tools import reclaim_ventana as rv

APP = (Path("/sys/fs/cgroup") / "user.slice" / f"user-{os.getuid()}.slice"
       / f"user@{os.getuid()}.service" / "app.slice")


@pytest.mark.unit
def test_reclamo_directo_de_app_slice_por_debajo_de_la_mitad():
    parte = rv.parte_directo(rv.lee_memory_stat(APP / "memory.stat"))
    assert parte is not None, "memory.stat de app.slice ilegible o sin escaneo: COULD_NOT_RUN"
    assert parte < 0.5, f"reclamo directo {parte:.1%} del escaneo de app.slice"


@pytest.mark.unit
def test_control_negativo_el_instrumento_lee_los_dos_contadores_vivos():
    """El lector puede dar un numero: los dos contadores existen en memory.stat de este kernel."""
    r = rv.lee_memory_stat(APP / "memory.stat")
    assert isinstance(r["pgscan_direct"], int) and isinstance(r["pgscan_kswapd"], int), r
