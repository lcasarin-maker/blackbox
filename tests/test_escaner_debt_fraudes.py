"""Cierre de DEBT-ESCANER-DEBT-CUENTA-FRAUDES-QUE-GATE-NO-REPRODUCE-01.

Usa la misma funcion del escaner (simplecode_backlog_verifier) y el mismo gate. Si el
escaner cuenta fraudes que el gate no ve, la prueba falla.
"""
import importlib.util
import pathlib
import subprocess

ROOT = pathlib.Path(__file__).resolve().parents[1]
SCAN = pathlib.Path.home() / ".claude/skills/debt/scan.py"


def _cargar_escaner():
    spec = importlib.util.spec_from_file_location("scan", SCAN)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


def test_conteo_de_fraudes_del_escaner_iguala_al_gate():
    escaner = _cargar_escaner().simplecode_backlog_verifier(ROOT)
    gate = subprocess.run(
        ["python3", ".simplecode/run.py", "simplecode.verification.backlog_verifier", "--root", ".", "--gate"],
        cwd=ROOT, capture_output=True, text=True, check=False)
    import re
    fraudes_gate = int(re.search(r"frauds: (\d+)", gate.stdout + gate.stderr).group(1))
    assert escaner[0] == fraudes_gate, (escaner, fraudes_gate)
