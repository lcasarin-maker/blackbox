"""Unit checks for GPU measurement semantics, independent of host capture availability."""
from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from tools import verify_gpu_clock_cap_ab as gpu


def _row(command: str, output: str, *, exit_code: int = 0, seconds: int = 0) -> dict[str, Any]:
    stamp = datetime(2026, 10, 4, tzinfo=UTC) + timedelta(seconds=seconds)
    return {"cmd": command, "stdout": output, "stderr": "", "exit": exit_code,
            "captured_at": stamp.isoformat()}


def _benchmark(**updates: Any) -> str:
    metrics: dict[str, Any] = {
        "duration_seconds": 30,
        "tokens_per_second": 100,
        "completed_requests": 10,
        "failed_requests": 0,
        "p50_latency_ms": 40,
        "p99_latency_ms": 70,
        "model_sha256": "model-digest",
        "image_digest": "image-digest",
        "input_sha256": "input-digest",
        "concurrency": 2,
        "max_new_tokens": 128,
    }
    metrics.update(updates)
    return json.dumps(metrics)


def test_benchmark_requires_finite_complete_metrics_and_stable_workload_identity() -> None:
    row = _row("llm-benchmark --json", _benchmark())
    parsed = gpu._benchmark(row)
    assert parsed is not None and parsed["tokens_per_second"] == 100.0
    assert gpu._benchmark(_row("benchmark", _benchmark(p99_latency_ms=39))) is None
    assert gpu._benchmark(_row("benchmark", _benchmark(failed_requests=-1))) is None
    assert gpu._benchmark(_row("benchmark", _benchmark(concurrency=True))) is None
    assert gpu._benchmark(_row("benchmark", _benchmark(tokens_per_second=float("inf")))) is None
    assert gpu._benchmark(_row("benchmark", "[]")) is None


def test_telemetry_requires_exact_fields_finite_ranges_and_nonempty_throttle_output() -> None:
    query = "nvidia-smi --query-gpu=clocks.current.graphics,power.draw,temperature.gpu,utilization.gpu,clocks_throttle_reasons.active --format=csv"
    valid = _row(query, "1800, 240, 65, 70, 0x00000000")
    reading = gpu._telemetry(valid)
    assert reading is not None and reading["clock_mhz"] == 1800
    assert gpu._telemetry(_row(query, "1800, 240, 65, 101, 0")) is None
    assert gpu._telemetry(_row(query, "nan, 240, 65, 70, 0")) is None
    assert gpu._telemetry(_row(query, "1800, 240, 65, 70,")) is None
    assert gpu._telemetry(_row("nvidia-smi --query-gpu=power.draw", "1800, 240, 65, 70, 0")) is None


def test_plan_is_predeclared_captured_exactly_and_requires_bounded_soak(tmp_path: Path) -> None:
    plan = {"stock_policy": [300, 2800], "capped_policy": [300, 2300],
            "soak_seconds": 600, "max_sample_gap_seconds": 60}
    rows = [_row("cat clock-cap-plan.json", json.dumps(plan))]
    parsed, error = gpu._plan({"experiment_plan": plan}, rows, tmp_path / "capture.json")
    assert parsed == plan and error is None

    bad_plan = {**plan, "capped_policy": [300, 2900]}
    parsed, error = gpu._plan({"experiment_plan": bad_plan}, rows, tmp_path / "capture.json")
    assert parsed is None and error is not None and error["status"] == "fail"

    missing = {**plan, "max_sample_gap_seconds": None}
    parsed, error = gpu._plan({"experiment_plan": missing}, rows, tmp_path / "capture.json")
    assert parsed is None and error is not None and error["status"] == "unknown"

    mismatch = [_row("cat clock-cap-plan.json", json.dumps({**plan, "soak_seconds": 601}))]
    parsed, error = gpu._plan({"experiment_plan": plan}, mismatch, tmp_path / "capture.json")
    assert parsed is None and error is not None and "differs" in error["reason"]


