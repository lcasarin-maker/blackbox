"""Parser safety and real-evidence absence tests for hardware forum controls."""
from __future__ import annotations

import json
import hashlib
from pathlib import Path

import pytest

from tools.forum_hardware_subjects import (
    IDS,
    _case,
    _check_eee_states,
    _check_watchdog,
    _classify_desktop_state,
    _number,
    _parse_eee_state,
    evaluate,
)


@pytest.mark.parametrize("value", [True, False, float("nan"), float("inf"), -float("inf")])
def test_measurement_parser_rejects_boolean_and_nonfinite_values(value: object) -> None:
    assert _number({"measurement": value}, "measurement") is None


@pytest.mark.parametrize("finding_id", sorted(IDS))
def test_missing_raw_capture_remains_could_not_run(tmp_path: Path, finding_id: str) -> None:
    result = evaluate(finding_id, tmp_path)
    assert result["status"] == "unknown"
    assert result["fail"] == 0
    assert result["could_not_run"] == 1


@pytest.mark.parametrize("finding_id", sorted(IDS - {"FORUM-02-GX10-READ-INTEGRITY"}))
def test_json_claim_transcript_from_native_command_is_not_measurement(
    tmp_path: Path, finding_id: str,
) -> None:
    """A dmidecode/ethtool argv cannot authenticate an invented JSON stdout."""
    path = tmp_path / "capture.json"
    name = {
        "FEATURE-FORUM-RESCUE-RUNBOOK-01": "oem_identity",
        "FEATURE-FORUM-SBSA-WATCHDOG-STATE-01": "watchdog",
        "FORUM-00-GB10-THERMAL-RESIDENCY-ADMISSION": "safety_limits",
        "FORUM-02-USB-UVC-EP0": "stack_identity",
    }.get(finding_id, "identity")
    captures = [{
        "name": name, "argv": ["dmidecode", "--json"], "exit_code": 0,
        "stdout": '{"oem":"claim","pass":true}', "stderr": "",
        "captured_at": "2026-10-03T00:00:01+00:00",
    }]
    path.write_text(json.dumps({"schema": 1, "id": finding_id, "captures": captures}), encoding="utf-8")
    result = evaluate(finding_id, tmp_path)
    assert result["status"] == "unknown"
    assert result["fail"] == 0
    assert result["could_not_run"] == 1
    assert result["reason"]


def test_oversized_capture_fails_closed(tmp_path: Path) -> None:
    (tmp_path / "capture.json").write_bytes(b" " * (4 * 1024 * 1024 + 1))
    result = evaluate("FORUM-00-CX7-HOTPLUG-FAN-PROTECTION", tmp_path)
    assert result["status"] == "fail"
    assert result["fail"] == 1
    assert result["could_not_run"] == 0


def test_native_ethtool_output_is_preserved_as_raw_text() -> None:
    stdout = (
        "EEE status: enabled - active\n"
        "Tx LPI: 16 (us)\n"
        "Supported EEE link modes: 100baseT/Full 1000baseT/Full\n"
        "Link partner advertised EEE link modes: 100baseT/Full\n"
    )
    document = {"captures": [{
        "name": "direct_eee_on", "argv": ["ethtool", "--show-eee", "enp1s0"],
        "exit_code": 0, "stdout": stdout, "stderr": "",
    }]}
    data, error = _case(document, "direct_eee_on", r"ethtool.*show-eee")
    assert error is None
    assert data is not None
    assert data["output"] == stdout
    assert data["eee_state"] == "active"
    assert data["partner_eee_modes"] == "100baseT/Full"
    assert _parse_eee_state(stdout) == "active"


@pytest.mark.parametrize(
    ("stdout", "expected"),
    [
        ("EEE status: enabled - active\n", "active"),
        ("EEE status: enabled - inactive\n", "inactive"),
        ("EEE status: disabled\n", "disabled"),
        ("EEE status: permission denied\n", None),
    ],
)
def test_eee_state_comes_from_native_ethtool_line(stdout: str, expected: str | None) -> None:
    assert _parse_eee_state(stdout) == expected


def test_eee_ab_states_pass_and_contradictory_state_fails() -> None:
    enabled = {"output": "EEE status: enabled - active\n"}
    disabled = {"output": "EEE status: disabled\n"}
    assert _check_eee_states(enabled, disabled)[0] == "pass"
    assert _check_eee_states(disabled, disabled)[0] == "fail"


def test_native_ethtool_stats_and_ping_measurements_are_derived() -> None:
    from tools.forum_hardware_subjects import _native_facts

    stats = _native_facts(["ethtool", "-S", "enp1s0"], "link_down_events: 4\ntx_packets: 900\n")
    ping = _native_facts(
        ["ping", "-c", "10", "192.0.2.1"],
        "10 packets transmitted, 8 received, 20% packet loss, time 9000ms\n",
    )
    assert stats["link_down_events"] == 4
    assert "tx_packets" not in stats
    assert ping["packets_sent"] == 10 and ping["packet_loss"] == 20


def test_lspci_derives_device_identity_and_effective_binding() -> None:
    from tools.forum_hardware_subjects import _native_facts

    facts = _native_facts(
        ["lspci", "-nnk", "-s", "0007:01:00.0"],
        "0007:01:00.0 Ethernet controller [0200]: Realtek Device [10ec:8127]\n"
        "\tKernel driver in use: r8127\n\tKernel modules: r8127\n",
    )
    assert facts["pci_id"] == "10ec:8127"
    assert facts["pci_state"] == "present"
    assert facts["driver"] == "r8127"


def test_native_thermal_outputs_extract_temperature_and_power() -> None:
    from tools.forum_hardware_subjects import _native_facts

    smi = _native_facts(
        ["nvidia-smi", "--query-gpu=temperature.gpu,power.draw", "--format=csv,noheader,nounits"],
        "71, 24.5\n",
    )
    sensors = _native_facts(["sensors"], "SoC: +63.0°C\nCPU: +65.0°C\nGPU: +70.0°C\n")
    assert smi["temperature_c"] == 71
    assert smi["power_w"] == 24.5
    assert sensors == {"output": "SoC: +63.0°C\nCPU: +65.0°C\nGPU: +70.0°C\n",
                       "soc_c": 63, "cpu_c": 65, "gpu_c": 70}


