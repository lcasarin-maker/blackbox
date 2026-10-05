from __future__ import annotations

import os
from pathlib import Path

import pytest

from tools import host_diagnostics as hd


def _link(root: Path, bus_path: str, target: Path) -> None:
    link = root / "sys" / bus_path
    link.parent.mkdir(parents=True, exist_ok=True)
    link.symlink_to(os.path.relpath(target, link.parent))


def test_usb_inventory_reads_identity_speed_and_correlates_hid(tmp_path: Path) -> None:
    root = tmp_path
    usb = root / "sys/devices/platform/usb1/1-2"
    interface = usb / "1-2:1.0"
    hid = interface / "0003:1234:5678.0001"
    hid.mkdir(parents=True)
    for name, value in {"idVendor": "1234", "idProduct": "5678", "manufacturer": "Maker",
                        "product": "Keyboard", "serial": "unit-01", "speed": "12"}.items():
        (usb / name).write_text(value, encoding="ascii")
    _link(root, "bus/usb/devices/1-2", usb)
    _link(root, "bus/usb/devices/1-2:1.0", interface)
    _link(root, "bus/hid/devices/0003:1234:5678.0001", hid)

    result = hd.usb_inventory(root)

    assert result["status"] == "ok"
    assert result["devices"]["1-2"] == {
        "status": "ok", "idVendor": {"status": "ok", "value": "1234"},
        "idProduct": {"status": "ok", "value": "5678"},
        "manufacturer": {"status": "ok", "value": "Maker"},
        "product": {"status": "ok", "value": "Keyboard"},
        "serial": {"status": "ok", "value": "unit-01"},
        "speed": {"status": "ok", "value": "12"}}
    assert result["hid_devices"]["0003:1234:5678.0001"] == {
        "status": "ok", "usb_device": "1-2"}


def test_hid_correlates_to_nearest_usb_device_below_hub(tmp_path: Path) -> None:
    root = tmp_path
    hub = root / "sys/devices/usb1/1-1"
    child = hub / "1-1.2"
    interface = child / "1-1.2:1.0"
    hid = interface / "0003:1234:5678.0001"
    hid.mkdir(parents=True)
    for target, vendor in ((hub, "1111"), (child, "1234")):
        for name, value in {"idVendor": vendor, "idProduct": "5678", "manufacturer": "Maker",
                            "product": "Device", "speed": "480"}.items():
            (target / name).write_text(value, encoding="ascii")
    _link(root, "bus/usb/devices/1-1", hub)
    _link(root, "bus/usb/devices/1-1.2", child)
    _link(root, "bus/usb/devices/1-1.2:1.0", interface)
    _link(root, "bus/hid/devices/0003:1234:5678.0001", hid)

    result = hd.usb_inventory(root)

    assert result["hid_devices"]["0003:1234:5678.0001"] == {
        "status": "ok", "usb_device": "1-1.2"}
    assert result["devices"]["1-1.2"]["serial"] == {
        "status": "unknown", "reason": "sysfs attribute absent"}


def test_usb_inventory_preserves_missing_and_unmatched_states(tmp_path: Path) -> None:
    usb = tmp_path / "sys/devices/usb1/1-1"
    usb.mkdir(parents=True)
    _link(tmp_path, "bus/usb/devices/1-1", usb)
    hid = tmp_path / "sys/devices/platform/orphan-hid"
    hid.mkdir(parents=True)
    _link(tmp_path, "bus/hid/devices/orphan", hid)

    result = hd.usb_inventory(tmp_path)

    assert result["status"] == "could_not_run"
    assert result["devices"]["1-1"]["status"] == "could_not_run"
    assert result["devices"]["1-1"]["speed"]["status"] == "could_not_run"
    assert result["hid_devices"]["orphan"] == {"status": "unmatched", "usb_device": None}
    assert hd.could_not_run_count(result) == 7


def test_sysfs_symlink_escape_is_inaccessible(tmp_path: Path) -> None:
    links = tmp_path / "sys/bus/usb/devices"
    links.mkdir(parents=True)
    (links / "1-1").symlink_to("/etc")

    result = hd.usb_inventory(tmp_path)

    assert result["devices"]["1-1"]["status"] == "could_not_run"
    assert "ValueError" in result["devices"]["1-1"]["error"]


def test_sysfs_symlink_loop_is_inaccessible(tmp_path: Path) -> None:
    links = tmp_path / "sys/bus/usb/devices"
    links.mkdir(parents=True)
    (links / "1-1").symlink_to("1-1")

    result = hd.usb_inventory(tmp_path)

    assert result["devices"]["1-1"]["status"] == "could_not_run"
    assert "RuntimeError" in result["devices"]["1-1"]["error"]


