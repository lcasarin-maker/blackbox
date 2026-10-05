"""Evaluate netconsole/receiver/security/rollback captures.

JSON metadata, command strings, identity receipts, and provenance labels are
caller-supplied and unauthenticated; matching hashes establish byte consistency,
not receiver origin or authenticity.
"""
from __future__ import annotations

import argparse
import hashlib
import ipaddress
import json
from pathlib import Path
import re
import sys
from datetime import datetime
from datetime import timezone
from typing import Any

from tools.kernel_capture import capture
from tools.netconsole_marker import classify, verify as verify_marker

MAX_EVIDENCE_BYTES = 1024 * 1024


def verify(directory: Path) -> dict[str, Any]:
    try:
        doc = _read_json(directory / "kernel-capture.json")
        receipt = _read_json(directory / "receiver.json")
    except (OSError, UnicodeError, ValueError, json.JSONDecodeError, RecursionError) as exc:
        return _result("unknown", [f"required raw capture unavailable: {exc}"], 1)
    if not isinstance(doc, dict) or not isinstance(receipt, dict):
        return _result("unknown", ["kernel capture and receiver receipt must be JSON objects"], 1)
    try:
        return _evaluate(doc, receipt)
    except (KeyError, TypeError, ValueError, AttributeError, OverflowError) as exc:
        return _result("unknown", [f"raw kernel/receiver evidence malformed: {exc}"], 1)


def _read_json(path: Path) -> Any:
    with path.open("rb") as stream:
        raw = stream.read(MAX_EVIDENCE_BYTES + 1)
    if len(raw) > MAX_EVIDENCE_BYTES:
        raise ValueError(f"{path.name} exceeds 1 MiB bound")
    return json.loads(raw.decode("utf-8"))


def _evaluate(doc: dict[str, Any], receipt: dict[str, Any]) -> dict[str, Any]:
    kernel = doc.get("kernel")
    boot_observation = kernel.get("boot_id") if isinstance(kernel, dict) else None
    if not isinstance(boot_observation, dict):
        return _result("unknown", ["boot identity observation missing or malformed"], 1)
    boot = boot_observation.get("value")
    if not isinstance(boot, str) or not boot:
        status = boot_observation.get("status")
        return _result("unknown" if status in ("could_not_run", "unavailable") else "fail",
                       ["kernel capture identity/schema missing"], int(status in ("could_not_run", "unavailable")))
    observed = capture(Path("/"))
    # A captured file is evidence only when it agrees with a fresh readonly capture.
    if doc.get("kernel") != observed.get("kernel") or doc.get("netconsole") != observed.get("netconsole"):
        return _result("fail", ["saved kernel/netconsole capture differs from current readonly observations"], 0)
    unreadable = _netconsole_unreadable(observed)
    if unreadable:
        return _result("unknown", ["netconsole configuration capture has unreadable required fields"], unreadable)
    netconsole = doc["netconsole"]
    return _receiver(receipt, boot, netconsole)


def _netconsole_unreadable(observed: dict[str, Any]) -> int:
    net = observed.get("netconsole", {})
    rows = (net.get("module", {}), net.get("static_parameter", {}), net.get("dynamic_targets_status", {}),
            observed.get("boot_parameter_netconsole", {}))
    return sum(row.get("status") == "could_not_run" for row in rows)


def _receiver(receipt: dict[str, Any], boot: str, netconsole: dict[str, Any]) -> dict[str, Any]:
    state_issue = _rollback_states(receipt, netconsole)
    if state_issue is not None:
        return state_issue
    marker_result = _receiver_marker(receipt, boot)
    if isinstance(marker_result, dict):
        return marker_result
    controls = _receiver_controls(receipt, boot, netconsole)
    if controls["status"] != "pass":
        return controls
    route = _unavailable_control(receipt.get("broken_route_control"), "route")
    if route is not None:
        return route
    receiver = _unavailable_control(receipt.get("unavailable_receiver_control"), "receiver")
    if receiver is not None:
        return receiver
    if any(control.get("marker") == receipt.get("marker") for control in
           (receipt["broken_route_control"], receipt["unavailable_receiver_control"])):
        return _result("fail", ["negative-control markers must be distinct from the delivered marker"], 0)
    continuity = _continuity(receipt.get("local_continuity"),
                             boot,
                             (receipt["broken_route_control"], receipt["unavailable_receiver_control"]))
    if continuity is not None:
        return continuity
    return _correlation_and_retention(receipt, boot)