def test_thermal_coverage_is_inventory_only_and_oem_limits_are_channel_scoped() -> None:
    from tools.forum_hardware_subjects import _thermal_coverage_observation, _thermal_limits

    inventory = {
        "schema": 1, "status": "observed", "could_not_run": 0,
        "thermal_zones": [
            {"type": {"value": "GPU"}, "temperature": {"status": "ok", "value": 72000}},
            {"type": {"value": "CPU"}, "temperature": {"status": "ok", "value": 68000}},
            {"type": {"value": "SoC"}, "temperature": {"status": "ok", "value": 75000}},
        ], "hwmon": [],
    }
    observed = _thermal_coverage_observation({"output": json.dumps(inventory)})
    assert observed == {"gpu_c": 72.0, "cpu_c": 68.0, "soc_c": 75.0}
    source = "GPU maximum 85 C. CPU limit 95 C. SoC shutdown 100 C."
    assert _thermal_limits(source) == {"gpu_c": 85.0, "cpu_c": 95.0, "soc_c": 100.0}
    inventory["could_not_run"] = 1
    assert _thermal_coverage_observation({"output": json.dumps(inventory)}) is None


def test_cx7_raw_symptom_thermal_power_ab_and_rollback(tmp_path: Path) -> None:
    from datetime import datetime, timedelta, timezone
    from tools.thermal_coverage import capture as capture_thermal

    finding_id = "FORUM-00-CX7-HOTPLUG-FAN-PROTECTION"

    def thermal(root: Path, temperature: int) -> str:
        for index, name in enumerate(("GPU", "CPU", "SoC")):
            zone = root / "sys/class/thermal" / f"thermal_zone{index}"
            zone.mkdir(parents=True, exist_ok=True)
            (zone / "type").write_text(name, encoding="utf-8")
            (zone / "temp").write_text(str(temperature * 1000), encoding="utf-8")
            (zone / "trip_point_0_temp").write_text("100000", encoding="utf-8")
            (zone / "trip_point_0_type").write_text("critical", encoding="utf-8")
        fan = root / "sys/class/hwmon/hwmon0"
        fan.mkdir(parents=True, exist_ok=True)
        (fan / "name").write_text("cooling", encoding="utf-8")
        (fan / "fan1_input").write_text("1200", encoding="utf-8")
        (root / "sys/class/hwmon/hwmon1").mkdir(parents=True, exist_ok=True)
        (root / "sys/class/hwmon").mkdir(parents=True, exist_ok=True)
        return json.dumps(capture_thermal(root))

    def row(name: str, argv: list[str], stdout: str, offset: int) -> dict[str, object]:
        time = datetime(2026, 10, 3, tzinfo=timezone.utc) + timedelta(seconds=offset)
        return {"name": name, "argv": argv, "exit_code": 0, "stdout": stdout,
                "stderr": "", "captured_at": time.isoformat()}

    meter = lambda watts: json.dumps({"sys": {"device": {"id": "shelly-pro-1pm-abc"}},
                                      "switch:0": {"apower": watts}})
    source = ("Dell Inc. Product X board P4242 A04 BIOS 5.36_0ACUM027 kernel 6.17.0-1032-nvidia "
              "mlx5 26.01 UEFI 5.36_0ACUM027 EC 0x03000508 SoC 0x02009b0b PD 0x516 CX7 28.45.4028; "
              "GPU maximum 85 C. CPU limit 95 C. SoC shutdown 100 C. These are the supported "
              "channel limits and exact-system thermal bounds for this identified configuration.")
    firmware = ("Name: UEFI firmware\nVersion: 5.36_0ACUM027\n"
                "Name: Embedded Controller\nVersion: 0x03000508\n"
                "Name: System-on-Chip firmware\nVersion: 0x02009b0b\n"
                "Name: USB-C PD firmware\nVersion: 0x516\n"
                "Name: ConnectX-7 firmware\nVersion: 28.45.4028\n")
    captures = [
        row("identity", ["dmidecode", "-t", "system"],
            "Manufacturer: Dell Inc.\nProduct Name: Product X\nBIOS Version: 5.36_0ACUM027\n", 1),
        row("identity", ["uname", "-r"], "6.17.0-1032-nvidia\n", 2),
        row("identity", ["modinfo", "-F", "version", "mlx5_core"], "26.01\n", 3),
        row("identity", ["fwupdmgr", "get-devices"], firmware, 4),
        row("symptom", ["dmesg", "--color=never"], "cx7-pcie-hotplug: Cable removal\n", 5),
        row("baseline", ["python3", "-m", "tools.thermal_coverage"],
            thermal(tmp_path / "base", 60), 6),
        row("baseline", ["curl", "http://meter/rpc/Shelly.GetStatus"], meter(24.0), 7),
        row("baseline", ["cat", "/sys/class/hwmon/hwmon0/fan1_input"], "1200\n", 8),
        row("candidate", ["python3", "-m", "tools.thermal_coverage"],
            thermal(tmp_path / "candidate", 70), 9),
        row("candidate", ["curl", "http://meter/rpc/Shelly.GetStatus"], meter(41.0), 10),
        row("candidate", ["cat", "/sys/class/hwmon/hwmon0/fan1_input"], "1200\n", 11),
        row("candidate", ["lspci", "-nnk"], "ConnectX-7 [15b3:101d]\n", 12),
        row("candidate", ["ethtool", "enp1s0"], "Link detected: yes\n", 13),
        row("candidate", ["journalctl", "-k", "--grep=cx7"], "No matching entries\n", 14),
        row("rollback", ["lspci", "-nnk"], "ConnectX-7 [15b3:101d]\n", 15),
        row("rollback", ["ethtool", "enp1s0"], "Link detected: yes\n", 16),
        row("rollback", ["cat", "/sys/class/hwmon/hwmon0/fan1_input"], "1200\n", 17),
    ]
    (tmp_path / "capture.json").write_text(json.dumps({
        "schema": 1, "id": finding_id, "captures": captures,
        "vendor_sources": [{"url": "https://www.dell.com/support", "text": source,
                            "sha256": hashlib.sha256(source.encode()).hexdigest()}],
    }), encoding="utf-8")
    result = evaluate(finding_id, tmp_path)
    assert result["status"] == "pass" and result["fail"] == result["could_not_run"] == 0, result

    data = json.loads((tmp_path / "capture.json").read_text(encoding="utf-8"))
    collector = next(item for item in data["captures"] if item["name"] == "candidate"
                     and "tools.thermal_coverage" in item["argv"])
    thermal_data = json.loads(collector["stdout"])
    thermal_data["thermal_zones"][0]["temperature"]["value"] = 85000
    collector["stdout"] = json.dumps(thermal_data)
    (tmp_path / "capture.json").write_text(json.dumps(data), encoding="utf-8")
    negative = evaluate(finding_id, tmp_path)
    assert negative["status"] == "fail" and negative["could_not_run"] == 0, negative


