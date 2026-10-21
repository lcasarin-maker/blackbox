"""Assess thermal-channel capture separately from clock-cap A/B performance."""
from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from tools import verify_gpu_clock_cap_ab as ab_verifier
from tools.capture_io import read_regular_bytes, strict_json_loads

ROOT = Path(__file__).resolve().parents[1]
MAX_CAPTURE_BYTES = 4 * 1024 * 1024
THERMAL_CAPTURE = ROOT / "tasks/evidence/DELTA-FORUM-THERMAL-TELEMETRY-COVERAGE-01/prototype-capture.json"


def _result(status: str, reason: str, files: list[str], checks: dict[str, str]) -> dict[str, Any]:
    return {"status": status, "reason": reason, "files": files, "checks": checks,
            "fail": int(status == "fail"), "could_not_run": int(status == "unknown")}


TRIP_TYPES = frozenset({"passive", "hot", "critical"})


def _oem_threshold(zones: list[Any]) -> str:
    """Firmware trip points are the OEM-declared limits; a zone at or above its lowest one fails."""
    seen = False
    for zone in zones:
        if not isinstance(zone, dict):
            continue
        trips = [trip.get("temperature", {}).get("value") for trip in zone.get("trip_points", [])
                 if isinstance(trip, dict) and trip.get("type", {}).get("value") in TRIP_TYPES
                 and trip.get("temperature", {}).get("status") == "ok"]
        limits = [value for value in trips if isinstance(value, (int, float)) and not isinstance(value, bool)]
        if not limits:
            continue
        seen = True
        reading = zone.get("temperature", {})
        if reading.get("status") == "ok" and isinstance(reading.get("value"), (int, float)) \
                and reading["value"] >= min(limits):
            return "fail"
    return "pass" if seen else "unknown"


def _unidentified_sensors(hwmon: list[Any], zones: list[Any]) -> list[str]:
    """Paths of hwmon temp inputs identified neither by temp*_label nor by a thermal_zone*/type.

    Vote of Luis 2026-10-20: an unlabelled input counts as identified only through the kernel's
    thermal_hwmon bridge, which registers ONE hwmon device named after the zone type and gives the
    i-th zone of that type (in zone-id order) the input temp{i}_input. The bridge is accepted only
    when exactly one hwmon device carries that name and its input count equals the zone count of
    that type; anything else (no zone of that type, ambiguous name, count mismatch) stays unidentified.
    """
    by_type: dict[str, list[str]] = {}
    for zone in sorted((z for z in zones if isinstance(z, dict)),
                       key=lambda z: int(m.group(1)) if (m := re.search(r"([0-9]+)$", str(z.get("name")))) else -1):
        kind = zone.get("type", {})
        if isinstance(kind, dict) and kind.get("status") == "ok" and str(kind.get("value", "")).strip():
            by_type.setdefault(str(kind["value"]).strip(), []).append(str(zone.get("name")))
    devices = [device for device in hwmon if isinstance(device, dict)]
    names = [device.get("chip_name", {}).get("value") if isinstance(device.get("chip_name"), dict)
             and device["chip_name"].get("status") == "ok" else None for device in devices]
    missing: list[str] = []
    for device, name in zip(devices, names):
        sensors = [sensor for sensor in device.get("temperature_inputs", []) if isinstance(sensor, dict)]
        bridged = by_type.get(str(name).strip()) if name is not None and names.count(name) == 1 else None
        for sensor in sensors:
            if sensor.get("label", {}).get("status") == "ok":
                continue
            index = re.search(r"temp([0-9]+)_input$", str(sensor.get("path", "")))
            if bridged is not None and len(bridged) == len(sensors) and index \
                    and 1 <= int(index.group(1)) <= len(bridged):
                continue
            missing.append(str(sensor.get("path", f"{device.get('name')}/<unnamed temp input>")))
    return missing