def _rollback_states(receipt: dict[str, Any], current: dict[str, Any]) -> dict[str, Any] | None:
    rollback = receipt.get("rollback_capture")
    if not isinstance(rollback, dict) or not all(isinstance(rollback.get(key), dict)
                                                for key in ("before", "during", "after")):
        return _result("unknown", ["raw before/during/after netconsole state captures required"], 1)
    before, during, after = (rollback[key] for key in ("before", "during", "after"))
    if after != current:
        return _result("fail", ["fresh after-state does not match the current netconsole configuration"], 0)
    if before != after:
        return _result("fail", ["netconsole module/configuration was not restored to its captured before-state"], 0)
    if not _configured_during(during):
        return _result("fail", ["during-state lacks a loaded module and configured netconsole target"], 0)
    target_hashes = []
    static = during.get("static_parameter")
    if isinstance(static, dict) and isinstance(static.get("configuration_sha256"), str):
        target_hashes.append(static["configuration_sha256"])
    for target in during.get("targets", []):
        if isinstance(target, dict) and isinstance(target.get("configuration_sha256"), str):
            target_hashes.append(target["configuration_sha256"])
    target_hash = receipt.get("configured_target_sha256")
    if not isinstance(target_hash, str) or target_hash not in target_hashes:
        return _result("unknown", ["receiver destination is not bound to a captured configured target"], 1)
    return None


def _configured_during(snapshot: dict[str, Any]) -> bool:
    module = snapshot.get("module")
    if not isinstance(module, dict) or module.get("status") not in ("loaded", "built_in"):
        return False
    static = snapshot.get("static_parameter")
    static_configured = isinstance(static, dict) and static.get("status") == "read" and static.get("configured") is True
    targets = snapshot.get("targets")
    dynamic_configured = (snapshot.get("dynamic_targets_status", {}).get("status") == "read" and
                          isinstance(targets, list) and any(isinstance(row, dict) and
                          row.get("status") == "observed" and
                          isinstance(row.get("configuration_sha256"), str) and
                          row["configuration_sha256"] for row in targets))
    return static_configured or dynamic_configured


def _receiver_marker(receipt: dict[str, Any], boot: str) -> dict[str, Any] | None:
    log = receipt.get("log_path")
    marker = receipt.get("marker")
    if not isinstance(log, str) or not isinstance(marker, str):
        return _result("unknown", ["receiver log path and exact expected marker required"], 1)
    marker_result = verify_marker(Path(log), marker)
    if marker_result["status"] != "present":
        return _result("fail" if marker_result["status"] in ("absent", "incomplete") else "unknown",
                       [f"receiver marker result: {marker_result['status']}", *marker_result.get("findings", [])],
                       marker_result.get("could_not_run", 0))
    return _verify_marker_receipt(receipt, boot, log, marker, marker_result)


def _verify_marker_receipt(receipt: dict[str, Any], boot: str, log: str, marker: str,
                           marker_result: dict[str, Any]) -> dict[str, Any] | None:
    provenance = receipt.get("provenance")
    if provenance is None:
        return _result("unknown", ["receiver capture provenance field is absent"], 1)
    if provenance != "receiver_capture" or boot not in marker:
        return _result("fail", ["receiver marker must contain target boot identity and have receiver provenance"], 0)
    command = receipt.get("capture_command")
    if not isinstance(command, list) or not command:
        return _result("unknown", ["raw receiver capture command is absent"], 1)
    capture_hash = receipt.get("capture_sha256")
    if capture_hash is None:
        return _result("unknown", ["receiver capture digest is absent"], 1)
    if not _receiver_command(command) or capture_hash != marker_result.get("capture_sha256"):
        return _result("fail", ["receiver log digest or literal capture command does not match bytes read"], 0)
    privacy_status, text = _privacy_safe(Path(log), marker, marker_result["capture_sha256"])
    if privacy_status == "unknown":
        return _result("unknown", ["receiver bytes became unreadable during bounded privacy inspection"], 1)
    if privacy_status == "fail" or text is None:
        return _result("fail", ["receiver capture contains content outside the exact marker or includes an IP/MAC address"], 0)
    return _verify_receiver_identity(receipt, boot, marker, text)


