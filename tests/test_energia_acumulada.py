"""Tests para FEATURE-ENERGIA-ACUMULADA-DEL-ENCHUFE-01."""
from __future__ import annotations

from datetime import datetime, timezone

from tools.energia_acumulada import resumen_energia


def test_energia_integrada_trapecio_y_contador():
    t0 = datetime(2026, 11, 26, 12, 0, 0, tzinfo=timezone.utc).timestamp()
    # Trapecio entre 100 W y 200 W durante 1800 s (0.5 h) => media 150 W * 0.5 h = 75 Wh
    # Un rectángulo con p1=100 W daría 50 Wh; la aserción exacta exige trapecio.
    filas = [
        {"epoch": t0, "ok": True, "potencia_w": 100.0},
        {"epoch": t0 + 300.0, "ok": True, "potencia_w": 116.6667},
        {"epoch": t0 + 600.0, "ok": True, "potencia_w": 133.3333},
        {"epoch": t0 + 900.0, "ok": True, "potencia_w": 150.0},
        {"epoch": t0 + 1200.0, "ok": True, "potencia_w": 166.6667},
        {"epoch": t0 + 1500.0, "ok": True, "potencia_w": 183.3333},
        {"epoch": t0 + 1800.0, "ok": True, "potencia_w": 200.0},
    ]
    res = resumen_energia(filas, ahora=t0 + 1800.0, max_hueco_s=350.0)
    assert res["energia_fuente"] == "integrada"
    assert res["wh_ultima_hora"] == 75.0
    assert res["potencia_min_w"] == 100.0
    assert res["potencia_max_w"] == 200.0
    assert res["huecos"] == 0

    filas_cnt = [
        {"epoch": t0, "ok": True, "potencia_w": 100.0, "energia_total_wh": 1000.0},
        {"epoch": t0 + 300.0, "ok": True, "potencia_w": 120.0, "energia_total_wh": 1012.5},
    ]
    res_cnt = resumen_energia(filas_cnt, ahora=t0 + 300.0, max_hueco_s=350.0)
    assert res_cnt["energia_fuente"] == "contador"
    assert res_cnt["wh_ultima_hora"] == 12.5


def test_control_negativo_hueco_y_ok_false_no_rellenan_ni_suman_cero():
    t0 = datetime(2026, 11, 26, 12, 0, 0, tzinfo=timezone.utc).timestamp()
    filas = [
        {"epoch": t0, "ok": True, "potencia_w": 100.0},
        {"epoch": t0 + 60.0, "ok": True, "potencia_w": 100.0},
        {"epoch": t0 + 120.0, "ok": False, "potencia_w": 0.0},  # fallo no cuenta como 0 W
        {"epoch": t0 + 720.0, "ok": True, "potencia_w": 100.0},  # hueco de 660 s (> 300 s)
        {"epoch": t0 + 780.0, "ok": True, "potencia_w": 100.0},
    ]
    res = resumen_energia(filas, ahora=t0 + 780.0, max_hueco_s=300.0)
    assert res["huecos"] >= 1
    # Solo dos tramos de 60 s a 100 W = 120 s / 3600 * 100 = 3.333 Wh (nunca 780 s = 21.667 Wh)
    assert res["wh_ultima_hora"] == 3.333
    assert res["ultima_hora"]["cobertura_pct"] < 10.0
