"""Check USB HID loss classification against the three boot observations."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from tools import verify_usb_hid_postupdate as usb


def _row(command: str, output: str, *, phase: str = "affected", boot: str = "1" * 36,
         exit_code: int = 0) -> dict[str, Any]:
    return {"cmd": command, "stdout": output, "stderr": "", "exit": exit_code,
            "capture_phase": phase, "boot_id": boot}


def test_boot_identity_is_phase_specific_and_rejects_recycled_or_malformed_ids() -> None:
    boots = {"pre-update": "11111111-1111-4111-8111-111111111111",
             "affected": "22222222-2222-4222-8222-222222222222",
             "recovery": "33333333-3333-4333-8333-333333333333"}
    rows = [_row("cat /proc/sys/kernel/random/boot_id", value, phase=phase, boot=value)
            for phase, value in boots.items()]
    assert usb._boot_ids(rows) == boots
    rows[-1]["stdout"] = boots["affected"]
    assert usb._boot_ids(rows) is None
    rows[-1]["stdout"] = "not-a-boot-id"
    assert usb._boot_ids(rows) is None


def test_affected_boot_healthy_builtin_or_loaded_hid_is_negative_control(tmp_path: Path) -> None:
    package = _row("dpkg --audit", "")
    journal = _row("journalctl -k", "usbhid: failed to initialize")
    loaded = [package, journal,
              _row("lsmod", "Module                  Size  Used by\nusbhid 1 0\nhid_generic 1 0")]
    result = usb._affected_loss(loaded, tmp_path / "commands.json")
    assert isinstance(result, dict) and result["status"] == "fail"

    builtin = [package, journal, _row("uname -r", "6.17.0-1032-nvidia\n"),
               _row("grep -E '^(# )?CONFIG_(HID|USB_HID|HID_GENERIC)[= ]' /boot/config-6.17.0-1032-nvidia",
                    "CONFIG_HID=y\nCONFIG_USB_HID=y\nCONFIG_HID_GENERIC=y")]
    result = usb._affected_loss(builtin, tmp_path / "commands.json")
    assert isinstance(result, dict) and result["status"] == "fail"


def test_affected_failure_requires_accessible_package_and_kernel_evidence(tmp_path: Path) -> None:
    absent, reason = usb._affected_loss([
        _row("lsmod", "xhci_hcd 1 0"), _row("dpkg --audit", ""),
        _row("journalctl -k", "usbhid: failed to initialize"),
    ], tmp_path / "commands.json")
    assert absent and not reason

    missing = usb._affected_loss([_row("lsmod", "xhci_hcd 1 0")], tmp_path / "commands.json")
    assert isinstance(missing, dict) and missing["status"] == "unknown"

    inaccessible = usb._affected_loss([
        _row("lsmod", "xhci_hcd 1 0"), _row("dpkg --audit", "", exit_code=1),
        _row("journalctl -k", "usbhid: failed to initialize"),
    ], tmp_path / "commands.json")
    assert isinstance(inaccessible, dict) and inaccessible["status"] == "unknown"


def test_malformed_rows_and_live_unbound_hid_are_distinguished(tmp_path: Path) -> None:
    malformed = usb._verify_rows([{"cmd": "lsusb -t", "exit": 0}], tmp_path / "commands.json")
    assert malformed["status"] == "fail" and "malformed" in malformed["reason"]

    unbound = usb._verify_rows([
        _row("lsusb -t", "Port 1: Dev 1, If 0, Class=Hub, Driver=xhci-hcd, 480M\n"
                         "    |__ Port 2: Dev 2, If 0, Class=Human Interface Device, Driver=[none], 1.5M",
             phase="snapshot"),
        _row("lsmod", "Module                  Size  Used by\nxhci_hcd 1 0", phase="snapshot"),
    ], tmp_path / "commands.json")
    assert unbound["status"] == "fail" and "no bound driver" in unbound["reason"]
