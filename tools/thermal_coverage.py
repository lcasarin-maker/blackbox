"""Inventory readable thermal channels without assigning a safe temperature."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import platform
import re
import sys
from typing import Any

from tools.host_diagnostics import read_names, read_text


def _numeric_suffix(path: Path) -> int:
    match = re.search(r"([0-9]+)$", path.name)
    return int(match.group(1)) if match else -1


def _channel(path: Path, *, label_path: Path | None = None,
             divisor: int = 1000, unit: str = "celsius") -> dict[str, Any]:
    value = read_text(path)
    label = read_text(label_path) if label_path is not None and label_path.exists() else None
    result: dict[str, Any] = {"path": str(path), "read": value}
    if label_path is not None:
        result["label_path"] = str(label_path)
        result["label"] = label or {"status": "absent", "error": "label unavailable"}
    if value["status"] == "ok":
        try:
            result["value_raw"] = int(value["value"])
            result["value"] = result["value_raw"] / divisor
            result["unit"] = unit
            result["status"] = "ok"
        except (TypeError, ValueError):
            result["status"] = "malformed"
            result["error"] = "sensor value is not an integer"
    else:
        result["status"] = value["status"]
    return result


def capture(root: Path = Path("/")) -> dict[str, Any]:
    thermal = root / "sys/class/thermal"
    zones: list[dict[str, Any]] = []
    thermal_listing = read_names(thermal)
    if thermal_listing["status"] == "ok":
        zone_paths = sorted((thermal / name for name in thermal_listing["value"]
                             if re.fullmatch(r"thermal_zone[0-9]+", name)), key=_numeric_suffix)
        zone_scan_status = "ok" if zone_paths else "no_thermal_zones"
        zone_scan_error = None
    else:
        zone_paths, zone_scan_status = [], "could_not_run"
        zone_scan_error = thermal_listing.get("error")
    for zone in zone_paths:
        trip_listing = read_names(zone)
        trip_paths = ([zone / name for name in trip_listing["value"]
                       if re.fullmatch(r"trip_point_[0-9]+_temp", name)]
                      if trip_listing["status"] == "ok" else [])
        trip_points = [
            {"type": read_text(path.with_name(path.name.replace("_temp", "_type"))),
             "temperature": _channel(path)} for path in sorted(trip_paths)]
        zones.append({"name": zone.name,
                      "type": read_text(zone / "type"),
                      "temperature": _channel(zone / "temp"),
                      "trip_point_scan": {"status": trip_listing["status"],
                                          "error": trip_listing.get("error"),
                                          "count": len(trip_points)},
                      "trip_points": trip_points})

    hwmon: list[dict[str, Any]] = []
    hwmon_root = root / "sys/class/hwmon"
    hwmon_listing = read_names(hwmon_root)
    if hwmon_listing["status"] == "ok":
        hwmon_paths = sorted((hwmon_root / name for name in hwmon_listing["value"]
                              if re.fullmatch(r"hwmon[0-9]+", name)), key=_numeric_suffix)
        hwmon_scan_status = "ok" if hwmon_paths else "no_hwmon_devices"
        hwmon_error = None
    else:
        hwmon_paths, hwmon_scan_status = [], "could_not_run"
        hwmon_error = hwmon_listing.get("error")
    for device in hwmon_paths:
        temperature_inputs = []
        for path in sorted(device.glob("temp[0-9]*_input")):
            label_path = path.with_name(path.name.replace("_input", "_label"))
            temperature_inputs.append(_channel(path, label_path=label_path))
        fan_inputs = []
        for path in sorted(device.glob("fan[0-9]*_input")):
            label_path = path.with_name(path.name.replace("_input", "_label"))
            fan_inputs.append(_channel(path, label_path=label_path, divisor=1, unit="rpm"))
        hwmon.append({"name": device.name, "chip_name": read_text(device / "name"),
                      "temperature_inputs": temperature_inputs, "fan_inputs": fan_inputs})

    unavailable = int(zone_scan_status != "ok") + int(hwmon_scan_status == "could_not_run")
    unavailable += sum(int(zone["temperature"].get("status") != "ok") for zone in zones)
    hwmon_inputs = [item for device in hwmon
                    for item in (*device["temperature_inputs"], *device["fan_inputs"])]
    unavailable += sum(int(item.get("status") != "ok") for item in hwmon_inputs)
    unavailable += sum(int(zone["trip_point_scan"]["status"] != "ok")
                        + sum(int(point["type"].get("status") != "ok")
                              + int(point["temperature"].get("status") != "ok")
                              for point in zone["trip_points"])
                        for zone in zones)
    no_sensor = not zones and not hwmon_inputs
    if no_sensor:
        unavailable += 1
    return {
        "schema": 1,
        "captured_at_utc": datetime.now(timezone.utc).isoformat(),
        "host": {"system": platform.system(), "release": platform.release(),
                 "machine": platform.machine(),
                 "dmi": {name: read_text(root / "sys/class/dmi/id" / name)
                         for name in ("sys_vendor", "product_name", "product_version",
                                      "board_name")},
                 "dgx_release": read_text(root / "etc/dgx-release")},
        "thermal_zones": zones,
        "hwmon": hwmon,
        "thermal_zone_scan": {"status": zone_scan_status, "error": zone_scan_error,
                              "count": len(zones)},
        "hwmon_scan": {"status": hwmon_scan_status, "error": hwmon_error,
                       "count": len(hwmon)},
        "scan_errors": {"thermal": zone_scan_error, "hwmon": hwmon_error},
        "no_sensor_detected": no_sensor,
        "could_not_run": unavailable,
        "assessment": "coverage_only; no thermal safety conclusion",
        "status": "partial" if unavailable else "observed",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path("/"), help="host root; fixture use")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    record = capture(args.root)
    payload = json.dumps(record, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload, encoding="utf-8")
    else:
        sys.stdout.write(payload)
    return 0 if record["could_not_run"] == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