def test_native_fuser_and_journal_records_derive_owner_and_boot_identity() -> None:
    from tools.forum_hardware_subjects import _native_facts

    owner = _native_facts(
        ["fuser", "-v", "/dev/watchdog0"],
        "/dev/watchdog0: root 218 F.... systemd\n",
    )
    journal = _native_facts(
        ["journalctl", "-b", "-o", "json"],
        '{"_BOOT_ID":"12345678-1234-1234-1234-123456789abc","MESSAGE":"watchdog"}\n',
    )
    assert owner["owner_pids"] == [218]
    assert journal["boot_id"] == "12345678-1234-1234-1234-123456789abc"


def test_uvc_trace_counts_post_stream_ep0_and_xhci_failure_from_native_rows() -> None:
    from tools.forum_hardware_subjects import _native_facts

    raw = (
        "[ 10.000000] uvcvideo: uvc_video_start_streaming\n"
        "ffff 10.100000 S Co:1:002:0 s 21 01 0100 0000 0000 0\n"
        "[ 40.000000] uvcvideo: uvc_video_stop_streaming\n"
        "[ 41.000000] xhci_hc_died: HC died; cleaning up\n"
    )
    facts = _native_facts(["trace-cmd", "report", "-i", "trace.dat"], raw)
    assert facts["ep0_after_stream_count"] == 1
    assert facts["xhci_resets"] == 1
    assert facts["stream_seconds"] == 30.0
    no_control = raw.replace("ffff 10.100000 S Co:1:002:0 s 21 01 0100 0000 0000 0\n", "")
    assert _native_facts(["trace-cmd", "report"], no_control)["ep0_after_stream_count"] == 0


def test_thermal_processes_and_throughput_are_derived_from_native_outputs() -> None:
    from tools.forum_hardware_subjects import _native_facts

    running = _native_facts(
        ["nvidia-smi", "--query-compute-apps=pid,name,used_memory", "--format=csv,noheader,nounits"],
        "2471, python, 8192 MiB\n",
    )
    idle = _native_facts(
        ["nvidia-smi", "--query-compute-apps=pid,name,used_memory", "--format=csv,noheader,nounits"],
        "No running processes found\n",
    )
    benchmark = _native_facts(["vllm", "bench", "serve", "--model", "models/served"],
                              "Output token throughput: 22.5 tokens/s\n")
    assert running["resident_processes"] == 1 and running["resident_bytes"] == 8192 * 1024 * 1024
    assert idle["resident_processes"] == 0 and idle["resident_bytes"] == 0
    assert benchmark["throughput"] == 22.5 and len(benchmark["workload_hash"]) == 64


def test_thermal_residency_raw_samples_workload_idle_and_rollback(tmp_path: Path) -> None:
    from datetime import datetime, timedelta, timezone
    from tools.thermal_coverage import capture as capture_thermal

    finding_id = "FORUM-00-GB10-THERMAL-RESIDENCY-ADMISSION"

    def thermal(root: Path, temperature: int) -> str:
        for index, name in enumerate(("GPU", "CPU", "SoC")):
            zone = root / "sys/class/thermal" / f"thermal_zone{index}"
            zone.mkdir(parents=True, exist_ok=True)
            (zone / "type").write_text(name, encoding="utf-8")
            (zone / "temp").write_text(str(temperature * 1000), encoding="utf-8")
            (zone / "trip_point_0_temp").write_text("100000", encoding="utf-8")
            (zone / "trip_point_0_type").write_text("critical", encoding="utf-8")
        fan = root / "sys/class/hwmon/hwmon0"
        fan.mkdir(parents=True, exist_ok=True)
        (fan / "name").write_text("cooling", encoding="utf-8")
        (fan / "fan1_input").write_text("1200", encoding="utf-8")
        (root / "sys/class/hwmon/hwmon1").mkdir(parents=True, exist_ok=True)
        return json.dumps(capture_thermal(root))

    def row(name: str, argv: list[str], stdout: str, second: int) -> dict[str, object]:
        time = datetime(2026, 10, 3, tzinfo=timezone.utc) + timedelta(seconds=second)
        return {"name": name, "argv": argv, "exit_code": 0, "stdout": stdout,
                "stderr": "", "captured_at": time.isoformat()}

    meter = lambda watts: json.dumps({"sys": {"device": {"id": "meter-abc"}},
                                      "switch:0": {"apower": watts}})
    smi_apps = ["nvidia-smi", "--query-compute-apps=pid,name,used_memory", "--format=csv,noheader,nounits"]
    sources = "Dell Inc. Product GB10 BIOS B1 kernel 6.17.0-1032-nvidia GPU maximum 85 C. CPU maximum 95 C. SoC shutdown 100 C. Exact OEM thermal limits and supported recovery for this configuration; caller-supplied excerpt."
    captures = [
        row("safety_limits", ["dmidecode", "-t", "system"],
            "Manufacturer: Dell Inc.\nProduct Name: Product GB10\nBIOS Version: B1\n", 1),
        row("safety_limits", ["uname", "-r"], "6.17.0-1032-nvidia\n", 2),
        row("resident_workload", ["python3", "-m", "tools.thermal_coverage"], thermal(tmp_path / "run1", 72), 3),
        row("resident_workload", ["python3", "-m", "tools.thermal_coverage"], thermal(tmp_path / "run2", 78), 303),
        row("resident_workload", smi_apps, "2471, vllm, 8192 MiB\n", 304),
        row("resident_workload", ["vllm", "bench", "serve", "--model", "model-A"],
            "Output token throughput: 22.5 tokens/s\n", 305),
        row("resident_workload", ["curl", "http://meter/rpc/Shelly.GetStatus"], meter(88.0), 306),
        row("resident_workload", ["cat", "/sys/class/hwmon/hwmon0/fan1_input"], "1200\n", 307),
        row("idle_control", ["python3", "-m", "tools.thermal_coverage"], thermal(tmp_path / "idle", 38), 308),
        row("idle_control", smi_apps, "No running processes found\n", 309),
        row("idle_control", ["curl", "http://meter/rpc/Shelly.GetStatus"], meter(29.0), 310),
        row("rollback", ["python3", "-m", "tools.thermal_coverage"], thermal(tmp_path / "rollback", 40), 311),
        row("rollback", smi_apps, "No running processes found\n", 312),
    ]
    (tmp_path / "capture.json").write_text(json.dumps({
        "schema": 1, "id": finding_id, "captures": captures,
        "vendor_sources": [{"url": "https://www.dell.com/support", "text": sources,
                            "sha256": hashlib.sha256(sources.encode()).hexdigest()}],
    }), encoding="utf-8")
    result = evaluate(finding_id, tmp_path)
    assert result["status"] == "pass" and result["fail"] == result["could_not_run"] == 0, result

    evidence = json.loads((tmp_path / "capture.json").read_text(encoding="utf-8"))
    samples = [item for item in evidence["captures"]
               if item["name"] == "resident_workload" and "tools.thermal_coverage" in item["argv"]]
    sample = samples[1]
    thermal_capture = json.loads(sample["stdout"])
    thermal_capture["thermal_zones"][0]["temperature"]["value"] = 86.0
    sample["stdout"] = json.dumps(thermal_capture)
    (tmp_path / "capture.json").write_text(json.dumps(evidence), encoding="utf-8")
    negative = evaluate(finding_id, tmp_path)
    assert negative["status"] == "fail" and negative["could_not_run"] == 0, negative


