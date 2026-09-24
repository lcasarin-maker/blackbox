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
    # El mensaje cambio el 2026-09-23 al endurecerse: "placeholder" hablaba de
    # la unica cadena literal que se rechazaba, y ahora es una familia entera.
    # El VEREDICTO es el mismo, que es lo que este test cubre.
    assert "marcador de pendiente" in motivo
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


# ------------------------------------------------- endurecido el 2026-09-23
# Antes de esta fecha el modulo rechazaba exactamente UNA cadena literal,
# "(pendiente)". Cada test de abajo cubre un caso que PASABA y no debia.

FICHA_TODO = """---
id: HARVEST-EJEMPLO
accepted: {"by": "TODO", "date": "2026-09-09", "trigger": "TODO"}
---
"""

FICHA_CERRADA_SIN_TIPO = """---
id: HARVEST-EJEMPLO
status: done
accepted: {"by": "the maintainer", "date": "2026-09-09", "trigger": "x"}
---
"""

FICHA_CERRADA_TIPO_INVENTADO = """---
id: HARVEST-EJEMPLO
status: done
closure_type: porque_si
reason: se cierra y ya
---
"""

FICHA_CERRADA_OK = """---
id: HARVEST-EJEMPLO
status: done
closure_type: void_wontfix
reason: los tres mecanismos son features de una UI, categoria descartada en el README
---
"""

FICHA_CERRADA_SIN_REASON = """---
id: HARVEST-EJEMPLO
status: done
closure_type: duplicate
---
"""

FICHA_CERRADA_REASON_MARCADOR = """---
id: HARVEST-EJEMPLO
status: done
closure_type: duplicate
reason: TBD
---
"""


@pytest.mark.parametrize(
    "marcador",
    ["TODO", "todo", "  TBD  ", "pendiente", "(pendiente)", "N/A", "-", "?", "por decidir", "none"],
)
def test_un_marcador_de_pendiente_no_es_una_decision(tmp_path, marcador):
    ficha = (
        "---\nid: HARVEST-EJEMPLO\n"
        f'accepted: {{"by": "{marcador}", "date": "2026-09-09", "trigger": "reabrir si X"}}\n---\n'
    )
    ok, motivo = check(_escribir(tmp_path, ficha))
    assert ok is False
    assert "marcador de pendiente" in motivo


def test_control_negativo_un_valor_real_no_se_confunde_con_marcador(tmp_path):
    """Sin esto, el test de arriba no distingue "rechaza marcadores" de
    "rechaza todo"."""
    ok, motivo = check(_escribir(tmp_path, FICHA_OK))
    assert ok is True, motivo


def test_TODO_ya_no_pasa(tmp_path):
    ok, motivo = check(_escribir(tmp_path, FICHA_TODO))
    assert ok is False
    assert "TODO" in motivo


# --- forma 1: la ficha CERRADA ------------------------------------------


def test_cerrada_con_closure_type_valido_y_reason(tmp_path):
    ok, motivo = check(_escribir(tmp_path, FICHA_CERRADA_OK))
    assert ok is True
    assert "void_wontfix" in motivo


def test_cerrada_sin_closure_type_se_rechaza(tmp_path):
    """Convergencia con harvest_decision de la flota, que da rc=1 aqui."""
    ok, motivo = check(_escribir(tmp_path, FICHA_CERRADA_SIN_TIPO))
    assert ok is False
    assert "closure_type=ninguno" in motivo


def test_cerrada_con_closure_type_inventado_se_rechaza(tmp_path):
    ok, motivo = check(_escribir(tmp_path, FICHA_CERRADA_TIPO_INVENTADO))
    assert ok is False
    assert "porque_si" in motivo


def test_cerrada_sin_reason_se_rechaza(tmp_path):
    ok, motivo = check(_escribir(tmp_path, FICHA_CERRADA_SIN_REASON))
    assert ok is False
    assert "sin reason" in motivo


def test_cerrada_con_reason_que_es_un_marcador_se_rechaza(tmp_path):
    ok, motivo = check(_escribir(tmp_path, FICHA_CERRADA_REASON_MARCADOR))
    assert ok is False
    assert "marcador de pendiente" in motivo


def test_una_ficha_ABIERTA_no_cae_por_la_forma_cerrada(tmp_path):
    """_decision_cerrada devuelve None (no False) para status != done: si
    devolviera False, mataria a toda ficha abierta antes de su contrato."""
    ficha = FICHA_OK.replace("id: HARVEST-EJEMPLO", "id: HARVEST-EJEMPLO\nstatus: open")
    ok, motivo = check(_escribir(tmp_path, ficha))
    assert ok is True, motivo
