"""Collect bounded, read-only host diagnostics for desktop and device failures."""
from __future__ import annotations

import argparse
import ctypes as C
import ctypes.util
import json
import os
from pathlib import Path
import platform
import re
import subprocess
import sys
from typing import Any, Callable, Sequence, cast

TIMEOUT_S = 4.0
MAX_OUTPUT_CHARS = 16_384
MAX_CONTAINER_IMAGE_INSPECTIONS = 4
INTERFACE_RE = re.compile(r"^[A-Za-z0-9_.:-]{1,15}$")
CONTACT_EMAIL_RE = re.compile(r"<[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}>")
RUNNER = Callable[..., subprocess.CompletedProcess[str]]


def read_text(path: Path) -> dict[str, Any]:
    """Read one local status file and preserve absence and access failures."""
    try:
        value = path.read_text(encoding="utf-8").strip()
    except FileNotFoundError as exc:
        return {"status": "could_not_run", "error": f"{type(exc).__name__}: {exc}"}
    except PermissionError as exc:
        return {"status": "could_not_run", "error": f"{type(exc).__name__}: {exc}"}
    except OSError as exc:
        return {"status": "could_not_run", "error": f"{type(exc).__name__}: {exc}"}
    return {"status": "ok", "value": value}


def read_names(path: Path) -> dict[str, Any]:
    """List one sysfs directory without following device paths."""
    try:
        names = sorted(entry.name for entry in path.iterdir())
    except FileNotFoundError as exc:
        return {"status": "could_not_run", "error": f"{type(exc).__name__}: {exc}"}
    except PermissionError as exc:
        return {"status": "could_not_run", "error": f"{type(exc).__name__}: {exc}"}
    except OSError as exc:
        return {"status": "could_not_run", "error": f"{type(exc).__name__}: {exc}"}
    return {"status": "ok", "value": names}


def run_readonly(argv: list[str], runner: RUNNER = subprocess.run,
                 accepted_exit_codes: tuple[int, ...] = ()) -> dict[str, Any]:
    """Run a fixed argv command with a short timeout and no shell."""
    try:
        result = runner(argv, text=True, capture_output=True, timeout=TIMEOUT_S,
                        check=False, stdin=subprocess.DEVNULL)
    except FileNotFoundError as exc:
        return {"status": "could_not_run", "command": argv,
                "error": f"{type(exc).__name__}: {exc}"}
    except PermissionError as exc:
        return {"status": "could_not_run", "command": argv,
                "error": f"{type(exc).__name__}: {exc}"}
    except subprocess.TimeoutExpired as exc:
        return {"status": "could_not_run", "command": argv,
                "error": f"{type(exc).__name__}: {exc}"}
    except OSError as exc:
        return {"status": "could_not_run", "command": argv,
                "error": f"{type(exc).__name__}: {exc}"}

    stdout = result.stdout.strip()
    stderr = result.stderr.strip()
    stdout_safe, out_contacts = CONTACT_EMAIL_RE.subn("<redacted-contact>", stdout)
    stderr_safe, err_contacts = CONTACT_EMAIL_RE.subn("<redacted-contact>", stderr)
    status = "ok" if result.returncode == 0 else (
        "observed" if result.returncode in accepted_exit_codes else "could_not_run")
    return {"status": status, "command": argv, "returncode": result.returncode,
            "stdout": stdout_safe[:MAX_OUTPUT_CHARS],
            "stdout_truncated": len(stdout_safe) > MAX_OUTPUT_CHARS,
            "stderr": stderr_safe[:MAX_OUTPUT_CHARS] or None,
            "stderr_truncated": len(stderr_safe) > MAX_OUTPUT_CHARS,
            "contact_emails_redacted": out_contacts + err_contacts}


def mount_summary(root: Path) -> dict[str, Any]:
    """Report root and boot mount modes from mountinfo, without probing disks."""
    record = read_text(root / "proc/self/mountinfo")
    if record["status"] != "ok":
        return record
    mounts: list[dict[str, Any]] = []
    for line in record["value"].splitlines():
        fields = line.split()
        if len(fields) < 6:
            continue
        target = fields[4].replace("\\040", " ")
        if target not in ("/", "/boot", "/boot/efi"):
            continue
        mounts.append({"target": target, "options": fields[5],
                       "read_only": "ro" in fields[5].split(",")})
    if not mounts:
        return {"status": "could_not_run", "error": "no root/boot mount records found"}
    return {"status": "ok", "value": mounts}