def _verify_receiver_identity(receipt: dict[str, Any], boot: str, marker: str, text: str) -> dict[str, Any] | None:
    remote = _receiver_is_remote(receipt)
    if remote is None:
        return _result("unknown", ["raw target and receiver hostname/machine-id command outputs required"], 1)
    if not remote:
        return _result("fail", ["receiver hostname/machine identity is not distinct from target identity"], 0)
    negative = receipt.get("negative_marker")
    if not isinstance(negative, str) or not negative.strip() or negative == marker:
        return _result("unknown", ["distinct absent-marker negative control required"], 1)
    if classify(text, negative) != "absent":
        return _result("fail", ["absent-marker negative control was not classified absent"], 0)
    return None


def _receiver_controls(receipt: dict[str, Any], boot: str, netconsole: dict[str, Any]) -> dict[str, Any]:
    secure_raw = receipt.get("secure_boot_output")
    signer_raw = receipt.get("module_signer_output")
    if (not isinstance(secure_raw, str) or not secure_raw.strip() or not isinstance(signer_raw, str) or
            receipt.get("module_signer_command") != ["modinfo", "-F", "signer", "netconsole"]):
        return _result("unknown", ["raw Secure Boot and module signer command output required"], 1)
    secure = secure_raw.lower()
    enabled = re.search(r"secureboot\s+(enabled|disabled)", secure)
    if not enabled:
        return _result("fail", ["Secure Boot output lacks an enabled/disabled state"], 0)
    signer = signer_raw.strip()
    if enabled.group(1) != "enabled":
        return _result("fail", ["target Secure Boot must be enabled during the netconsole marker test"], 0)
    if not signer:
        return _result("fail", ["Secure Boot enabled module has no observed signer"], 0)
    if not isinstance(netconsole, dict) or not isinstance(netconsole.get("module"), dict):
        return _result("unknown", ["target netconsole module state is incomplete"], 1)
    rollback = receipt.get("rollback_capture")
    if not isinstance(rollback, dict) or not isinstance(rollback.get("during"), dict):
        return _result("unknown", ["during-test target configuration capture is absent"], 1)
    persistence_issue = _persistent_configuration(receipt)
    if persistence_issue:
        return persistence_issue
    return _result("pass", [], 0)


def _persistent_configuration(receipt: dict[str, Any]) -> dict[str, Any] | None:
    captures = receipt.get("persistence_captures")
    paths = ("/etc/modprobe.d/blackbox-netconsole.conf", "/etc/modules-load.d/blackbox-netconsole.conf")
    if not isinstance(captures, list) or len(captures) != 6:
        return _result("unknown", ["before/during/after persistence file captures required"], 1)
    indexed, issue = _persistence_index(captures, paths)
    if issue:
        return issue
    assert indexed is not None
    for path in paths:
        captures = (indexed[(path, "before")], indexed[(path, "during")], indexed[(path, "after")])
        issue = _persistence_path_issue(path, captures, paths[0], receipt)
        if issue:
            return issue
    return None


def _persistence_index(captures: list[Any], paths: tuple[str, str]) -> tuple[dict[tuple[str, str], dict[str, Any]] | None, dict[str, Any] | None]:
    indexed: dict[tuple[str, str], dict[str, Any]] = {}
    for row in captures:
        if not isinstance(row, dict) or row.get("path") not in paths or row.get("phase") not in ("before", "during", "after"):
            return None, _result("unknown", ["persistence capture identity/phase malformed"], 1)
        key = (row["path"], row["phase"])
        if key in indexed or row.get("command") != ["cat", row["path"]] or type(row.get("returncode")) is not int:
            return None, _result("unknown", ["persistence capture command/result missing or duplicated"], 1)
        if (not isinstance(row.get("stdout"), str) or not isinstance(row.get("stderr"), str) or
                type(row.get("mode")) is not int or row["mode"] < 0 or row["mode"] > 0o7777 or
                type(row.get("symlink")) is not bool or not isinstance(row.get("sha256"), str)):
            return None, _result("unknown", ["persistence raw stdout/stderr missing"], 1)
        raw = row["stdout"].encode()
        expected_hash = hashlib.sha256(raw).hexdigest() if row["returncode"] == 0 else ""
        if row["sha256"] != expected_hash:
            return None, _result("fail", ["persistent file digest does not match captured bytes"], 0)
        indexed[key] = row
    return indexed, None


