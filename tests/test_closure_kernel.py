"""Focused positive/negative controls for the kernel closure evaluators."""
from __future__ import annotations

import json
import hashlib
import subprocess
import sys
from pathlib import Path

from tools.verify_cgroup_plan import verify as verify_cgroup
from tools.verify_cgroup_plan import _native as verify_native
from tools.verify_cgroup_plan import _patch as verify_patch
from tools.verify_cgroup_plan import _trace as verify_trace
from tools.verify_cgroup_plan import _hangs as verify_hangs
from tools.verify_cgroup_repro import APIS
from tools.verify_forum_pstore import verify as verify_forum
from tools.verify_memory_saver import verify as verify_memory
from tools.verify_netconsole import _receiver as verify_receiver, verify as verify_netconsole
from tools.verify_rcu_panic_pstore import verify as verify_rcu



def _asserted_status(result: dict[str, object] | None) -> object:
    assert result is not None, "verifier returned no result object"
    return result["status"]

def put(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")


def test_cgroup_rejects_cross_phase_and_requires_dynamic_rows(tmp_path):
    root = tmp_path / "evidence"
    put(root / "capture.json", {"schema": 1, "id": "FEATURE-1358-CGROUP-03-NATIVO", "phase": "03-nativo",
                                  "host": {"boot_id": "b", "kernel": "k", "driver": "d"}})
    assert _asserted_status(verify_cgroup("02-traza", root)) == "fail"
    assert _asserted_status(verify_cgroup("03-nativo", root)) == "unknown"


def test_cgroup_phase_router_reports_unsupported_identity_and_derived_failures(tmp_path):
    root = tmp_path / "phase"
    assert _asserted_status(verify_cgroup("unsupported", root)) == "fail"
    base = {"schema": 1, "id": "FEATURE-1358-CGROUP-02-TRAZA", "phase": "02-traza",
            "host": {"boot_id": "", "kernel": "k", "driver": "d"}, "allocations": []}
    put(root / "capture.json", base)
    assert _asserted_status(verify_cgroup("02-traza", root)) == "unknown"
    base["host"]["boot_id"] = "boot"
    put(root / "capture.json", base)
    assert _asserted_status(verify_cgroup("02-traza", root)) == "unknown"
    base["id"] = "FEATURE-1358-CGROUP-04-PARCHE"
    put(root / "capture.json", base)
    assert _asserted_status(verify_cgroup("02-traza", root)) == "fail"


def test_cgroup_phase02_reports_raw_negative_and_missing_trace_shapes(tmp_path):
    import pytest
    from tools.verify_cgroup_plan import MissingEvidence, _trace
    with pytest.raises(MissingEvidence):
        _trace({"allocations": [None]})
    with pytest.raises(MissingEvidence):
        _trace({"allocations": _closure_trace_rows()[:-1]})
    rows = _closure_trace_rows()
    rows[0].pop("trace_rows")
    with pytest.raises(MissingEvidence):
        _trace({"allocations": rows})
    root = tmp_path / "phase02-bad"
    duplicate = _closure_trace_rows(); duplicate.append(json.loads(json.dumps(duplicate[0])))
    put(root / "capture.json", {"schema": 1, "id": "FEATURE-1358-CGROUP-02-TRAZA", "phase": "02-traza",
        "host": {"boot_id": "b", "kernel": "k", "driver": "d"}, "allocations": duplicate})
    assert _asserted_status(verify_cgroup("02-traza", root)) == "fail"
    from tools.verify_cgroup_plan import _trace_case
    with pytest.raises(MissingEvidence, match="empty trace lacks observed"):
        _trace_case({"case": "empty"}, [])


def test_cgroup_malformed_nested_json_and_oversize_are_unknown(tmp_path, capsys):
    from tools.verify_cgroup_plan import main
    root = tmp_path / "evidence"
    for value in ([], {"schema": 1, "id": "FEATURE-1358-CGROUP-02-TRAZA", "phase": "02-traza", "host": None}):
        put(root / "capture.json", value)
        assert _asserted_status(verify_cgroup("02-traza", root)) == "unknown"
    (root / "capture.json").write_bytes(b" " * (16 * 1024 * 1024 + 1))
    assert _asserted_status(verify_cgroup("02-traza", root)) == "unknown"
    assert main(["--phase", "02-traza", "--evidence", str(tmp_path / "absent")]) == 2
    assert json.loads(capsys.readouterr().out)["could_not_run_count"] == 1


def test_cgroup_recursive_json_and_duplicate_api_observations_are_rejected(tmp_path):
    root = tmp_path / "recursive"
    root.mkdir()
    (root / "capture.json").write_text("[" * 6000 + "0" + "]" * 6000, encoding="utf-8")
    assert _asserted_status(verify_cgroup("02-traza", root)) == "unknown"
    rows = _closure_trace_rows()
    rows.append(json.loads(json.dumps(rows[0])))
    assert "duplicate allocation case" in verify_trace({"allocations": rows})[0]


def test_kernel_evaluator_bounded_parsers_report_recursive_json_as_unknown(tmp_path):
    recursive = "[" * 6000 + "0" + "]" * 6000
    cases = (
        (verify_netconsole, "kernel-capture.json"),
        (verify_rcu, "recovery.json"),
        (lambda path: verify_memory("02-trazador", path), "capture.json"),
        (lambda path: verify_forum("FORUM-02-PSTORE-KERNEL-REGRESSION", path), "finding.json"),
    )
    for evaluate, filename in cases:
        directory = tmp_path / filename
        directory.mkdir()
        (directory / filename).write_text(recursive, encoding="utf-8")
        if filename == "kernel-capture.json":
            (directory / "receiver.json").write_text("{}", encoding="utf-8")
        assert _asserted_status(evaluate(directory)) == "unknown"


def test_cgroup_trace_selector_evaluates_exact_phase_raw_capture(tmp_path):
    root = tmp_path / "phase02"
    put(root / "capture.json", {"schema": 1, "id": "FEATURE-1358-CGROUP-02-TRAZA",
        "phase": "02-traza", "host": {"boot_id": "boot", "kernel": "6.17", "driver": "615"},
        "allocations": _closure_trace_rows()})
    assert _asserted_status(verify_cgroup("02-traza", root)) == "pass"
    doc = json.loads((root / "capture.json").read_text(encoding="utf-8"))
    doc["host"] = None
    put(root / "capture.json", doc)
    assert _asserted_status(verify_cgroup("02-traza", root)) == "unknown"


def test_cgroup_nativo_needs_paired_complete_raw_runs(tmp_path):
    root = tmp_path / "evidence"
    put(root / "capture.json", {"schema": 1, "id": "FEATURE-1358-CGROUP-03-NATIVO", "phase": "03-nativo",
                                  "host": {"boot_id": "b", "kernel": "k", "driver": "d"},
                                  "stack_runs": [{"stack": "580-baseline"}, {"stack": "615-candidate"}]})
    assert _asserted_status(verify_cgroup("03-nativo", root)) == "unknown"


def test_cgroup_trace_computes_positive_balanced_allocation_and_empty_negative():
    rows = []
    cases = ("cpu_touch", "none", "cuda_malloc", "cuda_malloc_managed", "pytorch_empty")
    for index, name in enumerate(cases):
        events = [] if name == "none" else [
            {"event": "charge", "timestamp_ns": 1, "pid": index + 1, "cgroup": name,
             "active_memcg": name, "flags": "__GFP_ACCOUNT", "bytes": 4096, "page": name,
             "stack": ["charge", "allocation"]},
            {"event": "uncharge", "timestamp_ns": 2, "pid": index + 1, "cgroup": name,
             "active_memcg": name, "flags": "__GFP_ACCOUNT", "bytes": 4096, "page": name,
             "stack": ["uncharge", "free"]},
        ]
        row = {"case": name, "pid": index + 1, "cgroup": name, "trace_rows": events,
               "trace_sha256": hashlib.sha256(json.dumps(events, sort_keys=True, separators=(",", ":")).encode()).hexdigest()}
        if not events:
            row["window"] = {"pid": str(index + 1), "cgroup": name, "active_memcg": name, "start_ns": 0, "end_ns": 3,
                             "probe_active": True, "heartbeat_rows": [{"timestamp_ns": 1, "pid": str(index + 1),
                                                                          "cgroup": name, "active_memcg": name,
                                                                          "probe_active": True}]}
        rows.append(row)
    assert verify_trace({"allocations": rows}) == []
    rows[-1]["trace_rows"][1]["page"] = "other"
    rows[-1]["trace_sha256"] = hashlib.sha256(json.dumps(rows[-1]["trace_rows"], sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    assert "unmatched uncharge" in verify_trace({"allocations": rows})[0]


def test_cgroup_trace_adversarial_owner_probe_page_and_digest_cases():
    import pytest
    from tools.verify_cgroup_plan import MissingEvidence
    rows = _closure_trace_rows()
    assert verify_trace({"allocations": rows}) == []
    rows[1]["trace_rows"] = [{"event": "charge", "timestamp_ns": 1, "pid": 2, "cgroup": "none",
        "active_memcg": "none", "flags": "accounted", "bytes": 4096, "page": "p", "stack": ["charge"]}]
    rows[1]["trace_sha256"] = hashlib.sha256(json.dumps(rows[1]["trace_rows"], sort_keys=True,
        separators=(",", ":")).encode()).hexdigest()
    assert "no-allocation control" in verify_trace({"allocations": rows})[0]
    rows = _closure_trace_rows()
    rows[0]["trace_rows"][0]["active_memcg"] = "other"
    rows[0]["trace_rows"][1]["timestamp_ns"] = 1
    assert "identity change or non-increasing" in verify_trace({"allocations": rows})[0]
    rows = _closure_trace_rows()
    rows[0]["trace_rows"][0]["active_memcg"] = "unknown"
    rows[0]["trace_rows"][1]["active_memcg"] = "unknown"
    rows[0]["trace_sha256"] = hashlib.sha256(json.dumps(rows[0]["trace_rows"], sort_keys=True,
        separators=(",", ":")).encode()).hexdigest()
    with pytest.raises(MissingEvidence, match="owner or task cgroup is unobserved"):
        verify_trace({"allocations": rows})
    rows = _closure_trace_rows()
    rows[0]["pid"] = 999
    assert "does not match observed task" in verify_trace({"allocations": rows})[0]
    rows = _closure_trace_rows()
    rows[0]["trace_sha256"] = "bad"
    assert "digest mismatch" in verify_trace({"allocations": rows})[0]
    rows = _closure_trace_rows()
    rows[0]["trace_rows"][1]["page"] = "wrong-page"
    rows[0]["trace_sha256"] = hashlib.sha256(json.dumps(rows[0]["trace_rows"], sort_keys=True,
        separators=(",", ":")).encode()).hexdigest()
    assert "unmatched uncharge" in verify_trace({"allocations": rows})[0]
    rows = _closure_trace_rows()
    rows[0]["trace_rows"][0]["bytes"] = True
    with pytest.raises(ValueError):
        verify_trace({"allocations": rows})
    rows = _closure_trace_rows()
    rows[0]["trace_rows"][0].pop("flags")
    with pytest.raises(ValueError):
        verify_trace({"allocations": rows})


def test_cgroup_trace_empty_probe_and_page_ledgers_require_real_pairs():
    import pytest
    from tools.verify_cgroup_plan import MissingEvidence
    rows = _closure_trace_rows()
    rows[1]["window"]["heartbeat_rows"][0]["probe_active"] = False
    assert "inactive or misattributed" in verify_trace({"allocations": rows})[0]
    rows = _closure_trace_rows()
    rows[1]["window"]["heartbeat_rows"] = []
    with pytest.raises(MissingEvidence):
        verify_trace({"allocations": rows})
    with pytest.raises(MissingEvidence):
        verify_trace({"allocations": []})
    with pytest.raises(MissingEvidence):
        verify_trace({"allocations": [{"case": "cpu_touch"}]})
    rows = _closure_trace_rows()
    rows[0]["trace_rows"] = []
    rows[0]["trace_sha256"] = hashlib.sha256(b"[]").hexdigest()
    rows[0]["window"] = {"pid": "1", "cgroup": "cpu_touch", "active_memcg": "cpu_touch",
        "start_ns": 0, "end_ns": 3, "probe_active": True,
        "heartbeat_rows": [{"timestamp_ns": 1, "pid": "1", "cgroup": "cpu_touch",
                            "active_memcg": "cpu_touch", "probe_active": True}]}
    assert "CPU trace positive" in verify_trace({"allocations": rows})[0]
    rows = _closure_trace_rows()
    rows[1]["trace_sha256"] = "wrong"
    assert "empty-trace digest" in verify_trace({"allocations": rows})[0]
    rows = _closure_trace_rows()
    rows[1]["window"]["end_ns"] = 0
    with pytest.raises(ValueError):
        verify_trace({"allocations": rows})
    rows = _closure_trace_rows()
    rows[0]["trace_rows"] = [dict(rows[0]["trace_rows"][0]), dict(rows[0]["trace_rows"][0])]
    rows[0]["trace_rows"][1]["timestamp_ns"] = 2
    rows[0]["trace_sha256"] = hashlib.sha256(json.dumps(rows[0]["trace_rows"], sort_keys=True,
        separators=(",", ":")).encode()).hexdigest()
    assert "duplicate or unidentified charge" in verify_trace({"allocations": rows})[0]


def test_cgroup_trace_rejects_negative_bytes_and_reports_failure_only_events():
    import pytest
    from tools.verify_cgroup_plan import _trace_case
    bad = _closure_trace_rows()[0]
    bad["trace_rows"][0]["bytes"] = -1
    with pytest.raises(ValueError, match="invalid raw event"):
        _trace_case(bad, bad["trace_rows"])
    rows = _closure_trace_rows()
    event = dict(rows[0]["trace_rows"][0], event="failure", page="", bytes=0)
    rows[0]["trace_rows"] = [event]
    rows[0]["trace_sha256"] = hashlib.sha256(json.dumps([event], sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    assert verify_trace({"allocations": rows}) == ["CPU trace positive control did not observe balanced page charges"]


def test_cgroup_native_phase_reports_missing_and_malformed_capture_classes():
    import pytest
    from tools.verify_cgroup_plan import MissingEvidence, _native
    with pytest.raises(MissingEvidence, match="paired raw stack"):
        _native({"stack_runs": None})
    with pytest.raises(MissingEvidence, match="paired 580"):
        _native({"stack_runs": [{"stack": "580-baseline"}]})
    with pytest.raises(MissingEvidence, match="raw bounded run"):
        _native({"stack_runs": [{"stack": "580-baseline"}, {"stack": "615-candidate"}]})


def test_cgroup_patch_measurement_rows_and_raw_limit_parsers_reject_ambiguity():
    import pytest
    from tools.verify_cgroup_plan import MissingEvidence, _measurement_samples, _raw_json, _raw_limit_test
    with pytest.raises(MissingEvidence):
        _measurement_samples(None)
    with pytest.raises(ValueError, match="duplicate"):
        _measurement_samples([{"api": api, "samples": []} for api in APIS] + [{"api": "none", "samples": []}])
    assert _raw_json("{") is None
    assert not _raw_limit_test(json.dumps({"returncode": 0, "requested_bytes": 2, "limit_bytes": 1,
        "before": 0, "after": 0, "diagnostic": "resource limit"}))


def test_cgroup_phase03_and04_report_complete_and_incomplete_decisions(tmp_path):
    import pytest
    from tools.verify_cgroup_plan import _native_report, _patch_report
    root = tmp_path / "reports"
    pair = _native_pair()
    pair[1]["raw_run"] = _native_run(charge_dmem=False, version="615.71.09")
    doc = {"schema": 1, "id": "FEATURE-1358-CGROUP-03-NATIVO", "phase": "03-nativo",
           "host": {"boot_id": "boot-a", "kernel": "6.17", "driver": "615"},
           **_native_evidence(pair)}
    put(root / "capture.json", doc)
    result = verify_cgroup("03-nativo", root)
    assert _asserted_status(result) == "pass" and result["evaluation"]["complete"]
    bad = json.loads(json.dumps(doc))
    bad["stack_runs"][1]["raw_run"]["runs"] = []
    incomplete = _native_report(bad)
    assert incomplete["complete"] is False and incomplete["could_not_run"]
    incomplete_patch = _patch_report({"paired_runtime_evidence": []})
    assert incomplete_patch["complete"] is False and incomplete_patch["could_not_run"]


def test_cgroup_patch_dmem_rejects_mismatch_release_and_negative_samples():
    from tools.verify_cgroup_plan import MissingEvidence, _patch_dmem
    import pytest
    evidence = _patch_candidate_evidence()
    with pytest.raises(MissingEvidence, match="raw dmem"):
        _patch_dmem({**evidence, "dmem_measurements": []}, evidence["paired_runtime_evidence"])
    measurements = json.loads(json.dumps(evidence["dmem_measurements"]))
    measurements[0]["samples"][0]["value"] = -1
    with pytest.raises(ValueError, match="invalid raw"):
        _patch_dmem({**evidence, "dmem_measurements": measurements}, evidence["paired_runtime_evidence"])
    bad = _native_pair()
    rows = [json.loads(line) for line in bad[1]["raw_run"]["runs"][0]["stdout"].splitlines()]
    rows[-1]["files"]["dmem.current"]["value"] = "1"
    bad[1]["raw_run"]["runs"][0]["stdout"] = "\n".join(json.dumps(row) for row in rows)
    measurements = json.loads(json.dumps(evidence["dmem_measurements"]))
    measurements[0]["samples"][-1]["value"] = 1
    derived, issue = _patch_dmem({**evidence, "dmem_measurements": measurements}, bad)
    assert derived == {} and issue and "baseline" in issue


def test_cgroup_cli_pass_fail_and_native_raw_dmem_failure_paths(tmp_path, capsys):
    import pytest
    from tools.verify_cgroup_plan import main as cgroup_main
    root = tmp_path / "trace"; root.mkdir()
    put(root / "capture.json", {"schema": 1, "id": "FEATURE-1358-CGROUP-02-TRAZA", "phase": "02-traza",
        "host": {"boot_id": "b", "kernel": "k", "driver": "d"}, "allocations": _closure_trace_rows()})
    assert cgroup_main(["--phase", "02-traza", "--evidence", str(root)]) == 0
    doc = json.loads((root / "capture.json").read_text(encoding="utf-8")); doc["id"] = "wrong"; put(root / "capture.json", doc)
    assert cgroup_main(["--phase", "02-traza", "--evidence", str(root)]) == 1


def _closure_trace_rows():
    cases = ("cpu_touch", "none", "cuda_malloc", "cuda_malloc_managed", "pytorch_empty")
    result = []
    for index, name in enumerate(cases):
        events = [] if name == "none" else [
            {"event": "charge", "timestamp_ns": 1, "pid": index + 1, "cgroup": name,
             "active_memcg": name, "flags": "__GFP_ACCOUNT", "bytes": 4096, "page": name,
             "stack": ["charge"]},
            {"event": "uncharge", "timestamp_ns": 2, "pid": index + 1, "cgroup": name,
             "active_memcg": name, "flags": "__GFP_ACCOUNT", "bytes": 4096, "page": name,
             "stack": ["uncharge"]}]
        row = {"case": name, "pid": index + 1, "cgroup": name, "trace_rows": events,
               "trace_sha256": hashlib.sha256(json.dumps(events, sort_keys=True, separators=(",", ":")).encode()).hexdigest()}
        if not events:
            row["window"] = {"pid": str(index + 1), "cgroup": name, "active_memcg": name,
                "start_ns": 0, "end_ns": 3, "probe_active": True,
                "heartbeat_rows": [{"timestamp_ns": 1, "pid": str(index + 1), "cgroup": name,
                                    "active_memcg": name, "probe_active": True}]}
        result.append(row)
    return result


def _native_run(charge_dmem, version, charge_memory=False):
    runs = []
    for api, worker in APIS.items():
        phases = ["before"]
        if worker not in ("none", "cpu_touch"):
            phases.append("before_allocation")
        phases.append("held")
        if worker == "pytorch_empty":
            phases.append("allocator_cache_released")
        phases.append("after_release")
        lines = []
        for tick, phase in enumerate(phases, 1):
            current = 1_048_576 if phase == "held" and (api == "cpu_touch" or charge_memory and api not in ("none",)) else 0
            dmem = 1_048_576 if charge_dmem and api not in ("none", "cpu_touch") and phase == "held" else 0
            row = {"phase": phase, "pid": 2, "monotonic_ns": tick,
                   "cgroup_path": f"/sys/fs/cgroup/{api}.scope", "requested_bytes": 0 if api == "none" else 1_048_576,
                   "proc_cgroup_error": None, "mem_available_error": None, "host_memory_pressure_error": None,
                   "files": {name: {"value": str(dmem if name == "dmem.current" else current if name == "memory.current" else 0), "error": None}
                             for name in ("memory.current", "memory.events", "memory.pressure", "dmem.current")}}
            if phase == "held" and api == "cuda_malloc":
                row["cuda_runtime"] = "libcudart.so.615"
            if phase == "held" and api == "pytorch_empty":
                row["pytorch_version"] = "2.9.0"
            lines.append(json.dumps(row))
        runs.append({"api": api, "worker_api": worker, "unit": api, "requested_mib": 1,
                     "returncode": 0, "stdout": "\n".join(lines)})
    return {"schema": 1, "host": {"boot_id": "boot-a", "uname": {"release": "6.17.0-1032-nvidia"},
            "nvidia_smi": {"returncode": 0, "stdout": f"Driver Version: {version}"}}, "runs": runs}


def _native_pair():
    return [{"stack": name, "raw_run": _native_run(charge_dmem=True, version=version),
             "gsp": version, "driver_version": version, "kernel": "6.17.0-1032-nvidia",
             "module_capture": {module: f"version: {version}\nvermagic: 6.17.0-1032-nvidia SMP\n"
                                for module in ("nvidia", "nvidia_uvm")},
             "cuda_runtime": "libcudart.so.615", "pytorch_version": "2.9.0", "boot_id": "boot-a",
             "gsp_capture": {"command": ["nvidia-smi", "-q"], "returncode": 0,
                             "stdout": f"GSP Firmware Version : {version}"}}
            for name, version in (("580-baseline", "580.178.04"), ("615-candidate", "615.71.09"))]


def _native_controls():
    return {"limit_observations": [{"api": api, "domain": domain, "returncode": 1,
        "requested_bytes": 1_048_576, "limit_bytes": 524_288, "before": 0, "after": 0,
        "diagnostic": f"{domain}.max resource limit"}
        for api in ("cuda_malloc", "cuda_malloc_repeat", "cuda_malloc_managed", "pytorch_empty")
        for domain in ("memory", "dmem")],
        "sharing_rows": [{"cgroup": cg, "before": 0, "held": 1_048_576, "after_release": 0}
                         for cg in ("a", "b")]}


def _phase02_trace(pair):
    baseline = next(row for row in pair if row["stack"] == "580-baseline")
    rows = _closure_trace_rows()
    operations = []
    for api in ("cuda_malloc", "cuda_malloc_repeat", "cuda_malloc_managed", "pytorch_empty"):
        owner = "cuda_malloc" if api == "cuda_malloc_repeat" else api
        for kind in ("allocation", "residency", "migration"):
            raw = json.dumps({"api": api, "operation": kind, "bytes": 4096, "owner_memcg": owner,
                "pid": 1, "timestamp_ns": 10, "boot_id": baseline["boot_id"]}, sort_keys=True)
            operations.append({"api": api, "operation": kind, "raw_event": raw,
                "raw_event_sha256": hashlib.sha256(raw.encode()).hexdigest()})
    return {"id": "FEATURE-1358-CGROUP-02-TRAZA", "phase": "02-traza",
        "stack_identity": {key: baseline[key] for key in ("boot_id", "kernel", "driver_version", "gsp")},
        "allocations": rows, "operation_rows": operations,
        "provenance": "caller-supplied; unauthenticated"}


def _native_evidence(pair, controls=None):
    baseline = next(row for row in pair if row["stack"] == "580-baseline")
    plan = "Restore the measured 580 modules, GSP and compatible userspace before deployment."
    return {"stack_runs": pair, "native_controls": controls if controls is not None else _native_controls(),
        "phase02_trace": _phase02_trace(pair),
        "rollback_compatibility": {"original_stack": {key: baseline[key] for key in
            ("boot_id", "kernel", "driver_version", "gsp", "module_capture")},
            "restore_plan": plan, "restore_plan_sha256": hashlib.sha256(plan.encode()).hexdigest()}}


def test_cgroup_native_capture_identity_adversaries():
    pair = _native_pair()
    bad_pair = [{**pair[0], "driver_version": "615.1"}, pair[1]]
    assert "do not identify" in verify_native(_native_evidence(bad_pair))[0]
    for mutation in (
        lambda rows: rows[0]["gsp_capture"].update(command=["cat"]),
        lambda rows: rows[0]["gsp_capture"].update(stdout="GSP Firmware Version : other"),
        lambda rows: rows[0]["raw_run"]["host"]["nvidia_smi"].update(stdout="Driver Version: wrong"),
        lambda rows: rows[0]["raw_run"]["host"]["uname"].update(release="other"),
        lambda rows: rows[0]["module_capture"].pop("nvidia_uvm"),
    ):
        rows = json.loads(json.dumps(pair))
        mutation(rows)
        assert "does not match" in verify_native(_native_evidence(rows))[0]


def test_cgroup_native_runtime_identity_and_missing_capture_are_distinct():
    from tools.verify_cgroup_plan import MissingEvidence, _runtime_versions, _native_stack
    import pytest
    raw = _native_run(charge_dmem=True, version="615.71.09")
    stack = {"cuda_runtime": "libcudart.so.615", "pytorch_version": "2.9.0"}
    assert _runtime_versions(raw, stack) is None
    issue = _runtime_versions(raw, {**stack, "cuda_runtime": "wrong"})
    assert issue is not None and "does not match" in issue
    malformed = json.loads(json.dumps(raw))
    malformed["runs"] = []
    issue = _runtime_versions(malformed, stack)
    assert issue is not None and "incomplete" in issue
    with pytest.raises(MissingEvidence):
        verify_native({"stack_runs": None})
    pair = _native_pair()
    issue = _native_stack({**pair[0], "boot_id": "other"})
    assert issue is not None and "boot identity differs" in issue
    missing = json.loads(json.dumps(pair[0])); missing["raw_run"]["runs"] = []
    with pytest.raises(MissingEvidence, match="incomplete"):
        _native_stack(missing)
    versions = json.loads(json.dumps(pair[1]))
    cuda_run = next(row for row in versions["raw_run"]["runs"] if row["api"] == "cuda_malloc")
    lines = [json.loads(line) for line in cuda_run["stdout"].splitlines()]
    next(row for row in lines if row["phase"] == "held")["cuda_runtime"] = "wrong"
    cuda_run["stdout"] = "\n".join(json.dumps(row) for row in lines)
    issue = _native_stack(versions)
    assert issue is not None and "userspace version" in issue


def test_cgroup_native_positive_recomputes_dmem_and_rejects_neutralized_charge():
    from tools.verify_cgroup_plan import _native_report
    pair = [{"stack": name, "raw_run": _native_run(charge_dmem=True, version=version), "gsp": version, "driver_version": version,
             "kernel": "6.17.0-1032-nvidia", "module_capture": {module: f"version: {version}\nvermagic: 6.17.0-1032-nvidia SMP\n" for module in ("nvidia", "nvidia_uvm")},
             "cuda_runtime": "libcudart.so.615", "pytorch_version": "2.9.0", "boot_id": "boot-a",
             "gsp_capture": {"command": ["nvidia-smi", "-q"], "returncode": 0, "stdout": f"GSP Firmware Version : {version}"}}
            for name, version in (("580-baseline", "580.178.04"), ("615-candidate", "615.71.09"))]
    assert verify_native(_native_evidence(pair)) == []
    pair[1]["raw_run"] = _native_run(charge_dmem=False, version="615.71.09")
    report = _native_report(_native_evidence(pair))
    assert report["complete"] is True
    assert {row["classification"] for row in report["apis"]} == {"gap"}
    assert verify_native(_native_evidence(pair)) == []


def test_cgroup_nativo_complete_gap_is_pass_with_per_api_measurements(tmp_path):
    root = tmp_path / "native"
    pair = _native_pair()
    pair[1]["raw_run"] = _native_run(charge_dmem=False, version="615.71.09")
    put(root / "capture.json", {"schema": 1, "id": "FEATURE-1358-CGROUP-03-NATIVO",
        "phase": "03-nativo", "host": {"boot_id": "boot-a", "kernel": "6.17", "driver": "615"},
        **_native_evidence(pair)})
    outcome = verify_cgroup("03-nativo", root)
    assert _asserted_status(outcome) == "pass"
    assert outcome["evaluation"]["complete"] is True
    assert {row["classification"] for row in outcome["evaluation"]["apis"]} == {"gap"}


def test_cgroup_native_memory_only_accounting_is_containment_not_dmem_gap_patch_trigger():
    from tools.verify_cgroup_plan import _native_report
    pair = _native_pair()
    pair[1]["raw_run"] = _native_run(charge_dmem=False, version="615.71.09", charge_memory=True)
    assert verify_native(_native_evidence(pair)) == []
    api = next(row for row in _native_report(_native_evidence(pair))["apis"]
               if row["api"] == "cuda_malloc")
    assert api["classification"] == "contained"
    assert api["memory_accounted"] is True
    assert api["dmem_accounted"] is False
    assert api["unaccounted_bytes"] == 0


def test_cgroup_native_binds_phase02_owner_operation_classes_and_rollback_stack():
    import pytest
    from tools.verify_cgroup_plan import MissingEvidence
    pair = _native_pair()
    evidence = _native_evidence(pair)
    assert verify_native(evidence) == []
    bad = json.loads(json.dumps(evidence))
    bad["phase02_trace"]["id"] = "FEATURE-1358-CGROUP-04-PARCHE"
    assert "different task or phase" in verify_native(bad)[0]
    bad = json.loads(json.dumps(evidence))
    bad["phase02_trace"]["operation_rows"] = []
    with pytest.raises(MissingEvidence, match="allocation, residency and migration"):
        verify_native(bad)
    bad = json.loads(json.dumps(evidence))
    operation = bad["phase02_trace"]["operation_rows"][0]
    raw = json.loads(operation["raw_event"]); raw["owner_memcg"] = "other"
    operation["raw_event"] = json.dumps(raw, sort_keys=True)
    operation["raw_event_sha256"] = hashlib.sha256(operation["raw_event"].encode()).hexdigest()
    assert "does not match owner/stack" in verify_native(bad)[0]
    bad = json.loads(json.dumps(evidence))
    bad["rollback_compatibility"]["restore_plan_sha256"] = "wrong"
    assert "return plan" in verify_native(bad)[0]


def test_cgroup_phase02_dependencies_report_missing_and_adverse_capture_rows():
    import pytest
    from tools.verify_cgroup_plan import MissingEvidence
    pair = _native_pair()
    evidence = _native_evidence(pair)
    bad = json.loads(json.dumps(evidence)); bad.pop("phase02_trace")
    with pytest.raises(MissingEvidence, match="phase 02 owner"):
        verify_native(bad)
    bad = json.loads(json.dumps(evidence)); bad["phase02_trace"]["stack_identity"]["driver_version"] = "615.1"
    assert "exact captured 580" in verify_native(bad)[0]
    bad = json.loads(json.dumps(evidence)); bad["phase02_trace"]["allocations"] = None
    with pytest.raises(MissingEvidence, match="per-API owner"):
        verify_native(bad)
    bad = json.loads(json.dumps(evidence)); bad["phase02_trace"]["allocations"][0]["trace_rows"] = []
    bad["phase02_trace"]["allocations"][0]["window"] = {}
    with pytest.raises(MissingEvidence, match="empty trace lacks observed"):
        verify_native(bad)
    bad = json.loads(json.dumps(evidence)); bad["phase02_trace"]["operation_rows"] = None
    with pytest.raises(MissingEvidence, match="raw allocation/residency/migration"):
        verify_native(bad)
    bad = json.loads(json.dumps(evidence)); bad["phase02_trace"]["operation_rows"][0]["raw_event_sha256"] = "bad"
    with pytest.raises(MissingEvidence, match="hashed raw event"):
        verify_native(bad)
    bad = json.loads(json.dumps(evidence)); bad.pop("rollback_compatibility")
    with pytest.raises(MissingEvidence, match="restoration plan"):
        verify_native(bad)


def test_cgroup_native_reports_adverse_complete_control_as_gap_not_missing_or_clean():
    from tools.verify_cgroup_plan import _native_report
    pair = _native_pair()
    pair[1]["raw_run"] = _native_run(charge_dmem=False, version="615.71.09", charge_memory=True)
    controls = _native_controls()
    attempt = next(row for row in controls["limit_observations"] if row["api"] == "cuda_malloc" and row["domain"] == "memory")
    attempt.update(returncode=0, before=0, after=1_048_576, diagnostic="allocation returned successfully")
    sharing = controls["sharing_rows"][0]
    sharing["after_release"] = 4096
    assert verify_native(_native_evidence(pair, controls)) == []
    outcome = _native_report(_native_evidence(pair, controls))
    cuda = next(row for row in outcome["apis"] if row["api"] == "cuda_malloc")
    assert cuda["memory_accounted"] is True
    assert cuda["memory_limit_enforced"] is False
    assert cuda["enforcement_gap"] is True
    assert cuda["containment_result"] == "gap"


def test_cgroup_patch_decision_keeps_memory_accounted_but_unenforced_api_open():
    from tools.verify_cgroup_plan import _patch_report
    evidence = _patch_candidate_evidence()
    evidence["paired_runtime_evidence"][1]["raw_run"] = _native_run(
        charge_dmem=False, version="615.71.09", charge_memory=True)
    attempt = next(row for row in evidence["native_controls"]["limit_observations"]
                   if row["api"] == "cuda_malloc" and row["domain"] == "memory")
    attempt.update(returncode=0, before=0, after=1_048_576, diagnostic="allocation succeeded despite limit")
    evidence["native_controls"]["sharing_rows"][0]["after_release"] = 4096
    outcome = _patch_report(evidence)
    cuda = outcome["apis"]["cuda_malloc"]
    assert outcome["decision"] == "patch_required"
    assert cuda["memory_accounted"] is True
    assert cuda["memory_limit_enforced"] is False
    assert cuda["containment_result"] == "gap"
    assert outcome["controls"]["independent_cgroups"][0]["classification"] == "gap_or_leak"


def test_cgroup_phase04_cli_runs_complete_patch_selector_against_raw_bundle(tmp_path):
    evidence = _patch_candidate_evidence()
    root = tmp_path / "phase04"
    put(root / "capture.json", {"schema": 1, "id": "FEATURE-1358-CGROUP-04-PARCHE", "phase": "04-parche",
        "host": {"boot_id": "boot-a", "kernel": "6.17", "driver": "615"}, **evidence})
    outcome = verify_cgroup("04-parche", root)
    assert _asserted_status(outcome) == "pass"
    assert outcome["evaluation"]["decision"] == "patch_required"


def test_cgroup_patch_missing_post_build_capture_stays_unknown(tmp_path):
    root = tmp_path / "phase04"
    doc = {"schema": 1, "id": "FEATURE-1358-CGROUP-04-PARCHE", "phase": "04-parche",
           "host": {"boot_id": "boot-a", "kernel": "6.17", "driver": "615"},
           **_patch_candidate_evidence()}
    put(root / "capture.json", doc)
    baseline = verify_cgroup("04-parche", root)
    assert baseline["status"] == "pass" and baseline["could_not_run_count"] == 0
    doc.pop("candidate_after_stack")
    put(root / "capture.json", doc)
    negative = verify_cgroup("04-parche", root)
    assert negative["status"] == "unknown" and negative["could_not_run_count"] == 1
    assert "evaluation" not in negative


def test_cgroup_phase04_uses_legal_no_patch_decision_when_each_domain_contains(tmp_path):
    from tools.verify_cgroup_plan import _patch_report
    evidence = _patch_candidate_evidence()
    before = _native_run(charge_dmem=True, version="615.71.09")
    evidence["paired_runtime_evidence"][1]["raw_run"] = before
    rows = []
    for run in before["runs"]:
        samples = {row["phase"]: int(row["files"]["dmem.current"]["value"])
                   for row in (json.loads(line) for line in run["stdout"].splitlines())}
        baseline = "before" if run["api"] in ("none", "cpu_touch") else "before_allocation"
        rows.append({"api": run["api"], "samples": [
            {"phase": "before", "value": samples[baseline]},
            {"phase": "held", "value": samples["held"]},
            {"phase": "after_release", "value": samples["after_release"]}]})
    evidence["dmem_measurements"] = rows
    outcome = _patch_report(evidence)
    assert outcome["decision"] == "no_patch_needed"
    assert "after" not in outcome


def test_cgroup_patch_positive_requires_release_limit_and_two_cgroups():
    pair = [{"stack": name, "raw_run": _native_run(charge_dmem=True, version=version), "gsp": version, "driver_version": version,
             "kernel": "6.17.0-1032-nvidia", "module_capture": {module: f"version: {version}\nvermagic: 6.17.0-1032-nvidia SMP\n" for module in ("nvidia", "nvidia_uvm")},
             "cuda_runtime": "libcudart.so.615", "pytorch_version": "2.9.0", "boot_id": "boot-a",
             "gsp_capture": {"command": ["nvidia-smi", "-q"], "returncode": 0, "stdout": f"GSP Firmware Version : {version}"}}
            for name, version in (("580-baseline", "580.178.04"), ("615-candidate", "615.71.09"))]
    measurements = [{"api": api, "samples": [{"phase": phase, "value": 1_048_576 if phase == "held" and api not in ("none", "cpu_touch") else 0}
                                                for phase in ("before", "held", "after_release")]}
                    for api in APIS]
    controls = _native_controls()
    assert verify_patch({**_native_evidence(pair), "paired_runtime_evidence": pair,
                         "dmem_measurements": measurements, "native_controls": controls}) == []
    controls["sharing_rows"].pop()
    from tools.verify_cgroup_plan import MissingEvidence
    import pytest
    with pytest.raises(MissingEvidence):
        verify_patch({**_native_evidence(pair), "paired_runtime_evidence": pair,
                      "dmem_measurements": measurements, "native_controls": controls})


def _patch_candidate_evidence():
    pair = _native_pair()
    pair[1]["raw_run"] = _native_run(charge_dmem=False, version="615.71.09")
    measurements = [{"api": api, "samples": [{"phase": phase, "value": 0}
        for phase in ("before", "held", "after_release")]} for api in APIS]
    traces = []
    for index, api in enumerate(APIS):
        events = [] if api == "none" else [
            {"event": "charge", "timestamp_ns": 1, "pid": index + 1, "cgroup": api,
             "active_memcg": api, "flags": "__GFP_ACCOUNT", "bytes": 4096, "page": api, "stack": ["charge"]},
            {"event": "uncharge", "timestamp_ns": 2, "pid": index + 1, "cgroup": api,
             "active_memcg": api, "flags": "__GFP_ACCOUNT", "bytes": 4096, "page": api, "stack": ["free"]}]
        trace = {"case": api, "pid": index + 1, "cgroup": api, "events": events,
                 "trace_sha256": hashlib.sha256(json.dumps(events, sort_keys=True, separators=(",", ":")).encode()).hexdigest()}
        if not events:
            trace["window"] = {"pid": str(index + 1), "cgroup": api, "active_memcg": api,
                "start_ns": 0, "end_ns": 3, "probe_active": True,
                "heartbeat_rows": [{"timestamp_ns": 1, "pid": str(index + 1), "cgroup": api,
                                    "active_memcg": api, "probe_active": True}]}
        traces.append(trace)
    source = "static int charge_gpu_pages(struct page *page) { return memcg_charge(page); }\n"
    diff = "diff --git a/kernel/nvidia/page.c b/kernel/nvidia/page.c\n--- a/kernel/nvidia/page.c\n+++ b/kernel/nvidia/page.c\n@@ -1 +1 @@\n+" + source
    integrity = [
        {"case": "limit_rejection", "raw_output": json.dumps(_native_controls()["limit_observations"][0])},
        {"case": "error_unwind", "raw_output": json.dumps({"returncode": 1, "before": 4096, "after": 4096})},
        {"case": "sharing", "raw_output": json.dumps([
            {"cgroup": "a", "before": 0, "held": 4096, "after_release": 0},
            {"cgroup": "b", "before": 0, "held": 4096, "after_release": 0}])},
        {"case": "migration", "raw_output": json.dumps([
            {"page": "p1", "from_owner": "a", "to_owner": "b", "timestamp_ns": 1, "bytes": 4096, "charged_bytes": 4096, "freed_bytes": 4096},
            {"page": "p2", "from_owner": "b", "to_owner": "a", "timestamp_ns": 2, "bytes": 4096, "charged_bytes": 4096, "freed_bytes": 4096}])},
        {"case": "concurrent_release", "raw_output": json.dumps([
            {"event": "charge", "page": "p", "bytes": 4096},
            {"event": "uncharge", "page": "p", "bytes": 4096}])},
        {"case": "double_charge", "raw_output": json.dumps([
            {"event": "charge", "page": "p", "domain": "memory", "owner_memcg": "a", "bytes": 4096},
            {"event": "uncharge", "page": "p", "domain": "memory", "owner_memcg": "a", "bytes": 4096}])},
        {"case": "lost_charge", "raw_output": json.dumps([
            {"event": "charge", "page": "p", "domain": "dmem", "owner_memcg": "a", "bytes": 4096},
            {"event": "uncharge", "page": "p", "domain": "dmem", "owner_memcg": "a", "bytes": 4096}])},
        {"case": "teardown", "raw_output": json.dumps([
            {"cgroup": "a", "before": 0, "held": 4096, "after_release": 0},
            {"cgroup": "b", "before": 0, "held": 8192, "after_release": 0}])},
    ]
    after_stack = {**pair[1], "raw_run": _native_run(charge_dmem=True, version="615.71.09")}
    return {**_native_evidence(pair), "paired_runtime_evidence": pair, "candidate_after_stack": after_stack,
        "patch_diff": {"text": diff, "sha256": hashlib.sha256(diff.encode()).hexdigest()},
        "dmem_measurements": measurements,
        "native_controls": _native_controls(),
        "owner_trace": traces, "patch_source": {"text": source, "sha256": hashlib.sha256(source.encode()).hexdigest()},
        "build_log": {"command": ["make", "modules"], "returncode": 0,
                      "stdout": "CC [M] nvidia.ko\nCC [M] nvidia-uvm.ko\n"},
        "integrity_rows": integrity}


def test_cgroup_patch_residual_gap_requires_candidate_build_and_full_integrity():
    from tools.verify_cgroup_plan import _patch
    evidence = _patch_candidate_evidence()
    assert _patch(evidence) == []
    evidence["owner_trace"][1]["events"] = evidence["owner_trace"][1]["events"][:1]
    assert "invalid" in _patch(evidence)[0]
    evidence = _patch_candidate_evidence()
    evidence = _patch_candidate_evidence()
    assert "compiler/make error" in _patch({**evidence, "build_log": {
        "command": ["make", "modules"], "returncode": 0, "stdout": "make: *** failed\n"}})[0]
    evidence = _patch_candidate_evidence()
    evidence["owner_trace"][0]["events"] = [{"event": "charge", "timestamp_ns": 1, "pid": 1,
        "cgroup": "none", "active_memcg": "none", "flags": "accounted", "bytes": 4096,
        "page": "p", "stack": ["charge"]}]
    evidence["owner_trace"][0]["trace_sha256"] = hashlib.sha256(json.dumps(
        evidence["owner_trace"][0]["events"], sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    assert "no-allocation control" in _patch(evidence)[0]


def test_cgroup_patch_rejects_double_lost_migration_and_teardown_ledger_defects():
    from tools.verify_cgroup_plan import _patch
    evidence = _patch_candidate_evidence()
    rows = evidence["integrity_rows"]
    double = next(row for row in rows if row["case"] == "double_charge")
    events = json.loads(double["raw_output"])
    events.insert(1, dict(events[0]))
    double["raw_output"] = json.dumps(events)
    assert "double-charge" in _patch(evidence)[0]
    evidence = _patch_candidate_evidence()
    lost = next(row for row in evidence["integrity_rows"] if row["case"] == "lost_charge")
    lost["raw_output"] = json.dumps(json.loads(lost["raw_output"])[:1])
    assert "lost-charge" in _patch(evidence)[0]
    evidence = _patch_candidate_evidence()
    migration = next(row for row in evidence["integrity_rows"] if row["case"] == "migration")
    migration["raw_output"] = json.dumps([{**json.loads(migration["raw_output"])[0], "to_owner": "a"},
                                           json.loads(migration["raw_output"])[1]])
    assert "migration owner/charge" in _patch(evidence)[0]
    evidence = _patch_candidate_evidence()
    teardown = next(row for row in evidence["integrity_rows"] if row["case"] == "teardown")
    teardown["raw_output"] = json.dumps([{**json.loads(teardown["raw_output"])[0], "after_release": 4096},
                                          json.loads(teardown["raw_output"])[1]])
    assert "teardown" in _patch(evidence)[0]


def _legacy_summary_only_hang_runs():
    """The pre-2026-10-07 phase 05 fixture: a 10 ns window and a trusted ``{"ok":true}`` string."""
    apis = ("none", "cpu_touch", "cuda_malloc", "cuda_malloc_managed", "pytorch_empty")
    return [{"stack": stack, "started_ns": 10, "ended_ns": 20, "service_response": '{"ok":true}',
             "samples": [{"api": api, "requested_bytes": 4096, "monotonic_ns": 11 + index,
                          "memory_current": 10, "cgroup": stack} for index, api in enumerate(apis)],
             "journal": [{"monotonic_ns": 15, "message": "service ready"}]}
            for stack in ("baseline", "candidate")]


_HANG_TRIALS = (("none", 0, None, 0, ""), ("cpu_touch", 4096, None, 0, ""), ("cuda_malloc", 4096, None, 0, ""),
                ("cuda_malloc_managed", 4096, None, 0, ""), ("pytorch_empty", 4096, None, 0, ""),
                ("cuda_malloc", 4096, 1024, 1, "cudaMalloc: ENOMEM under dmem.max"))


def _hang_fixture_run(stack):
    boot = f"boot-{stack}"
    trials, samples = [], []
    for index, (api, requested, limit, returncode, diagnostic) in enumerate(_HANG_TRIALS):
        start = 1_000_000 * (index + 1)
        trials.append({"api": api, "requested_bytes": requested, "limit_bytes": limit, "cgroup": f"/{stack}/{index}",
                       "started_ns": start, "ended_ns": start + 900_000, "returncode": returncode,
                       "diagnostic": diagnostic})
        charged = 0 if limit is not None else requested
        for offset, value in ((100_000, 100), (500_000, 100 + charged), (800_000, 100)):
            samples.append({"api": api, "requested_bytes": requested, "cgroup": f"/{stack}/{index}",
                            "monotonic_ns": start + offset, "memory_current": value})
    return {"stack": stack, "boot_id": boot, "started_ns": 500_000, "ended_ns": 9_000_000,
            "started_utc": "2026-10-07T12:00:00+00:00", "ended_utc": "2026-10-07T12:00:10+00:00",
            "trials": trials, "samples": samples,
            "collection": [{"command": ["journalctl", "-o", "json", "--boot", boot], "returncode": 0},
                           {"command": ["python3", "-m", "tools.cgroup_repro", "--api", "all"], "returncode": 0}],
            "journal": [{"__REALTIME_TIMESTAMP": "1791374402000000", "__MONOTONIC_TIMESTAMP": "2000",
                         "_BOOT_ID": boot, "MESSAGE": "bounded trial started"}],
            "bb_samples": [{"ts": f"2026-10-07T12:00:0{second}+00:00", "boot_id": boot, "psi": {"mem_full": 0.0},
                            "servicio_ssh": {"estado": "OK"}} for second in (1, 5, 9)]}


def _hang_runs():
    return [_hang_fixture_run("baseline"), _hang_fixture_run("candidate")]


def _hang_capture(tmp_path, runs):
    root = tmp_path / "phase05"
    put(root / "capture.json", {"schema": 1, "id": "FEATURE-1358-CGROUP-05-CUELGUES", "phase": "05-cuelgues",
                                "host": {"boot_id": "boot-baseline", "kernel": "6.17", "driver": "580"},
                                "incidents": runs})
    return root


def _stack(result, name):
    return next(row for row in result["evaluation"]["stacks"] if row["stack"] == name)


def test_cgroup_hangs_legacy_summary_only_fixture_no_longer_passes():
    from tools.verify_cgroup_plan import MissingEvidence
    import pytest
    with pytest.raises(MissingEvidence, match="bb JSONL samples and trial rows"):
        verify_hangs({"incidents": _legacy_summary_only_hang_runs()})


def test_cgroup_hangs_positive_reports_counts_zeros_and_observed_window(tmp_path):
    result = verify_cgroup("05-cuelgues", _hang_capture(tmp_path, _hang_runs()))
    assert result["status"] == "pass" and result["could_not_run_count"] == 0 and result["fail"] == 0
    for name in ("baseline", "candidate"):
        stack = _stack(result, name)
        assert stack["outcome"] == "observed_window_without_hang"
        assert (stack["trials_planned"], stack["trials_executed"], stack["completed"], stack["controlled_rejection"],
                stack["accepted_over_limit"], stack["failed"], stack["not_executed"]) == (6, 6, 5, 1, 0, 0, 0)
        assert (stack["service_loss_events"], stack["watchdog_events"], stack["nvrm_events"], stack["oomd_actions"]) == (0, 0, 0, 0)
        assert stack["first_service_loss_utc"] is None and stack["last_useful_response_utc"].startswith("2026-10-07T12:00:09")
        assert stack["exposure_s"] == 0.0085
        assert stack["collection"][0] == {"command": ["journalctl", "-o", "json", "--boot", f"boot-{name}"], "returncode": 0}
        cpu = next(row for row in stack["trials"] if row["api"] == "cpu_touch")
        assert (cpu["charge_initial_bytes"], cpu["charge_peak_bytes"], cpu["charge_final_bytes"]) == (100, 4196, 100)


def test_cgroup_hangs_discriminates_service_loss_watchdog_and_reset_per_stack(tmp_path):
    runs = _hang_runs()
    runs[1]["bb_samples"][1]["servicio_ssh"] = {"estado": "TIMEOUT", "motivo": "ssh probe timed out"}
    result = verify_cgroup("05-cuelgues", _hang_capture(tmp_path, runs))
    assert result["status"] == "pass"
    assert _stack(result, "baseline")["outcome"] == "observed_window_without_hang"
    candidate = _stack(result, "candidate")
    assert candidate["outcome"] == "service_loss_observed" and candidate["service_loss_events"] == 1
    assert candidate["first_service_loss_utc"].startswith("2026-10-07T12:00:05")

    runs = _hang_runs()
    runs[1]["journal"].append({"__REALTIME_TIMESTAMP": "1791374404000000", "__MONOTONIC_TIMESTAMP": "4000",
                               "_BOOT_ID": "boot-candidate", "UNIT": "bb-usable.service",
                               "MESSAGE": "bb-usable.service: Watchdog timeout (limit 6min)!"})
    candidate = _stack(verify_cgroup("05-cuelgues", _hang_capture(tmp_path, runs)), "candidate")
    assert candidate["outcome"] == "service_loss_observed" and candidate["watchdog_events"] == 1

    runs = _hang_runs()
    runs[0]["journal"].append({"__REALTIME_TIMESTAMP": "1791374500000000", "__MONOTONIC_TIMESTAMP": "3",
                               "_BOOT_ID": "boot-after-reset", "MESSAGE": "Linux version 6.17.0"})
    baseline = _stack(verify_cgroup("05-cuelgues", _hang_capture(tmp_path, runs)), "baseline")
    assert baseline["outcome"] == "host_reset_observed"
    assert baseline["boots_observed"] == ["boot-after-reset", "boot-baseline"]


def test_cgroup_hangs_limit_trial_classes_are_measured_not_declared():
    from tools.verify_cgroup_plan import _hang_report
    runs = _hang_runs()
    runs[0]["trials"][5]["diagnostic"] = "Segmentation fault"
    runs[1]["trials"][5]["returncode"] = 0
    stacks = {row["stack"]: row for row in _hang_report({"incidents": runs})["stacks"]}
    assert (stacks["baseline"]["failed"], stacks["baseline"]["controlled_rejection"]) == (1, 0)
    assert (stacks["candidate"]["accepted_over_limit"], stacks["candidate"]["controlled_rejection"]) == (1, 0)
    runs = _hang_runs()
    leaked = next(row for row in runs[0]["samples"] if row["cgroup"] == "/baseline/5" and row["monotonic_ns"] == 6_800_000)
    leaked["memory_current"] = 200
    stacks = {row["stack"]: row for row in _hang_report({"incidents": runs})["stacks"]}
    assert stacks["baseline"]["failed"] == 1, "a rejection that leaves charge behind is not a controlled rejection"


def test_cgroup_hangs_neutralized_or_failed_healthy_controls_fail():
    runs = _hang_runs()
    for row in runs[0]["samples"]:
        if row["api"] == "cpu_touch":
            row["memory_current"] = 100
    assert "cpu_touch positive control" in verify_hangs({"incidents": runs})[0]
    runs = _hang_runs()
    runs[1]["trials"][0]["returncode"] = 1
    assert "healthy none/cpu_touch control" in verify_hangs({"incidents": runs})[0]


def test_cgroup_hangs_missing_controls_and_sources_stay_could_not_run(tmp_path):
    from tools.verify_cgroup_plan import MissingEvidence
    import pytest
    mutations = {
        "limit trial": lambda runs: [run["trials"].pop() for run in runs],
        "healthy controls": lambda runs: runs[0]["trials"][1].update(returncode=None),
        "journalctl JSON": lambda runs: runs[0].update(journal=[]),
        "boot_id ausente": lambda runs: runs[0]["journal"][0].pop("_BOOT_ID"),
        "servicio_ssh": lambda runs: [row.pop("servicio_ssh") for row in runs[1]["bb_samples"]],
        "PSI": lambda runs: [row.pop("psi") for row in runs[1]["bb_samples"]],
        "no memory.current samples": lambda runs: runs[0].update(
            samples=[row for row in runs[0]["samples"] if row["api"] != "pytorch_empty"]),
        "run boot": lambda runs: runs[0].update(boot_id="another-boot"),
        "boot identity absent": lambda runs: runs[1].update(boot_id=""),
        "literal collection commands": lambda runs: runs[0].pop("collection"),
        "journalctl -o json collection": lambda runs: runs[0]["collection"].pop(0),
        "collection failed: python3 -m tools.cgroup_repro": lambda runs: runs[1]["collection"][1].update(returncode=1),
    }
    for expected, mutate in mutations.items():
        runs = _hang_runs()
        mutate(runs)
        with pytest.raises(MissingEvidence, match=expected):
            verify_hangs({"incidents": runs})
        result = verify_cgroup("05-cuelgues", _hang_capture(tmp_path, runs))
        assert (result["status"], result["could_not_run_count"], result["fail"]) == ("unknown", 1, 0), expected


def test_cgroup_hang_capture_boundaries_and_api_size_discrimination(tmp_path, capsys):
    from tools.verify_cgroup_plan import main
    runs = _hang_runs()
    assert verify_hangs({"incidents": runs}) == []
    assert "baseline and candidate runs" in verify_hangs(
        {"incidents": [{**runs[0], "stack": "candidate"}, runs[1]]})[0]
    assert "baseline and candidate runs" in verify_hangs({"incidents": [*runs, runs[1]]})[0]
    failures = {
        "same API/size/limit": lambda data: data[1]["trials"][5].update(limit_bytes=2048),
        "each stack needs": lambda data: [row.update(api="other") for run in data
                                          for row in (run["trials"][4], *run["samples"]) if row["api"] == "pytorch_empty"],
        "journal records fall outside": lambda data: data[0]["journal"][0].update(__MONOTONIC_TIMESTAMP="9001"),
        "bb samples fall outside": lambda data: data[0]["bb_samples"][0].update(ts="2026-10-07T11:59:59+00:00"),
        "timestamps are not increasing": lambda data: data[0]["samples"][1].update(monotonic_ns=1_100_000),
        "memory.current samples fall outside": lambda data: data[0]["samples"][0].update(monotonic_ns=1),
        "exposure interval": lambda data: data[0].update(started_ns=data[0]["ended_ns"]),
        "UTC exposure": lambda data: data[0].update(started_utc=data[0]["ended_utc"]),
        "trial falls outside": lambda data: data[0]["trials"][5].update(ended_ns=9_500_000),
    }
    for expected, mutate in failures.items():
        data = _hang_runs()
        mutate(data)
        issues = verify_hangs({"incidents": data})
        assert issues and expected in issues[0], (expected, issues)
    data = _hang_runs()
    data[0]["started_utc"] = "2026-10-07T12:00:00"
    root = _hang_capture(tmp_path, data)
    assert _asserted_status(verify_cgroup("05-cuelgues", root)) == "unknown"
    assert main(["--phase", "05-cuelgues", "--evidence", str(_hang_capture(tmp_path, _hang_runs()))]) == 0
    out = json.loads(capsys.readouterr().out)
    assert (out["could_not_run_count"], out["fail"]) == (0, 0)
    data = _hang_runs()
    data[1]["trials"][5]["limit_bytes"] = 2048
    assert main(["--phase", "05-cuelgues", "--evidence", str(_hang_capture(tmp_path, data))]) == 1
    capsys.readouterr()
    data = _hang_runs()
    data[1]["bb_samples"] = []
    assert main(["--phase", "05-cuelgues", "--evidence", str(_hang_capture(tmp_path, data))]) == 2




def test_cgroup_patch_raw_helpers_reject_forged_controls():
    from tools.verify_cgroup_plan import (_concurrent_balanced, _migration_balanced, _raw_limit_test,
        _raw_unwind_test, _sharing_correct)
    assert _raw_limit_test('{"returncode": 1, "requested_bytes": 10, "limit_bytes": 5, "before": 0, "after": 0, "diagnostic": "memory.max resource limit"}')
    assert not _raw_limit_test('{"returncode": 1, "requested_bytes": 10, "limit_bytes": 5, "before": 0, "after": 0, "diagnostic": "generic worker error"}')
    assert not _raw_limit_test('{"returncode": 0, "requested_bytes": 10, "limit_bytes": 5, "before": 0, "after": 0, "diagnostic": "memory.max resource limit"}')
    assert _raw_unwind_test('{"returncode": 1, "before": 4096, "after": 4096}')
    assert not _raw_unwind_test('{"returncode": 1, "before": 4096, "after": 0}')
    assert _sharing_correct([{"cgroup": "a", "before": 0, "held": 4096, "after_release": 0},
                             {"cgroup": "b", "before": 0, "held": 4096, "after_release": 0}])
    assert not _sharing_correct([{"cgroup": "a", "before": 0, "held": 4096, "after_release": 0}])
    migration = [{"page": "p1", "from_owner": "a", "to_owner": "b", "timestamp_ns": 1,
                  "bytes": 4096, "charged_bytes": 4096, "freed_bytes": 4096},
                 {"page": "p2", "from_owner": "b", "to_owner": "a", "timestamp_ns": 2,
                  "bytes": 4096, "charged_bytes": 4096, "freed_bytes": 4096}]
    assert _migration_balanced(json.dumps(migration))
    assert not _migration_balanced(json.dumps([migration[0], {**migration[1], "freed_bytes": 0}]))
    assert _concurrent_balanced(json.dumps([{"event": "charge", "page": "p", "bytes": 4096},
                                            {"event": "uncharge", "page": "p", "bytes": 4096}]))


def test_memory_saver_rejects_neutralized_cpu_control(tmp_path):
    root = tmp_path / "evidence"
    put(root / "capture.json", {"schema": 1, "id": "FEATURE-MEMORYSAVER-02-TRAZADOR", "phase": "02-trazador",
                                  "cases": [_memory_case(name, charges) for name, charges in (("cpu_touch", 0), ("none", 0), ("cuda_bounded", 1))]})
    assert _asserted_status(verify_memory("02-trazador", root)) == "fail"


def _memory_case(name, charges):
    abi_text = "raw btf ABI v1"
    symbols = "0000 T __memcg_kmem_charge_page\n0001 T __memcg_kmem_uncharge_page\n"
    events = ([{"kind": "charge", "page": "a", "bytes": 4096, "timestamp_ns": 1, "boot_id": "b",
                "pid": 3, "cgroup": "cg", "owner_memcg": "cg", "flags": "__GFP_ACCOUNT", "stack": ["charge", "allocation"]},
               {"kind": "uncharge", "page": "a", "bytes": 4096, "timestamp_ns": 2, "boot_id": "b",
                "pid": 3, "cgroup": "cg", "owner_memcg": "cg", "flags": "__GFP_ACCOUNT", "stack": ["uncharge", "release"]}] if charges else
              [{"kind": "failure", "page": "", "bytes": 0, "timestamp_ns": 1, "boot_id": "b",
                "pid": 3, "cgroup": "cg", "owner_memcg": "cg", "flags": "none", "stack": ["allocation-attempt"]}])
    case = {"case": name, "boot_id": "b", "pid": 3, "cgroup": "cg", "start_ns": 0, "end_ns": 3,
            "lost_events": 0, "kernel_release": "6.17", "abi_sha256": "a" * 64,
            "events": events, "symbol_rows": ["__memcg_kmem_charge_page", "__memcg_kmem_uncharge_page"],
            "kernel_capture": {"command": ["uname", "-r"], "returncode": 0, "stdout": "6.17\n"},
            "abi_capture": {"command": ["bpftool", "btf", "dump", "file", "/sys/kernel/btf/vmlinux", "format", "raw"],
                            "returncode": 0, "stdout": abi_text},
            "symbol_capture": {"command": ["grep", "-E", "__memcg_kmem_charge_page|__memcg_kmem_uncharge_page", "/proc/kallsyms"],
                               "returncode": 0, "stdout": symbols}}
    case["abi_sha256"] = hashlib.sha256(abi_text.encode()).hexdigest()
    if name == "none":
        case["window"] = {"heartbeat_rows": [
            {"timestamp_ns": 1, "boot_id": "b", "pid": 3, "cgroup": "cg", "active": True},
            {"timestamp_ns": 2, "boot_id": "b", "pid": 3, "cgroup": "cg", "active": True}],
            "control_cpu_events": [{"kind": "charge", "boot_id": "b", "pid": 3, "cgroup": "cg"}]}
    return case


def test_memory_saver_computes_pass_from_balanced_raw_events(tmp_path):
    root = tmp_path / "evidence"
    put(root / "capture.json", {"schema": 1, "id": "FEATURE-MEMORYSAVER-02-TRAZADOR", "phase": "02-trazador",
                                  "cases": [_memory_case(name, charges) for name, charges in (("cpu_touch", 1), ("none", 0), ("cuda_bounded", 1))]})
    assert _asserted_status(verify_memory("02-trazador", root)) == "pass"


def test_memory_saver_missing_artifact_is_unknown(tmp_path):
    assert _asserted_status(verify_memory("04-packing-4k", tmp_path)) == "unknown"


def test_memory_saver_rejects_duplicate_unmatched_and_unknown_owner_events(tmp_path):
    root = tmp_path / "evidence"
    cases = [_memory_case(name, charges) for name, charges in
             (("cpu_touch", 1), ("none", 0), ("cuda_bounded", 1))]
    events = cases[0]["events"]
    events.insert(1, json.loads(json.dumps(events[0])))
    put(root / "capture.json", {"schema": 1, "id": "FEATURE-MEMORYSAVER-02-TRAZADOR",
                                  "phase": "02-trazador", "cases": cases})
    assert _asserted_status(verify_memory("02-trazador", root)) == "fail"
    cases[0]["events"] = [cases[0]["events"][0], {**cases[0]["events"][-1], "page": "wrong"}]
    put(root / "capture.json", {"schema": 1, "id": "FEATURE-MEMORYSAVER-02-TRAZADOR",
                                  "phase": "02-trazador", "cases": cases})
    assert _asserted_status(verify_memory("02-trazador", root)) == "fail"
    cases[0] = _memory_case("cpu_touch", 1)
    cases[0]["events"][0]["owner_memcg"] = "unknown"
    put(root / "capture.json", {"schema": 1, "id": "FEATURE-MEMORYSAVER-02-TRAZADOR",
                                  "phase": "02-trazador", "cases": cases})
    assert _asserted_status(verify_memory("02-trazador", root)) == "unknown"


def test_memory_saver_packing_recomputes_source_hash_and_page_size(tmp_path):
    root = tmp_path / "packing"
    source_text = "pinned HAL source dma_align"
    source_hash = hashlib.sha256(source_text.encode()).hexdigest()
    stock = {"page_size": 4096, "backing_bytes": 4096, "requested_bytes": 4096,
        "allocation_id": "stock-a", "api": "cuda", "offset_bytes": 0, "dma_alignment_bytes": 4096,
        "source_path": "hal.c", "source_sha256": source_hash, "map_operation": "map", "unmap_operation": "unmap",
        "tracker_before": 100, "tracker_after": 100, "allocator": "stock", "run_id": "stock", "logical_allocation_id": "logical-a",
        "corpus_sha256": "a" * 64, "protocol_sha256": "b" * 64, "stack_sha256": "c" * 64, "exposure": "same bounded workload",
        "gpu_base_address": 4096, "cacheline_bytes": 64, "cpu_mapping_offset_bytes": 64,
        "descriptor_bytes": 0, "owner_memcg": "gpu-owner", "memory_current_before": 1000,
        "memory_current_held": 5096, "memory_current_after": 1000}
    packed = {**stock, "allocation_id": "packed-a", "allocator": "packed", "run_id": "packed"}
    doc = {"schema": 1, "id": "FEATURE-MEMORYSAVER-04-PACKING-4K", "phase": "04-packing-4k",
           "comparison": {"corpus_sha256": "a" * 64, "protocol_sha256": "b" * 64, "stack_sha256": "c" * 64, "exposure": "same bounded workload"},
           "allocations": [stock, packed],
           "source_texts": [{"path": "hal.c", "version": "pinned", "text": source_text, "sha256": source_hash}],
           "alignment_requirements": [{"api": "cuda", "alignment_bytes": 4096,
               "source_path": "hal.c", "source_symbol": "dma_align"}],
           "sharing_rows": [{"allocation_id": alloc["allocation_id"], "owner_before": "gpu-owner",
               "owner_after": "gpu-owner", "charge_before": 5096, "charge_after": 5096} for alloc in (stock, packed)],
           "migration_rows": [{"allocation_id": alloc["allocation_id"], "charge_total_before": 8192,
               "charge_total_after": 8192, "source_charge_before": 4096, "source_charge_after": 4096,
               "destination_charge_before": 0, "destination_charge_after": 0,
               "expected_owner_after": "gpu-owner", "observed_owner_after": "gpu-owner"} for alloc in (stock, packed)],
           }
    put(root / "capture.json", doc)
    assert _asserted_status(verify_memory("04-packing-4k", root)) == "pass"
    doc["allocations"][0]["page_size"] = 65536
    put(root / "capture.json", doc)
    assert _asserted_status(verify_memory("04-packing-4k", root)) == "unknown"
    doc["allocations"][0]["page_size"] = 2048
    put(root / "capture.json", doc)
    assert _asserted_status(verify_memory("04-packing-4k", root)) == "fail"


def test_memory_saver_packing_rejects_unbound_allocation_and_boolean_alignment(tmp_path):
    root = tmp_path / "packing-trap"
    source = "arbitrary unbound text"
    put(root / "capture.json", {"schema": 1, "id": "FEATURE-MEMORYSAVER-04-PACKING-4K",
        "phase": "04-packing-4k",
        "allocations": [{"allocation_id": "unbound", "page_size": 4096, "backing_bytes": 0}],
        "source_texts": [{"text": source, "sha256": hashlib.sha256(source.encode()).hexdigest()}],
        "alignment_requirements": True})
    result = verify_memory("04-packing-4k", root)
    assert _asserted_status(result) == "unknown" and result["could_not_run_count"] == 1


def test_memory_saver_raw_runtime_and_packing_branch_edges(tmp_path):
    from tools.verify_memory_saver import _packing, _trace
    cases = [_memory_case(name, charges) for name, charges in (("cpu_touch", 1), ("none", 0), ("cuda_bounded", 1))]
    assert _asserted_status(_trace({"cases": cases})) == "pass"
    for key, value in (("pid", True), ("lost_events", 1), ("abi_sha256", "short"), ("kernel_release", "")):
        bad = json.loads(json.dumps(cases)); bad[0][key] = value
        assert _asserted_status(_trace({"cases": bad})) == "unknown"
    bad = json.loads(json.dumps(cases)); bad[2]["events"][1]["boot_id"] = "other"
    assert "invalid typed" in _trace({"cases": bad})["findings"][0]
    bad = json.loads(json.dumps(cases)); bad[2]["events"][0]["flags"] = ""
    assert "invalid typed" in _trace({"cases": bad})["findings"][0]
    bad = json.loads(json.dumps(cases)); bad[2]["events"][1]["bytes"] = True
    assert "invalid typed" in _trace({"cases": bad})["findings"][0]
    assert _asserted_status(_trace({"cases": [{**cases[0], "symbol_rows": None}, *cases[1:]]})) == "unknown"
    bad = json.loads(json.dumps(cases)); bad[2]["events"].pop()
    assert _asserted_status(_trace({"cases": bad})) == "fail"
    bad = json.loads(json.dumps(cases)); bad[2]["events"][0]["kind"] = "unexpected"
    assert "unknown event kind" in _trace({"cases": bad})["findings"][0]
    bad = json.loads(json.dumps(cases)); bad[2]["events"][0]["kind"] = "failure"; bad[2]["events"][0]["bytes"] = 1
    assert "failure event carries" in _trace({"cases": bad})["findings"][0]


def test_memory_saver_requires_live_probe_heartbeat_and_current_abi():
    from tools.verify_memory_saver import _trace
    cases = [_memory_case(name, charges) for name, charges in (("cpu_touch", 1), ("none", 0), ("cuda_bounded", 1))]
    del cases[1]["window"]
    assert _asserted_status(_trace({"cases": cases})) == "unknown"
    cases = [_memory_case(name, charges) for name, charges in (("cpu_touch", 1), ("none", 0), ("cuda_bounded", 1))]
    cases[1]["window"]["heartbeat_rows"][1]["active"] = False
    assert _asserted_status(_trace({"cases": cases})) == "fail"
    cases = [_memory_case(name, charges) for name, charges in (("cpu_touch", 1), ("none", 0), ("cuda_bounded", 1))]
    cases[0]["abi_capture"]["stdout"] = "different ABI bytes"
    assert _asserted_status(_trace({"cases": cases})) == "unknown"
    cases = [_memory_case(name, charges) for name, charges in (("cpu_touch", 1), ("none", 0), ("cuda_bounded", 1))]
    cases[2]["symbol_capture"]["stdout"] = "only uncharge symbol"
    assert _asserted_status(_trace({"cases": cases})) == "unknown"
    cases = [_memory_case(name, charges) for name, charges in (("cpu_touch", 1), ("none", 0), ("cuda_bounded", 1))]
    cases[0]["kernel_capture"]["returncode"] = 1
    assert _asserted_status(_trace({"cases": cases})) == "unknown"
    cases = [_memory_case(name, charges) for name, charges in (("cpu_touch", 1), ("none", 0), ("cuda_bounded", 1))]
    cases[1]["window"]["heartbeat_rows"][0]["timestamp_ns"] = "bad"
    assert _asserted_status(_trace({"cases": cases})) == "unknown"
    cases = [_memory_case(name, charges) for name, charges in (("cpu_touch", 1), ("none", 0), ("cuda_bounded", 1))]
    cases[1]["window"]["heartbeat_rows"][1]["timestamp_ns"] = 1
    assert _asserted_status(_trace({"cases": cases})) == "unknown"
    cases = [_memory_case(name, charges) for name, charges in (("cpu_touch", 1), ("none", 0), ("cuda_bounded", 1))]
    cases[1]["window"]["control_cpu_events"] = []
    assert _asserted_status(_trace({"cases": cases})) == "unknown"


def test_memory_saver_negative_control_is_honest_unique_and_windowed():
    """DEBT-CLOSE-CHECK-VERIFY-MEMORY-SAVER-01: the no-allocation control must discriminate."""
    from tools.verify_memory_saver import _trace

    def fresh():
        return [_memory_case(name, charges) for name, charges in (("cpu_touch", 1), ("none", 0), ("cuda_bounded", 1))]

    # An honest no-allocation capture records zero events; with live heartbeats it passes.
    cases = fresh()
    cases[1]["events"] = []
    assert _asserted_status(_trace({"cases": cases})) == "pass"
    # Positive cases with zero events stay a failed positive control.
    cases = fresh()
    cases[0]["events"] = []
    assert _asserted_status(_trace({"cases": cases})) == "fail"
    # A duplicate case must not mask a leaking positive or a charged negative.
    cases = fresh()
    leaking = json.loads(json.dumps(cases[0]))
    leaking["events"].pop()
    result = _trace({"cases": [leaking, *cases]})
    assert _asserted_status(result) == "unknown" and result["could_not_run_count"] == 1
    cases = fresh()
    charged_none = {**json.loads(json.dumps(cases[0])), "case": "none", "window": cases[1]["window"]}
    assert _asserted_status(_trace({"cases": [charged_none, *cases]})) == "unknown"
    # Heartbeats outside the no-allocation window do not prove the probe was live in it.
    cases = fresh()
    for offset, row in enumerate(cases[1]["window"]["heartbeat_rows"]):
        row["timestamp_ns"] = 1000 + offset
    result = _trace({"cases": cases})
    assert _asserted_status(result) == "unknown" and "outside" in result["findings"][0]


def test_memory_saver_packing_cost_alignment_and_candidate_branches():
    from tools.verify_memory_saver import _packing

    text = "pinned source align"
    digest = hashlib.sha256(text.encode()).hexdigest()
    row = {"allocation_id": "a", "api": "cuda", "requested_bytes": 4096, "page_size": 4096,
           "backing_bytes": 4096, "offset_bytes": 0, "dma_alignment_bytes": 4096,
           "source_path": "hal.c", "source_sha256": digest, "map_operation": "map", "unmap_operation": "unmap",
           "tracker_before": 10, "tracker_after": 10, "allocator": "stock", "run_id": "stock", "logical_allocation_id": "logical-a",
           "corpus_sha256": "a" * 64, "protocol_sha256": "b" * 64, "stack_sha256": "c" * 64, "exposure": "same bounded workload",
           "gpu_base_address": 4096, "cacheline_bytes": 64, "cpu_mapping_offset_bytes": 64,
           "descriptor_bytes": 0, "owner_memcg": "gpu-owner", "memory_current_before": 1000,
           "memory_current_held": 5096, "memory_current_after": 1000}
    packed_row = {**row, "allocation_id": "b", "allocator": "packed", "run_id": "packed"}
    doc = {"comparison": {"corpus_sha256": "a" * 64, "protocol_sha256": "b" * 64, "stack_sha256": "c" * 64, "exposure": "same bounded workload"},
           "allocations": [row, packed_row], "source_texts": [{"path": "hal.c", "version": "v", "text": text, "sha256": digest}],
           "alignment_requirements": [{"api": "cuda", "alignment_bytes": 4096, "source_path": "hal.c", "source_symbol": "align"}],
           "sharing_rows": [{"allocation_id": allocation["allocation_id"], "owner_before": "gpu-owner", "owner_after": "gpu-owner",
               "charge_before": 5096, "charge_after": 5096} for allocation in (row, packed_row)],
           "migration_rows": [{"allocation_id": allocation["allocation_id"], "charge_total_before": 8192,
               "charge_total_after": 8192, "source_charge_before": 4096, "source_charge_after": 4096,
               "destination_charge_before": 0, "destination_charge_after": 0,
               "expected_owner_after": "gpu-owner", "observed_owner_after": "gpu-owner"} for allocation in (row, packed_row)],
           }
    assert _asserted_status(_packing(doc)) == "pass"
    assert _asserted_status(_packing({**doc, "allocations": [None]})) == "unknown"
    assert _asserted_status(_packing({**doc, "allocations": [{**row, "page_size": True}, packed_row]})) == "fail"
    assert _asserted_status(_packing({**doc, "allocations": [{**row, "source_sha256": "f" * 64}, packed_row]})) == "fail"
    assert _asserted_status(_packing({**doc, "source_texts": [{**doc["source_texts"][0], "sha256": "wrong"}]})) == "unknown"
    assert _asserted_status(_packing({**doc, "alignment_requirements": [{**doc["alignment_requirements"][0], "source_symbol": "missing"}]})) == "unknown"
    assert _asserted_status(_packing({**doc, "alignment_requirements": [*doc["alignment_requirements"], doc["alignment_requirements"][0]]})) == "unknown"
    assert _asserted_status(_packing({**doc, "allocations": [{**row, "offset_bytes": 1}, packed_row]})) == "fail"
    assert _asserted_status(_packing({**doc, "allocations": [{**row, "tracker_after": 11}, packed_row]})) == "fail"
    assert _asserted_status(_packing({**doc, "allocations": [{**row, "backing_bytes": 1}, packed_row]})) == "fail"
    assert _asserted_status(_packing({**doc, "allocations": [row, dict(row)]})) == "fail"
    assert _asserted_status(_packing({**doc, "allocations": [{**row, "page_size": 65536}, packed_row]})) == "unknown"
    assert _asserted_status(_packing({**doc, "allocations": [row]})) == "unknown"
    assert _asserted_status(_packing({**doc, "allocations": [{**row, "backing_bytes": 8192}, packed_row]})) == "unknown"
    candidate_doc = json.loads(json.dumps(doc))
    candidate_doc["allocations"][0]["backing_bytes"] = 8192
    candidate_doc["allocations"][0]["memory_current_held"] = 9192
    candidate_doc["candidate"] = _memory_packing_candidate()
    assert _asserted_status(_packing(candidate_doc)) == "pass"
    bad_candidate = json.loads(json.dumps(candidate_doc)); bad_candidate["candidate"]["integrity_rows"][0]["events"].pop()
    assert _asserted_status(_packing(bad_candidate)) == "fail"
    bad_candidate = json.loads(json.dumps(candidate_doc)); bad_candidate["candidate"]["build"]["returncode"] = 2
    assert _asserted_status(_packing(bad_candidate)) == "fail"
    bad_measure = json.loads(json.dumps(doc)); bad_measure["allocations"][0]["cpu_mapping_offset_bytes"] = 1
    assert _asserted_status(_packing(bad_measure)) == "fail"
    bad_measure = json.loads(json.dumps(doc)); bad_measure["allocations"][0]["gpu_base_address"] = 1
    assert _asserted_status(_packing(bad_measure)) == "fail"
    bad_share = json.loads(json.dumps(doc)); bad_share["sharing_rows"][0]["charge_after"] += 4096
    assert _asserted_status(_packing(bad_share)) == "fail"
    bad_migration = json.loads(json.dumps(doc)); bad_migration["migration_rows"][0]["charge_total_after"] += 4096
    assert _asserted_status(_packing(bad_migration)) == "fail"


def test_memory_saver_sharing_migration_and_cost_unknown_branches():
    from tools.verify_memory_saver import _migration_issue, _packing_cost_decision, _sharing_issue
    rows = [{"allocation_id": "a", "api": "cuda", "allocator": "stock", "page_size": 4096,
             "backing_bytes": 4096, "descriptor_bytes": 0, "owner_memcg": "owner"},
            {"allocation_id": "b", "api": "cuda", "allocator": "packed", "page_size": 4096,
             "backing_bytes": 4096, "descriptor_bytes": 0, "owner_memcg": "owner"}]
    share = [{"allocation_id": "a", "owner_before": "owner", "owner_after": "owner", "charge_before": 4, "charge_after": 4},
             {"allocation_id": "b", "owner_before": "owner", "owner_after": "owner", "charge_before": 4, "charge_after": 4}]
    migration = [{"allocation_id": name, "charge_total_before": 4, "charge_total_after": 4,
        "source_charge_before": 4, "source_charge_after": 4, "destination_charge_before": 0,
        "destination_charge_after": 0, "expected_owner_after": "owner", "observed_owner_after": "owner"} for name in ("a", "b")]
    assert _asserted_status(_sharing_issue(None, rows)) == "unknown"
    assert _asserted_status(_sharing_issue([{**share[0], "owner_after": "other"}, share[1]], rows)) == "unknown"
    assert _asserted_status(_sharing_issue([{**share[0], "charge_before": True}, share[1]], rows)) == "unknown"
    assert _asserted_status(_sharing_issue([share[0]], rows)) == "unknown"
    assert _asserted_status(_migration_issue(None, rows)) == "unknown"
    assert _asserted_status(_migration_issue([{"allocation_id": "a"}], rows)) == "unknown"
    assert _asserted_status(_migration_issue([{**migration[0], "charge_total_after": 5}, migration[1]], rows)) == "fail"
    assert _asserted_status(_migration_issue([{**migration[0], "observed_owner_after": "other"}, migration[1]], rows)) == "fail"
    assert _asserted_status(_migration_issue([migration[0]], rows)) == "unknown"
    assert _asserted_status(_packing_cost_decision([rows[0]], {})) == "unknown"


def test_memory_saver_packing_requires_same_logical_workload():
    from tools.verify_memory_saver import _packing

    text = "pinned HAL source align"
    digest = hashlib.sha256(text.encode()).hexdigest()
    stock = {"allocation_id": "stock", "logical_allocation_id": "logical-1", "api": "cuda",
        "requested_bytes": 4096, "page_size": 4096, "backing_bytes": 4096, "offset_bytes": 0,
        "dma_alignment_bytes": 4096, "source_path": "hal.c", "source_sha256": digest,
        "map_operation": "map", "unmap_operation": "unmap", "tracker_before": 1, "tracker_after": 1,
        "allocator": "stock", "run_id": "same-corpus", "gpu_base_address": 4096, "cacheline_bytes": 64,
        "corpus_sha256": "a" * 64, "protocol_sha256": "b" * 64, "stack_sha256": "c" * 64, "exposure": "same bounded workload",
        "cpu_mapping_offset_bytes": 64, "descriptor_bytes": 0, "owner_memcg": "gpu-owner",
        "memory_current_before": 1000, "memory_current_held": 5096, "memory_current_after": 1000}
    packed = {**stock, "allocation_id": "packed", "allocator": "packed", "run_id": "same-corpus"}
    doc = {"allocations": [stock, packed], "comparison": {"corpus_sha256": "a" * 64,
        "protocol_sha256": "b" * 64, "stack_sha256": "c" * 64, "exposure": "same bounded workload"},
        "source_texts": [{"path": "hal.c", "version": "pinned", "text": text, "sha256": digest}],
        "alignment_requirements": [{"api": "cuda", "alignment_bytes": 4096,
            "source_path": "hal.c", "source_symbol": "align"}],
        "sharing_rows": [{"allocation_id": x, "owner_before": "gpu-owner", "owner_after": "gpu-owner",
            "charge_before": 5096, "charge_after": 5096} for x in ("stock", "packed")],
        "migration_rows": [{"allocation_id": x, "charge_total_before": 8192, "charge_total_after": 8192,
            "source_charge_before": 4096, "source_charge_after": 4096, "destination_charge_before": 0,
            "destination_charge_after": 0, "expected_owner_after": "gpu-owner", "observed_owner_after": "gpu-owner"}
            for x in ("stock", "packed")]}
    assert _asserted_status(_packing(doc)) == "pass"
    changed = json.loads(json.dumps(doc))
    changed["allocations"][1]["requested_bytes"] = 5000
    changed["allocations"][1]["backing_bytes"] = 8192
    changed["allocations"][1]["memory_current_held"] = 9192
    # Same total cost cannot compensate for a changed workload request.
    assert _asserted_status(_packing(changed)) == "unknown"
    changed = json.loads(json.dumps(doc))
    changed["allocations"][1]["stack_sha256"] = "d" * 64
    assert _asserted_status(_packing(changed)) == "unknown"
    from tools.verify_memory_saver import _packing_cost_decision
    req = {"cuda": {"alignment_bytes": 4096, "source_symbol": "align"}}
    assert _asserted_status(_packing_cost_decision([stock, packed, dict(packed)], {**doc, "_requirements": req})) == "unknown"
    assert _asserted_status(_packing_cost_decision([stock], {**doc, "_requirements": req})) == "unknown"
    stock_two = {**stock, "allocation_id": "stock-two", "logical_allocation_id": "logical-2", "backing_bytes": 8192}
    packed_two = {**packed, "allocation_id": "packed-two", "logical_allocation_id": "logical-2", "backing_bytes": 4096}
    packed_one_larger = {**packed, "backing_bytes": 8192}
    paired_costs = _packing_cost_decision([stock, packed_one_larger, stock_two, packed_two], doc)
    assert _asserted_status(paired_costs) == "pass", paired_costs  # equal per-API total means no net measured saving


def test_memory_saver_candidate_build_stack_and_phase03_adversarial_branches():
    from tools.verify_memory_saver import _packing_candidate_issue
    candidate = _memory_packing_candidate()
    assert _asserted_status(_packing_candidate_issue(candidate)) == "pass"
    assert _asserted_status(_packing_candidate_issue(None)) == "unknown"
    for mutation, status in (
        (lambda d: d.update(diff=None), "unknown"),
        (lambda d: d["diff"].update(patch_text="tampered"), "fail"),
        (lambda d: d.update(build=None), "unknown"),
        (lambda d: d["build"].update(artifact_sha256="wrong"), "unknown"),
        (lambda d: d.update(phase03=None), "unknown"),
        (lambda d: d["phase03"]["after"].update(kernel="different"), "fail"),
        (lambda d: d["phase03"]["after"]["modules"]["nvidia"].update(sha256="different"), "fail"),
        (lambda d: d["phase03"]["after"]["modules"]["nvidia_uvm"].update(sha256="wrong"), "unknown"),
        (lambda d: d.update(integrity_rows=[]), "unknown"),
        (lambda d: d["integrity_rows"][0].update(events=[]), "unknown"),
        (lambda d: d["integrity_rows"][0].update(events=[{"bytes": True}]), "unknown"),
        (lambda d: d["integrity_rows"][0]["events"].insert(1, dict(d["integrity_rows"][0]["events"][0])), "fail"),
        (lambda d: d["integrity_rows"][0].update(events=[{"kind": "uncharge", "page": "lost", "bytes": 1,
            "timestamp_ns": 1, "pid": 1, "cgroup": "a", "owner_memcg": "a", "boot_id": "b"}]), "fail"),
        (lambda d: d["integrity_rows"][0]["events"][0].update(timestamp_ns=2), "fail"),
        (lambda d: d["integrity_rows"][0]["events"].pop(), "fail"),
    ):
        changed = json.loads(json.dumps(candidate)); mutation(changed)
        assert _asserted_status(_packing_candidate_issue(changed)) == status


def _memory_packing_candidate():
    artifact = "candidate-module-raw-bytes"
    artifact_sha = hashlib.sha256(artifact.encode()).hexdigest()
    controls = ("charge", "release", "sharing", "migration", "descriptor", "concurrent_teardown")
    return {"diff": {"patch_text": "diff --git a/uvm b/uvm\n+candidate", "sha256": hashlib.sha256(b"diff --git a/uvm b/uvm\n+candidate").hexdigest(), "base_sha256": "b" * 64},
        "build": {"command": ["make", "modules"], "returncode": 0, "artifact": artifact, "artifact_sha256": artifact_sha},
        "phase03": {"id": "FEATURE-MEMORYSAVER-03-INTEGRIDAD",
            "before": {"kernel": "6.17", "driver": "615", "gsp": "gsp-a", "boot_id": "boot-a",
                       "modules": {"nvidia": {"sha256": "n"}, "nvidia_uvm": {"sha256": "old"}}},
            "after": {"kernel": "6.17", "driver": "615", "gsp": "gsp-a", "boot_id": "boot-a",
                      "modules": {"nvidia": {"sha256": "n"}, "nvidia_uvm": {"sha256": artifact_sha}}}},
        "integrity_rows": [{"control": control, "events": [
            {"kind": "charge", "page": control, "bytes": 4096, "timestamp_ns": 1, "pid": 4, "cgroup": "owner", "owner_memcg": "owner", "boot_id": "boot-a"},
            {"kind": "uncharge", "page": control, "bytes": 4096, "timestamp_ns": 2, "pid": 4, "cgroup": "owner", "owner_memcg": "owner", "boot_id": "boot-a"}]}
            for control in controls]}


def test_memory_saver_capture_boundaries_and_tracer_adversarial_rows(tmp_path):
    root = tmp_path / "capture"
    path = root / "capture.json"
    path.parent.mkdir()
    path.write_text("[]", encoding="utf-8")
    assert _asserted_status(verify_memory("02-trazador", root)) == "unknown"
    path.write_bytes(b" " * (16 * 1024 * 1024 + 1))
    assert _asserted_status(verify_memory("02-trazador", root)) == "unknown"
    path.unlink()
    assert _asserted_status(verify_memory("02-trazador", root)) == "unknown"
    put(path, {"schema": True, "id": "FEATURE-MEMORYSAVER-02-TRAZADOR", "phase": "02-trazador"})
    assert _asserted_status(verify_memory("02-trazador", root)) == "fail"
    assert _asserted_status(verify_memory("unsupported", root)) == "fail"
    base = {"schema": 1, "id": "FEATURE-MEMORYSAVER-02-TRAZADOR", "phase": "02-trazador",
            "cases": [_memory_case(name, count) for name, count in
                      (("cpu_touch", 1), ("none", 0), ("cuda_bounded", 1))]}
    for mutation, expected in (
        (lambda d: d.update(cases=[]), "unknown"),
        (lambda d: d["cases"][0].pop("pid"), "unknown"),
        (lambda d: d["cases"][0].update(symbol_rows=[]), "unknown"),
        (lambda d: d["cases"][0].update(events=[]), "fail"),
        (lambda d: d["cases"][0]["events"][1].update(timestamp_ns=1), "fail"),
        (lambda d: d["cases"][0]["events"][0].update(kind="strange"), "fail"),
    ):
        doc = json.loads(json.dumps(base))
        mutation(doc)
        put(path, doc)
        assert _asserted_status(verify_memory("02-trazador", root)) == expected


def test_memory_saver_packing_missing_source_alignment_and_hash_are_unknown(tmp_path):
    root = tmp_path / "packing"
    path = root / "capture.json"
    good_source = {"text": "source", "sha256": hashlib.sha256(b"source").hexdigest()}
    base = {"schema": 1, "id": "FEATURE-MEMORYSAVER-04-PACKING-4K", "phase": "04-packing-4k",
            "allocations": [{"page_size": 4096, "backing_bytes": 0, "allocation_id": "load"}],
            "source_texts": [good_source], "alignment_requirements": ["page aligned"]}
    for mutation in (lambda d: d.pop("source_texts"),
                     lambda d: d["source_texts"][0].update(sha256="wrong"),
                     lambda d: d.pop("alignment_requirements")):
        doc = json.loads(json.dumps(base))
        mutation(doc)
        put(path, doc)
    assert _asserted_status(verify_memory("04-packing-4k", root)) == "unknown"


def test_memory_saver_parser_malformed_owner_symbol_and_large_page_cases(tmp_path, monkeypatch):
    import tools.verify_memory_saver as module
    from tools.verify_memory_saver import _charge_ledger, _trace, _packing, main
    root = tmp_path / "bad"; root.mkdir()
    (root / "capture.json").write_text("{", encoding="utf-8")
    assert _asserted_status(verify_memory("02-trazador", root)) == "unknown"
    cases = [_memory_case(name, 1 if name != "none" else 0) for name in ("cpu_touch", "none", "cuda_bounded")]
    cases[0]["events"][0]["owner_memcg"] = "unknown"
    assert _asserted_status(_trace({"cases": cases})) == "unknown"
    bad = _memory_case("cpu_touch", 1); bad["events"][0].pop("bytes")
    assert _charge_ledger(bad)[1] is not None
    assert _packing({"allocations": [{"page_size": 65536, "backing_bytes": 8192, "allocation_id": "a"}],
        "source_texts": [{"text": "src", "sha256": hashlib.sha256(b"src").hexdigest()}],
        "alignment_requirements": [4096]})["status"] == "unknown"
    assert main(["--phase", "02-trazador", "--evidence", str(root)]) == 2
    (root / "capture.json").write_text(json.dumps([]), encoding="utf-8")
    assert _asserted_status(verify_memory("02-trazador", root)) == "unknown"
    from tools.verify_memory_saver import IDS
    doc = {"schema": 1, "id": IDS["02-trazador"], "phase": "02-trazador", "cases": []}
    put(root / "capture.json", doc)
    doc["cases"] = [_memory_case(name, 1 if name != "none" else 0) for name in ("cpu_touch", "none", "cuda_bounded")]
    duplicate = dict(doc["cases"][0]["events"][0])
    duplicate["timestamp_ns"] = 2
    doc["cases"][0]["events"][1]["timestamp_ns"] = 3
    doc["cases"][0]["events"].insert(1, duplicate)
    put(root / "capture.json", doc)
    assert _asserted_status(verify_memory("02-trazador", root)) == "fail"
    monkeypatch.setattr(module, "_trace", lambda _data: (_ for _ in ()).throw(ValueError("nested malformed")))
    put(root / "capture.json", {"schema": 1, "id": IDS["02-trazador"], "phase": "02-trazador"})
    assert _asserted_status(verify_memory("02-trazador", root)) == "unknown"
    monkeypatch.undo()
    assert _asserted_status(_packing({"allocations": []})) == "unknown"
    assert _packing({"allocations": [{"page_size": 4096, "backing_bytes": 0, "allocation_id": "x"}],
        "source_texts": [{"text": "source", "sha256": "bad"}], "alignment_requirements": [4096]})["status"] == "unknown"


def test_forum_evaluator_criteria_negative_paths():
    from tools.verify_forum_pstore import _evaluate
    identity = {key: value for key, value in zip(("oem", "bios", "ec", "kernel", "driver", "boot_id"),
        ("oem", "bios", "ec", "kernel-x", "driver", "boot"))}
    assert _asserted_status(_evaluate("FORUM-02-PSTORE-KERNEL-REGRESSION", {"schema": 1, "id": "FORUM-02-PSTORE-KERNEL-REGRESSION"})) == "unknown"
    doc = {"schema": 1, "id": "FORUM-02-PSTORE-KERNEL-REGRESSION", "stack": identity,
        "pstore": {"boot_id": "boot", "raw_records": [{"content": "clean", "sha256": hashlib.sha256(b"clean").hexdigest()}]}}
    assert _asserted_status(_evaluate("FORUM-02-PSTORE-KERNEL-REGRESSION", doc)) == "fail"
    doc["pstore"]["raw_records"] = [{"content": "FPAC PSCI NMI", "sha256": hashlib.sha256(b"FPAC PSCI NMI").hexdigest()}]
    doc["pstore"]["classification"] = {"ras_signature": "fpac", "sbsa_assessment": "observed", "doe_link_assessment": "not_in_record"}
    source = "oem bios ec kernel-x driver FPAC"
    doc["vendor_resolution"] = {"source_url": "https://example.org/doc", "publisher_domain": "example.org", "source_text": source,
        "source_sha256": hashlib.sha256(source.encode()).hexdigest(),
        "applicability": {"oem": "oem", "bios": "bios", "ec": "ec", "kernel": "kernel-x", "driver": "driver"}, "symptom_resolution": "FPAC"}
    assert _asserted_status(_evaluate("FORUM-02-PSTORE-KERNEL-REGRESSION", doc)) == "unknown"
    doc["vendor_resolution"]["source_url"] = "https://nvidia.com/doc"
    doc["vendor_resolution"]["publisher_domain"] = "nvidia.com"
    doc["vendor_resolution"].update(corrected_version="615.1", verified_fix=False)
    assert _asserted_status(_evaluate("FORUM-02-PSTORE-KERNEL-REGRESSION", doc)) == "fail"
    doc["vendor_resolution"]["verified_fix"] = True
    doc["recommendation"] = {"action": "monitor", "reason": "raw evidence"}
    doc["negative_control"] = {"content": "FPAC", "sha256": hashlib.sha256(b"FPAC").hexdigest()}
    assert _asserted_status(_evaluate("FORUM-02-PSTORE-KERNEL-REGRESSION", doc)) == "fail"


def test_rcu_requires_real_reboot_and_rollback(tmp_path, capsys):
    root = tmp_path / "evidence"
    raw_pstore = "Kernel panic - not syncing: panic-marker=bb-test\n"
    settings = "kernel.panic_on_rcu_stall=1\nkernel.panic=30\n"
    put(root / "recovery.json", {"schema": 1, "host": {"boot_id": "b"},
                                  "active": {"sysctl_text": settings, "cmdline": "x",
                                             "pstore_backend_capture": {"command": ["dmesg"], "returncode": 0,
                                                                         "stdout": "Registered efi as persistent store backend\n"}},
                                  "forced_test": {"raw_pstore": raw_pstore, "raw_pstore_sha256": hashlib.sha256(raw_pstore.encode()).hexdigest(), "expected_marker": "panic-marker=bb-test",
                                                  "boot_before": "a", "boot_after": "b"},
                                  "rollback": {"original_sysctl_text": "kernel.panic_on_rcu_stall=0\nkernel.panic=0\n",
                                               "restored_sysctl_text": "kernel.panic_on_rcu_stall=0\nkernel.panic=0\n"},
                                  "kdump": {"systemctl_show": "LoadState=loaded\nActiveState=active\n"}})
    result = verify_rcu(root)
    assert _asserted_status(result) == "pass"
    assert result["natural_rcu_recovery"] == "unobserved"
    from tools.verify_rcu_panic_pstore import main
    assert main(["--evidence", str(root)]) == 0
    assert _asserted_status(json.loads(capsys.readouterr().out)) == "pass"
    doc = json.loads((root / "recovery.json").read_text(encoding="utf-8"))
    doc["forced_test"]["expected_marker"] = ""
    put(root / "recovery.json", doc)
    assert _asserted_status(verify_rcu(root)) == "unknown"
    doc["forced_test"]["expected_marker"] = "panic-marker=bb-test"
    doc["forced_test"].pop("boot_before")
    put(root / "recovery.json", doc)
    assert _asserted_status(verify_rcu(root)) == "unknown"
    doc["forced_test"]["boot_before"] = "a"
    doc["kdump"]["systemctl_show"] = "LoadState=loaded\nActiveState=inactive\n"
    put(root / "recovery.json", doc)
    assert _asserted_status(verify_rcu(root)) == "fail"
    doc["kdump"]["systemctl_show"] = "LoadState=loaded\nActiveState=active\n"
    doc["rollback"]["restored_sysctl_text"] = settings
    put(root / "recovery.json", doc)
    assert _asserted_status(verify_rcu(root)) == "fail"
    (root / "recovery.json").unlink()
    assert _asserted_status(verify_rcu(root)) == "unknown"


def test_rcu_reported_prototype_counterexample_is_unknown_not_pass(tmp_path):
    root = tmp_path / "adversarial"
    raw = "ordinary boot, no panic marker"
    active = "kernel.panic_on_rcu_stall=1\nkernel.panic=30\n"
    put(root / "recovery.json", {"schema": 1, "host": {"boot_id": "after"},
        "active": {"sysctl_text": active, "cmdline": "crashkernel=1G",
                   "pstore_backend_capture": {"command": ["dmesg"], "returncode": 0, "stdout": "Registered efi as persistent store backend"}},
        "forced_test": {"raw_pstore": raw, "raw_pstore_sha256": hashlib.sha256(raw.encode()).hexdigest(),
                        "expected_marker": "", "boot_after": "after"},
        "rollback": {"original_sysctl_text": "old", "restored_sysctl_text": "old"},
        "kdump": {"systemctl_show": "LoadState=loaded\nActiveState=inactive\n"}})
    result = verify_rcu(root)
    assert _asserted_status(result) == "unknown"
    assert result["could_not_run_count"] == 1


def test_rcu_marker_incidental_without_real_panic_signature_fails(tmp_path):
    root = tmp_path / "incidental"
    raw = "ordinary log mentions panic-marker=bb-test but no kernel panic or RCU stall"
    settings = "kernel.panic_on_rcu_stall=1\nkernel.panic=30\n"
    put(root / "recovery.json", {"schema": 1, "host": {"boot_id": "b"},
        "active": {"sysctl_text": settings, "cmdline": "crashkernel=1G",
                   "pstore_backend_capture": {"command": ["dmesg"], "returncode": 0, "stdout": "Registered efi as persistent store backend"}},
        "forced_test": {"raw_pstore": raw, "raw_pstore_sha256": hashlib.sha256(raw.encode()).hexdigest(),
                        "expected_marker": "panic-marker=bb-test", "boot_before": "a", "boot_after": "b"},
        "rollback": {"original_sysctl_text": "old", "restored_sysctl_text": "old"},
        "kdump": {"systemctl_show": "LoadState=loaded\nActiveState=active\n"}})
    assert _asserted_status(verify_rcu(root)) == "fail"


def test_rcu_fixture_backend_and_kdump_description_do_not_pass(tmp_path):
    root = tmp_path / "fixture"
    raw = "Kernel panic - not syncing: panic-marker=bb-test\nrcu: stall detected\n"
    settings = "kernel.panic_on_rcu_stall=1\nkernel.panic=30\n"
    put(root / "recovery.json", {"schema": 1, "host": {"boot_id": "b"},
        "active": {"sysctl_text": settings, "cmdline": "crashkernel=1G", "pstore_backend_capture": "fixture"},
        "forced_test": {"raw_pstore": raw, "raw_pstore_sha256": hashlib.sha256(raw.encode()).hexdigest(),
                        "expected_marker": "panic-marker=bb-test", "boot_before": "a", "boot_after": "b"},
        "rollback": {"original_sysctl_text": "old", "restored_sysctl_text": "old"},
        "kdump": {"systemctl_show": "Description=service active, running\n"}})
    assert _asserted_status(verify_rcu(root)) == "unknown"
    doc = json.loads((root / "recovery.json").read_text(encoding="utf-8"))
    doc["active"]["pstore_backend_capture"] = {"command": ["dmesg"], "returncode": 0, "stdout": "Registered efi as persistent store backend"}
    put(root / "recovery.json", doc)
    # A kdump description without LoadState/ActiveState observed nothing: could_not_run, not fail.
    described = verify_rcu(root)
    assert described["status"] == "unknown" and described["could_not_run"] == 1 and described["fail"] == 0


def test_rcu_conflicting_duplicate_sysctls_fail(tmp_path):
    root = tmp_path / "duplicate"
    raw = "Kernel panic - not syncing: panic-marker=bb-test\nrcu: stall detected\n"
    settings = "kernel.panic_on_rcu_stall=1\nkernel.panic=30\nkernel.panic=0\n"
    put(root / "recovery.json", {"schema": 1, "host": {"boot_id": "b"},
        "active": {"sysctl_text": settings, "cmdline": "x", "pstore_backend_capture": {"command": ["dmesg"], "returncode": 0, "stdout": "Registered efi as persistent store backend"}}})
    assert _asserted_status(verify_rcu(root)) == "fail"


def test_rcu_active_policy_and_boot_correlations_fail_closed(tmp_path):
    root = tmp_path / "policy"
    raw = "Kernel panic - not syncing: panic-marker=bb-test\n"
    settings = "kernel.panic_on_rcu_stall=1\nkernel.panic=30\n"
    doc = {"schema": 1, "host": {"boot_id": "b"},
        "active": {"sysctl_text": settings, "cmdline": "x",
                   "pstore_backend_capture": {"command": ["dmesg"], "returncode": 0,
                                              "stdout": "Registered efi as persistent store backend"}},
        "forced_test": {"raw_pstore": raw, "raw_pstore_sha256": hashlib.sha256(raw.encode()).hexdigest(),
                        "expected_marker": "panic-marker=bb-test", "boot_before": "a", "boot_after": "b"},
        "rollback": {"original_sysctl_text": "old", "restored_sysctl_text": "old"},
        "kdump": {"systemctl_show": "LoadState=loaded\nActiveState=active\n"}}
    put(root / "recovery.json", doc)
    assert _asserted_status(verify_rcu(root)) == "pass"
    doc["active"]["sysctl_text"] = "kernel.panic_on_rcu_stall 1\nkernel.panic=30\n"
    put(root / "recovery.json", doc)
    malformed = verify_rcu(root)
    assert malformed["status"] == "unknown" and malformed["could_not_run_count"] == 1
    assert malformed["fail"] == 0
    doc["active"]["sysctl_text"] = "kernel.panic_on_rcu_stall=0\nkernel.panic=30\n"
    put(root / "recovery.json", doc)
    assert _asserted_status(verify_rcu(root)) == "fail"
    doc["active"]["sysctl_text"] = settings
    doc["forced_test"]["expected_marker"] = "missing-marker"
    put(root / "recovery.json", doc)
    assert _asserted_status(verify_rcu(root)) == "fail"
    doc["forced_test"]["expected_marker"] = "panic-marker=bb-test"
    doc["forced_test"]["boot_before"] = "b"
    put(root / "recovery.json", doc)
    assert _asserted_status(verify_rcu(root)) == "fail"
    doc["forced_test"]["boot_before"] = "a"
    doc["forced_test"]["boot_after"] = "other"
    put(root / "recovery.json", doc)
    assert _asserted_status(verify_rcu(root)) == "fail"


def test_rcu_missing_policy_backend_and_rollback_captures_stay_open(tmp_path):
    root = tmp_path / "incomplete"
    put(root / "recovery.json", {"schema": 1, "host": {"boot_id": "b"}, "active": "captured"})
    assert _asserted_status(verify_rcu(root)) == "unknown"
    active = {"sysctl_text": "kernel.panic=30", "cmdline": "x",
              "pstore_backend_capture": {"command": ["dmesg"], "returncode": 0, "stdout": "plain log"}}
    put(root / "recovery.json", {"schema": 1, "host": {"boot_id": "b"}, "active": active})
    assert _asserted_status(verify_rcu(root)) == "unknown"
    active["pstore_backend_capture"] = {"command": ["echo"], "returncode": 0,
                                        "stdout": "Registered efi as persistent store backend"}
    put(root / "recovery.json", {"schema": 1, "host": {"boot_id": "b"}, "active": active})
    assert _asserted_status(verify_rcu(root)) == "unknown"


def test_rcu_rollback_and_kdump_capture_types_are_distinguished(tmp_path):
    from tools.verify_rcu_panic_pstore import _validate_rollback
    assert _asserted_status(_validate_rollback({"rollback": [], "kdump": {}})) == "unknown"
    assert _asserted_status(_validate_rollback({"rollback": {"original_sysctl_text": "x", "restored_sysctl_text": "x"},
                               "kdump": {"systemctl_show": ""}})) == "unknown"
    assert _asserted_status(_validate_rollback({"rollback": {"original_sysctl_text": "x", "restored_sysctl_text": "x"},
                               "kdump": {"systemctl_show": "ActiveState=active\nActiveState=inactive"}})) == "fail"


def test_rcu_absent_rollback_or_kdump_state_is_could_not_run_not_fail():
    from tools.verify_rcu_panic_pstore import _validate_rollback
    kdump_ok = {"systemctl_show": "LoadState=loaded\nActiveState=active\n"}
    # Nothing captured about the rollback: could_not_run, never a claim that it failed.
    for rollback in ({}, {"original_sysctl_text": "x"}, {"restored_sysctl_text": "x"},
                     {"original_sysctl_text": "", "restored_sysctl_text": ""}):
        result = _validate_rollback({"rollback": rollback, "kdump": kdump_ok})
        assert result is not None
        assert result["status"] == "unknown" and result["could_not_run"] == 1 and result["fail"] == 0, rollback
    assert _asserted_status(_validate_rollback({"kdump": kdump_ok})) == "unknown"
    # A systemctl capture without the state keys observed nothing about kdump.
    for show in ("Description=kdump active, running\n", "LoadState=loaded\n", "ActiveState=active\n"):
        result = _validate_rollback({"rollback": {"original_sysctl_text": "x", "restored_sysctl_text": "x"},
                                     "kdump": {"systemctl_show": show}})
        assert result is not None
        assert result["status"] == "unknown" and result["could_not_run"] == 1 and result["fail"] == 0, show
    # Negative controls: captured and wrong still fails, captured and right still passes.
    assert _asserted_status(_validate_rollback({"rollback": {"original_sysctl_text": "x", "restored_sysctl_text": "y"},
                                                "kdump": kdump_ok})) == "fail"
    assert _asserted_status(_validate_rollback({"rollback": {"original_sysctl_text": "x", "restored_sysctl_text": "x"},
                                                "kdump": {"systemctl_show": "LoadState=masked\nActiveState=active\n"}})) == "fail"
    assert _validate_rollback({"rollback": {"original_sysctl_text": "x", "restored_sysctl_text": "x"},
                               "kdump": kdump_ok}) is None


def test_rcu_malformed_nested_types_and_boolean_schema_never_traceback(tmp_path):
    root = tmp_path / "types"
    put(root / "recovery.json", {"schema": True, "host": {"boot_id": "b"}, "active": "enabled", "forced_test": "pass"})
    assert _asserted_status(verify_rcu(root)) == "fail"
    put(root / "recovery.json", {"schema": 1, "host": {"boot_id": []}, "active": {"sysctl_text": "", "cmdline": ""}, "forced_test": []})
    assert _asserted_status(verify_rcu(root)) == "unknown"


def test_rcu_cli_malformed_missing_and_oversized_are_unknown(tmp_path, capsys):
    from tools.verify_rcu_panic_pstore import main
    import pytest
    path = tmp_path / "recovery.json"
    path.write_text("[]", encoding="utf-8")
    assert main(["--evidence", str(tmp_path)]) == 2
    assert json.loads(capsys.readouterr().out)["could_not_run_count"] == 1
    path.write_bytes(b"{" + b" " * (1024 * 1024))
    assert main(["--evidence", str(tmp_path)]) == 2
    assert json.loads(capsys.readouterr().out)["could_not_run_count"] == 1
    path.unlink()
    assert main(["--evidence", str(tmp_path)]) == 2
    assert json.loads(capsys.readouterr().out)["could_not_run_count"] == 1


def test_forum_finding_requires_pstore_and_exact_vendor_applicability(tmp_path):
    root = tmp_path / "evidence"
    put(root / "finding.json", {"schema": 1, "id": "FORUM-02-PSTORE-KERNEL-REGRESSION",
                                  "stack": {key: "x" for key in ("oem", "bios", "ec", "kernel", "driver", "boot_id")},
                                  "pstore": {"read_status": "denied", "records": []}})
    assert _asserted_status(verify_forum("FORUM-02-PSTORE-KERNEL-REGRESSION", root)) == "unknown"
    assert _asserted_status(verify_forum("OTHER", root)) == "fail"


def test_forum_finding_positive_from_raw_pstore_vendor_source_and_negative_record(tmp_path):
    root = tmp_path / "evidence"
    kernel = "6.17.0-1014-nvidia"
    record = "FPAC PSCI NMI SBSA Generic Watchdog timeout"
    source = f"OEM BIOS EC {kernel} driver 580 FPAC: no corrected release listed."
    negative = "ordinary boot log with no hardware exception"
    put(root / "finding.json", {"schema": 1, "id": "FORUM-02-PSTORE-KERNEL-REGRESSION",
        "stack": {"oem": "OEM", "bios": "BIOS", "ec": "EC", "kernel": kernel, "driver": "580", "boot_id": "boot-a"},
        "pstore": {"boot_id": "boot-a", "raw_records": [{"content": record, "sha256": hashlib.sha256(record.encode()).hexdigest()}],
                   "classification": {"ras_signature": "fpac", "sbsa_assessment": "observed", "doe_link_assessment": "observed"}},
        "vendor_resolution": {"source_text": source, "source_sha256": hashlib.sha256(source.encode()).hexdigest(),
                              "source_url": "https://www.nvidia.com/en-us/", "publisher_domain": "www.nvidia.com",
                              "applicability": {"oem": "OEM", "bios": "BIOS", "ec": "EC", "kernel": kernel, "driver": "580"},
                              "symptom_resolution": "FPAC"},
        "recommendation": {"action": "monitor", "reason": "No vendor fix applies."},
        "negative_control": {"content": negative, "sha256": hashlib.sha256(negative.encode()).hexdigest()}})
    assert _asserted_status(verify_forum("FORUM-02-PSTORE-KERNEL-REGRESSION", root)) == "pass"


def test_forum_pstore_rejects_identity_source_and_negative_control_traps(tmp_path):
    root = tmp_path / "evidence"
    kernel = "6.17.0-1014-nvidia"
    record = "FPAC PSCI NMI SBSA Generic Watchdog timeout"
    source = f"OEM BIOS EC {kernel} driver 580 FPAC: no corrected release listed."
    negative = "ordinary boot log with no hardware exception"
    doc = {"schema": 1, "id": "FORUM-02-PSTORE-KERNEL-REGRESSION",
        "stack": {"oem": "OEM", "bios": "BIOS", "ec": "EC", "kernel": kernel, "driver": "580", "boot_id": "boot-a"},
        "pstore": {"boot_id": "boot-a", "raw_records": [{"content": record, "sha256": hashlib.sha256(record.encode()).hexdigest()}],
                   "classification": {"ras_signature": "fpac", "sbsa_assessment": "observed", "doe_link_assessment": "observed"}},
        "vendor_resolution": {"source_text": source, "source_sha256": hashlib.sha256(source.encode()).hexdigest(),
                              "source_url": "https://docs.nvidia.com/advisory", "publisher_domain": "docs.nvidia.com",
                              "applicability": {"oem": "OEM", "bios": "BIOS", "ec": "EC", "kernel": kernel, "driver": "580"},
                              "symptom_resolution": "FPAC"},
        "recommendation": {"action": "monitor", "reason": "No vendor fix applies."},
        "negative_control": {"content": negative, "sha256": hashlib.sha256(negative.encode()).hexdigest()}}
    put(root / "finding.json", doc)
    assert _asserted_status(verify_forum("FORUM-02-PSTORE-KERNEL-REGRESSION", root)) == "pass"
    doc["pstore"]["boot_id"] = "other"
    put(root / "finding.json", doc)
    assert _asserted_status(verify_forum("FORUM-02-PSTORE-KERNEL-REGRESSION", root)) == "fail"


def test_forum_pstore_malformed_missing_source_and_control_boundaries(tmp_path):
    root = tmp_path / "finding"
    path = root / "finding.json"
    path.parent.mkdir()
    path.write_text("[]", encoding="utf-8")
    assert _asserted_status(verify_forum("FORUM-02-PSTORE-KERNEL-REGRESSION", root)) == "unknown"
    path.unlink()
    assert _asserted_status(verify_forum("FORUM-02-PSTORE-KERNEL-REGRESSION", root)) == "unknown"
    record = "FPAC PSCI NMI"
    source = "OEM BIOS EC kernel 6.17 driver 615 FPAC"
    negative = "normal startup only"
    base = {"schema": 1, "id": "FORUM-02-PSTORE-KERNEL-REGRESSION",
        "stack": {"oem": "OEM", "bios": "BIOS", "ec": "EC", "kernel": "6.17", "driver": "615", "boot_id": "b"},
        "pstore": {"boot_id": "b", "raw_records": [{"content": record, "sha256": hashlib.sha256(record.encode()).hexdigest()}],
                   "classification": {"ras_signature": "fpac", "sbsa_assessment": "observed", "doe_link_assessment": "not_in_record"}},
        "vendor_resolution": {"source_text": source, "source_sha256": hashlib.sha256(source.encode()).hexdigest(),
                              "source_url": "https://docs.nvidia.com/advisory", "publisher_domain": "docs.nvidia.com",
                              "applicability": {"oem": "OEM", "bios": "BIOS", "ec": "EC", "kernel": "6.17", "driver": "615"}, "symptom_resolution": "FPAC"},
        "recommendation": {"action": "monitor", "reason": "No fix identified."},
        "negative_control": {"content": negative, "sha256": hashlib.sha256(negative.encode()).hexdigest()}}
    mutations = (
        (lambda d: d["pstore"]["raw_records"].__setitem__(0, "raw"), "unknown"),
        (lambda d: d["pstore"]["raw_records"][0].update(content="wrong hash"), "fail"),
        (lambda d: d["pstore"]["raw_records"][0].update(content="ordinary"), "fail"),
        (lambda d: d.pop("vendor_resolution"), "unknown"),
        (lambda d: d["vendor_resolution"].update(source_sha256="wrong"), "fail"),
        (lambda d: d["recommendation"].update(action="ignore"), "unknown"),
        (lambda d: d.pop("negative_control"), "unknown"),
        (lambda d: d["negative_control"].update(sha256="wrong"), "fail"),
    )
    doc = json.loads(json.dumps(base))
    for mutation, expected in mutations:
        doc = json.loads(json.dumps(base))
        mutation(doc)
        put(path, doc)
        assert _asserted_status(verify_forum("FORUM-02-PSTORE-KERNEL-REGRESSION", root)) == expected
    doc["pstore"]["boot_id"] = "boot-a"
    doc["pstore"]["raw_records"][0]["sha256"] = "wrong"
    put(root / "finding.json", doc)
    assert _asserted_status(verify_forum("FORUM-02-PSTORE-KERNEL-REGRESSION", root)) == "fail"
    doc["pstore"]["raw_records"][0]["sha256"] = hashlib.sha256(record.encode()).hexdigest()
    doc["vendor_resolution"]["source_url"] = "https://attacker.example/advisory"
    put(root / "finding.json", doc)
    assert _asserted_status(verify_forum("FORUM-02-PSTORE-KERNEL-REGRESSION", root)) == "fail"
    doc["vendor_resolution"]["source_url"] = "https://docs.nvidia.com/advisory"
    doc["vendor_resolution"]["corrected_version"] = "615.99"
    doc["vendor_resolution"]["verified_fix"] = False
    put(root / "finding.json", doc)
    assert _asserted_status(verify_forum("FORUM-02-PSTORE-KERNEL-REGRESSION", root)) == "fail"
    doc["vendor_resolution"].pop("corrected_version")
    doc["vendor_resolution"].pop("verified_fix")
    doc["negative_control"]["content"] = "ordinary FPAC reference"
    doc["negative_control"]["sha256"] = hashlib.sha256(b"ordinary FPAC reference").hexdigest()
    put(root / "finding.json", doc)
    assert _asserted_status(verify_forum("FORUM-02-PSTORE-KERNEL-REGRESSION", root)) == "fail"


def _netconsole_case(tmp_path):
    from tools.netconsole_marker import verify as marker_verify
    boot = "boot-a"
    marker = f"BB-KERNEL-MARKER-{boot}"
    log = tmp_path / "receiver.log"
    payload = f"<6>1,6,12,-;{marker}\n"
    log.write_text(payload, encoding="utf-8")
    marker_result = marker_verify(log, marker)
    before = {"module": {"status": "absent"}, "boot_parameter_present": False,
              "static_parameter": {"status": "not_applicable"},
              "dynamic_targets_status": {"status": "read"}, "targets": []}
    during = {"module": {"status": "loaded", "loaded": True, "built_in": False},
              "boot_parameter_present": True,
              "static_parameter": {"status": "read", "configured": False},
              "dynamic_targets_status": {"status": "read"},
              "targets": [{"name": "target0", "status": "observed", "configuration_sha256": "a" * 64}]}
    receipt = {"log_path": str(log), "marker": marker, "provenance": "receiver_capture",
               "capture_command": ["socat", "-u", "UDP-RECV:6666", "-"], "capture_sha256": marker_result["capture_sha256"],
               "netconsole_parameter": "6665@dev0,6666@192.0.2.1/aa:bb:cc:dd:ee:ff",
               "correlation_boot_id": boot, "secure_boot_output": "SecureBoot enabled",
               "module_signer_command": ["modinfo", "-F", "signer", "netconsole"],
               "module_signer_output": "NVIDIA kernel signing key",
               "configured_target_sha256": "a" * 64,
               "negative_marker": marker + "-negative",
               "target_identity": {"hostname_command": ["hostnamectl", "--static"], "hostname": "target", "machine_id_command": ["cat", "/etc/machine-id"], "machine_id": "target-id"},
               "receiver_identity": {"hostname_command": ["hostnamectl", "--static"], "hostname": "receiver", "machine_id_command": ["cat", "/etc/machine-id"], "machine_id": "receiver-id"},
               "rollback_capture": {"before": before, "during": during, "after": json.loads(json.dumps(before))},
               "persistence_captures": _persistence_rows(),
               "broken_route_control": _netconsole_unavailable_control(tmp_path, "route", ["ip", "route", "get", "receiver"], "", "RTNETLINK answers: Network is unreachable"),
               "unavailable_receiver_control": _netconsole_unavailable_control(tmp_path, "receiver", ["systemctl", "is-active", "bb-netconsole-receiver"], "inactive", ""),
               "local_continuity": {"journal_capture": {"command": ["journalctl", "--output=json", "--since", "-2min"], "returncode": 0, "stdout": "{\"_BOOT_ID\":\"boot-a\",\"__REALTIME_TIMESTAMP\":\"1791021599000000\",\"MESSAGE\":\"before\"}\n{\"_BOOT_ID\":\"boot-a\",\"__REALTIME_TIMESTAMP\":\"1791021602000000\",\"MESSAGE\":\"after\"}\n"},
                   "telemetry_capture": {"command": ["tail", "-c", "1048576", "/tmp/atom_gpu_telemetry.jsonl"], "returncode": 0, "stdout": "{\"ts\":\"2026-10-03T09:59:59Z\",\"boot_id\":\"boot-a\",\"evento\":\"muestra\"}\n{\"ts\":\"2026-10-03T10:00:02Z\",\"boot_id\":\"boot-a\",\"evento\":\"muestra\"}\n"}},
               "capture_timestamps": {key: "2026-10-03T10:00:00Z" for key in ("target_start", "target_end", "receiver_start", "receiver_end", "marker")},
               "retention_capture": {"command": ["cat", "/etc/blackbox/netconsole-retention.conf"], "returncode": 0, "stdout": "destination=receiver\nmax_age_hours=72\nmax_bytes=10485760\n"}}
    return boot, marker, log, during, before, receipt


def _persistence_rows():
    rows = []
    for path, during in (("/etc/modprobe.d/blackbox-netconsole.conf", "options netconsole netconsole=6665@dev0,6666@192.0.2.1/aa:bb:cc:dd:ee:ff\n"),
                         ("/etc/modules-load.d/blackbox-netconsole.conf", "netconsole\n")):
        for phase in ("before", "during", "after"):
            present = phase == "during"
            rows.append({"path": path, "phase": phase, "command": ["cat", path],
                "returncode": 0 if present else 1, "stdout": during if present else "",
                "stderr": "" if present else f"cat: {path}: No such file or directory\n",
                "mode": 0o644 if present else 0, "symlink": False,
                "sha256": hashlib.sha256(during.encode()).hexdigest() if present else ""})
    return rows


def _netconsole_unavailable_control(tmp_path, kind, command, stdout, stderr):
    from tools.netconsole_marker import verify as marker_verify
    marker = f"BB-NETCONSOLE-{kind.upper()}-UNAVAILABLE"
    before, after = tmp_path / f"{kind}.before.log", tmp_path / f"{kind}.after.log"
    before.write_text("baseline receiver log\n", encoding="utf-8")
    after.write_text("baseline receiver log\n", encoding="utf-8")
    return {"command": command, "returncode": 2, "stdout": stdout, "stderr": stderr,
            "started_ns": 100_000, "ended_ns": 400_000, "marker": marker,
            "started_at": "2026-10-03T09:59:59.500000Z", "ended_at": "2026-10-03T10:00:00Z",
            "before_log_path": str(before), "after_log_path": str(after),
            "before_log_sha256": marker_verify(before, marker)["capture_sha256"],
            "after_log_sha256": marker_verify(after, marker)["capture_sha256"]}


def test_netconsole_receiver_positive_requires_marker_security_and_exact_rollback(tmp_path):
    boot, marker, log, during, before, receipt = _netconsole_case(tmp_path)
    assert _asserted_status(verify_receiver(receipt, boot, before)) == "pass"
    receipt["secure_boot_output"] = "SecureBoot disabled"
    assert _asserted_status(verify_receiver(receipt, boot, before)) == "fail"
    receipt["receiver_identity"]["machine_id"] = "target-id"
    assert _asserted_status(verify_receiver(receipt, boot, before)) == "fail"
    receipt["receiver_identity"]["machine_id"] = "receiver-id"
    receipt["rollback_capture"]["after"]["boot_parameter_present"] = False
    assert _asserted_status(verify_receiver(receipt, boot, before)) == "fail"


def test_netconsole_privacy_reader_limits_hash_encoding_and_addresses(tmp_path):
    from tools.verify_netconsole import _privacy_safe
    path = tmp_path / "log"
    path.write_text("MARKER\n", encoding="utf-8")
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    assert _privacy_safe(path, "MARKER", digest) == ("pass", "MARKER\n")
    assert _privacy_safe(path, "MARKER", "0" * 64)[0] == "fail"
    path.write_bytes(b"\xff")
    assert _privacy_safe(path, "MARKER", hashlib.sha256(b"\xff").hexdigest())[0] == "fail"
    path.write_text("MARKER\nsecond\n", encoding="utf-8")
    assert _privacy_safe(path, "MARKER", hashlib.sha256(path.read_bytes()).hexdigest())[0] == "fail"
    for content in ("MARKER 192.0.2.1", "MARKER aa:bb:cc:dd:ee:ff"):
        path.write_text(content, encoding="utf-8")
        assert _privacy_safe(path, content, hashlib.sha256(path.read_bytes()).hexdigest())[0] == "fail"
    path.write_bytes(b"x" * (1024 * 1024 + 1))
    assert _privacy_safe(path, "MARKER", "0" * 64)[0] == "unknown"
    assert _privacy_safe(tmp_path / "absent", "MARKER", "0" * 64)[0] == "unknown"


def test_netconsole_privacy_accepts_only_documented_kernel_payload_framing(tmp_path):
    from tools.verify_netconsole import _netconsole_payload, _receiver_command, _privacy_safe
    marker = "BB-KERNEL-MARKER-boot"
    payload = f"<6>12,607,22085407756,-;{marker}\n"
    path = tmp_path / "udp.log"
    path.write_text(payload, encoding="utf-8")
    digest = hashlib.sha256(payload.encode()).hexdigest()
    assert _privacy_safe(path, marker, digest) == ("pass", payload)
    assert _netconsole_payload(f"6.4.0,6,444,501151268,-;{marker}", marker)
    assert not _netconsole_payload(f"arbitrary-prefix {marker}", marker)
    assert not _netconsole_payload(f"12,607,22085407756,-;{marker} extra", marker)
    assert not _netconsole_payload(f"<192>12,607,22085407756,-;{marker}", marker)
    for executable in ("nc", "ncat", "netcat", "socat", "syslogd", "journalctl"):
        assert _receiver_command([executable, "--raw"])
    assert not _receiver_command(["tcpdump", "-A"])
    assert not _receiver_command("nc -u")


def test_netconsole_security_rollback_and_receiver_identity_decisions(tmp_path):
    from tools.verify_netconsole import _receiver_controls, _receiver_is_remote
    boot, _, _, _, before, receipt = _netconsole_case(tmp_path)
    assert _asserted_status(_receiver_controls(receipt, boot, before)) == "pass"
    receipt["secure_boot_output"] = "SecureBoot disabled"
    assert _asserted_status(_receiver_controls(receipt, boot, before)) == "fail"
    receipt["secure_boot_output"] = "SecureBoot enabled"
    receipt.pop("persistence_captures")
    assert _asserted_status(_receiver_controls(receipt, boot, before)) == "unknown"
    assert _receiver_is_remote({}) is None
    identity = {"hostname_command": ["hostnamectl", "--static"], "hostname": "host",
                "machine_id_command": ["cat", "/etc/machine-id"], "machine_id": "machine"}
    assert _receiver_is_remote({"target_identity": identity, "receiver_identity": identity}) is False
    assert _receiver_is_remote({"target_identity": identity,
        "receiver_identity": {**identity, "machine_id_command": ["false"]}}) is None


def test_netconsole_evaluate_current_capture_and_unknown_boundaries(monkeypatch):
    from tools import verify_netconsole
    kernel = {"boot_id": {"status": "read", "value": "boot"}}
    net = {"module": {"status": "loaded"}, "static_parameter": {"status": "read"},
           "dynamic_targets_status": {"status": "read"}, "targets": []}
    observed = {"kernel": kernel, "netconsole": net,
                "boot_parameter_netconsole": {"status": "read"}}
    monkeypatch.setattr(verify_netconsole, "capture", lambda _root: observed)
    doc = {"kernel": kernel, "netconsole": net}
    assert _asserted_status(verify_netconsole._evaluate(doc, {})) == "unknown"
    observed["netconsole"] = {**net, "module": {"status": "could_not_run"}}
    doc["netconsole"] = observed["netconsole"]
    assert _asserted_status(verify_netconsole._evaluate(doc, {})) == "unknown"
    observed["netconsole"] = {**net, "module": {"status": "absent"}}
    doc["netconsole"] = observed["netconsole"]
    assert _asserted_status(verify_netconsole._evaluate(doc, {})) == "unknown"
    observed["netconsole"] = net
    doc["netconsole"] = {"changed": True}
    assert _asserted_status(verify_netconsole._evaluate(doc, {})) == "fail"
    doc["netconsole"] = net
    observed["boot_parameter_netconsole"] = {"status": "could_not_run"}
    doc["boot_parameter_netconsole"] = observed["boot_parameter_netconsole"]
    assert _asserted_status(verify_netconsole._evaluate(doc, {})) == "unknown"


def test_netconsole_marker_receipt_rejects_incomplete_provenance_and_controls(tmp_path, monkeypatch):
    from tools import verify_netconsole
    from tools.netconsole_marker import verify as marker_verify
    log = tmp_path / "receiver"
    boot, marker = "boot", "marker-boot"
    log.write_text(marker + "\n", encoding="utf-8")
    marker_data = marker_verify(log, marker)
    good = {"provenance": "receiver_capture", "capture_command": ["journalctl"],
            "capture_sha256": marker_data["capture_sha256"],
            "target_identity": {"hostname_command": ["hostnamectl", "--static"], "hostname": "a",
                "machine_id_command": ["cat", "/etc/machine-id"], "machine_id": "a"},
            "receiver_identity": {"hostname_command": ["hostnamectl", "--static"], "hostname": "b",
                "machine_id_command": ["cat", "/etc/machine-id"], "machine_id": "b"},
            "negative_marker": "never-present"}
    assert _asserted_status(verify_netconsole._verify_marker_receipt({}, boot, str(log), marker, marker_data)) == "unknown"
    receipt = dict(good, provenance="forged")
    assert _asserted_status(verify_netconsole._verify_marker_receipt(receipt, boot, str(log), marker, marker_data)) == "fail"
    receipt = dict(good, capture_command=[])
    assert _asserted_status(verify_netconsole._verify_marker_receipt(receipt, boot, str(log), marker, marker_data)) == "unknown"
    receipt = dict(good)
    receipt.pop("capture_sha256")
    assert _asserted_status(verify_netconsole._verify_marker_receipt(receipt, boot, str(log), marker, marker_data)) == "unknown"
    receipt = dict(good, capture_command=["forged"])
    assert _asserted_status(verify_netconsole._verify_marker_receipt(receipt, boot, str(log), marker, marker_data)) == "fail"
    receipt = dict(good, negative_marker=marker)
    assert _asserted_status(verify_netconsole._verify_marker_receipt(receipt, boot, str(log), marker, marker_data)) == "unknown"
    receipt = dict(good)
    receipt["target_identity"] = {}
    assert _asserted_status(verify_netconsole._verify_marker_receipt(receipt, boot, str(log), marker, marker_data)) == "unknown"
    receipt = dict(good, negative_marker=marker + "suffix")
    assert _asserted_status(verify_netconsole._verify_marker_receipt(receipt, boot, "missing", marker, marker_data)) == "unknown"
    monkeypatch.setattr(verify_netconsole, "_privacy_safe", lambda *_args: ("unknown", None))
    assert _asserted_status(verify_netconsole._verify_marker_receipt(good, boot, str(log), marker, marker_data)) == "unknown"
    monkeypatch.setattr(verify_netconsole, "_privacy_safe", lambda *_args: ("fail", None))
    assert _asserted_status(verify_netconsole._verify_marker_receipt(good, boot, str(log), marker, marker_data)) == "fail"
    monkeypatch.setattr(verify_netconsole, "_privacy_safe", lambda *_args: ("pass", marker))
    assert _asserted_status(verify_netconsole._verify_marker_receipt(dict(good, negative_marker="marker"), boot, str(log),
                                                    marker, marker_data)) == "fail"
    monkeypatch.undo()
    assert _asserted_status(verify_netconsole._receiver_marker({}, boot)) == "unknown"
    assert _asserted_status(verify_netconsole._receiver_marker({"log_path": str(tmp_path / "absent"), "marker": marker}, boot)) == "unknown"
    log.write_text("marker-pre", encoding="utf-8")
    assert _asserted_status(verify_netconsole._receiver_marker({"log_path": str(log), "marker": "marker-prefix"}, boot)) == "fail"


def test_netconsole_cli_missing_and_malformed_inputs_are_unknown(tmp_path, capsys):
    from tools.verify_netconsole import main
    assert main(["--evidence", str(tmp_path / "missing")]) == 2
    assert json.loads(capsys.readouterr().out)["could_not_run_count"] == 1
    evidence = tmp_path / "malformed"
    evidence.mkdir()
    (evidence / "kernel-capture.json").write_text("[]", encoding="utf-8")
    (evidence / "receiver.json").write_text("{}", encoding="utf-8")
    assert main(["--evidence", str(evidence)]) == 2
    assert json.loads(capsys.readouterr().out)["could_not_run_count"] == 1
    (evidence / "kernel-capture.json").write_text("{", encoding="utf-8")
    assert main(["--evidence", str(evidence)]) == 2
    assert json.loads(capsys.readouterr().out)["could_not_run_count"] == 1
    (evidence / "kernel-capture.json").write_bytes(b" " * (1024 * 1024 + 1))
    assert main(["--evidence", str(evidence)]) == 2
    assert json.loads(capsys.readouterr().out)["could_not_run_count"] == 1


def test_kernel_control_module_entrypoints_preserve_missing_evidence_cnr(tmp_path):
    root = Path(__file__).resolve().parents[1]
    commands = (
        [sys.executable, "-m", "tools.verify_cgroup_plan", "--phase", "02-traza", "--evidence", str(tmp_path / "cgroup")],
        [sys.executable, "-m", "tools.verify_netconsole", "--evidence", str(tmp_path / "netconsole")],
        [sys.executable, "-m", "tools.verify_rcu_panic_pstore", "--evidence", str(tmp_path / "rcu")],
        [sys.executable, "-m", "tools.verify_memory_saver", "--phase", "02-trazador", "--evidence", str(tmp_path / "memory")],
        [sys.executable, "-m", "tools.verify_forum_pstore", "--id", "FORUM-02-PSTORE-KERNEL-REGRESSION",
         "--evidence", str(tmp_path / "forum")],
    )
    for command in commands:
        output = subprocess.run(command, cwd=root, capture_output=True, text=True, check=False)
        assert output.returncode == 2, (command, output.stdout, output.stderr)
        result = json.loads(output.stdout)
        assert _asserted_status(result) == "unknown" and result["could_not_run_count"] == 1


def test_netconsole_parser_structural_failures_and_current_capture_exceptions(tmp_path, monkeypatch):
    import tools.verify_netconsole as module
    from tools.verify_netconsole import _evaluate, _netconsole_payload, _receiver_controls
    assert not _netconsole_payload("1,2,3,4,5;MARKER", "MARKER")
    assert not _netconsole_payload("1,2,3,-,ncfrag=0/10;MARKER", "MARKER")
    assert not _netconsole_payload("6.4,not-level,4,5,-;MARKER", "MARKER")
    assert not _netconsole_payload("6,not-seq,4,-;MARKER", "MARKER")
    assert not _netconsole_payload("1,2,3;MARKER", "MARKER")
    assert _evaluate({"kernel": {"boot_id": {"status": "could_not_run"}}}, {})["could_not_run_count"] == 1
    assert _asserted_status(_evaluate({}, {})) == "unknown"
    (tmp_path / "kernel-capture.json").write_text("{}", encoding="utf-8")
    (tmp_path / "receiver.json").write_text("{}", encoding="utf-8")
    monkeypatch.setattr(module, "_evaluate", lambda _doc, _receipt: (_ for _ in ()).throw(KeyError("nested")))
    assert _asserted_status(module.verify(tmp_path)) == "unknown"
    assert _receiver_controls({"secure_boot_output": "SecureBoot disabled", "module_signer_output": ""},
                              "boot", {"module": {}})["status"] == "unknown"


def test_rcu_active_keys_forced_test_shape_and_malformed_catch_paths(tmp_path, monkeypatch):
    from tools.verify_rcu_panic_pstore import _active_policy, _evaluate, _validate_record, verify
    backend = {"command": ["dmesg"], "returncode": 0,
               "stdout": "Registered ramoops as persistent store backend"}
    assert _asserted_status(_active_policy({"sysctl_text": "kernel.panic=3", "cmdline": "quiet",
        "pstore_backend_capture": backend})) == "unknown"
    assert _asserted_status(_validate_record("bad", "boot")) == "unknown"
    assert _asserted_status(_evaluate({"schema": 1, "host": {"boot_id": "boot"}, "active": "active"})) == "unknown"
    root = tmp_path / "nested"; root.mkdir()
    (root / "recovery.json").write_text(json.dumps({"schema": 1, "host": {"boot_id": "boot"},
        "active": {"sysctl_text": 1, "cmdline": "quiet"}}), encoding="utf-8")
    assert _asserted_status(verify(root)) == "unknown"
    import tools.verify_rcu_panic_pstore as module
    (root / "recovery.json").write_text(json.dumps({"schema": 1}), encoding="utf-8")
    monkeypatch.setattr(module, "_evaluate", lambda _data: (_ for _ in ()).throw(ValueError("bad nested")))
    assert _asserted_status(verify(root)) == "unknown"


def test_forum_pstore_oversize_and_identity_boundaries(tmp_path):
    root = tmp_path / "oversize"; root.mkdir()
    (root / "finding.json").write_bytes(b" " * (1024 * 1024 + 1))
    assert _asserted_status(verify_forum("FORUM-02-PSTORE-KERNEL-REGRESSION", root)) == "unknown"
    assert _asserted_status(verify_forum("unsupported", root)) == "fail"
    assert _asserted_status(verify_forum("FORUM-02-PSTORE-KERNEL-REGRESSION", tmp_path / "missing")) == "unknown"


def test_forum_finding_parser_controls_cover_malformed_and_vendor_negative_paths(tmp_path, monkeypatch):
    import tools.verify_forum_pstore as module
    source = "oem bios ec kernel-x driver FPAC"
    valid = {"schema": 1, "id": "FORUM-02-PSTORE-KERNEL-REGRESSION",
        "stack": {key: value for key, value in zip(("oem", "bios", "ec", "kernel", "driver", "boot_id"),
            ("oem", "bios", "ec", "kernel-x", "driver", "boot"))},
        "pstore": {"boot_id": "boot", "raw_records": [{"content": "FPAC PSCI NMI SBSA DOE",
            "sha256": hashlib.sha256(b"FPAC PSCI NMI SBSA DOE").hexdigest()}],
            "classification": {"ras_signature": "fpac", "sbsa_assessment": "observed", "doe_link_assessment": "observed"}},
        "vendor_resolution": {"source_url": "https://nvidia.com/doc", "publisher_domain": "nvidia.com", "source_text": source,
            "source_sha256": hashlib.sha256(source.encode()).hexdigest(), "corrected_version": "615.1", "verified_fix": True,
            "applicability": {"oem": "oem", "bios": "bios", "ec": "ec", "kernel": "kernel-x", "driver": "driver"},
            "symptom_resolution": "FPAC"},
        "recommendation": {"action": "monitor", "reason": "measured"},
        "negative_control": {"content": "clean", "sha256": hashlib.sha256(b"clean").hexdigest()}}
    root = tmp_path / "valid"; root.mkdir(); put(root / "finding.json", valid)
    assert _asserted_status(verify_forum("FORUM-02-PSTORE-KERNEL-REGRESSION", root)) == "pass"
    monkeypatch.setattr(module, "_evaluate", lambda *_: (_ for _ in ()).throw(TypeError("malformed nested")))
    assert _asserted_status(module.verify("FORUM-02-PSTORE-KERNEL-REGRESSION", root)) == "unknown"
    valid["schema"] = True; put(root / "finding.json", valid)
    monkeypatch.undo()
    assert _asserted_status(verify_forum("FORUM-02-PSTORE-KERNEL-REGRESSION", root)) == "fail"


def test_forum_rejects_unbound_identity_and_irrelevant_vendor_text():
    from tools.verify_forum_pstore import _evaluate
    content = "FPAC PSCI NMI"
    doc = {"schema": 1, "id": "FORUM-02-PSTORE-KERNEL-REGRESSION",
        "stack": {"oem": "unknown", "bios": "unknown", "ec": "unknown", "kernel": "unbound",
                  "driver": "unknown", "boot_id": "boot"},
        "pstore": {"boot_id": "boot", "raw_records": [{"content": content,
            "sha256": hashlib.sha256(content.encode()).hexdigest()}]},
        "vendor_resolution": {"source_url": "https://docs.nvidia.com/irrelevant", "source_text": "kernel version only",
            "source_sha256": hashlib.sha256(b"kernel version only").hexdigest()},
        "recommendation": {"action": "RMA", "reason": "arbitrary"}}
    result = _evaluate("FORUM-02-PSTORE-KERNEL-REGRESSION", doc)
    assert _asserted_status(result) == "unknown" and result["could_not_run_count"] == 1


def test_forum_pstore_vendor_and_control_decision_branches():
    from tools.verify_forum_pstore import _evaluate
    identity = {"oem": "O", "bios": "B", "ec": "E", "kernel": "K", "driver": "D", "boot_id": "boot"}
    raw = "FPAC SBSA DOE"
    source = "O B E K D FPAC exact resolution"
    clean = "ordinary startup"
    base = {"schema": 1, "id": "FORUM-02-PSTORE-KERNEL-REGRESSION", "stack": identity,
        "pstore": {"boot_id": "boot", "raw_records": [{"content": raw, "sha256": hashlib.sha256(raw.encode()).hexdigest()}],
                   "classification": {"ras_signature": "fpac", "sbsa_assessment": "observed", "doe_link_assessment": "observed"}},
        "vendor_resolution": {"source_url": "https://vendor.example/advisory", "publisher_domain": "vendor.example",
            "source_text": source, "source_sha256": hashlib.sha256(source.encode()).hexdigest(),
            "applicability": {"oem": "O", "bios": "B", "ec": "E", "kernel": "K", "driver": "D"},
            "symptom_resolution": "exact resolution"},
        "recommendation": {"action": "monitor", "reason": "source-backed"},
        "negative_control": {"content": clean, "sha256": hashlib.sha256(clean.encode()).hexdigest()}}
    assert _asserted_status(_evaluate(base["id"], base)) == "pass"
    for mutate, result in (
        (lambda d: d["pstore"].pop("classification"), "unknown"),
        (lambda d: d["pstore"]["classification"].update(doe_link_assessment="unknown"), "unknown"),
        (lambda d: d["vendor_resolution"].update(source_url="bad"), "unknown"),
        (lambda d: d["vendor_resolution"].update(publisher_domain="other"), "unknown"),
        (lambda d: d["vendor_resolution"].update(applicability={}), "unknown"),
        (lambda d: d["vendor_resolution"].update(source_text="K only"), "fail"),
        (lambda d: d["vendor_resolution"].update(source_text="K only", source_sha256=hashlib.sha256(b"K only").hexdigest()), "unknown"),
        (lambda d: d["vendor_resolution"].update(symptom_resolution="absent"), "unknown"),
        (lambda d: d["vendor_resolution"].update(corrected_version="2", verified_fix=False), "fail"),
        (lambda d: d.update(recommendation={"action": "ignore", "reason": "x"}), "unknown"),
        (lambda d: d.pop("negative_control"), "unknown"),
        (lambda d: d["negative_control"].update(sha256="bad"), "fail"),
        (lambda d: d["negative_control"].update(content="FPAC", sha256=hashlib.sha256(b"FPAC").hexdigest()), "fail"),
    ):
        doc = json.loads(json.dumps(base)); mutate(doc)
        outcome = _evaluate(base["id"], doc)
        assert _asserted_status(outcome) == result, outcome


def test_cgroup_phase_evaluators_classify_measured_failures_and_missing_data():
    import pytest
    from tools.verify_cgroup_plan import (
        MissingEvidence, _candidate_build_issue, _candidate_integrity_issue,
        _hang_run, _limit_observation_complete, _matches_stack, _native_candidate,
        _native_controls as validate_native_controls, _native_report, _native_stack, _patch_dmem,
        _phase02_binding_and_rollback, _raw_json, _raw_limit_test,
        _sharing_correct,
    )

    pair = _native_pair()
    trace = _phase02_trace(pair)
    trace["allocations"][0]["trace_sha256"] = "wrong"
    assert "invalid" in _phase02_binding_and_rollback(
        {"phase02_trace": trace}, pair)[0]
    with pytest.raises(MissingEvidence, match="incomplete"):
        _native_stack({**pair[1], "raw_run": {**pair[1]["raw_run"], "runs": []}})
    assert not _matches_stack(pair[1]["raw_run"], {**pair[1], "module_capture": []})

    raw = _native_run(charge_dmem=True, version="615.71.09")
    none_run = next(row for row in raw["runs"] if row["api"] == "none")
    none_rows = [json.loads(line) for line in none_run["stdout"].splitlines()]
    next(row for row in none_rows if row["phase"] == "held")["files"]["dmem.current"]["value"] = "1"
    none_run["stdout"] = "\n".join(json.dumps(row) for row in none_rows)
    assert _native_candidate(raw) is not None
    malformed_candidate = json.loads(json.dumps(pair[1]))
    malformed_candidate["raw_run"]["runs"] = []
    malformed = {"stack_runs": [malformed_candidate], "native_controls": _native_controls()}
    assert _native_report(malformed)["complete"] is False

    controls = _native_controls()
    controls["limit_observations"].pop()
    with pytest.raises(MissingEvidence, match="cover every GPU API"):
        validate_native_controls(controls)
    controls = _native_controls()
    controls["sharing_rows"] = [{"cgroup": "a"}]
    with pytest.raises(MissingEvidence, match="independent two-cgroup"):
        validate_native_controls(controls)
    assert not _limit_observation_complete({"api": "cuda_malloc", "domain": "memory",
        "returncode": True, "requested_bytes": 10, "limit_bytes": 5,
        "before": 0, "after": 0, "diagnostic": "memory.max"})

    assert _raw_json("[not json") is None
    assert not _raw_limit_test(json.dumps({"returncode": 1, "requested_bytes": 10,
        "limit_bytes": 5, "before": 0, "after": 0, "diagnostic": "unrelated"}))
    assert not _sharing_correct([{"cgroup": "a", "before": 0, "held": 10,
        "after_release": 1}, {"cgroup": "b", "before": 0, "held": 10,
        "after_release": 0}])
    with pytest.raises(MissingEvidence, match="exact build command"):
        _candidate_build_issue({"command": ["make"], "returncode": 0, "stdout": ""})
    with pytest.raises(MissingEvidence):
        _candidate_integrity_issue([])
    malformed = _hang_fixture_run("baseline")
    malformed["samples"][0] = {"api": "cpu_touch", "monotonic_ns": 1}
    with pytest.raises(ValueError, match="sample rows"):
        _hang_run(malformed)
    with pytest.raises(MissingEvidence, match="trial rows required"):
        _hang_run({**malformed, "samples": [None]})


def test_cgroup_patch_measurements_require_exact_release_and_complete_cases():
    import pytest
    from tools.verify_cgroup_plan import (
        MissingEvidence, _captured_dmem_series, _measurement_samples, _patch_dmem,
    )

    with pytest.raises(MissingEvidence):
        _measurement_samples([])
    pair = _native_pair()
    pair[1]["raw_run"] = _native_run(charge_dmem=False, version="615.71.09")
    series = _captured_dmem_series(pair[1]["raw_run"])
    rows = [{"api": api, "samples": [
        {"phase": phase, "value": samples[phase]} for phase in
        ("before", "held", "after_release")]}
        for api, samples in series.items()]
    assert len(_measurement_samples(rows)) == len(APIS)
    evidence = {"dmem_measurements": rows, "native_controls": _native_controls()}
    outcomes, issue = _patch_dmem(evidence, pair)
    assert issue is None and outcomes["gap"]
    cuda_run = next(row for row in pair[1]["raw_run"]["runs"] if row["api"] == "cuda_malloc")
    cuda_rows = [json.loads(line) for line in cuda_run["stdout"].splitlines()]
    next(row for row in cuda_rows if row["phase"] == "after_release")["files"]["dmem.current"]["value"] = "1"
    cuda_run["stdout"] = "\n".join(json.dumps(row) for row in cuda_rows)
    series = _captured_dmem_series(pair[1]["raw_run"])
    evidence["dmem_measurements"] = [{"api": api, "samples": [
        {"phase": phase, "value": values[phase]} for phase in ("before", "held", "after_release")]}
        for api, values in series.items()]
    _, issue = _patch_dmem(evidence, pair)
    assert issue is not None and "return to its captured baseline" in issue


def test_cgroup_native_and_patch_reports_distinguish_adverse_from_missing():
    import pytest
    from tools.verify_cgroup_plan import (
        MissingEvidence, _native_candidate, _native_control_report, _native_controls as validate_controls,
        _native_report, _patch_report, _raw_limit_test,
    )

    raw = _native_run(charge_dmem=True, version="615.71.09")
    gpu = next(run for run in raw["runs"] if run["api"] == "cuda_malloc")
    rows = [json.loads(line) for line in gpu["stdout"].splitlines()]
    next(row for row in rows if row["phase"] == "after_release")["files"]["dmem.current"]["value"] = "1"
    gpu["stdout"] = "\n".join(json.dumps(row) for row in rows)
    issue = _native_candidate(raw)
    assert issue is not None and "did not return" in issue

    controls = _native_controls()
    assert _native_control_report(controls)["limits"]["cuda_malloc:memory"]["classification"] == "rejected_at_limit"
    controls["limit_observations"][0]["diagnostic"] = "unrelated worker error"
    assert _native_control_report(controls)["limits"]["cuda_malloc:memory"]["classification"] == "accepted_or_unattributed"
    controls = _native_controls()
    controls["sharing_rows"][0]["held"] = 0
    assert _native_control_report(controls)["independent_cgroups"][0]["classification"] == "gap_or_leak"
    with pytest.raises(MissingEvidence, match="controls are required"):
        validate_controls(None)
    with pytest.raises(MissingEvidence, match="observations required"):
        validate_controls({"limit_observations": None})
    controls = _native_controls()
    controls["limit_observations"][0]["diagnostic"] = ""
    with pytest.raises(MissingEvidence, match="diagnostic"):
        validate_controls(controls)
    controls = _native_controls()
    controls["sharing_rows"][1]["cgroup"] = controls["sharing_rows"][0]["cgroup"]
    with pytest.raises(MissingEvidence, match="two independent cgroups"):
        validate_controls(controls)
    controls = _native_controls()
    controls["sharing_rows"][0]["after_release"] = -1
    with pytest.raises(MissingEvidence, match="counters"):
        validate_controls(controls)
    assert not _raw_limit_test(json.dumps({"returncode": "1", "requested_bytes": 10,
        "limit_bytes": 5, "before": 0, "after": 0, "diagnostic": "memory.max"}))

    pair = _native_pair()
    pair[1]["raw_run"] = _native_run(charge_dmem=False, version="615.71.09")
    bad = _native_evidence(pair)
    bad["native_controls"]["limit_observations"] = []
    assert not _native_report(bad)["complete"]
    incomplete = _patch_report({"paired_runtime_evidence": pair,
        "native_controls": _native_controls(), "dmem_measurements": []})
    assert not incomplete["complete"] and incomplete["could_not_run"]


def test_cgroup_adverse_raw_native_captures_are_failures_with_zero_missing():
    from tools.verify_cgroup_plan import _native_candidate, _native_report, _native_stack

    candidate = _native_pair()[1]
    cpu = next(row for row in candidate["raw_run"]["runs"] if row["api"] == "cpu_touch")
    cpu_rows = [json.loads(line) for line in cpu["stdout"].splitlines()]
    next(row for row in cpu_rows if row["phase"] == "held")["files"]["memory.current"]["value"] = "0"
    cpu["stdout"] = "\n".join(json.dumps(row) for row in cpu_rows)
    issue = _native_stack(candidate)
    assert issue is not None and "status=fail" in issue

    raw = _native_run(charge_dmem=True, version="615.71.09")
    gpu = next(row for row in raw["runs"] if row["api"] == "cuda_malloc")
    rows = [json.loads(line) for line in gpu["stdout"].splitlines()]
    next(row for row in rows if row["phase"] == "before_allocation")["files"]["dmem.current"]["value"] = "2097152"
    next(row for row in rows if row["phase"] == "held")["files"]["dmem.current"]["value"] = "0"
    next(row for row in rows if row["phase"] == "after_release")["files"]["dmem.current"]["value"] = "2097152"
    gpu["stdout"] = "\n".join(json.dumps(row) for row in rows)
    issue = _native_candidate(raw)
    assert issue is not None and "negative allocation delta" in issue

    pair = _native_pair()
    raw = pair[1]["raw_run"]
    gpu = next(row for row in raw["runs"] if row["api"] == "cuda_malloc")
    rows = [json.loads(line) for line in gpu["stdout"].splitlines()]
    next(row for row in rows if row["phase"] == "after_release")["files"]["dmem.current"]["value"] = "1"
    gpu["stdout"] = "\n".join(json.dumps(row) for row in rows)
    report = _native_report({"stack_runs": [pair[1]], "native_controls": _native_controls()})
    assert not report["complete"] and report["could_not_run"]


def test_cgroup_patch_requires_after_build_and_full_raw_integrity_predicates():
    import pytest
    from tools.verify_cgroup_plan import (
        MissingEvidence, _candidate_after_issue, _candidate_build_issue,
        _candidate_integrity_issue, _patch, _patch_build_integrity,
        _patch_evidence, _raw_json, _raw_limit_test,
    )

    with pytest.raises(MissingEvidence, match="paired runtime"):
        _patch({"paired_runtime_evidence": []})
    evidence = _patch_candidate_evidence()
    baseline = evidence["paired_runtime_evidence"][0]
    baseline["boot_id"] = "different-boot"
    assert _patch(evidence)

    evidence = _patch_candidate_evidence()
    evidence["patch_source"] = {}
    with pytest.raises(MissingEvidence, match="hash-verified patch source"):
        _patch_build_integrity(evidence)
    evidence = _patch_candidate_evidence()
    evidence["patch_diff"]["text"] = "not a diff"
    with pytest.raises(MissingEvidence, match="reviewable fork diff"):
        _patch_build_integrity(evidence)
    with pytest.raises(MissingEvidence, match="both required module artifacts"):
        _candidate_build_issue({"command": ["make", "modules"], "returncode": 0,
            "stdout": "CC [M] nvidia.ko"})
    with pytest.raises(MissingEvidence, match="post-build candidate runtime"):
        _candidate_after_issue(None, _native_controls())
    evidence = _patch_candidate_evidence()
    evidence["candidate_after_stack"]["raw_run"]["runs"] = []
    with pytest.raises(MissingEvidence, match="incomplete"):
        _candidate_after_issue(evidence["candidate_after_stack"], evidence["native_controls"])

    integrity = _patch_candidate_evidence()["integrity_rows"]
    variants = (
        ("limit_rejection", "{}", "limit rejection"),
        ("error_unwind", "{}", "unwind"),
        ("sharing", "[]", "two-cgroup"),
        ("concurrent_release", "[]", "concurrent"),
        ("double_charge", "[]", "double-charge"),
        ("lost_charge", "[]", "lost-charge"),
        ("teardown", "[]", "teardown"),
    )
    for case, raw, expected in variants:
        rows = json.loads(json.dumps(integrity))
        next(row for row in rows if row["case"] == case)["raw_output"] = raw
        assert expected in _candidate_integrity_issue(rows)[0]
    assert _raw_json(None) is None
    assert not _raw_limit_test("[]")
    with pytest.raises(MissingEvidence):
        _candidate_integrity_issue(None)


def test_cgroup_patch_measurement_contradictions_and_ledger_malformed_rows():
    import pytest
    from tools.verify_cgroup_plan import (
        MissingEvidence, _candidate_integrity_issue, _concurrent_balanced, _domain_charge_ledger,
        _hang_run, _hangs, _migration_balanced, _patch_dmem,
    )

    pair = _native_pair()
    raw = pair[1]["raw_run"]
    baseline = next(row for row in raw["runs"] if row["api"] == "cuda_malloc")
    rows = [json.loads(line) for line in baseline["stdout"].splitlines()]
    next(row for row in rows if row["phase"] == "before_allocation")["files"]["dmem.current"]["value"] = "2"
    next(row for row in rows if row["phase"] == "held")["files"]["dmem.current"]["value"] = "0"
    next(row for row in rows if row["phase"] == "after_release")["files"]["dmem.current"]["value"] = "2"
    baseline["stdout"] = "\n".join(json.dumps(row) for row in rows)
    from tools.verify_cgroup_plan import _captured_dmem_series
    series = _captured_dmem_series(raw)
    measurements = [{"api": api, "samples": [{"phase": phase, "value": values[phase]}
        for phase in ("before", "held", "after_release")]} for api, values in series.items()]
    result, issue = _patch_dmem({"dmem_measurements": measurements,
        "native_controls": _native_controls()}, pair)
    assert not result and issue is not None and "fell during" in issue
    with pytest.raises(MissingEvidence, match="before/held/released"):
        _patch_dmem({"dmem_measurements": measurements[:-1],
            "native_controls": _native_controls()}, pair)

    assert not _migration_balanced("[null, null]")
    assert not _concurrent_balanced("[]")
    assert not _concurrent_balanced("[{}]")
    assert not _domain_charge_ledger("[null]")
    assert not _domain_charge_ledger("[{\"event\":\"charge\"}]")
    assert not _domain_charge_ledger("[{\"event\":\"charge\",\"page\":\"p\",\"domain\":\"memory\",\"owner_memcg\":\"a\",\"bytes\":true}]")
    conflict = [
        {"event": "charge", "page": "p", "domain": "memory", "owner_memcg": "a", "bytes": 4},
        {"event": "charge", "page": "p", "domain": "dmem", "owner_memcg": "a", "bytes": 4},
    ]
    assert not _domain_charge_ledger(json.dumps(conflict))
    with pytest.raises(MissingEvidence, match="incident captures"):
        _hangs({"incidents": []})
    malformed = _hang_fixture_run("baseline")
    malformed["journal"][0]["__MONOTONIC_TIMESTAMP"] = "not-a-number"
    with pytest.raises(ValueError, match="journal rows"):
        _hang_run(malformed)
    malformed = _hang_fixture_run("baseline")
    malformed["trials"][0]["returncode"] = True
    with pytest.raises(ValueError, match="trial rows need"):
        _hang_run(malformed)


def _patch_declining_capture():
    from tools.verify_cgroup_plan import _captured_dmem_series
    pair = _native_pair()
    pair[1]["raw_run"] = _native_run(charge_dmem=True, version="615.71.09")
    run = next(row for row in pair[1]["raw_run"]["runs"] if row["api"] == "cuda_malloc")
    rows = [json.loads(line) for line in run["stdout"].splitlines()]
    next(row for row in rows if row["phase"] == "before_allocation")["files"]["dmem.current"]["value"] = "2097152"
    next(row for row in rows if row["phase"] == "held")["files"]["dmem.current"]["value"] = "0"
    next(row for row in rows if row["phase"] == "after_release")["files"]["dmem.current"]["value"] = "2097152"
    run["stdout"] = "\n".join(json.dumps(row) for row in rows)
    series = _captured_dmem_series(pair[1]["raw_run"])
    measurements = [{"api": api, "samples": [{"phase": phase, "value": values[phase]}
        for phase in ("before", "held", "after_release")]} for api, values in series.items()]
    evidence = {"paired_runtime_evidence": pair, "dmem_measurements": measurements,
                "native_controls": _native_controls()}
    return pair, evidence


def test_cgroup_patch_declining_capture_routes_to_measured_failure():
    import pytest
    from tools.verify_cgroup_plan import (
        MissingEvidence, _measurement_samples, _native_dmem, _patch_dmem,
        _patch_evidence, _patch_report,
    )

    pair, evidence = _patch_declining_capture()
    result, issue = _patch_dmem(evidence, pair)
    assert not result and issue is not None and "fell during" in issue
    assert _patch_evidence(evidence, pair) == [issue]
    assert _patch_report(evidence)["findings"] == [issue]
    changed = json.loads(json.dumps(evidence["dmem_measurements"]))
    changed[0]["samples"][0]["value"] += 1
    with pytest.raises(MissingEvidence, match="series differs"):
        _patch_dmem({**evidence, "dmem_measurements": changed}, pair)

    for phase, value, expected in (("before_allocation", "not-a-number", "unreadable or invalid"),
                                   ("after_release", "not-a-number", "released dmem.current")):
        raw = _native_run(charge_dmem=True, version="615.71.09")
        run = next(row for row in raw["runs"] if row["api"] == "cuda_malloc")
        rows = [json.loads(line) for line in run["stdout"].splitlines()]
        next(row for row in rows if row["phase"] == phase)["files"]["dmem.current"]["value"] = value
        run["stdout"] = "\n".join(json.dumps(row) for row in rows)
        with pytest.raises(MissingEvidence, match=expected):
            _native_dmem(raw)
    raw = _native_run(charge_dmem=True, version="615.71.09")
    run = raw["runs"][0]
    rows = [json.loads(line) for line in run["stdout"].splitlines()]
    rows[0]["files"]["dmem.current"].update(value=None, error="permission denied")
    run["stdout"] = "\n".join(json.dumps(row) for row in rows)
    with pytest.raises(MissingEvidence, match="unreadable"):
        _native_dmem(raw)

    incomplete = [{"api": api, "samples": []} for api in APIS]
    with pytest.raises(MissingEvidence, match="three-phase"):
        _measurement_samples(incomplete)
    duplicated = [{"api": api, "samples": [
        {"phase": phase, "value": 1} for phase in ("before", "held", "after_release")]} for api in APIS]
    duplicated[0]["samples"][-1]["phase"] = "before"
    with pytest.raises(MissingEvidence, match="three-phase"):
        _measurement_samples(duplicated)
    with pytest.raises(ValueError, match="duplicate or malformed dmem.current phase"):
        malformed = json.loads(json.dumps(evidence["dmem_measurements"]))
        malformed[0]["samples"].append({"phase": "before", "value": 1})
        _measurement_samples(malformed)


def test_cgroup_patch_after_capture_and_owner_trace_fail_closed():
    import pytest
    from tools.verify_cgroup_plan import MissingEvidence, _candidate_after_issue, _patch_build_integrity, _patch_candidate

    with pytest.raises(MissingEvidence, match="owner trace rows"):
        _patch_candidate({"owner_trace": []})
    evidence = _patch_candidate_evidence()
    wrong = json.loads(json.dumps(evidence["candidate_after_stack"]))
    wrong["driver_version"] = "615.other"
    issue = _candidate_after_issue(wrong, evidence["native_controls"])
    assert issue is not None and "does not match selected stack" in issue
    evidence["candidate_after_stack"] = wrong
    assert "post-build candidate runtime failed" in _patch_build_integrity(evidence)[0]
    evidence = _patch_candidate_evidence()
    evidence["candidate_after_stack"]["raw_run"] = _native_run(charge_dmem=False, version="615.71.09")
    issue = _candidate_after_issue(evidence["candidate_after_stack"], evidence["native_controls"])
    assert issue is not None and "leave an API accounting/enforcement gap" in issue
