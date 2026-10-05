"""Assess thermal-channel capture separately from clock-cap A/B performance."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from tools.capture_io import read_regular_bytes, strict_json_loads

ROOT = Path(__file__).resolve().parents[1]
MAX_CAPTURE_BYTES = 4 * 1024 * 1024
THERMAL_CAPTURE = ROOT / "tasks/evidence/DELTA-FORUM-THERMAL-TELEMETRY-COVERAGE-01/prototype-capture.json"


def _result(status: str, reason: str, files: list[str], checks: dict[str, str]) -> dict[str, Any]:
    return {"status": status, "reason": reason, "files": files, "checks": checks,
            "fail": int(status == "fail"), "could_not_run": int(status == "unknown")}


def verify(evidence: str | Path | None = None) -> dict[str, Any]:
    """Validate channel inventory consistency and preserve unrun experiment as unknown."""
    capture = Path(evidence) if evidence else THERMAL_CAPTURE
    checks = {key: "unknown" for key in ("thermal_inventory", "oem_identity", "sensor_labels", "matched_clock_runs", "rollback")}
    try:
        raw = read_regular_bytes(capture, MAX_CAPTURE_BYTES)
        if len(raw) > MAX_CAPTURE_BYTES:
            return _result("fail", "raw thermal inventory exceeds the 4 MiB input bound", [str(capture)], checks)
        data = strict_json_loads(raw.decode("utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError, RecursionError) as exc:
        return _result("unknown", f"raw thermal inventory unavailable: {exc}", [str(capture)], checks)
    if not isinstance(data, dict):
        return _result("fail", "raw thermal inventory must be a JSON object", [str(capture)], checks)
    zones = data.get("thermal_zones")
    hwmon = data.get("hwmon")
    zone_scan = data.get("thermal_zone_scan")
    hwmon_scan = data.get("hwmon_scan")
    if not isinstance(zones, list) or not isinstance(hwmon, list) or not isinstance(zone_scan, dict) or not isinstance(hwmon_scan, dict):
        return _result("fail", "thermal capture does not match tools.thermal_coverage schema", [str(capture)], checks)
    if zone_scan.get("count") != len(zones) or hwmon_scan.get("count") != len(hwmon):
        checks["thermal_inventory"] = "fail"
        return _result("fail", "captured thermal counts disagree with raw arrays", [str(capture)], checks)
    if data.get("could_not_run", 1) != 0 or data.get("status") != "observed":
        return _result("unknown", "thermal inventory has unavailable channels or incomplete scan", [str(capture)], checks)
    checks["thermal_inventory"] = "pass"
    host = data.get("host")
    dmi = host.get("dmi") if isinstance(host, dict) else None
    identity = (dmi.get("sys_vendor"), dmi.get("product_name"), dmi.get("product_version")) if isinstance(dmi, dict) else ()
    if not identity or any(not isinstance(item, dict) or item.get("status") != "ok" for item in identity):
        return _result("unknown", "OEM/product/revision identity is incomplete", [str(capture)], checks)
    checks["oem_identity"] = "pass"
    labels = [sensor.get("label", {}).get("status") == "ok"
              for device in hwmon if isinstance(device, dict)
              for sensor in device.get("temperature_inputs", []) if isinstance(sensor, dict)]
    if labels and all(labels):
        checks["sensor_labels"] = "pass"
    return _result("unknown", "thermal inventory is observational only; matched clock-cap/workload runs, OEM-safe threshold, and applied-policy rollback readback are missing", [str(capture)], checks)