def test_gx10_reference_buffered_direct_nvme_ras_and_tuple_correlate(tmp_path: Path) -> None:
    from tools.read_integrity import inspect

    finding_id = "FORUM-02-GX10-READ-INTEGRITY"
    healthy = tmp_path / "healthy.bin"
    altered = tmp_path / "altered.bin"
    healthy.write_bytes(b"a" * 4096)
    altered.write_bytes(b"b" + b"a" * 4095)
    digest = hashlib.sha256(healthy.read_bytes()).hexdigest()

    def read_row(name: str, target: Path, expected: str, second: int) -> dict[str, object]:
        argv = ["python3", "-m", "tools.read_integrity", str(target), "--offset", "0",
                "--length", "4096", "--sha256", expected, "--repeats", "1"]
        measured = inspect(str(target), 0, 4096, expected, 1)
        return {"name": name, "argv": argv, "exit_code": {"pass": 0, "fail": 1,
                "could_not_run": 2}[measured["status"]], "stdout": json.dumps(measured),
                "stderr": "", "captured_at": f"2026-10-03T02:00:{second:02d}+00:00",
                "elapsed_ms": 1.0}

    def row(name: str, argv: list[str], stdout: str, second: int) -> dict[str, object]:
        return {"name": name, "argv": argv, "exit_code": 0, "stdout": stdout,
                "stderr": "", "captured_at": f"2026-10-03T02:00:{second:02d}+00:00"}

    source = "ASUS Product GX10 BIOS B1 kernel 6.17.0-1032-nvidia NVMe and RAS diagnostics apply to this exact supported stack; retain caller-supplied source provenance."
    captures = [
        read_row("healthy", healthy, digest, 1),
        read_row("altered", altered, digest, 2),
        row("external_reference", ["ssh", "trusted-head", "sha256sum", "weights.safetensors"],
            f"{digest}  weights.safetensors\n", 3),
        row("nvme_health", ["nvme", "smart-log", "/dev/nvme0", "-o", "json"],
            '{"critical_warning":0,"media_errors":0}\n', 4),
        row("ras_signals", ["journalctl", "-k", "--grep=ras|edac|bert"], "No matching entries\n", 5),
        row("stack_identity", ["dmidecode", "-t", "system"],
            "Manufacturer: ASUS\nProduct Name: Product GX10\nBIOS Version: B1\n", 6),
        row("stack_identity", ["uname", "-r"], "6.17.0-1032-nvidia\n", 7),
    ]
    snapshot = {"checks": {
        "storage": {
            "root_mounts": {"status": "ok", "value": [{"target": "/", "options": "rw,relatime", "read_only": False}]},
            "nvme_inventory": {"status": "ok", "stdout": '{"Devices":[{"DevicePath":"/dev/nvme0n1","SerialNumber":"fixture-serial"}]}'}},
        "kernel_signals": {"status": "ok", "stdout": ""},
    }}
    (tmp_path / "nvme-snapshot.json").write_text(json.dumps(snapshot), encoding="utf-8")
    (tmp_path / "capture.json").write_text(json.dumps({
        "schema": 1, "id": finding_id, "captures": captures,
        "vendor_sources": [{"url": "https://www.asus.com/support/", "text": source,
                            "sha256": hashlib.sha256(source.encode()).hexdigest()}],
    }), encoding="utf-8")
    result = evaluate(finding_id, tmp_path)
    assert result["status"] == "pass" and result["fail"] == result["could_not_run"] == 0, result

    evidence = json.loads((tmp_path / "capture.json").read_text(encoding="utf-8"))
    external = next(item for item in evidence["captures"] if item["name"] == "external_reference")
    external["stdout"] = "0" * 64 + "  weights.safetensors\n"
    (tmp_path / "capture.json").write_text(json.dumps(evidence), encoding="utf-8")
    negative = evaluate(finding_id, tmp_path)
    assert negative["status"] == "fail" and negative["could_not_run"] == 0, negative


