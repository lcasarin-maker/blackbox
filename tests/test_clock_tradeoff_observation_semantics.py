"""Thermal inventory can describe observability but never closes the clock experiment."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from tools import verify_clock_cap_tradeoff as tradeoff


def _capture(*, labels: list[Any] | None = None, unavailable: int = 0,
             identity_ok: bool = True) -> dict[str, Any]:
    dmi = {key: {"status": "ok", "value": value} for key, value in (
        ("sys_vendor", "OEM"), ("product_name", "GB10"), ("product_version", "1.0"))}
    if not identity_ok:
        dmi["product_version"] = {"status": "could_not_run", "error": "missing"}
    sensors = [] if labels is None else [{"label": label} for label in labels]
    hwmon = [{"temperature_inputs": sensors}]
    return {
        "thermal_zones": [], "hwmon": hwmon,
        "thermal_zone_scan": {"count": 0}, "hwmon_scan": {"count": 1},
        "could_not_run": unavailable, "status": "observed",
        "host": {"dmi": dmi},
    }


def _verify(tmp_path: Path, value: Any) -> dict[str, Any]:
    path = tmp_path / "capture.json"
    path.write_text(json.dumps(value), encoding="utf-8")
    return tradeoff.verify(path)


def test_reader_errors_and_oversize_are_not_reported_as_observed(tmp_path: Path) -> None:
    assert tradeoff.verify(tmp_path / "missing.json")["status"] == "unknown"
    oversized = tmp_path / "oversized.json"
    oversized.write_bytes(b" " * (tradeoff.MAX_CAPTURE_BYTES + 1))
    result = tradeoff.verify(oversized)
    assert result["status"] == "fail" and "exceeds" in result["reason"]


def test_inventory_requires_schema_equal_counts_and_observed_scan(tmp_path: Path) -> None:
    assert _verify(tmp_path, [])["status"] == "fail"
    malformed = _capture()
    malformed["thermal_zone_scan"] = []
    assert _verify(tmp_path, malformed)["status"] == "fail"
    capture = _capture()
    capture["hwmon_scan"] = {"count": 0}
    result = _verify(tmp_path, capture)
    assert result["status"] == "fail" and "counts disagree" in result["reason"]

    capture = _capture(unavailable=1)
    result = _verify(tmp_path, capture)
    assert result["status"] == "unknown" and result["checks"]["thermal_inventory"] == "unknown"


def test_oem_labels_and_experiment_remain_separate_checks(tmp_path: Path) -> None:
    capture = _capture(labels=[{"status": "ok", "value": "GPU"}])
    result = _verify(tmp_path, capture)
    assert result["status"] == "unknown"
    assert result["checks"]["thermal_inventory"] == "pass"
    assert result["checks"]["oem_identity"] == "pass"
    assert result["checks"]["sensor_labels"] == "pass"
    assert result["checks"]["matched_clock_runs"] == "unknown"

    capture = _capture(labels=[{"status": "absent"}], identity_ok=False)
    result = _verify(tmp_path, capture)
    assert result["status"] == "unknown" and result["checks"]["oem_identity"] == "unknown"

    capture = _capture(labels=[])
    result = _verify(tmp_path, capture)
    assert result["checks"]["sensor_labels"] == "unknown"
