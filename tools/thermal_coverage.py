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
from tools.incident_report import FORENSE_DIR, firmware_recogido


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


def _fan_index(path: Path) -> int:
    return int(path.name[len("fan"):-len("_input")])  # caller already fullmatched fan[0-9]+_input


def acpi_fan(root: Path = Path("/"), forense_dir: str = FORENSE_DIR) -> dict[str, Any]:
    """RPM per fan from every hwmon whose `name` is `acpi_fan` (FEATURE-FAN-RPM-LEER-ACPI-FAN-DONDE-EXISTA-01).

    A read of 0 is a stopped fan and is returned as 0 rpm; a missing or unreadable
    value is `NOT_COLLECTED` with its reason and `rpm: None`, never 0.
    """
    dmi = root / "sys/class/dmi/id"
    identidad: dict[str, Any] = {name: read_text(dmi / name)
                                 for name in ("sys_vendor", "product_name", "bios_version")}
    identidad["firmware"] = firmware_recogido(forense_dir)
    hwmon_root = root / "sys/class/hwmon"
    listing = read_names(hwmon_root)
    ventiladores: list[dict[str, Any]] = []
    name_ilegible: list[str] = []
    motivo = None
    if listing["status"] != "ok":
        motivo = f"NOT_COLLECTED: no se pudo listar {hwmon_root}: {listing.get('error')}"
    else:
        devices = sorted((hwmon_root / n for n in listing["value"] if re.fullmatch(r"hwmon[0-9]+", n)),
                         key=_numeric_suffix)
        fans = []
        for device in devices:
            chip = read_text(device / "name")
            if chip["status"] != "ok":
                name_ilegible.append(f"{device.name}: {chip.get('error')}")
            elif chip["value"] == "acpi_fan":
                fans.append(device)
        if not fans:
            motivo = "NOT_COLLECTED: sin hwmon acpi_fan"
            if name_ilegible:
                motivo += f" ({len(name_ilegible)} hwmon con name ilegible; no se descarta que alguno lo sea)"
        for device in fans:
            inputs = sorted((p for p in device.glob("fan*_input") if re.fullmatch(r"fan[0-9]+_input", p.name)),
                            key=_fan_index)
            if not inputs:
                ventiladores.append({"hwmon": device.name, "canal": None, "path": str(device), "rpm": None,
                                     "estado": "NOT_COLLECTED: hwmon acpi_fan sin fan*_input"})
            for path in inputs:
                channel = _channel(path, divisor=1, unit="rpm")
                rpm, estado = None, None
                if channel["status"] != "ok":
                    estado = f"NOT_COLLECTED: {channel.get('error') or channel['read'].get('error')}"
                elif channel["value_raw"] < 0:
                    estado = f"NOT_COLLECTED: valor negativo {channel['value_raw']}"
                else:
                    rpm = channel["value_raw"]
                    estado = "detenido" if rpm == 0 else "girando"
                ventiladores.append({"hwmon": device.name, "canal": path.name.removesuffix("_input"),
                                     "path": str(path), "rpm": rpm, "estado": estado})
    could_not_run = int(motivo is not None) + sum(int(v["rpm"] is None) for v in ventiladores)
    return {
        "schema": 1,
        "captured_at_utc": datetime.now(timezone.utc).isoformat(),
        "fuente": f"{hwmon_root}/hwmon*/fan*_input con name == acpi_fan",
        "identidad": identidad,
        "ventiladores": ventiladores,
        "motivo": motivo,
        "hwmon_name_ilegible": name_ilegible,
        "could_not_run": could_not_run,
        "status": "NOT_COLLECTED" if motivo else ("partial" if could_not_run else "observed"),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path("/"), help="host root; fixture use")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--acpi-fan", action="store_true",
                        help="only fan RPM from hwmon acpi_fan, with device identity")
    parser.add_argument("--forense-dir", default=FORENSE_DIR,
                        help="directory holding dmidecode-t45.txt/dmidecode-bios.txt; fixture use")
    args = parser.parse_args()
    record = acpi_fan(args.root, args.forense_dir) if args.acpi_fan else capture(args.root)
    payload = json.dumps(record, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload, encoding="utf-8")
    else:
        sys.stdout.write(payload)
    return 0 if record["could_not_run"] == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
