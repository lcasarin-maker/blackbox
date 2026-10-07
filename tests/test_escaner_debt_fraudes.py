"""Cierre de DEBT-ESCANER-DEBT-CUENTA-FRAUDES-QUE-GATE-NO-REPRODUCE-01 (version no recursiva).

Decision de Luis, 2026-10-07: la version anterior llamaba en vivo a
`simplecode.verification.backlog_verifier --gate`. Esta ficha esta en tasks/done/, y
`backlog_verifier` re-ejecuta el close_check de TODA ficha cerrada para detectar cierres
que ya no reproducen (closure_reproduces). El close_check de esta ficha es esta misma
prueba, asi que cada corrida lanzaba otra corrida completa del gate, que a su vez volvia
a lanzar esta prueba: recursion sin techo. Colgo el pre-push mas de una hora el 2026-10-06.

Esta version no invoca el gate en vivo. Compara el regex que el escaner usa para parsear
la salida de backlog_verifier contra una captura real, guardada en
tests/fixtures/backlog_verifier_gate_capture_20261006.txt (copia de una corrida real del
2026-10-06 08:44, hecha ANTES de cerrar esta ficha -- por tanto sin recursion posible).

Costo declarado: esta prueba ya no ve el estado vivo del gate. Si el escaner vuelve a
contar fraudes que el gate no ve, esta prueba no lo detecta; haria falta correr ambos a
mano, como se hizo para diagnosticar esta ficha.
"""
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parents[1]
SCAN = pathlib.Path.home() / ".claude/skills/debt/scan.py"
FIXTURE = ROOT / "tests/fixtures/backlog_verifier_gate_capture_20261006.txt"

# Copia literal de scan.py::_RE_RESUMEN_BACKLOG_VERIFIER -- escrita como dos literales,
# igual que en scan.py (ahi son dos strings "r...\" r\"..." adyacentes en lineas distintas).
# test_patron_del_escaner_no_cambio comprueba cada mitad por separado contra la fuente.
_PATRON_PARTE_1 = r"frauds:\s*(\d+).*?could_not_run:\s*(\d+)\s*\((\d+)\s*undeclared\).*?"
_PATRON_PARTE_2 = r"contract_breaches:\s*(\d+).*?unverified:\s*(\d+)"
_RE = re.compile(_PATRON_PARTE_1 + _PATRON_PARTE_2, re.S)


def _normalizar(texto: str) -> str:
    return re.sub(r"\s+", "", texto)


def test_patron_del_escaner_no_cambio():
    fuente = SCAN.read_text(encoding="utf-8")
    i = fuente.find("_RE_RESUMEN_BACKLOG_VERIFIER = re.compile(")
    assert i != -1, "scan.py ya no define _RE_RESUMEN_BACKLOG_VERIFIER donde se esperaba"
    bloque = _normalizar(fuente[i : i + 400])
    assert _normalizar(_PATRON_PARTE_1) in bloque, "la primera mitad del patron cambio en scan.py"
    assert _normalizar(_PATRON_PARTE_2) in bloque, "la segunda mitad del patron cambio en scan.py"


def test_conteo_de_fraudes_del_escaner_iguala_al_gate():
    texto = FIXTURE.read_text(encoding="utf-8")
    m = _RE.search(texto)
    assert m is not None, "la captura guardada no trae la linea de resumen del gate"
    frauds, cnr, undeclared, breaches, unverified = (int(x) for x in m.groups())
    # Captura del 2026-10-06 08:44: el gate daba 0 fraudes y 1 could_not_run (1 undeclared).
    assert (frauds, cnr, undeclared, breaches, unverified) == (0, 1, 1, 0, 0)