def _interfaces(root: Path) -> dict[str, Any]:
    result = read_names(root / "sys/class/net")
    if result["status"] != "ok":
        return result
    names = [name for name in result["value"]
             if name != "lo" and INTERFACE_RE.fullmatch(name)]
    ethernet: list[str] = []
    excluded: dict[str, str] = {}
    errors: dict[str, str] = {}
    for name in names:
        base = root / "sys/class/net" / name
        _device, error = _link_name(base / "device")
        if error:
            errors[name] = error
        elif _device is None:
            excluded[name] = "no sysfs device link (virtual or non-device interface)"
        elif (base / "wireless").exists():
            excluded[name] = "wireless interface"
        else:
            ethernet.append(name)
    return {"status": "could_not_run" if errors else "ok",
            "ethernet": ethernet, "excluded": excluded,
            "errors": errors, "interfaces": names}


def _link_name(path: Path) -> tuple[str | None, str | None]:
    """Read a sysfs link's basename while preserving absent and denied states."""
    try:
        return path.readlink().name, None
    except FileNotFoundError:
        return None, None
    except OSError as exc:
        return None, f"{type(exc).__name__}: {exc}"


def _pci_ids(device_path: Path) -> tuple[str | None, str | None, str | None]:
    try:
        vendor = (device_path / "vendor").read_text(encoding="ascii").strip()
        device = (device_path / "device").read_text(encoding="ascii").strip()
    except (FileNotFoundError, PermissionError, OSError) as exc:
        return None, None, f"{type(exc).__name__}: {exc}"
    return vendor, device, None


def _sysfs_target(root: Path, path: Path) -> tuple[Path | None, str | None]:
    """Resolve one sysfs entry only when it stays inside the supplied root."""
    try:
        target = path.resolve(strict=True)
        target.relative_to(root.resolve())
    except (FileNotFoundError, PermissionError, OSError, RuntimeError, ValueError) as exc:
        return None, f"{type(exc).__name__}: {exc}"
    return target, None


def _device_attributes(root: Path, path: Path, names: Sequence[str]) -> dict[str, Any]:
    target, error = _sysfs_target(root, path)
    if error:
        return {"status": "could_not_run", "error": error}
    target = cast(Path, target)
    values: dict[str, Any] = {}
    for name in names:
        attribute, error = _sysfs_target(root, target / name)
        if error:
            values[name] = ({"status": "unknown", "reason": "sysfs attribute absent"}
                            if name == "serial" and error.startswith("FileNotFoundError:")
                            else {"status": "could_not_run", "error": error})
        else:
            attribute = cast(Path, attribute)
            values[name] = (read_optional_text(attribute) if name == "serial"
                            else read_text(attribute))
    return {"status": "could_not_run" if any(value["status"] == "could_not_run"
                                                 for value in values.values()) else "ok",
            **values}


def read_optional_text(path: Path) -> dict[str, Any]:
    """Read optional identity metadata, distinguishing absence from access failure."""
    result = read_text(path)
    if result.get("error", "").startswith("FileNotFoundError:"):
        return {"status": "unknown", "reason": "sysfs attribute absent"}
    return result


