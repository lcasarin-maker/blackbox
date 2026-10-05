"""Positive, negative, and missing-evidence tests for three hardware selectors."""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from tools.verify_gpu_clock_cap_ab import _csv_policy, verify as verify_gpu
from tools.verify_usb_hid_postupdate import verify as verify_usb
from tools.verify_wifi_isolation import verify as verify_wifi


def _write(tmp_path: Path, finding: str, rows: list[dict[str, object]], **extra: object) -> Path:
    path = tmp_path / "commands.json"
    path.write_text(json.dumps({"id": finding, "commands": rows, **extra}), encoding="utf-8")
    return path.parent


def _row(cmd: str, stdout: str, *, exit: int = 0, phase: str | None = None, when: int = 0) -> dict[str, object]:
    row: dict[str, object] = {"cmd": cmd, "exit": exit, "stdout": stdout, "stderr": "",
                              "captured_at": f"2026-10-03T10:00:{when:02d}+00:00"}
    if phase:
        row["capture_phase"] = phase
        row["boot_id"] = {"pre-update": "00000000-0000-0000-0000-000000000001",
                          "affected": "00000000-0000-0000-0000-000000000002",
                          "recovery": "00000000-0000-0000-0000-000000000003"}[phase]
    return row


def test_gpu_clock_cap_needs_native_locked_policy_readback(tmp_path: Path) -> None:
    plan = {"stock_policy": [300, 2800], "capped_policy": [300, 2200],
            "soak_seconds": 3600, "max_sample_gap_seconds": 60}
    rows = [
        _row("dmidecode -t system", "Manufacturer: HP\nProduct Name: ZGX Nano G1n\nBIOS Version: F.01", when=0),
        _row("uname -r", "7.0.0-1019-nvidia", when=1),
        _row("cat /etc/os-release", "PRETTY_NAME=\"NVIDIA DGX OS 7.5\"", when=1),
        _row("nvidia-smi --query-gpu=name,driver_version --format=csv", "GB10, 580.178.04", when=2),
        _row("modinfo nvidia", "version: 580.178.04", when=3),
        _row("fwupdmgr get-devices", "├─System Firmware:\n│     Device ID: 1234\n│     Current version: 1.0", when=3),
        _row("nvidia-smi -q -d SUPPORTED_CLOCKS", "Supported Clocks\n    Graphics: [N/A]\n    Memory: [N/A]", when=3),
        _row("cat /tmp/clock-cap-plan.json", json.dumps(plan), when=3),
    ]
    rows.extend(_row("vllm benchmark", json.dumps({
        "duration_seconds": 3600, "tokens_per_second": 20, "completed_requests": 100,
        "failed_requests": 0, "p50_latency_ms": 50, "p99_latency_ms": 100}), when=6 + idx) for idx in range(2))
    rows.extend([
        _row("nvidia-smi --query-gpu=clocks.current.graphics,power.draw,temperature.gpu,utilization.gpu --format=csv,noheader,nounits", "2100, 70, 65, 90", when=8),
        _row("nvidia-smi -lgc 300,2200", "Applications clocks set", when=9),
        _row("vllm benchmark", json.dumps({"duration_seconds": 1800, "tokens_per_second": 18,
             "completed_requests": 100, "failed_requests": 0, "p50_latency_ms": 55, "p99_latency_ms": 110}), when=8),
        _row("vllm benchmark", json.dumps({"duration_seconds": 1800, "tokens_per_second": 18,
             "completed_requests": 100, "failed_requests": 0, "p50_latency_ms": 55, "p99_latency_ms": 110}), when=9),
        _row("vllm model load", "model loaded", when=10),
        _row("vllm model unload", "model unloaded", when=11),
        _row("nvidia-smi --query-gpu=clocks.current.graphics,power.draw,temperature.gpu,utilization.gpu --format=csv,noheader,nounits", "2000, 68, 63, 90", when=12),
        _row("nvidia-smi --query-gpu=clocks.current.graphics,power.draw,temperature.gpu,utilization.gpu --format=csv,noheader,nounits", "300, 20, 40, 0", when=13),
        _row("journalctl -k", "kernel log captured", when=14),
        _row("cat /sys/fs/pstore/console-ramoops-0", "", when=15),
        _row("nvidia-smi -lgc 300,2800", "Applications clocks set", when=16),
        _row("nvidia-smi --query-gpu=clocks.current.graphics,power.draw,temperature.gpu,utilization.gpu --format=csv,noheader,nounits", "2100, 20, 40, 0", when=17),
    ])
    # Raw capture interval spans the declared soak; source applies to this OEM/range.
    start = datetime(2026, 10, 3, 9, 59, tzinfo=timezone.utc)
    for idx, row in enumerate(rows):
        row["captured_at"] = (start + timedelta(seconds=idx)).isoformat()
    import hashlib
    source = "HP ZGX Nano G1n supports clock range 300-2200 MHz under driver 580.178.04" * 2
    evidence = _write(tmp_path, "FEATURE-FORUM-GPU-CLOCK-CAP-AB-01", rows,
                      experiment_plan=plan,
                      vendor_sources=[{"url": "https://www.hp.com/support/ZGX", "text": source,
                                       "sha256": hashlib.sha256(source.encode()).hexdigest()}])
    result = verify_gpu(evidence)
    assert result["status"] == "unknown" and "readbacks" in result["reason"], result
    # N/A supported clocks are capability-unavailable, not a policy readback.
    assert _csv_policy(rows[6]) is None
    failed = [dict(row) for row in rows]
    failed[3]["exit"] = 2
    failed[3]["stderr"] = "generic query error"
    result = verify_gpu(_write(tmp_path, "FEATURE-FORUM-GPU-CLOCK-CAP-AB-01", failed,
                               experiment_plan=plan,
                               vendor_sources=[{"url": "https://www.hp.com/support/ZGX", "text": source,
                                                "sha256": hashlib.sha256(source.encode()).hexdigest()}]))
    assert result["status"] == "unknown", result


