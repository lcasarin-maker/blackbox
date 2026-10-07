"""Classify Wi-Fi isolation from raw NetworkManager, host, and route probes."""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime
from pathlib import Path
import re
import shlex
import sys
from typing import Any, TypeGuard
from urllib.parse import urlparse

from tools.capture_io import read_regular_bytes, strict_json_loads

ROOT = Path(__file__).resolve().parents[1]
FINDING = "FEATURE-FORUM-WIFI-ISOLATION-01"
MAX_CAPTURE_BYTES = 4_000_000


def _result(status: str, reason: str, files: list[str]) -> dict[str, Any]:
    return {"status": status, "reason": reason, "files": files,
            "fail": int(status == "fail"), "could_not_run": int(status == "unknown")}


def _valid_timestamps(rows: list[dict[str, Any]]) -> bool:
    times: list[datetime] = []
    for row in rows:
        captured_at = row.get("captured_at")
        if captured_at is None:
            continue
        if not isinstance(captured_at, str):
            return False
        try:
            stamp = datetime.fromisoformat(captured_at.replace("Z", "+00:00"))
        except ValueError:
            return False
        if stamp.tzinfo is None:
            return False
        times.append(stamp)
    return (not times or (len(times) == len(rows)
            and all(left < right for left, right in zip(times, times[1:]))))


def _valid_rows(rows: Any) -> TypeGuard[list[dict[str, Any]]]:
    return isinstance(rows, list) and len(rows) <= 20_000 and all(
        isinstance(row, dict) and isinstance(row.get("cmd"), str) and bool(row["cmd"].strip())
        and type(row.get("exit")) is int and isinstance(row.get("stdout"), str)
        and isinstance(row.get("stderr", ""), str) for row in rows
    )


