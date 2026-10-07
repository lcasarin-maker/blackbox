"""Prueba de cierre de DEBT-GUARDIA-PROCESO-REINICIO-NO-LIMPIO-01.

Verifica que el servicio systemd bb-guardia-proceso.service tenga configurada la
política de reinicio 'on-failure' para reiniciar automáticamente el servicio cuando
ocurra una parada no limpia (SIGKILL, crash, error), sin reiniciar tras una parada
limpia (exit code 0 / stop deliberado).
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
UNIT_FILE = ROOT / "systemd" / "bb-guardia-proceso.service"


def test_unit_file_exists():
    assert UNIT_FILE.is_file(), f"No se encontró el archivo de unit: {UNIT_FILE}"


def test_unit_restart_policy_is_on_failure():
    content = UNIT_FILE.read_text(encoding="utf-8")
    lines = [line.strip() for line in content.splitlines()]

    # Verificar que contenga 'Restart=on-failure'
    restart_lines = [l for l in lines if l.startswith("Restart=")]
    assert restart_lines, "El archivo de unit debe definir una directiva Restart="
    assert restart_lines[0] == "Restart=on-failure", (
        f"Se esperaba 'Restart=on-failure', encontrado: {restart_lines[0]}"
    )


def test_unit_execstart_and_restartsec():
    content = UNIT_FILE.read_text(encoding="utf-8")
    assert "ExecStart=%h/projects/blackbox/bin/bb-guardia-proceso" in content
    assert "RestartSec=" in content