def test_uvc_full_native_affected_corrected_camera_and_rollback(tmp_path: Path) -> None:
    finding_id = "FORUM-02-USB-UVC-EP0"
    source = (
        "Dell Inc. Product X BIOS B1 kernel 6.17.0-1021-nvidia UVC driver 1.2.3; "
        "NVIDIA supported correction Dell Product X BIOS B1 kernel 6.17.0-1032-nvidia "
        "UVC driver 1.2.4 camera 8086:0b3a, same OEM image and recovery guidance."
    )

    def row(name: str, argv: list[str], stdout: str, second: int) -> dict[str, object]:
        return {"name": name, "argv": argv, "exit_code": 0, "stdout": stdout,
                "stderr": "", "captured_at": f"2026-10-03T01:00:{second:02d}+00:00"}

    camera = "Bus 001 Device 002: ID 8086:0b3a Intel RealSense D435i\n"
    old_events = (
        "[ 10.000000] uvcvideo: uvc_video_start_streaming\n"
        "ffff 10.100000 S Co:1:002:0 s 21 01 0100 0000 0000 0\n"
        "[ 20.000000] xhci_hc_died: HC died; cleaning up\n"
        "[ 30.000000] uvcvideo: uvc_video_stop_streaming\n"
    )
    fixed_events = (
        "[ 100.000000] uvcvideo: uvc_video_start_streaming\n"
        "ffff 101.000000 S Co:1:002:0 s 21 01 0100 0000 0000 0\n"
        "[ 140.000000] uvcvideo: uvc_video_stop_streaming\n"
    )
    no_ep0 = ("[ 200.000000] uvcvideo: uvc_video_start_streaming\n"
              "[ 240.000000] uvcvideo: uvc_video_stop_streaming\n")
    captures = [
        row("stack_identity", ["dmidecode", "-t", "system"],
            "Manufacturer: Dell Inc.\nProduct Name: Product X\nBIOS Version: B1\n", 1),
        row("stack_identity", ["uname", "-r"], "6.17.0-1032-nvidia\n", 2),
        row("stack_identity", ["modinfo", "-F", "version", "uvcvideo"], "1.2.4\n", 3),
        row("stack_identity", ["lsusb"], camera, 4),
        row("affected_stack", ["uname", "-r"], "6.17.0-1021-nvidia\n", 5),
        row("affected_stack", ["modinfo", "-F", "version", "uvcvideo"], "1.2.3\n", 6),
        row("affected_stack", ["lsusb"], camera, 7),
        row("stream_control", ["trace-cmd", "report"], old_events, 8),
        row("no_ep0_control", ["trace-cmd", "report"], no_ep0, 9),
        row("corrected_stack", ["trace-cmd", "report"], fixed_events, 10),
        row("corrected_stack", ["lsusb"], camera, 11),
        row("rollback", ["uname", "-r"], "6.17.0-1021-nvidia\n", 12),
        row("rollback", ["modinfo", "-F", "version", "uvcvideo"], "1.2.3\n", 13),
    ]
    (tmp_path / "capture.json").write_text(json.dumps({
        "schema": 1, "id": finding_id, "captures": captures,
        "vendor_sources": [{"url": "https://www.nvidia.com/en-us/solutions/embedded-computing/", "text": source,
                            "sha256": hashlib.sha256(source.encode()).hexdigest()}],
    }), encoding="utf-8")
    result = evaluate(finding_id, tmp_path)
    assert result["status"] == "pass" and result["fail"] == result["could_not_run"] == 0, result

    data = json.loads((tmp_path / "capture.json").read_text(encoding="utf-8"))
    corrected = next(item for item in data["captures"] if item["name"] == "corrected_stack")
    corrected["stdout"] = old_events
    (tmp_path / "capture.json").write_text(json.dumps(data), encoding="utf-8")
    negative = evaluate(finding_id, tmp_path)
    assert negative["status"] == "fail" and negative["could_not_run"] == 0, negative


def _watchdog_profile(root: Path, boot_id: str, bootstatus: str) -> dict[str, object]:
    from tools.recovery_profile import capture

    (root / "proc/sys/kernel/random").mkdir(parents=True, exist_ok=True)
    (root / "proc/sys/kernel/random/boot_id").write_text(boot_id, encoding="utf-8")
    (root / "proc/modules").parent.mkdir(parents=True, exist_ok=True)
    (root / "proc/modules").write_text("sbsa_gwdt 16384 0 - Live 0\n", encoding="utf-8")
    device = root / "sys/class/watchdog/watchdog0"
    device.mkdir(parents=True)
    for key, value in {"identity": "ARM SBSA Generic Watchdog", "state": "active",
                       "status": "0", "timeout": "60", "nowayout": "0",
                       "bootstatus": bootstatus}.items():
        (device / key).write_text(value, encoding="utf-8")
    return capture(root)


def test_watchdog_positive_uses_recovery_profile_owner_and_reset_flag(tmp_path: Path) -> None:
    before = _watchdog_profile(tmp_path / "before", "12345678-1234-1234-1234-123456789abc", "0")
    after = _watchdog_profile(tmp_path / "after", "22345678-1234-1234-1234-123456789abc", "32")
    cases = {
        "ownership": {"owner_pids": [218]},
        "watchdog": {**before, "driver_config": "m", "module_loaded": True},
        "boot_logs": {"boot_id": "12345678-1234-1234-1234-123456789abc"},
        "recovery": after,
    }
    status, _reason = _check_watchdog(cases)
    assert status == "pass"


def test_watchdog_rejects_unrelated_boot_and_missing_owner(tmp_path: Path) -> None:
    before = _watchdog_profile(tmp_path / "before", "12345678-1234-1234-1234-123456789abc", "0")
    after = _watchdog_profile(tmp_path / "after", "22345678-1234-1234-1234-123456789abc", "0")
    cases = {
        "ownership": {"owner_pids": [218]},
        "watchdog": {**before, "driver_config": "m", "module_loaded": True},
        "boot_logs": {"boot_id": "12345678-1234-1234-1234-123456789abc"},
        "recovery": after,
    }
    assert _check_watchdog(cases)[0] == "fail"
    cases["ownership"] = {"owner_pids": []}
    assert _check_watchdog(cases)[0] == "unknown"


