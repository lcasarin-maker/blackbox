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

from tools import capture_io

TIMEOUT_S = 4.0
MAX_OUTPUT_CHARS = 16_384
MAX_CONTAINER_IMAGE_INSPECTIONS = 4
MAX_PCI_DEVICE_INSPECTIONS = 256
MAX_NETWORK_INTERFACE_INSPECTIONS = 256
MAX_SYSFS_TEXT_BYTES = 65_536
INTERFACE_RE = re.compile(r"^[A-Za-z0-9_.:-]{1,15}$")
PCI_ADDRESS_RE = re.compile(r"^(?:[0-9a-f]{4}:)?[0-9a-f]{2}:[0-9a-f]{2}\.[0-7]$")
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


def _backup_mountpoint_state(root: Path, mountpoint: str) -> dict[str, str]:
    target = Path(mountpoint)
    if not target.is_absolute() or ".." in target.parts:
        return {"status": "unknown", "reason": "mountpoint must be an absolute normalized path"}
    rooted_target = root / target.relative_to("/")
    try:
        resolved_root = root.resolve(strict=True)
        resolved_target = rooted_target.resolve(strict=True)
        resolved_target.relative_to(resolved_root)
        if not resolved_target.is_dir():
            return {"status": "block", "reason": "mountpoint directory absent"}
    except FileNotFoundError:
        return {"status": "block", "reason": "mountpoint directory absent"}
    except (OSError, RuntimeError, ValueError) as exc:
        return {"status": "unknown", "reason": f"mountpoint inspection failed: {type(exc).__name__}: {exc}"}
    return {"status": "ok"}


def _findmnt_identity(query: dict[str, Any]) -> dict[str, Any]:
    if query["status"] != "ok":
        if query.get("returncode") == 1 and not query.get("stderr"):
            return {"status": "block", "reason": "exact mountpoint is not mounted",
                    "query": query}
        return {"status": "unknown", "reason": "findmnt could not inspect mount identity",
                "query": query}
    try:
        filesystems = json.loads(query["stdout"])["filesystems"]
    except (json.JSONDecodeError, KeyError, TypeError) as exc:
        return {"status": "unknown", "reason": f"invalid findmnt JSON: {type(exc).__name__}: {exc}"}
    if not isinstance(filesystems, list) or not filesystems:
        return {"status": "block", "reason": "exact mountpoint has no mounted filesystem"}
    if len(filesystems) != 1 or not isinstance(filesystems[0], dict):
        return {"status": "unknown", "reason": "findmnt returned ambiguous mount identity"}
    observed = {"target": filesystems[0].get("target"),
                "source": filesystems[0].get("source"), "uuid": filesystems[0].get("uuid")}
    if not all(isinstance(value, str) and value for value in observed.values()):
        return {"status": "unknown", "reason": "findmnt identity fields absent or unreadable",
                "observed": observed}
    return {"status": "ok", "observed": observed}


def backup_destination_check(root: Path, mountpoint: str | None,
                             expected_source: str | None, expected_uuid: str | None,
                             runner: RUNNER | None = None) -> dict[str, Any]:
    """Require an exact mounted destination and caller-supplied device identity."""
    if not all(isinstance(value, str) and value.strip() for value in
               (mountpoint, expected_source, expected_uuid)):
        return {"status": "unknown", "reason": "explicit mountpoint, source, and UUID required"}
    mountpoint = cast(str, mountpoint)
    expected_source = cast(str, expected_source)
    expected_uuid = cast(str, expected_uuid)
    selected_runner = runner or subprocess.run
    if root != Path("/") and selected_runner is subprocess.run:
        return {"status": "unknown",
                "reason": "fixture roots require an injected findmnt runner"}
    mount_state = _backup_mountpoint_state(root, mountpoint)
    if mount_state["status"] != "ok":
        return mount_state
    query = run_readonly(["findmnt", "--json", "--mountpoint", mountpoint,
                          "--output", "TARGET,SOURCE,UUID"], selected_runner)
    identity = _findmnt_identity(query)
    if identity["status"] != "ok":
        return identity
    observed = identity["observed"]
    expected = {"target": mountpoint, "source": expected_source, "uuid": expected_uuid}
    mismatches = [key for key, value in expected.items() if observed[key] != value]
    return {"status": "block" if mismatches else "pass", "expected": expected,
            "observed": identity, "mismatches": mismatches}


