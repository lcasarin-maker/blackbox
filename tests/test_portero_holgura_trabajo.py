"""La holgura de app.slice debe medirse sobre la memoria de trabajo, no sobre `memory.current` con su cache inactiva.

Medido el 2026-10-17 en esta ATOM: app.slice tenia memory.current 38.7 GiB de un tope de 42, pero 15.6 GiB eran
`inactive_file` (cache que el kernel recupera sin costo) y la memoria de trabajo era ~23 GiB. El portero calculaba
una holgura de 3.3 GiB (< 4 GiB) y congelaba suites que tenian 19 GiB reales de margen.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from tools import portero as po

GIB = 1024 ** 3


def _cg(d: Path, current_gib: float, max_gib: int, stat: str | None) -> Path:
    d.mkdir(parents=True, exist_ok=True)
    (d / "memory.max").write_text(f"{max_gib * GIB}\n", encoding="ascii")
    (d / "memory.current").write_text(f"{int(current_gib * GIB)}\n", encoding="ascii")
    if stat is not None:
        (d / "memory.stat").write_text(stat, encoding="ascii")
    return d


@pytest.mark.unit
def test_la_cache_inactiva_no_cuenta_como_uso(tmp_path: Path):
    d = _cg(tmp_path / "a", 38.0, 42, f"anon {14 * GIB}\nfile {22 * GIB}\ninactive_file {15 * GIB}\nactive_file {7 * GIB}\n")
    tope, uso = po.lee_slice(d)
    assert tope == 42 * GIB // 1024
    assert uso == 23 * GIB // 1024  # 38 - 15 GiB de cache inactiva


@pytest.mark.unit
def test_sin_memory_stat_se_conserva_memory_current(tmp_path: Path):
    """Control negativo del instrumento: sin memory.stat no hay nada que restar y el uso es memory.current entero."""
    d = _cg(tmp_path / "b", 38.0, 42, None)
    assert po.lee_slice(d) == (42 * GIB // 1024, 38 * GIB // 1024)


@pytest.mark.unit
def test_cache_inactiva_mayor_que_el_uso_no_da_uso_negativo(tmp_path: Path):
    d = _cg(tmp_path / "c", 10.0, 42, f"inactive_file {20 * GIB}\n")
    assert po.lee_slice(d)[1] == 0


@pytest.mark.unit
def test_una_linea_ilegible_de_memory_stat_no_lanza(tmp_path: Path):
    d = _cg(tmp_path / "d", 10.0, 42, "inactive_file no-es-un-numero\nbasura\n")
    assert po.lee_slice(d)[1] == 10 * GIB // 1024