def test_watchdog_complete_raw_capture_passes_from_collector_and_native_outputs(tmp_path: Path) -> None:
    finding_id = "FEATURE-FORUM-SBSA-WATCHDOG-STATE-01"
    before = _watchdog_profile(tmp_path / "before", "12345678-1234-1234-1234-123456789abc", "0")
    after = _watchdog_profile(tmp_path / "after", "22345678-1234-1234-1234-123456789abc", "32")
    source = (
        "Dell Inc. OEM watchdog compatibility for Product X board X BIOS X1 kernel 6.17.0; "
        "ARM SBSA driver owner and timeout behavior are supported on this exact software tuple."
    )

    def row(name: str, argv: list[str], stdout: str, seconds: int) -> dict[str, object]:
        return {"name": name, "argv": argv, "exit_code": 0, "stdout": stdout,
                "stderr": "", "captured_at": f"2026-10-03T00:00:{seconds:02d}+00:00"}

    captures = [
        row("identity", ["dmidecode", "-t", "system"],
            "Manufacturer: Dell Inc.\nProduct Name: Product X\nBIOS Version: X1\n", 1),
        row("identity", ["uname", "-r"], "6.17.0\n", 2),
        row("watchdog", ["python3", "-m", "tools.recovery_profile"], json.dumps(before), 3),
        row("watchdog", ["grep", "CONFIG_ARM_SBSA_WATCHDOG", "/proc/config.gz"],
            "CONFIG_ARM_SBSA_WATCHDOG=m\n", 4),
        row("ownership", ["fuser", "-v", "/dev/watchdog0"],
            "/dev/watchdog0: root 218 F.... systemd\n", 5),
        row("boot_logs", ["journalctl", "-b", "-o", "json"],
            '{"_BOOT_ID":"12345678-1234-1234-1234-123456789abc","MESSAGE":"watchdog"}\n', 6),
        row("recovery", ["python3", "-m", "tools.recovery_profile"], json.dumps(after), 7),
    ]
    (tmp_path / "capture.json").write_text(json.dumps({
        "schema": 1, "id": finding_id, "captures": captures,
        "vendor_sources": [{"url": "https://www.dell.com/support", "text": source,
                            "sha256": hashlib.sha256(source.encode()).hexdigest()}],
    }), encoding="utf-8")
    result = evaluate(finding_id, tmp_path)
    assert result["status"] == "pass" and result["fail"] == result["could_not_run"] == 0, result

    capture_path = tmp_path / "capture.json"
    evidence = json.loads(capture_path.read_text(encoding="utf-8"))
    recovery_row = next(row for row in evidence["captures"] if row["name"] == "recovery")
    recovered = json.loads(recovery_row["stdout"])
    recovered["watchdog"]["watchdog0"]["bootstatus"]["value"] = "0"
    recovery_row["stdout"] = json.dumps(recovered)
    capture_path.write_text(json.dumps(evidence), encoding="utf-8")
    negative = evaluate(finding_id, tmp_path)
    assert negative["status"] == "fail" and negative["fail"] == 1, negative


def test_realtek_complete_warm_cold_binding_and_rollback_from_native_outputs(tmp_path: Path) -> None:
    finding_id = "FORUM-REALTEK-DRIVER-BINDING-01"
    source = (
        "Dell Inc. Product X board B BIOS X1 kernel 6.17.0 supports Realtek r8127 version 11.014.00 "
        "with signed module signer OEM Linux Driver Support Matrix, exact supported tuple and rollback guidance."
    )

    def row(name: str, argv: list[str], stdout: str, seconds: int, rc: int = 0) -> dict[str, object]:
        return {"name": name, "argv": argv, "exit_code": rc, "stdout": stdout,
                "stderr": "", "captured_at": f"2026-10-03T00:01:{seconds:02d}+00:00"}

    captures = [
        row("identity", ["dmidecode", "-t", "system"],
            "Manufacturer: Dell Inc.\nProduct Name: Product X\nBIOS Version: X1\n", 1),
        row("identity", ["uname", "-r"], "6.17.0\n", 2),
        row("identity", ["modinfo", "-F", "version", "r8127"], "11.014.00\n", 3),
        row("identity", ["modinfo", "-F", "signer", "r8127"], "OEM Linux Driver Support Matrix\n", 4),
        row("before", ["cat", "/proc/sys/kernel/random/boot_id"],
            "12345678-1234-1234-1234-123456789abc\n", 5),
        row("before", ["lspci", "-nnk", "-s", "0007:01:00.0"],
            "0007:01:00.0 Ethernet controller [0200]: Realtek [10ec:8127]\n\tKernel driver in use: r8169\n", 6),
    ]
    for seconds, phase, boot_id in ((7, "warm_after", "22345678-1234-1234-1234-123456789abc"),
                                    (13, "cold_after", "32345678-1234-1234-1234-123456789abc")):
        captures.extend([
            row(phase, ["cat", "/proc/sys/kernel/random/boot_id"], boot_id + "\n", seconds),
            row(phase, ["lspci", "-nnk", "-s", "0007:01:00.0"],
                "0007:01:00.0 Ethernet controller [0200]: Realtek [10ec:8127]\n\tKernel driver in use: r8127\n", seconds + 1),
            row(phase, ["modinfo", "-F", "version", "r8127"], "11.014.00\n", seconds + 2),
            row(phase, ["modinfo", "-F", "signer", "r8127"], "OEM Linux Driver Support Matrix\n", seconds + 3),
            row(phase, ["ethtool", "enP7s7"], "Settings for enP7s7:\n\tLink detected: yes\n", seconds + 4),
            row(phase, ["ssh", "management-host", "true"], "", seconds + 5),
        ])
    captures.extend([
        row("alternate_nic", ["lspci", "-nnk", "-s", "0009:01:00.0"],
            "0009:01:00.0 Ethernet controller [0200]: Intel [8086:15f3]\n\tKernel driver in use: igc\n", 20),
        row("driver_absent", ["lspci", "-nnk", "-s", "0007:01:00.0"],
            "0007:01:00.0 Ethernet controller [0200]: Realtek [10ec:8127]\n", 21),
        row("rollback", ["lspci", "-nnk", "-s", "0007:01:00.0"],
            "0007:01:00.0 Ethernet controller [0200]: Realtek [10ec:8127]\n\tKernel driver in use: r8169\n", 22),
        row("rollback", ["ssh", "management-host", "true"], "", 23),
    ])
    (tmp_path / "capture.json").write_text(json.dumps({
        "schema": 1, "id": finding_id, "captures": captures,
        "vendor_sources": [{"url": "https://www.dell.com/support", "text": source,
                            "sha256": hashlib.sha256(source.encode()).hexdigest()}],
    }), encoding="utf-8")
    result = evaluate(finding_id, tmp_path)
    assert result["status"] == "pass" and result["fail"] == result["could_not_run"] == 0, result

    capture_path = tmp_path / "capture.json"
    evidence = json.loads(capture_path.read_text(encoding="utf-8"))
    cold_binding = next(row for row in evidence["captures"]
                        if row["name"] == "cold_after" and row["argv"][0] == "lspci")
    cold_binding["stdout"] = cold_binding["stdout"].replace("in use: r8127", "in use: r8169")
    capture_path.write_text(json.dumps(evidence), encoding="utf-8")
    negative = evaluate(finding_id, tmp_path)
    assert negative["status"] == "fail" and negative["fail"] == 1, negative


