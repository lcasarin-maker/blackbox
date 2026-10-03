"""Observe kernel identity, pstore records, and active netconsole configuration."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from tools.host_diagnostics import could_not_run_count, module_state
from tools.recovery_profile import read


KERNEL_PATHS = {
    "release": "proc/sys/kernel/osrelease",
    "boot_id": "proc/sys/kernel/random/boot_id",
    "cmdline": "proc/cmdline",
    "panic": "proc/sys/kernel/panic",
    "panic_on_rcu_stall": "proc/sys/kernel/panic_on_rcu_stall",
}
NETCONSOLE_ATTRIBUTES = (
    "enabled", "extended", "release", "dev_name", "local_port", "remote_port",
    "local_ip", "remote_ip", "local_mac", "remote_mac", "transmit_errors",
)


def _optional_value(path: Path) -> dict[str, Any]:
    """Read a native config value, distinguishing absent from denied."""
    try:
        return {"status": "read", "value": path.read_text(encoding="utf-8").strip()}
    except FileNotFoundError:
        return {"status": "unavailable", "reason": "path absent"}
    except (OSError, UnicodeError) as exc:
        return {"status": "could_not_run", "error": f"{type(exc).__name__}: {exc}"}


def _entries(path: Path) -> tuple[list[Path], dict[str, Any]]:
    try:
        return sorted(path.iterdir()), {"status": "read"}
    except FileNotFoundError:
        return [], {"status": "unavailable", "reason": "path absent"}
    except (OSError, UnicodeError) as exc:
        return [], {"status": "could_not_run", "error": f"{type(exc).__name__}: {exc}"}


def _within(root: Path, path: Path) -> bool:
    """Reject symlink targets outside the captured filesystem root."""
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except (OSError, ValueError, RuntimeError):
        return False


def _safe_value(root: Path, path: Path) -> dict[str, Any]:
    if not _within(root, path):
        return {"status": "could_not_run", "error": "path escapes capture root"}
    return _optional_value(path)


def _safe_entries(root: Path, path: Path) -> tuple[list[Path], dict[str, Any]]:
    if not _within(root, path):
        return [], {"status": "could_not_run", "error": "path escapes capture root"}
    return _entries(path)


def _fingerprint(values: dict[str, str]) -> str:
    canonical = json.dumps(values, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _target(root: Path, path: Path) -> dict[str, Any]:
    attributes = {name: _safe_value(root, path / name) for name in NETCONSOLE_ATTRIBUTES}
    readable = {name: row["value"] for name, row in attributes.items()
                if row["status"] == "read"}
    return {
        "name": path.name,
        "status": ("could_not_run" if any(row["status"] == "could_not_run"
                                           for row in attributes.values()) else
                   "observed" if readable else "unknown"),
        "enabled": attributes["enabled"],
        "attribute_status": {name: row["status"] for name, row in attributes.items()},
        "readable_attribute_count": len(readable),
        "configuration_sha256": _fingerprint(readable) if readable else None,
    }


def _netconsole(root: Path, cmdline: dict[str, Any]) -> dict[str, Any]:
    module = module_state(root, "netconsole")
    command_line = cmdline.get("value") if cmdline.get("status") == "read" else None
    boot_parameter_present = (any(token == "netconsole" or token.startswith("netconsole=")
                                   for token in command_line.split())
                              if isinstance(command_line, str) else None)
    result: dict[str, Any] = {
        "module": module,
        "boot_parameter_present": boot_parameter_present,
        "static_parameter": {"status": "not_applicable"},
        "dynamic_targets_status": {"status": "not_applicable"},
        "targets": [],
        "receiver_receipt": "not observed",
    }
    if module.get("status") == "could_not_run":
        return result
    if module.get("status") not in ("loaded", "built_in"):
        return result

    static_value = _safe_value(root, root / "sys/module/netconsole/parameters/netconsole")
    if static_value["status"] == "read":
        value = static_value.pop("value")
        static_value["configuration_sha256"] = _fingerprint({"netconsole": value})
        static_value["configured"] = bool(value)
    result["static_parameter"] = static_value

    target_paths, listing = _safe_entries(root, root / "sys/kernel/config/netconsole")
    result["dynamic_targets_status"] = listing
    if listing["status"] == "read":
        for path in target_paths:
            if not _within(root, path):
                result["targets"].append({"name": path.name, "status": "could_not_run",
                                          "error": "target escapes capture root"})
            elif path.is_dir():
                result["targets"].append(_target(root, path))
    result["configured_target_count"] = len(result["targets"])
    return result


def capture(root: Path = Path("/")) -> dict[str, Any]:
    """Collect filesystem observations without configuring or probing delivery."""
    kernel = {
        name: (read(root / path) if _within(root, root / path) else
               {"status": "could_not_run", "error": "path escapes capture root"})
        for name, path in KERNEL_PATHS.items()
    }
    pstore_path = root / "sys/fs/pstore"
    files, listing = _safe_entries(root, pstore_path)
    records = []
    for file in files:
        if not _within(root, file):
            records.append({"file": file.name, "status": "could_not_run",
                            "error": "pstore entry escapes capture root"})
            continue
        observation = read(file)
        if observation["status"] == "read":
            content = observation.pop("value")
            observation["normalized_text_sha256"] = hashlib.sha256(content.encode()).hexdigest()
            observation["signals"] = [name for name in ("FPAC", "PSCI", "NMI", "SBSA", "DOE", "RCU")
                                       if name in content]
        records.append({"file": file.name, **observation})
    persistent = {"status": listing["status"],
                  "error": listing.get("error"), "records": records, "record_count": len(records)}
    netconsole = _netconsole(root, kernel["cmdline"])
    unavailable = could_not_run_count(kernel) + int(persistent["status"] == "could_not_run")
    unavailable += sum(row["status"] == "could_not_run" for row in persistent["records"])
    unavailable += could_not_run_count(netconsole)
    return {
        "status": "partial" if unavailable else "observed",
        "could_not_run": unavailable,
        "kernel": {name: value for name, value in kernel.items() if name != "cmdline"},
        "boot_parameter_netconsole": {
            "status": kernel["cmdline"]["status"],
            "present": netconsole["boot_parameter_present"],
        },
        "pstore": persistent,
        "netconsole": netconsole,
        "limitations": [
            "pstore reads are not size-bounded; symlink checks and reads are not atomic against path replacement",
            "an empty pstore does not prove that persistent capture or recovery works",
            "netconsole configuration does not prove packets reached a receiver",
            "no panic, reboot, module load, or receiver test was performed",
        ],
    }


def main() -> int:
    result = capture()
    print(json.dumps(result, indent=2, sort_keys=True))
    return 2 if result["could_not_run"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
