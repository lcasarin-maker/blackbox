"""Recompute nine forum hardware predicates from raw, read-only case captures.

The adapter contract is intentionally data-only: ``capture.json`` contains raw
command argv/exit/stdout/stderr and timestamped measurements. It rejects asserted
``status``, ``pass``, or boolean outcome fields. Case names partition A/B captures;
verdicts are recomputed from measured values and raw command outputs.
"""
from __future__ import annotations

import hashlib
import json
import math
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from tools.capture_io import read_regular_bytes, strict_json_loads
from urllib.parse import urlparse

IDS = {
    "FORUM-00-CX7-HOTPLUG-FAN-PROTECTION",
    "FORUM-02-GX10-READ-INTEGRITY",
    "FEATURE-FORUM-SBSA-WATCHDOG-STATE-01",
    "FORUM-REALTEK-DRIVER-BINDING-01",
    "FEATURE-FORUM-DESKTOP-SESSION-POSTUPDATE-01",
    "FORUM-00-REALTEK-EEE-DIRECT-LINK",
    "FEATURE-FORUM-RESCUE-RUNBOOK-01",
    "FORUM-00-GB10-THERMAL-RESIDENCY-ADMISSION",
    "FORUM-02-USB-UVC-EP0",
}


def _result(status: str, reason: str, files: list[str], *, checks: dict[str, str] | None = None) -> dict[str, Any]:
    return {"status": status, "reason": reason, "files": files,
            "fail": int(status == "fail"), "could_not_run": int(status == "unknown"),
            "checks": checks or {}}