def test_desktop_incident_separates_ssh_greeter_and_package_rollback(tmp_path: Path) -> None:
    finding_id = "FEATURE-FORUM-DESKTOP-SESSION-POSTUPDATE-01"
    source = (
        "Dell Inc. Product X board B BIOS X1 kernel 6.17.0, supported desktop package 46.1 and 46.2 "
        "with documented GNOME recovery and package rollback behavior on this exact stack."
    )

    def row(name: str, argv: list[str], stdout: str, seconds: int, rc: int = 0) -> dict[str, object]:
        return {"name": name, "argv": argv, "exit_code": rc, "stdout": stdout,
                "stderr": "", "captured_at": f"2026-10-03T00:02:{seconds:02d}+00:00"}

    active = "Id=2\nState=active\nType=wayland\nClass=user\nDisplay=:0\n"
    captures = [
        row("identity", ["dmidecode", "-t", "system"],
            "Manufacturer: Dell Inc.\nProduct Name: Product X\nBIOS Version: X1\n", 1),
        row("identity", ["uname", "-r"], "6.17.0\n", 2),
        row("incident", ["journalctl", "-b", "-u", "gdm3"],
            "Oct 03 00:00:01 host gdm: Failed to start GNOME Display Manager\n", 3),
        row("incident", ["ssh", "host", "true"], "", 4),
        row("incident", ["dpkg-query", "-W", "mutter"], "mutter 46.1\n", 5),
        row("control", ["loginctl", "show-session", "2"], active, 6),
        row("control", ["xrandr", "--query"], "HDMI-1 connected primary 3840x2160+0+0\n", 7),
        row("control", ["ssh", "host", "true"], "", 8),
        row("recovery", ["loginctl", "show-session", "2"], active, 9),
        row("recovery", ["xrandr", "--query"], "HDMI-1 connected primary 3840x2160+0+0\n", 10),
        row("recovery", ["dpkg-query", "-W", "mutter"], "mutter 46.2\n", 11),
        row("rollback", ["dpkg-query", "-W", "mutter"], "mutter 46.1\n", 12),
        row("rollback", ["ssh", "host", "true"], "", 13),
    ]
    (tmp_path / "capture.json").write_text(json.dumps({
        "schema": 1, "id": finding_id, "captures": captures,
        "vendor_sources": [{"url": "https://www.dell.com/support", "text": source,
                            "sha256": hashlib.sha256(source.encode()).hexdigest()}],
    }), encoding="utf-8")
    result = evaluate(finding_id, tmp_path)
    assert result["status"] == "pass" and result["fail"] == result["could_not_run"] == 0, result

    evidence_path = tmp_path / "capture.json"
    evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
    recovery = next(row for row in evidence["captures"] if row["name"] == "recovery" and row["argv"][0] == "loginctl")
    recovery["stdout"] = "Id=2\nState=closing\nType=wayland\nClass=user\nDisplay=:0\n"
    evidence_path.write_text(json.dumps(evidence), encoding="utf-8")
    failed = evaluate(finding_id, tmp_path)
    assert failed["status"] == "fail" and failed["fail"] == 1, failed


@pytest.mark.parametrize(
    ("observation", "expected"),
    [
        ({"session_classification": "headless", "ssh_exit_code": 0}, "headless"),
        ({"session_classification": "greeter", "ssh_exit_code": 0}, "greeter_login_loop"),
        ({"session_classification": "active_session", "display_connected": True, "ssh_exit_code": 0}, "healthy_desktop"),
        ({"session_failure_signatures": ["gdm-failed"], "ssh_exit_code": 0}, "session_failure"),
        ({"ssh_exit_code": 255}, "host_reachability_failed_total_host_state_unknown"),
    ],
)
def test_desktop_classifier_keeps_host_and_session_states_distinct(
    observation: dict[str, object], expected: str,
) -> None:
    assert _classify_desktop_state(observation) == expected


def test_eee_direct_link_ab_switch_control_and_rollback_pass_from_native_outputs(tmp_path: Path) -> None:
    finding_id = "FORUM-00-REALTEK-EEE-DIRECT-LINK"
    source = (
        "Dell Inc. Product X board B BIOS X1 kernel 6.14.0-1015-nvidia r8127 11.014.00-NAPI "
        "Intel I225-V EEE direct-link compatibility advisory; disable EEE only on this affected pair. "
        "A switch-connected control remains supported and EEE must be restored to its original negotiated state."
    )

    def row(name: str, argv: list[str], stdout: str, seconds: int, rc: int = 0) -> dict[str, object]:
        return {"name": name, "argv": argv, "exit_code": rc, "stdout": stdout,
                "stderr": "", "captured_at": f"2026-10-03T00:03:{seconds:02d}+00:00"}

    captures = [
        row("identity", ["dmidecode", "-t", "system"],
            "Manufacturer: Dell Inc.\nProduct Name: Product X\nBIOS Version: X1\n", 1),
        row("identity", ["uname", "-r"], "6.14.0-1015-nvidia\n", 2),
        row("identity", ["ethtool", "-i", "enP7s7"],
            "driver: r8127\nversion: 11.014.00-NAPI\nfirmware-version: 1.2\nbus-info: 0007:01:00.0\n", 3),
        row("identity", ["lldpctl", "enP7s7"], "SysName: Intel I225-V peer\nSysDescr: I225-V\n", 4),
        row("identity", ["ethtool", "--show-eee", "enP7s7"],
            "EEE status: enabled - active\nLink partner advertised EEE link modes: 100baseT/Full\n", 5),
    ]
    for phase, start, peer, state, counters, family_losses, ssh_count in [
        ("direct_eee_on", 6, "Intel I225-V", "enabled - active", [10, 11, 12, 13], (20, 20), 0),
        ("direct_eee_off", 20, "Intel I225-V", "disabled", [13, 13, 13, 13], (0, 0), 3),
        ("switch_control", 34, "NETGEAR Switch", "enabled - active", [4, 4, 4, 4], (0, 0), 3),
    ]:
        captures.append(row(phase, ["lldpctl", "enP7s7"], f"SysName: {peer}\n", start))
        captures.append(row(phase, ["ethtool", "--show-eee", "enP7s7"], f"EEE status: {state}\n", start + 1))
        for offset, counter in enumerate(counters, 2):
            captures.append(row(phase, ["ethtool", "-S", "enP7s7"],
                                f"link_down_events: {counter}\n", start + offset))
        for offset, (family, loss) in enumerate(zip(("ipv4", "ipv6"), family_losses, strict=True), 6):
            flag = "-4" if family == "ipv4" else "-6"
            captures.append(row(phase, ["ping", flag, "-c", "10", "192.0.2.2" if family == "ipv4" else "2001:db8::2"],
                                f"10 packets transmitted, {10 - loss // 10} received, {loss}% packet loss\n",
                                start + offset))
        for offset in range(ssh_count):
            captures.append(row(phase, ["ssh", "management-peer", "true"], "", start + 8 + offset))
    captures.extend([
        row("rollback", ["ethtool", "--show-eee", "enP7s7"], "EEE status: enabled - active\n", 50),
        row("rollback", ["ping", "-4", "-c", "10", "192.0.2.2"], "10 packets transmitted, 10 received, 0% packet loss\n", 51),
        row("rollback", ["ping", "-6", "-c", "10", "2001:db8::2"], "10 packets transmitted, 10 received, 0% packet loss\n", 52),
    ])
    (tmp_path / "capture.json").write_text(json.dumps({
        "schema": 1, "id": finding_id, "captures": captures,
        "vendor_sources": [{"url": "https://www.intel.com/support", "text": source,
                            "sha256": hashlib.sha256(source.encode()).hexdigest()}],
    }), encoding="utf-8")
    result = evaluate(finding_id, tmp_path)
    assert result["status"] == "pass" and result["fail"] == result["could_not_run"] == 0, result

    evidence_path = tmp_path / "capture.json"
    evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
    switch_stat = [row for row in evidence["captures"]
                   if row["name"] == "switch_control" and row["argv"][:2] == ["ethtool", "-S"]][-1]
    switch_stat["stdout"] = "link_down_events: 5\n"
    evidence_path.write_text(json.dumps(evidence), encoding="utf-8")
    failed = evaluate(finding_id, tmp_path)
    assert failed["status"] == "fail" and failed["fail"] == 1, failed