def test_measurement_rejects_nonzero_workload_and_cap_exceedance(tmp_path: Path) -> None:
    plan = {"capped_policy": [300, 2100], "max_sample_gap_seconds": 60}
    failed = _row("llm-benchmark --json", _benchmark(), exit_code=9)
    error = gpu._consume_measurement({"row": failed, "phase": "baseline", "plan": plan,
                                      "path": tmp_path / "capture.json", "runs": [], "samples": []})
    assert error is not None and error["status"] == "fail"

    query = "nvidia-smi --query-gpu=clocks.current.graphics,power.draw,temperature.gpu,utilization.gpu,clocks_throttle_reasons.active --format=csv"
    capped = _row(query, "2200, 240, 65, 70, 0")
    error = gpu._consume_measurement({"row": capped, "phase": "capped", "plan": plan,
                                      "path": tmp_path / "capture.json", "runs": [], "samples": []})
    assert error is not None and "exceeded" in error["reason"]


def test_measurement_averaging_inputs_require_repeats_and_gap_bound(tmp_path: Path) -> None:
    query = "nvidia-smi --query-gpu=clocks.current.graphics,power.draw,temperature.gpu,utilization.gpu,clocks_throttle_reasons.active --format=csv"
    rows = [
        _row("llm-benchmark --json", _benchmark(), seconds=1),
        _row(query, "1800, 240, 65, 70, 0", seconds=2),
        _row("llm-benchmark --json", _benchmark(), seconds=3),
        _row(query, "1800, 240, 65, 70, 0", seconds=4),
    ]
    plan = {"max_sample_gap_seconds": 60, "capped_policy": [300, 2100]}
    runs, error = gpu._measurements({"rows": rows, "start": 0, "end": len(rows),
                                     "phase": "baseline", "plan": plan,
                                     "path": tmp_path / "capture.json"})
    assert error is None and runs is not None and len(runs) == 2

    runs, error = gpu._measurements({"rows": rows[:2], "start": 0, "end": 2,
                                     "phase": "baseline", "plan": plan,
                                     "path": tmp_path / "capture.json"})
    assert runs is None and error is not None and "repeats" in error["reason"]

    rows[3]["captured_at"] = (datetime(2026, 10, 4, tzinfo=UTC) + timedelta(seconds=100)).isoformat()
    runs, error = gpu._measurements({"rows": rows, "start": 0, "end": len(rows),
                                     "phase": "baseline", "plan": plan,
                                     "path": tmp_path / "capture.json"})
    assert runs is None and error is not None and "gap" in error["reason"]


def test_supported_clock_parser_and_tuple_comparison_do_not_accept_partial_pairs() -> None:
    rows = [_row("nvidia-smi -q -d SUPPORTED_CLOCKS",
                 "Graphics : 1800 MHz\nGraphics : 2100 MHz\nMemory : 8000 MHz")]
    assert gpu._supported_graphics_clocks(rows) == {1800, 2100}
    assert gpu._supported_graphics_clocks([_row("nvidia-smi -q", "Graphics : 1800 MHz")]) == set()

    first = gpu._benchmark(_row("benchmark", _benchmark()))
    changed = gpu._benchmark(_row("benchmark", _benchmark(image_digest="different-image")))
    assert first is not None and changed is not None
    assert gpu._matched([first, first], Path("capture.json"))[1] is None
    mismatch, error = gpu._matched([first, changed], Path("capture.json"))
    assert mismatch is None and error is not None and "tuple" in error["reason"]


