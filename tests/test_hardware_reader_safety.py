"""Hardware verifier inputs stay bounded, strict-JSON, regular, and no-follow."""
from __future__ import annotations

import os
import json
from pathlib import Path
from typing import Any, Callable

from tools import forum_finding, forum_hardware_subjects, provider_trace
from tools import verify_clock_cap_tradeoff, verify_gpu_clock_cap_ab
from tools import verify_usb_hid_postupdate, verify_wifi_isolation


READERS: tuple[tuple[str, Callable[[Path], object]], ...] = (
    ("gpu", verify_gpu_clock_cap_ab._json),
    ("usb", verify_usb_hid_postupdate._read),
    ("wifi", verify_wifi_isolation._read_capture),
    ("forum", forum_finding._read_json),
    ("forum_subject", lambda path: forum_hardware_subjects._read_capture(path)),
    ("provider", provider_trace.analyze_file),
    ("tradeoff", verify_clock_cap_tradeoff.verify),
)


def _rejected(kind: str, path: Path) -> bool:
    value = dict(READERS)[kind](path)
    if kind == "provider":
        return isinstance(value, dict) and value.get("could_not_run_count") == 1
    if kind == "tradeoff":
        return isinstance(value, dict) and value.get("status") == "unknown"
    if kind == "forum_subject":
        return isinstance(value, tuple) and value[0] is None
    if kind == "wifi":
        return value is None
    return value is None


def test_all_file_readers_reject_duplicate_keys_and_nonfinite_json(tmp_path: Path) -> None:
    for index, (kind, reader) in enumerate(READERS):
        duplicate = tmp_path / f"duplicate-{index}.json"
        duplicate.write_text('{"id":"one","id":"two"}', encoding="utf-8")
        assert _rejected(kind, duplicate)

        nonfinite = tmp_path / f"nonfinite-{index}.json"
        nonfinite.write_text('{"value":NaN}', encoding="utf-8")
        assert _rejected(kind, nonfinite)


def test_all_file_readers_reject_symlink_and_fifo_inputs(tmp_path: Path) -> None:
    target = tmp_path / "target.json"
    target.write_text("{}", encoding="utf-8")
    symlink = tmp_path / "linked.json"
    symlink.symlink_to(target)
    for kind, _reader in READERS:
        assert _rejected(kind, symlink), kind

        fifo = tmp_path / f"{kind}.fifo"
        os.mkfifo(fifo)
        assert _rejected(kind, fifo), kind


def test_all_file_readers_reject_symlinked_ancestor(tmp_path: Path) -> None:
    real = tmp_path / "real"
    real.mkdir()
    (real / "capture.json").write_text("{}", encoding="utf-8")
    alias = tmp_path / "alias"
    alias.symlink_to(real, target_is_directory=True)
    for kind, _reader in READERS:
        assert _rejected(kind, alias / "capture.json"), kind


def test_provider_evaluator_accepts_raw_trace_for_investigation_without_closing(tmp_path: Path) -> None:
    directory = tmp_path / "provider"
    directory.mkdir()
    events = [
        {"event": "request", "request_id": "r1", "requested_provider": "gpu"},
        {"event": "worker", "request_id": "r1", "worker_id": "before", "pid": 10},
        {"event": "provider", "request_id": "r1", "worker_id": "before", "provider": "CUDAExecutionProvider"},
        {"event": "latency", "request_id": "r1", "worker_id": "before", "milliseconds": 10},
        {"event": "restart", "request_id": "r1", "old_worker_id": "before", "new_worker_id": "after"},
        {"event": "worker", "request_id": "r1", "worker_id": "after", "pid": 11},
        {"event": "provider", "request_id": "r1", "worker_id": "after", "provider": "CPUExecutionProvider"},
        {"event": "latency", "request_id": "r1", "worker_id": "after", "milliseconds": 200},
    ]
    trace = directory / "provider-trace.jsonl"
    trace.write_text("\n".join(json.dumps(event) for event in events) + "\n", encoding="utf-8")

    result = forum_finding._evaluate_provider_fallback(directory)

    assert result["status"] == "unknown", result
    assert result["could_not_run"] == 1, result
    assert str(trace) in result["files"]
    assert "real request trace recomputed" in result["reason"]


def test_wifi_oem_tuple_is_bound_to_the_adapter_seen_in_the_roam_trace() -> None:
    rows: list[dict[str, Any]] = [
        {"cmd": "dmidecode -t system", "exit": 0,
         "stdout": "Manufacturer: ASUSTeK\nProduct Name: GX10\nBIOS Version: 1.0", "stderr": ""},
        {"cmd": "uname -r", "exit": 0, "stdout": "6.17.0-1029-nvidia", "stderr": ""},
        {"cmd": "modinfo mt7925e", "exit": 0, "stdout": "version: 1.0", "stderr": ""},
        {"cmd": "nmcli --version", "exit": 0, "stdout": "nmcli tool, version 1.48", "stderr": ""},
        {"cmd": "cat /etc/os-release", "exit": 0,
         "stdout": 'PRETTY_NAME="NVIDIA DGX OS 7.5.0"', "stderr": ""},
        {"cmd": "wpa_supplicant -v", "exit": 0, "stdout": "wpa_supplicant v2.10", "stderr": ""},
        {"cmd": "ethtool -i wlan0", "exit": 0,
         "stdout": "driver: mt7925e\nversion: 1.0\nfirmware-version: 202401", "stderr": ""},
        {"cmd": "iw dev wlan0 link", "exit": 0,
         "stdout": "Connected to AA:AA:AA:AA:AA:AA\nSSID: Home\nfreq: 5180", "stderr": ""},
    ]

    assert verify_wifi_isolation._observed_identity(rows) is not None
    rows[6]["cmd"] = "ethtool -i eth0"
    assert verify_wifi_isolation._observed_identity(rows) is None


def test_clock_tradeoff_evaluator_keeps_observation_distinct_from_experiment(tmp_path: Path) -> None:
    capture = {
        "thermal_zones": [], "hwmon": [],
        "thermal_zone_scan": {"count": 0}, "hwmon_scan": {"count": 0},
        "could_not_run": 0, "status": "observed",
        "host": {"dmi": {key: {"status": "ok", "value": value} for key, value in (
            ("sys_vendor", "NVIDIA"), ("product_name", "DGX Spark"), ("product_version", "1.0"))}},
    }
    path = tmp_path / "thermal.json"
    path.write_text(json.dumps(capture), encoding="utf-8")
    result = verify_clock_cap_tradeoff.verify(path)
    assert result["status"] == "unknown" and result["checks"]["oem_identity"] == "pass", result

    capture["thermal_zone_scan"] = {"count": 1}
    path.write_text(json.dumps(capture), encoding="utf-8")
    result = verify_clock_cap_tradeoff.verify(path)
    assert result["status"] == "fail" and "counts disagree" in result["reason"], result

    path.write_text("[]", encoding="utf-8")
    result = verify_clock_cap_tradeoff.verify(path)
    assert result["status"] == "fail" and "JSON object" in result["reason"], result
