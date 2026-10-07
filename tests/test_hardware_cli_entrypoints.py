"""The original `python -m` close-check commands must print and enforce verdicts."""
from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[1]
MODULES = (
    "tools.verify_gpu_clock_cap_ab",
    "tools.verify_wifi_isolation",
    "tools.verify_usb_hid_postupdate",
)


def _run(module: str, evidence: Path | None = None, *extra: str) -> subprocess.CompletedProcess[str]:
    command = [sys.executable, "-m", module]
    if evidence is not None:
        command.extend(("--evidence", str(evidence)))
    command.extend(extra)
    env = {**os.environ, "PYTHONPATH": str(ROOT)}
    return subprocess.run(command, cwd=ROOT, env=env, text=True, capture_output=True, check=False)


@pytest.mark.parametrize("module", MODULES)
def test_missing_real_capture_is_printed_unknown_and_nonzero(module: str, tmp_path: Path) -> None:
    result = _run(module, tmp_path / "absent")
    assert result.returncode == 2, result
    verdict = json.loads(result.stdout)
    assert verdict["status"] == "unknown" and verdict["could_not_run"] == 1
    assert verdict["fail"] == 0


@pytest.mark.parametrize("module", MODULES)
def test_invalid_arguments_are_rejected_by_the_real_module_command(module: str) -> None:
    result = _run(module, None, "--unexpected-option")
    assert result.returncode == 2
    assert result.stdout == ""
    assert "usage:" in result.stderr


def test_gpu_generic_nonzero_native_command_is_could_not_run_and_rc2(tmp_path: Path) -> None:
    evidence = tmp_path / "gpu"
    evidence.mkdir()
    (evidence / "commands.json").write_text(json.dumps({
        "id": "FEATURE-FORUM-GPU-CLOCK-CAP-AB-01",
        "commands": [{"cmd": "nvidia-smi -q", "exit": 2, "stdout": "", "stderr": "error",
                      "captured_at": "2026-10-04T00:00:00+00:00"}],
    }), encoding="utf-8")
    result = _run(MODULES[0], evidence)
    assert result.returncode == 2, result
    verdict = json.loads(result.stdout)
    assert verdict["status"] == "unknown" and verdict["fail"] == 0
    assert verdict["could_not_run"] == 1


def test_wifi_failed_local_and_remote_probes_are_reported_as_fail_and_rc1(tmp_path: Path) -> None:
    evidence = tmp_path / "wifi"
    evidence.mkdir()
    (evidence / "commands.json").write_text(json.dumps({
        "id": "FEATURE-FORUM-WIFI-ISOLATION-01",
        "commands": [
            {"cmd": "ping -c 1 127.0.0.1", "exit": 1, "stdout": "", "stderr": "",
             "captured_at": "2026-10-04T00:00:00+00:00"},
            {"cmd": "ssh operator@management true", "exit": 255, "stdout": "", "stderr": "Connection refused",
             "captured_at": "2026-10-04T00:00:01+00:00"},
        ],
    }), encoding="utf-8")
    result = _run(MODULES[1], evidence)
    assert result.returncode == 1, result
    verdict = json.loads(result.stdout)
    assert verdict["status"] == "fail" and verdict["fail"] == 1
    assert verdict["could_not_run"] == 0


def _usb_capture() -> dict[str, Any]:
    boots = {"pre-update": "11111111-1111-4111-8111-111111111111",
             "affected": "22222222-2222-4222-8222-222222222222",
             "recovery": "33333333-3333-4333-8333-333333333333"}
    rows: list[dict[str, Any]] = []

    def add(phase: str, command: str, output: str, *, exit_code: int = 0) -> None:
        rows.append({"cmd": command, "exit": exit_code, "stdout": output, "stderr": "",
                     "capture_phase": phase, "boot_id": boots[phase]})

    add("pre-update", "dmidecode -t system", "Manufacturer: OEM\nProduct Name: Model")
    for phase, kernel in (("pre-update", "6.1-old"), ("affected", "6.2-bad"), ("recovery", "6.1-old")):
        add(phase, "cat /proc/sys/kernel/random/boot_id", boots[phase])
        add(phase, "uname -r", kernel)
    add("pre-update", "evtest /dev/input/event0", "type 1 (EV_KEY), code 30, value 1")
    add("pre-update", "ssh operator@management true", "reachable")
    # Driver=[none]: the HID-class interface is unbound, the real signature of post-update loss
    # (a root-hub/controller driver such as xhci-hcd is never what binds to the device itself).
    add("affected", "lsusb -t", "Class=Human Interface Device, Driver=[none]")
    add("affected", "lsmod", "Module                  Size  Used by\nxhci_hcd 1 0")
    add("affected", "grep CONFIG_USB_HID /boot/config", "CONFIG_USB_HID=n\nCONFIG_USB_HID_GENERIC=n")
    add("affected", "dpkg --audit", "The following packages have been unpacked but not yet configured:\n linux-modules")
    add("affected", "journalctl -k", "usbhid: failed to initialize")
    add("recovery", "evtest /dev/input/event0", "type 1 (EV_KEY), code 30, value 1")
    add("recovery", "ssh operator@management true", "reachable")
    add("recovery", "lsmod", "Module                  Size  Used by\nusbhid 1 0\nhid_generic 1 0")
    return {"id": "FEATURE-USB-HID-POSTUPDATE-CHECK", "commands": rows}


def test_usb_complete_unit_contract_can_return_zero_only_for_pass(tmp_path: Path) -> None:
    evidence = tmp_path / "usb"
    evidence.mkdir()
    (evidence / "commands.json").write_text(json.dumps(_usb_capture()), encoding="utf-8")
    result = _run(MODULES[2], evidence)
    assert result.returncode == 0, result
    verdict = json.loads(result.stdout)
    assert verdict["status"] == "pass" and verdict["fail"] == verdict["could_not_run"] == 0