def usb_inventory(root: Path) -> dict[str, Any]:
    """Read USB identity/speed and correlate HID interfaces through sysfs ancestry."""
    entries = read_names(root / "sys/bus/usb/devices")
    if entries["status"] != "ok":
        return entries
    devices: dict[str, dict[str, Any]] = {}
    targets: dict[str, Path] = {}
    for name in entries["value"]:
        path = root / "sys/bus/usb/devices" / name
        target, error = _sysfs_target(root, path)
        if error:
            devices[name] = {"status": "could_not_run",
                             "error": error}
            continue
        target = cast(Path, target)
        targets[name] = target
        if ":" in name:
            continue
        attrs = _device_attributes(root, path, (
            "idVendor", "idProduct", "manufacturer", "product", "serial", "speed"))
        devices[name] = attrs
    hid_entries = read_names(root / "sys/bus/hid/devices")
    hid: dict[str, Any] = {}
    if hid_entries["status"] == "ok":
        for name in hid_entries["value"]:
            target, error = _sysfs_target(root, root / "sys/bus/hid/devices" / name)
            if error:
                hid[name] = {"status": "could_not_run",
                             "error": error,
                             "usb_device": None}
                continue
            target = cast(Path, target)
            ancestors = [(usb_name, usb_path) for usb_name, usb_path in targets.items()
                         if ":" not in usb_name and usb_path in target.parents]
            matched = max(ancestors, key=lambda item: len(item[1].parts))[0] if ancestors else None
            hid[name] = {"status": "ok" if matched else "unmatched",
                         "usb_device": matched}
    return {"status": "could_not_run" if entries["status"] != "ok" or
            hid_entries["status"] != "ok" or any(v.get("status") == "could_not_run"
                                                   for v in devices.values()) or
            any(v.get("status") == "could_not_run" for v in hid.values()) else "ok",
            "devices": devices, "hid_devices": hid,
            "hid_inventory_status": hid_entries["status"]}


def watchdog_inventory(root: Path) -> dict[str, Any]:
    """Read watchdog sysfs metadata; never open a watchdog device node."""
    entries = read_names(root / "sys/class/watchdog")
    if entries["status"] != "ok":
        return {**entries, "owner": "UNKNOWN"}
    devices = {name: _device_attributes(root, root / "sys/class/watchdog" / name,
                                        ("identity", "state", "timeout", "nowayout"))
               for name in entries["value"]}
    return {"status": "could_not_run" if any(v["status"] == "could_not_run"
                                               for v in devices.values()) else "ok",
            "owner": "UNKNOWN", "devices": devices}


def pci_binding(root: Path, interface: str) -> dict[str, Any]:
    """Read a network interface's PCI IDs and bound driver/module via sysfs."""
    if not INTERFACE_RE.fullmatch(interface):
        return {"status": "could_not_run", "error": "invalid interface name"}
    device_path = root / "sys/class/net" / interface / "device"
    device_link, error = _link_name(device_path)
    if error:
        return {"status": "could_not_run", "error": error}
    if device_link is None:
        return {"status": "not_pci", "pci_vendor": None, "pci_device": None,
                "pci_address": None, "driver": None, "module": None,
                "module_version": None}
    vendor, device, error = _pci_ids(device_path)
    if error:
        return {"status": "could_not_run", "error": error}
    driver, error = _link_name(device_path / "driver")
    if error:
        return {"status": "could_not_run", "error": error}
    if driver is None:
        return {"status": "unbound", "pci_vendor": vendor, "pci_device": device,
                "pci_address": device_link,
                "driver": None, "module": None, "module_version": None}
    module, error = _link_name(device_path / "driver/module")
    if error:
        return {"status": "could_not_run", "error": error}
    if module is None:
        module = driver
    version = read_text(root / "sys/module" / module / "version")
    return {"status": "bound", "pci_vendor": vendor, "pci_device": device,
            "pci_address": device_link,
            "driver": driver, "module": module,
            "module_version": version,
            "module_version_status": version["status"]}


def _module_loaded(path: Path) -> tuple[bool | None, str | None]:
    """Return loaded state without treating permission errors as absence."""
    try:
        path.stat()
        return True, None
    except FileNotFoundError:
        return False, None
    except OSError as exc:
        return None, f"{type(exc).__name__}: {exc}"


def module_state(root: Path, name: str) -> dict[str, Any]:
    """Distinguish loaded, built-in, absent, and inaccessible kernel modules."""
    if not re.fullmatch(r"[A-Za-z0-9_-]+", name):
        return {"status": "could_not_run", "error": "invalid module name"}
    loaded_state, loaded_error = _module_loaded(root / "sys/module" / name.replace("-", "_"))
    if loaded_state is None:
        return {"status": "could_not_run", "error": loaded_error}
    release = read_text(root / "proc/sys/kernel/osrelease")
    if release["status"] != "ok":
        if loaded_state:
            return {"status": "loaded", "loaded": True, "built_in": None,
                    "built_in_status": "could_not_run", "error": release.get("error")}
        return {"status": "could_not_run", "error": release.get("error")}
    builtin = read_text(root / "lib/modules" / release["value"] / "modules.builtin")
    if builtin["status"] != "ok":
        if loaded_state:
            return {"status": "loaded", "loaded": True, "built_in": None,
                    "built_in_status": "could_not_run", "error": builtin.get("error")}
        return {"status": "could_not_run", "error": builtin.get("error")}
    module_paths = {name + ".ko", name.replace("-", "_") + ".ko"}
    is_builtin = any(Path(line).name in module_paths for line in builtin["value"].splitlines())
    if is_builtin:
        status = "built_in"
    elif loaded_state:
        status = "loaded"
    else:
        status = "absent"
    return {"status": status, "loaded": bool(loaded_state) or is_builtin,
            "built_in": is_builtin}