def boot_state_inventory(root: Path, kernel_release: str | None = None) -> dict[str, Any]:
    """Record current kernel/DRM/initrd observations without asserting bootability."""
    release_record = ({"status": "ok", "value": kernel_release, "source": "explicit input"}
                      if kernel_release is not None else
                      _sysfs_text(root, root / "proc/sys/kernel/osrelease"))
    if kernel_release is None and release_record["status"] == "ok":
        release_record["source"] = "proc/sys/kernel/osrelease"
    if release_record["status"] != "ok":
        return {"status": "could_not_run", "running_kernel_release": release_record,
                "bootability": "not_verified"}
    release = release_record["value"]
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._+-]{0,127}", release) or ".." in release:
        return {"status": "could_not_run", "running_kernel_release": release_record,
                "reason": "invalid kernel release token",
                "bootability": "not_verified"}
    modeset = _sysfs_text(root, root / "sys/module/nvidia_drm/parameters/modeset",
                          optional=True)
    command_line = _sysfs_text(root, root / "proc/cmdline")
    overrides: dict[str, Any] = {"status": command_line["status"]}
    if command_line["status"] == "ok":
        observed: list[str] = []
        for token in command_line["value"].split():
            key, separator, value = token.partition("=")
            if key in ("nvidia-drm.modeset", "nvidia_drm.modeset") and separator:
                allowed = {"0", "1", "Y", "N", "y", "n", "true", "false", "on", "off"}
                observed.append(value if value in allowed else "unknown")
        overrides.update({"observed_modeset_overrides": observed})
    else:
        overrides["error"] = command_line.get("error")
    artifacts: dict[str, Any] = {}
    for name in (f"vmlinuz-{release}", f"initrd.img-{release}"):
        path = root / "boot" / name
        try:
            resolved_root = root.resolve(strict=True)
            resolved_path = path.resolve(strict=True)
            resolved_path.relative_to(resolved_root)
            resolved_path.stat()
            artifacts[name] = {"status": "observed", "present": resolved_path.is_file()}
        except FileNotFoundError:
            artifacts[name] = {"status": "observed", "present": False}
        except (OSError, RuntimeError, ValueError) as exc:
            artifacts[name] = {"status": "could_not_run",
                               "error": f"{type(exc).__name__}: {exc}"}
    release_record["status"] = "observed"
    return {"running_kernel_release": release_record, "drm_command_line_overrides": overrides,
            "nvidia_drm_modeset_effective": modeset,
            "current_kernel_artifact_presence_only": artifacts,
            "bootability": "not_verified"}


