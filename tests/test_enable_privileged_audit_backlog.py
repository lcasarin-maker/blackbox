"""enable-privileged.sh fija el limite de la cola de audit antes de las reglas de captura (DEBT-AUDIT-ANILLO-DESBORDADO-SIN-LIMITE-01).

Estatico: lee el instalador, no toca /etc/audit. El control negativo corre el mismo chequeo sobre el texto sin esa linea.
"""

from __future__ import annotations

import re
from pathlib import Path

INSTALADOR = Path(__file__).resolve().parent.parent / "enable-privileged.sh"


def limite_antes_de_la_captura(texto: str) -> bool:
    limite = re.search(r"^-b 32768$", texto, re.M)
    captura = re.search(r"^-a always,exit .*-k blackbox_sigterm$", texto, re.M)
    return bool(limite and captura and limite.start() < captura.start())


def test_el_instalador_fija_el_limite_antes_de_la_captura() -> None:
    assert limite_antes_de_la_captura(INSTALADOR.read_text(encoding="utf-8"))


def test_control_negativo_sin_la_linea_o_despues_de_la_captura_falla() -> None:
    texto = INSTALADOR.read_text(encoding="utf-8")
    assert not limite_antes_de_la_captura(texto.replace("-b 32768\n", "", 1))
    movido = texto.replace("-b 32768\n", "", 1).replace("RULES\n", "-b 32768\nRULES\n", 1)
    assert not limite_antes_de_la_captura(movido)
