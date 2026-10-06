"""Cierre de DEBT-RENDERER-PROBE-SLEEP-01: el probe no debe tener time.sleep ni real_sleep(."""
import pathlib

PROBE = pathlib.Path(
    "tasks/evidence/OPEN-96-CLASSIFICATION-2026-10-04/publication-sunset/renderer-delayed-probe.py"
)


def test_renderer_probe_sin_sleeps_fijos():
    texto = PROBE.read_text(encoding="utf-8")
    assert "time.sleep" not in texto
    assert "real_sleep(" not in texto