def _interfaces(root: Path) -> dict[str, Any]:
    path, error = _sysfs_target(root, root / "sys/class/net")
    if error:
        return {"status": "could_not_run", "error": error}
    try:
        with os.scandir(cast(Path, path)) as entries:
            names = []
            for entry in entries:
                names.append(entry.name)
                if len(names) > MAX_NETWORK_INTERFACE_INSPECTIONS:
                    break
    except OSError as exc:
        return {"status": "could_not_run", "error": f"{type(exc).__name__}: {exc}"}
    truncated = len(names) > MAX_NETWORK_INTERFACE_INSPECTIONS
    names = sorted(names[:MAX_NETWORK_INTERFACE_INSPECTIONS])
    names = [name for name in names
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
    result = {"status": "could_not_run" if errors or truncated else "ok",
              "ethernet": ethernet, "excluded": excluded,
              "errors": errors, "interfaces": names}
    if truncated:
        result.update({"truncated": True,
                       "inspected_count": len(names)})
    return result


def _link_name(path: Path) -> tuple[str | None, str | None]:
    """Read a sysfs link's basename while preserving absent and denied states."""
    try:
        return path.readlink().name, None
    except FileNotFoundError:
        return None, None
    except OSError as exc:
        return None, f"{type(exc).__name__}: {exc}"


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
            values[name] = _bounded_sysfs_text(attribute)
            if name == "serial" and values[name].get("error", "").startswith(
                    "FileNotFoundError:"):
                values[name] = {"status": "unknown", "reason": "sysfs attribute absent"}
    return {"status": "could_not_run" if any(value["status"] == "could_not_run"
                                                 for value in values.values()) else "ok",
            **values}


def read_optional_text(path: Path) -> dict[str, Any]:
    """Read optional identity metadata, distinguishing absence from access failure."""
    result = read_text(path)
    if result.get("error", "").startswith("FileNotFoundError:"):
        return {"status": "unknown", "reason": "sysfs attribute absent"}
    return result


def _sysfs_text(root: Path, path: Path, *, optional: bool = False) -> dict[str, Any]:
    target, error = _sysfs_target(root, path)
    if error:
        if optional and error.startswith("FileNotFoundError:"):
            return {"status": "unknown", "reason": "sysfs attribute absent"}
        return {"status": "could_not_run", "error": error}
    result = _bounded_sysfs_text(cast(Path, target))
    if optional and result.get("error", "").startswith("FileNotFoundError:"):
        return {"status": "unknown", "reason": "sysfs attribute absent"}
    return result


def _bounded_sysfs_text(path: Path) -> dict[str, Any]:
    """Read a resolved, root-confined sysfs/proc file with a strict byte ceiling."""
    try:
        raw = capture_io.read_regular_bytes(path, MAX_SYSFS_TEXT_BYTES)
        if len(raw) > MAX_SYSFS_TEXT_BYTES:
            return {"status": "could_not_run", "error": "sysfs text exceeds byte limit",
                    "truncated": True}
        return {"status": "ok", "value": raw.decode("utf-8").strip()}
    except (OSError, UnicodeError, RecursionError) as exc:
        return {"status": "could_not_run", "error": f"{type(exc).__name__}: {exc}"}


def ip_link_inventory(runner: RUNNER = subprocess.run) -> dict[str, Any]:
    """Capture selected interface state from native ip JSON output."""
    query = run_readonly(["ip", "-j", "link", "show"], runner)
    if query["status"] != "ok":
        return query
    try:
        records = json.loads(query["stdout"])
    except (json.JSONDecodeError, TypeError) as exc:
        return {"status": "could_not_run", "command": query["command"],
                "error": f"{type(exc).__name__}: {exc}"}
    if not isinstance(records, list):
        return {"status": "could_not_run", "command": query["command"],
                "error": "ip JSON root is not a list"}
    links: dict[str, dict[str, Any]] = {}
    errors: dict[str, str] = {}
    for index, record in enumerate(records):
        if not isinstance(record, dict):
            errors[str(index)] = "link entry is not an object"
            continue
        name = record.get("ifname")
        if not isinstance(name, str) or not INTERFACE_RE.fullmatch(name) or name in links:
            errors[str(index)] = "missing, invalid, or duplicate interface name"
            continue
        fields = {key: ({"status": "ok", "value": record[key]} if key in record else
                        {"status": "unknown", "reason": "field absent from ip JSON"})
                  for key in ("ifindex", "mtu", "operstate", "link_type")}
        links[name] = {"status": "partial" if any(value["status"] == "unknown"
                                                       for value in fields.values()) else "ok",
                       **fields}
    return {"status": "could_not_run" if errors else "ok",
            "command": query["command"], "links": links, "errors": errors}


def _infiniband_port(root: Path, path: Path) -> dict[str, Any]:
    port_path, error = _sysfs_target(root, path)
    if error:
        return {"status": "could_not_run", "error": error, "gids": {}}
    port_path = cast(Path, port_path)
    gids_path, error = _sysfs_target(root, port_path / "gids")
    gids = ({"status": "could_not_run", "error": error} if error else
            read_names(cast(Path, gids_path)))
    gid_records: dict[str, Any] = {}
    if gids["status"] == "ok":
        for index in gids["value"]:
            if not re.fullmatch(r"[0-9]+", index):
                gid_records[index] = {"status": "could_not_run", "error": "invalid GID index"}
                continue
            values = {
                "gid": _sysfs_text(root, port_path / "gids" / index),
                "type": _sysfs_text(root, port_path / "gid_attrs/types" / index),
                "netdev": _sysfs_text(root, port_path / "gid_attrs/ndevs" / index),
            }
            netdev = values["netdev"].get("value")
            if values["netdev"]["status"] == "ok" and isinstance(netdev, str):
                values["pci_binding"] = pci_binding(root, netdev)
            gid_records[index] = {"status": "could_not_run" if any(
                value["status"] == "could_not_run" for value in values.values()
                if isinstance(value, dict) and "status" in value) else "ok", **values}
    link_layer = _sysfs_text(root, port_path / "link_layer")
    state = _sysfs_text(root, port_path / "state")
    return {"status": "could_not_run" if gids["status"] != "ok" or
            link_layer["status"] == "could_not_run" or
            state["status"] == "could_not_run" or any(
                gid["status"] == "could_not_run" for gid in gid_records.values()) else "ok",
            "gids": gid_records, "link_layer": link_layer, "state": state}


def _infiniband_device(root: Path, name: str) -> dict[str, Any]:
    base = root / "sys/class/infiniband" / name
    base, error = _sysfs_target(root, base)
    if error:
        return {"status": "could_not_run", "error": error}
    base = cast(Path, base)
    pci_target, error = _sysfs_target(root, base / "device")
    pci: dict[str, Any] = {"status": "unknown", "pci_address": None}
    if error:
        pci = {"status": "could_not_run", "error": error}
    else:
        pci_target = cast(Path, pci_target)
        pci_address = pci_target.name
        ids = _device_attributes(root, root / "sys/bus/pci/devices" / pci_address,
                                 ("vendor", "device"))
        pci = {"status": ids["status"], "pci_address": pci_address,
               "pci_vendor": ids.get("vendor"), "pci_device": ids.get("device")}
    ports_path, error = _sysfs_target(root, base / "ports")
    port_names = ({"status": "could_not_run", "error": error} if error else
                  read_names(cast(Path, ports_path)))
    ports: dict[str, Any] = {}
    if port_names["status"] == "ok":
        for port in port_names["value"]:
            ports[port] = (_infiniband_port(root, base / "ports" / port)
                           if re.fullmatch(r"[0-9]+", port) else
                           {"status": "could_not_run", "error": "invalid port name"})
    fields = {"firmware_version": _sysfs_text(root, base / "fw_ver", optional=True),
              "node_guid": _sysfs_text(root, base / "node_guid", optional=True),
              "system_image_guid": _sysfs_text(root, base / "sys_image_guid", optional=True)}
    return {"status": "could_not_run" if pci["status"] == "could_not_run" or
            port_names["status"] != "ok" or
            any(port["status"] == "could_not_run" for port in ports.values()) or
            any(field["status"] == "could_not_run" for field in fields.values()) else "ok",
            "pci": pci, **fields, "ports": ports}


def infiniband_inventory(root: Path) -> dict[str, Any]:
    """Read available RDMA GID, netdev, PCI, and firmware sysfs metadata."""
    directory, error = _sysfs_target(root, root / "sys/class/infiniband")
    if error:
        return {"status": "could_not_run", "error": error, "devices": {}}
    devices = read_names(cast(Path, directory))
    if devices["status"] != "ok":
        return {**devices, "devices": {}}
    result = {name: _infiniband_device(root, name) for name in devices["value"]}
    return {"status": "could_not_run" if any(item["status"] == "could_not_run"
                                               for item in result.values()) else "ok",
            "devices": result}


def network_inventory(root: Path, runner: RUNNER = subprocess.run) -> dict[str, Any]:
    """Join native link records with sysfs identity and optional RDMA metadata."""
    interfaces = _interfaces(root)
    links = ip_link_inventory(runner)
    link_records = links.get("links", {})
    unmatched = [name for name in interfaces.get("interfaces", []) if name not in link_records]
    profiles: dict[str, Any] = {}
    for name in interfaces.get("interfaces", []):
        base = root / "sys/class/net" / name
        profiles[name] = {
            "ip_link": link_records.get(name, {"status": "unknown",
                                                 "reason": "interface absent from ip JSON"}),
            "mtu_sysfs": _sysfs_text(root, base / "mtu"),
            "carrier": _sysfs_text(root, base / "carrier"),
            "operstate": _sysfs_text(root, base / "operstate"),
            "pci_binding": pci_binding(root, name),
            "firmware_version": {"status": "unknown",
                                  "reason": "no generic interface sysfs firmware field"},
        }
        profile = profiles[name]
        profile["status"] = "could_not_run" if any(
            profile[key]["status"] == "could_not_run"
            for key in ("mtu_sysfs", "carrier", "operstate", "pci_binding")) else "ok"
    infiniband = infiniband_inventory(root)
    return {"status": "could_not_run" if interfaces["status"] != "ok" or
            links["status"] == "could_not_run" or
            bool(unmatched) or
            any(profile["status"] == "could_not_run" for profile in profiles.values()) or
            infiniband["status"] == "could_not_run" else "ok",
            "physical_attachment": "UNKNOWN", "transport_validation": "not_run",
            "links": links, "interfaces": profiles, "interfaces_missing_from_ip": unmatched,
            "infiniband": infiniband}


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
    return _pci_binding_target(root, device_path, device_link)


def _pci_binding_target(root: Path, device_path: Path,
                        device_link: str) -> dict[str, Any]:
    resolved_device, error = _sysfs_target(root, device_path)
    if error:
        return {"status": "could_not_run", "error": error}
    resolved_device = cast(Path, resolved_device)
    vendor = _sysfs_text(root, resolved_device / "vendor")
    device = _sysfs_text(root, resolved_device / "device")
    if vendor["status"] != "ok" or device["status"] != "ok":
        return {"status": "could_not_run", "error": {
            "vendor": vendor.get("error"), "device": device.get("error")}}
    driver_link = resolved_device / "driver"
    driver, error = _link_name(driver_link)
    if error:
        return {"status": "could_not_run", "error": error}
    if driver is None:
        return {"status": "unbound", "pci_vendor": vendor["value"],
                "pci_device": device["value"],
                "pci_address": device_link,
                "driver": None, "module": None, "module_version": None}
    resolved_driver, error = _sysfs_target(root, driver_link)
    if error:
        return {"status": "could_not_run", "error": error}
    resolved_driver = cast(Path, resolved_driver)
    driver = resolved_driver.name
    module_link = resolved_driver / "module"
    module, error = _link_name(module_link)
    if error:
        return {"status": "could_not_run", "error": error}
    if module is None:
        module = driver
    else:
        resolved_module, error = _sysfs_target(root, module_link)
        if error:
            return {"status": "could_not_run", "error": error}
        module = cast(Path, resolved_module).name
    version = _sysfs_text(root, root / "sys/module" / module / "version")
    return {"status": "bound", "pci_vendor": vendor["value"],
            "pci_device": device["value"],
            "pci_address": device_link,
            "driver": driver, "module": module,
            "module_version": version,
            "module_version_status": version["status"]}


def _pci_device_inventory(root: Path) -> dict[str, Any]:
    """Read PCI identity and driver bindings from sysfs without invoking tools."""
    directory, error = _sysfs_target(root, root / "sys/bus/pci/devices")
    if error:
        return {"status": "could_not_run", "error": error, "devices": {}}
    try:
        with os.scandir(cast(Path, directory)) as entries:
            names: list[str] = []
            for entry in entries:
                names.append(entry.name)
                if len(names) > MAX_PCI_DEVICE_INSPECTIONS:
                    break
    except OSError as exc:
        return {"status": "could_not_run",
                "error": f"{type(exc).__name__}: {exc}", "devices": {}}
    truncated = len(names) > MAX_PCI_DEVICE_INSPECTIONS
    names = sorted(names[:MAX_PCI_DEVICE_INSPECTIONS])
    devices: dict[str, Any] = {}
    errors: dict[str, str] = {}
    for address in names[:MAX_PCI_DEVICE_INSPECTIONS]:
        if not PCI_ADDRESS_RE.fullmatch(address):
            errors[address] = "invalid PCI address"
            continue
        device_path, error = _sysfs_target(root, root / "sys/bus/pci/devices" / address)
        if error:
            devices[address] = {"status": "could_not_run", "error": error}
            continue
        device_path = cast(Path, device_path)
        fields = {
            name: _sysfs_text(root, device_path / name)
            for name in ("vendor", "device", "class")
        }
        driver_path, driver_error = _sysfs_target(root, device_path / "driver")
        if driver_error and not driver_error.startswith("FileNotFoundError:"):
            driver = {"status": "could_not_run", "error": driver_error}
        elif driver_error:
            driver = {"status": "unbound", "name": None}
        else:
            driver = {"status": "bound", "name": cast(Path, driver_path).name}
        status = "could_not_run" if any(
            value["status"] == "could_not_run" for value in fields.values()
        ) or driver["status"] == "could_not_run" else "observed"
        devices[address] = {"status": status, "address": address,
                            "vendor": fields["vendor"], "device": fields["device"],
                            "class": fields["class"], "driver": driver}
    return {
        "status": "could_not_run" if errors or truncated or any(
            row.get("status") == "could_not_run" for row in devices.values()
        ) else "observed",
        "devices": devices,
        "errors": errors,
        "device_count": None if truncated else len(names),
        "observed_entry_count": len(names),
        "inspected_count": len(devices),
        "truncated": truncated,
    }


def sysfs_hardware_capture(root: Path = Path("/")) -> dict[str, Any]:
    """Collect present-time host identity and physical buses without service calls."""
    interfaces = _interfaces(root)
    network: dict[str, Any] = {}
    for name in interfaces.get("interfaces", []):
        base = root / "sys/class/net" / name
        network[name] = {
            "mtu": _sysfs_text(root, base / "mtu"),
            "carrier": _sysfs_text(root, base / "carrier"),
            "operstate": _sysfs_text(root, base / "operstate"),
            "pci_binding": pci_binding(root, name),
        }
    observations = {
        "boot_id": _sysfs_text(root, root / "proc/sys/kernel/random/boot_id"),
        "kernel_release": _sysfs_text(root, root / "proc/sys/kernel/osrelease"),
        "network_interfaces": interfaces,
        "network": network,
        "pci_devices": _pci_device_inventory(root),
        "infiniband": infiniband_inventory(root),
    }
    pci_inventory = observations["pci_devices"]
    unavailable = (
        could_not_run_count(observations)
        + len(pci_inventory.get("errors", {}))
        + int(pci_inventory.get("truncated", False))
    )
    return {
        "schema": 1,
        "status": "partial" if unavailable else "observed",
        "could_not_run": unavailable,
        "scope": "current local sysfs snapshot; historical and remote workloads are unverified",
        "safety": {
            "commands_executed": False,
            "services_contacted": False,
            "services_changed": False,
            "network_changed": False,
            "modules_changed": False,
            "block_device_written": False,
        },
        "identity": {
            "architecture": platform.machine(),
            "kernel_release": platform.uname().release,
        },
        "observations": observations,
    }


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
    """Count nodes carrying an unavailable status in a diagnostics report."""
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
        "boot_state": boot_state_inventory(root),
        "gpu_runtime": gpu_runtime_capture(runner),
        "network": {
            "nm_devices": run_readonly(
                ["nmcli", "--terse", "--fields", "DEVICE,TYPE,STATE", "device", "status"], runner),
            "links": run_readonly(["ip", "-brief", "link"], runner),
            "default_routes": run_readonly(["ip", "route", "show", "default"], runner),
            "wireless_interfaces": run_readonly(["iw", "dev"], runner),
            "interface_inventory": interfaces,
            "inventory": network_inventory(root, runner),
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
                     "page_size_bytes": os.sysconf("SC_PAGE_SIZE"),
                     "source": "host"},
        "filesystem_root": str(root),
        "command_scope": "host" if runner is subprocess.run else "caller_supplied",
        "safety": {"mode": "read_only", "shell": False,
                   "services_changed": False, "network_changed": False,
                   "modules_changed": False, "block_device_written": False},
        "checks": checks,
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path("/"),
                        help="filesystem root for fixture-based checks")
    parser.add_argument("--sysfs-only", action="store_true",
                        help="collect local proc/sysfs identity without commands or service calls")
    parser.add_argument("--check-backup-destination", action="store_true",
                        help="verify an exact mounted destination using explicit identity")
    parser.add_argument("--backup-mountpoint")
    parser.add_argument("--backup-source")
    parser.add_argument("--backup-uuid")
    args = parser.parse_args(argv)
    if args.sysfs_only:
        if args.check_backup_destination or any(value is not None for value in
                                                 (args.backup_mountpoint, args.backup_source,
                                                  args.backup_uuid)):
            parser.error("--sysfs-only cannot be combined with backup destination checks")
        report = sysfs_hardware_capture(args.root)
        sys.stdout.write(json.dumps(report, indent=2, sort_keys=True) + "\n")
        return 2 if report["could_not_run"] else 0
    backup_values = (args.backup_mountpoint, args.backup_source, args.backup_uuid)
    if args.check_backup_destination:
        if args.root != Path("/"):
            parser.error("backup destination check always queries the live mount namespace")
        report = backup_destination_check(Path("/"), *backup_values)
        sys.stdout.write(json.dumps(report, indent=2, sort_keys=True) + "\n")
        return {"pass": 0, "block": 1, "unknown": 2}[report["status"]]
    if any(value is not None for value in backup_values):
        parser.error("backup identity arguments require --check-backup-destination")
    report = capture(args.root)
    sys.stdout.write(json.dumps(report, indent=2, sort_keys=True) + "\n")
    return 2 if report["could_not_run"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
