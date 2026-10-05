"""Verify raw Memory Saver tracer or 4 KiB packing measurements."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
from typing import Any

PHASES = ("02-trazador", "04-packing-4k")
IDS = {"02-trazador": "FEATURE-MEMORYSAVER-02-TRAZADOR",
       "04-packing-4k": "FEATURE-MEMORYSAVER-04-PACKING-4K"}
MAX_CAPTURE_BYTES = 16 * 1024 * 1024  # multi-case trace envelope; bounds JSON decoding memory


def verify(phase: str, directory: Path) -> dict[str, Any]:
    try:
        with (directory / "capture.json").open("rb") as stream:
            raw = stream.read(MAX_CAPTURE_BYTES + 1)
        if len(raw) > MAX_CAPTURE_BYTES:
            return _r("unknown", ["phase capture exceeds 16 MiB bounded input"], 1)
        d = json.loads(raw.decode("utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        return _r("unknown", [f"raw phase capture unavailable: {exc}"], 1)
    if not isinstance(d, dict):
        return _r("unknown", ["top-level phase capture must be a JSON object"], 1)
    if phase not in PHASES:
        return _r("fail", ["unsupported phase"], 0)
    if type(d.get("schema")) is not int or d.get("schema") != 1 or d.get("id") != IDS[phase] or d.get("phase") != phase:
        return _r("fail", ["unsupported or mismatched exact phase/id"], 0)
    check = _trace if phase == "02-trazador" else _packing
    try:
        return check(d)
    except (KeyError, TypeError, ValueError, AttributeError, OverflowError) as exc:
        return _r("unknown", [f"raw phase evidence malformed: {exc}"], 1)


def _trace(d: dict[str, Any]) -> dict[str, Any]:
    cases = d.get("cases")
    expected = {"cpu_touch", "none", "cuda_bounded"}
    if not isinstance(cases, list) or {x.get("case") for x in cases} != expected:
        return _r("unknown", ["CPU positive, no-allocation negative, and bounded CUDA captures required"], 1)
    fields = ("boot_id", "pid", "cgroup", "start_ns", "end_ns", "events", "symbol_rows")
    for x in cases:
        if any(field not in x for field in fields):
            return _r("unknown", [f"raw case missing one of {fields}"], 1)
    if any("__memcg_kmem_charge_page" not in x["symbol_rows"] or "__memcg_kmem_uncharge_page" not in x["symbol_rows"] for x in cases):
        return _r("unknown", ["target kernel charge/uncharge symbols unobserved"], 1)
    computed = {}
    for case in cases:
        state, problem = _charge_ledger(case)
        if problem:
            return _r("fail", [problem], 0)
        computed[case["case"]] = state
    cpu, none = computed["cpu_touch"], computed["none"]
    if cpu["peak_live"] <= 0 or cpu["live"] != 0 or none["charged"] != 0:
        return _r("fail", ["tracer positive/negative control failed"], 0)
    if any(state["charged"] and state["owner"] in (None, "unknown") for state in computed.values()):
        return _r("unknown", ["executor cgroup does not establish charged owner memcg"], 1)
    return _r("pass", [], 0)


def _charge_ledger(case: dict[str, Any]) -> tuple[dict[str, Any], str | None]:
    events = case["events"]
    if not isinstance(events, list) or not events:
        return {}, f"no raw charge events for {case['case']}"
    fields = ("kind", "page", "bytes", "timestamp_ns", "pid", "cgroup", "owner_memcg")
    if any(not isinstance(e, dict) or any(k not in e for k in fields) for e in events):
        return {}, f"malformed charge event for {case['case']}"
    stamps = [e["timestamp_ns"] for e in events]
    if any(a >= b for a, b in zip(stamps, stamps[1:])):
        return {}, f"non-increasing event time in {case['case']}"
    ledger: dict[str, int] = {}
    charged = freed = peak_live = 0
    for event in events:
        if event["kind"] == "charge":
            if event["page"] in ledger:
                return {}, f"duplicate page charge in {case['case']}"
            ledger[event["page"]] = event["bytes"]
            charged += event["bytes"]
            peak_live = max(peak_live, sum(ledger.values()))
        elif event["kind"] == "uncharge":
            if event["page"] not in ledger or ledger.pop(event["page"]) != event["bytes"]:
                return {}, f"unmatched page uncharge in {case['case']}"
            freed += event["bytes"]
        elif event["kind"] != "failure":
            return {}, f"unknown event kind in {case['case']}"
    owners = {e["owner_memcg"] for e in events if e["kind"] == "charge"}
    owner = next(iter(owners)) if len(owners) == 1 else "unknown" if owners else "not-applicable"
    return {"charged": charged, "freed": freed, "live": sum(ledger.values()), "peak_live": peak_live,
            "owner": owner}, None


def _packing(d: dict[str, Any]) -> dict[str, Any]:
    measurements = d.get("allocations")
    if not isinstance(measurements, list) or not measurements:
        return _r("unknown", ["raw per-load page-table backing measurements required"], 1)
    if any(x.get("page_size") != 4096 or not isinstance(x.get("backing_bytes"), int) or x["backing_bytes"] < 0 or not x.get("allocation_id") for x in measurements):
        return _r("fail", ["packing-4k raw allocation rows invalid"], 0)
    sources = d.get("source_texts")
    if not isinstance(sources, list) or not sources or any(not isinstance(s.get("text"), str) or hashlib.sha256(s["text"].encode()).hexdigest() != s.get("sha256") for s in sources):
        return _r("unknown", ["pinned source text with recomputed SHA-256 required"], 1)
    if not d.get("alignment_requirements"):
        return _r("unknown", ["HAL alignment requirements extracted from pinned source absent"], 1)
    measured_bytes = sum(x["backing_bytes"] for x in measurements)
    if measured_bytes < 0:
        return _r("fail", ["invalid computed backing total"], 0)
    # PAGE_SIZE=4 KiB selects the stock allocator; packing's 64 KiB path is inapplicable.
    if any(x["page_size"] == 65536 for x in measurements):
        return _r("unknown", ["64 KiB candidate requires its own packed-vs-stock measured comparison"], 1)
    return _r("pass", [], 0)


def _r(status: str, findings: list[str], could_not_run: int) -> dict[str, Any]:
    return {"status": status, "findings": findings, "could_not_run": could_not_run,
            "could_not_run_count": could_not_run, "fail": int(status == "fail")}


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--phase", required=True, choices=PHASES)
    p.add_argument("--evidence", type=Path, required=True)
    a = p.parse_args(argv)
    out = verify(a.phase, a.evidence)
    print(json.dumps(out, sort_keys=True))
    return {"pass": 0, "fail": 1, "unknown": 2}[out["status"]]


if __name__ == "__main__":
    sys.exit(main())