def test_usb_hid_classifies_update_loss_and_prior_kernel_recovery(tmp_path: Path) -> None:
    rows = [
        _row("dmidecode -t system", "Manufacturer: NVIDIA\nProduct Name: DGX Spark"),
        _row("cat /proc/sys/kernel/random/boot_id", "00000000-0000-0000-0000-000000000001", phase="pre-update", when=1),
        _row("evtest /dev/input/event2", "Event: time 1.0, type 1 (EV_KEY), code 28 (KEY_ENTER), value 1", phase="pre-update", when=1),
        _row("ssh admin@management uname -r", "6.17.0-1025-nvidia", phase="pre-update", when=1),
        _row("uname -r", "6.17.0-1025-nvidia", phase="pre-update", when=1),
        _row("cat /proc/sys/kernel/random/boot_id", "00000000-0000-0000-0000-000000000002", phase="affected", when=2),
        _row("uname -r", "6.17.0-1026-nvidia", phase="affected", when=2),
        _row("lsusb -t", "Class=Human Interface Device, Driver=xhci-hcd", phase="affected", when=3),
        _row("lsmod", "xhci_hcd 123", phase="affected", when=4),
        _row("grep CONFIG_USB_HID /boot/config", "# CONFIG_USB_HID is not set", phase="affected", when=5),
        _row("dpkg --audit", "The following packages have been unpacked but not yet configured:\n linux-modules-nvidia-550-open", phase="affected", when=6),
        _row("journalctl -k -b", "usbhid: Unknown symbol hidinput_connect", phase="affected", when=7),
        _row("cat /proc/sys/kernel/random/boot_id", "00000000-0000-0000-0000-000000000003", phase="recovery", when=8),
        _row("uname -r", "6.17.0-1025-nvidia", phase="recovery", when=8),
        _row("lsusb -t", "Class=Human Interface Device, Driver=usbhid", phase="recovery", when=9),
        _row("lsmod", "usbhid 123\nhid_generic 123", phase="recovery", when=10),
        _row("evtest /dev/input/event2", "Event: time 1.0, type 1 (EV_KEY), code 28 (KEY_ENTER), value 1", phase="recovery", when=11),
        _row("ssh admin@management uname -r", "6.17.0-1025-nvidia", phase="recovery", when=12),
    ]
    for index, row in enumerate(rows):
        row["captured_at"] = f"2026-10-03T10:00:{index:02d}+00:00"
    evidence = _write(tmp_path, "FEATURE-USB-HID-POSTUPDATE-CHECK", rows)
    result = verify_usb(evidence)
    assert result["status"] == "pass", result
    next(row for row in rows if row["cmd"] == "lsmod" and row.get("capture_phase") == "affected")["stdout"] = "usbhid 123\nhid_generic 123"
    result = verify_usb(_write(tmp_path, "FEATURE-USB-HID-POSTUPDATE-CHECK", rows))
    assert result["status"] == "fail", result


