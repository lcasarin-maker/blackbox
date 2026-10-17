"""El controlador `io` de cgroup v2 debe estar delegado al arbol del usuario para poder acotar el disco de las suites.

Cierre de DEBT-IO-NO-DELEGADO-AL-USUARIO-LAS-SUITES-SATURAN-EL-DISCO-01. Mide el equipo real: mientras la ficha siga
abierta `tests/conftest.py` marca el test xfail (tests/known_failures.json).
"""
from __future__ import annotations

import os
from pathlib import Path

import pytest

RAIZ_CG = Path("/sys/fs/cgroup")


def _controladores(ruta: Path) -> set[str]:
    return set((ruta / "cgroup.controllers").read_text(encoding="ascii").split())


@pytest.mark.unit
def test_io_esta_delegado_al_manager_del_usuario():
    uid = os.getuid()
    manager = RAIZ_CG / "user.slice" / f"user-{uid}.slice" / f"user@{uid}.service"
    assert "io" in _controladores(manager)


@pytest.mark.unit
def test_control_negativo_el_instrumento_ve_io_donde_si_existe():
    """El lector puede decir que si: la raiz de cgroup v2 de este equipo ofrece `io`."""
    assert "io" in _controladores(RAIZ_CG)
