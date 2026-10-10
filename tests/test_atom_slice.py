"""Valida adopted/system-config/atom-secundarias.slice.

`systemd-analyze verify` devuelve rc=0 INCLUSO sobre una unidad rota -- solo
imprime advertencias ('Invalid ...', 'Unknown key ...') y las ignora, medido
contra una unidad deliberadamente rota antes de escribir este test. Por eso
el criterio real no es el codigo de salida: es que STDOUT/STDERR queden
vacios de esas dos frases.

Requiere `systemd-analyze` en el PATH; si no esta, el test se salta (no
falla) -- no es una comprobacion de la unidad, es del entorno de CI.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

_UNIDAD = (
    Path(__file__).resolve().parent.parent
    / "adopted"
    / "system-config"
    / "etc_systemd_system_atom-secundarias.slice"
)

pytestmark = pytest.mark.skipif(
    shutil.which("systemd-analyze") is None,
    reason="systemd-analyze no disponible en este entorno",
)


def test_la_unidad_real_no_produce_advertencias():
    assert _UNIDAD.is_file(), f"No existe la unidad en {_UNIDAD}"
    r = subprocess.run(
        ["systemd-analyze", "verify", str(_UNIDAD)],
        capture_output=True,
        text=True,
        timeout=10,
    )
    salida = r.stdout + r.stderr
    assert "Invalid" not in salida, salida
    assert "Unknown key" not in salida, salida


def test_control_negativo_una_unidad_rota_SI_produce_advertencias(tmp_path: Path):
    """Prueba que el criterio de arriba puede fallar de verdad -- si esta
    unidad rota no produjera ninguna advertencia, el test de la unidad real
    estaria pasando por casualidad, no por verificacion."""
    rota = tmp_path / "rota.slice"
    rota.write_text(
        "[Slice]\nMemoryMax=notanumber\nUnknownDirectiveXYZ=true\n",
        encoding="utf-8",
    )
    r = subprocess.run(
        ["systemd-analyze", "verify", str(rota)],
        capture_output=True,
        text=True,
        timeout=10,
    )
    salida = r.stdout + r.stderr
    assert "Invalid" in salida
    assert "Unknown key" in salida


def test_memory_max_mayor_que_memory_high():
    """MemoryHigh es el umbral blando; debe ser MENOR que el limite duro, o
    el throttling nunca ocurriria antes del OOM-kill."""
    texto = _UNIDAD.read_text(encoding="utf-8")
    high = int(
        [line for line in texto.splitlines() if line.startswith("MemoryHigh=")][0]
        .split("=")[1]
        .rstrip("G")
    )
    max_ = int(
        [line for line in texto.splitlines() if line.startswith("MemoryMax=")][0]
        .split("=")[1]
        .rstrip("G")
    )
    assert high < max_, f"MemoryHigh={high}G debe ser menor que MemoryMax={max_}G"