def test_wifi_distinguishes_live_host_and_recovers_bounded_roam_trials(tmp_path: Path) -> None:
    rows: list[dict[str, object]] = [
        _row("dmidecode -t system", "Manufacturer: ASUSTeK\nProduct Name: GX10\nBIOS Version: 1.0"),
        _row("uname -r", "6.17.0-1029-nvidia"),
        _row("modinfo mt7925e", "version: 1.0"),
        _row("nmcli --version", "nmcli tool, version 1.48"),
        _row("cat /etc/os-release", 'PRETTY_NAME="NVIDIA DGX OS 7.5.0"'),
        _row("wpa_supplicant -v", "wpa_supplicant v2.10"),
        _row("ethtool -i wlan0", "driver: mt7925e\nversion: 1.0\nfirmware-version: 202401"),
        _row("journalctl -u NetworkManager", "wpa_supplicant: CTRL-EVENT-ASSOC-REJECT WRONG_KEY\nNetworkManager: failed (reason 'no-secrets')"),
        _row("ping -c 1 127.0.0.1", "1 packets received"),
        _row("ssh admin@management uname -r", "", exit=255),
        _row("nmcli connection show Home", "802-11-wireless.ssid: Home\n802-11-wireless.bssid: AA:AA:AA:AA:AA:AA\n802-11-wireless.band: a\n802-11-wireless.autoconnect-retries: 0"),
    ]
    sec = 8
    for prop, value in (("802-11-wireless.bssid", "BB:BB:BB:BB:BB:BB"),
                        ("802-11-wireless.band", "bg"),
                        ("802-11-wireless.autoconnect-retries", "-1")):
        rows.extend([
            _row(f"nmcli connection modify Home {prop} {value}", "" , when=sec),
            _row("nmcli connection up Home --timeout 15", "Connection successfully activated", when=sec + 1),
            _row("iw dev wlan0 link", "Connected to BB:BB:BB:BB:BB:BB\nSSID: Home\nfreq: " + ("2437" if value == "bg" else "5180"), when=sec + 2),
            _row("ip route", "default via 192.0.2.1 dev wlan0" , when=sec + 3),
            _row("ssh admin@management uname -r", "6.17.0-1029-nvidia", when=sec + 4),
        ])
        sec += 5
    rows.extend([
        _row("nmcli connection modify Home 802-11-wireless.bssid AA:AA:AA:AA:AA:AA", "", when=sec),
        _row("nmcli connection modify Home 802-11-wireless.band a", "", when=sec + 1),
        _row("nmcli connection modify Home 802-11-wireless.autoconnect-retries 0", "", when=sec + 2),
        _row("nmcli connection show Home", "802-11-wireless.ssid: Home\n802-11-wireless.bssid: AA:AA:AA:AA:AA:AA\n802-11-wireless.band: a\n802-11-wireless.autoconnect-retries: 0", when=sec + 3),
    ])
    for index, row in enumerate(rows):
        row["captured_at"] = f"2026-10-03T10:00:{index:02d}+00:00"
    source = ("ASUSTeK GX10 BIOS 1.0 kernel 6.17.0-1029-nvidia mt7925e 1.0 "
              "nmcli 1.48 NVIDIA DGX OS 7.5.0 wpa_supplicant 2.10 firmware 202401 " * 3)
    import hashlib
    vendor_sources = [{"url": "https://www.asus.com/support/GX10", "text": source,
                       "sha256": hashlib.sha256(source.encode()).hexdigest()}]
    evidence = _write(tmp_path, "FEATURE-FORUM-WIFI-ISOLATION-01", rows, vendor_sources=vendor_sources)
    initial_ssh = next(row for row in rows if row["cmd"] == "ssh admin@management uname -r" and row["exit"] == 255)
    initial_ssh["stderr"] = "ssh: connect to host management port 22: Connection refused"
    evidence = _write(tmp_path, "FEATURE-FORUM-WIFI-ISOLATION-01", rows,
                      vendor_sources=vendor_sources)
    result = verify_wifi(evidence)
    assert result["status"] == "pass", result
    initial_ssh["stderr"] = ""
    result = verify_wifi(_write(tmp_path, "FEATURE-FORUM-WIFI-ISOLATION-01", rows,
                                vendor_sources=vendor_sources))
    assert result["status"] == "unknown", result
    initial_ssh["stderr"] = "ssh: connect to host management port 22: Connection refused"

    failing = rows.copy()
    local_index = next(i for i, row in enumerate(failing) if "ping" in str(row["cmd"]))
    remote_index = next(i for i, row in enumerate(failing) if "ssh admin@management" in str(row["cmd"]) and row["exit"] == 255)
    failing[local_index] = _row("ping -c 1 127.0.0.1", "", exit=1, when=8)
    failing[remote_index] = _row("ssh admin@management uname -r", "", exit=255, when=9)
    failing[remote_index]["stderr"] = "ssh: connect to host management port 22: Connection refused"
    result = verify_wifi(_write(tmp_path, "FEATURE-FORUM-WIFI-ISOLATION-01", failing, vendor_sources=vendor_sources))
    assert result["status"] == "fail", result
