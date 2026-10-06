"""Cierre de DEBT-ESCANER-DEBT-CUENTA-FRAUDES-QUE-GATE-NO-REPRODUCE-01: escaner y gate deben contar igual."""
import re
import subprocess
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]


def test_conteo_de_fraudes_del_escaner_iguala_al_gate():
    gate = subprocess.run(
        ["python3", ".simplecode/run.py", "simplecode.verification.backlog_verifier", "--root", ".", "--gate"],
        cwd=ROOT, capture_output=True, text=True, check=False)
    escaner = subprocess.run(
        ["python3", str(pathlib.Path.home() / ".claude/skills/debt/scan.py")],
        cwd=ROOT, capture_output=True, text=True, check=False)
    fraudes_gate = int(re.search(r"frauds: (\d+)", gate.stdout + gate.stderr).group(1))
    fraudes_escaner = len(re.findall(r"FRAUD DETECTED", escaner.stdout))
    assert fraudes_escaner == fraudes_gate