def test_capture_schema_and_policy_readback_remain_cnr_until_native_api_exists(tmp_path: Path) -> None:
    path = tmp_path / "commands.json"
    path.write_text(json.dumps({"id": gpu.FINDING, "commands": []}), encoding="utf-8")
    assert gpu._capture(path) is None

    row = _row("nvidia-smi -lgc 300,2100", "")
    assert gpu._csv_policy(row) is None
    policy = gpu._policy_window([], {"stock_policy": [300, 2800], "capped_policy": [300, 2100]}, path)
    assert isinstance(policy, dict)
    assert policy["status"] == "unknown" and "readbacks" in policy["reason"]


def _identity_rows() -> list[dict[str, Any]]:
    return [
        _row("dmidecode -t system",
             "Manufacturer: Example OEM\nProduct Name: GB10 test system\nBIOS Version: 1.0"),
        _row("uname -r", "6.17.0-test"),
        _row("cat /etc/os-release", "PRETTY_NAME=Test OS"),
        _row("modinfo nvidia", "version: 580.178.04"),
        _row("nvidia-smi --query-gpu=name,driver_version --format=csv", "GB10, 580.178.04"),
        _row("fwupdmgr get-devices", "├─System Firmware:\n│     Device ID: 1234\n│     Current version: 1.0"),
    ]


def test_full_evaluator_stops_on_command_failure_or_missing_identity_before_claiming_trial(tmp_path: Path) -> None:
    path = tmp_path / "capture.json"
    failed = _identity_rows()
    failed.append(_row("nvidia-smi -q", "", exit_code=2))
    result = gpu._verify({}, failed, path)
    assert result["status"] == "unknown" and "without an explicit hardware-fault diagnostic" in result["reason"]

    result = gpu._verify({}, [_row("uname -r", "6.17")], path)
    assert result["status"] == "unknown" and "tuple incomplete" in result["reason"]

    result = gpu._verify({}, _identity_rows(), path)
    assert result["status"] == "unknown" and "plan absent" in result["reason"]

    plan = {"stock_policy": [300, 2800], "capped_policy": [300, 2100],
            "soak_seconds": 600, "max_sample_gap_seconds": 60}
    rows = _identity_rows() + [_row("cat clock-cap-plan.json", json.dumps(plan))]
    result = gpu._verify({"experiment_plan": plan}, rows, path)
    assert result["status"] == "unknown" and "readbacks" in result["reason"]

    invalid = {**plan, "capped_policy": [300, 2900]}
    rows[-1] = _row("cat clock-cap-plan.json", json.dumps(invalid))
    result = gpu._verify({"experiment_plan": invalid}, rows, path)
    assert result["status"] == "fail" and "lower the stock ceiling" in result["reason"]


def test_support_gates_require_kernel_pstore_idle_load_unload_and_predeclared_soak(tmp_path: Path) -> None:
    query = "nvidia-smi --query-gpu=clocks.current.graphics,power.draw,temperature.gpu,utilization.gpu,clocks_throttle_reasons.active --format=csv"
    rows = [
        _row("cat /sys/fs/pstore/console-ramoops", "empty", seconds=0),
        _row("journalctl -k", "kernel output", seconds=1),
        _row(query, "1500, 80, 45, 2, 0", seconds=2),
        _row("nvidia-smi -lgc 300,2100", "", seconds=3),
        _row("model load", "loaded", seconds=4),
        _row("model unload", "unloaded", seconds=5),
        _row("nvidia-smi -lgc 300,2800", "", seconds=16),
    ]
    plan = {"soak_seconds": 10}
    assert gpu._support_gates(rows, 3, 6, plan, tmp_path / "capture.json") is None
    missing_pstore = gpu._support_gates(rows[1:], 2, 5, plan, tmp_path / "capture.json")
    assert missing_pstore is not None and missing_pstore["status"] == "unknown"
    short = dict(rows[6], captured_at=rows[6]["captured_at"].replace(":16", ":10"))
    rows[6] = short
    gate = gpu._support_gates(rows, 3, 6, plan, tmp_path / "capture.json")
    assert gate is not None and gate["status"] == "unknown" and "soak" in gate["reason"]
