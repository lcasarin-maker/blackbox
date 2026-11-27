"""Pruebas de guardrail de CPU por clase del portero (FEATURE-GUARDRAIL-CPU-POR-CLASE-DEL-PORTERO-01)."""
from __future__ import annotations

import subprocess
import pytest


def cpu_quota_para_clase(clase: str, modo: str) -> str | None:
    """Devuelve CPUQuota= solo para clases acotadas cuando el interruptor esta en actuar."""
    if modo != "actuar":
        return None
    if clase == "suite":
        return "CPUQuota=800%"
    return None


def test_cpu_quota_modo_actuar_vs_off_y_observar() -> None:
    assert cpu_quota_para_clase("suite", "off") is None
    assert cpu_quota_para_clase("suite", "observar") is None
    assert cpu_quota_para_clase("suite", "actuar") == "CPUQuota=800%"
    assert cpu_quota_para_clase("escritorio", "actuar") is None


def test_systemd_run_acepta_cpu_quota_en_scope_de_usuario() -> None:
    r = subprocess.run(
        ["systemd-run", "--user", "--scope", "-p", "CPUQuota=200%", "cat", "/proc/self/cgroup"],
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    if r.returncode != 0:
        pytest.skip(f"systemd --user no disponible: {r.stderr}")
    assert ".scope" in r.stdout
