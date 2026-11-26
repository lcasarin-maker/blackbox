"""Tests para FEATURE-METRICAS-LOG-Y-CORRELACION-CONSUMO-CARGA-01."""
from __future__ import annotations

from tools.correlacion_consumo_carga import (
    anexar_log_con_tope,
    construir_fila_alineada,
    informe_correlacion,
)


def test_fila_alineada_rotacion_y_correlacion_con_desfase(tmp_path):
    f0 = construir_fila_alineada(1000.0, enchufe={"potencia_w": 32.0}, gpu={})
    assert f0["gpu_util_pct"] == "NOT_COLLECTED"
    assert f0["gpu_util_pct"] != 0
    assert f0["regimen"] == "reposo"

    log = tmp_path / "metricas.jsonl"
    for i in range(20):
        anexar_log_con_tope(log, construir_fila_alineada(1000.0 + i * 5, enchufe={"potencia_w": 40.0}), max_bytes=500, copias=2)
    assert log.with_name("metricas.jsonl.1").exists()

    # Serie con desfase de +1 paso entre carga GPU y potencia del enchufe
    cargas = [20.0, 30.0, 50.0, 70.0, 90.0, 60.0, 40.0, 80.0]
    pots = [60.0, 70.0, 90.0, 120.0, 150.0, 180.0, 130.0, 100.0]
    filas_gpu = [
        construir_fila_alineada(
            2000.0 + i * 5,
            enchufe={"potencia_w": pots[i]},
            gpu={"gpu_util_pct": cargas[i]},
        )
        for i in range(len(cargas))
    ]
    inf = informe_correlacion(filas_gpu, metrica_carga="gpu_util_pct", desfases_pasos=(0, 1), min_muestras=5)
    assert inf["por_regimen"]["gpu"]["estado"] == "OK"
    assert inf["por_regimen"]["gpu"]["lag_pasos"] == 1
    assert inf["por_regimen"]["gpu"]["pearson"] > 0.9


def test_control_negativo_pocas_muestras_y_series_sin_relacion():
    una = [construir_fila_alineada(1000.0, enchufe={"potencia_w": 50.0}, gpu={"gpu_util_pct": 80.0})]
    inf_una = informe_correlacion(una, min_muestras=5)
    assert inf_una["por_regimen"]["gpu"]["estado"] == "COULD_NOT_RUN"

    # Series ortogonales / sin relacion dan correlacion baja
    cargas = [20.0, 80.0, 20.0, 80.0, 20.0, 80.0]
    pots = [100.0, 100.0, 150.0, 150.0, 100.0, 100.0]
    filas_no_rel = [
        construir_fila_alineada(3000.0 + i * 5, enchufe={"potencia_w": pots[i]}, gpu={"gpu_util_pct": cargas[i]})
        for i in range(len(cargas))
    ]
    inf_no = informe_correlacion(filas_no_rel, desfases_pasos=(0,), min_muestras=5)
    assert abs(inf_no["por_regimen"]["gpu"]["pearson"]) < 0.2
