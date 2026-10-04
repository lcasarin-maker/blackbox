"""Recompute a clock-cap experiment from timestamped native command output."""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import math
import re
import shlex
from datetime import datetime
from pathlib import Path
import sys
from typing import Any, cast

from tools.capture_io import read_regular_bytes, strict_json_loads

ROOT = Path(__file__).resolve().parents[1]
FINDING = "FEATURE-FORUM-GPU-CLOCK-CAP-AB-01"
CAPTURE_LIMIT = 4_000_000
ROW_LIMIT = 20_000


def _result(status: str, reason: str, files: list[str]) -> dict[str, Any]:
    return {"status": status, "reason": reason, "files": files,
            "fail": int(status == "fail"), "could_not_run": int(status == "unknown")}


def _json(path: Path) -> dict[str, Any] | None:
    try:
        raw = read_regular_bytes(path, CAPTURE_LIMIT)
        if len(raw) > CAPTURE_LIMIT:
            return None
        value = strict_json_loads(raw.decode("utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError, RecursionError):
        return None
    return value if isinstance(value, dict) else None


def _capture(path: Path) -> tuple[dict[str, Any], list[dict[str, Any]]] | None:
    data = _json(path)
    if data is None or data.get("id") != FINDING or not isinstance(data.get("commands"), list):
        return None
    rows = data["commands"]
    if not rows or len(rows) > ROW_LIMIT or any(
        not isinstance(row, dict) or not isinstance(row.get("cmd"), str) or not row["cmd"].strip()
        or type(row.get("exit")) is not int or not isinstance(row.get("stdout"), str)
        or not isinstance(row.get("stderr", ""), str) or not isinstance(row.get("captured_at"), str)
        for row in rows
    ):
        return None
    try:
        stamps = [datetime.fromisoformat(row["captured_at"].replace("Z", "+00:00")) for row in rows]
    except ValueError:
        return None
    if any(stamp.tzinfo is None for stamp in stamps) or any(a >= b for a, b in zip(stamps, stamps[1:])):
        return None
    return data, rows


def _timestamp(row: dict[str, Any]) -> datetime | None:
    try:
        return datetime.fromisoformat(row["captured_at"].replace("Z", "+00:00"))
    except (KeyError, TypeError, ValueError):
        return None


def _command_args(row: dict[str, Any]) -> list[str]:
    try:
        argv = shlex.split(row["cmd"])
    except (KeyError, TypeError, ValueError):
        return []
    while argv and Path(argv[0]).name in {"sudo", "doas"}:
        argv = argv[1:]
        while argv and argv[0] in {"-n", "--non-interactive", "-E", "--preserve-env", "--"}:
            argv = argv[1:]
        if argv and argv[0] in {"-u", "--user", "-g", "--group"}:
            argv = argv[2:]
    return argv


def _runs_program(row: dict[str, Any], program: str, *, success: bool = True) -> bool:
    argv = _command_args(row)
    return (bool(argv) and Path(argv[0]).name == program
            and (not success or row.get("exit") == 0))


def _clock_command(row: dict[str, Any], range_text: str) -> bool:
    argv = _command_args(row)
    return (_runs_program(row, "nvidia-smi") and len(argv) >= 3
            and argv[1] == "-lgc" and argv[2] == range_text)


def _csv_policy(row: dict[str, Any]) -> tuple[int, int] | None:
    # nvidia-smi exposes current/max and supported clocks, not the active -lgc
    # locked range.  A caller-created min.graphics query is unsupported on GB10
    # and cannot be treated as a policy readback.
    del row
    return None


def _telemetry(row: dict[str, Any]) -> dict[str, float | str] | None:
    required = ("clocks.current.graphics", "power.draw", "temperature.gpu", "utilization.gpu", "clocks_throttle_reasons.active")
    argv = _command_args(row)
    if (not _runs_program(row, "nvidia-smi") or len(argv) < 2
            or not all(value in " ".join(argv[1:]) for value in required)):
        return None
    fields = [item.strip() for item in row["stdout"].strip().split(",")]
    if len(fields) != 5 or not fields[4]:
        return None
    try:
        values = [float(item) for item in fields[:4]]
    except ValueError:
        return None
    if not all(math.isfinite(value) and value >= 0 for value in values) or values[3] > 100:
        return None
    return {"clock_mhz": values[0], "power_w": values[1], "temperature_c": values[2],
            "utilization_pct": values[3], "throttle_reason": fields[4]}


def _benchmark(row: dict[str, Any]) -> dict[str, Any] | None:
    try:
        value = strict_json_loads(row["stdout"])
    except (json.JSONDecodeError, ValueError, RecursionError):
        return None
    if not isinstance(value, dict):
        return None
    numeric = ("duration_seconds", "tokens_per_second", "completed_requests", "failed_requests",
               "p50_latency_ms", "p99_latency_ms")
    if any(not isinstance(value.get(key), (int, float)) or isinstance(value.get(key), bool)
           or not math.isfinite(value[key]) for key in numeric):
        return None
    if any(not isinstance(value.get(key), str) or not value[key].strip()
           for key in ("model_sha256", "image_digest", "input_sha256")):
        return None
    if any(type(value.get(key)) is not int or value[key] <= 0 for key in ("concurrency", "max_new_tokens")):
        return None
    if (value["duration_seconds"] <= 0 or value["tokens_per_second"] <= 0
            or value["completed_requests"] <= 0 or value["failed_requests"] < 0
            or value["p50_latency_ms"] <= 0 or value["p99_latency_ms"] < value["p50_latency_ms"]):
        return None
    for key in numeric:
        value[key] = float(value[key])
    return value


def _identity(rows: list[dict[str, Any]]) -> bool:
    success_rows = [row for row in rows if row.get("exit") == 0]
    dmi_rows = [row for row in success_rows if _runs_program(row, "dmidecode")
                and _command_args(row)[1:3] == ["-t", "system"]]
    kernel_rows = [row for row in success_rows if _runs_program(row, "uname")
                   and "-r" in _command_args(row)[1:]]
    os_rows = [row for row in success_rows if _runs_program(row, "cat")
               and "/etc/os-release" in _command_args(row)[1:]]
    module_rows = [row for row in success_rows if _runs_program(row, "modinfo")
                   and "nvidia" in _command_args(row)[1:]]
    driver_rows = [row for row in success_rows if _runs_program(row, "nvidia-smi")
                   and any("driver_version" in arg for arg in _command_args(row)[1:])]
    firmware_rows = [row for row in success_rows if _runs_program(row, "fwupdmgr")
                     and "get-devices" in _command_args(row)[1:]]
    dmi_pattern = re.compile(r"(?im)^Manufacturer:\s*\S.*\n(?:.*\n)*?Product Name:\s*\S.*\n(?:.*\n)*?BIOS Version:\s*\S.+")
    driver_version_pattern = re.compile(r"(?i)^(?:driver_version\s*,\s*)?v?\d+(?:\.\d+){1,3}$")
    module_version_pattern = re.compile(r"(?im)^version:\s*\d+(?:\.\d+){1,3}$")
    return (any(dmi_pattern.search(row["stdout"]) for row in dmi_rows)
            and any(row["stdout"].strip() for row in kernel_rows)
            and any(re.search(r"(?m)^PRETTY_NAME=", row["stdout"]) for row in os_rows)
            and any(module_version_pattern.search(row["stdout"]) for row in module_rows)
            and any((version := _driver_version(row)) is not None
                    and driver_version_pattern.fullmatch(version) for row in driver_rows)
            and any(_system_firmware_version(row["stdout"]) for row in firmware_rows))


def _driver_version(row: dict[str, Any]) -> str | None:
    argv = _command_args(row)
    query = next((token.partition("=")[2] for token in argv[1:]
                  if token.startswith("--query-gpu=")), None)
    if not query:
        return None
    try:
        fields = next(csv.reader([query]))
        records = list(csv.reader(io.StringIO(row["stdout"])))
    except (csv.Error, TypeError):
        return None
    fields = [field.strip() for field in fields]
    if "driver_version" not in fields or not records:
        return None
    records = [[cell.strip() for cell in record] for record in records]
    if records[0] == fields:
        records = records[1:]
    if len(records) == 1 and len(records[0]) == len(fields) + 1 and records[0][:len(fields)] == fields:
        records[0] = records[0][len(fields):]
    if not records or len(records[0]) != len(fields):
        return None
    return records[0][fields.index("driver_version")]


def _system_firmware_version(output: str) -> bool:
    lines = output.splitlines()
    for index, line in enumerate(lines):
        if not re.search(r"(?i)^\s*[├└]─\s*(?:System Firmware|UEFI Device Firmware):\s*$", line):
            continue
        block = []
        for following in lines[index + 1:]:
            if re.match(r"^\s*[├└]─", following):
                break
            block.append(following)
        if any(re.match(r"^\s*[│ ]*Current version:\s*\S+", item) for item in block):
            return True
    return False


def _supported_graphics_clocks(rows: list[dict[str, Any]]) -> set[int]:
    row = next((item for item in rows if _runs_program(item, "nvidia-smi")
                and _command_args(item)[1:3] == ["-q", "-d"]
                and len(_command_args(item)) > 3 and _command_args(item)[3] == "SUPPORTED_CLOCKS"), None)
    if row is None:
        return set()
    return {int(value) for match in re.finditer(r"(?im)^\s*Graphics\s*:\s*(\d+)\s*MHz\s*$", row["stdout"])
            for value in [match.group(1)]}


def _plan(data: dict[str, Any], rows: list[dict[str, Any]], path: Path) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    plan = data.get("experiment_plan")
    if not isinstance(plan, dict):
        return None, _result("unknown", "predeclared experiment plan absent", [str(path)])
    pairs = (plan.get("stock_policy"), plan.get("capped_policy"))
    if any(not isinstance(pair, list) or len(pair) != 2 or any(type(n) is not int or n <= 0 for n in pair) for pair in pairs):
        return None, _result("unknown", "plan lacks concrete positive stock and capped clock ranges", [str(path)])
    stock = cast(list[int], pairs[0])
    capped = cast(list[int], pairs[1])
    if stock[0] != capped[0] or capped[1] >= stock[1]:
        return None, _result("fail", "planned cap must preserve the floor and lower the stock ceiling", [str(path)])
    if type(plan.get("soak_seconds")) is not int or plan["soak_seconds"] <= 0:
        return None, _result("unknown", "plan lacks a positive predeclared soak duration", [str(path)])
    if type(plan.get("max_sample_gap_seconds")) is not int or plan["max_sample_gap_seconds"] <= 0:
        return None, _result("unknown", "plan lacks a positive maximum telemetry gap", [str(path)])
    plan_row = next((row for row in rows if _runs_program(row, "cat")
                     and any(Path(arg).name == "clock-cap-plan.json" for arg in _command_args(row)[1:])), None)
    if plan_row is None or plan_row["exit"] != 0:
        return None, _result("unknown", "literal plan-file capture is missing", [str(path)])
    try:
        captured = strict_json_loads(plan_row["stdout"])
    except json.JSONDecodeError:
        return None, _result("fail", "captured experiment plan is malformed JSON", [str(path)])
    if captured != plan:
        return None, _result("fail", "captured plan content differs from the plan used by the evaluator", [str(path)])
    return plan, None


def _policy_window(rows: list[dict[str, Any]], plan: dict[str, Any], path: Path) -> tuple[int, int] | dict[str, Any]:
    stock = tuple(plan["stock_policy"])
    capped = tuple(plan["capped_policy"])
    initial = next((index for index, row in enumerate(rows) if index < len(rows)
                    and row["exit"] == 0 and _csv_policy(row) == stock), None)
    apply = next((index for index, row in enumerate(rows)
                  if row["exit"] == 0 and _clock_command(row, f"{stock[0]},{capped[1]}")), None)
    cap_readback = next((index for index, row in enumerate(rows)
                         if apply is not None and index > apply and _csv_policy(row) == capped), None)
    restore = next((index for index, row in enumerate(rows)
                    if apply is not None and index > apply and row["exit"] == 0
                    and _clock_command(row, f"{stock[0]},{stock[1]}")), None)
    restored_readback = next((index for index, row in enumerate(rows)
                              if restore is not None and index > restore and _csv_policy(row) == stock), None)
    if any(index is None for index in (initial, apply, cap_readback, restore, restored_readback)):
        return _result("unknown", "native stock/cap application and effective readbacks are incomplete", [str(path)])
    assert apply is not None and restore is not None and cap_readback is not None
    assert initial is not None and apply is not None and cap_readback is not None
    assert restore is not None and restored_readback is not None
    if not initial < apply < cap_readback < restore < restored_readback:
        return _result("fail", "effective clock policies were not applied and read back in stock/cap/rollback order", [str(path)])
    if capped[1] not in _supported_graphics_clocks(rows):
        return _result("fail", "requested cap ceiling is absent from nvidia-smi supported graphics clocks", [str(path)])
    return apply, restore


def _measurements(spec: dict[str, Any]) -> tuple[list[dict[str, Any]] | None, dict[str, Any] | None]:
    rows = spec["rows"]
    start = spec["start"]
    end = spec["end"]
    phase = spec["phase"]
    plan = spec["plan"]
    path = spec["path"]
    runs: list[dict[str, Any]] = []
    samples: list[tuple[datetime, dict[str, float | str]]] = []
    for index in range(start, end):
        error = _consume_measurement({"row": rows[index], "phase": phase, "plan": plan,
                                      "path": path, "runs": runs, "samples": samples})
        if error:
            return None, error
    if len(runs) < 2:
        return None, _result("unknown", f"at least two {phase} workload repeats are required", [str(path)])
    if len(samples) < 2:
        return None, _result("unknown", f"{phase} power/temperature/clock/throttle telemetry is incomplete", [str(path)])
    if any((right[0] - left[0]).total_seconds() > plan["max_sample_gap_seconds"]
           for left, right in zip(samples, samples[1:])):
        return None, _result("unknown", f"{phase} telemetry gap exceeds the predeclared maximum", [str(path)])
    return runs, None


def _consume_measurement(spec: dict[str, Any]) -> dict[str, Any] | None:
    row = spec["row"]
    phase = spec["phase"]
    plan = spec["plan"]
    path = spec["path"]
    runs = spec["runs"]
    samples = spec["samples"]
    stamp = _timestamp(row)
    if stamp is None:
        return _result("unknown", f"{phase} capture timestamp unavailable", [str(path)])
    reading = _telemetry(row) if row["exit"] == 0 else None
    if reading is not None:
        samples.append((stamp, reading))
        if phase == "capped" and float(reading["clock_mhz"]) > plan["capped_policy"][1]:
            return _result("fail", "measured graphics clock exceeded the applied cap", [str(path)])
    argv = _command_args(row)
    command = row["cmd"].lower()
    mentions_workload = "benchmark" in command or "inference" in command or "bench" in command
    executable = Path(argv[0]).name.lower() if argv else ""
    workload_runner = ("benchmark" in executable or "inference" in executable or "bench" in executable
                       or (executable in {"python", "python3", "uv"}
                           and any("benchmark" in arg.lower() or "inference" in arg.lower() or "bench" in arg.lower()
                                   for arg in argv[1:]))
                       or (executable == "vllm" and any(arg in {"bench", "benchmark"} for arg in argv[1:])))
    if mentions_workload and not workload_runner:
        return _result("unknown", f"{phase} workload command does not identify a native benchmark/inference runner", [str(path)])
    if not workload_runner:
        return None
    if row["exit"] != 0:
        return _result("fail", f"{phase} workload command returned nonzero", [str(path)])
    metrics = _benchmark(row)
    if metrics is None:
        return _result("unknown", f"{phase} workload output lacks complete raw identity/performance metrics", [str(path)])
    if metrics["failed_requests"] > 0:
        return _result("fail", f"{phase} workload recorded failed requests", [str(path)])
    runs.append(metrics)
    return None


def _matched(runs: list[dict[str, Any]], path: Path) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    keyset = ("model_sha256", "image_digest", "input_sha256", "concurrency", "max_new_tokens")
    signature = tuple(runs[0][key] for key in keyset)
    if any(tuple(row[key] for key in keyset) != signature for row in runs[1:]):
        return None, _result("fail", "workload repeats do not use one model/image/input/concurrency/token-limit tuple", [str(path)])
    return runs[0], None


def _support_gates(rows: list[dict[str, Any]], apply: int, restore: int,
                   plan: dict[str, Any], path: Path) -> dict[str, Any] | None:
    if not any("/sys/fs/pstore" in row["cmd"] and row["exit"] == 0 for row in rows):
        return _result("unknown", "pstore output is missing; crash evidence is incomplete", [str(path)])
    if not any("journalctl" in row["cmd"] and "-k" in row["cmd"] and row["exit"] == 0 for row in rows):
        return _result("unknown", "kernel journal output is missing", [str(path)])
    idle = [row for row in rows if row["exit"] == 0 and (reading := _telemetry(row)) is not None
            and float(reading["utilization_pct"]) < 5]
    if not idle:
        return _result("unknown", "no captured idle/control telemetry period", [str(path)])
    load_unload = {term: any(term in row["cmd"].lower() and row["exit"] == 0 and row["stdout"].strip()
                             for row in rows[apply + 1:restore]) for term in ("load", "unload")}
    if not all(load_unload.values()):
        return _result("unknown", "capped model load and unload observations are incomplete", [str(path)])
    first, last = _timestamp(rows[apply]), _timestamp(rows[restore])
    if first is None or last is None or (last - first).total_seconds() < plan["soak_seconds"]:
        return _result("unknown", "capped interval is shorter than the captured predeclared soak", [str(path)])
    return None


def _verify(data: dict[str, Any], rows: list[dict[str, Any]], path: Path) -> dict[str, Any]:
    files = [str(path)]
    failed_queries = [row for row in rows if row["exit"] != 0
                      and _runs_program(row, "nvidia-smi", success=False)]
    if any(re.search(r"(?i)(couldn't|could not) communicate with the NVIDIA driver|"
                     r"GPU has fallen off the bus|Xid.*PCI:",
                     row["stdout"] + "\n" + row.get("stderr", ""))
           for row in failed_queries):
        return _result("fail", "native NVIDIA output reports a driver communication or GPU hardware fault", files)
    if failed_queries:
        return _result("unknown", "native NVIDIA query returned nonzero without an explicit hardware-fault diagnostic", files)
    if not _identity(rows):
        return _result("unknown", "OEM, BIOS, OS, kernel, driver/module and firmware tuple incomplete", files)
    plan, error = _plan(data, rows, path)
    if error:
        return error
    assert plan is not None
    window = _policy_window(rows, plan, path)
    if isinstance(window, dict):
        return window
    apply, restore = window
    baseline, error = _measurements({"rows": rows, "start": 0, "end": apply,
                                     "phase": "baseline", "plan": plan, "path": path})
    if error:
        return error
    capped, error = _measurements({"rows": rows, "start": apply + 1, "end": restore,
                                   "phase": "capped", "plan": plan, "path": path})
    if error:
        return error
    assert baseline is not None and capped is not None
    if any(tuple(item[key] for key in ("model_sha256", "image_digest", "input_sha256", "concurrency", "max_new_tokens"))
           != tuple(baseline[0][key] for key in ("model_sha256", "image_digest", "input_sha256", "concurrency", "max_new_tokens"))
           for item in capped + baseline[1:]):
        return _result("fail", "baseline/capped run tuples differ", files)
    gate = _support_gates(rows, apply, restore, plan, path)
    if gate:
        return gate
    baseline_tps = sum(item["tokens_per_second"] for item in baseline) / len(baseline)
    capped_tps = sum(item["tokens_per_second"] for item in capped) / len(capped)
    baseline_p99 = sum(item["p99_latency_ms"] for item in baseline) / len(baseline)
    capped_p99 = sum(item["p99_latency_ms"] for item in capped) / len(capped)
    # Captures are caller-supplied; hashes/argv/output consistency do not authenticate their origin.
    return _result("pass", f"caller-supplied native captures show matched workload tuple; stock/cap throughput={baseline_tps:.3f}/{capped_tps:.3f} tok/s, p99={baseline_p99:.3f}/{capped_p99:.3f} ms, declared soak={plan['soak_seconds']}s; origin remains unauthenticated", files)


def verify(evidence: str | Path | None = None) -> dict[str, Any]:
    """Require a supported, observed A/B policy and its exact rollback readback."""
    directory = Path(evidence) if evidence is not None else ROOT / "tasks/evidence" / FINDING
    path = directory / "commands.json"
    capture = _capture(path)
    if capture is None:
        return _result("unknown", "raw timestamped GPU clock-cap command capture missing or malformed", [str(path)])
    return _verify(*capture, path)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence", type=Path, default=None,
                        help="directory containing commands.json")
    args = parser.parse_args(argv)
    result = verify(args.evidence)
    print(json.dumps(result, sort_keys=True))
    if result.get("status") == "pass" and result.get("fail") == 0 and result.get("could_not_run") == 0:
        return 0
    if result.get("status") == "fail" and result.get("fail", 0) > 0 and result.get("could_not_run") == 0:
        return 1
    return 2


if __name__ == "__main__":
    sys.exit(main())