def could_not_run_count(value: Any) -> int:
    """Count unavailable leaf checks so partial reports cannot look clean."""
    if isinstance(value, dict):
        own = int(value.get("status") == "could_not_run")
        return own + sum(could_not_run_count(child) for child in value.values())
    if isinstance(value, list):
        return sum(could_not_run_count(child) for child in value)
    return 0


def gpu_runtime_capture(runner: RUNNER = subprocess.run) -> dict[str, Any]:
    """Capture host and running-container runtime identities read-only."""
    containers = run_readonly(
        ["docker", "ps", "--no-trunc", "--format", "{{.ID}} {{.Image}}"], runner)
    image_ids = running_container_image_ids(containers, runner)
    return {
        "nvidia_smi_banner": run_readonly(["nvidia-smi"], runner),
        "nvidia_gpu_state": run_readonly([
            "nvidia-smi", "--query-gpu=name,driver_version,pci.bus_id,utilization.gpu,power.draw",
            "--format=csv,noheader",
        ], runner),
        "cuda_runtime": cuda_runtime_version_capture(),
        "container_runtime_version": run_readonly(
            ["docker", "version", "--format", "{{.Server.Version}}"], runner),
        "running_container_image_tags": containers,
        "running_container_image_ids": image_ids,
    }


def running_container_image_ids(containers: dict[str, Any], runner: RUNNER) -> dict[str, Any]:
    """Inspect up to four vLLM candidates' image IDs; never read container config or environment."""
    if containers["status"] != "ok":
        return {"status": "partial", "source_key": "running_container_image_tags"}
    rows = containers["stdout"].splitlines()
    parsed: list[tuple[str, str]] = []
    for row in rows:
        fields = row.split(maxsplit=1)
        if len(fields) != 2 or not re.fullmatch(r"[0-9a-f]{64}", fields[0]):
            return {"status": "partial", "containers": [
                {"status": "could_not_run", "reason": "malformed container image list"}]}
        parsed.append((fields[0], fields[1]))
    candidates = [(container_id, image_ref) for container_id, image_ref in parsed
                  if "vllm" in image_ref.casefold()]
    observed = []
    for container_id, image_ref in candidates[:MAX_CONTAINER_IMAGE_INSPECTIONS]:
        image = run_readonly(["docker", "inspect", "--format", "{{.Image}}", container_id], runner)
        value = image.get("stdout")
        if image["status"] != "ok" or not isinstance(value, str) or not re.fullmatch(
                r"sha256:[0-9a-f]{64}", value):
            observed.append({"status": "could_not_run", "container_id": container_id,
                             "image_ref": image_ref, "inspect_status": image["status"]})
        else:
            observed.append({"status": "ok", "container_id": container_id,
                             "image_ref": image_ref, "image_id": value})
    if len(candidates) > MAX_CONTAINER_IMAGE_INSPECTIONS:
        observed.append({"status": "could_not_run", "reason": "inspection limit exceeded",
                         "container_count": len(candidates),
                         "uninspected_container_count": len(candidates) - MAX_CONTAINER_IMAGE_INSPECTIONS})
    return {"status": "partial" if any(item["status"] == "could_not_run" for item in observed)
            else "ok", "candidate_count": len(candidates), "containers": observed}