def _same_window(data: dict[str, Any], ab_path: Path) -> tuple[str, str]:
    """The thermal inventory must be taken inside the A/B capture on the same OEM/product."""
    parsed = ab_verifier._capture(ab_path)
    try:
        stamp = datetime.fromisoformat(str(data.get("captured_at_utc")).replace("Z", "+00:00"))
    except ValueError:
        return "unknown", "thermal inventory lacks a parseable captured_at_utc"
    if parsed is None or stamp.tzinfo is None:
        return "unknown", "A/B capture or thermal timestamp unavailable for the window comparison"
    rows = parsed[1]
    first = datetime.fromisoformat(rows[0]["captured_at"].replace("Z", "+00:00"))
    last = datetime.fromisoformat(rows[-1]["captured_at"].replace("Z", "+00:00"))
    if not first <= stamp <= last:
        return "fail", "thermal inventory was captured outside the A/B evidence window"
    dmi = data["host"]["dmi"]
    vendor, product = (str(dmi[key].get("value", "")).strip() for key in ("sys_vendor", "product_name"))
    for row in rows:
        if ab_verifier._runs_program(row, "dmidecode"):
            found = {key: match.group(1).strip() for key in ("Manufacturer", "Product Name")
                     if (match := re.search(rf"(?im)^\s*{key}:\s*(.+)$", row["stdout"]))}
            if found.get("Manufacturer") == vendor and found.get("Product Name") == product:
                return "pass", ""
    return "fail", "thermal inventory and A/B capture name different OEM/product identities"


def verify(evidence: str | Path | None = None, ab_evidence: str | Path | None = None) -> dict[str, Any]:
    """Pass only when inventory, labels, OEM threshold and the composed A/B verifier agree on one window."""
    capture = Path(evidence) if evidence else THERMAL_CAPTURE
    checks = {key: "unknown" for key in ("thermal_inventory", "oem_identity", "sensor_labels", "matched_clock_runs",
                                         "rollback", "oem_threshold", "same_window")}
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
    sensors = [sensor for device in hwmon if isinstance(device, dict)
               for sensor in device.get("temperature_inputs", []) if isinstance(sensor, dict)]
    unidentified = _unidentified_sensors(hwmon, zones)
    if sensors and not unidentified:
        checks["sensor_labels"] = "pass"
    ab_dir = Path(ab_evidence) if ab_evidence is not None else ab_verifier.ROOT / "tasks/evidence" / ab_verifier.FINDING
    ab = ab_verifier.verify(ab_dir)
    files = [str(capture), *ab["files"]]
    # The A/B verifier owns matched runs and the stock/cap/rollback readback order; its verdict is not re-derived here.
    checks["matched_clock_runs"] = ab["status"] if ab["status"] in ("pass", "fail") else "unknown"
    checks["rollback"] = "pass" if ab["status"] == "pass" else "unknown"
    checks["oem_threshold"] = _oem_threshold(zones)
    checks["same_window"], window_reason = _same_window(data, ab_dir / "commands.json")
    if ab["status"] == "fail":
        return _result("fail", f"composed A/B verifier failed: {ab['reason']}", files, checks)
    if checks["oem_threshold"] == "fail":
        return _result("fail", "a thermal zone reads at or above its OEM firmware trip point", files, checks)
    if checks["same_window"] == "fail":
        return _result("fail", window_reason, files, checks)
    if ab["status"] != "pass":
        return _result("unknown", f"thermal inventory is observational only; matched clock-cap/workload runs, OEM-safe threshold, and applied-policy rollback readback are missing (A/B: {ab['reason']})", files, checks)
    if checks["sensor_labels"] != "pass":
        return _result("unknown", "hwmon temperature inputs lack labels and no thermal_zone type identifies them; "
                       f"zones cannot be tied to OEM sensors (unidentified: {', '.join(unidentified) or 'no inputs'})",
                       files, checks)
    if checks["oem_threshold"] != "pass":
        return _result("unknown", "no OEM-safe threshold: no thermal zone exposes a passive/hot/critical trip point", files, checks)
    if checks["same_window"] != "pass":
        return _result("unknown", window_reason, files, checks)
    return _result("pass", f"thermal inventory, labels, OEM trip points and the composed A/B verifier agree on one window; {ab['reason']}", files, checks)