def _persistence_path_issue(path: str, captures: tuple[dict[str, Any], dict[str, Any], dict[str, Any]], modprobe_path: str, receipt: dict[str, Any]) -> dict[str, Any] | None:
    before, during, after = captures
    if any(before[key] != after[key] for key in ("returncode", "stdout", "stderr", "mode", "sha256", "symlink")):
        return _result("fail", [f"persistent configuration {path} was not restored to its before-state"], 0)
    if before["returncode"] not in (0, 1):
        return _result("unknown", [f"cannot classify baseline existence of {path}"], 1)
    if before["returncode"] == 1 and (before["stdout"] or "No such file" not in before["stderr"]):
        return _result("unknown", [f"baseline absence of {path} lacks raw missing-file diagnostic"], 1)
    if during["returncode"] != 0:
        return _result("fail", [f"persistent configuration {path} is unavailable during test"], 0)
    if during["symlink"]:
        return _result("fail", [f"persistent configuration {path} unexpectedly resolves through a symlink"], 0)
    if path == modprobe_path:
        directives = [line.strip() for line in during["stdout"].splitlines() if line.strip().startswith("options netconsole")]
        parameter = None
        if len(directives) == 1:
            match = re.fullmatch(r"options netconsole netconsole=(\d+@[^,\s]+,\d+@[^/\s]+/[0-9a-fA-F:]{17})", directives[0])
            if match:
                parameter = match.group(1)
        configured = bool(parameter and receipt.get("netconsole_parameter") == parameter)
    else:
        configured = during["stdout"].splitlines() == ["netconsole"]
    return None if configured else _result("fail", [f"persistent configuration {path} lacks the active netconsole entry"], 0)


def _unavailable_control(control: Any, kind: str) -> dict[str, Any] | None:
    issue = _unavailable_command_issue(control, kind)
    if issue is not None:
        return issue
    return _unavailable_logs_issue(control, kind)


def _unavailable_command_issue(control: Any, kind: str) -> dict[str, Any] | None:
    if not isinstance(control, dict):
        return _result("unknown", [f"raw {kind}-unavailable negative control is absent"], 1)
    command = control.get("command")
    if not isinstance(command, list) or not command or not all(isinstance(part, str) and part for part in command):
        return _result("unknown", [f"raw {kind}-unavailable command is absent"], 1)
    if type(control.get("returncode")) is not int or type(control.get("started_ns")) is not int or type(control.get("ended_ns")) is not int:
        return _result("unknown", [f"raw {kind}-unavailable timestamps/result are incomplete"], 1)
    if control["started_ns"] < 0 or control["ended_ns"] <= control["started_ns"]:
        return _result("fail", [f"{kind}-unavailable control has invalid time interval"], 0)
    stdout, stderr = control.get("stdout"), control.get("stderr")
    if not isinstance(stdout, str) or not isinstance(stderr, str) or not (stdout + stderr).strip():
        return _result("unknown", [f"raw {kind}-unavailable command output is absent"], 1)
    if control["returncode"] == 0:
        return _result("fail", [f"{kind}-unavailable control did not make the path unavailable"], 0)
    if kind == "route" and (Path(command[0]).name != "ip" or command[1:3] != ["route", "get"] or
            re.search(r"(?i)(unreachable|network is unreachable|no route to host|route not found)", stdout + stderr) is None):
        return _result("unknown", ["route control failure lacks raw unreachable-route diagnostic"], 1)
    if kind == "receiver" and (Path(command[0]).name != "systemctl" or command[1:2] != ["is-active"] or len(command) < 3 or
            (stdout + stderr).strip() != "inactive"):
        return _result("unknown", ["receiver control failure lacks raw unavailable-receiver diagnostic"], 1)
    return None