def _read_capture(path: Path) -> tuple[dict[str, Any], list[dict[str, Any]]] | None:
    try:
        raw = read_regular_bytes(path, MAX_CAPTURE_BYTES)
        if len(raw) > MAX_CAPTURE_BYTES:
            return None
        data = strict_json_loads(raw.decode("utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError, RecursionError):
        return None
    if not isinstance(data, dict) or data.get("id") != FINDING:
        return None
    rows = data.get("commands")
    if not _valid_rows(rows):
        return None
    if not _valid_timestamps(rows):
        return None
    return data, rows


def _tokens(row: dict[str, Any]) -> list[str]:
    try:
        return shlex.split(row["cmd"])
    except ValueError:
        return []


def _command_args(row: dict[str, Any]) -> list[str]:
    """Return executable argv after supported privilege wrappers, never later argv words."""
    argv = _tokens(row)
    while argv and Path(argv[0]).name in {"sudo", "doas"}:
        argv = argv[1:]
        while argv and argv[0] in {"-n", "--non-interactive", "-E", "--preserve-env", "--"}:
            argv = argv[1:]
        if argv and argv[0] in {"-u", "--user", "-g", "--group"}:
            argv = argv[2:]
    return argv


def _has_program(row: dict[str, Any], program: str) -> bool:
    argv = _command_args(row)
    return bool(argv and Path(argv[0]).name == program)


def _ssh_target(row: dict[str, Any]) -> str | None:
    argv = _command_args(row)
    if not argv or Path(argv[0]).name != "ssh":
        return None
    options_with_argument = {"-b", "-c", "-D", "-E", "-e", "-F", "-I", "-i", "-J", "-L",
                            "-l", "-m", "-O", "-o", "-p", "-Q", "-R", "-S", "-W", "-w"}
    index = 1
    while index < len(argv):
        token = argv[index]
        if token == "--":
            return argv[index + 1] if index + 1 < len(argv) else None
        if not token.startswith("-"):
            return token
        if token in {"-V", "-G", "-Q", "-O"}:
            return None
        if token in options_with_argument:
            index += 1
        elif token.startswith("-") and not token.startswith("--"):
            flags = token[1:]
            if not flags or any(flag in flags for flag in "VGQON"):
                return None
            # These common no-argument flags are sufficient for captured probes.
            # Unknown options remain CNR; attached values are accepted only for
            # the known argument-taking options above.
            if any(flag not in "1246ABCafgKkMmnqTt vXxYy".replace(" ", "") for flag in flags):
                return None
        else:
            return None
        index += 1
    return None


def _is_loopback_probe(row: dict[str, Any]) -> bool:
    argv = _command_args(row)
    target = _ssh_target(row)
    return ((bool(argv) and Path(argv[0]).name == "ping"
             and any(token in {"127.0.0.1", "::1", "localhost"} for token in argv[1:]))
            or (target is not None and target in {"localhost", "127.0.0.1", "::1"}))


def _loopback_probe(row: dict[str, Any]) -> bool:
    argv = _command_args(row)
    if argv and Path(argv[0]).name == "ping" and _is_loopback_probe(row):
        return row["exit"] == 0 and bool(re.search(r"\b[1-9]\d* (?:packets? )?received\b|bytes from (?:127\.0\.0\.1|localhost)", row["stdout"], re.I))
    if argv and Path(argv[0]).name == "ssh" and _is_loopback_probe(row):
        return row["exit"] == 0 and bool(row["stdout"].strip())
    return False


def _management_probe(row: dict[str, Any]) -> bool:
    target = _ssh_target(row)
    return target is not None and target not in {"localhost", "127.0.0.1", "::1"}


def _management_ping(row: dict[str, Any]) -> bool:
    """A ping whose destination (last argv word) is a non-loopback management host."""
    argv = _command_args(row)
    return (len(argv) >= 2 and Path(argv[0]).name == "ping" and not argv[-1].startswith("-")
            and not _is_loopback_probe(row))


def _ping_no_reply(row: dict[str, Any]) -> bool:
    """iputils ping exits 1 only when it ran and got no reply; 2/127 mean it never ran."""
    return row["exit"] == 1


def _explicit_loopback_failure(row: dict[str, Any]) -> bool:
    if not _is_loopback_probe(row):
        return False
    if Path(_command_args(row)[0]).name == "ping":
        return _ping_no_reply(row)
    return _explicit_remote_failure(row)


def _wifi_connected(row: dict[str, Any]) -> bool:
    if row["exit"] != 0:
        return False
    text = row["stdout"]
    argv = _command_args(row)
    if _has_program(row, "iw") and len(argv) >= 4 and argv[1] == "dev" and argv[3] == "link":
        return bool(re.search(r"(?im)^Connected to [0-9a-f:]{17}$", text))
    if (_has_program(row, "nmcli") and len(argv) >= 4
            and argv[1:3] == ["device", "show"]
            and "GENERAL.STATE" in text):
        return bool(re.search(r"(?im)^GENERAL.STATE:\s*100 \(connected\)$", text))
    return False


def _link_details(row: dict[str, Any]) -> tuple[str, str, int] | None:
    argv = _command_args(row)
    if (row["exit"] != 0 or not _has_program(row, "iw") or len(argv) < 4
            or argv[1] != "dev" or argv[3] != "link"):
        return None
    bssid = re.search(r"(?im)^Connected to ([0-9a-f:]{17})$", row["stdout"])
    ssid = re.search(r"(?im)^SSID:\s*(.+)$", row["stdout"])
    frequency = re.search(r"(?im)^freq:\s*(\d+)$", row["stdout"])
    if bssid is None or ssid is None or frequency is None:
        return None
    return bssid.group(1).upper(), ssid.group(1).strip(), int(frequency.group(1))


def _iw_interface(row: dict[str, Any]) -> str | None:
    argv = _command_args(row)
    if (row["exit"] != 0 or not _has_program(row, "iw") or len(argv) < 4
            or argv[1] != "dev" or argv[3] != "link"):
        return None
    interface = argv[2]
    return interface if re.fullmatch(r"[A-Za-z0-9_.:-]{1,32}", interface) else None


def _adapter_interface(row: dict[str, Any]) -> str | None:
    argv = _command_args(row)
    if (row["exit"] != 0 or not _has_program(row, "ethtool") or len(argv) < 3
            or argv[1] != "-i"):
        return None
    interface = argv[2]
    return interface if re.fullmatch(r"[A-Za-z0-9_.:-]{1,32}", interface) else None


def _association_matches(rows: list[dict[str, Any]], link_index: int, prop: str, value: str,
                         expected_ssid: str) -> bool:
    details = _link_details(rows[link_index])
    if details is None or details[1] != expected_ssid:
        return False
    if prop.endswith("bssid"):
        return details[0] == value.upper()
    if prop.endswith("band"):
        return (value == "a" and details[2] >= 5000) or (value == "bg" and 2400 <= details[2] < 2500)
    return True


def _default_route(row: dict[str, Any], device: str | None = None) -> bool:
    argv = _command_args(row)
    if row["exit"] != 0 or not _has_program(row, "ip") or "route" not in argv[1:]:
        return False
    default = next((line for line in row["stdout"].splitlines() if line.startswith("default ")), "")
    if not default:
        return False
    return device is None or re.search(rf"\bdev\s+{re.escape(device)}\b", default) is not None


def _connection_snapshot(row: dict[str, Any]) -> dict[str, str]:
    argv = _command_args(row)
    if (row["exit"] != 0 or not _has_program(row, "nmcli") or len(argv) < 3
            or argv[1:3] != ["connection", "show"]):
        return {}
    found: dict[str, str] = {}
    for line in row["stdout"].splitlines():
        match = re.match(r"\s*(802-11-wireless\.(?:ssid|bssid|band|autoconnect-retries)):\s*(.*?)\s*$", line)
        if match:
            found[match.group(1)] = match.group(2)
    return found


def _modified_value(row: dict[str, Any], prop: str) -> str | None:
    argv = _command_args(row)
    if (row["exit"] != 0 or not _has_program(row, "nmcli") or len(argv) < 4
            or argv[1:3] != ["connection", "modify"]):
        return None
    try:
        return argv[argv.index(prop) + 1]
    except (ValueError, IndexError):
        return None


def _trial_window(rows: list[dict[str, Any]], change_index: int) -> tuple[int, int] | None:
    next_change = next((index for index in range(change_index + 1, len(rows))
                        if _has_program(rows[index], "nmcli")
                        and _command_args(rows[index])[1:3] == ["connection", "modify"]), len(rows))
    for index in range(change_index + 1, next_change):
        argv = _command_args(rows[index])
        if (_has_program(rows[index], "nmcli") and argv[1:3] == ["connection", "up"]
                and any(token in {"timeout", "--timeout"} for token in argv)):
            return next_change, index
    return None


def _trial_link(following: list[tuple[int, dict[str, Any]]]) -> tuple[int | None, str]:
    for index, row in following:
        if _wifi_connected(row):
            return index, "connected"
    for _index, row in following:
        argv = _command_args(row)
        is_probe = ((_has_program(row, "iw") and argv[1:2] == ["dev"])
                    or (_has_program(row, "nmcli") and "GENERAL.STATE" in row["stdout"]))
        if row["exit"] == 0 and is_probe and (
                "Not connected" in row["stdout"] or "disconnected" in row["stdout"].lower()):
            return None, "disconnected"
    return None, "missing"


def _trial_route_status(following: list[tuple[int, dict[str, Any]]], interface: str) -> str:
    if any(_default_route(row, interface) for _index, row in following):
        return "matched"
    captured_routes = [row for _index, row in following if row["exit"] == 0
                       and _has_program(row, "ip") and "route" in _command_args(row)[1:]]
    return "conflict" if any(_default_route(row) for row in captured_routes) else "missing"


def _trial_remote_index(following: list[tuple[int, dict[str, Any]]]) -> tuple[int | None, str]:
    remote = [(index, row) for index, row in following if _management_probe(row)]
    if not remote:
        return None, "missing"
    index = next((index for index, row in remote if row["exit"] == 0 and row["stdout"].strip()), None)
    if index is not None:
        return index, "recovered"
    if any(_explicit_remote_failure(row) for _index, row in remote):
        return None, "failed"
    return None, "missing"


def _explicit_remote_failure(row: dict[str, Any]) -> bool:
    if _management_ping(row):
        return _ping_no_reply(row)
    if row["exit"] == 0 or _ssh_target(row) is None:
        return False
    diagnostic = row["stdout"] + "\n" + row["stderr"]
    return bool(re.search(
        r"(?i)connection refused|connection timed out|no route to host|network is unreachable|"
        r"could not resolve hostname|name or service not known|connection reset by peer",
        diagnostic))


def _trial_timing_ok(rows: list[dict[str, Any]], started_index: int,
                     recovered_index: int) -> bool | None:
    started_value = rows[started_index].get("captured_at")
    recovered_value = rows[recovered_index].get("captured_at")
    if not isinstance(started_value, str) or not isinstance(recovered_value, str):
        return None
    try:
        started = datetime.fromisoformat(started_value.replace("Z", "+00:00"))
        recovered = datetime.fromisoformat(recovered_value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if started.tzinfo is None or recovered.tzinfo is None:
        return None
    return 0 <= (recovered - started).total_seconds() <= 60


def _recovered_trial(rows: list[dict[str, Any]], change_index: int, prop: str,
                     value: str, ssid: str) -> bool | None:
    window = _trial_window(rows, change_index)
    if window is None:
        return None
    next_change, timeout_index = window
    if rows[timeout_index]["exit"] != 0:
        diagnostic = rows[timeout_index]["stdout"] + "\n" + rows[timeout_index]["stderr"]
        return False if re.search(r"(?i)activation failed|connection activation failed", diagnostic) else None
    following = list(enumerate(rows[timeout_index + 1:next_change], timeout_index + 1))
    link_index, link_status = _trial_link(following)
    if link_index is None:
        return False if link_status == "disconnected" else None
    interface = _iw_interface(rows[link_index])
    if interface is None:
        return None
    route_status = _trial_route_status(following, interface)
    if route_status != "matched":
        return False if route_status == "conflict" else None
    remote_index, remote_status = _trial_remote_index(following)
    if remote_index is None:
        return False if remote_status == "failed" else None
    if _link_details(rows[link_index]) is None:
        return None
    if not _association_matches(rows, link_index, prop, value, ssid):
        return False
    return _trial_timing_ok(rows, timeout_index, remote_index)


def _observed_identity(rows: list[dict[str, Any]]) -> list[str] | None:
    dmi = next((row["stdout"] for row in rows if row["exit"] == 0 and _has_program(row, "dmidecode")), "")
    kernel = next((row["stdout"].strip() for row in rows if row["exit"] == 0 and _has_program(row, "uname")), "")
    driver = next((row["stdout"].strip() for row in rows if row["exit"] == 0 and _has_program(row, "modinfo")), "")
    nm_row = next((row["stdout"] for row in rows if _has_program(row, "nmcli")
                   and row["exit"] == 0
                   and ("--version" in _command_args(row) or "version" in row["stdout"].lower())), "")
    os_release = next((row["stdout"] for row in rows if row["exit"] == 0
                       and _has_program(row, "cat") and "/etc/os-release" in _command_args(row)), "")
    supplicant = next((row["stdout"] for row in rows if row["exit"] == 0
                       and _has_program(row, "wpa_supplicant") and "-v" in _command_args(row)), "")
    adapter_row = next((row for row in rows if row["exit"] == 0
                        and _has_program(row, "ethtool") and "-i" in _command_args(row)), None)
    adapter = adapter_row["stdout"] if adapter_row is not None else ""
    driver_version = re.search(r"(?im)^\s*version:\s*(.+)$", driver)
    nm_version = re.search(r"(?i)version\s+([0-9][0-9.]+)", nm_row)
    os_version = re.search(r'(?m)^PRETTY_NAME="?([^"\n]+)', os_release)
    wpa_version = re.search(r"(?i)wpa_supplicant v?([0-9][0-9.]+)", supplicant)
    firmware = re.search(r"(?im)^firmware-version:\s*(.+)$", adapter)
    product = re.findall(r"(?im)^\s*(?:Manufacturer|Product Name|BIOS Version):\s*(.+)$", dmi)
    adapter_interface = _adapter_interface(adapter_row) if adapter_row is not None else None
    observed_interfaces = {_iw_interface(row) for row in rows if _link_details(row) is not None}
    if (not adapter_interface or adapter_interface not in observed_interfaces
            or not kernel or driver_version is None or nm_version is None or os_version is None
            or wpa_version is None or firmware is None or len(product) != 3):
        return None
    if not re.search(r"(?im)^driver:\s*mt7925e\s*$", adapter):
        return None
    return [*(value.strip() for value in product), kernel, driver_version.group(1).strip(),
            nm_version.group(1), os_version.group(1).strip(), wpa_version.group(1), firmware.group(1).strip()]


def _vendor_cites_identity(sources: Any, identity: list[str]) -> bool:
    if not isinstance(sources, list) or not sources:
        return False
    for source in sources:
        if not isinstance(source, dict) or not isinstance(source.get("text"), str):
            continue
        text = source["text"]
        if hashlib.sha256(text.encode()).hexdigest() != source.get("sha256") or len(text) < 80:
            continue
        host = urlparse(source.get("url", "")).hostname
        if host in {"nvidia.com", "www.nvidia.com", "asus.com", "www.asus.com"} and all(value in text for value in identity):
            return True
    return False


def _source_applies(data: dict[str, Any], rows: list[dict[str, Any]]) -> bool:
    identity = _observed_identity(rows)
    return identity is not None and _vendor_cites_identity(data.get("vendor_sources"), identity)


def _check_incident(data: dict[str, Any], rows: list[dict[str, Any]], path: Path) -> dict[str, Any] | None:
    journal = [row for row in rows if row["exit"] == 0 and _has_program(row, "journalctl")]
    journal_text = "\n".join(row["stdout"] + row["stderr"] for row in journal)
    network_fault = bool(re.search(r"WRONG_KEY", journal_text, re.I)
                         and re.search(r"no-secrets", journal_text, re.I)
                         and re.search(r"wpa_supplicant|NetworkManager", journal_text, re.I))
    local_rows = [row for row in rows if _is_loopback_probe(row)]
    remote_rows = [row for row in rows if _management_probe(row) or _management_ping(row)]
    local_alive = any(_loopback_probe(row) for row in local_rows)
    local_failed = any(_explicit_loopback_failure(row) for row in local_rows)
    remote_failed = any(_explicit_remote_failure(row) for row in remote_rows)
    if not local_alive and local_failed and remote_failed:
        return _result("fail", "loopback and management probes both fail; this is host failure, not Wi-Fi isolation", [str(path)])
    if not journal or not local_rows or not remote_rows:
        return _result("unknown", "raw NetworkManager incident, successful local-host probe, or management endpoint probe missing", [str(path)])
    if not remote_failed:
        return _result("unknown", "management probe has no successful response or explicit native connection failure diagnostic", [str(path)])
    if not local_alive:
        # An explicit loopback failure already returned fail above; what remains never ran.
        return _result("unknown", "loopback probe did not run to a native reply or no-reply verdict", [str(path)])
    if not network_fault:
        return _result("fail", "raw output does not show WRONG_KEY/no-secrets with a responsive local host and failed remote path", [str(path)])
    if not _source_applies(data, rows):
        return _result("unknown", "exact OEM/BIOS/kernel/Wi-Fi driver and vendor applicability evidence missing", [str(path)])
    return None


def _verify_trials(rows: list[dict[str, Any]], path: Path) -> dict[str, Any]:
    files = [str(path)]
    initial = next((snapshot for row in rows if (snapshot := _connection_snapshot(row))), {})
    if not {"802-11-wireless.ssid", "802-11-wireless.bssid", "802-11-wireless.band",
            "802-11-wireless.autoconnect-retries"}.issubset(initial):
        return _result("unknown", "initial SSID, BSSID, band, and autoconnect-retry settings were not captured", files)
    required_properties = ("802-11-wireless.bssid", "802-11-wireless.band", "802-11-wireless.autoconnect-retries")
    candidate_changes: dict[str, list[tuple[int, str]]] = {prop: [] for prop in required_properties}
    rollback_changes = {prop: [] for prop in required_properties}
    for index, row in enumerate(rows):
        for prop in required_properties:
            value = _modified_value(row, prop)
            if value is None:
                continue
            original = initial[prop]
            is_original = value in {original, "\"\"", ""} or (prop.endswith("bssid") and original == "--" and value == "--")
            if is_original:
                rollback_changes[prop].append(index)
            else:
                candidate_changes[prop].append((index, value))
    if any(not indexes for indexes in candidate_changes.values()):
        return _result("unknown", "raw BSSID and band-steering candidate changes are not both recorded", files)
    ssid = initial["802-11-wireless.ssid"]
    for prop, trials in candidate_changes.items():
        outcomes = [_recovered_trial(rows, index, prop, value, ssid) for index, value in trials]
        error = _trial_verdict(outcomes, prop, path)
        if error is not None:
            return error
    final = next((snapshot for row in reversed(rows) if (snapshot := _connection_snapshot(row))), {})
    if (any(not indexes for indexes in rollback_changes.values()) or final != initial):
        return _result("unknown", "rollback command or readback of original BSSID/band policy missing", files)
    return _result("pass", "raw WPA failure is isolated from local-host health; bounded BSSID/band trials recovered route and rollback restored original settings", files)


def _trial_verdict(outcomes: list[bool | None], prop: str, path: Path) -> dict[str, Any] | None:
    if True in outcomes:
        return None
    if any(outcome is None for outcome in outcomes):
        return _result("unknown", f"bounded {prop} trial lacks successful route, association, remote-access, or timing probes", [str(path)])
    return _result("fail", f"bounded {prop} trial did not associate to the expected AP/band and restore route/access within 60 seconds", [str(path)])


def _verify_capture(data: dict[str, Any], rows: list[dict[str, Any]], path: Path) -> dict[str, Any]:
    incident_error = _check_incident(data, rows, path)
    if incident_error is not None:
        return incident_error
    return _verify_trials(rows, path)


def verify(evidence: str | Path | None = None) -> dict[str, Any]:
    """Require raw evidence for network-only outage, bounded A/B recovery, and rollback."""
    directory = Path(evidence) if evidence is not None else ROOT / "tasks/evidence" / FINDING
    path = directory / "commands.json"
    capture = _read_capture(path)
    if capture is None:
        return _result("unknown", "raw command capture missing or malformed; current snapshot cannot prove a roam sequence", [str(path)])
    data, rows = capture
    return _verify_capture(data, rows, path)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence", type=Path, default=None,
                        help="directory containing commands.json")
    args = parser.parse_args(argv)
    result = verify(args.evidence)
    print(json.dumps(result, sort_keys=True))
    if result.get("status") == "pass" and result.get("fail") == 0 and result.get("could_not_run") == 0:
        return 0
    if result.get("status") == "fail" and result.get("fail", 0) > 0 and result.get("could_not_run") == 0:
        return 1
    return 2


if __name__ == "__main__":
    sys.exit(main())
