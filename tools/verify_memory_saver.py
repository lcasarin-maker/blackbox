"""Verify Memory Saver tracer or 4 KiB packing captures.

Capture fields and hashes are caller-supplied and unauthenticated; hashes
establish consistency only and do not authenticate host measurements.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
from typing import Any

from tools.capture_io import read_regular_bytes, strict_json_loads

PHASES = ("02-trazador", "04-packing-4k")
IDS = {"02-trazador": "FEATURE-MEMORYSAVER-02-TRAZADOR",
       "04-packing-4k": "FEATURE-MEMORYSAVER-04-PACKING-4K"}
MAX_CAPTURE_BYTES = 16 * 1024 * 1024  # multi-case trace envelope; bounds JSON decoding memory


def verify(phase: str, directory: Path) -> dict[str, Any]:
    if phase not in PHASES:
        return _r("fail", ["unsupported phase"], 0)
    try:
        raw = read_regular_bytes(directory / "capture.json", MAX_CAPTURE_BYTES)
        if len(raw) > MAX_CAPTURE_BYTES:
            return _r("unknown", ["phase capture exceeds 16 MiB bounded input"], 1)
        d = strict_json_loads(raw.decode("utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError, RecursionError) as exc:
        return _r("unknown", [f"raw phase capture unavailable: {exc}"], 1)
    if not isinstance(d, dict):
        return _r("unknown", ["top-level phase capture must be a JSON object"], 1)
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
    # Exactly one capture per case: a duplicate would let a clean copy mask a leaking or charged one.
    if (not isinstance(cases, list) or not all(isinstance(x, dict) for x in cases) or
            {x.get("case") for x in cases} != expected or len(cases) != len(expected)):
        return _r("unknown", ["exactly one CPU positive, no-allocation negative, and bounded CUDA capture required"], 1)
    issue = _trace_case_captures(cases)
    if issue:
        return issue
    return _trace_balances(cases)


def _trace_case_captures(cases: list[Any]) -> dict[str, Any] | None:
    fields = ("boot_id", "pid", "cgroup", "start_ns", "end_ns", "events", "symbol_rows")
    for x in cases:
        if not isinstance(x, dict) or any(field not in x for field in fields):
            return _r("unknown", [f"raw case missing one of {fields}"], 1)
        issue = _runtime_case_issue(x)
        if issue:
            return issue
        issue = _runtime_source_issue(x)
        if issue:
            return issue
        if x["case"] == "none":
            issue = _empty_window_issue(x.get("window"), x)
            if issue:
                return issue
    if any("__memcg_kmem_charge_page" not in x["symbol_rows"] or "__memcg_kmem_uncharge_page" not in x["symbol_rows"] for x in cases):
        return _r("unknown", ["target kernel charge/uncharge symbols unobserved"], 1)
    return None


def _trace_balances(cases: list[dict[str, Any]]) -> dict[str, Any]:
    computed = {}
    for case in cases:
        state, problem = _charge_ledger(case)
        if problem:
            return _r("fail", [problem], 0)
        computed[case["case"]] = state
    cpu, none = computed["cpu_touch"], computed["none"]
    if cpu["peak_live"] <= 0 or any(state["live"] != 0 or state["charged"] != state["freed"]
                                    for state in computed.values()) or none["charged"] != 0:
        return _r("fail", ["tracer positive/negative control failed"], 0)
    if any(state["charged"] and state["owner"] in (None, "unknown") for state in computed.values()):
        return _r("unknown", ["executor cgroup does not establish charged owner memcg"], 1)
    return _r("pass", [], 0)


def _runtime_case_issue(case: dict[str, Any]) -> dict[str, Any] | None:
    if (not isinstance(case.get("boot_id"), str) or not case["boot_id"] or type(case.get("pid")) is not int or
            case["pid"] <= 0 or not isinstance(case.get("cgroup"), str) or not case["cgroup"] or
            type(case.get("start_ns")) is not int or type(case.get("end_ns")) is not int or
            case["start_ns"] < 0 or case["end_ns"] <= case["start_ns"] or
            type(case.get("lost_events")) is not int or case["lost_events"] != 0 or
            not isinstance(case.get("kernel_release"), str) or not case["kernel_release"] or
            not isinstance(case.get("abi_sha256"), str) or len(case["abi_sha256"]) != 64):
        return _r("unknown", [f"{case['case']} lacks bound boot/PID/cgroup/window/kernel ABI/loss capture"], 1)
    if not isinstance(case["symbol_rows"], list) or not all(isinstance(row, str) and row for row in case["symbol_rows"]):
        return _r("unknown", [f"{case['case']} symbol rows malformed"], 1)
    return None


def _runtime_source_issue(case: dict[str, Any]) -> dict[str, Any] | None:
    kernel = case.get("kernel_capture")
    abi = case.get("abi_capture")
    symbols = case.get("symbol_capture")
    if (not isinstance(kernel, dict) or kernel.get("command") != ["uname", "-r"] or
            type(kernel.get("returncode")) is not int or kernel["returncode"] != 0 or
            not isinstance(kernel.get("stdout"), str) or kernel["stdout"].strip() != case["kernel_release"]):
        return _r("unknown", [f"{case['case']} lacks raw current kernel release capture"], 1)
    if (not isinstance(abi, dict) or abi.get("command") != ["bpftool", "btf", "dump", "file", "/sys/kernel/btf/vmlinux", "format", "raw"] or
            type(abi.get("returncode")) is not int or abi["returncode"] != 0 or not isinstance(abi.get("stdout"), str) or
            len(abi["stdout"].encode()) > MAX_CAPTURE_BYTES or hashlib.sha256(abi["stdout"].encode()).hexdigest() != case["abi_sha256"]):
        return _r("unknown", [f"{case['case']} lacks bounded raw kernel ABI capture"], 1)
    expected_symbols = ("__memcg_kmem_charge_page", "__memcg_kmem_uncharge_page")
    if (not isinstance(symbols, dict) or symbols.get("command") != ["grep", "-E", "__memcg_kmem_charge_page|__memcg_kmem_uncharge_page", "/proc/kallsyms"] or
            type(symbols.get("returncode")) is not int or symbols["returncode"] != 0 or not isinstance(symbols.get("stdout"), str) or
            any(name not in symbols["stdout"] for name in expected_symbols)):
        return _r("unknown", [f"{case['case']} lacks current raw charge/uncharge symbol rows"], 1)
    return None


def _empty_window_issue(window: Any, case: dict[str, Any]) -> dict[str, Any] | None:
    if not isinstance(window, dict) or not isinstance(window.get("heartbeat_rows"), list) or len(window["heartbeat_rows"]) < 2:
        return _r("unknown", ["no-allocation window needs active probe heartbeats and CPU control evidence"], 1)
    heartbeats = window["heartbeat_rows"]
    timestamps = [row.get("timestamp_ns") if isinstance(row, dict) else None for row in heartbeats]
    if any(type(ts) is not int for ts in timestamps):
        return _r("unknown", ["probe heartbeat timestamps absent or unordered"], 1)
    ordered = [ts for ts in timestamps if type(ts) is int]
    if any(a >= b for a, b in zip(ordered, ordered[1:])):
        return _r("unknown", ["probe heartbeat timestamps absent or unordered"], 1)
    if any(ts < case["start_ns"] or ts > case["end_ns"] for ts in ordered):
        return _r("unknown", ["probe heartbeats fall outside the no-allocation window"], 1)
    if any(row.get("boot_id") != case["boot_id"] or row.get("pid") != case["pid"] or
           row.get("cgroup") != case["cgroup"] or row.get("active") is not True for row in heartbeats):
        return _r("fail", ["no-allocation probe heartbeat is inactive or misattributed"], 0)
    control = window.get("control_cpu_events")
    if not isinstance(control, list) or not control or any(not isinstance(row, dict) or
            row.get("kind") not in ("charge", "uncharge") or row.get("pid") != case["pid"] or
            row.get("cgroup") != case["cgroup"] or row.get("boot_id") != case["boot_id"]
            for row in control):
        return _r("unknown", ["no-allocation window lacks independent CPU probe control events"], 1)
    return None


def _charge_ledger(case: dict[str, Any]) -> tuple[dict[str, Any], str | None]:
    events = case["events"]
    # The no-allocation control honestly records zero events; its liveness comes from the
    # windowed heartbeats checked in _empty_window_issue. Positive cases still need events.
    if not isinstance(events, list) or (not events and case["case"] != "none"):
        return {}, f"no raw charge events for {case['case']}"
    fields = ("kind", "page", "bytes", "timestamp_ns", "pid", "cgroup", "owner_memcg")
    if any(not isinstance(e, dict) or any(k not in e for k in fields) for e in events):
        return {}, f"malformed charge event for {case['case']}"
    issue = _event_binding_issue(case, events)
    if issue:
        return {}, issue
    stamps = [e["timestamp_ns"] for e in events]
    if any(a >= b for a, b in zip(stamps, stamps[1:])):
        return {}, f"non-increasing event time in {case['case']}"
    return _event_ledger(case, events)


def _event_ledger(case: dict[str, Any], events: list[dict[str, Any]]) -> tuple[dict[str, Any], str | None]:
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
        elif event["bytes"] != 0:
            return {}, f"failure event carries a nonzero charge in {case['case']}"
    owners = {e["owner_memcg"] for e in events if e["kind"] == "charge"}
    owner = next(iter(owners)) if len(owners) == 1 else "unknown" if owners else "not-applicable"
    return {"charged": charged, "freed": freed, "live": sum(ledger.values()), "peak_live": peak_live,
            "owner": owner}, None


def _event_binding_issue(case: dict[str, Any], events: list[Any]) -> str | None:
    for event in events:
        if (not isinstance(event["kind"], str) or event.get("boot_id") != case.get("boot_id") or
                type(event["timestamp_ns"]) is not int or event["timestamp_ns"] < case["start_ns"] or
                event["timestamp_ns"] > case["end_ns"] or type(event["pid"]) is not int or
                event["pid"] != case["pid"] or event["cgroup"] != case["cgroup"] or
                not isinstance(event["page"], str) or type(event["bytes"]) is not int or event["bytes"] < 0 or
                not isinstance(event.get("flags"), str) or not event["flags"] or
                not isinstance(event.get("stack"), list) or not event["stack"] or
                not all(isinstance(frame, str) and frame for frame in event["stack"])):
            return f"invalid typed/attributed raw event for {case['case']}"
    return None


def _packing(d: dict[str, Any]) -> dict[str, Any]:
    rows, row_issue = _packing_rows(d.get("allocations"))
    if row_issue:
        return row_issue
    assert rows is not None
    source_by_path, source_issue = _packing_sources(d.get("source_texts"), rows)
    if source_issue:
        return source_issue
    assert source_by_path is not None
    req_by_api, requirement_issue = _packing_requirements(d.get("alignment_requirements"), source_by_path, rows)
    if requirement_issue:
        return requirement_issue
    assert req_by_api is not None
    return _packing_decision(rows, req_by_api, d)


def _packing_rows(raw: Any) -> tuple[list[dict[str, Any]] | None, dict[str, Any] | None]:
    if not isinstance(raw, list) or not raw:
        return None, _r("unknown", ["raw per-load page-table backing measurements required"], 1)
    required = ("allocation_id", "api", "requested_bytes", "page_size", "backing_bytes", "offset_bytes",
                "dma_alignment_bytes", "source_path", "source_sha256", "map_operation", "unmap_operation",
                "tracker_before", "tracker_after", "allocator", "run_id", "gpu_base_address",
                "cacheline_bytes", "cpu_mapping_offset_bytes", "descriptor_bytes", "owner_memcg",
                "memory_current_before", "memory_current_held", "memory_current_after", "logical_allocation_id",
                "corpus_sha256", "protocol_sha256", "stack_sha256", "exposure")
    if any(not isinstance(x, dict) for x in raw):
        return None, _r("unknown", ["allocation rows must be raw objects"], 1)
    if any(any(key not in x for key in required) for x in raw):
        return None, _r("unknown", ["raw API allocation, DMA alignment, mapping, tracker and teardown observations required"], 1)
    invalid = any(type(x.get("page_size")) is not int or x["page_size"] not in (4096, 65536) or
        any(type(x.get(k)) is not int or x[k] < 0 for k in ("backing_bytes", "requested_bytes", "offset_bytes", "dma_alignment_bytes")) or
        x["requested_bytes"] == 0 or x["dma_alignment_bytes"] == 0 or
        not all(isinstance(x.get(k), str) and x[k].strip() for k in ("allocation_id", "logical_allocation_id", "api", "source_path", "map_operation", "unmap_operation", "corpus_sha256", "protocol_sha256", "stack_sha256", "exposure")) or
        x.get("allocator") not in ("stock", "packed") or not isinstance(x.get("run_id"), str) or not x["run_id"].strip() or
        any(type(x.get(k)) is not int or x[k] < 0 for k in ("gpu_base_address", "cacheline_bytes", "cpu_mapping_offset_bytes", "descriptor_bytes", "memory_current_before", "memory_current_held", "memory_current_after")) or
        x["cacheline_bytes"] == 0 or not isinstance(x.get("owner_memcg"), str) or not x["owner_memcg"].strip() or
        not isinstance(x.get("source_sha256"), str) or len(x["source_sha256"]) != 64 or
        type(x.get("tracker_before")) is not int or type(x.get("tracker_after")) is not int for x in raw)
    return (None, _r("fail", ["packing-4k raw allocation rows invalid"], 0)) if invalid else (raw, None)


def _packing_sources(raw: Any, rows: list[dict[str, Any]]) -> tuple[dict[str, dict[str, Any]] | None, dict[str, Any] | None]:
    if not isinstance(raw, list) or not raw or any(not isinstance(s, dict) or
            not isinstance(s.get("text"), str) or not isinstance(s.get("path"), str) or
            not isinstance(s.get("version"), str) or hashlib.sha256(s["text"].encode()).hexdigest() != s.get("sha256") for s in raw):
        return None, _r("unknown", ["pinned source text with recomputed SHA-256 required"], 1)
    by_path = {s["path"]: s for s in raw}
    if any(x["source_path"] not in by_path or by_path[x["source_path"]]["sha256"] != x["source_sha256"] for x in rows):
        return None, _r("fail", ["allocation source path/digest does not bind to pinned source text"], 0)
    return by_path, None


def _packing_requirements(raw: Any, sources: dict[str, dict[str, Any]], rows: list[dict[str, Any]]) -> tuple[dict[str, dict[str, Any]] | None, dict[str, Any] | None]:
    invalid = not isinstance(raw, list) or not raw or any(not isinstance(x, dict) or
        not isinstance(x.get("api"), str) or type(x.get("alignment_bytes")) is not int or x["alignment_bytes"] <= 0 or
        not isinstance(x.get("source_path"), str) or not isinstance(x.get("source_symbol"), str) or
        not x["source_symbol"] or x["source_path"] not in sources or x["source_symbol"] not in sources[x["source_path"]]["text"]
        for x in (raw if isinstance(raw, list) else []))
    if invalid:
        return None, _r("unknown", ["HAL alignment requirements extracted from pinned source absent"], 1)
    by_api = {x["api"]: x for x in raw}
    if len(by_api) != len(raw) or {x["api"] for x in rows} - set(by_api):
        return None, _r("unknown", ["per-API alignment requirements or captures are ambiguous/incomplete"], 1)
    return by_api, None


def _packing_decision(rows: list[dict[str, Any]], requirements: dict[str, dict[str, Any]], capture: dict[str, Any]) -> dict[str, Any]:
    for row in rows:
        issue = _packing_measure_issue(row, requirements[row["api"]])
        if issue:
            return issue
    if len({x["allocation_id"] for x in rows}) != len(rows):
        return _r("fail", ["duplicate per-load allocation identity"], 0)
    issue = _sharing_issue(capture.get("sharing_rows"), rows)
    if issue:
        return issue
    issue = _migration_issue(capture.get("migration_rows"), rows)
    if issue:
        return issue
    return _packing_cost_decision(rows, capture)


def _packing_measure_issue(row: dict[str, Any], requirement: dict[str, Any]) -> dict[str, Any] | None:
    alignment = max(requirement["alignment_bytes"], row["dma_alignment_bytes"])
    if row["offset_bytes"] % alignment or row["gpu_base_address"] % alignment:
        return _r("fail", [f"{row['api']} base/offset violates captured HAL/DMA alignment"], 0)
    if row["cpu_mapping_offset_bytes"] % row["cacheline_bytes"]:
        return _r("fail", [f"{row['api']} CPU mapping offset violates cache-line separation"], 0)
    if row["tracker_after"] > row["tracker_before"] or row["memory_current_after"] != row["memory_current_before"]:
        return _r("fail", [f"{row['api']} tracker or owner charge failed to return after teardown"], 0)
    if row["backing_bytes"] < row["requested_bytes"]:
        return _r("fail", [f"{row['api']} backing measurement is below requested allocation"], 0)
    if row["memory_current_held"] - row["memory_current_before"] < row["backing_bytes"] + row["descriptor_bytes"]:
        return _r("unknown", [f"{row['api']} owner charge does not account for backing plus descriptors"], 1)
    return None


def _packing_cost_decision(rows: list[dict[str, Any]], capture: dict[str, Any]) -> dict[str, Any]:
    if any(x["page_size"] != 4096 for x in rows):
        return _r("unknown", ["4 KiB target requires measurements at the captured 4 KiB page size"], 1)
    workload = capture.get("comparison")
    metadata = ("corpus_sha256", "protocol_sha256", "stack_sha256", "exposure")
    if (not isinstance(workload, dict) or any(not isinstance(workload.get(k), str) or not workload[k].strip() for k in metadata) or
            any(k.endswith("sha256") and (len(workload[k]) != 64 or any(c not in "0123456789abcdef" for c in workload[k])) for k in metadata)):
        return _r("unknown", ["comparable corpus, protocol, stack and exposure metadata required"], 1)
    costs: dict[tuple[str, str], int] = {}
    for row in rows:
        key = (row["logical_allocation_id"], row["allocator"])
        if key in costs:
            return _r("unknown", ["duplicate logical allocation within stock/packed workload"], 1)
        costs[key] = row["backing_bytes"] + row["descriptor_bytes"]
    stock = {row["logical_allocation_id"]: row for row in rows if row["allocator"] == "stock"}
    packed = {row["logical_allocation_id"]: row for row in rows if row["allocator"] == "packed"}
    if not stock or stock.keys() != packed.keys():
        return _r("unknown", ["stock and packed runs must contain the same logical allocation corpus"], 1)
    for logical_id in stock:
        left, right = stock[logical_id], packed[logical_id]
        if any(left[key] != right[key] for key in ("api", "requested_bytes", "dma_alignment_bytes", "owner_memcg")):
            return _r("unknown", [f"stock/packed workload mismatch for logical allocation {logical_id}"], 1)
        if any(left[key] != right[key] or left[key] != workload[key] for key in metadata):
            return _r("unknown", [f"stock/packed corpus/protocol/stack/exposure mismatch for logical allocation {logical_id}"], 1)
    if _api_has_measured_saving(rows, costs):
        return _packing_candidate_issue(capture.get("candidate"))
    return _r("pass", [], 0)


def _api_has_measured_saving(rows: list[dict[str, Any]], costs: dict[tuple[str, str], int]) -> bool:
    api_totals: dict[tuple[str, str], int] = {}
    for row in rows:
        key = (row["api"], row["allocator"])
        api_totals[key] = api_totals.get(key, 0) + costs[(row["logical_allocation_id"], row["allocator"])]
    return any(api_totals.get((api, "packed"), 0) < api_totals.get((api, "stock"), 0)
               for api in {row["api"] for row in rows})


def _sharing_issue(raw: Any, rows: list[dict[str, Any]]) -> dict[str, Any] | None:
    if not isinstance(raw, list) or not raw:
        return _r("unknown", ["raw second-process sharing controls required"], 1)
    identities = {row["allocation_id"]: row for row in rows}
    for item in raw:
        if not isinstance(item, dict) or item.get("allocation_id") not in identities:
            return _r("unknown", ["sharing row lacks allocation binding"], 1)
        if (item.get("owner_before") != identities[item["allocation_id"]]["owner_memcg"] or
                item.get("owner_after") != item.get("owner_before") or type(item.get("charge_before")) is not int or
                type(item.get("charge_after")) is not int):
            return _r("unknown", ["sharing control lacks owner/charge measurements"], 1)
        if item["charge_after"] != item["charge_before"]:
            return _r("fail", ["sharing changed owner charge unexpectedly"], 0)
    if {item.get("allocation_id") for item in raw if isinstance(item, dict)} != set(identities):
        return _r("unknown", ["sharing controls do not cover every measured allocation"], 1)
    return None


def _migration_issue(raw: Any, rows: list[dict[str, Any]]) -> dict[str, Any] | None:
    if not isinstance(raw, list) or not raw:
        return _r("unknown", ["raw process migration controls required"], 1)
    ids = {row["allocation_id"] for row in rows}
    for item in raw:
        if not isinstance(item, dict) or item.get("allocation_id") not in ids or not all(type(item.get(k)) is int for k in
                ("charge_total_before", "charge_total_after", "source_charge_before", "source_charge_after", "destination_charge_before", "destination_charge_after")):
            return _r("unknown", ["migration row lacks bound owner charge counters"], 1)
        if item["charge_total_after"] != item["charge_total_before"]:
            return _r("fail", ["migration lost or double charged backing"], 0)
        if item.get("expected_owner_after") != item.get("observed_owner_after"):
            return _r("fail", ["migration changed the measured backing owner unexpectedly"], 0)
    if {item.get("allocation_id") for item in raw if isinstance(item, dict)} != ids:
        return _r("unknown", ["migration controls do not cover every measured allocation"], 1)
    return None


def _packing_candidate_issue(candidate: Any) -> dict[str, Any]:
    if not isinstance(candidate, dict):
        return _r("unknown", ["measured saving requires candidate diff/build/phase03 integrity matrix"], 1)
    diff, build, comparison, matrix = (candidate.get(key) for key in ("diff", "build", "phase03", "integrity_rows"))
    issue, artifact_sha = _candidate_build_issue(diff, build)
    if issue:
        return issue
    assert artifact_sha is not None
    issue = _candidate_stack_issue(comparison, artifact_sha)
    if issue:
        return issue
    issue = _candidate_matrix_issue(matrix)
    if issue:
        return issue
    assert isinstance(matrix, list)
    for item in matrix:
        issue = _candidate_control_issue(item)
        if issue:
            return issue
    return _r("pass", [], 0)


def _candidate_build_issue(diff: Any, build: Any) -> tuple[dict[str, Any] | None, str | None]:
    if not isinstance(diff, dict) or not isinstance(diff.get("patch_text"), str) or not isinstance(diff.get("base_sha256"), str) or len(diff["base_sha256"]) != 64:
        return _r("unknown", ["candidate diff bytes and recomputed digest required"], 1), None
    if hashlib.sha256(diff["patch_text"].encode()).hexdigest() != diff.get("sha256"):
        return _r("fail", ["candidate diff digest does not match raw patch bytes"], 0), None
    if not isinstance(build, dict) or type(build.get("returncode")) is not int:
        return _r("unknown", ["raw candidate build result required"], 1), None
    if build["returncode"] != 0:
        return _r("fail", ["candidate module build failed"], 0), None
    if (
            not isinstance(build.get("command"), list) or not build["command"] or
            not isinstance(build.get("artifact"), str) or not build["artifact"] or
            hashlib.sha256(build["artifact"].encode()).hexdigest() != build.get("artifact_sha256")):
        return _r("unknown", ["successful build command and artifact digest required"], 1), None
    return None, build["artifact_sha256"]


def _candidate_stack_issue(comparison: Any, artifact_sha: str) -> dict[str, Any] | None:
    if not isinstance(comparison, dict) or comparison.get("id") != "FEATURE-MEMORYSAVER-03-INTEGRIDAD" or not isinstance(comparison.get("before"), dict) or not isinstance(comparison.get("after"), dict):
        return _r("unknown", ["before/after phase03 stack comparison required"], 1)
    before, after = comparison["before"], comparison["after"]
    if any(before.get(key) != after.get(key) for key in ("kernel", "driver", "gsp", "boot_id")):
        return _r("fail", ["candidate changed an unreviewed phase03 stack identity"], 0)
    before_modules, after_modules = before.get("modules"), after.get("modules")
    if not isinstance(before_modules, dict) or not isinstance(after_modules, dict) or set(before_modules) != set(after_modules) or not isinstance(after_modules.get("nvidia_uvm"), dict) or after_modules["nvidia_uvm"].get("sha256") != artifact_sha:
        return _r("unknown", ["phase03 module inventories do not bind the built candidate artifact"], 1)
    if any(before_modules[name] != after_modules[name] for name in before_modules if name != "nvidia_uvm"):
        return _r("fail", ["candidate changed modules outside the reviewed UVM module"], 0)
    return None


def _candidate_matrix_issue(matrix: Any) -> dict[str, Any] | None:
    expected = {"charge", "release", "sharing", "migration", "descriptor", "concurrent_teardown"}
    if not isinstance(matrix, list) or any(not isinstance(item, dict) for item in matrix) or {item.get("control") for item in matrix} != expected or len(matrix) != len(expected):
        return _r("unknown", ["phase03 charge/release/sharing/migration/descriptor/concurrent teardown matrix incomplete"], 1)
    return None


def _candidate_control_issue(item: dict[str, Any]) -> dict[str, Any] | None:
    name = item.get("control")
    events = item.get("events")
    if not isinstance(events, list) or not events:
        return _r("unknown", [f"phase03 {name} raw events absent"], 1)
    ledger: dict[str, tuple[int, str, int, str, str]] = {}
    stamps: list[int] = []
    for event in events:
        if (not isinstance(event, dict) or type(event.get("bytes")) is not int or event["bytes"] < 0 or
                type(event.get("timestamp_ns")) is not int or type(event.get("pid")) is not int or
                not isinstance(event.get("cgroup"), str) or not isinstance(event.get("owner_memcg"), str) or
                not isinstance(event.get("boot_id"), str) or not isinstance(event.get("page"), str)):
            return _r("unknown", [f"phase03 {name} event malformed or unattributed"], 1)
        stamps.append(event["timestamp_ns"])
        page = event["page"]
        if event.get("kind") == "charge":
            if page in ledger:
                return _r("fail", [f"phase03 {name} double charged page"], 0)
            ledger[page] = (event["bytes"], event["owner_memcg"], event["pid"], event["cgroup"], event["boot_id"])
        elif event.get("kind") == "uncharge" and page in ledger and ledger.pop(page) == (event["bytes"], event["owner_memcg"], event["pid"], event["cgroup"], event["boot_id"]):
            continue
        else:
            return _r("fail", [f"phase03 {name} lost or unmatched charge"], 0)
    if any(a >= b for a, b in zip(stamps, stamps[1:])):
        return _r("fail", [f"phase03 {name} event time not increasing"], 0)
    if ledger:
        return _r("fail", [f"phase03 {name} teardown left charged pages"], 0)
    return None


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
