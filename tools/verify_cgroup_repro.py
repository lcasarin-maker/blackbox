"""Check raw cgroup reproduction observations; this does not authenticate their origin."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

APIS = {
    "none": "none", "cpu_touch": "cpu_touch", "cuda_malloc": "cuda_malloc",
    "cuda_malloc_repeat": "cuda_malloc", "cuda_malloc_managed": "cuda_malloc_managed",
    "pytorch_empty": "pytorch_empty",
}


def _integer(value: Any, label: str) -> int:
    if type(value) is not int or value < 0:
        raise ValueError(f"{label}: expected nonnegative integer")
    return value


def _observations(run: dict) -> list[dict]:
    rows = [json.loads(line) for line in run["stdout"].splitlines()]
    if not rows or any(not isinstance(row, dict) for row in rows):
        raise ValueError("worker observations must be nonempty JSON objects")
    phases = [row["phase"] for row in rows]
    expected = ["before"]
    if run["worker_api"] not in ("none", "cpu_touch"):
        expected.append("before_allocation")
    expected.append("held")
    if run["worker_api"] == "pytorch_empty":
        expected.append("allocator_cache_released")
    expected.append("after_release")
    if phases != expected:
        raise ValueError("worker phases absent, duplicated, or out of order")
    times = [_integer(row["monotonic_ns"], "observation timestamp") for row in rows]
    if any(a >= b for a, b in zip(times, times[1:])):
        raise ValueError("observation timestamps are not increasing")
    if any(row["pid"] != rows[0]["pid"] or row["cgroup_path"] != rows[0]["cgroup_path"] for row in rows):
        raise ValueError("worker identity changes within a run")
    _integer(rows[0]["pid"], "worker PID")
    if not rows[0]["cgroup_path"].endswith("/" + run["unit"] + ".scope"):
        raise ValueError("observed cgroup differs from the requested scope")
    return rows


def _unread(rows: list[dict], api: str) -> list[str]:
    unread: list[str] = []
    for row in rows:
        for key in ("proc_cgroup_error", "mem_available_error", "host_memory_pressure_error"):
            if row[key]:
                unread.append(f"{api}/{row['phase']}/{key}: {row[key]}")
        for name, observation in row["files"].items():
            if observation["error"] or observation["value"] is None:
                unread.append(f"{api}/{row['phase']}/{name}: {observation['error'] or 'value absent'}")
        for name in ("memory.current", "memory.events", "memory.pressure", "dmem.current"):
            if name not in row["files"]:
                unread.append(f"{api}/{row['phase']}/{name}: observation absent")
    return unread


def _case(run: dict) -> tuple[dict, list[str]]:
    api = run["api"]
    if run["worker_api"] != APIS[api] or run["returncode"] != 0:
        raise ValueError("worker API mismatch or unsuccessful worker")
    mib = _integer(run["requested_mib"], "requested MiB")
    if not 1 <= mib <= 32:
        raise ValueError("allocation outside bounded experiment")
    rows = _observations(run)
    phases = {row["phase"]: row for row in rows}
    held = phases["held"]
    requested = 0 if api == "none" else mib * 1024 * 1024
    if held["requested_bytes"] != requested:
        raise ValueError("held allocation differs from requested size")
    unread = _unread(rows, api)
    def current(phase: str) -> int:
        value = phases[phase]["files"]["memory.current"]["value"]
        if not isinstance(value, str) or not value.isdecimal():
            raise ValueError("memory.current is unreadable or invalid")
        return int(value)
    baseline = "before" if api in ("none", "cpu_touch") else "before_allocation"
    base, allocated, released = current(baseline), current("held"), current("after_release")
    return {"api": api, "cgroup": rows[0]["cgroup_path"], "requested_bytes": requested,
            "held_delta_bytes": allocated - base, "release_delta_bytes": released - base}, unread


def verify(document: Any) -> dict:
    """Recompute controls from raw worker rows; stored verdicts are ignored."""
    derived: list[dict] = []
    unread: list[str] = []
    try:
        if document["schema"] != 1 or not document["host"]["boot_id"]:
            raise ValueError("missing schema or boot identity")
        runs = document["runs"]
        if sorted(run["api"] for run in runs) != sorted(APIS):
            raise ValueError("required six API runs must appear exactly once")
        for run in runs:
            result, failures = _case(run)
            derived.append(result)
            unread.extend(failures)
        if len({row["cgroup"] for row in derived}) != len(APIS):
            raise ValueError("runs do not use independent scopes")
        by_api = {row["api"]: row for row in derived}
        cpu, idle = by_api["cpu_touch"], by_api["none"]
        if cpu["held_delta_bytes"] < cpu["requested_bytes"] // 2 or cpu["held_delta_bytes"] <= abs(idle["held_delta_bytes"]):
            return _result("fail", derived, unread, ["CPU positive control does not exceed noise and half the touched allocation"])
        if cpu["release_delta_bytes"] >= cpu["held_delta_bytes"]:
            return _result("fail", derived, unread, ["CPU release control shows no reduction"])
    except (KeyError, TypeError, ValueError, AttributeError) as exc:
        return _result("unknown", derived, [*unread, str(exc)], ["malformed or incomplete raw observations"])
    return _result("unknown" if unread else "pass", derived, unread, [])


def _result(status: str, rows: list[dict], unread: list[str], findings: list[str]) -> dict:
    return {"status": status, "rows": rows, "findings": findings,
            "could_not_run": unread, "could_not_run_count": len(unread),
            "scope": "observation consistency and CPU calibration; no native GPU containment or provenance proof"}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("evidence", type=Path)
    args = parser.parse_args(argv)
    try:
        result = verify(json.loads(args.evidence.read_text(encoding="utf-8")))
    except (OSError, UnicodeError, ValueError) as exc:
        result = _result("unknown", [], [str(exc)], ["evidence could not be read"])
    print(json.dumps(result, sort_keys=True))
    return {"pass": 0, "fail": 1, "unknown": 2}[result["status"]]


if __name__ == "__main__":
    sys.exit(main())