def _unavailable_logs_issue(control: dict[str, Any], kind: str) -> dict[str, Any] | None:
    marker = control.get("marker")
    before_path, after_path = control.get("before_log_path"), control.get("after_log_path")
    expected_before, expected_after = control.get("before_log_sha256"), control.get("after_log_sha256")
    if not isinstance(marker, str) or not marker.strip() or not isinstance(before_path, str) or not isinstance(after_path, str):
        return _result("unknown", [f"{kind}-unavailable receiver log snapshots and test marker are required"], 1)
    for path_text, digest in ((before_path, expected_before), (after_path, expected_after)):
        if not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest):
            return _result("unknown", [f"{kind}-unavailable receiver log digest is malformed"], 1)
        marker_result = verify_marker(Path(path_text), marker)
        if marker_result["status"] == "unknown":
            return _result("unknown", [f"{kind}-unavailable receiver log could not be read"], 1)
        if marker_result["capture_sha256"] != digest:
            return _result("fail", [f"{kind}-unavailable receiver log digest does not match raw bytes"], 0)
        if marker_result["status"] != "absent":
            return _result("fail", [f"{kind}-unavailable marker unexpectedly reached the receiver"], 0)
    return None


def _continuity(value: Any, boot: str, controls: tuple[dict[str, Any], dict[str, Any]]) -> dict[str, Any] | None:
    if not isinstance(value, dict):
        return _result("unknown", ["local journal and telemetry continuity captures are absent"], 1)
    journal = value.get("journal_capture")
    telemetry = value.get("telemetry_capture")
    issue = _continuity_capture_issue(journal, telemetry)
    if issue:
        return issue
    assert isinstance(journal, dict) and isinstance(telemetry, dict)
    try:
        journal_rows = [json.loads(line) for line in journal["stdout"].splitlines() if line]
        telemetry_rows = [json.loads(line) for line in telemetry["stdout"].splitlines() if line]
    except (json.JSONDecodeError, RecursionError):
        return _result("unknown", ["local journal/telemetry records are malformed JSONL"], 1)
    if not journal_rows or not telemetry_rows or any(not isinstance(row, dict) for row in journal_rows + telemetry_rows):
        return _result("unknown", ["local journal/telemetry raw records are absent or malformed"], 1)
    parsed, issue = _continuity_timestamps(journal_rows, telemetry_rows, boot)
    if issue:
        return issue
    assert parsed is not None
    intervals, issue = _control_intervals(controls)
    if issue:
        return issue
    assert intervals is not None
    start_us, end_us = min(x[0] for x in intervals), max(x[1] for x in intervals)
    for name, values in parsed:
        if not any(ts <= start_us for ts in values) or not any(ts >= end_us for ts in values):
            return _result("fail", [f"local {name} records do not span both receiver negative controls"], 0)
    return None


def _continuity_capture_issue(journal: Any, telemetry: Any) -> dict[str, Any] | None:
    if not isinstance(journal, dict) or journal.get("command") != ["journalctl", "--output=json", "--since", "-2min"] or type(journal.get("returncode")) is not int or journal["returncode"] != 0 or not isinstance(journal.get("stdout"), str):
        return _result("unknown", ["raw local journal continuity capture is absent"], 1)
    if not isinstance(telemetry, dict) or type(telemetry.get("returncode")) is not int or telemetry["returncode"] != 0 or not isinstance(telemetry.get("stdout"), str):
        return _result("unknown", ["raw local telemetry continuity capture is absent"], 1)
    command = telemetry.get("command")
    if (not isinstance(command, list) or len(command) != 4 or Path(str(command[0])).name != "tail" or
            command[1:3] != ["-c", str(MAX_EVIDENCE_BYTES)] or not isinstance(command[3], str) or
            not command[3].endswith("atom_gpu_telemetry.jsonl")):
        return _result("unknown", ["bounded raw read of atom_gpu_telemetry.jsonl is required"], 1)
    if len(journal["stdout"].encode()) > MAX_EVIDENCE_BYTES or len(telemetry["stdout"].encode()) > MAX_EVIDENCE_BYTES:
        return _result("unknown", ["local continuity output exceeds bounded capture size"], 1)
    return None