def test_rescue_boot_and_verified_service_restore_pass_from_native_outputs(tmp_path: Path) -> None:
    finding_id = "FEATURE-FORUM-RESCUE-RUNBOOK-01"
    source = (
        "Dell Inc. Product X board B BIOS X1 kernel 6.17.0 supports this OEM rescue entry, "
        "its authenticated console path, network limits, and return to the normal boot target; "
        "this tuple is specific to Product X and BIOS X1."
    )

    def row(name: str, argv: list[str], stdout: str, seconds: int) -> dict[str, object]:
        return {"name": name, "argv": argv, "exit_code": 0, "stdout": stdout,
                "stderr": "", "captured_at": f"2026-10-03T00:04:{seconds:02d}+00:00"}

    unit = tmp_path / "canary" / "service.service"
    unit.parent.mkdir()
    content = b"[Service]\nExecStart=/usr/local/bin/canary\n"
    unit.write_bytes(content)
    unit.chmod(0o640)
    manifest = {"path": "canary/service.service", "suspended_path": "canary/service.service.disabled",
                "sha256": hashlib.sha256(content).hexdigest(), "mode": 0o640,
                "expiry": "2026-10-04T00:00:00+00:00", "watcher": "ops-canary@example.invalid"}
    (tmp_path / "service-restore-manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    captures = [
        row("oem_identity", ["dmidecode", "-t", "system"],
            "Manufacturer: Dell Inc.\nProduct Name: Product X\nBIOS Version: X1\n", 1),
        row("oem_identity", ["uname", "-r"], "6.17.0\n", 2),
        row("rescue_entry", ["efibootmgr", "-v"],
            "BootCurrent: 0001\nBoot0001* Ubuntu\nBoot0007* OEM rescue\n", 3),
        row("rescue_boot", ["journalctl", "-b", "-o", "json"],
            '{"_BOOT_ID":"12345678-1234-1234-1234-123456789abc","MESSAGE":"rescue.target"}\n', 4),
        row("rescue_boot", ["efibootmgr", "-v"], "BootCurrent: 0007\n", 5),
        row("rescue_boot", ["cat", "/proc/cmdline"], "root=/dev/nvme0n1p2 systemd.unit=rescue.target\n", 6),
        row("normal_boot", ["journalctl", "-b", "-o", "json"],
            '{"_BOOT_ID":"22345678-1234-1234-1234-123456789abc","MESSAGE":"default.target"}\n', 7),
        row("restoration", ["journalctl", "-b", "-o", "json"],
            '{"_BOOT_ID":"32345678-1234-1234-1234-123456789abc","MESSAGE":"normal.target"}\n', 8),
        row("restoration", ["efibootmgr", "-v"], "BootCurrent: 0001\n", 9),
        row("restoration", ["ip", "route", "get", "192.0.2.10"], "192.0.2.10 via 192.0.2.1 dev enP7s7 src 192.0.2.20\n", 10),
    ]
    (tmp_path / "capture.json").write_text(json.dumps({
        "schema": 1, "id": finding_id, "captures": captures,
        "vendor_sources": [{"url": "https://www.dell.com/support", "text": source,
                            "sha256": hashlib.sha256(source.encode()).hexdigest()}],
    }), encoding="utf-8")
    result = evaluate(finding_id, tmp_path)
    assert result["status"] == "pass" and result["fail"] == result["could_not_run"] == 0, result

    # Expiry is judged against the restoration capture (2026-10-03), not the day the verifier runs.
    expired = {**manifest, "expiry": "2026-10-02T00:00:00+00:00"}
    (tmp_path / "service-restore-manifest.json").write_text(json.dumps(expired), encoding="utf-8")
    late = evaluate(finding_id, tmp_path)
    assert late["status"] == "fail" and late["reason"] == "service restore was captured after the manifest expiry", late
    (tmp_path / "service-restore-manifest.json").write_text(json.dumps(manifest), encoding="utf-8")

    evidence = json.loads((tmp_path / "capture.json").read_text(encoding="utf-8"))
    rescue_cmdline = next(row for row in evidence["captures"]
                          if row["name"] == "rescue_boot" and row["argv"][0] == "cat")
    rescue_cmdline["stdout"] = "root=/dev/nvme0n1p2 systemd.unit=graphical.target\n"
    (tmp_path / "capture.json").write_text(json.dumps(evidence), encoding="utf-8")
    failed = evaluate(finding_id, tmp_path)
    assert failed["status"] == "fail" and failed["fail"] == 1, failed
