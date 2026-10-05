"""Adversarial controls for command ownership and unavailable native outputs."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from tools import verify_gpu_clock_cap_ab as gpu
from tools import verify_usb_hid_postupdate as usb
from tools import verify_wifi_isolation as wifi


def _row(command: str, output: str, *, exit_code: int = 0) -> dict[str, Any]:
    return {"cmd": command, "exit": exit_code, "stdout": output, "stderr": ""}


def test_wifi_readers_require_successful_native_commands_and_actual_executable() -> None:
    link_text = "Connected to AA:BB:CC:DD:EE:FF\nSSID: lab\nfreq: 5180"
    assert not wifi._has_program(_row("echo iw dev wlan0 link", link_text), "iw")
    assert not wifi._management_probe(_row("ssh -V", "OpenSSH_9.6p1"))
    for command in ("ssh -G operator@mgmt", "ssh -Q cipher operator@mgmt",
                    "ssh -O check operator@mgmt", "ssh -N operator@mgmt",
                    "ssh -NT operator@mgmt", "ssh -TV operator@mgmt",
                    "ssh -TG operator@mgmt"):
        assert wifi._ssh_target(_row(command, "operator@mgmt")) is None
    assert wifi._management_probe(_row("ssh -o BatchMode=yes operator@mgmt true", "ok"))
    assert wifi._management_probe(_row("ssh -n operator@mgmt uname -r", "6.17-test"))
    assert wifi._management_probe(_row("ssh -nT operator@mgmt uname -r", "6.17-test"))
    assert wifi._management_probe(_row("ssh -o -N operator@mgmt hostname -N", "-N"))
    assert not wifi._wifi_connected(_row("iw dev wlan0 link", link_text, exit_code=2))
    assert wifi._link_details(_row("iw dev wlan0 link", link_text, exit_code=2)) is None
    assert not wifi._default_route(
        _row("ip route show default", "default via 192.0.2.1 dev wlan0", exit_code=2))
    assert wifi._connection_snapshot(_row(
        "nmcli connection show lab", "802-11-wireless.ssid: lab", exit_code=1)) == {}
    assert wifi._modified_value(_row(
        "nmcli connection modify lab 802-11-wireless.band bg", "", exit_code=10),
        "802-11-wireless.band") is None
    generic_nmcli = _row("nmcli --version", "GENERAL.STATE: 100 (connected)")
    assert not wifi._wifi_connected(generic_nmcli)


def test_wifi_generic_remote_nonzero_is_could_not_run_but_native_refusal_is_failure() -> None:
    generic = _row("ssh operator@management true", "stale success-looking output", exit_code=255)
    refused = _row("ssh operator@management true", "", exit_code=255)
    refused["stderr"] = "ssh: connect to host management port 22: Connection refused"
    assert wifi._trial_remote_index([(3, generic)]) == (None, "missing")
    assert wifi._trial_remote_index([(3, refused)]) == (None, "failed")
    assert not wifi._explicit_remote_failure(_row("ssh -G operator@management", "Connection refused", exit_code=255))


def test_wifi_failed_identity_commands_cannot_supply_a_usable_oem_tuple() -> None:
    rows = [
        _row("dmidecode -t system", "Manufacturer: ASUS\nProduct Name: GX10\nBIOS Version: 1.0", exit_code=1),
        _row("uname -r", "6.17-test", exit_code=1),
        _row("modinfo mt7925e", "version: 1.0", exit_code=1),
        _row("nmcli --version", "nmcli tool, version 1.48", exit_code=1),
        _row("cat /etc/os-release", 'PRETTY_NAME="DGX OS"', exit_code=1),
        _row("wpa_supplicant -v", "wpa_supplicant v2.10", exit_code=1),
        _row("ethtool -i wlan0", "driver: mt7925e\nfirmware-version: 1.0", exit_code=1),
        _row("iw dev wlan0 link", "Connected to AA:BB:CC:DD:EE:FF\nSSID: lab\nfreq: 5180", exit_code=1),
    ]
    assert wifi._observed_identity(rows) is None


def test_wifi_missing_trial_time_is_could_not_run_not_failed_recovery() -> None:
    rows = [
        _row("nmcli connection modify lab 802-11-wireless.band bg", ""),
        _row("nmcli connection up lab --timeout 20", "activated"),
        _row("iw dev wlan0 link", "Connected to AA:BB:CC:DD:EE:FF\nSSID: lab\nfreq: 2412"),
        _row("ip route show default", "default via 192.0.2.1 dev wlan0"),
        _row("ssh operator@management true", "reachable"),
    ]
    assert wifi._recovered_trial(rows, 0, "802-11-wireless.band", "bg", "lab") is None


def test_usb_readers_require_native_command_ownership_for_module_and_input_evidence() -> None:
    modules = _row("echo lsmod", "usbhid 1 0\nhid_generic 1 0")
    event = _row("echo evtest /dev/input/event0",
                 "Event: type 1 (EV_KEY), code 30, value 1")
    assert not usb._has(modules, "lsmod")
    assert not usb._input_event([event], "affected")
    fake_config = _row("echo CONFIG_USB_HID=y", "CONFIG_USB_HID=y\nCONFIG_USB_HID_GENERIC=y")
    fake_config["capture_phase"] = "affected"
    assert usb._integrated([fake_config], "affected") is None
    for command in ("ssh -V", "ssh -G operator@host", "ssh -Q cipher operator@host",
                    "ssh -O check operator@host", "ssh -N operator@host", "ssh -NT operator@host",
                    "ssh -TV operator@host", "ssh -TG operator@host"):
        command_row = _row(command, "apparently reachable")
        command_row["capture_phase"] = "affected"
        assert not usb._ssh_ok([command_row], "affected")
    valid_remote = _row("ssh -n operator@host uname -r", "6.17-test")
    valid_remote["capture_phase"] = "affected"
    assert usb._ssh_ok([valid_remote], "affected")
    remote_option_argument = _row("ssh operator@host hostname -N", "-N")
    remote_option_argument["capture_phase"] = "affected"
    assert usb._ssh_ok([remote_option_argument], "affected")


def test_gpu_outputs_must_belong_to_the_executed_native_program(tmp_path: Path) -> None:
    supported = _row("echo nvidia-smi -q -d SUPPORTED_CLOCKS", "Graphics : 2100 MHz")
    assert gpu._supported_graphics_clocks([supported]) == set()
    assert gpu._supported_graphics_clocks([_row("sudo -n nvidia-smi -q -d SUPPORTED_CLOCKS",
                                                "Graphics : 2100 MHz")]) == {2100}

    query = ("nvidia-smi --query-gpu=clocks.current.graphics,power.draw,temperature.gpu,"
             "utilization.gpu,clocks_throttle_reasons.active --format=csv")
    fake_telemetry = _row("echo " + query, "1800, 200, 60, 70, 0")
    assert gpu._telemetry(fake_telemetry) is None
    assert gpu._telemetry(_row("sudo -n " + query, "1800, 200, 60, 70, 0")) is not None

    plan = {"stock_policy": [300, 2800], "capped_policy": [300, 2100],
            "soak_seconds": 600, "max_sample_gap_seconds": 60}
    fake_plan = _row("echo cat clock-cap-plan.json", json.dumps(plan))
    parsed, error = gpu._plan({"experiment_plan": plan}, [fake_plan], tmp_path / "capture.json")
    assert parsed is None and error is not None and error["status"] == "unknown"

    rows = gpu_identity_rows()
    assert gpu._identity(rows)
    for row in rows:
        row["cmd"] = "echo " + row["cmd"]
    assert not gpu._identity(rows)

    incomplete_tuple = gpu_identity_rows()
    incomplete_tuple[4]["stdout"] = "driver_version, N/A"
    incomplete_tuple[5]["stdout"] = "No updatable devices found"
    assert not gpu._identity(incomplete_tuple)

    echo_error = _row("echo nvidia-smi -q", "", exit_code=1)
    result = gpu._verify({}, [echo_error], tmp_path / "capture.json")
    assert result["status"] == "unknown" and "tuple incomplete" in result["reason"]
    native_query_error = _row("nvidia-smi -q", "generic query error", exit_code=2)
    assert gpu._verify({}, [native_query_error], tmp_path / "capture.json")["status"] == "unknown"
    hardware_fault = _row("nvidia-smi -q", "NVIDIA-SMI has failed because it couldn't communicate with the NVIDIA driver", exit_code=2)
    assert gpu._verify({}, [hardware_fault], tmp_path / "capture.json")["status"] == "fail"

    output = json.dumps({"duration_seconds": 10, "tokens_per_second": 20,
                         "completed_requests": 1, "failed_requests": 0,
                         "p50_latency_ms": 5, "p99_latency_ms": 8,
                         "model_sha256": "model", "image_digest": "image",
                         "input_sha256": "input", "concurrency": 1, "max_new_tokens": 20})
    spec = {"row": _row("echo benchmark --json", output), "phase": "baseline",
            "plan": {"capped_policy": [300, 2100]}, "path": tmp_path / "capture.json",
            "runs": [], "samples": []}
    result = gpu._consume_measurement(spec)
    assert result is not None and result["status"] == "unknown"


def gpu_identity_rows() -> list[dict[str, Any]]:
    return [
        _row("dmidecode -t system", "Manufacturer: OEM\nProduct Name: GB10\nBIOS Version: 1.0"),
        _row("uname -r", "6.17-test"),
        _row("cat /etc/os-release", "PRETTY_NAME=Test"),
        _row("modinfo nvidia", "version: 580.178.04"),
        _row("nvidia-smi --query-gpu=name,driver_version --format=csv", "GB10, 580.178.04"),
        _row("fwupdmgr get-devices", "├─System Firmware:\n│     Device ID: 1234\n│     Current version: 1.0"),
    ]
