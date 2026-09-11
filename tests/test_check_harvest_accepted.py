"""Cobertura de tools/check_harvest_accepted.py -- unica pieza de Python de
este repo (bash-first, ver bin/bb). Cada test cubre una rama real del
close_check que usan las fichas HARVEST-*.md y FEATURE-*.md."""

import sys

import pytest

from tools.check_harvest_accepted import check, main

FICHA_OK = """---
id: HARVEST-EJEMPLO
accepted: {"by": "the maintainer", "date": "2026-09-09", "trigger": "reabrir si X"}
---
"""

FICHA_SIN_ACCEPTED = """---
id: HARVEST-EJEMPLO
status: open
---
"""

FICHA_PLACEHOLDER = """---
id: HARVEST-EJEMPLO
accepted: {"by": "(pendiente)", "date": "2026-09-09", "trigger": "x"}
---
"""

FICHA_VACIO = """---
id: HARVEST-EJEMPLO
accepted: {"by": "", "date": "2026-09-09", "trigger": "x"}
---
"""

FICHA_FECHA_MALA = """---
id: HARVEST-EJEMPLO
accepted: {"by": "the maintainer", "date": "09/09/2026", "trigger": "x"}
---
"""


def _escribir(tmp_path, contenido):
    p = tmp_path / "FICHA.md"
    p.write_text(contenido, encoding="utf-8")
    return p


def test_archivo_no_existe(tmp_path):
    ok, motivo = check(tmp_path / "no-existe.md")
    assert ok is False
    assert "no existe" in motivo


def test_sin_campo_accepted(tmp_path):
    p = _escribir(tmp_path, FICHA_SIN_ACCEPTED)
    ok, motivo = check(p)
    assert ok is False
    assert "sin campo accepted" in motivo


def test_accepted_no_es_objeto(tmp_path, monkeypatch):
    # El regex de `check()` solo captura contenido con forma `{...}`, y YAML
    # siempre parsea eso como mapping (o lanza) -- nunca como no-dict por una
    # ficha real. Se fuerza la rama defensiva con un mock, igual que se haria
    # con cualquier guarda que protege un caso que el formato de entrada ya
    # excluye en la practica.
    import yaml as yaml_mod

    p = _escribir(tmp_path, FICHA_OK)
    monkeypatch.setattr(yaml_mod, "safe_load", lambda _s: ["no", "es", "dict"])
    ok, motivo = check(p)
    assert ok is False
    assert "no es un objeto" in motivo


def test_placeholder_sin_resolver(tmp_path):
    p = _escribir(tmp_path, FICHA_PLACEHOLDER)
    ok, motivo = check(p)
    assert ok is False
    assert "placeholder" in motivo
    assert "accepted.by" in motivo


def test_campo_vacio(tmp_path):
    p = _escribir(tmp_path, FICHA_VACIO)
    ok, motivo = check(p)
    assert ok is False
    assert "accepted.by" in motivo


def test_fecha_no_iso8601(tmp_path):
    p = _escribir(tmp_path, FICHA_FECHA_MALA)
    ok, motivo = check(p)
    assert ok is False
    assert "ISO-8601" in motivo


def test_ficha_completa_pasa(tmp_path):
    p = _escribir(tmp_path, FICHA_OK)
    ok, motivo = check(p)
    assert ok is True
    assert motivo == "accepted completo"


def test_main_sin_argumentos(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["check_harvest_accepted.py"])
    with pytest.raises(SystemExit) as exc:
        main()
    assert exc.value.code == 2
    assert "uso:" in capsys.readouterr().err


def test_main_ficha_ok_sale_cero(tmp_path, monkeypatch, capsys):
    p = _escribir(tmp_path, FICHA_OK)
    monkeypatch.setattr(sys, "argv", ["check_harvest_accepted.py", str(p)])
    with pytest.raises(SystemExit) as exc:
        main()
    assert exc.value.code == 0
    assert "accepted completo" in capsys.readouterr().out


def test_main_ficha_mala_sale_uno(tmp_path, monkeypatch, capsys):
    p = _escribir(tmp_path, FICHA_SIN_ACCEPTED)
    monkeypatch.setattr(sys, "argv", ["check_harvest_accepted.py", str(p)])
    with pytest.raises(SystemExit) as exc:
        main()
    assert exc.value.code == 1
    assert "sin campo accepted" in capsys.readouterr().out