def test_usb_inventory_preserves_missing_usb_directory(tmp_path: Path) -> None:
    result = hd.usb_inventory(tmp_path)
    assert result["status"] == "could_not_run"
    assert "FileNotFoundError" in result["error"]


def test_device_attributes_preserves_unavailable_sysfs_entry(tmp_path: Path) -> None:
    result = hd._device_attributes(tmp_path, tmp_path / "missing", ("serial",))
    assert result["status"] == "could_not_run"
    assert "FileNotFoundError" in result["error"]


def test_optional_serial_read_failure_reports_unknown_only_for_absence(
        monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(hd, "read_text", lambda _path: {
        "status": "could_not_run", "error": "FileNotFoundError: raced with unplug"})
    assert hd.read_optional_text(tmp_path / "serial") == {
        "status": "unknown", "reason": "sysfs attribute absent"}


def test_hid_symlink_error_is_reported_as_could_not_run(tmp_path: Path) -> None:
    usb = tmp_path / "sys/devices/usb1/1-1"
    usb.mkdir(parents=True)
    for name, value in {"idVendor": "1234", "idProduct": "5678", "manufacturer": "Maker",
                        "product": "Device", "speed": "480"}.items():
        (usb / name).write_text(value, encoding="ascii")
    _link(tmp_path, "bus/usb/devices/1-1", usb)
    hid_dir = tmp_path / "sys/bus/hid/devices"
    hid_dir.mkdir(parents=True)
    (hid_dir / "broken").symlink_to("/etc")

    result = hd.usb_inventory(tmp_path)

    assert result["hid_devices"]["broken"]["status"] == "could_not_run"
    assert result["hid_devices"]["broken"]["usb_device"] is None


def test_serial_permission_failure_stays_could_not_run(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    device = tmp_path / "sys/devices/usb1/1-1"
    device.mkdir(parents=True)
    for name, value in {"idVendor": "1234", "idProduct": "5678", "manufacturer": "Maker",
                        "product": "Device", "serial": "unit-01", "speed": "480"}.items():
        (device / name).write_text(value, encoding="ascii")
    _link(tmp_path, "bus/usb/devices/1-1", device)
    original = hd.capture_io.read_regular_bytes

    def read_bytes(path: Path, max_bytes: int) -> bytes:
        if path.name == "serial":
            raise PermissionError("serial denied")
        return original(path, max_bytes)

    monkeypatch.setattr(hd.capture_io, "read_regular_bytes", read_bytes)
    result = hd.usb_inventory(tmp_path)

    assert result["status"] == "could_not_run"
    assert result["devices"]["1-1"]["serial"] == {
        "status": "could_not_run", "error": "PermissionError: serial denied"}


def test_usb_attribute_symlink_escape_is_inaccessible(tmp_path: Path) -> None:
    device = tmp_path / "sys/devices/usb1/1-1"
    device.mkdir(parents=True)
    (device / "idVendor").symlink_to("/etc/passwd")
    for name, value in {"idProduct": "5678", "manufacturer": "Maker", "product": "Device",
                        "speed": "480"}.items():
        (device / name).write_text(value, encoding="ascii")
    _link(tmp_path, "bus/usb/devices/1-1", device)

    result = hd.usb_inventory(tmp_path)

    assert result["devices"]["1-1"]["status"] == "could_not_run"
    assert result["devices"]["1-1"]["idVendor"]["status"] == "could_not_run"
    assert "ValueError" in result["devices"]["1-1"]["idVendor"]["error"]


def test_watchdog_inventory_reports_unknown_owner_without_device_open(tmp_path: Path) -> None:
    device = tmp_path / "sys/devices/platform/sbsa/watchdog/watchdog0"
    device.mkdir(parents=True)
    for name, value in {"identity": "SBSA", "state": "active", "timeout": "60",
                        "nowayout": "0"}.items():
        (device / name).write_text(value, encoding="ascii")
    _link(tmp_path, "class/watchdog/watchdog0", device)

    result = hd.watchdog_inventory(tmp_path)

    assert result == {"status": "ok", "owner": "UNKNOWN", "devices": {
        "watchdog0": {"status": "ok", "identity": {"status": "ok", "value": "SBSA"},
                       "state": {"status": "ok", "value": "active"},
                       "timeout": {"status": "ok", "value": "60"},
                       "nowayout": {"status": "ok", "value": "0"}}}}


def test_watchdog_inventory_keeps_absent_owner_unknown(tmp_path: Path) -> None:
    result = hd.watchdog_inventory(tmp_path)
    assert result["status"] == "could_not_run"
    assert result["owner"] == "UNKNOWN"
    assert hd.could_not_run_count(result) == 1
