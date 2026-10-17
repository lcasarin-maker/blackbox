"""Los dos limites que impiden que el verificador de topes de reloj dé `pass` en este equipo.

Son el cierre de DEBT-RELOJ-VERIFICADOR-ETIQUETAS-DE-SENSORES-INCOMPLETAS-01 y
DEBT-RELOJ-VERIFICADOR-SIN-LECTURA-DEL-RANGO-LGC-APLICADO-01. Miden el equipo real, no fixtures:
mientras su ficha siga abierta `tests/conftest.py` las marca xfail (tests/known_failures.json).
"""
from __future__ import annotations

from tools import verify_clock_cap_tradeoff, verify_gpu_clock_cap_ab


def test_etiquetas_de_sensores_completas_en_la_captura_real():
    assert verify_clock_cap_tradeoff.verify()["checks"]["sensor_labels"] == "pass"


def test_hay_lectura_nativa_del_rango_lgc_aplicado():
    assert verify_gpu_clock_cap_ab._csv_policy({"stdout": "300, 2200"}) is not None