def cuda_runtime_version_capture() -> dict[str, Any]:
    """Read CUDA Runtime API version without initializing a device or allocating memory."""
    library_name = ctypes.util.find_library("cudart")
    if not library_name:
        return {"status": "could_not_run", "error": "libcudart unavailable"}
    try:
        library = C.CDLL(library_name)
        get_version = library.cudaRuntimeGetVersion
    except (OSError, AttributeError) as exc:
        return {"status": "could_not_run", "library": library_name,
                "error": f"{type(exc).__name__}: {exc}"}
    get_version.argtypes = [C.POINTER(C.c_int)]
    get_version.restype = C.c_int
    value = C.c_int()
    result = get_version(C.byref(value))
    if result != 0 or value.value <= 0:
        return {"status": "could_not_run", "library": library_name,
                "returncode": result, "runtime_version": value.value}
    return {"status": "ok", "library": library_name, "runtime_version": value.value,
            "major": value.value // 1000, "minor": (value.value % 1000) // 10}


def capture(root: Path = Path("/"), runner: RUNNER = subprocess.run) -> dict[str, Any]:
    """Capture local status only; do not change services, links, modules, or disks."""
    interfaces = _interfaces(root)
    ethernet_interfaces = interfaces.get("ethernet", [])
    checks: dict[str, Any] = {
        "desktop": {
            "sessions": run_readonly(["loginctl", "list-sessions", "--no-pager", "--no-legend"], runner),
            "display_manager": run_readonly(["systemctl", "is-active", "display-manager.service"], runner,
                                             (3, 4)),
            "gdm": run_readonly(["systemctl", "is-active", "gdm.service"], runner, (3, 4)),
            "ssh": run_readonly(["systemctl", "is-active", "ssh.service"], runner, (3, 4)),
            "default_target": run_readonly(["systemctl", "get-default"], runner),
        },
        "storage": {
            "root_mounts": mount_summary(root),
            "block_devices": run_readonly(
                ["lsblk", "--json", "--output", "NAME,TYPE,RO,MODEL,MOUNTPOINT"], runner),
            "nvme_inventory": run_readonly(["nvme", "list", "--output-format=json"], runner),
        },
        "gpu_runtime": gpu_runtime_capture(runner),
        "network": {
            "nm_devices": run_readonly(
                ["nmcli", "--terse", "--fields", "DEVICE,TYPE,STATE", "device", "status"], runner),
            "links": run_readonly(["ip", "-brief", "link"], runner),
            "default_routes": run_readonly(["ip", "route", "show", "default"], runner),
            "wireless_interfaces": run_readonly(["iw", "dev"], runner),
            "interface_inventory": interfaces,
            "pci_bindings": {name: pci_binding(root, name)
                             for name in interfaces.get("interfaces", [])},
            "eee": {name: run_readonly(["ethtool", "--show-eee", name], runner)
                    for name in ethernet_interfaces},
        },
        "usb": {
            "hid_devices": read_names(root / "sys/bus/hid/devices"),
            "usb_devices": read_names(root / "sys/bus/usb/devices"),
            "inventory": usb_inventory(root),
            "usbhid_module": module_state(root, "usbhid"),
            "hid_generic_module": module_state(root, "hid_generic"),
            "xhci_hcd_module": module_state(root, "xhci_hcd"),
            "usb_tree": run_readonly(["lsusb", "-t"], runner),
        },
        "watchdog": watchdog_inventory(root),
        "kernel_signals": run_readonly([
            "journalctl", "--no-pager", "--boot", "--dmesg", "--lines=500",
            "--grep=HC died|uvcvideo|xhci|nvme|read-only|I/O error|usbhid|no-secrets|WRONG_KEY|r8127",
        ], runner),
    }
    unavailable = could_not_run_count(checks)
    return {
        "schema": 1,
        "report_status": "partial" if unavailable else "complete",
        "status": "partial" if unavailable else "complete",
        "could_not_run": unavailable,
        "identity": {"kernel_release": platform.uname().release,
                     "architecture": platform.machine(),
                     "page_size_bytes": os.sysconf("SC_PAGE_SIZE")},
        "safety": {"mode": "read_only", "shell": False,
                   "services_changed": False, "network_changed": False,
                   "modules_changed": False, "block_device_written": False},
        "checks": checks,
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path("/"),
                        help="filesystem root for fixture-based checks")
    args = parser.parse_args(argv)
    report = capture(args.root)
    sys.stdout.write(json.dumps(report, indent=2, sort_keys=True) + "\n")
    return 2 if report["could_not_run"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
