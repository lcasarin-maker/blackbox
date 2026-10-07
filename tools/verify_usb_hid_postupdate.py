"""Evaluate USB-HID post-update loss from raw Linux command output."""
from __future__ import annotations

import argparse
import json
import re
import shlex
from pathlib import Path
import sys
from typing import Any

from tools.capture_io import read_regular_bytes, strict_json_loads
from tools.verify_wifi_isolation import _ssh_target

ROOT = Path(__file__).resolve().parents[1]
FINDING = "FEATURE-USB-HID-POSTUPDATE-CHECK"
MAX_CAPTURE_BYTES = 4_000_000


def _result(status: str, reason: str, files: list[str]) -> dict[str, Any]:
    return {"status": status, "reason": reason, "files": files,
            "fail": int(status == "fail"), "could_not_run": int(status == "unknown")}


def _read(path: Path) -> dict[str, Any] | None:
    try:
        raw = read_regular_bytes(path, MAX_CAPTURE_BYTES)
        if len(raw) > MAX_CAPTURE_BYTES:
            return None
        value = strict_json_loads(raw.decode("utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError, RecursionError):
        return None
    return value if isinstance(value, dict) else None


def _argv(row: dict[str, Any]) -> list[str]:
    try:
        return shlex.split(row["cmd"])
    except ValueError:
        return []


def _command_args(row: dict[str, Any]) -> list[str]:
    """Return the executed argv after recognized privilege wrappers."""
    argv = _argv(row)
    while argv and Path(argv[0]).name in {"sudo", "doas"}:
        argv = argv[1:]
        while argv and argv[0] in {"-n", "--non-interactive", "-E", "--preserve-env", "--"}:
            argv = argv[1:]
        if argv and argv[0] in {"-u", "--user", "-g", "--group"}:
            argv = argv[2:]
    return argv


def _has(row: dict[str, Any], *tokens: str) -> bool:
    argv = _command_args(row)
    return (bool(tokens) and bool(argv) and Path(argv[0]).name == tokens[0]
            and all(token in argv[1:] for token in tokens[1:]))


def _phase(row: dict[str, Any]) -> str | None:
    phase = row.get("capture_phase")
    return phase if phase in {"pre-update", "affected", "recovery"} else None


def _boot_ids(rows: list[dict[str, Any]]) -> dict[str, str] | None:
    found: dict[str, str] = {}
    for row in rows:
        phase = _phase(row)
        if phase is not None and _has(row, "cat", "/proc/sys/kernel/random/boot_id") and row["exit"] == 0:
            value = row["stdout"].strip()
            if not re.fullmatch(r"[0-9a-fA-F-]{36}", value):
                return None
            found[phase] = value
    if set(found) != {"pre-update", "affected", "recovery"} or len(set(found.values())) != 3:
        return None
    for row in rows:
        phase = _phase(row)
        if phase is not None and row.get("boot_id") != found.get(phase):
            return None
    return found


def _kernel(rows: list[dict[str, Any]], phase: str) -> str | None:
    row = next((r for r in rows if _phase(r) == phase and _has(r, "uname", "-r")), None)
    return row["stdout"].strip() if row and row["exit"] == 0 and row["stdout"].strip() else None


def _input_event(rows: list[dict[str, Any]], phase: str) -> bool:
    return any(_phase(row) == phase and _has(row, "evtest") and row["exit"] == 0
               and re.search(r"(?im)type\s+1\s+\(EV_KEY\).*code\s+\d+.*value\s+[12]", row["stdout"])
               for row in rows)


def _ssh_ok(rows: list[dict[str, Any]], phase: str) -> bool:
    return any(_phase(row) == phase and _ssh_target(row) is not None and row["exit"] == 0
               and row["stdout"].strip() for row in rows)


def _usb_tree(rows: list[dict[str, Any]], phase: str) -> str:
    row = next((r for r in rows if _phase(r) == phase and _has(r, "lsusb", "-t") and r["exit"] == 0), None)
    return row["stdout"] if row else ""


def _hid_drivers(tree: str) -> list[str]:
    """Driver bound to each HID-class interface in `lsusb -t`; unbound reads `[none]`."""
    return re.findall(r"(?i)Class=Human Interface Device,\s*Driver=([^,\s]*)", tree)


def _modules(rows: list[dict[str, Any]], phase: str) -> tuple[bool, bool] | None:
    row = next((r for r in rows if _phase(r) == phase and _has(r, "lsmod") and r["exit"] == 0), None)
    if row is None:
        return None
    names = {line.split()[0] for line in row["stdout"].splitlines()[1:] if line.split()}
    return "usbhid" in names, "hid_generic" in names


# Real Kconfig symbols for built-in USB HID (CONFIG_USB_HID_GENERIC does not exist).
HID_SYMBOLS = ("CONFIG_HID", "CONFIG_USB_HID", "CONFIG_HID_GENERIC")


def _integrated(rows: list[dict[str, Any]], phase: str) -> bool | None:
    """True/False only from the config of this phase's running kernel naming every symbol."""
    kernel = _kernel(rows, phase)
    if kernel is None:
        return None
    config = f"/boot/config-{kernel}"
    for row in rows:
        argv = _command_args(row)
        if (_phase(row) != phase or row["exit"] != 0 or not argv
                or Path(argv[0]).name not in {"cat", "grep"} or config not in argv[1:]):
            continue
        values = {}
        for symbol in HID_SYMBOLS:
            match = re.search(rf"(?m)^(?:{symbol}=([ym])|# {symbol} is not set)$", row["stdout"])
            if match:
                values[symbol] = match.group(1)
        if len(values) == len(HID_SYMBOLS):
            return all(value == "y" for value in values.values())
    return None


def _boot_observations(rows: list[dict[str, Any]], path: Path) -> tuple[tuple[str, str, str], str] | dict[str, Any]:
    dmi = next((r["stdout"] for r in rows if _has(r, "dmidecode", "-t", "system") and r["exit"] == 0), "")
    if not re.search(r"(?im)^\s*(?:Manufacturer|Product Name):\s*\S", dmi):
        return _result("unknown", "OEM and product identity are not captured", [str(path)])
    if _boot_ids(rows) is None:
        return _result("unknown", "distinct pre-update, affected, and recovery boot identifiers are missing", [str(path)])
    pre, affected, recovery = (_kernel(rows, phase) for phase in ("pre-update", "affected", "recovery"))
    if not pre or not affected:
        return _result("unknown", "pre-update and affected-boot kernel identities are incomplete", [str(path)])
    if pre == affected:
        return _result("fail", "pre-update and affected captures identify the same running kernel", [str(path)])
    if not _input_event(rows, "pre-update") or not _ssh_ok(rows, "pre-update"):
        return _result("unknown", "pre-update healthy keyboard and remote access control is missing", [str(path)])
    tree = _usb_tree(rows, "affected")
    if not tree:
        return _result("unknown", "affected boot USB topology is inaccessible", [str(path)])
    if not re.search(r"(?i)class\s*=\s*(?:human interface device|hid|03h)|\b(?:keyboard|mouse|hid)\b", tree):
        return _result("unknown", "affected boot has no identified HID device; headless system remains possible", [str(path)])
    return (pre, affected, recovery or ""), tree


def _affected_loss(rows: list[dict[str, Any]], path: Path) -> tuple[bool, str] | dict[str, Any]:
    module_state = _modules(rows, "affected")
    built_in = _integrated(rows, "affected")
    if module_state is None and built_in is None:
        return _result("unknown", "cannot distinguish built-in HID support from missing modules or inaccessible telemetry", [str(path)])
    dpkg = next((r for r in rows if _phase(r) == "affected" and _has(r, "dpkg", "--audit")), None)
    kernel_log = next((r for r in rows if _phase(r) == "affected" and _has(r, "journalctl", "-k")), None)
    if dpkg is None or kernel_log is None:
        return _result("unknown", "affected-boot package audit or kernel journal is missing", [str(path)])
    if dpkg["exit"] != 0 or kernel_log["exit"] != 0:
        return _result("unknown", "package or kernel-log telemetry failed; inaccessible evidence stays could-not-run", [str(path)])
    errors = dpkg["stdout"] + dpkg["stderr"] + kernel_log["stdout"] + kernel_log["stderr"]
    broken = bool(re.search(r"(?im)^The following packages have been unpacked but not yet configured:|^The following packages have unmet dependencies:|^dpkg: error", errors))
    broken |= bool(re.search(r"(?i)(usbhid|hid_generic|xhci).*(?:failed|error|unknown symbol|not found)|(?:failed|error|unknown symbol|not found).*(usbhid|hid_generic|xhci)", errors))
    supported = module_state == (True, True) or built_in is True
    tree = _usb_tree(rows, "affected")
    drivers = _hid_drivers(tree)
    if supported or _input_event(rows, "affected") or any(d != "[none]" for d in drivers):
        return _result("fail", "healthy HID evidence on affected boot means post-update loss was not reproduced", [str(path)])
    # Only an lsusb -t capture that shows NO unbound HID interface is ambiguous (it may just
    # mean the tree was captured too late, or the interface enumerated under a different
    # class). No lsusb -t row at all still falls through to the package/journal correlation
    # below, which is the only signal those cases have.
    if tree and "[none]" not in drivers:
        return _result("unknown", "affected boot did not capture an unbound HID-class interface", [str(path)])
    return broken, "" if broken else "correlated HID/module or package failure is absent"


def _check_recovery(rows: list[dict[str, Any]], path: Path, prior: str,
                    affected: str, recovery: str) -> dict[str, Any] | None:
    if not recovery:
        return _result("unknown", "working prior-kernel recovery boot and rollback evidence are missing", [str(path)])
    if recovery == affected:
        return _result("fail", "recovery boot did not switch to a distinct kernel", [str(path)])
    if recovery != prior:
        return _result("fail", "recovery did not return to the identified pre-update kernel", [str(path)])
    if not _input_event(rows, "recovery") or not _ssh_ok(rows, "recovery"):
        return _result("unknown", "rollback kernel did not prove local keyboard input and remote access", [str(path)])
    modules = _modules(rows, "recovery")
    builtin = _integrated(rows, "recovery")
    if modules == (True, True) or builtin is True:
        return None
    if modules is None or builtin is None:
        return _result("unknown", "recovery kernel HID support is unproven: modules absent or unread and built-in config unread", [str(path)])
    return _result("fail", "recovery kernel lacks loaded or built-in USB-HID support", [str(path)])


def _verify_rows(rows: list[dict[str, Any]], path: Path) -> dict[str, Any]:
    if not rows or any(not isinstance(row, dict) or not isinstance(row.get("cmd"), str)
                       or type(row.get("exit")) is not int or not isinstance(row.get("stdout"), str)
                       or not isinstance(row.get("stderr", ""), str) for row in rows):
        return _result("fail", "raw USB command capture has malformed rows", [str(path)])
    tree = next((row["stdout"] for row in rows if _has(row, "lsusb", "-t") and row["exit"] == 0), "")
    declared_phases = {_phase(row) for row in rows}
    # Binding is read on the interface itself: lsmod cannot see built-in usbhid.
    if (not {"pre-update", "affected", "recovery"}.issubset(declared_phases)
            and "Driver=xhci-hcd" in tree and "[none]" in _hid_drivers(tree)):
        return _result("fail", "attached HID-class interface has no bound driver while xHCI is live", [str(path)])
    observed = _boot_observations(rows, path)
    if isinstance(observed, dict):
        return observed
    (pre, affected, recovery), _tree = observed
    loss_result = _affected_loss(rows, path)
    if isinstance(loss_result, dict):
        return loss_result
    loss, reason = loss_result
    if not loss:
        return _result("unknown", reason, [str(path)])
    recovery_error = _check_recovery(rows, path, pre, affected, recovery)
    if recovery_error is not None:
        return recovery_error
    return _result("pass", f"identified {affected} post-update HID loss and recovered local keyboard plus SSH on prior kernel {recovery}", [str(path)])


def verify(evidence: str | Path | None = None) -> dict[str, Any]:
    """Require an observed affected boot, distinct recovery boot, usable HID and SSH."""
    directory = Path(evidence) if evidence is not None else ROOT / "tasks/evidence" / FINDING
    path = directory / "commands.json"
    data = _read(path)
    if data is None or data.get("id") != FINDING or not isinstance(data.get("commands"), list):
        return _result("unknown", "paired raw post-update USB command capture is missing", [str(path)])
    if len(data["commands"]) > 20_000:
        return _result("fail", "raw USB command capture exceeds the row safety limit", [str(path)])
    return _verify_rows(data["commands"], path)


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