def _read_capture(path: Path) -> tuple[Any | None, dict[str, Any] | None]:
    try:
        raw = read_regular_bytes(path, 4 * 1024 * 1024)
        if len(raw) > 4 * 1024 * 1024:
            return None, _result("fail", "raw capture exceeds the 4 MiB safety bound", [str(path)])
        document = strict_json_loads(raw.decode("utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError, RecursionError) as exc:
        return None, _result("unknown", f"raw case capture unavailable: {exc}", [str(path)])
    return document, None


def _load(finding_id: str, directory: Path) -> tuple[dict[str, Any] | None, Path, dict[str, Any] | None]:
    path = directory / "capture.json"
    document, error = _read_capture(path)
    if error:
        return None, path, error
    if not isinstance(document, dict) or document.get("schema") != 1 or document.get("id") != finding_id:
        return None, path, _result("fail", "raw capture schema or subject identity mismatch", [str(path)])
    rows = document.get("captures")
    if not isinstance(rows, list):
        return None, path, _result("fail", "captures must be a raw command list", [str(path)])
    times: list[datetime] = []
    for row in rows:
        if (not isinstance(row, dict) or not isinstance(row.get("name"), str)
                or not isinstance(row.get("argv"), list)
                or any(not isinstance(arg, str) for arg in row["argv"])
                or type(row.get("exit_code")) is not int
                or not isinstance(row.get("stdout"), str)
                or not isinstance(row.get("stderr"), str)
                or not isinstance(row.get("captured_at"), str)):
            return None, path, _result("fail", "raw command row malformed", [str(path)])
        try:
            timestamp = datetime.fromisoformat(row["captured_at"].replace("Z", "+00:00"))
        except ValueError:
            return None, path, _result("fail", "raw command timestamp is not ISO-8601", [str(path)])
        if timestamp.tzinfo is None:
            return None, path, _result("fail", "raw command timestamp lacks timezone", [str(path)])
        times.append(timestamp)
        if any(key in row for key in ("status", "pass", "passed", "healthy", "negative_detected")):
            return None, path, _result("fail", "raw command row contains an asserted outcome flag", [str(path)])
    if any(left >= right for left, right in zip(times, times[1:])):
        return None, path, _result("fail", "raw capture timestamps are not strictly increasing", [str(path)])
    return document, path, None


def _case(document: dict[str, Any], name: str, command_re: str) -> tuple[dict[str, Any] | None, str | None]:
    matches = [row for row in document["captures"] if row["name"] == name]
    if not matches:
        return None, f"raw case {name} missing"
    return _aggregate_case(name, matches, command_re)


def _aggregate_case(name: str, matches: list[dict[str, Any]],
                    command_re: str) -> tuple[dict[str, Any] | None, str | None]:
    measurements: list[dict[str, Any]] = []
    raw_outputs: list[str] = []
    for row in matches:
        data, error = _case_row(name, row, command_re)
        if error:
            return None, error
        assert data is not None
        measurements.append(data)
        raw_outputs.append(row["stdout"])
    merged, counters, traffic, ssh_successes, error = _merge_measurements(name, measurements)
    if error:
        return None, error
    assert merged is not None
    error = _derive_counter_deltas(name, merged, counters)
    if error:
        return None, error
    _derive_traffic(merged, traffic)
    if ssh_successes:
        merged["ssh_reconnects"] = ssh_successes
    if name == "rescue_entry" and _text(merged, "rescue_entry_id"):
        merged["entry_id"] = merged["rescue_entry_id"]
    if name == "rescue_boot" and _text(merged, "boot_current"):
        merged["entry_id"] = merged["boot_current"]
    if name == "restoration" and _text(merged, "boot_current"):
        merged["restored_entry"] = merged["boot_current"]
    merged["output"] = "\n".join(raw_outputs)
    if all(isinstance(row.get("captured_at"), str) for row in matches):
        timestamps = [datetime.fromisoformat(row["captured_at"].replace("Z", "+00:00")) for row in matches]
        merged["capture_span_s"] = (timestamps[-1] - timestamps[0]).total_seconds()
    return merged, None


def _merge_measurements(name: str, rows: list[dict[str, Any]]) -> tuple[
    dict[str, Any] | None, dict[str, list[int]], dict[str, dict[str, list[float]]], int, str | None
]:
    merged: dict[str, Any] = {}
    counters: dict[str, list[int]] = {}
    traffic: dict[str, dict[str, list[float]]] = {}
    ssh_successes = 0
    for data in rows:
        for key, value in data.items():
            if key == "output" or key == "network_family":
                continue
            if key == "thermal_capture" and isinstance(value, dict):
                merged.setdefault("thermal_captures", []).append(value)
                continue
            if _merge_thermal_metric(name, key, value, merged):
                continue
            if _is_counter(key, value):
                counters.setdefault(key, []).append(value)
                continue
            if _is_traffic_metric(key, value):
                family = str(data.get("network_family", "unknown"))
                traffic.setdefault(family, {}).setdefault(key, []).append(float(value))
                continue
            if key == "ssh_exit_code":
                ssh_successes += int(value == 0)
            if key in merged and merged[key] != value:
                return None, counters, traffic, 0, f"case {name} repeats conflicting raw field {key}"
            merged[key] = value
    return merged, counters, traffic, ssh_successes, None


def _merge_thermal_metric(name: str, key: str, value: Any, merged: dict[str, Any]) -> bool:
    keys = {"gpu_c", "cpu_c", "soc_c", "power_w", "resident_bytes", "throughput", "fan_rpm"}
    if (name not in {"resident_workload", "idle_control", "rollback"} or key not in keys
            or isinstance(value, bool) or not isinstance(value, (int, float))):
        return False
    if key not in merged:
        merged[key] = value
    elif key == "fan_rpm":
        merged[key] = min(merged[key], value)
    else:
        merged[key] = max(merged[key], value)
    return True


def _is_counter(key: str, value: Any) -> bool:
    return key in {"link_down_events", "link_resets"} and type(value) is int


def _is_traffic_metric(key: str, value: Any) -> bool:
    return (key in {"packet_loss", "packets_sent", "packets_received"}
            and isinstance(value, (int, float)) and not isinstance(value, bool))


def _derive_counter_deltas(name: str, merged: dict[str, Any], counters: dict[str, list[int]]) -> str | None:
    for key, samples in counters.items():
        if len(samples) > 1:
            delta = samples[-1] - samples[0]
            if delta < 0:
                return f"case {name} raw counter moved backwards"
            merged[key] = delta
            merged["cycles"] = max(merged.get("cycles", 0), delta, len(samples) - 1)
    if "link_down_events" in merged:
        merged["link_resets"] = merged["link_down_events"]


def _derive_traffic(merged: dict[str, Any], traffic: dict[str, dict[str, list[float]]]) -> None:
    for family, metrics in traffic.items():
        if family in {"ipv4", "ipv6"}:
            losses = metrics.get("packet_loss", [])
            received = metrics.get("packets_received", [])
            merged[family] = "up" if losses and all(loss == 0 for loss in losses) and received and all(count > 0 for count in received) else "down"
            merged[family + "_packet_loss"] = max(losses, default=100.0)
            if losses:
                merged["packet_loss"] = max(merged.get("packet_loss", 0.0), max(losses))


def _case_row(name: str, row: dict[str, Any], command_re: str) -> tuple[dict[str, Any] | None, str | None]:
    command = " ".join(row["argv"])
    if not re.search(command_re, command, re.I):
        return None, f"case {name} was not captured by the required command"
    if row["exit_code"] != 0 and not set(row["argv"]) & {"ssh", "ping", "fuser"}:
        return None, f"case {name} command failed: {row['stderr'][:180]}"
    trusted_json_tools = {"tools.read_integrity", "tools.host_diagnostics",
                          "tools.nvme_readonly", "tools.thermal_coverage"}
    if set(row["argv"]) & trusted_json_tools or "tools.recovery_profile" in row["argv"]:
        try:
            data = strict_json_loads(row["stdout"])
        except (json.JSONDecodeError, ValueError, RecursionError):
            return None, f"case {name} collector JSON is malformed"
        if not isinstance(data, dict):
            return None, f"case {name} collector output is not an object"
        if "tools.thermal_coverage" in row["argv"]:
            return {"thermal_capture": data}, None
        return data, None
    facts = _native_facts(row["argv"], row["stdout"] + row["stderr"])
    if _is_shelly_status(row["argv"]):
        meter = _parse_shelly_status(row["stdout"])
        if meter is None:
            return None, f"case {name} external power meter status malformed"
        facts.update(meter)
    if "ssh" in row["argv"]:
        facts["ssh_exit_code"] = row["exit_code"]
    return facts, None


def _is_shelly_status(argv: list[str]) -> bool:
    return any("/rpc/Shelly.GetStatus" in token for token in argv)


def _parse_shelly_status(output: str) -> dict[str, Any] | None:
    try:
        data = strict_json_loads(output)
    except (json.JSONDecodeError, ValueError, RecursionError):
        return None
    if not isinstance(data, dict):
        return None
    device = data.get("sys", {}).get("device", {}).get("id") if isinstance(data.get("sys"), dict) else None
    power: Any = None
    for name in ("switch:0", "em:0"):
        channel = data.get(name)
        if isinstance(channel, dict):
            power = channel.get("apower", channel.get("total_act_power"))
            if power is not None:
                break
    if not isinstance(device, str) or not device.strip() or isinstance(power, bool) or not isinstance(power, (int, float)):
        return None
    numeric = float(power)
    if not math.isfinite(numeric) or numeric < 0:
        return None
    return {"meter_id": device, "power_w": numeric}


def _native_facts(argv: list[str], output: str) -> dict[str, Any]:
    """Extract a small set of measured fields from well-known native formats."""
    facts = {"output": output}
    for parser in (_parse_ethtool_eee, _parse_ethtool_stats, _parse_ethtool_driver,
                   _parse_link_state, _parse_ping, _parse_nvidia_smi, _parse_dmi,
                   _parse_uname, _parse_modinfo, _parse_lspci, _parse_boot_id,
                   _parse_ssh_probe, _parse_dpkg_version, _parse_sensors, _parse_sysfs,
                   _parse_fuser, _parse_kernel_config, _parse_module_list,
                   _parse_journal_json, _parse_loginctl, _parse_xrandr,
                   _parse_desktop_journal, _parse_lldp, _parse_efibootmgr,
                   _parse_cmdline, _parse_route, _parse_usb_trace, _parse_lsusb,
                   _parse_compute_apps, _parse_fwupdmgr,
                   _parse_benchmark):
        facts.update(parser(argv, output))
    return facts


def _parse_ethtool_eee(argv: list[str], output: str) -> dict[str, Any]:
    if "--show-eee" not in argv:
        return {}
    state = _parse_eee_state(output)
    partner = re.search(r"(?im)^Link partner advertised EEE link modes:\s*(.+)$", output)
    facts: dict[str, Any] = {"eee_state": state, "eee": state} if state else {}
    if partner and partner.group(1).strip() != "Not reported":
        facts["partner_eee_modes"] = partner.group(1).strip()
    return facts


def _parse_ethtool_stats(argv: list[str], output: str) -> dict[str, Any]:
    if "ethtool" not in argv or "-S" not in argv:
        return {}
    facts: dict[str, Any] = {}
    for line in output.splitlines():
        match = re.match(r"\s*([\w_]+):\s*(\d+)\s*$", line)
        if match and re.search(r"(link|reset|retrain|down|recovery)", match.group(1), re.I):
            facts[match.group(1).lower()] = int(match.group(2))
    return facts


def _parse_ethtool_driver(argv: list[str], output: str) -> dict[str, Any]:
    if "ethtool" not in argv or "-i" not in argv:
        return {}
    facts: dict[str, Any] = {}
    for line in output.splitlines():
        key, separator, value = line.partition(":")
        if separator and key.strip() in {"driver", "version", "firmware-version", "bus-info"}:
            normalized = {"version": "module_version", "firmware-version": "firmware_version"}.get(
                key.strip(), key.strip().replace("-", "_")
            )
            facts[normalized] = value.strip()
    return facts


def _parse_link_state(argv: list[str], output: str) -> dict[str, Any]:
    if "ethtool" not in argv:
        return {}
    link = re.search(r"(?im)^\s*Link detected:\s*(yes|no)\s*$", output)
    if not link:
        return {}
    state = "up" if link.group(1).lower() == "yes" else "down"
    return {"link": state, "network_state": state}


def _parse_ping(argv: list[str], output: str) -> dict[str, Any]:
    if "ping" not in argv:
        return {}
    match = re.search(r"(\d+) packets transmitted, (\d+) (?:packets )?received, (\d+(?:\.\d+)?)% packet loss", output)
    if not match:
        return {}
    sent, received, loss = match.groups()
    family = "ipv6" if "-6" in argv else "ipv4" if "-4" in argv else "ipv6" if ":" in argv[-1] else "ipv4"
    return {"packets_sent": int(sent), "packets_received": int(received),
            "packet_loss": float(loss), "network_family": family}


def _parse_nvidia_smi(argv: list[str], output: str) -> dict[str, Any]:
    command = " ".join(argv)
    if "nvidia-smi" not in argv or "--query-gpu=" not in command:
        return {}
    values = [part.strip() for part in output.strip().split(",")]
    columns = command.partition("--query-gpu=")[2].partition(" ")[0].split(",")
    facts: dict[str, Any] = {}
    for column, value in zip(columns, values, strict=False):
        number = re.fullmatch(r"-?\d+(?:\.\d+)?", value)
        key = {"temperature.gpu": "temperature_c", "power.draw": "power_w"}.get(
            column, column.rsplit(".", 1)[-1]
        )
        facts[key] = float(value) if number else value
    return facts


def _parse_compute_app(line: str) -> dict[str, Any] | None:
    match = re.fullmatch(r"\s*(\d+)\s*,\s*([^,]+)\s*,\s*(\d+(?:\.\d+)?)\s*MiB\s*", line)
    if not match:
        return None
    pid, name, mib = match.groups()
    memory = float(mib)
    if not math.isfinite(memory) or memory < 0:
        return None
    return {"pid": int(pid), "name": name.strip(), "bytes": int(memory * 1024 * 1024)}


def _parse_compute_apps(argv: list[str], output: str) -> dict[str, Any]:
    if "nvidia-smi" not in argv or "--query-compute-apps=" not in " ".join(argv):
        return {}
    if "No running processes found" in output:
        return {"resident_bytes": 0, "resident_processes": 0}
    lines = [line for line in output.splitlines() if line.strip()]
    apps = [_parse_compute_app(line) for line in lines]
    if not apps or any(app is None for app in apps):
        return {}
    return {"resident_bytes": sum(int(app["bytes"]) for app in apps if app),
            "resident_processes": len(apps)}


def _parse_benchmark(argv: list[str], output: str) -> dict[str, Any]:
    if not any(Path(token).name in {"vllm", "llama-benchy", "llama-bench"} for token in argv):
        return {}
    patterns = (r"(?im)^\s*(?:Output )?token throughput:\s*(\d+(?:\.\d+)?)\s*(?:tokens/s)?\s*$",
                r"(?im)^\s*Throughput:\s*(\d+(?:\.\d+)?)\s*tokens/s\s*$",
                r"(?im)^\s*generated tokens/s:\s*(\d+(?:\.\d+)?)\s*$")
    for pattern in patterns:
        match = re.search(pattern, output)
        if match:
            throughput = float(match.group(1))
            if math.isfinite(throughput) and throughput > 0:
                canonical = json.dumps(argv, separators=(",", ":"), ensure_ascii=True)
                return {"throughput": throughput, "workload_hash": hashlib.sha256(canonical.encode()).hexdigest()}
    return {}


def _parse_sensors(argv: list[str], output: str) -> dict[str, Any]:
    if not argv or Path(argv[0]).name != "sensors":
        return {}
    facts: dict[str, Any] = {}
    for line in output.splitlines():
        match = re.match(r"\s*([\w /-]+):\s*\+?(-?\d+(?:\.\d+)?)\s*°?C\b", line)
        if match:
            label = match.group(1).strip().lower()
            key = "soc_c" if "soc" in label else "cpu_c" if "cpu" in label else "gpu_c" if "gpu" in label else None
            if key:
                facts[key] = float(match.group(2))
    return facts


def _parse_sysfs(argv: list[str], output: str) -> dict[str, Any]:
    path = " ".join(argv)
    facts: dict[str, Any] = {}
    if re.search(r"/fan\d+_input$", path):
        value = output.strip()
        if value.isdecimal():
            facts["fan_rpm"] = int(value)
    if "/power/" in path and "power_now" in path:
        value = output.strip()
        if value.isdecimal():
            facts["power_w"] = int(value) / 1_000_000
    return facts


def _parse_fuser(argv: list[str], output: str) -> dict[str, Any]:
    if "fuser" not in argv:
        return {}
    pids = re.findall(r"(?m)^\S*watchdog\S*:\s*(?:\S+\s+)?(\d+)\s+[A-Z.]+\s+\S+", output)
    return {"owner_pids": sorted({int(pid) for pid in pids})}


def _parse_kernel_config(argv: list[str], output: str) -> dict[str, Any]:
    if "SBSA_WATCHDOG" not in " ".join(argv):
        return {}
    match = re.search(r"(?m)^CONFIG_ARM_SBSA_WATCHDOG=([ym])$", output.strip())
    return {"driver_config": match.group(1)} if match else {}


def _parse_module_list(argv: list[str], output: str) -> dict[str, Any]:
    if "/proc/modules" not in " ".join(argv):
        return {}
    return {"module_loaded": any(line.split()[:1] == ["sbsa_gwdt"] for line in output.splitlines())}


def _parse_journal_json(argv: list[str], output: str) -> dict[str, Any]:
    if "journalctl" not in argv or not any(value in argv for value in ("json", "json-seq")):
        return {}
    boot_ids: set[str] = set()
    for line in output.splitlines():
        try:
            item = strict_json_loads(line)
        except (json.JSONDecodeError, RecursionError):
            continue
        if isinstance(item, dict) and isinstance(item.get("_BOOT_ID"), str):
            boot_ids.add(item["_BOOT_ID"])
    if len(boot_ids) == 1:
        return {"boot_id": next(iter(boot_ids))}
    return {}


def _parse_loginctl(argv: list[str], output: str) -> dict[str, Any]:
    if "loginctl" not in argv:
        return {}
    properties = dict(re.findall(r"(?m)^([A-Za-z]+)=(.*)$", output))
    if not properties:
        return {}
    state = properties.get("State")
    session_type = properties.get("Type")
    display = properties.get("Display")
    session_class = properties.get("Class")
    session_name = properties.get("Name")
    facts: dict[str, Any] = {"session_state": state} if state else {}
    if session_type:
        facts["session_type"] = session_type
    facts["session_display"] = display or ""
    if session_class == "greeter" or session_name in {"gdm", "sddm", "lightdm"}:
        facts["session_classification"] = "greeter"
    elif session_type == "tty" or not display:
        facts["session_classification"] = "headless"
    elif state in {"active", "online"}:
        facts["session_classification"] = "active_session"
    elif state == "closing":
        facts["session_classification"] = "session_ending"
    return facts


def _parse_xrandr(argv: list[str], output: str) -> dict[str, Any]:
    if "xrandr" not in argv:
        return {}
    connected = re.findall(r"(?m)^\S+ connected(?: primary)?(?: \([^)]*\))?", output)
    return {"display_connected": bool(connected), "display_outputs": connected}


def _parse_desktop_journal(argv: list[str], output: str) -> dict[str, Any]:
    if "journalctl" not in argv:
        return {}
    signatures = (
        r"Failed to start GNOME Display Manager", r"gnome-session.*(failed|exited|crash)",
        r"gnome-shell.*(segfault|core dumped|Oh no)", r"mutter.*(failed|crash|no GPU)",
    )
    matches = [pattern for pattern in signatures if re.search(pattern, output, re.I)]
    return {"session_failure_signatures": matches, "incident_log_lines": len(output.splitlines())}


def _parse_lldp(argv: list[str], output: str) -> dict[str, Any]:
    if not any(Path(token).name in {"lldpctl", "lldpcli"} for token in argv):
        return {}
    system_name = re.search(r"(?im)^\s*(?:SysName|System Name):\s*(.+)$", output)
    description = re.search(r"(?im)^\s*(?:SysDescr|System Description):\s*(.+)$", output)
    identity = " ".join(match.group(1) for match in (system_name, description) if match)
    if not identity:
        return {}
    lowered = identity.lower()
    if "i225-v" in lowered or "i225v" in lowered:
        return {"partner": "Intel I225-V", "topology": "direct"}
    if any(term in lowered for term in ("switch", "netgear", "cisco", "aruba", "mikrotik")):
        return {"neighbor": identity, "topology": "switch"}
    return {"neighbor": identity}


def _parse_efibootmgr(argv: list[str], output: str) -> dict[str, Any]:
    if "efibootmgr" not in argv:
        return {}
    current = re.search(r"(?m)^BootCurrent:\s*([0-9A-Fa-f]{4})$", output)
    entry = re.search(r"(?m)^Boot([0-9A-Fa-f]{4})\*?\s+.*(?:rescue|recovery)", output, re.I)
    facts = {"boot_current": current.group(1).upper()} if current else {}
    if entry:
        facts["rescue_entry_id"] = entry.group(1).upper()
    return facts


def _parse_cmdline(argv: list[str], output: str) -> dict[str, Any]:
    if "/proc/cmdline" not in " ".join(argv):
        return {}
    tokens = output.split()
    rescue = "systemd.unit=rescue.target" in tokens or "systemd.unit=emergency.target" in tokens
    return {"rescue_target": rescue}


def _parse_route(argv: list[str], output: str) -> dict[str, Any]:
    if not argv or Path(argv[0]).name != "ip" or "route" not in argv:
        return {}
    dev = re.search(r"(?:^|\s)dev\s+(\S+)", output)
    via = re.search(r"(?:^|\s)via\s+(\S+)", output)
    if not dev:
        return {"network_route": None}
    return {"network_route": f"dev {dev.group(1)}" + (f" via {via.group(1)}" if via else "")}


def _parse_usb_trace(argv: list[str], output: str) -> dict[str, Any]:
    if not re.search(r"usbmon|trace-cmd|trace_pipe|tracefs", " ".join(argv), re.I):
        return {}
    lines = output.splitlines()
    stream_start = [i for i, line in enumerate(lines)
                    if re.search(r"uvc_video_start_streaming|STREAMON", line, re.I)]
    stream_stop = [i for i, line in enumerate(lines)
                   if re.search(r"uvc_video_stop_streaming|STREAMOFF", line, re.I)]
    resets = sum(bool(re.search(r"HC died|host controller not responding|xhci_hc_died", line, re.I))
                 for line in lines)
    if not stream_start or not stream_stop:
        return {"xhci_resets": resets} if resets else {}
    start_index = stream_start[0]
    stop_index = next((index for index in stream_stop if index > start_index), None)
    if stop_index is None:
        return {"xhci_resets": resets}
    ep0_count = sum(bool(re.search(r"\bS C[io]:\d+:\d+:\d+", line))
                    for line in lines[start_index + 1:stop_index])
    start_time = _trace_timestamp(lines[start_index])
    stop_time = _trace_timestamp(lines[stop_index])
    facts: dict[str, Any] = {"xhci_resets": resets, "ep0_after_stream_count": ep0_count}
    if start_time is not None and stop_time is not None and stop_time > start_time:
        facts["stream_seconds"] = stop_time - start_time
    return facts


def _trace_timestamp(line: str) -> float | None:
    match = re.search(r"(?:\s|\[)(\d+\.\d{6,})(?=[:\]])", line)
    if match is None:
        return None
    value = float(match.group(1))
    return value if math.isfinite(value) else None


def _parse_dmi(argv: list[str], output: str) -> dict[str, Any]:
    if "dmidecode" not in argv:
        return {}
    accepted = {"Manufacturer", "Product Name", "Board Name", "BIOS Version", "BIOS Revision"}
    facts: dict[str, Any] = {}
    for line in output.splitlines():
        key, separator, value = line.partition(":")
        if separator and key.strip() in accepted:
            facts[key.strip().lower().replace(" ", "_")] = value.strip()
    return facts


def _parse_uname(argv: list[str], output: str) -> dict[str, Any]:
    if "uname" not in argv or "-r" not in argv:
        return {}
    release = output.strip()
    return {"kernel_release": release, "kernel": release} if release and "\n" not in release else {}


def _parse_modinfo(argv: list[str], output: str) -> dict[str, Any]:
    if "modinfo" not in argv:
        return {}
    facts: dict[str, Any] = {}
    if "-F" in argv:
        try:
            field = argv[argv.index("-F") + 1]
        except IndexError:
            return {}
        values = output.strip().splitlines()
        if len(values) == 1 and values[0]:
            key = {"version": "module_version", "signer": "module_signer",
                   "firmware": "module_firmware", "vermagic": "module_vermagic"}.get(field)
            return {key: values[0]} if key else {}
    for line in output.splitlines():
        key, separator, value = line.partition(":")
        if separator and key.strip() in {"version", "firmware", "signer", "vermagic"} and value.strip():
            facts[f"module_{key.strip()}"] = value.strip()
    return facts


def _parse_lsusb(argv: list[str], output: str) -> dict[str, Any]:
    if not argv or Path(argv[0]).name != "lsusb":
        return {}
    identifiers = re.findall(r"(?im)^Bus\s+\d+\s+Device\s+\d+:\s+ID\s+([0-9a-f]{4}:[0-9a-f]{4})\s*(.*)$", output)
    if len(identifiers) != 1:
        return {}
    product = identifiers[0][1].strip()
    return {"usb_device_id": identifiers[0][0].lower(), "camera": product} if product else {}


def _parse_fwupdmgr(argv: list[str], output: str) -> dict[str, Any]:
    if "fwupdmgr" not in argv:
        return {}
    versions: dict[str, str] = {}
    name: str | None = None
    for line in output.splitlines():
        match_name = re.match(r"\s*(?:Name|Device name):\s*(.+)$", line, re.I)
        match_version = re.match(r"\s*(?:Current )?Version:\s*(.+)$", line, re.I)
        if match_name:
            name = match_name.group(1).strip().lower()
        elif match_version and name:
            normalized = next((key for token, key in (("connectx", "connectx"), ("connectx-7", "connectx"),
                                ("embedded controller", "ec"), ("\bec\b", "ec"),
                                ("system-on-chip", "soc"), ("soc", "soc"),
                                ("usb-c pd", "pd"), ("power delivery", "pd"),
                                ("uefi", "uefi"), ("system firmware", "uefi"))
                              if re.search(token, name)), None)
            if normalized:
                versions[normalized] = match_version.group(1).strip()
            name = None
    return {"firmware_versions": versions} if versions else {}


def _parse_lspci(argv: list[str], output: str) -> dict[str, Any]:
    if "lspci" not in argv:
        return {}
    facts: dict[str, Any] = {}
    device = re.search(r"\[([\da-fA-F]{4}:[\da-fA-F]{4})\]", output)
    binding = re.search(r"(?im)^\s*Kernel driver in use:\s*(\S+)\s*$", output)
    if device:
        facts["pci_id"] = device.group(1).lower()
        facts["pci_state"] = "present"
        if device.group(1).lower() == "8086:15f3":
            facts["partner"] = "Intel I225-V"
    if binding:
        facts["driver"] = binding.group(1)
    return facts


def _parse_boot_id(argv: list[str], output: str) -> dict[str, Any]:
    if "boot_id" not in " ".join(argv):
        return {}
    boot_id = output.strip()
    return {"boot_id": boot_id} if re.fullmatch(r"[0-9a-fA-F-]{36}", boot_id) else {}


def _parse_ssh_probe(argv: list[str], output: str) -> dict[str, Any]:
    if "ssh" not in argv:
        return {}
    return {"ssh_exit_code": 0} if not output.strip() else {"ssh_output": output.strip()}


def _parse_dpkg_version(argv: list[str], output: str) -> dict[str, Any]:
    if "dpkg-query" not in argv or "-W" not in argv:
        return {}
    version = output.strip().splitlines()
    return {"package_version": version[0].split()[-1]} if version and version[0].split() else {}


def _number(data: dict[str, Any], key: str, minimum: float = 0) -> float | None:
    value = data.get(key)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    numeric = float(value)
    if not math.isfinite(numeric) or numeric < minimum:
        return None
    return numeric


def _text(data: dict[str, Any], key: str) -> str | None:
    value = data.get(key)
    return value.strip() if isinstance(value, str) and value.strip() else None


def _identity_matches_source(document: dict[str, Any], refs: list[dict[str, Any]]) -> tuple[bool, str | None]:
    identity_names = {"identity", "stack_identity", "oem_identity", "watchdog", "before", "incident",
                      "direct_eee_on", "safety_limits", "affected_stack", "corrected_stack"}
    identity_rows = [row for row in document["captures"] if row["name"] in identity_names]
    identity: dict[str, Any] = {}
    for row in identity_rows:
        identity.update(_native_facts(row["argv"], row["stdout"]))
    required = ("manufacturer", "product_name", "bios_version", "kernel_release")
    missing = [key for key in required if not _text(identity, key)]
    if missing:
        return False, "raw OEM/software identity tuple incomplete: " + ", ".join(missing)
    version_values = [_text(identity, key) for key in required]
    module_version = _text(identity, "module_version")
    if module_version:
        version_values.append(module_version)
    if not identity_rows:
        return False, "raw OEM/firmware/software identity command missing"
    source_text = " ".join(row["text"] for row in refs)
    if any(value is None or value not in source_text for value in version_values):
        return False, "vendor source does not cite the captured OEM/version tuple"
    return True, None


def _references(document: dict[str, Any]) -> tuple[bool, str | None]:
    refs = document.get("vendor_sources")
    if not isinstance(refs, list) or not refs:
        return False, "version-scoped OEM/vendor source text and digest missing"
    for row in refs:
        if not isinstance(row, dict) or not isinstance(row.get("text"), str):
            return False, "vendor source row malformed"
        if hashlib.sha256(row["text"].encode()).hexdigest() != row.get("sha256"):
            return False, "vendor source digest mismatch"
        url = row.get("url")
        host = urlparse(url).hostname if isinstance(url, str) else None
        if host not in {"nvidia.com", "docs.nvidia.com", "www.nvidia.com", "asus.com", "www.asus.com",
                        "dell.com", "www.dell.com", "intel.com", "www.intel.com", "ubuntu.com", "canonical.com"}:
            return False, "source URL is not on an allowed OEM/vendor domain"
        if len(row["text"].strip()) < 80:
            return False, "vendor source text lacks substantive compatibility detail"
    matched, error = _identity_matches_source(document, refs)
    if not matched:
        return False, error
    # URL and digest establish integrity of the supplied excerpt only; they do not
    # authenticate who supplied it. Keep this limitation explicit in verdicts.
    return True, None


def _replay_read_case(document: dict[str, Any], directory: Path, name: str) -> tuple[dict[str, Any] | None, Path | None, str | None]:
    row = next((entry for entry in document["captures"] if entry["name"] == name), None)
    if row is None:
        return None, None, f"raw case {name} missing"
    if "tools.read_integrity" not in row["argv"]:
        return None, None, f"case {name} is not a read_integrity invocation"
    try:
        actual = strict_json_loads(row["stdout"])
        args = row["argv"]
        module_index = args.index("tools.read_integrity")
        target_input = Path(args[module_index + 1])
        offset = int(args[args.index("--offset") + 1])
        length = int(args[args.index("--length") + 1])
        digest = args[args.index("--sha256") + 1]
        repeats = int(args[args.index("--repeats") + 1]) if "--repeats" in args else 2
    except (ValueError, IndexError, OSError, json.JSONDecodeError) as exc:
        return None, None, f"read_integrity capture lacks literal bounded argv/output: {exc}"
    actual_status = actual.get("status") if isinstance(actual, dict) else None
    expected_exit = {"pass": 0, "fail": 1, "could_not_run": 2}.get(actual_status) if isinstance(actual_status, str) else None
    if expected_exit is None or row["exit_code"] != expected_exit:
        return None, None, f"read_integrity command exit status disagrees with its measured outcome for {name}"
    try:
        target = target_input.resolve(strict=True)
    except FileNotFoundError:
        return None, None, f"read_integrity target unavailable for {name}"
    try:
        target.relative_to(directory.resolve(strict=True))
    except (ValueError, OSError):
        return None, None, "read_integrity target escapes the evidence directory"
    elapsed = row.get("elapsed_ms")
    if isinstance(elapsed, bool) or not isinstance(elapsed, (int, float)) or elapsed <= 0:
        return None, None, f"measured elapsed time absent for {name}"
    from tools.read_integrity import inspect as inspect_region

    derived = inspect_region(str(target), offset, length, digest, repeats)
    if derived.get("status") == "could_not_run":
        return None, None, f"read_integrity replay unavailable for {name}: {derived.get('reason')}"
    if derived != actual:
        return None, None, f"captured read_integrity output differs from fresh read-only replay for {name}"
    return {**derived, "elapsed_ms": float(elapsed)}, target, None


def _read_integrity(document: dict[str, Any], directory: Path) -> tuple[str, str]:
    cases: dict[str, dict[str, Any]] = {}
    targets: set[Path] = set()
    for name in ("healthy", "altered"):
        data, target, error = _replay_read_case(document, directory, name)
        if error:
            return "fail" if "mismatch" in error or "escapes" in error or "differs" in error else "unknown", error
        assert data is not None and target is not None
        if name == "healthy" and data.get("status") != "pass":
            return "fail", "healthy external-reference control disagrees across buffered/O_DIRECT reads"
        if name == "altered" and data.get("status") != "fail":
            return "fail", "altered-byte negative control was not detected by the reference digest"
        cases[name] = data
        targets.add(target)
    if len(targets) != 2:
        return "fail", "healthy and altered-byte controls did not use two distinct staging files"
    if not all(data.get("elapsed_ms", 0) > 0 for data in cases.values()):
        return "unknown", "bounded inspection cost was not measured in both raw runs"
    return "pass", "healthy and altered-byte controls recomputed from repeated buffered/O_DIRECT digests"


def _check_nvme_snapshot(directory: Path) -> tuple[str, str]:
    snapshot_path = directory / "nvme-snapshot.json"
    try:
        raw = read_regular_bytes(snapshot_path, 4 * 1024 * 1024)
        if len(raw) > 4 * 1024 * 1024:
            return "unknown", "read-only NVMe/RAS snapshot exceeds the 4 MiB safety bound"
        snapshot = strict_json_loads(raw.decode("utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError, RecursionError) as exc:
        return "unknown", f"read-only NVMe/RAS snapshot unavailable: {exc}"
    from tools.nvme_readonly import classify

    storage = classify(snapshot)
    if storage["status"] == "fail":
        return "fail", "read-only NVMe/RAS classifier found a failure signal: " + "; ".join(storage["findings"])
    if storage["status"] != "pass" or storage["could_not_run"]:
        return "unknown", "read-only NVMe/RAS inventory incomplete: " + "; ".join(storage["unknowns"])
    return "pass", "read-only NVMe/RAS snapshot classifies without a recorded failure"


def _evaluate_gx10(document: dict[str, Any], directory: Path) -> tuple[str, str]:
    status, reason = _check_nvme_snapshot(directory)
    if status != "pass":
        return status, reason
    status, reason = _read_integrity(document, directory)
    if status != "pass":
        return status, reason
    return _check_gx10_correlations(document, reason)


def _check_gx10_correlations(document: dict[str, Any], reason: str) -> tuple[str, str]:
    sources_ok, source_error = _references(document)
    if not sources_ok:
        return "unknown", source_error or "vendor applicability source unavailable"
    for name, command in (("external_reference", r"sha256sum|manifest"),
                          ("nvme_health", r"nvme.*smart-log|smartctl.*-a"),
                          ("ras_signals", r"journalctl.*(ras|edac|bert)|ras-mc-ctl"),
                          ("stack_identity", r"dmidecode|uname|modinfo")):
        data, error = _case(document, name, command)
        if error:
            return "unknown", error
        assert data is not None
        if not _text(data, "output"):
            return "unknown", f"{name} raw output missing"
    ref, _ = _case(document, "external_reference", r"sha256sum|manifest")
    reference_row = next(row for row in document["captures"] if row["name"] == "external_reference")
    argv = reference_row["argv"]
    if "ssh" not in argv or len(argv) < 3 or argv[1] in {"localhost", "127.0.0.1", "::1"}:
        return "unknown", "reference digest was not queried from a separately named host over SSH"
    healthy_row = next(row for row in document["captures"] if row["name"] == "healthy")
    healthy = strict_json_loads(healthy_row["stdout"])
    healthy_digest = healthy.get("reference_sha256") if isinstance(healthy, dict) else None
    external_output = _text(ref or {}, "output")
    if not isinstance(healthy_digest, str) or not external_output or not external_output.startswith(healthy_digest):
        return "fail", "external-node digest does not match the healthy read reference"
    nvme, _ = _case(document, "nvme_health", r"nvme.*smart-log|smartctl.*-a")
    assert nvme is not None
    try:
        nvme_raw = strict_json_loads(_text(nvme, "output") or "")
    except json.JSONDecodeError:
        return "fail", "NVMe health output is malformed"
    if not isinstance(nvme_raw, dict) or nvme_raw.get("critical_warning") != 0 or nvme_raw.get("media_errors") != 0:
        return "fail", "NVMe health reports a critical warning or media error"
    return "pass", reason + "; external reference, NVMe/RAS and exact stack observations captured"


REQUIRED: dict[str, dict[str, str]] = {
    "FORUM-00-CX7-HOTPLUG-FAN-PROTECTION": {"identity": r"dmidecode|fwupdmgr|uname|modinfo", "symptom": r"journalctl.*(kernel|cx7)|dmesg", "baseline": r"thermal|sensors|nvidia-smi|Shelly.GetStatus|fan[0-9]+_input", "candidate": r"thermal|sensors|nvidia-smi|Shelly.GetStatus|lspci|ethtool|fan[0-9]+_input|journalctl", "rollback": r"lspci|ethtool|ip|fan[0-9]+_input"},
    "FEATURE-FORUM-SBSA-WATCHDOG-STATE-01": {"watchdog": r"tools\.recovery_profile|watchdog|wdctl", "ownership": r"fuser|lsof|systemctl", "boot_logs": r"journalctl|pstore", "recovery": r"recovery|watchdog"},
    "FORUM-REALTEK-DRIVER-BINDING-01": {"identity": r"dmidecode|uname|modinfo", "before": r"lspci|ethtool|modinfo|boot_id", "warm_after": r"lspci|ethtool|modinfo|boot_id|ssh", "cold_after": r"lspci|ethtool|modinfo|boot_id|ssh", "alternate_nic": r"lspci|ethtool", "driver_absent": r"lspci|modinfo", "rollback": r"grub|modprobe|lspci|ssh"},
    "FEATURE-FORUM-DESKTOP-SESSION-POSTUPDATE-01": {"identity": r"dmidecode|uname|dpkg", "incident": r"journalctl|loginctl|ssh|dpkg", "control": r"loginctl|ssh|xrandr", "recovery": r"systemctl|apt|loginctl|dpkg|xrandr", "rollback": r"apt|dpkg|systemctl|ssh"},
    "FORUM-00-REALTEK-EEE-DIRECT-LINK": {"identity": r"dmidecode|uname|ethtool|lldpctl|lspci", "direct_eee_on": r"ethtool.*(show-eee|-S)|journalctl|lldpctl|ping|ssh", "direct_eee_off": r"ethtool.*(show-eee|-S)|journalctl|lldpctl|ping|ssh", "switch_control": r"ethtool.*(show-eee|-S)|journalctl|lldpctl|ping|ssh", "rollback": r"ethtool.*show-eee|ip|ping"},
    "FEATURE-FORUM-RESCUE-RUNBOOK-01": {"oem_identity": r"dmidecode|fwupdmgr|uname", "rescue_entry": r"efibootmgr|grub|systemd-boot", "rescue_boot": r"journalctl|bootctl|efibootmgr|cmdline", "normal_boot": r"journalctl|bootctl", "restoration": r"bootctl|efibootmgr|grub|journalctl|ip"},
    "FORUM-00-GB10-THERMAL-RESIDENCY-ADMISSION": {"safety_limits": r"dmidecode|vendor|thermal|uname", "resident_workload": r"nvidia-smi|thermal|dcgmi|vllm|Shelly.GetStatus|fan[0-9]+_input", "idle_control": r"nvidia-smi|thermal|dcgmi|Shelly.GetStatus|fan[0-9]+_input", "rollback": r"nvidia-smi|systemctl|thermal|fan[0-9]+_input"},
    "FORUM-02-USB-UVC-EP0": {"stack_identity": r"uname|lsusb|modinfo|dmidecode", "affected_stack": r"uname|lsusb|modinfo|dmidecode", "stream_control": r"usbmon|trace|uvc", "no_ep0_control": r"usbmon|trace|uvc", "corrected_stack": r"usbmon|trace|uvc|lsusb", "rollback": r"uname|modinfo|apt"},
}


def _gather_cases(document: dict[str, Any], finding_id: str) -> tuple[dict[str, dict[str, Any]], str | None]:
    cases: dict[str, dict[str, Any]] = {}
    for name, command in REQUIRED[finding_id].items():
        data, error = _case(document, name, command)
        if error:
            return cases, error
        assert data is not None
        if not data:
            return cases, f"case {name} contains no raw measurements"
        cases[name] = data
    return cases, None


def _check_cx7_safety(document: dict[str, Any], cases: dict[str, dict[str, Any]]) -> tuple[str, str]:
    status, reason = _check_cx7_oem_tuple(document, cases["identity"])
    if status != "pass":
        return status, reason
    symptom = cases["symptom"]
    if not re.search(r"Cable removal|hotplug.*remov", _text(symptom, "output") or "", re.I):
        return "fail", "raw kernel log does not contain the observed CX7 hotplug symptom"
    status, reason = _check_cx7_thermal(document, cases["baseline"], cases["candidate"])
    if status != "pass":
        return status, reason
    baseline, candidate = cases["baseline"], cases["candidate"]
    baseline_power, candidate_power = _number(baseline, "power_w", 0), _number(candidate, "power_w", 0)
    meter = _text(baseline, "meter_id")
    if baseline_power is None or candidate_power is None or not meter or _text(candidate, "meter_id") != meter:
        return "unknown", "baseline/candidate wall-power measurements from the same identified external meter missing"
    if re.search(r"Cable removal|hotplug.*remov", _text(candidate, "output") or "", re.I):
        return "fail", "candidate prevention capture repeats the CX7 hotplug-removal symptom"
    if any(_number(case, "fan_rpm", 1) is None for case in (baseline, candidate, cases["rollback"])):
        return "unknown", "baseline/candidate/rollback fan tachometer samples missing; stable temperature cannot prove fan operation"
    return "pass", "raw CX7-removal symptom, full OEM firmware tuple, complete thermal inventory, per-channel OEM bounds, fan tachometer, and same-meter wall-power A/B observed"


def _check_cx7_oem_tuple(document: dict[str, Any], identity: dict[str, Any]) -> tuple[str, str]:
    sources_ok, source_error = _references(document)
    if not sources_ok:
        return "unknown", source_error or "version-scoped source unavailable"
    firmware = identity.get("firmware_versions")
    if not isinstance(firmware, dict) or any(not _text(firmware, key) for key in ("uefi", "ec", "soc", "pd", "connectx")):
        return "unknown", "captured OEM identity lacks the UEFI/EC/SoC/PD/ConnectX firmware tuple"
    source_text = " ".join(row["text"] for row in document["vendor_sources"])
    if any(value not in source_text for value in firmware.values() if isinstance(value, str)):
        return "unknown", "version-scoped OEM source does not cite the captured full firmware tuple"
    return "pass", "full captured firmware tuple is cited in the caller-supplied OEM source"


def _check_cx7_thermal(document: dict[str, Any], baseline: dict[str, Any],
                       candidate: dict[str, Any]) -> tuple[str, str]:
    baseline_observation = _thermal_coverage_observation(baseline)
    candidate_observation = _thermal_coverage_observation(candidate)
    if baseline_observation is None or candidate_observation is None:
        return "unknown", "raw thermal_coverage collector lacks complete thermal zone/hwmon inventory"
    source_text = " ".join(row["text"] for row in document["vendor_sources"])
    limits = _thermal_limits(source_text)
    if not limits:
        return "unknown", "version-scoped source lacks channel-specific OEM temperature limits"
    for channel in ("gpu_c", "cpu_c", "soc_c"):
        value = candidate_observation.get(channel)
        limit = limits.get(channel)
        if value is None or limit is None:
            return "unknown", f"candidate/source lacks matching {channel} observation and OEM limit"
        if value >= limit:
            return "fail", f"candidate {channel} reached or exceeded its sourced OEM limit"
    return "pass", "complete thermal channel observations remain below the matching OEM limits"


def _thermal_coverage_observation(case_data: dict[str, Any]) -> dict[str, Any] | None:
    captures = case_data.get("thermal_captures")
    if isinstance(captures, list):
        observations: dict[str, Any] = {}
        for capture in captures:
            if not isinstance(capture, dict):
                return None
            sample = _thermal_capture_observation(capture)
            if sample is None:
                return None
            for key, value in sample.items():
                observations[key] = max(value, observations.get(key, value))
        return observations if observations else None
    capture = _thermal_capture(case_data)
    if capture is None:
        return None
    return _thermal_capture_observation(capture)


def _thermal_capture_observation(capture: dict[str, Any]) -> dict[str, Any] | None:
    channels = {"gpu": "gpu_c", "cpu": "cpu_c", "soc": "soc_c"}
    zones = capture.get("thermal_zones")
    hwmon = capture.get("hwmon")
    if not isinstance(zones, list) or not isinstance(hwmon, list):
        return None
    observations = _thermal_zone_values(zones, channels)
    if observations is None:
        return None
    hwmon_values = _thermal_hwmon_values(hwmon, channels)
    if hwmon_values is None:
        return None
    for key, value in hwmon_values.items():
        observations[key] = max(value, observations.get(key, value))
    return observations


def _thermal_zone_values(zones: list[Any], channels: dict[str, str]) -> dict[str, float] | None:
    values: dict[str, float] = {}
    for zone in zones:
        if not isinstance(zone, dict):
            return None
        kind = zone.get("type", {}).get("value") if isinstance(zone.get("type"), dict) else None
        channel = channels.get(str(kind).lower())
        value = _thermal_value(zone.get("temperature"))
        if channel and value is not None:
            values[channel] = max(value, values.get(channel, value))
    return values


def _thermal_hwmon_values(devices: list[Any], channels: dict[str, str]) -> dict[str, float] | None:
    values: dict[str, float] = {}
    for device in devices:
        if not isinstance(device, dict) or not isinstance(device.get("temperature_inputs"), list):
            return None
        for item in device["temperature_inputs"]:
            if not isinstance(item, dict):
                return None
            label = item.get("label", {}).get("value", "") if isinstance(item.get("label"), dict) else ""
            channel = next((value for key, value in channels.items() if key in str(label).lower()), None)
            value = _thermal_value(item)
            if channel and value is not None:
                values[channel] = max(value, values.get(channel, value))
    return values


def _thermal_capture(case_data: dict[str, Any]) -> dict[str, Any] | None:
    output = case_data.get("output")
    if not isinstance(output, str):
        return None
    decoder = json.JSONDecoder(parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)))
    offset = 0
    while offset < len(output):
        while offset < len(output) and output[offset].isspace():
            offset += 1
        if offset == len(output):
            break
        try:
            capture, offset = decoder.raw_decode(output, offset)
        except (json.JSONDecodeError, ValueError, RecursionError):
            return None
        if (isinstance(capture, dict) and capture.get("schema") == 1
                and capture.get("status") == "observed" and capture.get("could_not_run") == 0
                and isinstance(capture.get("thermal_zones"), list)):
            return capture
    return None


def _thermal_value(channel: Any) -> float | None:
    if not isinstance(channel, dict) or channel.get("status") != "ok":
        return None
    raw = channel.get("value")
    if isinstance(raw, bool) or not isinstance(raw, (int, float)):
        return None
    value = float(raw) / 1000 if abs(raw) > 200 else float(raw)
    return value if math.isfinite(value) else None


def _thermal_limits(source_text: str) -> dict[str, float]:
    limits: dict[str, float] = {}
    for channel, aliases in (("gpu_c", r"GPU|graphics|accelerator"),
                             ("cpu_c", r"CPU|processor"), ("soc_c", r"SoC|system.on.chip")):
        match = re.search(rf"(?:{aliases})[^.\n]{{0,100}}?(?:maximum|max|limit|shutdown)[^\n]{{0,50}}?(\d+(?:\.\d+)?)\s*(?:°?C)", source_text, re.I)
        if match:
            value = float(match.group(1))
            if math.isfinite(value):
                limits[channel] = value
    return limits


def _check_cx7(document: dict[str, Any], cases: dict[str, dict[str, Any]]) -> tuple[str, str]:
    status, reason = _check_cx7_safety(document, cases)
    if status != "pass":
        return status, reason
    candidate, rollback = cases["candidate"], cases["rollback"]
    if not _text(rollback, "pci_state") or not _text(rollback, "network_state"):
        return "unknown", "PCIe and network recovery after rollback were not observed"
    if rollback["pci_state"] != "present" or rollback["network_state"] != "up":
        return "fail", "CX7 PCIe/network state did not recover after rollback"
    if _text(candidate, "pci_state") != "present" or not _text(candidate, "network_state"):
        return "unknown", "candidate PCIe and network outcomes were not captured"
    if _text(candidate, "network_state") != "up":
        return "fail", "candidate CX7 network link is not up"
    return "pass", reason + "; rollback restored PCIe and network"


def _check_watchdog(cases: dict[str, dict[str, Any]]) -> tuple[str, str]:
    pids = cases["ownership"].get("owner_pids")
    if not isinstance(pids, list) or len(pids) != 1 or type(pids[0]) is not int or pids[0] <= 0:
        return "unknown", "watchdog ownership is ambiguous; failed fuser alone cannot prove absence of owner"
    boot_id, watchdog, error = _watchdog_profile(cases["watchdog"])
    if error:
        return "unknown", error
    assert boot_id is not None and watchdog is not None
    config = cases["watchdog"].get("driver_config")
    if config not in {"y", "m"}:
        return "unknown", "kernel config does not distinguish built-in/module watchdog driver state"
    profile_state = cases["watchdog"].get("state")
    modules_observation = profile_state.get("proc/modules") if isinstance(profile_state, dict) else None
    module_value = modules_observation.get("value") if isinstance(modules_observation, dict) and modules_observation.get("status") == "read" else ""
    module_text = module_value if isinstance(module_value, str) else ""
    module_loaded = any(line.split()[:1] == ["sbsa_gwdt"] for line in module_text.splitlines())
    if config != "y" and not module_loaded:
        return "fail", "watchdog driver is configured as a module but is not loaded"
    if _text(cases["boot_logs"], "boot_id") != boot_id:
        return "fail", "watchdog state and boot log belong to different boot identities"
    return _check_watchdog_recovery(boot_id, cases["recovery"])


def _check_watchdog_recovery(boot_id: str, profile: dict[str, Any]) -> tuple[str, str]:
    recovery_boot, recovery_watchdog, error = _watchdog_profile(profile)
    if error:
        return "unknown", "watchdog recovery " + error
    assert recovery_boot is not None and recovery_watchdog is not None
    if recovery_boot == boot_id:
        return "fail", "recovery control did not produce a distinct boot identity"
    bootstatus = recovery_watchdog.get("bootstatus")
    raw_bootstatus = bootstatus.get("value") if isinstance(bootstatus, dict) and bootstatus.get("status") == "read" else None
    if raw_bootstatus is None:
        return "unknown", "recovery boot lacks read-only watchdog-reset bootstatus"
    try:
        watchdog_reset = int(str(raw_bootstatus), 0) & 0x20 != 0
    except ValueError:
        return "unknown", "watchdog-reset bootstatus is not a numeric flag set"
    if not watchdog_reset:
        return "fail", "new boot does not report the watchdog reset flag"
    return "pass", "watchdog owner, distinct boot and hardware watchdog-reset flag correlate"


def _watchdog_profile(profile: dict[str, Any]) -> tuple[str | None, dict[str, Any] | None, str | None]:
    state = profile.get("state")
    devices = profile.get("watchdog")
    if not isinstance(state, dict) or not isinstance(devices, dict) or len(devices) != 1:
        return None, None, "read-only recovery_profile lacks a unique watchdog device inventory"
    boot_row = state.get("proc/sys/kernel/random/boot_id")
    boot_id = boot_row.get("value") if isinstance(boot_row, dict) and boot_row.get("status") == "read" else None
    if not isinstance(boot_id, str) or not boot_id:
        return None, None, "observation lacks boot identity"
    watchdog = next(iter(devices.values()))
    if not isinstance(watchdog, dict):
        return None, None, "device record malformed"
    identity, timeout = watchdog.get("identity"), watchdog.get("timeout")
    if not isinstance(identity, dict) or identity.get("status") != "read" or not str(identity.get("value", "")).strip():
        return None, None, "read-only watchdog identity is unavailable"
    if not isinstance(timeout, dict) or timeout.get("status") != "read" or not str(timeout.get("value", "")).isdigit():
        return None, None, "read-only watchdog timeout is unavailable"
    return boot_id, watchdog, None


def _check_realtek_binding(cases: dict[str, dict[str, Any]]) -> tuple[str, str]:
    before = cases["before"]
    warm, cold = cases["warm_after"], cases["cold_after"]
    baseline_boot = _text(before, "boot_id")
    warm_boot, cold_boot = _text(warm, "boot_id"), _text(cold, "boot_id")
    if not baseline_boot or not warm_boot or not cold_boot:
        return "unknown", "baseline, warm reboot, and cold reboot boot IDs are required"
    if len({baseline_boot, warm_boot, cold_boot}) != 3:
        return "fail", "warm/cold A/B observations do not belong to three distinct boots"
    for stage in (warm, cold):
        if not _text(stage, "module_version") or not _text(stage, "module_signer"):
            return "unknown", "effective module version or signer unavailable after reboot"
        if stage.get("driver") != "r8127":
            return "fail", "post-reboot PCI binding is not the supported r8127 driver"
        if stage.get("link") != "up":
            return "fail", "Ethernet link did not recover after driver binding"
    absent = cases["driver_absent"]
    if absent.get("driver") is not None or not _text(absent, "pci_id"):
        return "fail", "driver-absent negative control still shows a bound driver or lacks target PCI identity"
    return "pass", "warm/cold PCI binding and the driver-absent negative control passed"


def _check_realtek(cases: dict[str, dict[str, Any]]) -> tuple[str, str]:
    status, reason = _check_realtek_binding(cases)
    if status != "pass":
        return status, reason
    before, warm, cold = cases["before"], cases["warm_after"], cases["cold_after"]
    for stage_name, stage in (("warm", warm), ("cold", cold)):
        ssh_rc = _number(stage, "ssh_exit_code")
        if ssh_rc is None:
            return "unknown", f"management SSH probe unavailable after {stage_name} reboot"
        if ssh_rc != 0:
            return "fail", f"management SSH path failed after {stage_name} reboot"
    if before.get("pci_id") == cases["alternate_nic"].get("pci_id"):
        return "fail", "alternate-NIC negative control reused the target PCI device"
    rollback_rc = _number(cases["rollback"], "ssh_exit_code")
    if rollback_rc is None:
        return "unknown", "SSH continuity after rollback is unavailable"
    if cases["rollback"].get("driver") != before.get("driver") or rollback_rc != 0:
        return "fail", "driver/configuration rollback did not restore the previous binding"
    return "pass", reason + "; alternate NIC, SSH continuity and rollback passed"


def _check_desktop(cases: dict[str, dict[str, Any]]) -> tuple[str, str]:
    incident, control = cases["incident"], cases["control"]
    category = _classify_desktop_state(incident)
    incident_ssh = _number(incident, "ssh_exit_code")
    if incident_ssh is None:
        return "unknown", "SSH probe missing during the reported display/session incident"
    if incident_ssh != 0:
        return "unknown", "host reachability is not established independently of the display"
    signatures = incident.get("session_failure_signatures")
    if not signatures and category not in {"headless", "greeter_login_loop"}:
        return "fail", "incident state has no GNOME failure signature or distinct headless classification"
    if control.get("session_classification") != "active_session" or control.get("display_connected") is not True:
        return "unknown", "known-good graphical session/display control is incomplete"
    if _number(control, "ssh_exit_code") != 0:
        return "unknown", "known-good display control lacks an independent successful SSH probe"
    return _check_desktop_recovery(incident, cases["recovery"], cases["rollback"])


def _classify_desktop_state(observation: dict[str, Any]) -> str:
    if observation.get("session_classification") == "headless":
        return "headless"
    signatures = observation.get("session_failure_signatures")
    if signatures or observation.get("session_classification") in {"greeter", "session_ending"}:
        return "greeter_login_loop" if observation.get("session_classification") == "greeter" else "session_failure"
    if (observation.get("session_classification") == "active_session"
            and observation.get("display_connected") is True):
        return "healthy_desktop"
    if _number(observation, "ssh_exit_code") == 0:
        return "host_reachable_display_unresolved"
    if isinstance(_number(observation, "ssh_exit_code"), float):
        return "host_reachability_failed_total_host_state_unknown"
    return "unknown"


def _check_desktop_recovery(incident: dict[str, Any], recovery: dict[str, Any],
                            rollback: dict[str, Any]) -> tuple[str, str]:
    if recovery.get("session_classification") != "active_session" or recovery.get("display_connected") is not True:
        return "fail", "recovery did not restore an active graphical session on a connected display"
    incident_version = _text(incident, "package_version")
    recovery_version = _text(recovery, "package_version")
    if not incident_version or not recovery_version:
        return "unknown", "captured pre/post-update desktop package versions are missing"
    if recovery_version == incident_version:
        return "fail", "recovery package version did not change from the affected version"
    rollback_version = _text(rollback, "package_version")
    rollback_ssh = _number(rollback, "ssh_exit_code")
    if not rollback_version or rollback_ssh is None:
        return "unknown", "rollback package version or independent management probe is missing"
    if rollback_version != incident_version or rollback_ssh != 0:
        return "fail", "rollback did not restore the recorded package version with host reachability"
    return "pass", "incident was separable from host failure; known-good display, fixed session, and package rollback verified"


def _check_eee_counters(cases: dict[str, dict[str, Any]]) -> tuple[str, str]:
    direct, disabled, switch = cases["direct_eee_on"], cases["direct_eee_off"], cases["switch_control"]
    status, reason = _check_eee_states(direct, disabled)
    if status != "pass":
        return status, reason
    return _check_eee_measurements(cases, direct, disabled, switch)


def _check_eee_measurements(cases: dict[str, dict[str, Any]], direct: dict[str, Any],
                            disabled: dict[str, Any], switch: dict[str, Any]) -> tuple[str, str]:
    if _number(direct, "link_resets") is None or _number(disabled, "link_resets") is None:
        return "unknown", "direct-link A/B counters missing"
    switch_resets = _number(switch, "link_resets")
    if switch_resets is None:
        return "unknown", "switch-control link counter unavailable"
    if disabled["link_resets"] >= direct["link_resets"] or switch_resets != 0:
        return "fail", "EEE A/B or stable-switch negative control contradicts the proposed scope"
    if direct["link_resets"] <= 0:
        return "unknown", "direct-link failure did not reproduce during the measured EEE-on interval"
    return _check_eee_scope(cases, direct, disabled, switch)


def _check_eee_scope(cases: dict[str, dict[str, Any]], direct: dict[str, Any],
                     disabled: dict[str, Any], switch: dict[str, Any]) -> tuple[str, str]:
    if direct.get("topology") != "direct" or switch.get("topology") != "switch":
        return "fail", "direct-link and stable-switch controls are not distinct topologies"
    if _text(cases["identity"], "partner") != "Intel I225-V":
        return "unknown", "the reported Intel I225-V direct-link peer is not identified"
    if _number(direct, "cycles", 1) is None or _number(disabled, "cycles", 1) is None:
        return "unknown", "repeated EEE cycle counts unavailable"
    if direct["cycles"] < 3 or disabled["cycles"] < 3:
        return "unknown", "fewer than three direct-link A/B cycles were captured"
    if _number(direct, "packet_loss") is None or _number(disabled, "packet_loss") is None:
        return "unknown", "packet-loss observations unavailable for direct-link comparison"
    if _number(disabled, "ssh_reconnects", 3) is None:
        return "unknown", "three independent SSH reconnect probes are missing after EEE mitigation"
    return "pass", "direct-link and switch counter controls passed"


def _check_eee_states(direct: dict[str, Any], disabled: dict[str, Any]) -> tuple[str, str]:
    direct_state = _parse_eee_state(_text(direct, "output") or "")
    disabled_state = _parse_eee_state(_text(disabled, "output") or "")
    if direct_state == "disabled" or disabled_state == "active":
        return "fail", "native ethtool output contradicts the requested EEE-on/off A/B state"
    if direct_state is None or disabled_state is None:
        return "unknown", "native ethtool output does not identify both negotiated-on and disabled states"
    if direct_state not in {"active", "inactive"}:
        return "unknown", "direct-link negotiated EEE activity is unresolved"
    return "pass", "native ethtool outputs identify the EEE states"


def _parse_eee_state(output: str) -> str | None:
    match = re.search(r"(?im)^EEE status:\s*(enabled|disabled)\s*(?:-\s*(active|inactive))?\s*$", output)
    if match is None:
        return None
    enabled, activity = match.groups()
    if enabled.lower() == "disabled":
        return "disabled"
    if activity is None:
        return "enabled"
    return activity.lower()


def _check_eee(cases: dict[str, dict[str, Any]]) -> tuple[str, str]:
    status, reason = _check_eee_counters(cases)
    if status != "pass":
        return status, reason
    disabled = cases["direct_eee_off"]
    if disabled.get("ipv4") != "up" or disabled.get("ipv6") != "up":
        return "fail", "network connectivity did not recover with EEE change"
    initial_eee = _text(cases["identity"], "eee_state")
    rollback_eee = _text(cases["rollback"], "eee_state")
    if (not initial_eee or rollback_eee != initial_eee or _text(cases["rollback"], "ipv4") != "up"
            or _text(cases["rollback"], "ipv6") != "up"):
        return "fail", "EEE setting or network did not return to its original state on rollback"
    return "pass", "direct-link EEE A/B, switch control and bidirectional connectivity passed"


def _check_rescue(document: dict[str, Any], cases: dict[str, dict[str, Any]], directory: Path) -> tuple[str, str]:
    if not _text(cases["rescue_entry"], "entry_id") or not _text(cases["restoration"], "restored_entry"):
        return "unknown", "OEM rescue selection or restored boot entry was not observed"
    if cases["normal_boot"].get("boot_id") == cases["restoration"].get("boot_id"):
        return "fail", "rescue/restore sequence lacks a new boot identity"
    if cases["rescue_boot"].get("boot_id") in {cases["normal_boot"].get("boot_id"), cases["restoration"].get("boot_id")}:
        return "fail", "rescue path was not observed as its own boot transition"
    if not _text(cases["rescue_boot"], "boot_id"):
        return "unknown", "rescue boot identity unavailable"
    if _text(cases["rescue_boot"], "entry_id") != _text(cases["rescue_entry"], "entry_id"):
        return "fail", "booted rescue entry differs from the OEM rescue menu entry"
    if _text(cases["restoration"], "restored_entry") == _text(cases["rescue_entry"], "entry_id"):
        return "fail", "restoration still selects the rescue boot entry instead of normal boot"
    if cases["rescue_boot"].get("rescue_target") is not True:
        return "fail", "rescue boot lacks systemd.unit=rescue.target or emergency.target in kernel command line"
    return _check_rescue_restoration(document, cases, directory)


def _check_rescue_restoration(document: dict[str, Any], cases: dict[str, dict[str, Any]],
                              directory: Path) -> tuple[str, str]:
    if not _text(cases["restoration"], "network_route"):
        return "unknown", "restored boot management route unavailable"
    # The expiry is judged against the restoration capture's own clock, never the verifier's:
    # the same evidence must yield the same verdict on every later re-run. _load already
    # guarantees these rows exist with timezone-aware, strictly increasing captured_at.
    restored_at = max(datetime.fromisoformat(row["captured_at"].replace("Z", "+00:00"))
                      for row in document["captures"] if row["name"] == "restoration")
    restored, error = _verify_restored_service(directory, restored_at)
    if error:
        status = "unknown" if error.startswith("canary service restoration manifest unavailable") else "fail"
        return status, error
    if not restored:
        return "fail", "canary service content or mode differs from the verified pre-suspension manifest"
    return "pass", "OEM rescue transition, normal boot, management route, and canary service restoration verified"


def _verify_restored_service(directory: Path, restored_at: datetime) -> tuple[bool, str | None]:
    manifest_path = directory / "service-restore-manifest.json"
    try:
        raw = read_regular_bytes(manifest_path, 65_536)
        if len(raw) > 65_536:
            return False, "service restore manifest exceeds 64 KiB"
        manifest = strict_json_loads(raw.decode("utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError, RecursionError) as exc:
        return False, f"canary service restoration manifest unavailable: {exc}"
    if not isinstance(manifest, dict):
        return False, "canary service restoration manifest malformed"
    path_value, suspended_value = manifest.get("path"), manifest.get("suspended_path")
    digest, mode = manifest.get("sha256"), manifest.get("mode")
    expiry, watcher = manifest.get("expiry"), manifest.get("watcher")
    if (not isinstance(path_value, str) or not isinstance(suspended_value, str)
            or not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest)
            or type(mode) is not int or not isinstance(expiry, str) or not isinstance(watcher, str) or not watcher.strip()):
        return False, "manifest lacks exact path/hash/mode, expiry, or restoration watcher"
    try:
        expiry_day = datetime.fromisoformat(expiry).date()
    except ValueError:
        return False, "service restore expiry is not an ISO date/time"
    if expiry_day < restored_at.date():
        return False, "service restore was captured after the manifest expiry"
    original_relative = Path(path_value)
    suspended_relative = Path(suspended_value)
    if (original_relative.is_absolute() or suspended_relative.is_absolute()
            or ".." in original_relative.parts or ".." in suspended_relative.parts):
        return False, "service restore paths must stay relative to the evidence directory"
    original = directory / original_relative
    suspended = directory / suspended_relative
    try:
        actual = read_regular_bytes(original, 4 * 1024 * 1024)
        actual_digest = hashlib.sha256(actual).hexdigest()
        actual_mode = original.lstat().st_mode & 0o777
    except OSError:
        return False, "original canary service unit is unavailable after restore"
    return actual_digest == digest and actual_mode == mode and not suspended.exists(), None


def _check_thermal(document: dict[str, Any], cases: dict[str, dict[str, Any]]) -> tuple[str, str]:
    run, idle, rollback = (cases[name] for name in ("resident_workload", "idle_control", "rollback"))
    if _number(run, "capture_span_s", 300) is None:
        return "unknown", "raw resident-workload capture window is shorter than the five-minute minimum soak"
    if _number(run, "throughput", 0) is None or not re.fullmatch(r"[0-9a-f]{64}", _text(run, "workload_hash") or ""):
        return "unknown", "literal workload throughput output or derived command identity missing"
    if _number(run, "resident_bytes", 1) is None or _number(idle, "resident_bytes") != 0:
        return "unknown", "GPU process inventory does not distinguish resident workload from no-model control"
    meter = _text(run, "meter_id")
    if (_number(run, "power_w", 0) is None or not meter
            or _text(idle, "meter_id") != meter or _number(idle, "power_w", 0) is None):
        return "unknown", "same identified external meter is required for workload and idle control"
    if (_number(run, "fan_rpm", 1) is None or _number(rollback, "resident_bytes") != 0):
        return "unknown", "fan tachometer or proof of workload release from GPU memory is unavailable"
    source_text = " ".join(row["text"] for row in document.get("vendor_sources", [])
                            if isinstance(row, dict) and isinstance(row.get("text"), str))
    limits = _thermal_limits(source_text)
    run_thermal = _thermal_coverage_observation(run)
    rollback_thermal = _thermal_coverage_observation(rollback)
    if run_thermal is None or rollback_thermal is None:
        return "unknown", "raw thermal zone/hwmon series missing for workload or rollback"
    for channel in ("gpu_c", "cpu_c", "soc_c"):
        limit, value, recovered = limits.get(channel), run_thermal.get(channel), rollback_thermal.get(channel)
        if limit is None or value is None or recovered is None:
            return "unknown", f"OEM limit or raw {channel} sample missing from A/B and rollback"
        if value >= limit or recovered >= limit:
            return "fail", f"workload or rollback {channel} reached/exceeded its OEM limit"
    return "pass", "raw no-model/workload A/B, five-minute sensor/power soak, useful throughput, fan RPM and OEM-bounded rollback verified"


def _check_uvc(cases: dict[str, dict[str, Any]]) -> tuple[str, str]:
    failing, fixed = cases["stream_control"], cases["corrected_stack"]
    if _number(failing, "xhci_resets") is None or _number(fixed, "xhci_resets") is None:
        return "unknown", "USB trace lacks xHCI reset counters"
    if failing["xhci_resets"] <= 0 or fixed["xhci_resets"] != 0:
        return "fail", "affected/corrected UVC A/B does not reproduce then eliminate the controller failure"
    if _number(cases["no_ep0_control"], "xhci_resets") != 0 or _number(cases["no_ep0_control"], "ep0_after_stream_count") != 0:
        return "fail", "UVC no-EP0 negative control does not isolate the post-STREAMON control path"
    if (_number(fixed, "stream_seconds", 1) is None
            or _number(fixed, "ep0_after_stream_count") is None
            or fixed["ep0_after_stream_count"] <= 0):
        return "unknown", "corrected stream soak or EP0 behavior unobserved"
    affected_kernel = _text(cases["affected_stack"], "kernel_release")
    corrected_kernel = _text(cases["stack_identity"], "kernel_release")
    affected_driver = _text(cases["affected_stack"], "module_version")
    corrected_driver = _text(cases["stack_identity"], "module_version")
    camera = _text(cases["affected_stack"], "usb_device_id")
    if not all((affected_kernel, corrected_kernel, affected_driver, corrected_driver, camera)):
        return "unknown", "affected/corrected kernel, UVC driver versions, or USB camera identity missing"
    if (camera != _text(cases["stack_identity"], "usb_device_id")
            or camera != _text(cases["corrected_stack"], "usb_device_id")):
        return "fail", "UVC A/B did not retain the same camera USB identity"
    if affected_kernel == corrected_kernel and affected_driver == corrected_driver:
        return "fail", "corrected A/B reused the affected kernel and driver versions"
    if (_text(cases["rollback"], "kernel_release") != affected_kernel
            or _text(cases["rollback"], "module_version") != affected_driver):
        return "fail", "UVC rollback does not restore the affected kernel/driver versions"
    return "pass", "affected/corrected UVC stream, EP0 and xHCI controls passed"


CHECKS = {
    "FORUM-00-CX7-HOTPLUG-FAN-PROTECTION": _check_cx7,
    "FEATURE-FORUM-SBSA-WATCHDOG-STATE-01": lambda _doc, cases: _check_watchdog(cases),
    "FORUM-REALTEK-DRIVER-BINDING-01": lambda _doc, cases: _check_realtek(cases),
    "FEATURE-FORUM-DESKTOP-SESSION-POSTUPDATE-01": lambda _doc, cases: _check_desktop(cases),
    "FORUM-00-REALTEK-EEE-DIRECT-LINK": lambda _doc, cases: _check_eee(cases),
    "FORUM-00-GB10-THERMAL-RESIDENCY-ADMISSION": _check_thermal,
    "FORUM-02-USB-UVC-EP0": lambda _doc, cases: _check_uvc(cases),
}


def _evaluate_simple(document: dict[str, Any], finding_id: str, directory: Path) -> tuple[str, str]:
    if finding_id == "FORUM-02-GX10-READ-INTEGRITY":
        return _evaluate_gx10(document, directory)
    cases, error = _gather_cases(document, finding_id)
    if error:
        return "unknown", error
    if finding_id == "FORUM-00-CX7-HOTPLUG-FAN-PROTECTION":
        return _check_cx7(document, cases)
    if finding_id == "FEATURE-FORUM-RESCUE-RUNBOOK-01":
        sources_ok, source_error = _references(document)
        if not sources_ok:
            return "unknown", source_error or "version-scoped OEM rescue path unavailable"
        return _check_rescue(document, cases, directory)
    if finding_id not in CHECKS:
        return "fail", "unsupported subject predicate"
    sources_ok, source_error = _references(document)
    if not sources_ok:
        return "unknown", source_error or "version-scoped source unavailable"
    return CHECKS[finding_id](document, cases)


def evaluate(finding_id: str, directory: str | Path) -> dict[str, Any]:
    if finding_id not in IDS:
        return _result("fail", "unsupported hardware forum subject", [])
    document, path, error = _load(finding_id, Path(directory))
    if error:
        return error
    assert document is not None
    status, reason = _evaluate_simple(document, finding_id, Path(directory))
    files = [str(path)]
    if finding_id == "FORUM-02-GX10-READ-INTEGRITY":
        files.append(str(Path(directory) / "nvme-snapshot.json"))
    return _result(status, reason, files)
