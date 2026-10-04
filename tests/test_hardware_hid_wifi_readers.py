"""Adversarial input and prior-kernel recovery tests for hardware parsers."""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from tools import verify_usb_hid_postupdate as usb
from tools import verify_wifi_isolation as wifi


def test_usb_reader_rejects_duplicate_keys_and_symlink(tmp_path: Path) -> None:
    duplicate = tmp_path / "duplicate.json"
    duplicate.write_text('{"id":"first","id":"second"}', encoding="utf-8")
    assert usb._read(duplicate) is None

    target = tmp_path / "target.json"
    target.write_text("{}", encoding="utf-8")
    link = tmp_path / "link.json"
    link.symlink_to(target)
    assert usb._read(link) is None


def test_wifi_reader_is_bounded_strict_and_symlink_safe(tmp_path: Path) -> None:
    duplicate = tmp_path / "duplicate.json"
    duplicate.write_text('{"id":"first","id":"second"}', encoding="utf-8")
    assert wifi._read_capture(duplicate) is None

    target = tmp_path / "target.json"
    target.write_text(json.dumps({"id": wifi.FINDING, "commands": []}), encoding="utf-8")
    link = tmp_path / "link.json"
    link.symlink_to(target)
    assert wifi._read_capture(link) is None

    oversized = tmp_path / "oversized.json"
    oversized.write_bytes(b" " * (wifi.MAX_CAPTURE_BYTES + 1))
    assert wifi._read_capture(oversized) is None


def test_wifi_reader_rejects_fifo_without_blocking(tmp_path: Path) -> None:
    fifo = tmp_path / "capture.json"
    os.mkfifo(fifo)
    assert wifi._read_capture(fifo) is None


def test_usb_recovery_must_return_to_the_preupdate_kernel(tmp_path: Path) -> None:
    rows: list[dict[str, Any]] = [
        {"cmd": "evtest /dev/input/event0", "exit": 0,
         "stdout": "Event: type 1 (EV_KEY), code 30 (KEY_A), value 1", "stderr": "",
         "capture_phase": "recovery"},
        {"cmd": "ssh operator@management true", "exit": 0, "stdout": "ok", "stderr": "",
         "capture_phase": "recovery"},
        {"cmd": "lsmod", "exit": 0, "stdout": "usbhid 1 0\nhid_generic 1 0", "stderr": "",
         "capture_phase": "recovery"},
    ]
    wrong_kernel = usb._check_recovery(rows, tmp_path / "commands.json", "kernel-old", "kernel-new",
                                       "kernel-third")
    assert wrong_kernel is not None and wrong_kernel["status"] == "fail"

    prior_kernel = usb._check_recovery(rows, tmp_path / "commands.json", "kernel-old", "kernel-new",
                                       "kernel-old")
    assert prior_kernel is None


def test_usb_full_rollback_fixture_requires_and_accepts_the_exact_prior_kernel(tmp_path: Path) -> None:
    rows: list[dict[str, Any]] = []
    boots = {"pre-update": "11111111-1111-4111-8111-111111111111",
             "affected": "22222222-2222-4222-8222-222222222222",
             "recovery": "33333333-3333-4333-8333-333333333333"}

    def add(phase: str, argv: str, stdout: str, *, exit_code: int = 0) -> None:
        rows.append({"cmd": argv, "exit": exit_code, "stdout": stdout, "stderr": "",
                     "capture_phase": phase, "boot_id": boots[phase]})

    add("pre-update", "dmidecode -t system", "Manufacturer: NVIDIA\nProduct Name: DGX Spark")
    for phase, kernel in (("pre-update", "6.17.0-1028-nvidia"),
                          ("affected", "6.17.0-1029-nvidia"),
                          ("recovery", "6.17.0-1028-nvidia")):
        add(phase, "cat /proc/sys/kernel/random/boot_id", boots[phase])
        add(phase, "uname -r", kernel)
    add("pre-update", "evtest /dev/input/event0", "Event: type 1 (EV_KEY), code 30, value 1")
    add("pre-update", "ssh operator@management true", "reachable")
    add("affected", "lsusb -t", "Class=Human Interface Device, Driver=xhci-hcd")
    add("affected", "lsmod", "xhci_hcd 1 0")
    add("affected", "grep CONFIG_USB_HID /boot/config", "CONFIG_USB_HID=n\nCONFIG_USB_HID_GENERIC=n")
    add("affected", "dpkg --audit", "The following packages have been unpacked but not yet configured:\n linux-modules-nvidia")
    add("affected", "journalctl -k", "usbhid: failed to initialize")
    add("recovery", "evtest /dev/input/event0", "Event: type 1 (EV_KEY), code 30, value 1")
    add("recovery", "ssh operator@management true", "reachable")
    add("recovery", "lsmod", "usbhid 1 0\nhid_generic 1 0")

    result = usb._verify_rows(rows, tmp_path / "commands.json")

    assert result["status"] == "pass", result
    recovery_kernel = next(row for row in rows if row["capture_phase"] == "recovery" and row["cmd"] == "uname -r")
    recovery_kernel["stdout"] = "6.17.0-1030-nvidia"
    result = usb._verify_rows(rows, tmp_path / "commands.json")
    assert result["status"] == "fail" and "pre-update kernel" in result["reason"], result
