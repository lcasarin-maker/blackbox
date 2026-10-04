"""Verify raw, phase-specific cgroup investigation evidence.

Evidence contract: ``<evidence>/capture.json`` is a versioned observation
bundle. See ``_phase_checks`` for required raw fields for each phase. Existing
text reports are context only; they never establish a passing result. Every
identity, command and digest in this JSON is caller-supplied and unauthenticated;
the digest checks internal consistency, not capture origin.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
import sys
from typing import Any

from tools.verify_cgroup_repro import APIS, _case as verify_case, verify as verify_reproduction

PHASES = ("02-traza", "03-nativo", "04-parche", "05-cuelgues")
MAX_CAPTURE_BYTES = 16 * 1024 * 1024  # bounded multi-API trace bundle; avoids unbounded JSON allocation
IDS = {
    "02-traza": "FEATURE-1358-CGROUP-02-TRAZA",
    "03-nativo": "FEATURE-1358-CGROUP-03-NATIVO",
    "04-parche": "FEATURE-1358-CGROUP-04-PARCHE",
    "05-cuelgues": "FEATURE-1358-CGROUP-05-CUELGUES",
}


class MissingEvidence(ValueError):
    """A required raw capture is absent, so this phase is CNR."""


def verify(phase: str, directory: Path) -> dict[str, Any]:
    if phase not in PHASES:
        return result("fail", [f"unsupported phase: {phase}"], 0)
    path = directory / "capture.json"
    try:
        with path.open("rb") as stream:
            raw = stream.read(MAX_CAPTURE_BYTES + 1)
        if len(raw) > MAX_CAPTURE_BYTES:
            return result("unknown", ["raw capture exceeds 16 MiB bounded input"], 1)
        doc = json.loads(raw.decode("utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError, RecursionError) as exc:
        return result("unknown", [f"raw capture unavailable: {exc}"], 1)
    if not isinstance(doc, dict):
        return result("unknown", ["top-level capture must be a JSON object"], 1)
    return _evaluate(phase, doc)


def _evaluate(phase: str, doc: dict[str, Any]) -> dict[str, Any]:
    try:
        if type(doc.get("schema")) is not int or doc["schema"] != 1 or doc.get("id") != IDS[phase] or doc.get("phase") != phase:
            return result("fail", ["schema, exact task id, or phase mismatch"], 0)
        host = doc["host"]
        if not isinstance(host, dict):
            return result("unknown", ["host identity capture must be an object"], 1)
        if not all(isinstance(host.get(k), str) and host[k] for k in ("boot_id", "kernel", "driver")):
            return result("unknown", ["host boot/kernel/driver identity incomplete"], 1)
        checks = _phase_checks(phase, doc)
        if checks:
            return result("fail", checks, 0)
    except MissingEvidence as exc:
        return result("unknown", [str(exc)], 1)
    except (KeyError, TypeError, ValueError, AttributeError, OverflowError) as exc:
        return result("unknown", [f"required raw observation missing or malformed: {exc}"], 1)
    passed = result("pass", [], 0)
    if phase == "03-nativo":
        passed["evaluation"] = _native_report(doc)
    elif phase == "04-parche":
        passed["evaluation"] = _patch_report(doc)
    return passed


def _phase_checks(phase: str, d: dict[str, Any]) -> list[str]:
    """Recompute phase predicates from measurements; reject summary booleans."""
    check = {"02-traza": _trace, "03-nativo": _native, "04-parche": _patch, "05-cuelgues": _hangs}[phase]
    return check(d)


def _trace(d: dict[str, Any]) -> list[str]:
    rows = d["allocations"]
    cases = {"cpu_touch", "none", "cuda_malloc", "cuda_malloc_managed", "pytorch_empty"}
    if not isinstance(rows, list) or any(not isinstance(r, dict) for r in rows):
        raise MissingEvidence("raw per-API allocation capture is absent or malformed")
    if not cases <= {r.get("case") for r in rows}:
        raise MissingEvidence("raw captures for all five API cases are required")
    names = [r.get("case") for r in rows]
    if len(names) != len(set(names)):
        return ["duplicate allocation case rows make the per-API observation ambiguous"]
    issues = []
    derived_cases: dict[str, dict[str, Any]] = {}
    for row in rows:
        events = row.get("trace_rows")
        if not isinstance(events, list):
            raise MissingEvidence("dynamic trace rows absent for one or more allocation cases")
        derived, error = _trace_case(row, events)
        if error:
            issues.append(error)
        if derived:
            derived_cases[row["case"]] = derived
        if row["case"] == "none" and derived and derived["charged_bytes"]:
            issues.append("no-allocation control contains charges")
    cpu = derived_cases.get("cpu_touch", {})
    if cpu.get("charged_bytes", 0) <= 0 or cpu.get("outstanding_bytes", 0) != 0:
        issues.append("CPU trace positive control did not observe balanced page charges")
    return issues


def _trace_case(case: dict[str, Any], events: list[Any]) -> tuple[dict[str, Any] | None, str | None]:
    if not events:
        return _empty_trace(case, events)
    required = ("event", "timestamp_ns", "pid", "cgroup", "active_memcg", "flags", "bytes", "page", "stack")
    if any(not isinstance(event, dict) or any(key not in event for key in required) for event in events):
        raise ValueError(f"malformed raw event row for {case.get('case')}")
    if any(event["event"] not in ("charge", "uncharge", "failure") or type(event["bytes"]) is not int or event["bytes"] < 0 or
           type(event["timestamp_ns"]) is not int or type(event["pid"]) is not int or
           not isinstance(event["cgroup"], str) or event["active_memcg"] is not None and not isinstance(event["active_memcg"], str) or
           not isinstance(event["flags"], str) or not isinstance(event["page"], str) or
           not isinstance(event["stack"], list) or any(not isinstance(frame, str) for frame in event["stack"])
           for event in events):
        raise ValueError(f"invalid raw event value for {case.get('case')}")
    identity = {(event["pid"], event["cgroup"], event["active_memcg"]) for event in events}
    stamps = [event["timestamp_ns"] for event in events]
    if len(identity) != 1 or any(a >= b for a, b in zip(stamps, stamps[1:])):
        return None, f"identity change or non-increasing event times in {case['case']}"
    pid, cgroup, memcg = next(iter(identity))
    if memcg in ("", "unknown") or cgroup == "":
        raise MissingEvidence(f"charge owner or task cgroup is unobserved in {case['case']}")
    if not isinstance(case.get("pid"), int) or case["pid"] != pid or case.get("cgroup") != cgroup:
        return None, f"raw event identity does not match observed task identity for {case['case']}"
    canonical = json.dumps(events, sort_keys=True, separators=(",", ":")).encode()
    if case.get("trace_sha256") != hashlib.sha256(canonical).hexdigest():
        return None, f"raw trace digest mismatch in {case['case']}"
    return _trace_ledger(case, events)


def _empty_trace(case: dict[str, Any], events: list[Any]) -> tuple[dict[str, Any] | None, str | None]:
    window = case.get("window")
    identity = ("pid", "cgroup", "active_memcg")
    if not isinstance(window, dict) or not all(isinstance(window.get(k), str) for k in identity):
        raise MissingEvidence(f"empty trace lacks observed process/cgroup window for {case.get('case')}")
    if type(window.get("start_ns")) is not int or type(window.get("end_ns")) is not int or window["start_ns"] >= window["end_ns"]:
        raise ValueError(f"empty trace has invalid window for {case.get('case')}")
    heartbeats = window.get("heartbeat_rows")
    if window.get("probe_active") is not True or not isinstance(heartbeats, list) or not heartbeats:
        raise MissingEvidence(f"empty trace lacks active-probe heartbeat evidence for {case.get('case')}")
    if any(not isinstance(row, dict) or row.get("probe_active") is not True or type(row.get("timestamp_ns")) is not int or
           not window["start_ns"] <= row["timestamp_ns"] <= window["end_ns"] or
           (row.get("pid"), row.get("cgroup"), row.get("active_memcg")) !=
           (window["pid"], window["cgroup"], window["active_memcg"]) for row in heartbeats):
        return None, f"inactive or misattributed probe heartbeat for {case['case']}"
    canonical = json.dumps(events, sort_keys=True, separators=(",", ":")).encode()
    if case.get("trace_sha256") != hashlib.sha256(canonical).hexdigest():
        return None, f"raw empty-trace digest mismatch in {case['case']}"
    return {"charged_bytes": 0, "freed_bytes": 0, "outstanding_bytes": 0}, None


def _trace_ledger(case: dict[str, Any], events: list[dict[str, Any]]) -> tuple[dict[str, Any] | None, str | None]:
    ledger: dict[str, int] = {}
    for event in events:
        page, size = event["page"], event["bytes"]
        if event["event"] == "charge":
            if not page or page in ledger:
                return None, f"duplicate or unidentified charge page in {case['case']}"
            ledger[page] = size
        elif event["event"] == "uncharge" and (page not in ledger or ledger.pop(page) != size):
            return None, f"unmatched uncharge page in {case['case']}"
    charged = sum(e["bytes"] for e in events if e["event"] == "charge")
    freed = sum(e["bytes"] for e in events if e["event"] == "uncharge")
    return {"charged_bytes": charged, "freed_bytes": freed, "outstanding_bytes": sum(ledger.values())}, None


def _native(d: dict[str, Any]) -> list[str]:
    runs = d["stack_runs"]
    if not isinstance(runs, list):
        raise MissingEvidence("paired raw stack runs are absent")
    if {r["stack"] for r in runs} != {"580-baseline", "615-candidate"}:
        raise MissingEvidence("paired 580 and complete 615 stack runs required")
    for r in runs:
        issue = _native_stack(r)
        if issue:
            return [issue]
    _native_controls(d.get("native_controls"))
    dependency_issue = _phase02_binding_and_rollback(d, runs)
    if dependency_issue:
        return dependency_issue
    return []


def _phase02_binding_and_rollback(d: dict[str, Any], runs: list[dict[str, Any]]) -> list[str]:
    trace = d.get("phase02_trace")
    if not isinstance(trace, dict):
        raise MissingEvidence("phase 03 requires bound raw phase 02 owner/allocation trace evidence")
    if trace.get("id") != IDS["02-traza"] or trace.get("phase") != "02-traza":
        return ["phase 02 trace evidence belongs to a different task or phase"]
    baseline = next(row for row in runs if row["stack"] == "580-baseline")
    identity = trace.get("stack_identity")
    expected_identity = {key: baseline[key] for key in ("boot_id", "kernel", "driver_version", "gsp")}
    if identity != expected_identity:
        return ["phase 02 owner trace is not bound to the exact captured 580 stack identity"]
    allocations = trace.get("allocations")
    if not isinstance(allocations, list):
        raise MissingEvidence("phase 02 raw per-API owner allocation rows are required")
    issues = _trace({"allocations": allocations})
    if issues:
        return [f"phase 02 raw allocation/owner trace invalid: {issue}" for issue in issues]
    trace_owner: dict[str, Any] = {}
    for row in allocations:
        events = row["trace_rows"]
        trace_owner[row["case"]] = events[0]["active_memcg"] if events else row["window"]["active_memcg"]
    operation_issue = _phase02_operations(trace, trace_owner, baseline)
    if operation_issue:
        return operation_issue
    return _rollback_compatible(d.get("rollback_compatibility"), baseline)


def _phase02_operations(trace: dict[str, Any], trace_owner: dict[str, str], baseline: dict[str, Any]) -> list[str]:
    operation_rows = trace.get("operation_rows")
    required_pairs = {(api, operation) for api in ("cuda_malloc", "cuda_malloc_repeat", "cuda_malloc_managed", "pytorch_empty")
                      for operation in ("allocation", "residency", "migration")}
    if not isinstance(operation_rows, list) or any(not isinstance(row, dict) for row in operation_rows):
        raise MissingEvidence("phase 02 raw allocation/residency/migration observations are required")
    observed_pairs = {(row.get("api"), row.get("operation")) for row in operation_rows}
    if observed_pairs != required_pairs or len(operation_rows) != len(required_pairs):
        raise MissingEvidence("phase 02 must distinguish allocation, residency and migration for every GPU API")
    api_trace = {"cuda_malloc_repeat": "cuda_malloc"}
    for row in operation_rows:
        raw = _raw_json(row.get("raw_event"))
        if not isinstance(raw, dict) or row.get("raw_event_sha256") != hashlib.sha256(row["raw_event"].encode()).hexdigest():
            raise MissingEvidence("phase 02 operation evidence requires hashed raw event bytes")
        api = row["api"]
        trace_case = api_trace.get(api)
        owner = trace_owner.get(api if trace_case is None else trace_case)
        if (raw.get("api") != api or raw.get("operation") != row["operation"] or
                type(raw.get("bytes")) is not int or raw["bytes"] < 0 or
                raw.get("owner_memcg") != owner or type(raw.get("pid")) is not int or
                not isinstance(raw.get("timestamp_ns"), int) or raw.get("boot_id") != baseline["boot_id"]):
            return [f"phase 02 {api}/{row['operation']} raw event does not match owner/stack identity"]

    return []


def _rollback_compatible(rollback: Any, baseline: dict[str, Any]) -> list[str]:
    if not isinstance(rollback, dict):
        raise MissingEvidence("phase 03 requires the captured compatible original stack restoration plan")
    original = rollback.get("original_stack")
    original_expected = {key: baseline[key] for key in ("boot_id", "kernel", "driver_version", "gsp", "module_capture")}
    plan = rollback.get("restore_plan")
    if original != original_expected or not isinstance(plan, str) or not plan.strip() or rollback.get("restore_plan_sha256") != hashlib.sha256(plan.encode()).hexdigest():
        return ["phase 03 original compatible-stack return plan does not match the measured 580 captures"]
    return []


def _native_stack(r: dict[str, Any]) -> str | None:
    raw = r.get("raw_run")
    if not isinstance(raw, dict) or not all(isinstance(r.get(k), str) and r[k] for k in ("gsp", "driver_version", "kernel", "cuda_runtime", "pytorch_version", "boot_id")):
        raise MissingEvidence("raw bounded run and matched GSP/userspace/boot identity required")
    expected_prefix = "580." if r["stack"] == "580-baseline" else "615."
    if not r.get("driver_version", "").startswith(expected_prefix) or not r.get("gsp", "").startswith(expected_prefix):
        return f"{r['stack']} driver/GSP versions do not identify the requested stack"
    if not _matches_stack(raw, r):
        return "raw kernel, module, GSP, or driver version capture does not match selected stack"
    result = verify_reproduction(raw)
    if result["status"] != "pass":
        if result["status"] == "unknown" or result["could_not_run_count"]:
            raise MissingEvidence(f"{r['stack']} raw reproduction incomplete: could_not_run={result['could_not_run_count']}")
        return f"{r['stack']} raw reproduction status={result['status']} could_not_run={result['could_not_run_count']}"
    if raw["host"]["boot_id"] != r["boot_id"]:
        return f"{r['stack']} host boot identity differs from run identity"
    if r["stack"] == "615-candidate":
        issue = _runtime_versions(raw, r) or _native_candidate(raw)
        if issue:
            return issue
    return None


def _matches_stack(raw: dict[str, Any], stack: dict[str, Any]) -> bool:
    capture = stack.get("gsp_capture")
    if not isinstance(capture, dict) or capture.get("command") != ["nvidia-smi", "-q"] or capture.get("returncode") != 0:
        return False
    gsp_match = re.search(r"GSP Firmware Version\s*:\s*(\S+)", capture.get("stdout", ""))
    if not gsp_match or gsp_match.group(1) != stack["gsp"]:
        return False
    smi = raw.get("host", {}).get("nvidia_smi", {})
    if smi.get("returncode") != 0 or f"Driver Version: {stack['driver_version']}" not in smi.get("stdout", ""):
        return False
    if raw.get("host", {}).get("uname", {}).get("release") != stack["kernel"]:
        return False
    modules = stack.get("module_capture")
    if not isinstance(modules, dict):
        return False
    for module in ("nvidia", "nvidia_uvm"):
        output = modules.get(module)
        if not isinstance(output, str) or f"version: {stack['driver_version']}" not in output or f"vermagic: {stack['kernel']} " not in output:
            return False
    return True


def _native_candidate(raw: dict[str, Any]) -> str | None:
    derived, issue = _native_dmem(raw)
    if issue:
        return issue
    if derived["cpu_touch"][0] <= 0 or derived["none"][1] != 0:
        return "native-stack CPU positive/no-allocation negative controls failed"
    if any(dmem_delta < 0 for api, (_, dmem_delta) in derived.items() if api not in ("none", "cpu_touch")):
        return "native-stack GPU dmem.current control has a negative allocation delta"
    return None


def _native_report(d: dict[str, Any]) -> dict[str, Any]:
    candidate = next(row for row in d["stack_runs"] if row["stack"] == "615-candidate")
    raw = candidate["raw_run"]
    try:
        _native_controls(d.get("native_controls"))
    except MissingEvidence as exc:
        return {"complete": False, "could_not_run": [str(exc)], "apis": []}
    try:
        derived, issue = _native_dmem(raw)
    except MissingEvidence as exc:
        return {"complete": False, "could_not_run": [str(exc)], "apis": []}
    if issue:
        return {"complete": False, "could_not_run": [issue], "apis": []}
    outcomes = []
    control_report = _native_control_report(d["native_controls"])
    limit_rows = control_report["limits"]
    for api in ("cuda_malloc", "cuda_malloc_repeat", "cuda_malloc_managed", "pytorch_empty"):
        memory_delta, dmem_delta = derived[api]
        requested = APISIZE(raw, api)
        memory_accounted = memory_delta >= requested
        dmem_accounted = dmem_delta >= requested
        memory_limit = limit_rows[f"{api}:memory"]
        dmem_limit = limit_rows[f"{api}:dmem"]
        memory_enforced = memory_limit["classification"] == "rejected_at_limit"
        dmem_enforced = dmem_limit["classification"] == "rejected_at_limit"
        memory_contained = memory_accounted and memory_enforced
        dmem_contained = dmem_accounted and dmem_enforced
        outcomes.append({"api": api, "classification": "contained" if memory_contained or dmem_contained else "gap",
                         "requested_bytes": requested, "memory_current_delta_bytes": memory_delta,
                         "memory_accounted": memory_accounted, "dmem_accounted": dmem_accounted,
                         "memory_limit_enforced": memory_enforced, "dmem_limit_enforced": dmem_enforced,
                         "accounting_gap": not (memory_accounted or dmem_accounted),
                         "enforcement_gap": not (memory_accounted and memory_enforced or dmem_accounted and dmem_enforced),
                         "containment_result": "contained" if memory_contained or dmem_contained else "gap",
                         "dmem_current_delta_bytes": dmem_delta,
                         "unaccounted_bytes": max(0, requested - max(memory_delta, dmem_delta))})
    return {"complete": True, "could_not_run": [], "apis": outcomes,
            "controls": control_report}


def _patch_report(d: dict[str, Any]) -> dict[str, Any]:
    runs = d["paired_runtime_evidence"]
    try:
        derived, issue = _patch_dmem(d, runs)
    except MissingEvidence as exc:
        return {"complete": False, "could_not_run": [str(exc)], "findings": [], "apis": []}
    if issue:
        return {"complete": False, "could_not_run": [], "findings": [issue], "apis": []}
    report = {"complete": True, "could_not_run": [],
              "decision": "patch_required" if derived["gap"] else "no_patch_needed",
              "before": derived["apis"], "apis": derived["apis"],
              "controls": _native_control_report(d["native_controls"])}
    if derived["gap"]:
        # _patch_build_integrity already requires a valid post-build capture.
        after = d["candidate_after_stack"]
        report["after"] = _native_report({"stack_runs": [after], "native_controls": d["native_controls"]})
    return report


def _native_controls(controls: Any) -> str | None:
    if not isinstance(controls, dict):
        raise MissingEvidence("raw below-limit rejection and independent two-cgroup/release controls are required")
    limits = controls.get("limit_observations")
    expected = {f"{api}:{domain}" for api in ("cuda_malloc", "cuda_malloc_repeat", "cuda_malloc_managed", "pytorch_empty") for domain in ("memory", "dmem")}
    if not isinstance(limits, list) or any(not isinstance(row, dict) for row in limits):
        raise MissingEvidence("raw per-API memory/dmem effective-limit observations required")
    identities = {f"{row.get('api')}:{row.get('domain')}" for row in limits}
    if identities != expected or len(limits) != len(expected):
        raise MissingEvidence("raw effective-limit attempts must cover every GPU API and memory/dmem domain exactly once")
    for row in limits:
        if not _limit_observation_complete(row):
            raise MissingEvidence("per-API effective-limit attempt lacks raw request/limit/delta/diagnostic/returncode observations")
    sharing = controls.get("sharing_rows")
    if not isinstance(sharing, list) or len(sharing) < 2 or any(not isinstance(row, dict) for row in sharing):
        raise MissingEvidence("raw independent two-cgroup charge and exact release rows are required")
    if len({row.get("cgroup") for row in sharing}) < 2:
        raise MissingEvidence("raw controls do not identify two independent cgroups")
    if any(not _sharing_observation_complete(row) for row in sharing):
        raise MissingEvidence("independent-cgroup raw controls need identity and before/held/after-release counters")
    return None


def _limit_observation_complete(value: Any) -> bool:
    return (isinstance(value, dict) and isinstance(value.get("api"), str) and isinstance(value.get("domain"), str) and
            value.get("domain") in ("memory", "dmem") and all(type(value.get(key)) is int for key in
            ("returncode", "requested_bytes", "limit_bytes", "before", "after")) and
            0 <= value["limit_bytes"] < value["requested_bytes"] and value["before"] >= 0 and
            value["after"] >= 0 and isinstance(value.get("diagnostic"), str) and bool(value["diagnostic"].strip()))


def _sharing_observation_complete(row: dict[str, Any]) -> bool:
    return (isinstance(row.get("cgroup"), str) and bool(row["cgroup"]) and
            all(type(row.get(key)) is int and row[key] >= 0 for key in ("before", "held", "after_release")))


def _native_control_report(controls: dict[str, Any]) -> dict[str, Any]:
    limits = {}
    for row in controls["limit_observations"]:
        diag_causal = re.search(r"(?i)(?:ENOMEM|EAGAIN|EDQUOT|dmem\.max|memory\.max|cgroup.{0,20}limit|resource limit)", row["diagnostic"]) is not None
        classification = "rejected_at_limit" if row["returncode"] != 0 and row["before"] == row["after"] and diag_causal else "accepted_or_unattributed"
        limits[f"{row['api']}:{row['domain']}"] = {"classification": classification,
                "requested_bytes": row["requested_bytes"], "limit_bytes": row["limit_bytes"],
                "returncode": row["returncode"], "before_bytes": row["before"],
                "after_bytes": row["after"], "diagnostic": row["diagnostic"]}
    return {"limits": limits,
            "independent_cgroups": [{"cgroup": row["cgroup"], "before_bytes": row["before"],
                "held_bytes": row["held"], "after_release_bytes": row["after_release"],
                "classification": "charged_and_released" if row["held"] > row["before"] and row["after_release"] == row["before"] else "gap_or_leak"}
                for row in controls["sharing_rows"]]}


def _runtime_versions(raw: dict[str, Any], stack: dict[str, Any]) -> str | None:
    try:
        cuda = next(run for run in raw["runs"] if run["api"] == "cuda_malloc")
        cuda_held = next(row for row in _observations(cuda) if row["phase"] == "held")
        torch = next(run for run in raw["runs"] if run["api"] == "pytorch_empty")
        torch_held = next(row for row in _observations(torch) if row["phase"] == "held")
    except (KeyError, StopIteration, TypeError, ValueError) as exc:
        return f"runtime version capture incomplete: {exc}"
    if cuda_held.get("cuda_runtime") != stack["cuda_runtime"] or torch_held.get("pytorch_version") != stack["pytorch_version"]:
        return "CUDA/PyTorch userspace version does not match raw bounded runtime rows"
    return None


def _observations(run: dict[str, Any]) -> list[dict[str, Any]]:
    return [json.loads(line) for line in run["stdout"].splitlines()]


def APISIZE(raw: dict[str, Any], api: str) -> int:
    run = next(row for row in raw["runs"] if row["api"] == api)
    return run["requested_mib"] * 1024 * 1024


def _native_dmem(raw: dict[str, Any]) -> tuple[dict[str, tuple[int, int]], str | None]:
    derived = {}
    try:
        runs = raw.get("runs")
        if not isinstance(runs, list) or {row.get("api") for row in runs if isinstance(row, dict)} != set(APIS) or len(runs) != len(APIS):
            raise MissingEvidence("raw per-API stack observations are absent or duplicated")
        for run in raw["runs"]:
            result, unread = verify_case(run)
            if unread:
                raise MissingEvidence(f"615 dmem observations unreadable: {unread[0]}")
            rows = [json.loads(line) for line in run["stdout"].splitlines()]
            by_phase = {row["phase"]: row for row in rows}
            baseline = "before" if run["api"] in ("none", "cpu_touch") else "before_allocation"
            memory_delta = result["held_delta_bytes"]
            dmem_before = by_phase[baseline]["files"]["dmem.current"]["value"]
            dmem_held = by_phase["held"]["files"]["dmem.current"]["value"]
            dmem_after = by_phase["after_release"]["files"]["dmem.current"]["value"]
            if not isinstance(dmem_before, str) or not dmem_before.isdecimal() or not isinstance(dmem_held, str) or not dmem_held.isdecimal():
                raise MissingEvidence(f"{run['api']} dmem.current is unreadable or invalid")
            if not isinstance(dmem_after, str) or not dmem_after.isdecimal():
                raise MissingEvidence(f"{run['api']} released dmem.current is unreadable or invalid")
            if int(dmem_after) != int(dmem_before):
                return {}, f"{run['api']} dmem.current did not return to its captured baseline"
            derived[result["api"]] = (memory_delta, int(dmem_held) - int(dmem_before))
    except (KeyError, TypeError, ValueError) as exc:
        raise MissingEvidence(f"615 dmem evidence malformed: {exc}") from exc
    return derived, None


def _patch(d: dict[str, Any]) -> list[str]:
    runs = d.get("paired_runtime_evidence")
    if not isinstance(runs, list) or len(runs) != 2:
        raise MissingEvidence("paired runtime evidence from phases 01-03 absent")
    native = _native({"stack_runs": runs, "native_controls": d.get("native_controls"),
                      "phase02_trace": d.get("phase02_trace"),
                      "rollback_compatibility": d.get("rollback_compatibility")})
    if native:
        return native
    return _patch_evidence(d, runs)


def _patch_evidence(d: dict[str, Any], runs: list[dict[str, Any]]) -> list[str]:
    derived, issue = _patch_dmem(d, runs)
    if issue:
        return [issue]
    if not derived["gap"]:
        return []
    return _patch_candidate(d)


def _patch_dmem(d: dict[str, Any], runs: list[dict[str, Any]]) -> tuple[dict[str, Any], str | None]:
    by_api = _measurement_samples(d.get("dmem_measurements"))
    run615 = next(r["raw_run"] for r in runs if r["stack"] == "615-candidate")
    request_bytes = {r["api"]: r["requested_mib"] * 1024 * 1024 for r in run615["runs"]}
    native_derived, native_issue = _native_dmem(run615)
    if native_issue:
        return {}, native_issue
    raw_series = _captured_dmem_series(run615)
    if raw_series != by_api:
        raise MissingEvidence("phase 04 dmem.current series differs from the paired raw 615 runtime capture")
    if any(data["held"] < data["before"] for data in by_api.values()):
        return {}, "dmem.current fell during an allocation exposure; the measurement is internally inconsistent"
    api_outcomes = {}
    limit_rows = _native_control_report(d["native_controls"])["limits"]
    for api, data in by_api.items():
        delta = data["held"] - data["before"]
        if api not in ("none", "cpu_touch"):
            memory_delta = native_derived[api][0]
            memory_accounted = memory_delta >= request_bytes[api]
            dmem_accounted = delta >= request_bytes[api]
            memory_enforced = limit_rows[f"{api}:memory"]["classification"] == "rejected_at_limit"
            dmem_enforced = limit_rows[f"{api}:dmem"]["classification"] == "rejected_at_limit"
            memory_contained = memory_accounted and memory_enforced
            dmem_contained = dmem_accounted and dmem_enforced
            api_outcomes[api] = {"classification": "contained" if memory_contained or dmem_contained else "gap",
                                 "requested_bytes": request_bytes[api], "dmem_current_delta_bytes": delta,
                                 "memory_current_delta_bytes": memory_delta,
                                 "memory_accounted": memory_accounted, "dmem_accounted": dmem_accounted,
                                 "memory_limit_enforced": memory_enforced, "dmem_limit_enforced": dmem_enforced,
                                 "accounting_gap": not (memory_accounted or dmem_accounted),
                                 "enforcement_gap": not (memory_accounted and memory_enforced or dmem_accounted and dmem_enforced),
                                 "containment_result": "contained" if memory_contained or dmem_contained else "gap",
                                 "unaccounted_bytes": max(0, request_bytes[api] - max(memory_delta, delta))}
    gap = any(row["classification"] == "gap" for row in api_outcomes.values())
    return {"gap": gap, "apis": api_outcomes}, None


def _measurement_samples(measured: Any) -> dict[str, dict[str, int]]:
    if not isinstance(measured, list) or {x.get("api") for x in measured if isinstance(x, dict)} != set(APIS):
        raise MissingEvidence("raw dmem.current before/held/released values required to derive patch decision")
    if len(measured) != len(APIS) or any(not isinstance(row, dict) for row in measured):
        raise ValueError("duplicate or malformed per-API dmem.current rows")
    output = {}
    for row in measured:
        phases = row.get("samples")
        if not isinstance(phases, list) or {p.get("phase") for p in phases if isinstance(p, dict)} != {"before", "held", "after_release"}:
            raise MissingEvidence(f"raw three-phase dmem.current series absent for {row.get('api')}")
        if len(phases) != 3 or any(not isinstance(sample, dict) for sample in phases):
            raise ValueError(f"duplicate or malformed dmem.current phase for {row.get('api')}")
        if any(type(p.get("value")) is not int or p["value"] < 0 for p in phases):
            raise ValueError(f"invalid raw dmem.current sample for {row.get('api')}")
        output[row["api"]] = {p["phase"]: p["value"] for p in phases}
    return output


def _captured_dmem_series(raw: dict[str, Any]) -> dict[str, dict[str, int]]:
    output = {}
    for run in raw["runs"]:
        observations = _observations(run)
        values = {row["phase"]: row["files"]["dmem.current"]["value"] for row in observations}
        baseline = "before" if run["api"] in ("none", "cpu_touch") else "before_allocation"
        output[run["api"]] = {target: int(values[source]) for target, source in
                              (("before", baseline), ("held", "held"), ("after_release", "after_release"))}
    return output


def _patch_candidate(d: dict[str, Any]) -> list[str]:
    trace = d.get("owner_trace")
    if not isinstance(trace, list) or {row.get("case") for row in trace if isinstance(row, dict)} != set(APIS):
        raise MissingEvidence("measured residual gap lacks raw owner trace rows for all APIs")
    for row in trace:
        derived, issue = _trace_case(row, row.get("events", []))
        if issue:
            return [f"residual owner trace invalid: {issue}"]
        if row["case"] == "none" and derived and derived["charged_bytes"]:
            return ["candidate no-allocation control contains charges"]
    return _patch_build_integrity(d)


def _patch_build_integrity(d: dict[str, Any]) -> list[str]:
    _verified_patch_sources(d)
    build_issue = _candidate_build_issue(d.get("build_log"))
    if build_issue:
        return [build_issue]
    after_issue = _candidate_after_issue(d.get("candidate_after_stack"), d.get("native_controls"))
    if after_issue:
        return [after_issue]
    return _candidate_integrity_issue(d.get("integrity_rows"))


def _verified_patch_sources(d: dict[str, Any]) -> None:
    source = d.get("patch_source")
    if not isinstance(source, dict) or not isinstance(source.get("text"), str) or hashlib.sha256(source["text"].encode()).hexdigest() != source.get("sha256"):
        raise MissingEvidence("measured residual gap lacks hash-verified patch source")
    diff = d.get("patch_diff")
    if not isinstance(diff, dict) or not isinstance(diff.get("text"), str) or not diff["text"].startswith("diff --git ") or hashlib.sha256(diff["text"].encode()).hexdigest() != diff.get("sha256"):
        raise MissingEvidence("measured residual gap lacks a hash-verified reviewable fork diff")


def _candidate_build_issue(build: Any) -> str | None:
    if not isinstance(build, dict) or build.get("command") != ["make", "modules"] or build.get("returncode") != 0 or not isinstance(build.get("stdout"), str):
        raise MissingEvidence("candidate module build log does not show successful exact build command")
    if re.search(r"(?im)^(?:make(?:\[\d+\])?: \*\*\*|[^\n]*\berror:)", build["stdout"]):
        return "candidate module build output contains a compiler/make error despite its reported return code"
    if not all(module in build["stdout"] for module in ("nvidia.ko", "nvidia-uvm.ko")):
        raise MissingEvidence("candidate build output does not identify both required module artifacts")


def _candidate_after_issue(after: Any, controls: Any) -> str | None:
    if not isinstance(after, dict):
        raise MissingEvidence("measured residual gap requires an actual post-build candidate runtime capture")
    after_issue = _native_stack(after)
    if after_issue:
        return f"post-build candidate runtime failed its raw reproduction: {after_issue}"
    after_report = _native_report({"stack_runs": [after], "native_controls": controls})
    if not after_report.get("complete") or any(row["classification"] != "contained" for row in after_report.get("apis", [])):
        return "post-build candidate raw results leave an API accounting/enforcement gap"
    return None


def _candidate_integrity_issue(integrity: Any) -> list[str]:
    required = {"limit_rejection", "error_unwind", "sharing", "migration", "concurrent_release",
                "double_charge", "lost_charge", "teardown"}
    if not isinstance(integrity, list) or {row.get("case") for row in integrity if isinstance(row, dict)} != required:
        raise MissingEvidence("measured residual gap requires raw owner trace and reviewed candidate build/integrity evidence")
    by_case = {row["case"]: row for row in integrity}
    if not _raw_limit_test(by_case["limit_rejection"].get("raw_output")):
        return ["candidate native limit rejection control failed"]
    if not _raw_unwind_test(by_case["error_unwind"].get("raw_output")):
        return ["candidate failed-allocation unwind left dmem charge behind"]
    if not _sharing_correct(by_case["sharing"].get("raw_output")):
        return ["candidate two-cgroup sharing observations failed"]
    if not _migration_balanced(by_case["migration"].get("raw_output")):
        return ["candidate migration owner/charge observations failed"]
    if not _concurrent_balanced(by_case["concurrent_release"].get("raw_output")):
        return ["candidate concurrent charge/uncharge ledger failed"]
    if not _domain_charge_ledger(by_case["double_charge"].get("raw_output")):
        return ["candidate double-charge control found a duplicate physical-page charge"]
    if not _domain_charge_ledger(by_case["lost_charge"].get("raw_output")):
        return ["candidate lost-charge control found unmatched charge or release"]
    if not _sharing_correct(by_case["teardown"].get("raw_output")):
        return ["candidate cgroup teardown failed to return all counters to baseline"]
    return []


def _raw_json(value: Any) -> dict[str, Any] | list[Any] | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = json.loads(value)
    except (json.JSONDecodeError, RecursionError):
        return None
    return parsed if isinstance(parsed, (dict, list)) else None


def _raw_limit_test(value: Any) -> bool:
    parsed = _raw_json(value)
    if not isinstance(parsed, dict):
        return False
    required = ("requested_bytes", "limit_bytes", "before", "after", "diagnostic")
    if any(type(parsed.get(key)) is not int for key in ("returncode", "requested_bytes", "limit_bytes", "before", "after")):
        return False
    diagnostic = parsed.get("diagnostic")
    return (parsed["returncode"] != 0 and 0 <= parsed["limit_bytes"] < parsed["requested_bytes"] and
            parsed["before"] == parsed["after"] and isinstance(diagnostic, str) and
            re.search(r"(?i)(?:ENOMEM|EAGAIN|EDQUOT|dmem\.max|memory\.max|cgroup.{0,20}limit|resource limit)", diagnostic) is not None)


def _raw_unwind_test(value: Any) -> bool:
    parsed = _raw_json(value)
    return isinstance(parsed, dict) and type(parsed.get("returncode")) is int and parsed["returncode"] != 0 and type(parsed.get("before")) is int and parsed.get("after") == parsed["before"]


def _sharing_correct(rows: Any) -> bool:
    if isinstance(rows, str):
        rows = _raw_json(rows)
    if not isinstance(rows, list) or len(rows) < 2:
        return False
    ids = {row.get("cgroup") for row in rows if isinstance(row, dict)}
    return len(ids) == 2 and all(isinstance(row.get("before"), int) and isinstance(row.get("held"), int) and isinstance(row.get("after_release"), int) and row["held"] > row["before"] and row["after_release"] == row["before"] for row in rows)


def _migration_balanced(value: Any) -> bool:
    rows = _raw_json(value)
    if not isinstance(rows, list) or len(rows) < 2 or any(not isinstance(row, dict) for row in rows):
        return False
    owners = {owner for row in rows for owner in (row.get("from_owner"), row.get("to_owner"))}
    stamps = [row.get("timestamp_ns") for row in rows]
    return (len(owners) >= 2 and all(isinstance(row.get("page"), str) and row["page"] and
            isinstance(row.get("from_owner"), str) and isinstance(row.get("to_owner"), str) and row["from_owner"] != row["to_owner"] and
            type(row.get("bytes")) is int and row["bytes"] > 0 and row.get("charged_bytes") == row["bytes"] and
            row.get("freed_bytes") == row["bytes"] for row in rows) and
            all(type(stamp) is int for stamp in stamps) and all(a < b for a, b in zip(stamps, stamps[1:])))


def _concurrent_balanced(value: Any) -> bool:
    rows = _raw_json(value)
    if not isinstance(rows, list) or not rows:
        return False
    try:
        derived, issue = _trace_ledger({"case": "concurrent_release"}, rows)
        return issue is None and derived is not None and derived["outstanding_bytes"] == 0
    except (KeyError, TypeError):
        return False


def _domain_charge_ledger(value: Any) -> bool:
    rows = _raw_json(value)
    if not isinstance(rows, list) or not rows or any(not isinstance(row, dict) for row in rows):
        return False
    physical_pages: dict[str, str] = {}
    events = []
    for row in rows:
        if not all(isinstance(row.get(key), str) and row[key] for key in ("event", "page", "domain", "owner_memcg")):
            return False
        if type(row.get("bytes")) is not int or row["bytes"] < 0:
            return False
        previous = physical_pages.setdefault(row["page"], row["domain"])
        if previous != row["domain"]:
            return False
        events.append({"event": row["event"], "page": row["domain"] + ":" + row["page"], "bytes": row["bytes"]})
    derived, issue = _trace_ledger({"case": "candidate_domain_ledger"}, events)
    return issue is None and derived is not None and derived["outstanding_bytes"] == 0


def _hangs(d: dict[str, Any]) -> list[str]:
    runs = d["incidents"]
    if not isinstance(runs, list) or len(runs) < 2:
        raise MissingEvidence("comparable baseline/candidate incident captures required")
    if {r.get("stack") for r in runs} != {"baseline", "candidate"}:
        return ["baseline and candidate runs must both be present"]
    return _compare_hang_runs(runs)


def _compare_hang_runs(runs: list[dict[str, Any]]) -> list[str]:
    outputs = [_hang_run(r) for r in runs]
    if any(issue for _, issue in outputs):
        return [issue for _, issue in outputs if issue]
    case_sets = [row[0][0] for row in outputs]
    sizes = [row[0][1] for row in outputs]
    required = {"none", "cpu_touch", "cuda_malloc", "cuda_malloc_managed", "pytorch_empty"}
    if case_sets[0] != required or case_sets[1] != required:
        return ["each stack needs raw none/CPU/CUDA/managed/PyTorch cases"]
    if sizes[0] != sizes[1]:
        return ["baseline and candidate do not cover the same API/size cases"]
    return []


def _hang_run(r: dict[str, Any]) -> tuple[tuple[set[str], set[tuple[str, int]]], str | None]:
    samples, journal = r.get("samples"), r.get("journal")
    if not isinstance(samples, list) or not samples or not isinstance(journal, list):
        raise MissingEvidence("raw samples and JSON journal events required per run")
    valid_samples = all(isinstance(row, dict) and isinstance(row.get("monotonic_ns"), int) and isinstance(row.get("api"), str) and isinstance(row.get("requested_bytes"), int) and isinstance(row.get("memory_current"), int) and isinstance(row.get("cgroup"), str) for row in samples)
    if not valid_samples:
        raise ValueError("raw sample rows need monotonic time, API, requested bytes and memory.current")
    if any(a["monotonic_ns"] >= b["monotonic_ns"] for a, b in zip(samples, samples[1:])):
        return (set(), set()), "sample timestamps are not increasing"
    start, end = r.get("started_ns"), r.get("ended_ns")
    if not isinstance(start, int) or not isinstance(end, int) or start >= end:
        return (set(), set()), "positive exposure interval absent"
    if any(not isinstance(e, dict) or not isinstance(e.get("monotonic_ns"), int) or not isinstance(e.get("message"), str) for e in journal):
        raise ValueError("raw journal rows require monotonic timestamp and message")
    if any(not start <= event["monotonic_ns"] <= end for event in journal):
        return (set(), set()), "journal records fall outside the measured exposure interval"
    response = r.get("service_response")
    if not isinstance(response, str) or not response.strip():
        return (set(), set()), "service returned no useful response bytes"
    pairs = {(row["api"], row["requested_bytes"]) for row in samples}
    return ({api for api, _ in pairs}, pairs), None


def result(status: str, reasons: list[str], could_not_run: int) -> dict[str, Any]:
    return {"status": status, "findings": reasons, "could_not_run": could_not_run,
            "could_not_run_count": could_not_run, "fail": int(status == "fail")}


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--phase", required=True, choices=PHASES)
    p.add_argument("--evidence", type=Path, required=True)
    args = p.parse_args(argv)
    out = verify(args.phase, args.evidence)
    print(json.dumps(out, sort_keys=True))
    return {"pass": 0, "fail": 1, "unknown": 2}[out["status"]]


if __name__ == "__main__":
    sys.exit(main())
