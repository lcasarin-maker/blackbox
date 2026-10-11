"""Valida el reinicio de la guardia tras una salida limpia o inesperada.

Verifica que el servicio systemd bb-guardia-proceso.service tenga configurada la
política 'always' para recuperar salidas limpias como SIGTERM externo además de
fallos. systemd sigue suprimiendo el reinicio cuando el operador ejecuta
`systemctl stop` explícitamente.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
UNIT_FILE = ROOT / "systemd" / "bb-guardia-proceso.service"


def test_unit_file_exists():
    assert UNIT_FILE.is_file(), f"No se encontró el archivo de unit: {UNIT_FILE}"


def test_unit_restart_policy_is_always():
    content = UNIT_FILE.read_text(encoding="utf-8")
    lines = [line.strip() for line in content.splitlines()]

    # SIGTERM externo se considera salida limpia y no activa on-failure.
    restart_lines = [l for l in lines if l.startswith("Restart=")]
    assert restart_lines, "El archivo de unit debe definir una directiva Restart="
    assert restart_lines[0] == "Restart=always", (
        f"Se esperaba 'Restart=always', encontrado: {restart_lines[0]}"
    )


def test_unit_execstart_and_restartsec():
    content = UNIT_FILE.read_text(encoding="utf-8")
    assert "ExecStart=%h/projects/blackbox/bin/bb-guardia-proceso" in content
    assert "RestartSec=" in content
