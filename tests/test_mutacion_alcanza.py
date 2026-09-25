"""Suite de `tools/mutacion_alcanza.py`.

El control negativo es todo el punto: este script existe porque el runner del
kit llego vendorizado a este repo sin poder capturar nada, y nadie lo noto
durante meses. Un guardian de esa condicion que no pudiera salir en rojo
repetiria el mismo fallo una capa mas arriba.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from tools import mutacion_alcanza


@pytest.fixture
def repo_plano(tmp_path: Path) -> Path:
    """Un repo con el kit vendorizado y su codigo en `tools/`, como este."""
    (tmp_path / ".simplecode").mkdir()
    real = Path(__file__).resolve().parent.parent / ".simplecode" / "runtime.zip"
    (tmp_path / ".simplecode" / "runtime.zip").write_bytes(real.read_bytes())
    (tmp_path / "tools").mkdir()
    (tmp_path / "tools" / "__init__.py").write_text("", encoding="utf-8")
    (tmp_path / "tools" / "calc.py").write_text(
        "def par(n):\n    return n % 2 == 0\n", encoding="utf-8")
    (tmp_path / "tests").mkdir()
    return tmp_path


def test_un_test_que_importa_su_modulo_resuelve(repo_plano: Path):
    (repo_plano / "tests" / "test_calc.py").write_text(
        "from tools import calc\n\ndef test_par():\n    assert calc.par(4)\n", encoding="utf-8")

    assert mutacion_alcanza.resuelven(repo_plano) == (1, 1)


def test_control_negativo_un_repo_que_el_runner_NO_alcanza_sale_1(repo_plano: Path, capsys):
    """El estado que este guardian existe para cazar: tests que no importan
    ningun modulo local, asi que no hay sujeto que mutar."""
    (repo_plano / "tests" / "test_nada.py").write_text(
        "def test_nada():\n    assert 1 == 1\n", encoding="utf-8")

    assert mutacion_alcanza.main(["--root", str(repo_plano)]) == 1
    salida = capsys.readouterr().out
    assert "0 de 1" in salida
    assert "no alcanza a este repo" in salida


def test_con_al_menos_uno_alcanzado_sale_0(repo_plano: Path, capsys):
    (repo_plano / "tests" / "test_calc.py").write_text(
        "from tools import calc\n\ndef test_par():\n    assert calc.par(4)\n", encoding="utf-8")
    (repo_plano / "tests" / "test_nada.py").write_text(
        "def test_nada():\n    assert 1 == 1\n", encoding="utf-8")

    assert mutacion_alcanza.main(["--root", str(repo_plano)]) == 0
    assert "1 de 2" in capsys.readouterr().out


def test_contra_ESTE_repo_de_verdad():
    """El sujeto real, no un doble: si la proxima sincronizacion del kit
    volviera a romper el resolutor, esto es lo que lo dice."""
    raiz = Path(__file__).resolve().parent.parent
    alcanzados, total = mutacion_alcanza.resuelven(raiz)
    assert total >= 9, f"solo {total} ficheros de test?"
    assert alcanzados >= 7, f"el runner solo alcanza {alcanzados} de {total}"