def _continuity_timestamps(journal_rows: list[dict[str, Any]], telemetry_rows: list[dict[str, Any]], boot: str) -> tuple[list[tuple[str, list[int]]] | None, dict[str, Any] | None]:
    journal_times = [row.get("__REALTIME_TIMESTAMP") for row in journal_rows]
    telemetry_times = [row.get("ts") for row in telemetry_rows]
    boots_journal = [row.get("_BOOT_ID") for row in journal_rows]
    boots_telemetry = [row.get("boot_id") for row in telemetry_rows]
    if (any(not isinstance(ts, str) or not ts.isdecimal() for ts in journal_times) or
            any(not isinstance(ts, str) for ts in telemetry_times) or
            any(not isinstance(b, str) or not b for b in boots_journal + boots_telemetry) or
            set(boots_journal + boots_telemetry) != {boot} or
            any(row.get("evento") != "muestra" for row in telemetry_rows)):
        return None, _result("unknown", ["journal and telemetry records lack raw timestamps"], 1)
    journal_text = [ts for ts in journal_times if isinstance(ts, str)]
    telemetry_text = [ts for ts in telemetry_times if isinstance(ts, str)]
    try:
        telemetry_dt = [datetime.fromisoformat(ts.replace("Z", "+00:00")) for ts in telemetry_text]
        if any(value.tzinfo is None for value in telemetry_dt):
            return None, _result("unknown", ["telemetry timestamps require explicit timezone offsets"], 1)
        journal_us = [int(ts) for ts in journal_text]
        telemetry_us = [int(value.astimezone(timezone.utc).timestamp() * 1_000_000) for value in telemetry_dt]
    except (ValueError, OverflowError):
        return None, _result("unknown", ["journal/telemetry epoch timestamps malformed"], 1)
    if (any(a >= b for a, b in zip(journal_us, journal_us[1:])) or
            any(a >= b for a, b in zip(telemetry_us, telemetry_us[1:]))):
        return None, _result("fail", ["local journal/telemetry continuity timestamps are not increasing"], 0)
    return [("journal", journal_us), ("telemetry", telemetry_us)], None


def _control_intervals(controls: tuple[dict[str, Any], dict[str, Any]]) -> tuple[list[tuple[int, int]] | None, dict[str, Any] | None]:
    intervals: list[tuple[int, int]] = []
    for control in controls:
        try:
            start = datetime.fromisoformat(control["started_at"].replace("Z", "+00:00"))
            end = datetime.fromisoformat(control["ended_at"].replace("Z", "+00:00"))
        except (KeyError, TypeError, ValueError, AttributeError):
            return None, _result("unknown", ["negative-control wall-clock timestamps required for epoch correlation"], 1)
        if start.tzinfo is None or end.tzinfo is None or end <= start:
            return None, _result("unknown", ["negative-control wall-clock interval invalid"], 1)
        intervals.append((int(start.timestamp() * 1_000_000), int(end.timestamp() * 1_000_000)))
    return intervals, None


def _correlation_and_retention(receipt: dict[str, Any], boot: str) -> dict[str, Any]:
    if receipt.get("correlation_boot_id") != boot:
        return _result("fail" if isinstance(receipt.get("correlation_boot_id"), str) else "unknown",
                       ["receiver marker boot identity is absent or differs from target boot"],
                       int(not isinstance(receipt.get("correlation_boot_id"), str)))
    timestamps = receipt.get("capture_timestamps")
    if not isinstance(timestamps, dict):
        return _result("unknown", ["receiver/target timestamp correlation capture is absent"], 1)
    try:
        parsed = {key: datetime.fromisoformat(timestamps[key].replace("Z", "+00:00"))
                  for key in ("target_start", "target_end", "receiver_start", "receiver_end", "marker")}
    except (KeyError, TypeError, ValueError, AttributeError):
        return _result("unknown", ["target, receiver and marker timestamps must be RFC3339"], 1)
    if any(value.tzinfo is None for value in parsed.values()):
        return _result("unknown", ["correlation timestamps require explicit timezone offsets"], 1)
    if not parsed["target_start"] <= parsed["marker"] <= parsed["target_end"] or not parsed["receiver_start"] <= parsed["marker"] <= parsed["receiver_end"]:
        return _result("fail", ["target, receiver and marker timestamps are not correlated within captured windows"], 0)
    retention = receipt.get("retention_capture")
    if not isinstance(retention, dict) or retention.get("command") != ["cat", "/etc/blackbox/netconsole-retention.conf"] or type(retention.get("returncode")) is not int or retention["returncode"] != 0:
        return _result("unknown", ["raw receiver destination/retention policy capture is absent"], 1)
    policy = retention.get("stdout")
    receiver = receipt.get("receiver_identity")
    destination = re.search(r"(?m)^destination=([A-Za-z0-9_.-]+)$", policy) if isinstance(policy, str) else None
    if (not isinstance(policy, str) or not destination or not isinstance(receiver, dict) or
            destination.group(1) != receiver.get("hostname") or
            not re.search(r"(?m)^max_age_hours=[1-9][0-9]*$", policy) or
            not re.search(r"(?m)^max_bytes=[1-9][0-9]*$", policy)):
        return _result("unknown", ["receiver destination and positive retention limits are incomplete"], 1)
    return _result("pass", [], 0)


