"""Branch coverage for forum_hardware_subjects: loader, merge, parsers, per-subject predicates.

Every test feeds real small inputs (files in tmp_path, raw argv/stdout text, case dicts) to the
real functions and asserts the returned verdict or parsed facts. No mocks.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import pytest

from tools import forum_hardware_subjects as fhs
from tools.forum_hardware_subjects import (
    _case,
    _case_row,
    _load,
    _parse_shelly_status,
    _references,
    evaluate,
)

FID = "FORUM-00-REALTEK-EEE-DIRECT-LINK"


def _row(name: str, argv: list[str], stdout: str = "", second: int = 1, rc: int = 0,
         **extra: Any) -> dict[str, Any]:
    return {"name": name, "argv": argv, "exit_code": rc, "stdout": stdout, "stderr": "",
            "captured_at": f"2026-10-03T00:00:{second:02d}+00:00", **extra}


def _write(tmp_path: Path, document: Any) -> None:
    (tmp_path / "capture.json").write_text(json.dumps(document), encoding="utf-8")


# --------------------------------------------------------------------------- loader

@pytest.mark.parametrize(("document", "fragment"), [
    ({"schema": 2, "id": FID, "captures": []}, "schema or subject identity"),
    ({"schema": 1, "id": "OTHER", "captures": []}, "schema or subject identity"),
    ([1, 2], "schema or subject identity"),
    ({"schema": 1, "id": FID, "captures": {"a": 1}}, "captures must be a raw command list"),
    ({"schema": 1, "id": FID, "captures": ["row"]}, "raw command row malformed"),
    ({"schema": 1, "id": FID, "captures": [{**_row("a", ["x"]), "exit_code": True}]},
     "raw command row malformed"),
    ({"schema": 1, "id": FID, "captures": [{**_row("a", ["x"]), "captured_at": "yesterday"}]},
     "not ISO-8601"),
    ({"schema": 1, "id": FID, "captures": [{**_row("a", ["x"]), "captured_at": "2026-10-03T00:00:01"}]},
     "lacks timezone"),
    *[({"schema": 1, "id": FID, "captures": [{**_row("a", ["x"]), flag: True}]}, "asserted outcome flag")
      for flag in ("status", "pass", "passed", "healthy", "negative_detected")],
    ({"schema": 1, "id": FID, "captures": [_row("a", ["x"], second=5), _row("b", ["x"], second=5)]},
     "strictly increasing"),
])
def test_load_rejects_malformed_capture_with_fail_verdict(tmp_path: Path, document: Any,
                                                          fragment: str) -> None:
    _write(tmp_path, document)
    loaded, _path, error = _load(FID, tmp_path)
    assert loaded is None
    assert error is not None and error["status"] == "fail" and error["fail"] == 1
    assert fragment in error["reason"]


def test_load_accepts_well_formed_capture_and_z_suffix(tmp_path: Path) -> None:
    rows = [_row("a", ["x"], second=1), {**_row("b", ["x"]), "captured_at": "2026-10-03T00:00:09Z"}]
    _write(tmp_path, {"schema": 1, "id": FID, "captures": rows})
    loaded, _path, error = _load(FID, tmp_path)
    assert error is None and loaded is not None and len(loaded["captures"]) == 2


def test_evaluate_unsupported_subject_is_fail(tmp_path: Path) -> None:
    result = evaluate("NOT-A-SUBJECT", tmp_path)
    assert result["status"] == "fail" and result["files"] == []


# --------------------------------------------------------------------------- merge / counters

def _merge(rows: list[dict[str, Any]], name: str = "direct", regex: str = ".") -> tuple[Any, Any]:
    return _case({"captures": rows}, name, regex)


def test_conflicting_repeated_raw_field_is_reported() -> None:
    rows = [_row("direct", ["ethtool", "-i", "e0"], "driver: r8127\n"),
            _row("direct", ["ethtool", "-i", "e0"], "driver: r8169\n", 2)]
    data, error = _merge(rows)
    assert data is None and error == "case direct repeats conflicting raw field driver"


def test_identical_repeated_field_merges() -> None:
    rows = [_row("direct", ["ethtool", "-i", "e0"], "driver: r8127\n"),
            _row("direct", ["ethtool", "-i", "e0"], "driver: r8127\n", 2)]
    data, error = _merge(rows)
    assert error is None and data is not None and data["driver"] == "r8127"
    assert data["capture_span_s"] == 1.0


def test_counter_samples_become_delta_and_backwards_counter_is_error() -> None:
    forward = [_row("direct", ["ethtool", "-S", "e0"], "link_down_events: 1\n"),
               _row("direct", ["ethtool", "-S", "e0"], "link_down_events: 4\n", 2)]
    data, error = _merge(forward)
    assert error is None and data is not None
    assert data["link_down_events"] == 3 and data["link_resets"] == 3 and data["cycles"] == 3
    backwards = [forward[1], {**forward[0], "captured_at": "2026-10-03T00:00:09+00:00"}]
    data, error = _merge(backwards)
    assert data is None and error == "case direct raw counter moved backwards"


def test_thermal_metrics_take_max_and_fan_takes_min() -> None:
    def sensors(t: int, s: int) -> dict[str, Any]:
        return _row("resident_workload", ["sensors"], f"GPU temp: +{t}°C\n", s)

    def fan(v: int, s: int) -> dict[str, Any]:
        return _row("resident_workload", ["cat", "/sys/class/hwmon/hwmon0/fan1_input"], f"{v}\n", s)

    data, error = _merge([sensors(40, 1), sensors(55, 2), sensors(47, 3), fan(3000, 4), fan(2000, 5),
                          fan(2500, 6)], name="resident_workload")
    assert error is None and data is not None
    assert data["gpu_c"] == 55.0
    assert data["fan_rpm"] == 2000


def test_thermal_metric_outside_thermal_cases_is_not_folded() -> None:
    assert fhs._merge_thermal_metric("direct", "gpu_c", 50.0, {}) is False
    assert fhs._merge_thermal_metric("rollback", "gpu_c", True, {}) is False
    merged: dict[str, Any] = {}
    assert fhs._merge_thermal_metric("rollback", "gpu_c", 50.0, merged) is True and merged == {"gpu_c": 50.0}


def test_ssh_successes_and_traffic_families_are_derived() -> None:
    ping4 = "4 packets transmitted, 4 received, 0% packet loss, time 3ms\n"
    ping6 = "4 packets transmitted, 0 received, 100% packet loss, time 3ms\n"
    rows = [_row("direct", ["ping", "-4", "-c", "4", "h"], ping4),
            _row("direct", ["ping", "-6", "-c", "4", "h"], ping6, 2),
            _row("direct", ["ssh", "host", "true"], "", 3),
            _row("direct", ["ssh", "host", "true"], "", 4)]
    data, error = _merge(rows)
    assert error is None and data is not None
    assert data["ipv4"] == "up" and data["ipv6"] == "down"
    assert data["ipv6_packet_loss"] == 100.0 and data["packet_loss"] == 100.0
    assert data["ssh_reconnects"] == 2


def test_rescue_and_restoration_cases_get_entry_aliases() -> None:
    entry = _row("rescue_entry", ["efibootmgr"], "Boot0003* Rescue Mode\n")
    boot = _row("rescue_boot", ["efibootmgr"], "BootCurrent: 0003\n", 2)
    restored = _row("restoration", ["efibootmgr"], "BootCurrent: 0001\n", 3)
    doc = {"captures": [entry, boot, restored]}
    assert _case(doc, "rescue_entry", "efibootmgr")[0]["entry_id"] == "0003"
    assert _case(doc, "rescue_boot", "efibootmgr")[0]["entry_id"] == "0003"
    assert _case(doc, "restoration", "efibootmgr")[0]["restored_entry"] == "0001"


def test_case_missing_reports_name() -> None:
    assert _case({"captures": []}, "nothing", ".") == (None, "raw case nothing missing")


# --------------------------------------------------------------------------- _case_row

def test_case_row_rejects_wrong_command_and_failed_command() -> None:
    data, error = _case_row("x", _row("x", ["uname", "-r"]), r"dmidecode")
    assert data is None and "not captured by the required command" in error
    failing = {**_row("x", ["dmidecode"]), "exit_code": 1, "stderr": "denied"}
    data, error = _case_row("x", failing, "dmidecode")
    assert data is None and error == "case x command failed: denied"


def test_case_row_failing_ssh_is_kept_as_measurement() -> None:
    row = {**_row("x", ["ssh", "h", "true"]), "exit_code": 255}
    data, error = _case_row("x", row, "ssh")
    assert error is None and data is not None and data["ssh_exit_code"] == 255


@pytest.mark.parametrize(("stdout", "fragment"), [
    ("{not json", "collector JSON is malformed"),
    ('{"a": 1, "a": 2}', "collector JSON is malformed"),
    ("[1]", "collector output is not an object"),
])
def test_case_row_trusted_collector_output_must_be_json_object(stdout: str, fragment: str) -> None:
    row = _row("x", ["python3", "-m", "tools.host_diagnostics"], stdout)
    data, error = _case_row("x", row, "host_diagnostics")
    assert data is None and fragment in error


def test_case_row_collector_object_and_thermal_wrapper() -> None:
    row = _row("x", ["python3", "-m", "tools.host_diagnostics"], '{"k": 1}')
    assert _case_row("x", row, "host_diagnostics") == ({"k": 1}, None)
    thermal = _row("x", ["python3", "-m", "tools.thermal_coverage"], '{"schema": 1}')
    assert _case_row("x", thermal, "thermal_coverage") == ({"thermal_capture": {"schema": 1}}, None)


def test_case_row_shelly_meter_valid_and_malformed() -> None:
    good = '{"sys": {"device": {"id": "shellyplug-1"}}, "switch:0": {"apower": 41.5}}'
    row = _row("x", ["curl", "http://m/rpc/Shelly.GetStatus"], good)
    data, error = _case_row("x", row, "Shelly")
    assert error is None and data["meter_id"] == "shellyplug-1" and data["power_w"] == 41.5
    bad = _row("x", ["curl", "http://m/rpc/Shelly.GetStatus"], "garbage")
    data, error = _case_row("x", bad, "Shelly")
    assert data is None and error == "case x external power meter status malformed"


@pytest.mark.parametrize(("text", "expected"), [
    ("garbage", None),
    ("[1]", None),
    ('{"sys": {"device": {"id": "m"}}, "switch:0": {"apower": -1}}', None),
    ('{"sys": {"device": {"id": "m"}}, "switch:0": {"apower": true}}', None),
    ('{"sys": {"device": {"id": " "}}, "switch:0": {"apower": 3}}', None),
    ('{"switch:0": {"apower": 3}}', None),
    ('{"sys": {"device": {"id": "m"}}}', None),
    ('{"sys": {"device": {"id": "m"}}, "em:0": {"total_act_power": 12}}', {"meter_id": "m", "power_w": 12.0}),
    ('{"sys": {"device": {"id": "m"}}, "switch:0": {}, "em:0": {"total_act_power": 7}}',
     {"meter_id": "m", "power_w": 7.0}),
])
def test_shelly_status_parser(text: str, expected: Any) -> None:
    assert _parse_shelly_status(text) == expected


# --------------------------------------------------------------------------- native parsers

def test_ping_without_summary_line_yields_nothing_and_family_detection() -> None:
    assert fhs._parse_ping(["ping", "h"], "no summary") == {}
    out = "3 packets transmitted, 3 received, 0% packet loss\n"
    assert fhs._parse_ping(["ping", "fe80::1"], out)["network_family"] == "ipv6"
    assert fhs._parse_ping(["ping", "10.0.0.1"], out)["network_family"] == "ipv4"
    assert fhs._parse_ping(["ping", "-6", "h"], out)["network_family"] == "ipv6"


def test_compute_apps_parse_and_reject() -> None:
    assert fhs._parse_compute_app("garbage") is None
    assert fhs._parse_compute_app("123, python, 2 MiB") == {"pid": 123, "name": "python", "bytes": 2 * 1024 * 1024}
    argv = ["nvidia-smi", "--query-compute-apps=pid,name,used_memory", "--format=csv,noheader"]
    assert fhs._parse_compute_apps(argv, "No running processes found") == {"resident_bytes": 0, "resident_processes": 0}
    assert fhs._parse_compute_apps(argv, "1, a, 1 MiB\n2, b, 3 MiB\n") == {
        "resident_bytes": 4 * 1024 * 1024, "resident_processes": 2}
    assert fhs._parse_compute_apps(argv, "1, a, 1 MiB\nbroken line\n") == {}
    assert fhs._parse_compute_apps(argv, "") == {}
    assert fhs._parse_compute_apps(["nvidia-smi"], "1, a, 1 MiB") == {}


def test_benchmark_parsers_and_no_match() -> None:
    argv = ["/usr/bin/vllm", "bench"]
    parsed = fhs._parse_benchmark(argv, "Output token throughput: 41.5 tokens/s\n")
    assert parsed["throughput"] == 41.5 and len(parsed["workload_hash"]) == 64
    assert fhs._parse_benchmark(argv, "nothing useful here") == {}
    assert fhs._parse_benchmark(argv, "Throughput: 0 tokens/s\n") == {}
    assert fhs._parse_benchmark(["ls"], "Throughput: 9 tokens/s\n") == {}
    assert fhs._parse_benchmark(["llama-bench"], "generated tokens/s: 12.5\n")["throughput"] == 12.5


def test_sysfs_fan_and_power_now() -> None:
    assert fhs._parse_sysfs(["cat", "/sys/class/hwmon/hwmon1/fan2_input"], "1800\n") == {"fan_rpm": 1800}
    assert fhs._parse_sysfs(["cat", "/sys/class/hwmon/hwmon1/fan2_input"], "n/a\n") == {}
    power = ["cat", "/sys/class/power_supply/ucsi/power/power_now"]
    assert fhs._parse_sysfs(power, "25000000\n") == {"power_w": 25.0}
    assert fhs._parse_sysfs(power, "x\n") == {}


def test_sensors_parser_labels() -> None:
    out = "SoC temp: +61.5°C\nCPU Core: +50.0°C\nGPU: +70.2°C\nnvme: +40.0°C\n"
    assert fhs._parse_sensors(["sensors"], out) == {"soc_c": 61.5, "cpu_c": 50.0, "gpu_c": 70.2}
    assert fhs._parse_sensors(["cat"], out) == {}
    assert fhs._parse_sensors([], out) == {}


def test_kernel_config_and_module_list() -> None:
    cfg = ["zcat", "/proc/config.gz", "SBSA_WATCHDOG"]
    assert fhs._parse_kernel_config(cfg, "CONFIG_ARM_SBSA_WATCHDOG=m\n") == {"driver_config": "m"}
    assert fhs._parse_kernel_config(cfg, "# CONFIG_ARM_SBSA_WATCHDOG is not set\n") == {}
    assert fhs._parse_kernel_config(["true"], "") == {}
    mods = ["cat", "/proc/modules"]
    assert fhs._parse_module_list(mods, "sbsa_gwdt 16384 0 - Live 0x0\n") == {"module_loaded": True}
    assert fhs._parse_module_list(mods, "other 1 0 - Live 0x0\n\n") == {"module_loaded": False}
    assert fhs._parse_module_list(["cat", "x"], "") == {}


def test_journal_json_boot_id_extraction() -> None:
    argv = ["journalctl", "-o", "json"]
    one = '{"_BOOT_ID": "aaa"}\nnot json\n[1]\n{"_BOOT_ID": "aaa"}\n'
    assert fhs._parse_journal_json(argv, one) == {"boot_id": "aaa"}
    two = '{"_BOOT_ID": "aaa"}\n{"_BOOT_ID": "bbb"}\n'
    assert fhs._parse_journal_json(argv, two) == {}
    assert fhs._parse_journal_json(["journalctl"], one) == {}
    assert fhs._parse_journal_json(["ls", "json"], one) == {}


def test_loginctl_session_classifications() -> None:
    argv = ["loginctl", "show-session", "1"]
    assert fhs._parse_loginctl(argv, "no properties") == {}
    assert fhs._parse_loginctl(["ls"], "State=active\n") == {}
    greeter = fhs._parse_loginctl(argv, "State=active\nType=wayland\nDisplay=:0\nClass=greeter\n")
    assert greeter["session_classification"] == "greeter"
    by_name = fhs._parse_loginctl(argv, "State=active\nType=x11\nDisplay=:0\nName=gdm\n")
    assert by_name["session_classification"] == "greeter"
    tty = fhs._parse_loginctl(argv, "State=active\nType=tty\nDisplay=:0\n")
    assert tty["session_classification"] == "headless"
    nodisplay = fhs._parse_loginctl(argv, "State=active\nType=x11\n")
    assert nodisplay["session_classification"] == "headless" and nodisplay["session_display"] == ""
    active = fhs._parse_loginctl(argv, "State=online\nType=x11\nDisplay=:0\n")
    assert active["session_classification"] == "active_session" and active["session_type"] == "x11"
    closing = fhs._parse_loginctl(argv, "State=closing\nType=x11\nDisplay=:0\n")
    assert closing["session_classification"] == "session_ending"
    other = fhs._parse_loginctl(argv, "State=lingering\nType=x11\nDisplay=:0\n")
    assert "session_classification" not in other


def test_xrandr_and_desktop_journal_and_cmdline_and_route() -> None:
    xr = fhs._parse_xrandr(["xrandr"], "HDMI-1 connected primary (normal left)\nDP-1 disconnected\n")
    assert xr["display_connected"] is True and len(xr["display_outputs"]) == 1
    assert fhs._parse_xrandr(["xrandr"], "DP-1 disconnected\n")["display_connected"] is False
    assert fhs._parse_xrandr(["ls"], "") == {}
    journal = fhs._parse_desktop_journal(["journalctl", "-b"], "Failed to start GNOME Display Manager\nx\n")
    assert journal["incident_log_lines"] == 2 and len(journal["session_failure_signatures"]) == 1
    assert fhs._parse_desktop_journal(["ls"], "") == {}
    assert fhs._parse_cmdline(["cat", "/proc/cmdline"], "ro systemd.unit=rescue.target") == {"rescue_target": True}
    assert fhs._parse_cmdline(["cat", "/proc/cmdline"], "ro quiet") == {"rescue_target": False}
    assert fhs._parse_cmdline(["cat", "x"], "") == {}
    ip = ["ip", "route", "get", "1.1.1.1"]
    assert fhs._parse_route(ip, "1.1.1.1 via 10.0.0.1 dev eth0 src 10.0.0.5") == {"network_route": "dev eth0 via 10.0.0.1"}
    assert fhs._parse_route(ip, "10.0.0.0/24 dev eth0") == {"network_route": "dev eth0"}
    assert fhs._parse_route(ip, "unreachable") == {"network_route": None}
    assert fhs._parse_route(["ls", "route"], "") == {}


def test_lldp_identity_classification() -> None:
    argv = ["lldpctl"]
    assert fhs._parse_lldp(argv, "") == {}
    assert fhs._parse_lldp(["ls"], "SysName: x") == {}
    assert fhs._parse_lldp(argv, "SysName: Intel I225-V peer\n") == {"partner": "Intel I225-V", "topology": "direct"}
    switch = fhs._parse_lldp(argv, "SysName: core\nSysDescr: Netgear managed switch\n")
    assert switch["topology"] == "switch" and "Netgear" in switch["neighbor"]
    assert fhs._parse_lldp(argv, "SysName: mystery-box\n") == {"neighbor": "mystery-box"}


def test_efibootmgr_and_lspci_and_boot_id_and_ssh_and_dpkg() -> None:
    efi = fhs._parse_efibootmgr(["efibootmgr"], "BootCurrent: 000a\nBoot0003* Recovery Mode\n")
    assert efi == {"boot_current": "000A", "rescue_entry_id": "0003"}
    assert fhs._parse_efibootmgr(["efibootmgr"], "nothing") == {}
    assert fhs._parse_efibootmgr(["ls"], "") == {}
    lspci = fhs._parse_lspci(["lspci", "-nnk"], "01:00.0 Ethernet [8086:15F3]\n\tKernel driver in use: igc\n")
    assert lspci["partner"] == "Intel I225-V" and lspci["driver"] == "igc"
    assert fhs._parse_lspci(["ls"], "") == {}
    uuid = "0123456789abcdef0123456789abcdef0123"
    assert fhs._parse_boot_id(["cat", "boot_id"], uuid + "\n") == {"boot_id": uuid}
    assert fhs._parse_boot_id(["cat", "boot_id"], "short") == {}
    assert fhs._parse_boot_id(["ls"], uuid) == {}
    assert fhs._parse_ssh_probe(["ssh", "h"], "") == {"ssh_exit_code": 0}
    assert fhs._parse_ssh_probe(["ssh", "h"], "Permission denied\n") == {"ssh_output": "Permission denied"}
    assert fhs._parse_ssh_probe(["ls"], "") == {}
    assert fhs._parse_dpkg_version(["dpkg-query", "-W", "p"], "gdm3 43.0-1\n") == {"package_version": "43.0-1"}
    assert fhs._parse_dpkg_version(["dpkg-query", "-W", "p"], "") == {}
    assert fhs._parse_dpkg_version(["ls"], "x") == {}


def test_usb_trace_branches() -> None:
    argv = ["trace-cmd", "report"]
    assert fhs._parse_usb_trace(["ls"], "") == {}
    assert fhs._parse_usb_trace(argv, "nothing") == {}
    assert fhs._parse_usb_trace(argv, "xhci_hc_died\n") == {"xhci_resets": 1}
    no_stop = "t 1.000001: uvc_video_start_streaming\nHC died\n"
    assert fhs._parse_usb_trace(argv, no_stop) == {"xhci_resets": 1}
    stop_before = "t 2.000001: uvc_video_stop_streaming\nt 1.000001: uvc_video_start_streaming\n"
    assert fhs._parse_usb_trace(argv, stop_before) == {"xhci_resets": 0}
    full = ("t [1.000001]: uvc_video_start_streaming\n"
            "x S Ci:1:2:3\n"
            "t [3.500001]: uvc_video_stop_streaming\n")
    facts = fhs._parse_usb_trace(argv, full)
    assert facts["ep0_after_stream_count"] == 1 and facts["stream_seconds"] == pytest.approx(2.5)
    untimed = "uvc_video_start_streaming\nuvc_video_stop_streaming\n"
    assert fhs._parse_usb_trace(argv, untimed) == {"xhci_resets": 0, "ep0_after_stream_count": 0}
    assert fhs._trace_timestamp("no stamp here") is None
    assert fhs._trace_timestamp(" 12.345678:") == pytest.approx(12.345678)


def test_modinfo_branches() -> None:
    assert fhs._parse_modinfo(["ls"], "") == {}
    assert fhs._parse_modinfo(["modinfo", "-F"], "x") == {}
    assert fhs._parse_modinfo(["modinfo", "-F", "version", "r8127"], "9.1\n") == {"module_version": "9.1"}
    assert fhs._parse_modinfo(["modinfo", "-F", "bogus", "r8127"], "9.1\n") == {}
    full = fhs._parse_modinfo(["modinfo", "r8127"], "version:   9.1\nsigner:    Canonical\nauthor: x\n")
    assert full == {"module_version": "9.1", "module_signer": "Canonical"}
    multi = fhs._parse_modinfo(["modinfo", "-F", "version", "m"], "a\nb\n")
    assert multi == {}


def test_lsusb_requires_exactly_one_device() -> None:
    line = "Bus 001 Device 004: ID 046d:0825 Logitech Webcam C270\n"
    assert fhs._parse_lsusb(["lsusb"], line) == {"usb_device_id": "046d:0825", "camera": "Logitech Webcam C270"}
    assert fhs._parse_lsusb(["lsusb"], line + line) == {}
    assert fhs._parse_lsusb(["lsusb"], "") == {}
    assert fhs._parse_lsusb(["ls"], line) == {}
    assert fhs._parse_lsusb(["lsusb"], "Bus 001 Device 004: ID 046d:0825 \n") == {}


def test_fwupdmgr_versions_and_no_match() -> None:
    out = ("Name: ConnectX-7\nCurrent Version: 28.1\n"
           "Device name: System Firmware\nVersion: 5.2\n"
           "Name: Unrelated\nVersion: 1\n"
           "Version: 99\n")
    assert fhs._parse_fwupdmgr(["fwupdmgr", "get-devices"], out) == {
        "firmware_versions": {"connectx": "28.1", "uefi": "5.2"}}
    assert fhs._parse_fwupdmgr(["fwupdmgr"], "nothing") == {}
    assert fhs._parse_fwupdmgr(["ls"], out) == {}


def test_nvidia_smi_query_columns() -> None:
    argv = ["nvidia-smi", "--query-gpu=temperature.gpu,power.draw,name", "--format=csv,noheader"]
    assert fhs._parse_nvidia_smi(argv, "61, 33.5, GB10\n") == {
        "temperature_c": 61.0, "power_w": 33.5, "name": "GB10"}
    assert fhs._parse_nvidia_smi(["nvidia-smi"], "x") == {}


def test_helpers_number_and_text() -> None:
    assert fhs._number({"a": 3}, "a", 5) is None
    assert fhs._number({"a": "3"}, "a") is None
    assert fhs._number({"a": 3}, "a", 3) == 3.0
    assert fhs._text({"a": "  x "}, "a") == "x"
    assert fhs._text({"a": " "}, "a") is None
    assert fhs._text({"a": 1}, "a") is None


# --------------------------------------------------------------------------- vendor references

_SRC = ("ASUS Product GX10 BIOS B1 kernel 6.17.0 NVMe and RAS diagnostics apply to this exact "
        "supported stack; retain caller-supplied source provenance.")


def _ref(text: str = _SRC, url: str = "https://www.asus.com/support/") -> dict[str, Any]:
    return {"url": url, "text": text, "sha256": hashlib.sha256(text.encode()).hexdigest()}


def _identity_row() -> list[dict[str, Any]]:
    return [_row("identity", ["dmidecode"], "Manufacturer: ASUS\nProduct Name: Product GX10\nBIOS Version: B1\n"),
            _row("identity", ["uname", "-r"], "6.17.0\n", 2)]


@pytest.mark.parametrize(("sources", "fragment"), [
    (None, "source text and digest missing"),
    ([], "source text and digest missing"),
    (["row"], "vendor source row malformed"),
    ([{"text": 5}], "vendor source row malformed"),
    ([{**_ref(), "sha256": "0" * 64}], "digest mismatch"),
    ([_ref(url="https://evil.example/x")], "not on an allowed OEM/vendor domain"),
    ([{**_ref(), "url": 7}], "not on an allowed OEM/vendor domain"),
    ([_ref("short text")], "lacks substantive compatibility detail"),
])
def test_references_reject_bad_sources(sources: Any, fragment: str) -> None:
    ok, reason = _references({"captures": _identity_row(), "vendor_sources": sources})
    assert ok is False and fragment in reason


def test_references_identity_tuple_must_be_complete_and_cited() -> None:
    incomplete = {"captures": [_row("identity", ["uname", "-r"], "6.17.0\n")], "vendor_sources": [_ref()]}
    ok, reason = _references(incomplete)
    assert ok is False and "identity tuple incomplete: manufacturer, product_name, bios_version" in reason
    uncited = {"captures": _identity_row(), "vendor_sources": [_ref(_SRC.replace("GX10", "ZZ99"))]}
    ok, reason = _references(uncited)
    assert ok is False and "does not cite the captured OEM/version tuple" in reason
    ok, reason = _references({"captures": _identity_row(), "vendor_sources": [_ref()]})
    assert (ok, reason) == (True, None)
    with_module = _identity_row() + [_row("identity", ["modinfo", "-F", "version", "m"], "9.9.9\n", 3)]
    ok, reason = _references({"captures": with_module, "vendor_sources": [_ref()]})
    assert ok is False and "does not cite" in reason


# --------------------------------------------------------------------------- GX10 read integrity

GX10 = "FORUM-02-GX10-READ-INTEGRITY"
_GX_SRC = ("ASUS Product GX10 BIOS B1 kernel 6.17.0-1032-nvidia NVMe and RAS diagnostics apply to this "
           "exact supported stack; retain caller-supplied source provenance.")


def _read_row(name: str, target: Path, expected: str, second: int) -> dict[str, Any]:
    from tools.read_integrity import inspect

    argv = ["python3", "-m", "tools.read_integrity", str(target), "--offset", "0",
            "--length", "4096", "--sha256", expected, "--repeats", "1"]
    measured = inspect(str(target), 0, 4096, expected, 1)
    rc = {"pass": 0, "fail": 1, "could_not_run": 2}[measured["status"]]
    return {**_row(name, argv, json.dumps(measured), second, rc), "elapsed_ms": 1.0}


def _gx10(tmp_path: Path) -> tuple[Path, dict[str, Any]]:
    """A passing GX10 evidence directory under tmp_path/ev; returns (directory, document)."""
    ev = tmp_path / "ev"
    ev.mkdir()
    healthy, altered = ev / "healthy.bin", ev / "altered.bin"
    healthy.write_bytes(b"a" * 4096)
    altered.write_bytes(b"b" + b"a" * 4095)
    digest = hashlib.sha256(healthy.read_bytes()).hexdigest()
    document = {"schema": 1, "id": GX10, "captures": [
        _read_row("healthy", healthy, digest, 1),
        _read_row("altered", altered, digest, 2),
        _row("external_reference", ["ssh", "trusted-head", "sha256sum", "w.safetensors"],
             f"{digest}  w.safetensors\n", 3),
        _row("nvme_health", ["nvme", "smart-log", "/dev/nvme0", "-o", "json"],
             '{"critical_warning":0,"media_errors":0}\n', 4),
        _row("ras_signals", ["journalctl", "-k", "--grep=ras|edac|bert"], "No matching entries\n", 5),
        _row("stack_identity", ["dmidecode", "-t", "system"],
             "Manufacturer: ASUS\nProduct Name: Product GX10\nBIOS Version: B1\n", 6),
        _row("stack_identity", ["uname", "-r"], "6.17.0-1032-nvidia\n", 7),
    ], "vendor_sources": [_ref(_GX_SRC)]}
    snapshot = {"checks": {
        "storage": {
            "root_mounts": {"status": "ok", "value": [{"target": "/", "options": "rw", "read_only": False}]},
            "nvme_inventory": {"status": "ok", "stdout": json.dumps({"Devices": [
                {"DevicePath": "/dev/nvme0n1", "SerialNumber": "s1"}]})}},
        "kernel_signals": {"status": "ok", "stdout": ""}}}
    (ev / "nvme-snapshot.json").write_text(json.dumps(snapshot), encoding="utf-8")
    return ev, document


def _gx_eval(ev: Path, document: dict[str, Any]) -> dict[str, Any]:
    (ev / "capture.json").write_text(json.dumps(document), encoding="utf-8")
    return evaluate(GX10, ev)


def _named(document: dict[str, Any], name: str) -> dict[str, Any]:
    return next(row for row in document["captures"] if row["name"] == name)


def test_gx10_baseline_passes(tmp_path: Path) -> None:
    ev, document = _gx10(tmp_path)
    result = _gx_eval(ev, document)
    assert result["status"] == "pass", result
    assert result["files"][1].endswith("nvme-snapshot.json")


def _drop_healthy(ev: Path, doc: dict[str, Any]) -> None:
    doc["captures"] = [row for row in doc["captures"] if row["name"] != "healthy"]


def _not_read_integrity(ev: Path, doc: dict[str, Any]) -> None:
    row = _named(doc, "healthy")
    row["argv"] = [("tools.other" if a == "tools.read_integrity" else a) for a in row["argv"]]


def _no_offset(ev: Path, doc: dict[str, Any]) -> None:
    row = _named(doc, "healthy")
    row["argv"] = [a for a in row["argv"] if a != "--offset"]


def _wrong_exit(ev: Path, doc: dict[str, Any]) -> None:
    _named(doc, "healthy")["exit_code"] = 1


def _target_gone(ev: Path, doc: dict[str, Any]) -> None:
    (ev / "healthy.bin").unlink()


def _target_outside(ev: Path, doc: dict[str, Any]) -> None:
    outside = ev.parent / "outside.bin"
    outside.write_bytes(b"a" * 4096)
    digest = hashlib.sha256(outside.read_bytes()).hexdigest()
    doc["captures"][0] = _read_row("healthy", outside, digest, 1)


def _no_elapsed(ev: Path, doc: dict[str, Any]) -> None:
    del _named(doc, "healthy")["elapsed_ms"]


def _tampered_output(ev: Path, doc: dict[str, Any]) -> None:
    row = _named(doc, "healthy")
    payload = json.loads(row["stdout"])
    payload["buffered_sha256"] = ["0" * 64]
    row["stdout"] = json.dumps(payload)


def _target_is_directory(ev: Path, doc: dict[str, Any]) -> None:
    (ev / "dir").mkdir()
    row = _named(doc, "healthy")
    row["argv"][row["argv"].index("tools.read_integrity") + 1] = str(ev / "dir")
    row["stdout"] = json.dumps({"status": "could_not_run"})
    row["exit_code"] = 2


def _healthy_reference_wrong(ev: Path, doc: dict[str, Any]) -> None:
    doc["captures"][0] = _read_row("healthy", ev / "healthy.bin", "0" * 64, 1)


def _altered_matches(ev: Path, doc: dict[str, Any]) -> None:
    digest = hashlib.sha256((ev / "healthy.bin").read_bytes()).hexdigest()
    doc["captures"][1] = _read_row("altered", ev / "healthy.bin", digest, 2)


def _same_staging_file(ev: Path, doc: dict[str, Any]) -> None:
    doc["captures"][1] = _read_row("altered", ev / "healthy.bin", "0" * 64, 2)


def _bad_length_argv(ev: Path, doc: dict[str, Any]) -> None:
    row = _named(doc, "healthy")
    row["argv"][row["argv"].index("--length") + 1] = "100"
    row["stdout"] = json.dumps({"status": "pass"})
    row["exit_code"] = 0


def _no_sources(ev: Path, doc: dict[str, Any]) -> None:
    del doc["vendor_sources"]


def _no_nvme_health(ev: Path, doc: dict[str, Any]) -> None:
    doc["captures"] = [row for row in doc["captures"] if row["name"] != "nvme_health"]


def _empty_ras(ev: Path, doc: dict[str, Any]) -> None:
    _named(doc, "ras_signals")["stdout"] = ""


def _local_reference(ev: Path, doc: dict[str, Any]) -> None:
    _named(doc, "external_reference")["argv"][1] = "localhost"


def _nvme_malformed(ev: Path, doc: dict[str, Any]) -> None:
    _named(doc, "nvme_health")["stdout"] = "not json\n"


def _nvme_warning(ev: Path, doc: dict[str, Any]) -> None:
    _named(doc, "nvme_health")["stdout"] = '{"critical_warning":1,"media_errors":0}\n'


def _nvme_array(ev: Path, doc: dict[str, Any]) -> None:
    _named(doc, "nvme_health")["stdout"] = "[1]\n"


def _digest_mismatch(ev: Path, doc: dict[str, Any]) -> None:
    _named(doc, "external_reference")["stdout"] = "0" * 64 + "  w\n"


@pytest.mark.parametrize(("mutate", "status", "fragment"), [
    (_drop_healthy, "unknown", "raw case healthy missing"),
    (_not_read_integrity, "unknown", "is not a read_integrity invocation"),
    (_no_offset, "unknown", "lacks literal bounded argv/output"),
    (_wrong_exit, "unknown", "exit status disagrees with its measured outcome"),
    (_target_gone, "unknown", "target unavailable"),
    (_target_outside, "fail", "escapes the evidence directory"),
    (_no_elapsed, "unknown", "elapsed time absent"),
    (_tampered_output, "fail", "differs from fresh read-only replay"),
    (_target_is_directory, "unknown", "replay unavailable"),
    (_healthy_reference_wrong, "fail", "healthy external-reference control disagrees"),
    (_altered_matches, "fail", "altered-byte negative control was not detected"),
    (_same_staging_file, "fail", "two distinct staging files"),
    (_bad_length_argv, "unknown", "multiples of 4096"),
    (_no_sources, "unknown", "source text and digest missing"),
    (_no_nvme_health, "unknown", "raw case nvme_health missing"),
    (_empty_ras, "unknown", "ras_signals raw output missing"),
    (_local_reference, "unknown", "separately named host"),
    (_nvme_malformed, "fail", "NVMe health output is malformed"),
    (_nvme_warning, "fail", "critical warning or media error"),
    (_nvme_array, "fail", "critical warning or media error"),
    (_digest_mismatch, "fail", "external-node digest does not match"),
])
def test_gx10_mutations_yield_specific_verdicts(tmp_path: Path, mutate: Any, status: str,
                                                fragment: str) -> None:
    ev, document = _gx10(tmp_path)
    mutate(ev, document)
    result = _gx_eval(ev, document)
    assert result["status"] == status and fragment in result["reason"], result


def test_gx10_nvme_snapshot_failure_modes(tmp_path: Path) -> None:
    ev, document = _gx10(tmp_path)
    snap = ev / "nvme-snapshot.json"
    snapshot = json.loads(snap.read_text(encoding="utf-8"))
    snap.write_bytes(b" " * (4 * 1024 * 1024 + 1))
    assert "exceeds the 4 MiB" in _gx_eval(ev, document)["reason"]
    snap.write_text("{broken", encoding="utf-8")
    assert "snapshot unavailable" in _gx_eval(ev, document)["reason"]
    snap.unlink()
    assert _gx_eval(ev, document)["status"] == "unknown"
    snapshot["checks"]["storage"]["root_mounts"]["value"][0]["read_only"] = True
    snap.write_text(json.dumps(snapshot), encoding="utf-8")
    failed = _gx_eval(ev, document)
    assert failed["status"] == "fail" and "read-only root mount" in failed["reason"]
    snapshot["checks"]["storage"]["root_mounts"]["value"][0]["read_only"] = False
    snapshot["checks"]["storage"]["nvme_inventory"] = {"status": "could_not_run"}
    snap.write_text(json.dumps(snapshot), encoding="utf-8")
    incomplete = _gx_eval(ev, document)
    assert incomplete["status"] == "unknown" and "inventory incomplete" in incomplete["reason"]


def test_gx10_snapshot_without_checks_is_unknown_not_a_crash(tmp_path: Path) -> None:
    ev, document = _gx10(tmp_path)
    (ev / "nvme-snapshot.json").write_text("{}", encoding="utf-8")
    result = _gx_eval(ev, document)
    assert result["status"] == "unknown" and "inventory incomplete" in result["reason"]
    assert "snapshot checks missing" in result["reason"]


# --------------------------------------------------------------------------- CX7 / thermal predicates

def _tcap(gpu: float | None = 50, cpu: float | None = 50, soc: float | None = 50) -> dict[str, Any]:
    zones = [{"type": {"value": kind}, "temperature": {"status": "ok", "value": value * 1000}}
             for kind, value in (("gpu", gpu), ("cpu", cpu), ("soc", soc)) if value is not None]
    return {"schema": 1, "status": "observed", "could_not_run": 0, "thermal_zones": zones, "hwmon": []}


_LIMITS = "GPU maximum 90 C. CPU max 95 C. SoC limit 100 C."
_FIRMWARE = {"uefi": "U1", "ec": "E1", "soc": "S1", "pd": "P1", "connectx": "C1"}


def _vendor(text: str) -> dict[str, Any]:
    return {"vendor_sources": [{"text": text, "url": "https://www.asus.com/x",
                                "sha256": hashlib.sha256(text.encode()).hexdigest()}]}


def test_thermal_limits_parse_per_channel() -> None:
    assert fhs._thermal_limits(_LIMITS) == {"gpu_c": 90.0, "cpu_c": 95.0, "soc_c": 100.0}
    assert fhs._thermal_limits("nothing sourced") == {}


def test_thermal_coverage_observation_shapes() -> None:
    assert fhs._thermal_coverage_observation({"thermal_captures": [_tcap(60, 55, 40), _tcap(65, 50, 45)]}) == {
        "gpu_c": 65.0, "cpu_c": 55.0, "soc_c": 45.0}
    assert fhs._thermal_coverage_observation({"thermal_captures": ["not a dict"]}) is None
    assert fhs._thermal_coverage_observation({"thermal_captures": [{"thermal_zones": 1}]}) is None
    assert fhs._thermal_coverage_observation({"thermal_captures": [_tcap(None, None, None)]}) is None
    assert fhs._thermal_coverage_observation({"thermal_captures": []}) is None
    assert fhs._thermal_coverage_observation({"output": 5}) is None
    # single capture embedded as JSON text in the raw output
    assert fhs._thermal_coverage_observation({"output": json.dumps(_tcap(61, 62, 63))}) == {
        "gpu_c": 61.0, "cpu_c": 62.0, "soc_c": 63.0}


def test_thermal_capture_json_stream_scanning() -> None:
    good = _tcap()
    assert fhs._thermal_capture({"output": "  \n" + json.dumps({"schema": 2}) + "\n" + json.dumps(good)}) == good
    assert fhs._thermal_capture({"output": json.dumps({"schema": 2}) + "  \n \n"}) is None
    assert fhs._thermal_capture({"output": ""}) is None
    assert fhs._thermal_capture({"output": "{broken"}) is None
    assert fhs._thermal_capture({"output": json.dumps({**good, "status": "partial"})}) is None
    assert fhs._thermal_capture({"output": '{"a": NaN}'}) is None


def test_thermal_zone_and_hwmon_value_extraction() -> None:
    channels = {"gpu": "gpu_c", "cpu": "cpu_c", "soc": "soc_c"}
    assert fhs._thermal_zone_values(["x"], channels) is None
    assert fhs._thermal_zone_values([{"type": "gpu", "temperature": 1}], channels) == {}
    hw = [{"temperature_inputs": [
        {"label": {"value": "GPU core"}, "status": "ok", "value": 71},
        {"label": {"value": "CPU"}, "status": "ok", "value": 70500},
        {"label": "plain", "status": "ok", "value": 5},
        {"label": {"value": "SoC"}, "status": "bad", "value": 5}]}]
    assert fhs._thermal_hwmon_values(hw, channels) == {"gpu_c": 71.0, "cpu_c": 70.5}
    assert fhs._thermal_hwmon_values(["x"], channels) is None
    assert fhs._thermal_hwmon_values([{"temperature_inputs": "x"}], channels) is None
    assert fhs._thermal_hwmon_values([{"temperature_inputs": ["x"]}], channels) is None
    capture = {**_tcap(), "hwmon": hw}
    assert fhs._thermal_capture_observation(capture)["gpu_c"] == 71.0
    assert fhs._thermal_capture_observation({**_tcap(), "hwmon": ["x"]}) is None
    assert fhs._thermal_capture_observation({**_tcap(), "thermal_zones": ["x"]}) is None
    assert fhs._thermal_capture_observation({"hwmon": []}) is None


def test_thermal_value_validation() -> None:
    assert fhs._thermal_value("x") is None
    assert fhs._thermal_value({"status": "bad", "value": 1}) is None
    assert fhs._thermal_value({"status": "ok", "value": True}) is None
    assert fhs._thermal_value({"status": "ok", "value": "5"}) is None
    assert fhs._thermal_value({"status": "ok", "value": 45}) == 45.0
    assert fhs._thermal_value({"status": "ok", "value": 45000}) == 45.0


def test_cx7_oem_tuple_branches() -> None:
    identity = {"firmware_versions": dict(_FIRMWARE)}
    doc = {**_vendor(_LIMITS + " firmware U1 E1 S1 P1 C1 pad pad pad pad pad pad pad pad pad pad pad"),
           "captures": [_row("identity", ["dmidecode"],
                             "Manufacturer: ASUS\nProduct Name: P\nBIOS Version: B\n"),
                        _row("identity", ["uname", "-r"], "6.1\n", 2)]}
    assert fhs._check_cx7_oem_tuple(doc, identity)[0] == "unknown"  # identity tuple not cited
    doc_ok = {**_vendor(_LIMITS + " ASUS P B 6.1 firmware U1 E1 S1 P1 C1 pad pad pad pad pad pad pad pad"),
              "captures": doc["captures"]}
    assert fhs._check_cx7_oem_tuple(doc_ok, identity)[0] == "pass"
    assert "firmware tuple" in fhs._check_cx7_oem_tuple(doc_ok, {"firmware_versions": {"uefi": "U1"}})[1]
    assert "firmware tuple" in fhs._check_cx7_oem_tuple(doc_ok, {})[1]
    cited = {"firmware_versions": {**_FIRMWARE, "ec": "E999"}}
    status, reason = fhs._check_cx7_oem_tuple(doc_ok, cited)
    assert status == "unknown" and "does not cite the captured full firmware tuple" in reason


def test_cx7_thermal_branches() -> None:
    base = {"thermal_captures": [_tcap(50, 50, 50)]}
    ok = {"thermal_captures": [_tcap(60, 60, 60)]}
    doc = _vendor(_LIMITS)
    assert fhs._check_cx7_thermal(doc, base, ok)[0] == "pass"
    assert fhs._check_cx7_thermal(doc, {}, ok)[0] == "unknown"
    assert fhs._check_cx7_thermal(doc, base, {})[0] == "unknown"
    assert "lacks channel-specific" in fhs._check_cx7_thermal(_vendor("no limits at all here"), base, ok)[1]
    missing = {"thermal_captures": [_tcap(60, 60, None)]}
    assert "soc_c" in fhs._check_cx7_thermal(doc, base, missing)[1]
    hot = {"thermal_captures": [_tcap(90, 60, 60)]}
    status, reason = fhs._check_cx7_thermal(doc, base, hot)
    assert status == "fail" and "gpu_c" in reason


def _cx7_cases() -> dict[str, dict[str, Any]]:
    th = {"thermal_captures": [_tcap(60, 60, 60)]}
    return {
        "identity": {"firmware_versions": dict(_FIRMWARE)},
        "symptom": {"output": "mlx5: Cable removal detected\n"},
        "baseline": {**th, "power_w": 40.0, "meter_id": "m1", "fan_rpm": 3000, "output": "ok"},
        "candidate": {**th, "power_w": 41.0, "meter_id": "m1", "fan_rpm": 3100, "output": "ok",
                      "pci_state": "present", "network_state": "up"},
        "rollback": {"fan_rpm": 3000, "pci_state": "present", "network_state": "up"},
    }


def _cx7_doc() -> dict[str, Any]:
    text = _LIMITS + " ASUS P B 6.1 firmware U1 E1 S1 P1 C1 pad pad pad pad pad pad pad pad pad pad"
    return {**_vendor(text), "captures": [
        _row("identity", ["dmidecode"], "Manufacturer: ASUS\nProduct Name: P\nBIOS Version: B\n"),
        _row("identity", ["uname", "-r"], "6.1\n", 2)]}


def test_cx7_full_predicate_and_each_failure_edge() -> None:
    document = _cx7_doc()
    assert fhs._check_cx7(document, _cx7_cases())[0] == "pass"

    def variant(mutate: Any) -> tuple[str, str]:
        cases = _cx7_cases()
        mutate(cases)
        return fhs._check_cx7(document, cases)

    status, reason = variant(lambda c: c["symptom"].update(output="quiet"))
    assert status == "fail" and "hotplug symptom" in reason
    status, reason = variant(lambda c: c["baseline"].update(thermal_captures=[]))
    assert status == "unknown" and "thermal_coverage" in reason
    status, reason = variant(lambda c: c["baseline"].pop("power_w"))
    assert status == "unknown" and "same identified external meter" in reason
    status, reason = variant(lambda c: c["candidate"].update(meter_id="m2"))
    assert status == "unknown"
    status, reason = variant(lambda c: c["candidate"].update(output="Cable removal again"))
    assert status == "fail" and "repeats the CX7" in reason
    status, reason = variant(lambda c: c["rollback"].pop("fan_rpm"))
    assert status == "unknown" and "fan tachometer" in reason
    status, reason = variant(lambda c: c["rollback"].pop("pci_state"))
    assert status == "unknown" and "recovery after rollback" in reason
    status, reason = variant(lambda c: c["rollback"].update(network_state="down"))
    assert status == "fail" and "did not recover" in reason
    status, reason = variant(lambda c: c["candidate"].pop("pci_state"))
    assert status == "unknown" and "candidate PCIe" in reason
    status, reason = variant(lambda c: c["candidate"].update(network_state="down"))
    assert status == "fail" and "candidate CX7 network link is not up" in reason
    bad_doc = {**document, "vendor_sources": []}
    assert fhs._check_cx7(bad_doc, _cx7_cases())[0] == "unknown"


def _thermal_cases() -> dict[str, dict[str, Any]]:
    return {
        "resident_workload": {"capture_span_s": 600.0, "throughput": 12.0, "workload_hash": "a" * 64,
                              "resident_bytes": 1024.0, "meter_id": "m", "power_w": 50.0, "fan_rpm": 3000.0,
                              "thermal_captures": [_tcap(70, 60, 60)]},
        "idle_control": {"resident_bytes": 0, "meter_id": "m", "power_w": 20.0},
        "rollback": {"resident_bytes": 0, "thermal_captures": [_tcap(40, 40, 40)]},
    }


def test_gb10_thermal_predicate_and_each_edge() -> None:
    document = _vendor(_LIMITS)
    assert fhs._check_thermal(document, _thermal_cases())[0] == "pass"

    def variant(mutate: Any, doc: dict[str, Any] = document) -> tuple[str, str]:
        cases = _thermal_cases()
        mutate(cases)
        return fhs._check_thermal(doc, cases)

    assert "five-minute" in variant(lambda c: c["resident_workload"].update(capture_span_s=10.0))[1]
    assert "throughput" in variant(lambda c: c["resident_workload"].update(workload_hash="zz"))[1]
    assert "GPU process inventory" in variant(lambda c: c["idle_control"].update(resident_bytes=5))[1]
    assert "same identified external meter" in variant(lambda c: c["idle_control"].update(meter_id="x"))[1]
    assert "fan tachometer" in variant(lambda c: c["rollback"].update(resident_bytes=9))[1]
    assert "series missing" in variant(lambda c: c["rollback"].update(thermal_captures=[]))[1]
    status, reason = variant(lambda c: None, {"vendor_sources": [{"text": "no limits"}, "junk"]})
    assert status == "unknown" and "OEM limit or raw gpu_c" in reason
    status, reason = variant(lambda c: c["rollback"].update(thermal_captures=[_tcap(95, 40, 40)]))
    assert status == "fail" and "gpu_c" in reason
    status, reason = variant(lambda c: c["resident_workload"].update(thermal_captures=[_tcap(70, 60, None)]))
    assert status == "unknown" and "soc_c" in reason
    status, reason = variant(lambda c: c["resident_workload"].update(throughput=None))
    assert status == "unknown"


# --------------------------------------------------------------------------- watchdog

BOOT_A = "11111111-1111-1111-1111-111111111111"
BOOT_B = "22222222-2222-2222-2222-222222222222"


def _profile(boot: str = BOOT_A, bootstatus: Any = "0x20", modules: str = "sbsa_gwdt 1 0 - Live 0x0",
             **extra: Any) -> dict[str, Any]:
    return {"state": {"proc/sys/kernel/random/boot_id": {"status": "read", "value": boot},
                      "proc/modules": {"status": "read", "value": modules}},
            "watchdog": {"watchdog0": {"identity": {"status": "read", "value": "SBSA"},
                                       "timeout": {"status": "read", "value": "30"},
                                       "bootstatus": {"status": "read", "value": bootstatus}}},
            **extra}


def _wd_cases() -> dict[str, dict[str, Any]]:
    return {"ownership": {"owner_pids": [321]},
            "watchdog": _profile(BOOT_A, driver_config="y"),
            "boot_logs": {"boot_id": BOOT_A},
            "recovery": _profile(BOOT_B, "0x20")}


def test_watchdog_predicate_each_edge() -> None:
    assert fhs._check_watchdog(_wd_cases())[0] == "pass"

    def variant(mutate: Any) -> tuple[str, str]:
        cases = _wd_cases()
        mutate(cases)
        return fhs._check_watchdog(cases)

    assert "ownership is ambiguous" in variant(lambda c: c["ownership"].update(owner_pids=[1, 2]))[1]
    assert "ownership is ambiguous" in variant(lambda c: c["ownership"].update(owner_pids=[0]))[1]
    assert "ownership is ambiguous" in variant(lambda c: c["ownership"].update(owner_pids="x"))[1]
    assert "unique watchdog device" in variant(lambda c: c["watchdog"].update(watchdog={}))[1]
    assert "does not distinguish" in variant(lambda c: c["watchdog"].update(driver_config="n"))[1]
    status, reason = variant(lambda c: c["watchdog"].update(driver_config="m", state={
        **c["watchdog"]["state"], "proc/modules": {"status": "read", "value": "other 1 0 - Live 0x0"}}))
    assert status == "fail" and "configured as a module but is not loaded" in reason
    assert variant(lambda c: c["watchdog"].update(driver_config="m"))[0] == "pass"
    status, reason = variant(lambda c: c["boot_logs"].update(boot_id=BOOT_B))
    assert status == "fail" and "different boot identities" in reason


def test_watchdog_recovery_each_edge() -> None:
    assert fhs._check_watchdog_recovery(BOOT_A, _profile(BOOT_B, "0x20"))[0] == "pass"
    assert fhs._check_watchdog_recovery(BOOT_A, _profile(BOOT_B, "32"))[0] == "pass"
    status, reason = fhs._check_watchdog_recovery(BOOT_A, {})
    assert status == "unknown" and reason.startswith("watchdog recovery ")
    status, reason = fhs._check_watchdog_recovery(BOOT_A, _profile(BOOT_A, "0x20"))
    assert status == "fail" and "distinct boot identity" in reason
    nostatus = _profile(BOOT_B)
    nostatus["watchdog"]["watchdog0"]["bootstatus"] = {"status": "denied"}
    assert "lacks read-only watchdog-reset bootstatus" in fhs._check_watchdog_recovery(BOOT_A, nostatus)[1]
    assert "not a numeric flag set" in fhs._check_watchdog_recovery(BOOT_A, _profile(BOOT_B, "zz"))[1]
    status, reason = fhs._check_watchdog_recovery(BOOT_A, _profile(BOOT_B, "0x0"))
    assert status == "fail" and "does not report the watchdog reset flag" in reason


def test_watchdog_profile_validation_edges() -> None:
    assert fhs._watchdog_profile(_profile())[2] is None
    bad_boot = _profile()
    bad_boot["state"]["proc/sys/kernel/random/boot_id"] = {"status": "denied"}
    assert fhs._watchdog_profile(bad_boot)[2] == "observation lacks boot identity"
    malformed = _profile()
    malformed["watchdog"] = {"w": "text"}
    assert fhs._watchdog_profile(malformed)[2] == "device record malformed"
    no_identity = _profile()
    no_identity["watchdog"]["watchdog0"]["identity"] = {"status": "read", "value": "  "}
    assert "identity is unavailable" in fhs._watchdog_profile(no_identity)[2]
    no_timeout = _profile()
    no_timeout["watchdog"]["watchdog0"]["timeout"] = {"status": "read", "value": "abc"}
    assert "timeout is unavailable" in fhs._watchdog_profile(no_timeout)[2]


# --------------------------------------------------------------------------- realtek

def _rt_cases() -> dict[str, dict[str, Any]]:
    stage = {"module_version": "9.1", "module_signer": "Canonical", "driver": "r8127", "link": "up",
             "ssh_exit_code": 0}
    return {"before": {"boot_id": "b0", "pci_id": "10ec:8127", "driver": "r8169"},
            "warm_after": {**stage, "boot_id": "b1"}, "cold_after": {**stage, "boot_id": "b2"},
            "alternate_nic": {"pci_id": "8086:15f3"}, "driver_absent": {"pci_id": "10ec:8127"},
            "rollback": {"driver": "r8169", "ssh_exit_code": 0}}


def test_realtek_predicate_each_edge() -> None:
    assert fhs._check_realtek(_rt_cases())[0] == "pass"

    def variant(mutate: Any) -> tuple[str, str]:
        cases = _rt_cases()
        mutate(cases)
        return fhs._check_realtek(cases)

    assert variant(lambda c: c["cold_after"].pop("boot_id"))[0] == "unknown"
    status, reason = variant(lambda c: c["cold_after"].update(boot_id="b1"))
    assert status == "fail" and "three distinct boots" in reason
    assert "version or signer" in variant(lambda c: c["warm_after"].pop("module_signer"))[1]
    assert "not the supported r8127" in variant(lambda c: c["warm_after"].update(driver="r8169"))[1]
    assert "link did not recover" in variant(lambda c: c["cold_after"].update(link="down"))[1]
    assert "driver-absent" in variant(lambda c: c["driver_absent"].update(driver="r8127"))[1]
    assert "driver-absent" in variant(lambda c: c["driver_absent"].pop("pci_id"))[1]
    status, reason = variant(lambda c: c["warm_after"].pop("ssh_exit_code"))
    assert status == "unknown" and "after warm reboot" in reason
    status, reason = variant(lambda c: c["cold_after"].update(ssh_exit_code=255))
    assert status == "fail" and "after cold reboot" in reason
    assert "reused the target PCI" in variant(lambda c: c["alternate_nic"].update(pci_id="10ec:8127"))[1]
    status, reason = variant(lambda c: c["rollback"].pop("ssh_exit_code"))
    assert status == "unknown" and "after rollback" in reason
    assert "rollback did not restore" in variant(lambda c: c["rollback"].update(driver="r8127"))[1]
    assert "rollback did not restore" in variant(lambda c: c["rollback"].update(ssh_exit_code=1))[1]


# --------------------------------------------------------------------------- desktop

def _desk_cases() -> dict[str, dict[str, Any]]:
    return {
        "incident": {"ssh_exit_code": 0, "session_failure_signatures": ["gnome"], "package_version": "1.0"},
        "control": {"session_classification": "active_session", "display_connected": True, "ssh_exit_code": 0},
        "recovery": {"session_classification": "active_session", "display_connected": True,
                     "package_version": "2.0"},
        "rollback": {"package_version": "1.0", "ssh_exit_code": 0},
    }


def test_desktop_predicate_each_edge() -> None:
    assert fhs._check_desktop(_desk_cases())[0] == "pass"

    def variant(mutate: Any) -> tuple[str, str]:
        cases = _desk_cases()
        mutate(cases)
        return fhs._check_desktop(cases)

    assert "SSH probe missing" in variant(lambda c: c["incident"].pop("ssh_exit_code"))[1]
    assert "reachability is not established" in variant(lambda c: c["incident"].update(ssh_exit_code=255))[1]
    status, reason = variant(lambda c: c["incident"].update(session_failure_signatures=[]))
    assert status == "fail" and "no GNOME failure signature" in reason
    assert variant(lambda c: c["incident"].update(session_failure_signatures=[],
                                                   session_classification="headless"))[0] == "pass"
    assert "control is incomplete" in variant(lambda c: c["control"].update(display_connected=False))[1]
    assert "independent successful SSH" in variant(lambda c: c["control"].update(ssh_exit_code=1))[1]
    assert variant(lambda c: c["recovery"].update(display_connected=False))[0] == "fail"
    assert "package versions are missing" in variant(lambda c: c["recovery"].pop("package_version"))[1]
    assert "did not change" in variant(lambda c: c["recovery"].update(package_version="1.0"))[1]
    assert "rollback package version or independent" in variant(lambda c: c["rollback"].pop("ssh_exit_code"))[1]
    assert "rollback did not restore" in variant(lambda c: c["rollback"].update(package_version="3.0"))[1]
    assert "rollback did not restore" in variant(lambda c: c["rollback"].update(ssh_exit_code=2))[1]


@pytest.mark.parametrize(("observation", "category"), [
    ({"ssh_exit_code": 0}, "host_reachable_display_unresolved"),
    ({"ssh_exit_code": 255}, "host_reachability_failed_total_host_state_unknown"),
    ({}, "unknown"),
    ({"session_classification": "session_ending"}, "session_failure"),
    ({"session_classification": "greeter"}, "greeter_login_loop"),
    ({"session_classification": "active_session", "display_connected": True}, "healthy_desktop"),
])
def test_desktop_classifier_edges(observation: dict[str, Any], category: str) -> None:
    assert fhs._classify_desktop_state(observation) == category


# --------------------------------------------------------------------------- EEE

def _eee_cases() -> dict[str, dict[str, Any]]:
    on = {"output": "EEE status: enabled - active\n", "link_resets": 5, "topology": "direct", "cycles": 3,
          "packet_loss": 10.0}
    off = {"output": "EEE status: disabled\n", "link_resets": 0, "cycles": 3, "packet_loss": 0.0,
           "ssh_reconnects": 3, "ipv4": "up", "ipv6": "up"}
    return {"direct_eee_on": on, "direct_eee_off": off,
            "switch_control": {"link_resets": 0, "topology": "switch"},
            "identity": {"partner": "Intel I225-V", "eee_state": "active"},
            "rollback": {"eee_state": "active", "ipv4": "up", "ipv6": "up"}}


def test_eee_predicate_each_edge() -> None:
    assert fhs._check_eee(_eee_cases())[0] == "pass"

    def variant(mutate: Any) -> tuple[str, str]:
        cases = _eee_cases()
        mutate(cases)
        return fhs._check_eee(cases)

    assert variant(lambda c: c["direct_eee_on"].update(output="EEE status: disabled\n"))[0] == "fail"
    assert "counters missing" in variant(lambda c: c["direct_eee_on"].pop("link_resets"))[1]
    assert "switch-control link counter" in variant(lambda c: c["switch_control"].pop("link_resets"))[1]
    assert variant(lambda c: c["switch_control"].update(link_resets=2))[0] == "fail"
    assert variant(lambda c: c["direct_eee_off"].update(link_resets=9))[0] == "fail"
    assert "not distinct topologies" in variant(lambda c: c["switch_control"].update(topology="direct"))[1]
    assert "peer is not identified" in variant(lambda c: c["identity"].update(partner="other"))[1]
    assert "cycle counts unavailable" in variant(lambda c: c["direct_eee_on"].pop("cycles"))[1]
    assert "fewer than three" in variant(lambda c: c["direct_eee_off"].update(cycles=2))[1]
    assert "fewer than three" in variant(lambda c: c["direct_eee_on"].update(cycles=2))[1]
    assert "not distinct topologies" in variant(lambda c: c["direct_eee_on"].update(topology="switch"))[1]
    assert "packet-loss observations" in variant(lambda c: c["direct_eee_on"].pop("packet_loss"))[1]
    assert "SSH reconnect probes" in variant(lambda c: c["direct_eee_off"].update(ssh_reconnects=1))[1]
    assert "connectivity did not recover" in variant(lambda c: c["direct_eee_off"].update(ipv6="down"))[1]
    assert "did not return to its original state" in variant(lambda c: c["rollback"].update(eee_state="inactive"))[1]
    assert "did not return to its original state" in variant(lambda c: c["rollback"].update(ipv4="down"))[1]


def test_eee_state_pair_edges() -> None:
    active = {"output": "EEE status: enabled - active\n"}
    assert fhs._check_eee_states({"output": "garbage"}, {"output": "EEE status: disabled\n"})[0] == "unknown"
    assert fhs._check_eee_states(active, {"output": "garbage"})[0] == "unknown"
    plain = {"output": "EEE status: enabled\n"}
    status, reason = fhs._check_eee_states(plain, {"output": "EEE status: disabled\n"})
    assert status == "unknown" and "unresolved" in reason
    assert fhs._parse_eee_state("EEE status: enabled\n") == "enabled"


# --------------------------------------------------------------------------- rescue

def _rescue_cases() -> dict[str, dict[str, Any]]:
    return {"rescue_entry": {"entry_id": "0003"},
            "rescue_boot": {"boot_id": "r", "entry_id": "0003", "rescue_target": True},
            "normal_boot": {"boot_id": "n"},
            "restoration": {"boot_id": "x", "restored_entry": "0001", "network_route": "dev eth0"}}


def _service_dir(root: Path, **override: Any) -> dict[str, Any]:
    unit = root / "canary.service"
    unit.write_text("[Service]\n", encoding="utf-8")
    unit.chmod(0o644)
    manifest = {"path": "canary.service", "suspended_path": "canary.service.off",
                "sha256": hashlib.sha256(unit.read_bytes()).hexdigest(), "mode": 0o644,
                "expiry": "2099-01-01", "watcher": "luis", **override}
    (root / "service-restore-manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    return manifest


def _rescue_doc() -> dict[str, Any]:
    return {"captures": [_row("restoration", ["efibootmgr"], "BootCurrent: 0001\n", 1)]}


def test_rescue_predicate_each_edge(tmp_path: Path) -> None:
    _service_dir(tmp_path)
    document = _rescue_doc()
    assert fhs._check_rescue(document, _rescue_cases(), tmp_path)[0] == "pass"

    def variant(mutate: Any) -> tuple[str, str]:
        cases = _rescue_cases()
        mutate(cases)
        return fhs._check_rescue(document, cases, tmp_path)

    assert variant(lambda c: c["rescue_entry"].pop("entry_id"))[0] == "unknown"
    assert "new boot identity" in variant(lambda c: c["normal_boot"].update(boot_id="x"))[1]
    assert "own boot transition" in variant(lambda c: c["rescue_boot"].update(boot_id="n"))[1]
    assert variant(lambda c: c["rescue_boot"].pop("boot_id")) == ("unknown", "rescue boot identity unavailable")
    assert "differs from the OEM rescue menu entry" in variant(lambda c: c["rescue_boot"].update(entry_id="0009"))[1]
    assert "still selects the rescue" in variant(lambda c: c["restoration"].update(restored_entry="0003"))[1]
    assert "rescue.target" in variant(lambda c: c["rescue_boot"].update(rescue_target=False))[1]
    assert "route unavailable" in variant(lambda c: c["restoration"].pop("network_route"))[1]


def test_rescue_unknown_boot_identity_edge(tmp_path: Path) -> None:
    cases = _rescue_cases()
    cases["rescue_boot"]["boot_id"] = "  "
    status, reason = fhs._check_rescue(_rescue_doc(), cases, tmp_path)
    assert (status, reason) == ("unknown", "rescue boot identity unavailable")


def test_restored_service_manifest_failure_modes(tmp_path: Path) -> None:
    when = fhs.datetime.fromisoformat("2026-10-03T00:00:01+00:00")
    manifest_path = tmp_path / "service-restore-manifest.json"
    assert fhs._verify_restored_service(tmp_path, when)[1].startswith("canary service restoration manifest unavailable")
    manifest_path.write_bytes(b" " * 65_537)
    assert fhs._verify_restored_service(tmp_path, when) == (False, "service restore manifest exceeds 64 KiB")
    manifest_path.write_text("{broken", encoding="utf-8")
    assert fhs._verify_restored_service(tmp_path, when)[1].startswith("canary service restoration manifest unavailable")
    manifest_path.write_text("[1]", encoding="utf-8")
    assert fhs._verify_restored_service(tmp_path, when) == (False, "canary service restoration manifest malformed")
    _service_dir(tmp_path, watcher="  ")
    assert "lacks exact path/hash/mode" in fhs._verify_restored_service(tmp_path, when)[1]
    _service_dir(tmp_path, expiry="someday")
    assert fhs._verify_restored_service(tmp_path, when)[1] == "service restore expiry is not an ISO date/time"
    _service_dir(tmp_path, expiry="2026-10-02")
    assert "after the manifest expiry" in fhs._verify_restored_service(tmp_path, when)[1]
    _service_dir(tmp_path, path="../escape.service")
    assert "must stay relative" in fhs._verify_restored_service(tmp_path, when)[1]
    _service_dir(tmp_path, suspended_path="/abs/off")
    assert "must stay relative" in fhs._verify_restored_service(tmp_path, when)[1]
    _service_dir(tmp_path, path="missing.service")
    assert "unit is unavailable after restore" in fhs._verify_restored_service(tmp_path, when)[1]
    _service_dir(tmp_path)
    assert fhs._verify_restored_service(tmp_path, when) == (True, None)
    (tmp_path / "canary.service.off").write_text("x", encoding="utf-8")
    assert fhs._verify_restored_service(tmp_path, when) == (False, None)
    (tmp_path / "canary.service.off").unlink()
    _service_dir(tmp_path, mode=0o600)
    assert fhs._verify_restored_service(tmp_path, when) == (False, None)


def test_rescue_restoration_verdict_mapping(tmp_path: Path) -> None:
    document = _rescue_doc()
    status, reason = fhs._check_rescue_restoration(document, _rescue_cases(), tmp_path)
    assert status == "unknown" and "manifest unavailable" in reason
    _service_dir(tmp_path, expiry="2000-01-01")
    status, reason = fhs._check_rescue_restoration(document, _rescue_cases(), tmp_path)
    assert status == "fail" and "after the manifest expiry" in reason
    _service_dir(tmp_path, mode=0o600)
    status, reason = fhs._check_rescue_restoration(document, _rescue_cases(), tmp_path)
    assert status == "fail" and "differs from the verified pre-suspension manifest" in reason


# --------------------------------------------------------------------------- UVC

def _uvc_cases() -> dict[str, dict[str, Any]]:
    return {
        "stream_control": {"xhci_resets": 2},
        "no_ep0_control": {"xhci_resets": 0, "ep0_after_stream_count": 0},
        "corrected_stack": {"xhci_resets": 0, "stream_seconds": 30.0, "ep0_after_stream_count": 4,
                            "usb_device_id": "046d:0825"},
        "affected_stack": {"kernel_release": "6.1", "module_version": "1.0", "usb_device_id": "046d:0825"},
        "stack_identity": {"kernel_release": "6.2", "module_version": "2.0", "usb_device_id": "046d:0825"},
        "rollback": {"kernel_release": "6.1", "module_version": "1.0"},
    }


def test_uvc_predicate_each_edge() -> None:
    assert fhs._check_uvc(_uvc_cases())[0] == "pass"

    def variant(mutate: Any) -> tuple[str, str]:
        cases = _uvc_cases()
        mutate(cases)
        return fhs._check_uvc(cases)

    assert "lacks xHCI reset counters" in variant(lambda c: c["stream_control"].pop("xhci_resets"))[1]
    assert variant(lambda c: c["stream_control"].update(xhci_resets=0))[0] == "fail"
    assert variant(lambda c: c["corrected_stack"].update(xhci_resets=1))[0] == "fail"
    assert "no-EP0 negative control" in variant(lambda c: c["no_ep0_control"].update(xhci_resets=1))[1]
    assert "no-EP0 negative control" in variant(lambda c: c["no_ep0_control"].update(ep0_after_stream_count=2))[1]
    assert "unobserved" in variant(lambda c: c["corrected_stack"].pop("stream_seconds"))[1]
    assert "unobserved" in variant(lambda c: c["corrected_stack"].update(ep0_after_stream_count=0))[1]
    assert "identity missing" in variant(lambda c: c["affected_stack"].pop("kernel_release"))[1]
    assert "same camera USB identity" in variant(lambda c: c["stack_identity"].update(usb_device_id="1:2"))[1]
    assert "same camera USB identity" in variant(lambda c: c["corrected_stack"].update(usb_device_id="1:2"))[1]
    assert "reused the affected kernel and driver" in variant(
        lambda c: c["stack_identity"].update(kernel_release="6.1", module_version="1.0"))[1]
    assert "rollback does not restore" in variant(lambda c: c["rollback"].update(kernel_release="9"))[1]
    assert "rollback does not restore" in variant(lambda c: c["rollback"].update(module_version="9"))[1]


# --------------------------------------------------------------------------- evaluate() wiring

def _simple_doc(finding_id: str, rows: list[dict[str, Any]], **extra: Any) -> dict[str, Any]:
    return {"schema": 1, "id": finding_id, "captures": rows, **extra}


def test_evaluate_uvc_without_vendor_sources_is_unknown(tmp_path: Path) -> None:
    fid = "FORUM-02-USB-UVC-EP0"
    names = {"stack_identity": "uname", "affected_stack": "uname", "stream_control": "usbmon",
             "no_ep0_control": "usbmon", "corrected_stack": "usbmon", "rollback": "uname"}
    rows = [_row(name, [tool], "x", second + 1) for second, (name, tool) in enumerate(names.items())]
    _write(tmp_path, _simple_doc(fid, rows))
    result = evaluate(fid, tmp_path)
    assert result["status"] == "unknown" and "source text and digest missing" in result["reason"]


def test_evaluate_rescue_without_vendor_sources_is_unknown(tmp_path: Path) -> None:
    fid = "FEATURE-FORUM-RESCUE-RUNBOOK-01"
    names = {"oem_identity": "uname", "rescue_entry": "efibootmgr", "rescue_boot": "efibootmgr",
             "normal_boot": "bootctl", "restoration": "bootctl"}
    rows = [_row(name, [tool], "x", second + 1) for second, (name, tool) in enumerate(names.items())]
    _write(tmp_path, _simple_doc(fid, rows))
    result = evaluate(fid, tmp_path)
    assert result["status"] == "unknown" and "source text and digest missing" in result["reason"]


def test_evaluate_reports_missing_required_case(tmp_path: Path) -> None:
    fid = "FORUM-02-USB-UVC-EP0"
    _write(tmp_path, _simple_doc(fid, [_row("stack_identity", ["uname"], "x")]))
    result = evaluate(fid, tmp_path)
    assert result["status"] == "unknown" and result["reason"] == "raw case affected_stack missing"
