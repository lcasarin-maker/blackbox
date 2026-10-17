"""Voto de Luis 2026-10-16: el tradeoff pasa sólo si inventario, labels y el A/B compuesto pasan en la misma ventana.

Fixtures sintéticas: la A/B sana es `_scenario()` de test_cobertura_g3_hardware (con su misma costura `_csv_policy`,
porque GB10 no expone el rango -lgc activo); el inventario térmico extiende el `_capture` de los tests semánticos.
Nada sale del host vivo.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from test_clock_tradeoff_observation_semantics import _capture as _thermal_base
from test_cobertura_g3_hardware import _bench, _evidence, _fake_policy, _scenario
from tools import verify_clock_cap_tradeoff as tradeoff
from tools import verify_gpu_clock_cap_ab as gpu

INSIDE_WINDOW = "2026-10-04T00:00:20+00:00"  # _scenario() fecha sus filas desde 2026-10-04T00:00:00, 2 s por fila


@pytest.fixture(autouse=True)
def policy(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(gpu, "_csv_policy", _fake_policy)


def _thermal(*, stamp: str = INSIDE_WINDOW, label: str = "ok", trips: bool = True,
             unavailable: int = 0, zone_c: float = 60.0) -> dict[str, Any]:
    capture = _thermal_base(labels=[{"status": label, "value": "GPU"}], unavailable=unavailable)
    trip = [{"type": {"status": "ok", "value": "critical"},
             "temperature": {"status": "ok", "value": 104.8}}] if trips else []
    capture["thermal_zones"] = [{"name": "thermal_zone0", "type": {"status": "ok", "value": "acpitz"},
                                 "temperature": {"status": "ok", "value": zone_c}, "trip_points": trip}]
    capture["thermal_zone_scan"] = {"count": 1}
    capture["captured_at_utc"] = stamp
    return capture


def _run(tmp_path: Path, thermal: dict[str, Any], ab_rows: list[dict[str, Any]] | None) -> dict[str, Any]:
    thermal_path = tmp_path / "thermal.json"
    thermal_path.write_text(json.dumps(thermal), encoding="utf-8")
    ab_dir = tmp_path / "ab"
    ab_dir.mkdir()
    if ab_rows is not None:
        _evidence(ab_dir, ab_rows)
    return tradeoff.verify(thermal_path, ab_dir)


def test_pass_when_inventory_labels_threshold_and_composed_ab_share_one_window(tmp_path: Path) -> None:
    result = _run(tmp_path, _thermal(), _scenario())
    assert result["status"] == "pass" and result["fail"] == 0 and result["could_not_run"] == 0, result
    assert set(result["checks"].values()) == {"pass"}, result
    assert "throughput=100.000/80.000 tok/s" in result["reason"], result


def test_ab_missing_stays_unknown(tmp_path: Path) -> None:
    result = _run(tmp_path, _thermal(), None)
    assert result["status"] == "unknown" and result["could_not_run"] == 1, result
    assert result["checks"]["matched_clock_runs"] == "unknown" and result["checks"]["rollback"] == "unknown", result


def test_ab_failure_propagates_as_fail(tmp_path: Path) -> None:
    result = _run(tmp_path, _thermal(), _scenario(capped_clock=2200))
    assert result["status"] == "fail" and "exceeded the applied cap" in result["reason"], result
    assert result["checks"]["matched_clock_runs"] == "fail", result


def test_ab_without_rollback_readback_stays_unknown(tmp_path: Path) -> None:
    rows = _scenario()[:-1]  # se quita el readback posterior al rollback 300,2800
    result = _run(tmp_path, _thermal(), rows)
    assert result["status"] == "unknown" and "readbacks" in result["reason"], result
    assert result["checks"]["rollback"] == "unknown", result


def test_window_mismatch_is_fail(tmp_path: Path) -> None:
    result = _run(tmp_path, _thermal(stamp="2026-10-03T17:23:11+00:00"), _scenario())
    assert result["status"] == "fail" and "outside the A/B evidence window" in result["reason"], result
    assert result["checks"]["same_window"] == "fail", result


def test_identity_mismatch_is_fail(tmp_path: Path) -> None:
    thermal = _thermal()
    thermal["host"]["dmi"]["product_name"] = {"status": "ok", "value": "Other product"}
    result = _run(tmp_path, thermal, _scenario())
    assert result["status"] == "fail" and "different OEM/product" in result["reason"], result


def test_thermal_inventory_missing_or_incomplete_is_not_pass(tmp_path: Path) -> None:
    ab_dir = tmp_path / "ab"
    ab_dir.mkdir()
    _evidence(ab_dir, _scenario())
    missing = tradeoff.verify(tmp_path / "absent.json", ab_dir)
    assert missing["status"] == "unknown" and missing["checks"]["thermal_inventory"] == "unknown", missing
    (tmp_path / "x").mkdir()
    incomplete = _run(tmp_path / "x", _thermal(unavailable=1), _scenario())
    assert incomplete["status"] == "unknown" and incomplete["checks"]["thermal_inventory"] == "unknown", incomplete


def test_label_missing_stays_unknown(tmp_path: Path) -> None:
    result = _run(tmp_path, _thermal(label="absent"), _scenario())
    assert result["status"] == "unknown" and "lack labels" in result["reason"], result
    assert result["checks"]["sensor_labels"] == "unknown" and result["checks"]["matched_clock_runs"] == "pass", result


def test_oem_threshold_missing_is_unknown_and_exceeded_is_fail(tmp_path: Path) -> None:
    (tmp_path / "a").mkdir()
    (tmp_path / "b").mkdir()
    missing = _run(tmp_path / "a", _thermal(trips=False), _scenario())
    assert missing["status"] == "unknown" and "OEM-safe threshold" in missing["reason"], missing
    hot = _run(tmp_path / "b", _thermal(zone_c=105.0), _scenario(capped_bench=_bench(80)))
    assert hot["status"] == "fail" and "trip point" in hot["reason"], hot