def _privacy_safe(path: Path, marker: str, expected_sha256: str) -> tuple[str, str | None]:
    try:
        with path.open("rb") as stream:
            raw = stream.read(MAX_EVIDENCE_BYTES + 1)
    except OSError:
        return "unknown", None
    if len(raw) > MAX_EVIDENCE_BYTES:
        return "unknown", None
    if hashlib.sha256(raw).hexdigest() != expected_sha256:
        return "fail", None
    try:
        text = raw.decode("utf-8")
    except UnicodeError:
        return "fail", None
    lines = [line for line in text.splitlines() if line]
    if len(lines) != 1 or not _netconsole_payload(lines[0], marker):
        return "fail", None
    if re.search(r"(?i)\b(?:[0-9a-f]{2}:){5}[0-9a-f]{2}\b", marker):
        return "fail", None
    for token in re.findall(r"[0-9a-fA-F:.]+", marker):
        try:
            ipaddress.ip_address(token)
        except ValueError:
            continue
        return "fail", None
    return "pass", text


def _receiver_command(command: Any) -> bool:
    if not isinstance(command, list) or not command or not all(isinstance(part, str) for part in command):
        return False
    executable = Path(command[0]).name
    return executable in {"journalctl", "nc", "ncat", "netcat", "socat", "syslogd"}


def _netconsole_payload(line: str, marker: str) -> bool:
    syslog_pri = re.match(r"^<([0-9]{1,3})>", line)
    if syslog_pri:
        if int(syslog_pri.group(1)) > 191:
            return False
        line = line[syslog_pri.end():]
    if ";" in line:
        header, payload = line.split(";", maxsplit=1)
        fields = header.split(",")
        if fields and re.fullmatch(r"ncfrag=\d+/\d+", fields[-1]):
            return False
        if len(fields) == 4 and not (fields[0].isdigit() and 0 <= int(fields[0]) <= 191 and
                fields[1].isdigit() and fields[2].isdigit() and fields[3] in ("-", "c")):
            return False
        if len(fields) == 5 and not (re.fullmatch(r"[0-9][A-Za-z0-9._+-]*", fields[0]) and
                fields[1].isdigit() and 0 <= int(fields[1]) <= 191 and fields[2].isdigit() and
                fields[3].isdigit() and fields[4] in ("-", "c")):
            return False
        if len(fields) not in (4, 5):
            return False
    else:
        payload = line
    return payload == marker


def _receiver_is_remote(receipt: dict[str, Any]) -> bool | None:
    target = receipt.get("target_identity")
    receiver = receipt.get("receiver_identity")
    if not isinstance(target, dict) or not isinstance(receiver, dict):
        return None
    for identity in (target, receiver):
        if identity.get("hostname_command") != ["hostnamectl", "--static"] or not isinstance(identity.get("hostname"), str) or not identity["hostname"].strip():
            return None
        if identity.get("machine_id_command") != ["cat", "/etc/machine-id"] or not isinstance(identity.get("machine_id"), str) or not identity["machine_id"].strip():
            return None
    return target["hostname"] != receiver["hostname"] and target["machine_id"] != receiver["machine_id"]


def _result(status: str, findings: list[str], could_not_run: int) -> dict[str, Any]:
    return {"status": status, "findings": findings, "could_not_run": could_not_run,
            "could_not_run_count": could_not_run, "fail": int(status == "fail")}


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--evidence", type=Path, required=True)
    a = p.parse_args(argv)
    out = verify(a.evidence)
    print(json.dumps(out, sort_keys=True))
    return {"pass": 0, "fail": 1, "unknown": 2}[out["status"]]


if __name__ == "__main__":
    sys.exit(main())
