"""Evidence-backed predicates for the generated hardware batch-03 cards."""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import pytest

from tools.hardware_batch03_controls import verify


def test_shared_reader_rejects_negative_bound_before_opening_input(tmp_path):
    from tools.capture_io import read_regular_bytes

    path = tmp_path / "capture.json"
    path.write_bytes(b"native")
    assert read_regular_bytes(path, 6) == b"native"
    with pytest.raises(ValueError, match="non-negative"):
        read_regular_bytes(path, -1)


@pytest.mark.parametrize("text", ['{"schema":0,"schema":1}', '{"x":NaN}',
                                 '{"x":Infinity}', '{"x":-Infinity}'])
def test_capture_json_rejects_duplicate_keys_and_nonfinite_constants(tmp_path, text):
    from tools.hardware_batch03_controls import MissingEvidence, _json_capture, _strict_json

    assert _strict_json('{"schema":1,"nested":{"value":2}}')["nested"] == {"value": 2}
    path = tmp_path / "capture.json"
    path.write_text(text, encoding="utf-8")
    report = verify(CARDS["usb"], path)
    assert report["status"] == "unknown" and report["could_not_run_count"] == 1
    with pytest.raises(MissingEvidence, match="raw JSON capture malformed"):
        _json_capture({"host": {"text": text}}, "host")


def test_regular_reader_rejects_ancestor_symlinks_and_parent_traversal(tmp_path):
    from tools.hardware_batch03_controls import _regular_bytes

    directory = tmp_path / "actual"
    directory.mkdir()
    artifact = directory / "capture.json"
    artifact.write_bytes(b"native-bytes")
    assert _regular_bytes(artifact) == b"native-bytes"
    alias = tmp_path / "alias"
    alias.symlink_to(directory, target_is_directory=True)
    with pytest.raises(OSError):
        _regular_bytes(alias / artifact.name)
    with pytest.raises(OSError, match="parent traversal"):
        _regular_bytes(directory / ".." / "actual" / artifact.name)
    report = verify(CARDS["usb"], alias / artifact.name)
    assert report["status"] == "unknown" and report["could_not_run_count"] == 1


def test_fifo_inputs_return_unknown_without_waiting_for_a_writer(tmp_path):
    envelope = tmp_path / "envelope.fifo"
    os.mkfifo(envelope)
    artifact_dir = _capture(tmp_path / "artifacts", CARDS["usb"], [], vendor="ASUS", product="GX10")
    host = artifact_dir / "host.json"
    host.unlink()
    os.mkfifo(host)
    for evidence in (envelope, artifact_dir):
        result = subprocess.run(
            [sys.executable, "-m", "tools.hardware_batch03_controls",
             "--id", CARDS["usb"], "--evidence", str(evidence)],
            capture_output=True, text=True, timeout=3,
        )
        assert result.returncode == 2, result.stderr
        verdict = json.loads(result.stdout)
        assert verdict["status"] == "unknown" and verdict["could_not_run_count"] == 1
        assert any("regular file" in finding for finding in verdict["findings"])


CARDS = {
    "thermal_aux": "DELTA-FORUM-THERMAL-AUXILIARY-COOLING-AND-CLOCK-CAP-01",
    "thermal_coverage": "DELTA-FORUM-THERMAL-TELEMETRY-COVERAGE-01",
    "usb": "DELTA-FORUM-USB-RAID-LINK-ADMISSION-01",
    "backup": "DELTA-ROOT-BACKUP-MOUNT-BOOT-IDENTITY-01",
    "display": "DELTA-ROOT-DISPLAY-CARVEOUT-OEM-FIX-GATE-01",
    "cable": "DELTA-ROOT-GX10-SOC-EC-CABLE-RECOVERY-CANDIDATE-01",
    "subambient": "DELTA-ROOT-SUBAMBIENT-COOLING-AND-UMA-CANARY-01",
}


def _capture(tmp_path: Path, card_id: str, rows: list[dict], *, vendor: str, product: str) -> Path:
    tmp_path.mkdir(parents=True, exist_ok=True)
    host = {"schema": 1, "identity": {"architecture": "aarch64", "kernel_release": "6.17.0-test"}, "checks": {}}
    thermal = {"schema": 1, "status": "observed", "captured_at_utc": "2026-10-04T12:00:00+00:00",
        "host": {"system": "Linux", "release": "6.17.0-test", "machine": "aarch64", "dmi": {
            "sys_vendor": {"status": "ok", "value": vendor}, "product_name": {"status": "ok", "value": product},
            "product_version": {"status": "ok", "value": "B.1"}, "board_name": {"status": "ok", "value": "P4242"}}},
        "thermal_zones": [{"name": "thermal_zone0", "type": {"status": "ok", "value": "cpu"},
            "temperature": {"path": "/sys/class/thermal/thermal_zone0/temp",
                "read": {"status": "ok", "value": "42000"}, "value_raw": 42000,
                "value": 42.0, "unit": "celsius", "status": "ok"},
            "trip_point_scan": {"status": "ok", "error": None, "count": 0}, "trip_points": []}],
        "hwmon": [], "thermal_zone_scan": {"status": "ok", "error": None, "count": 1},
        "hwmon_scan": {"status": "no_hwmon_devices", "error": None, "count": 0},
        "no_sensor_detected": False, "could_not_run": 0, "assessment": "coverage_only"}
    payloads = {"host.json": json.dumps(host, sort_keys=True) + "\n",
        "thermal.json": json.dumps(thermal, sort_keys=True) + "\n"}
    if card_id == CARDS["thermal_coverage"]:
        host_digest = hashlib.sha256(payloads["host.json"].encode()).hexdigest()
        digest = hashlib.sha256(payloads["thermal.json"].encode()).hexdigest()
        for row in rows:
            if row.get("case") in {"inference_soak", "thermal_control", "oom_control", "power_cut_control"}:
                row["subject_host_capture_sha256"] = host_digest
            if row.get("case") == "inference_soak":
                row["thermal_capture_sha256"] = digest
                row["collector_captured_at_utc"] = thermal["captured_at_utc"]
                for source in row.get("thermal_sources", []):
                    source["collector_sha256"] = digest
                    source["collector_captured_at_utc"] = thermal["captured_at_utc"]
                for sample in row.get("samples", []):
                    sample.setdefault("boot_id", row["boot_id"])
        payloads["journal.jsonl"] = _journal_fixture_content(rows)
        payloads["power-loss.json"] = _power_fixture_content(rows, host_digest)
    payloads["study.jsonl"] = "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows)
    if card_id == CARDS["thermal_aux"]:
        payloads["oem-limits.txt"] = "gpu_max_c=100\ncpu_max_c=100\npsu_zone_max_c=80\nwall_power_max_w=500\n"
    records = []
    commands = {"host_diagnostics": ["python3", "-m", "tools.host_diagnostics"],
        "thermal_coverage": ["python3", "-m", "tools.thermal_coverage"], "study": ["cat", "study.jsonl"],
        "journal_events": ["journalctl", "--no-pager", "--output=json", "--since", "2026-10-04T12:00:00+00:00",
            "--until", "2026-10-04T12:04:00+00:00"],
        "power_loss_instrument": ["external-power-recorder", "read-json"],
        "oem_limits_doc": ["cat", "oem-limits.txt"]}
    for name, content in payloads.items():
        path = tmp_path / name
        path.write_text(content, encoding="utf-8")
        key = {"host.json": "host_diagnostics", "thermal.json": "thermal_coverage", "study.jsonl": "study",
            "journal.jsonl": "journal_events", "power-loss.json": "power_loss_instrument",
            "oem-limits.txt": "oem_limits_doc"}[name]
        digest = hashlib.sha256(content.encode()).hexdigest()
        records.append({"name": key, "command": commands[key], "returncode": 0, "stderr": "",
            "artifact": name, "sha256_oracle": {"command": ["sha256sum", name], "returncode": 0,
                "stdout": f"{digest}  {name}\n"}})
    doc = {"schema": 1, "card_id": card_id, "captures": records}
    (tmp_path / "capture.json").write_text(json.dumps(doc, sort_keys=True), encoding="utf-8")
    return tmp_path


def _journal_fixture_content(rows: list[dict]) -> str:
    events = []
    for row in rows:
        case = row.get("case")
        if (case not in {"inference_soak", "thermal_control", "oom_control", "power_cut_control"} or
                not isinstance(row.get("started_at_utc"), str) or not isinstance(row.get("boot_id"), str)):
            continue
        start = row["started_at_utc"]
        when = int(datetime.fromisoformat(start).timestamp() * 1_000_000) + 1_000_000
        message = row.get("journal_text", "soak journal sample" if case == "inference_soak" else "boot journal context")
        events.append({"__REALTIME_TIMESTAMP": str(when), "_BOOT_ID": row["boot_id"], "MESSAGE": message})
    return "".join(json.dumps(row) + "\n" for row in events)


def _power_fixture_content(rows: list[dict], host_digest: str) -> str:
    run = next((row for row in rows if row.get("case") == "power_cut_control"), {})
    record = {"event_kind": "power_loss", "observed_at_utc": run.get("started_at_utc"),
        "run_boot_id": run.get("boot_id"), "subject_host_capture_sha256": host_digest,
        "instrument_id": "bench-recorder-01"}
    return json.dumps(record, sort_keys=True) + "\n"


def _sample(timestamp: int = 1) -> dict:
    return {"timestamp_ns": timestamp, "gpu_c": 70.0, "cpu_c": 65.0, "inlet_c": 24.0,
        "psu_zone_c": 45.0, "wall_power_w": 250.0, "throughput": 100.0, "gpu_clock_mhz": 1900,
        "throttled": False, "shutdown": False}


def _rollback() -> dict:
    return {"configuration_before": {"airflow": "a" * 64, "clock": "b" * 64},
        "configuration_after": {"airflow": "a" * 64, "clock": "b" * 64}}


def test_thermal_aux_measured_matched_ab_pass_and_mismatch_does_not_close(tmp_path):
    runs = []
    for case, gpu, throughput in (("stock", 75, 100), ("base_fan", 70, 100),
                                  ("extractor_plus_clock_cap", 68, 99)):
        runs.append({"case": case, "workload_id": "c"*64, "ambient_c": 24.0, "ambient_source": "external-probe-serial-1",
            "kernel_release": "6.17.0-test", "driver_version": "580.159.03", "firmware_version": "7.6.0", "boot_id": "boot-a",
            "configuration_sha256": "c" * 64, **_rollback(),
            "oem_limits": {"stack_sha256": "", "document_sha256": "", "gpu_max_c": 100, "cpu_max_c": 100,
                "psu_zone_max_c": 80, "wall_power_max_w": 500, "throughput_min": 90},
            "samples": [{**_sample(1), "gpu_c": gpu, "throughput": throughput},
                        {**_sample(2), "gpu_c": gpu, "throughput": throughput}]})
    # The stack binding is a recomputed capture digest, not a status field.
    def build(directory):
        evidence = _capture(directory, CARDS["thermal_aux"], runs, vendor="ASUSTeK COMPUTER INC.", product="GX10")
        capture = json.loads((directory / "capture.json").read_text(encoding="utf-8"))
        digest = capture["captures"][1]["sha256_oracle"]["stdout"].split()[0]
        doc_digest = next(row for row in capture["captures"] if row["name"] == "oem_limits_doc")["sha256_oracle"]["stdout"].split()[0]
        for row in runs:
            row["oem_limits"]["stack_sha256"] = digest
            row["oem_limits"]["document_sha256"] = doc_digest
        return _capture(directory, CARDS["thermal_aux"], runs, vendor="ASUSTeK COMPUTER INC.", product="GX10")
    path = build(tmp_path / "pass")
    (path / "study.jsonl").write_text("".join(json.dumps(row) + "\n" for row in runs), encoding="utf-8")
    # Recompute the independent oracle after writing the raw artifact.
    _refresh_study_oracle(path)
    negative = {"case": "negative_control", "baseline_ambient_c": 24.0, "candidate_ambient_c": 27.0,
        "baseline_workload_id": "c"*64, "candidate_workload_id": "d"*64}
    _replace_study_rows(path, [*runs, negative])
    result = verify(CARDS["thermal_aux"], path)
    assert result["status"] == "pass", result
    negative["candidate_ambient_c"] = 24.0
    negative["candidate_workload_id"] = "c"*64
    _replace_study_rows(path, [*runs, negative])
    assert verify(CARDS["thermal_aux"], path)["status"] == "fail"
    negative.update(candidate_ambient_c=27.0, candidate_workload_id="d"*64)
    matched = [json.loads(json.dumps(row)) for row in runs]
    matched[1]["ambient_c"] = 25.0
    _replace_study_rows(path, [*matched, negative])
    assert verify(CARDS["thermal_aux"], path)["status"] == "unknown"
    matched[1]["ambient_c"] = 24.0
    for sample in matched[2]["samples"]:
        sample["gpu_clock_mhz"] = 2050
    _replace_study_rows(path, [*matched, negative])
    assert verify(CARDS["thermal_aux"], path)["status"] == "fail"
    for sample in matched[2]["samples"]:
        sample["gpu_clock_mhz"] = 1900
    matched[0]["configuration_after"]["airflow"] = "d"*64
    _replace_study_rows(path, [*matched, negative])
    assert verify(CARDS["thermal_aux"], path)["status"] == "unknown"
    matched = [json.loads(json.dumps(row)) for row in runs]
    matched[1]["samples"][0]["gpu_c"] = 101
    _replace_study_rows(path, [*matched, negative])
    assert verify(CARDS["thermal_aux"], path)["status"] == "fail"
    matched[1]["samples"][0]["gpu_c"] = 70
    matched[1]["configuration_sha256"] = "bad"
    _replace_study_rows(path, [*matched, negative])
    assert verify(CARDS["thermal_aux"], path)["status"] == "unknown"
    matched = [json.loads(json.dumps(row)) for row in runs]
    matched[1]["oem_limits"]["stack_sha256"] = "bad"
    _replace_study_rows(path, [*matched, negative])
    assert verify(CARDS["thermal_aux"], path)["status"] == "unknown"
    _replace_study_rows(path, [*runs[:2], negative])
    assert verify(CARDS["thermal_aux"], path)["status"] == "unknown"


def _refresh_study_oracle(path: Path) -> None:
    doc = json.loads((path / "capture.json").read_text(encoding="utf-8"))
    raw = (path / "study.jsonl").read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    row = next(item for item in doc["captures"] if item["name"] == "study")
    row["sha256_oracle"]["stdout"] = f"{digest}  study.jsonl\n"
    (path / "capture.json").write_text(json.dumps(doc), encoding="utf-8")


def _replace_study_rows(path: Path, rows: list[dict]) -> None:
    if any(row.get("case") == "inference_soak" for row in rows):
        thermal_raw = (path / "thermal.json").read_bytes()
        thermal = json.loads(thermal_raw)
        digest = hashlib.sha256(thermal_raw).hexdigest()
        timestamp = thermal["captured_at_utc"]
        for row in rows:
            if row.get("case") == "inference_soak":
                row["thermal_capture_sha256"] = digest
                row["collector_captured_at_utc"] = timestamp
                for source in row.get("thermal_sources", []):
                    source["collector_sha256"] = digest
                    source["collector_captured_at_utc"] = timestamp
    (path / "study.jsonl").write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
    _refresh_study_oracle(path)
    capture_doc = json.loads((path / "capture.json").read_text(encoding="utf-8"))
    capture_names = {row["name"] for row in capture_doc["captures"]}
    host_row = next(row for row in capture_doc["captures"] if row["name"] == "host_diagnostics")
    host_digest = host_row["sha256_oracle"]["stdout"].split()[0]
    for name, artifact, raw in (
        ("journal_events", "journal.jsonl", _journal_fixture_content(rows).encode()),
        ("power_loss_instrument", "power-loss.json", _power_fixture_content(rows, host_digest).encode()),
    ):
        if name not in capture_names:
            continue
        (path / artifact).write_bytes(raw)
        capture_row = next(row for row in capture_doc["captures"] if row["name"] == name)
        capture_row["sha256_oracle"]["stdout"] = f"{hashlib.sha256(raw).hexdigest()}  {artifact}\n"
    (path / "capture.json").write_text(json.dumps(capture_doc), encoding="utf-8")


def _drop_journal_boot(path: Path, boot_id: str) -> None:
    rows = [json.loads(line) for line in (path / "journal.jsonl").read_text(encoding="utf-8").splitlines() if line]
    raw = "".join(json.dumps(row) + "\n" for row in rows if row.get("_BOOT_ID") != boot_id).encode()
    _rewrite_capture_artifact(path, "journal_events", "journal.jsonl", raw)


def _rewrite_capture_artifact(path: Path, name: str, artifact: str, raw: bytes) -> None:
    (path / artifact).write_bytes(raw)
    doc = json.loads((path / "capture.json").read_text(encoding="utf-8"))
    row = next(item for item in doc["captures"] if item["name"] == name)
    row["sha256_oracle"]["stdout"] = f"{hashlib.sha256(raw).hexdigest()}  {artifact}\n"
    (path / "capture.json").write_text(json.dumps(doc), encoding="utf-8")


def test_common_reader_rejects_wrong_digest_oversize_wrong_command_and_missing_file(tmp_path):
    root = tmp_path / "base"
    root.mkdir()
    path = _capture(root, CARDS["thermal_coverage"], [], vendor="ASUS", product="GX10")
    doc_path = path / "capture.json"
    doc = json.loads(doc_path.read_text(encoding="utf-8"))
    assert verify(CARDS["thermal_coverage"], path)["status"] == "unknown"
    doc["captures"][0]["sha256_oracle"]["stdout"] = "0" * 64 + "  host.json\n"
    doc_path.write_text(json.dumps(doc), encoding="utf-8")
    assert verify(CARDS["thermal_coverage"], path)["status"] == "fail"
    doc["captures"][0]["sha256_oracle"]["stdout"] = hashlib.sha256((path / "host.json").read_bytes()).hexdigest() + "  host.json\n"
    doc["captures"][0]["command"] = ["bash", "-c", "uname"]
    doc_path.write_text(json.dumps(doc), encoding="utf-8")
    assert verify(CARDS["thermal_coverage"], path)["status"] == "unknown"
    doc["captures"][0]["command"] = ["python3", "-m", "tools.host_diagnostics"]
    doc_path.write_text(json.dumps(doc), encoding="utf-8")
    (path / "study.jsonl").write_bytes(b"x" * (8 * 1024 * 1024 + 1))
    assert verify(CARDS["thermal_coverage"], path)["status"] == "unknown"
    assert verify(CARDS["thermal_coverage"], path / "missing.json")["could_not_run_count"] == 1


def test_capture_schema_path_digest_and_process_failures_are_classified(tmp_path):
    cases = (
        ("top-level-array", lambda doc: [doc], "unknown"),
        ("wrong-card", lambda doc: {**doc, "card_id": CARDS["usb"]}, "fail"),
        ("unknown-schema", lambda doc: {**doc, "schema": 2}, "unknown"),
        ("captures-missing", lambda doc: {**doc, "captures": None}, "unknown"),
        ("capture-row-type", lambda doc: {**doc, "captures": ["not a capture record"]}, "unknown"),
        ("escaping-artifact", lambda doc: _mutate_capture(doc, 0, artifact="../outside.json"), "fail"),
        ("shell-argv", lambda doc: _mutate_capture(doc, 0, command=["bash", "-c", "uname"]), "unknown"),
        ("failed-collector", lambda doc: _mutate_capture(doc, 0, returncode=2), "unknown"),
    )
    for name, mutate, expected in cases:
        case_dir = tmp_path / name
        path = _capture(case_dir, CARDS["thermal_coverage"], [], vendor="ASUS", product="GX10")
        doc = json.loads((path / "capture.json").read_text(encoding="utf-8"))
        (path / "capture.json").write_text(json.dumps(mutate(doc)), encoding="utf-8")
        result = verify(CARDS["thermal_coverage"], path)
        assert result["status"] == expected, (name, result)
        assert result["could_not_run_count"] == (1 if expected == "unknown" else 0)


def _mutate_capture(document: dict, index: int, **changes) -> dict:
    modified = json.loads(json.dumps(document))
    modified["captures"][index].update(changes)
    return modified


def _replace_capture_artifact(path: Path, name: str, payload: bytes) -> None:
    doc = json.loads((path / "capture.json").read_text(encoding="utf-8"))
    row = next(item for item in doc["captures"] if item["name"] == name)
    artifact = path / row["artifact"]
    artifact.write_bytes(payload)
    row["sha256_oracle"]["stdout"] = f"{hashlib.sha256(payload).hexdigest()}  {row['artifact']}\n"
    (path / "capture.json").write_text(json.dumps(doc), encoding="utf-8")


def test_bounded_reader_handles_oversize_symlink_missing_unicode_and_bad_oracle(tmp_path):
    too_big = tmp_path / "oversized.json"
    too_big.write_bytes(b" " * (8 * 1024 * 1024 + 1))
    assert verify(CARDS["usb"], too_big)["status"] == "unknown"
    nested = tmp_path / "deeply-nested.json"
    nested.write_text("[" * 2000 + "0" + "]" * 2000, encoding="utf-8")
    assert verify(CARDS["usb"], nested)["status"] == "unknown"
    target = tmp_path / "target.json"
    target.write_text("{}", encoding="utf-8")
    alias = tmp_path / "alias.json"
    alias.symlink_to(target)
    assert verify(CARDS["usb"], alias)["status"] == "unknown"

    path = _capture(tmp_path / "artifacts", CARDS["thermal_coverage"], [], vendor="ASUS", product="GX10")
    doc = json.loads((path / "capture.json").read_text(encoding="utf-8"))
    doc["captures"][0]["sha256_oracle"]["command"] = ["sha256sum", "host.json"]
    doc["captures"][0]["sha256_oracle"]["returncode"] = 1
    (path / "capture.json").write_text(json.dumps(doc), encoding="utf-8")
    assert verify(CARDS["thermal_coverage"], path)["status"] == "unknown"
    _replace_capture_artifact(path, "host_diagnostics", b"\xff")
    assert verify(CARDS["thermal_coverage"], path)["status"] == "unknown"
    doc = json.loads((path / "capture.json").read_text(encoding="utf-8"))
    doc["captures"][0]["sha256_oracle"]["command"] = ["sha256sum", "host.json"]
    doc["captures"][0]["sha256_oracle"]["returncode"] = 0
    doc["captures"][0]["sha256_oracle"]["stdout"] = f"{hashlib.sha256(b'\xff').hexdigest()}  host.json\n"
    (path / "capture.json").write_text(json.dumps(doc), encoding="utf-8")
    assert verify(CARDS["thermal_coverage"], path)["status"] == "unknown"


def test_identity_capture_contradictions_fail_and_missing_details_remain_unknown(tmp_path):
    path = _capture(tmp_path / "identity", CARDS["display"], [], vendor="Dell", product="Other")
    result = verify(CARDS["display"], path)
    assert result["status"] == "fail"
    assert "OEM" in result["findings"][0] or "product" in result["findings"][0]

    doc_path = path / "capture.json"
    doc = json.loads(doc_path.read_text(encoding="utf-8"))
    doc.pop("card_id")
    doc_path.write_text(json.dumps(doc), encoding="utf-8")
    result = verify(CARDS["display"], path)
    assert result["status"] == "unknown" and result["could_not_run_count"] == 1
    doc["card_id"] = CARDS["display"]
    doc["captures"] = doc["captures"][:1]
    doc_path.write_text(json.dumps(doc), encoding="utf-8")
    result = verify(CARDS["display"], path)
    assert result["status"] == "unknown" and result["could_not_run_count"] == 1


def test_raw_measurement_helpers_classify_malformed_values_and_policy_edges():
    from tools.hardware_batch03_controls import (
        MissingEvidence,
        _dew_point,
        _findmnt_targets,
        _finite_number,
        _native_result,
        _ordered_samples,
        _need_fields,
        _parse_oem_limits,
        _rollback_complete,
        _run_index,
    )

    with pytest.raises(MissingEvidence):
        _finite_number(True, "temperature")
    with pytest.raises(MissingEvidence):
        _finite_number(float("nan"), "temperature")
    with pytest.raises(MissingEvidence, match="raw fields absent"):
        _need_fields({"present": True}, ("present", "absent"), "sample")
    with pytest.raises(MissingEvidence):
        _ordered_samples({"samples": []}, "empty")
    with pytest.raises(MissingEvidence):
        _ordered_samples({"samples": [{"timestamp_ns": 1}, {"timestamp_ns": True}], "boot_id": "b"}, "bool timestamp")
    with pytest.raises(MissingEvidence, match="boot identity"):
        _ordered_samples({"samples": [{"timestamp_ns": 1}, {"timestamp_ns": 2}]}, "no boot")
    with pytest.raises(ValueError):
        _ordered_samples({"samples": [{"timestamp_ns": 2}, {"timestamp_ns": 2}], "boot_id": "b"}, "duplicate time")
    with pytest.raises(ValueError):
        _run_index([{"case": "same"}, {"case": "same"}])
    with pytest.raises(MissingEvidence):
        _native_result({}, "findmnt")
    with pytest.raises(MissingEvidence):
        _native_result({"native_commands": {"findmnt": {"argv": ["sh", "-c", "findmnt"]}}}, "findmnt")
    with pytest.raises(MissingEvidence):
        _native_result({"native_commands": {"findmnt": {"argv": ["findmnt"], "returncode": False,
            "stdout": "{}", "stderr": ""}}}, "findmnt")
    with pytest.raises(MissingEvidence, match="must come from findmnt"):
        _native_result({"native_commands": {"findmnt": {"argv": ["cat", "findmnt.json"], "returncode": 0,
            "stdout": "{}", "stderr": ""}}}, "findmnt")
    with pytest.raises(MissingEvidence):
        _findmnt_targets("not-json")
    with pytest.raises(MissingEvidence):
        _findmnt_targets("{}")
    with pytest.raises(MissingEvidence):
        _findmnt_targets('{"filesystems": [null]}')
    with pytest.raises(MissingEvidence):
        _parse_oem_limits("gpu_max_c=80\n")
    with pytest.raises(MissingEvidence, match="empty"):
        _parse_oem_limits("")
    with pytest.raises(ValueError):
        _dew_point(20, 0)
    assert _rollback_complete({"x": {"configuration_before": {"a": "a"*64},
        "configuration_after": {"a": "b"*64}}}, ("x",)) is False
    assert _rollback_complete({"x": {"configuration_before": {}, "configuration_after": {}}}, ("x",)) is False
    assert _rollback_complete({"x": {"configuration_before": {"a": "A"*64},
        "configuration_after": {"a": "A"*64}}}, ("x",)) is False


def test_capture_index_rejects_duplicate_names_oracle_tampering_and_raw_capture_failures(tmp_path):
    from tools.hardware_batch03_controls import MissingEvidence, _capture_index, _capture_record

    path = _capture(tmp_path, CARDS["thermal_coverage"], [], vendor="ASUS", product="GX10")
    doc = json.loads((path / "capture.json").read_text(encoding="utf-8"))
    with pytest.raises(ValueError, match="unique"):
        _capture_index([doc["captures"][0], doc["captures"][0]], path)
    with pytest.raises(MissingEvidence, match="receipt missing"):
        _capture_record({"command": ["cat"], "returncode": 0, "stderr": "", "artifact": "host.json"},
                        "host_diagnostics", path)
    host_bytes = (path / "host.json").read_bytes()
    host_digest = hashlib.sha256(host_bytes).hexdigest()
    valid_oracle = {"command": ["sha256sum", "host.json"], "returncode": 0,
        "stdout": f"{host_digest}  host.json\n"}
    bad_code = {"command": ["cat"], "returncode": 1, "stderr": "denied", "artifact": "host.json",
        "sha256_oracle": valid_oracle}
    with pytest.raises(MissingEvidence, match="returned 1"):
        _capture_record(bad_code, "host_diagnostics", path)
    oracle_mismatch = {**bad_code, "returncode": 0,
        "sha256_oracle": {**valid_oracle, "stdout": "0" * 64 + "  host.json\n"}}
    with pytest.raises(ValueError, match="does not match"):
        _capture_record(oracle_mismatch, "host_diagnostics", path)
    with pytest.raises(ValueError, match="escapes"):
        _capture_record({**oracle_mismatch, "artifact": "../host.json"}, "host_diagnostics", path)
    (path / "alias.json").symlink_to(path / "host.json")
    with pytest.raises(ValueError, match="symlink"):
        _capture_record({**oracle_mismatch, "artifact": "alias.json"}, "host_diagnostics", path)


def test_oem_limit_document_parser_rejects_malformed_duplicate_and_nonfinite_values():
    from tools.hardware_batch03_controls import MissingEvidence, _parse_oem_limits

    valid = "gpu_max_c=90\ncpu_max_c=95\npsu_zone_max_c=75\nwall_power_max_w=400\n"
    parsed = _parse_oem_limits(valid)
    assert parsed["gpu_max_c"] == 90
    for source in (
        "gpu_max_c=90\ncpu_max_c=95\npsu_zone_max_c=75\n",
        "gpu_max_c=nan\ncpu_max_c=95\npsu_zone_max_c=75\nwall_power_max_w=400\n",
        "gpu_max_c=90\ncpu_max_c=95\npsu_zone_max_c=75\nwall_power_max_w=400\ngpu_max_c=120\n",
        "gpu_max_c=90,\ncpu_max_c=95\npsu_zone_max_c=75\nwall_power_max_w=400\n",
    ):
        with pytest.raises(MissingEvidence):
            _parse_oem_limits(source)


def test_capture_identity_and_native_findmnt_shapes_remain_fail_closed(tmp_path):
    from tools.hardware_batch03_controls import MissingEvidence, _capture_index, _findmnt_targets, _target_context

    path = _capture(tmp_path, CARDS["thermal_coverage"], [], vendor="ASUS", product="GX10")
    doc = json.loads((path / "capture.json").read_text(encoding="utf-8"))
    captures = _capture_index(doc["captures"], path)
    host = json.loads(captures["host_diagnostics"]["text"])
    host["identity"]["kernel_release"] = "different-kernel"
    (path / "host.json").write_text(json.dumps(host), encoding="utf-8")
    _replace_capture_artifact(path, "host_diagnostics", (path / "host.json").read_bytes())
    captures = _capture_index(json.loads((path / "capture.json").read_text(encoding="utf-8"))["captures"], path)
    with pytest.raises(ValueError, match="different running stacks"):
        _target_context(captures)
    with pytest.raises(MissingEvidence):
        _findmnt_targets('{"filesystems": "bad-shape"}')


def test_capture_schema_and_error_classification_for_incomplete_native_records(tmp_path):
    from tools.hardware_batch03_controls import (
        MissingEvidence,
        _capture_index,
        _capture_record,
        _evaluate_document,
        _json_capture,
        _validate_document_identity,
    )

    unsupported = _validate_document_identity("unrecognized-card", {})
    assert unsupported is not None and unsupported["status"] == "fail"
    path = _capture(tmp_path, CARDS["thermal_coverage"], [], vendor="ASUS", product="GX10")
    assert verify("unsupported-id", path)["status"] == "fail"
    mismatched = _validate_document_identity(CARDS["usb"], {"card_id": "different"})
    assert mismatched is not None and mismatched["status"] == "fail"
    for captures in (None, [], [None], [{"name": 9}], [{"name": "host_diagnostics"}]):
        with pytest.raises(MissingEvidence):
            _capture_index(captures, path)
    doc = json.loads((path / "capture.json").read_text(encoding="utf-8"))
    changed_host = _mutate_capture(doc, 0, command=["other", "collector"])
    with pytest.raises(ValueError, match="host_diagnostics collector"):
        _capture_index(changed_host["captures"], path)
    assert _evaluate_document(CARDS["thermal_coverage"], {"captures": None}, path)["status"] == "unknown"
    with pytest.raises(MissingEvidence, match="malformed or missing"):
        _json_capture({"broken": {"text": "{"}}, "broken")
    doc = json.loads((path / "capture.json").read_text(encoding="utf-8"))
    assert _evaluate_document("non-routed-card", doc, path)["status"] == "unknown"
    changed_thermal = _mutate_capture(doc, 1, command=["cat", "thermal.json"])
    with pytest.raises(ValueError, match="thermal_coverage collector"):
        _capture_index(changed_thermal["captures"], path)
    with pytest.raises(MissingEvidence, match="artifact path missing"):
        _capture_record({"command": ["cat"], "returncode": 0, "stderr": ""}, "missing-artifact", path)


def test_native_raw_artifact_and_oracle_incompleteness_remain_unknown(tmp_path):
    from tools.hardware_batch03_controls import MissingEvidence, _capture_record

    path = _capture(tmp_path, CARDS["thermal_coverage"], [], vendor="ASUS", product="GX10")
    base = {"command": ["cat", "absent"], "returncode": 0, "stderr": "", "artifact": "absent.txt",
        "sha256_oracle": {"command": ["sha256sum", "absent.txt"], "returncode": 0, "stdout": ""}}
    with pytest.raises(MissingEvidence, match="unreadable"):
        _capture_record(base, "study", path)
    malformed_oracle = {**base, "artifact": "host.json", "sha256_oracle": {"command": ["sha256sum"], "returncode": 0}}
    with pytest.raises(MissingEvidence, match="oracle command/result"):
        _capture_record(malformed_oracle, "host_diagnostics", path)
    malformed_result = {**malformed_oracle, "sha256_oracle": None}
    with pytest.raises(MissingEvidence, match="receipt missing"):
        _capture_record(malformed_result, "host_diagnostics", path)
    with pytest.raises(MissingEvidence, match="process result/stderr"):
        _capture_record({"command": ["cat"], "returncode": True, "stderr": "", "artifact": "host.json"},
                        "host_diagnostics", path)


def test_card_specific_case_sets_fail_closed_before_partial_studies_can_pass():
    from tools.hardware_batch03_controls import (
        MissingEvidence,
        _backup_mount,
        _display_carveout,
        _gx10_cable,
        _subambient,
        _thermal_coverage,
    )

    incomplete = {"study": {"text": '{"case":"incomplete"}\n'}}
    with pytest.raises(MissingEvidence, match="synchronized soak"):
        _thermal_coverage({}, incomplete, {"identity": {"architecture": "aarch64", "sys_vendor": "ASUS",
            "product_name": "GX10"}})
    with pytest.raises(MissingEvidence, match="post-boot mounted identity"):
        _backup_mount({}, incomplete, {})
    with pytest.raises(MissingEvidence, match="reproduced 6K failure"):
        _display_carveout({}, incomplete, {"identity": {"architecture": "aarch64", "sys_vendor": "GIGABYTE",
            "product_name": "AI TOP ATOM"}})
    with pytest.raises(MissingEvidence, match="original/candidate SoC"):
        _gx10_cable({}, incomplete, {"identity": {"architecture": "aarch64", "sys_vendor": "ASUS",
            "product_name": "GX10"}})
    wrong_subambient_subject = _subambient({}, incomplete, {"identity": {"architecture": "aarch64", "product_name": "Other"}})
    assert wrong_subambient_subject["status"] == "fail"
    with pytest.raises(MissingEvidence, match="matched baseline"):
        _subambient({}, incomplete, {"identity": {"architecture": "aarch64", "product_name": "GB10"}})


def test_thermal_coverage_event_sensor_and_staleness_predicates_are_distinct():
    from tools.hardware_batch03_controls import (
        MissingEvidence,
        _thermal_negative,
        _validate_event_classes,
        _validate_sensor_sources,
        _validate_stale_sensor,
    )

    with pytest.raises(MissingEvidence, match="coverage matrix"):
        _validate_sensor_sources([])
    with pytest.raises(MissingEvidence, match="rows must be objects"):
        _validate_sensor_sources([None])
    _validate_sensor_sources([{"source": "fan0", "status": "absent", "unit": "rpm", "freshness_ns": None}])
    with pytest.raises(ValueError, match="unique"):
        _validate_sensor_sources([
            {"source": "fan0", "status": "absent", "unit": "rpm", "freshness_ns": None},
            {"source": "fan0", "status": "unreadable", "unit": "rpm", "freshness_ns": None},
        ])
    with pytest.raises(MissingEvidence, match="capability"):
        _validate_sensor_sources([{"source": "fan0", "status": "unknown", "unit": "rpm", "freshness_ns": None}])
    with pytest.raises(MissingEvidence, match="freshness age"):
        _validate_sensor_sources([{"source": "fan0", "status": "observed", "unit": "rpm", "freshness_ns": True}])
    incomplete = {"thermal_control": {}, "oom_control": {}, "power_cut_control": {}}
    with pytest.raises(MissingEvidence, match="literal journal"):
        _validate_event_classes(incomplete)
    controls = {"thermal_control": {"journal_text": "thermal slowdown"},
        "oom_control": {"journal_text": "Out of memory: Killed process 4"},
        "power_cut_control": {"journal_text": "power cut", "independent_capture_command": ["power-recorder", "read"]}}
    controls["thermal_control"]["journal_text"] = "ordinary message"
    event_failure = _validate_event_classes(controls)
    assert event_failure is not None and event_failure["status"] == "fail"
    controls["thermal_control"]["journal_text"] = "thermal slowdown"
    assert _validate_event_classes(controls) is None
    controls["power_cut_control"].pop("independent_capture_command")
    with pytest.raises(MissingEvidence, match="independent instrument"):
        _validate_event_classes(controls)
    controls["power_cut_control"]["independent_capture_command"] = "power-recorder"
    with pytest.raises(MissingEvidence, match="independent instrument"):
        _validate_event_classes(controls)
    soak = {"samples": [{"timestamp_ns": 1000}]}
    stale = {"sample_time_ns": 0, "observed_at_ns": 10, "max_freshness_ns": 5, "sensor_value_raw": "92"}
    assert _validate_stale_sensor(stale, soak) is None
    with pytest.raises(MissingEvidence, match="raw integer"):
        _validate_stale_sensor({**stale, "sample_time_ns": True}, soak)
    with pytest.raises(MissingEvidence, match="old raw sensor value"):
        _validate_stale_sensor({**stale, "sensor_value_raw": " "}, soak)
    stale_failure = _validate_stale_sensor({**stale, "max_freshness_ns": 10}, soak)
    assert stale_failure is not None and stale_failure["status"] == "fail"
    with pytest.raises(MissingEvidence, match="time-correlated"):
        _validate_stale_sensor({**stale, "observed_at_ns": 2000}, soak)
    thermal_failure = _thermal_negative({"baseline_ambient_c": 20, "candidate_ambient_c": 20,
        "baseline_workload_id": "a", "candidate_workload_id": "a"})
    assert thermal_failure is not None and thermal_failure["status"] == "fail"
    assert _thermal_negative({"baseline_ambient_c": 20, "candidate_ambient_c": 25,
        "baseline_workload_id": "a", "candidate_workload_id": "b"}) is None


def test_target_context_requires_consistent_raw_host_and_dmi_identity():
    from tools.hardware_batch03_controls import MissingEvidence, _subject, _target_context

    host = {"schema": 1, "identity": {"kernel_release": "k1", "architecture": "aarch64"}}
    dmi = {key: {"status": "ok", "value": value} for key, value in {
        "sys_vendor": "ASUS", "product_name": "GX10", "product_version": "1", "board_name": "b"}.items()}
    thermal = {"schema": 1, "status": "observed", "host": {"system": "Linux", "release": "k1",
        "machine": "aarch64", "dmi": dmi}}

    def captures(host_record=host, thermal_record=thermal):
        return {"host_diagnostics": {"text": json.dumps(host_record), "sha256": "a"},
            "thermal_coverage": {"text": json.dumps(thermal_record), "sha256": "b"},
            "study": {"sha256": "c"}}

    good = _target_context(captures())
    assert _subject(good, vendor="ASUS", product="GX10") is None
    wrong_arch = _subject(good, arch="x86_64")
    assert wrong_arch is not None and wrong_arch["status"] == "fail"
    wrong_product = _subject(good, product="different-SKU")
    assert wrong_product is not None and wrong_product["status"] == "fail"
    with pytest.raises(MissingEvidence, match="JSON objects"):
        _target_context({"host_diagnostics": {"text": "[]"}, "thermal_coverage": {"text": "{}"}})
    with pytest.raises(ValueError, match="schema mismatch"):
        _target_context(captures({**host, "schema": 2}))
    with pytest.raises(MissingEvidence, match="identity captures"):
        _target_context(captures({"schema": 1}, thermal))
    with pytest.raises(MissingEvidence, match="lacks kernel_release"):
        _target_context(captures({"schema": 1, "identity": {"architecture": "aarch64"}}, thermal))
    bad_dmi = {**dmi, "board_name": {"status": "error", "value": ""}}
    with pytest.raises(MissingEvidence, match="DMI board_name"):
        _target_context(captures(host, {**thermal, "host": {**thermal["host"], "dmi": bad_dmi}}))
    with pytest.raises(MissingEvidence, match="Linux sensor inventory"):
        _target_context(captures(host, {**thermal, "status": "unknown"}))
    with pytest.raises(MissingEvidence, match="Linux sensor inventory"):
        _target_context(captures(host, {**thermal, "host": {**thermal["host"], "system": "Other"}}))


def test_exact_card_router_refuses_wrong_subject_before_evaluating_study(tmp_path):
    path = _capture(tmp_path, CARDS["thermal_coverage"], [], vendor="Dell Inc.", product="Other")
    assert verify("unknown-generated-id", path)["status"] == "fail"
    for key in ("thermal_aux", "thermal_coverage", "cable"):
        subject_path = _capture(tmp_path / key, CARDS[key], [], vendor="Dell Inc.", product="Other")
        result = verify(CARDS[key], subject_path)
        assert result["status"] == "fail", (key, result)
        assert "OEM" in result["findings"][0]


def test_thermal_sample_limits_and_metadata_are_recomputed_from_numeric_values():
    from tools.hardware_batch03_controls import (
        MissingEvidence,
        _check_thermal_sample,
        _thermal_run_metadata,
    )

    limits: dict[str, float] = {"gpu_max_c": 90, "cpu_max_c": 95, "psu_zone_max_c": 80, "wall_power_max_w": 500}
    sample = {"gpu_c": 80, "cpu_c": 80, "psu_zone_c": 50, "wall_power_w": 200,
        "throttled": False, "shutdown": False}
    assert _check_thermal_sample("run", sample, limits, limits) is None
    hot_failure = _check_thermal_sample("run", {**sample, "gpu_c": 91}, limits, limits)
    assert hot_failure is not None and hot_failure["status"] == "fail"
    throttle_failure = _check_thermal_sample("run", {**sample, "throttled": True}, limits, limits)
    assert throttle_failure is not None and throttle_failure["status"] == "fail"
    with pytest.raises(MissingEvidence, match="disagrees"):
        _check_thermal_sample("run", sample, limits, {**limits, "gpu_max_c": 91})
    context = {"identity": {"kernel_release": "kernel-a"}}
    metadata = {"workload_id": "a"*64, "ambient_c": 21, "ambient_source": "probe-serial",
        "kernel_release": "kernel-a", "driver_version": "580", "firmware_version": "7.6",
        "oem_limits": {}, "samples": [], "configuration_sha256": "c"*64}
    assert _thermal_run_metadata("baseline", metadata, context)[0] == "a"*64
    with pytest.raises(MissingEvidence, match="workload identity"):
        _thermal_run_metadata("baseline", {**metadata, "workload_id": "unknown"}, context)
    with pytest.raises(MissingEvidence, match="kernel, driver and firmware"):
        _thermal_run_metadata("baseline", {**metadata, "driver_version": " "}, context)
    with pytest.raises(MissingEvidence, match="ambient measurement source"):
        _thermal_run_metadata("baseline", {**metadata, "ambient_source": " "}, context)


def test_thermal_profile_requires_bound_native_oem_document_bytes():
    from tools.hardware_batch03_controls import MissingEvidence, _thermal_profile

    run = {"boot_id": "boot-a", "samples": [{"timestamp_ns": 1}, {"timestamp_ns": 2}],
        "oem_limits": {"stack_sha256": "stack-hash", "document_sha256": "doc-hash"},
        "configuration_sha256": "a"*64}
    context = {"identity": {"thermal_capture_sha256": "stack-hash"}}
    with pytest.raises(MissingEvidence, match="raw OEM limit document capture"):
        _thermal_profile("run", run, context, {})
    with pytest.raises(MissingEvidence, match="not bound to the captured OEM document"):
        _thermal_profile("run", run, context, {"oem_limits_doc": {"sha256": "other", "text": ""}})


def test_usb_member_identity_speed_and_decision_edges():
    from tools.hardware_batch03_controls import MissingEvidence, _usb_case_policy, _usb_case_result, _usb_member_observations

    member = {"uuid": "u1", "serial": "s1", "sysfs_speed_raw": "20000"}
    assert _usb_member_observations([member], "case") == ([20000], {("u1", "s1")}, False)
    assert _usb_member_observations([member, member], "case")[2] is True
    with pytest.raises(MissingEvidence, match="member rows"):
        _usb_member_observations([None], "case")
    with pytest.raises(MissingEvidence, match="stable UUID"):
        _usb_member_observations([{**member, "uuid": " "}], "case")
    with pytest.raises(MissingEvidence, match="malformed raw"):
        _usb_member_observations([{**member, "sysfs_speed_raw": "480Mbps"}], "case")
    with pytest.raises(MissingEvidence, match="integer Mbps"):
        _usb_member_observations([{**member, "sysfs_speed_raw": "480.5"}], "case")
    assert _usb_member_observations([{**member, "sysfs_speed_raw": None}], "case")[0] == [None]
    doc = {"expected_members": [{"uuid": "u1", "serial": "s1"}]}
    healthy = {"speeds": [20000], "pairs": {("u1", "s1")}, "assembled": True, "mounted": True}
    assert _usb_case_policy("healthy_boot_a", healthy, 5000, doc) is None
    healthy_failure = _usb_case_policy("healthy_boot_a", {**healthy, "mounted": False}, 5000, doc)
    assert healthy_failure is not None and healthy_failure["status"] == "fail"
    slow = {"speeds": [480], "pairs": set(), "assembled": False, "mounted": False}
    assert _usb_case_policy("slow_link", slow, 5000, doc) is None
    no_slow_measurement = _usb_case_policy("slow_link", {**slow, "speeds": [20000]}, 5000, doc)
    assert no_slow_measurement is not None and no_slow_measurement["status"] == "fail"
    slow_failure = _usb_case_policy("slow_link", {**slow, "assembled": True}, 5000, doc)
    assert slow_failure is not None and slow_failure["status"] == "fail"
    assert _usb_case_policy("missing_speed", {**slow, "speeds": [None]}, 5000, doc) is None
    no_speed_failure = _usb_case_policy("missing_speed", slow, 5000, doc)
    assert no_speed_failure is not None and no_speed_failure["status"] == "fail"
    with pytest.raises(MissingEvidence, match="expected per-member"):
        _usb_case_policy("negative_identity_swap", {**slow, "pairs": set()}, 5000, {})
    assert _usb_case_policy("negative_identity_swap", {**healthy, "pairs": {("u2", "s2")},
        "assembled": False, "mounted": False}, 5000, doc) is None
    native = {"mdadm_detail": {"argv": ["mdadm", "--detail", "/dev/md0"], "returncode": 0,
            "stdout": "Array UUID : array-a\n", "stderr": ""},
        "findmnt": {"argv": ["findmnt", "--json"], "returncode": 0,
            "stdout": json.dumps({"filesystems": [{"target": "/mnt/raid", "uuid": "array-a"}]}), "stderr": ""}}
    raw_run = {"boot_id": "boot-a", "cold_boot": True, "array_uuid": "array-a", "mountpoint": "/mnt/raid",
        "members": [member], "native_commands": native}
    assert _usb_case_result("healthy_boot_a", raw_run, 5000, doc) is None
    with pytest.raises(MissingEvidence, match="cold-boot identity"):
        _usb_case_result("healthy_boot_a", {**raw_run, "cold_boot": False}, 5000, doc)
    with pytest.raises(MissingEvidence, match="raw member"):
        _usb_case_result("healthy_boot_a", {**raw_run, "members": []}, 5000, doc)
    duplicate_result = _usb_case_result("healthy_boot_a", {**raw_run, "members": [member, member]}, 5000, doc)
    assert duplicate_result is not None and duplicate_result["status"] == "fail"



def test_thermal_coverage_capture_uses_existing_collector_shape(tmp_path):
    from tools.thermal_coverage import capture

    root = tmp_path / "rootfs"
    dmi = root / "sys/class/dmi/id"
    dmi.mkdir(parents=True)
    for key, value in {"sys_vendor": "ASUS", "product_name": "GX10", "product_version": "B.1",
                       "board_name": "P4242"}.items():
        (dmi / key).write_text(value, encoding="utf-8")
    thermal_record = capture(root)
    assert thermal_record["host"]["system"] == "Linux"
    assert "system" not in thermal_record
    path = _capture(tmp_path / "evidence", CARDS["thermal_coverage"], [], vendor="ASUS", product="GX10")
    (path / "thermal.json").write_text(json.dumps(thermal_record), encoding="utf-8")
    host = json.loads((path / "host.json").read_text(encoding="utf-8"))
    host["identity"]["kernel_release"] = thermal_record["host"]["release"]
    host["identity"]["architecture"] = thermal_record["host"]["machine"]
    (path / "host.json").write_text(json.dumps(host), encoding="utf-8")
    doc = json.loads((path / "capture.json").read_text(encoding="utf-8"))
    thermal_row = next(row for row in doc["captures"] if row["name"] == "thermal_coverage")
    thermal_row["sha256_oracle"]["stdout"] = f"{hashlib.sha256((path / 'thermal.json').read_bytes()).hexdigest()}  thermal.json\n"
    host_row = next(row for row in doc["captures"] if row["name"] == "host_diagnostics")
    host_row["sha256_oracle"]["stdout"] = f"{hashlib.sha256((path / 'host.json').read_bytes()).hexdigest()}  host.json\n"
    (path / "capture.json").write_text(json.dumps(doc), encoding="utf-8")
    result = verify(CARDS["thermal_coverage"], path)
    assert result["status"] == "unknown", result
    assert "study JSON Lines" in result["findings"][0]


def test_malformed_study_jsonl_is_unknown_not_traceback(tmp_path):
    path = _capture(tmp_path, CARDS["thermal_coverage"], [], vendor="ASUS", product="GX10")
    _replace_study_rows(path, [{"case": "placeholder"}])
    (path / "study.jsonl").write_text("{bad json}\n", encoding="utf-8")
    _refresh_study_oracle(path)
    result = verify(CARDS["thermal_coverage"], path)
    assert result["status"] == "unknown" and result["could_not_run_count"] == 1
    assert "JSON Lines" in result["findings"][0]


def test_cli_reports_malformed_missing_and_symlink_inputs_as_unknown(tmp_path, capsys):
    from tools.hardware_batch03_controls import main

    malformed = tmp_path / "malformed.json"
    malformed.write_text("{", encoding="utf-8")
    assert main(["--id", CARDS["thermal_coverage"], "--evidence", str(malformed)]) == 2
    assert json.loads(capsys.readouterr().out)["could_not_run_count"] == 1
    target = tmp_path / "target.json"
    target.write_text("{}", encoding="utf-8")
    alias = tmp_path / "alias.json"
    alias.symlink_to(target)
    assert main(["--id", CARDS["thermal_coverage"], "--evidence", str(alias)]) == 2
    result = json.loads(capsys.readouterr().out)
    assert result["status"] == "unknown" and result["could_not_run_count"] == 1
    process = subprocess.run([sys.executable, "-m", "tools.hardware_batch03_controls", "--id",
        CARDS["thermal_coverage"], "--evidence", str(alias)], capture_output=True, text=True, check=False)
    assert process.returncode == 2
    assert json.loads(process.stdout)["could_not_run_count"] == 1


def _complete_thermal_coverage_rows() -> list[dict]:
    return [
        {"case": "inference_soak", "workload_id": "work", "boot_id": "boot-a",
         "started_at_utc": "2026-10-04T12:00:00+00:00", "ended_at_utc": "2026-10-04T12:00:03+00:00",
         "firmware": {"channel": "stable", "signature_verification_stdout": "Valid\n", "signature_verification_returncode": 0},
         "samples": [{"timestamp_ns": 10_000, "timestamp_utc": "2026-10-04T12:00:01+00:00", "gpu_c": 90, "acpi_zone_c": 96, "gpu_clock_mhz": 2000, "throttle_counter": 2, "workload_id": "work"},
                     {"timestamp_ns": 11_000, "timestamp_utc": "2026-10-04T12:00:02+00:00", "gpu_c": 90, "acpi_zone_c": 96, "gpu_clock_mhz": 2000, "throttle_counter": 2, "workload_id": "work"}],
         "journal_records": ["thermal slowdown"], "thermal_sources": [{"source": "fan_rpm", "status": "absent", "unit": "rpm", "freshness_ns": None}]},
        {"case": "thermal_control", "boot_id": "boot-b", "started_at_utc": "2026-10-04T12:01:00+00:00",
         "ended_at_utc": "2026-10-04T12:01:10+00:00", "journal_text": "GPU thermal slowdown active"},
        {"case": "oom_control", "boot_id": "boot-c", "started_at_utc": "2026-10-04T12:02:00+00:00",
         "ended_at_utc": "2026-10-04T12:02:10+00:00", "journal_text": "Out of memory: Killed process 10"},
        {"case": "power_cut_control", "boot_id": "boot-d", "started_at_utc": "2026-10-04T12:03:00+00:00",
         "ended_at_utc": "2026-10-04T12:03:10+00:00", "journal_text": "power loss independently captured"},
        {"case": "negative_stale_sensor", "sample_time_ns": 100, "observed_at_ns": 10_000, "max_freshness_ns": 500,
         "sensor_value_raw": "90.0"},
    ]


def test_thermal_coverage_rejects_mixed_classifiers_and_accepts_explicit_sensor_gaps(tmp_path, capsys):
    rows = _complete_thermal_coverage_rows()
    _replace_study_rows(path := _capture(tmp_path, CARDS["thermal_coverage"], rows, vendor="ASUS", product="GX10"), rows)
    result = verify(CARDS["thermal_coverage"], path)
    assert result["status"] == "pass", result
    from tools.hardware_batch03_controls import main
    assert main(["--id", CARDS["thermal_coverage"], "--evidence", str(path)]) == 0
    assert json.loads(capsys.readouterr().out)["status"] == "pass"
    thermal_path = path / "thermal.json"
    collector = json.loads(thermal_path.read_text(encoding="utf-8"))
    collector["could_not_run"] = 1
    collector["status"] = "partial"
    collector["thermal_zones"][0]["temperature"].update(
        {"status": "unreadable", "read": {"status": "error", "error": "permission denied"}})
    thermal_path.write_text(json.dumps(collector), encoding="utf-8")
    capture_doc = json.loads((path / "capture.json").read_text(encoding="utf-8"))
    thermal_row = next(row for row in capture_doc["captures"] if row["name"] == "thermal_coverage")
    thermal_row["sha256_oracle"]["stdout"] = f"{hashlib.sha256(thermal_path.read_bytes()).hexdigest()}  thermal.json\n"
    (path / "capture.json").write_text(json.dumps(capture_doc), encoding="utf-8")
    partial = verify(CARDS["thermal_coverage"], path)
    assert partial["status"] == "unknown" and partial["could_not_run_count"] == 1, partial
    assert any("collector reports could_not_run=1" in finding for finding in partial["findings"])
    assert main(["--id", CARDS["thermal_coverage"], "--evidence", str(path)]) == 2
    cli_partial = json.loads(capsys.readouterr().out)
    assert cli_partial["status"] == "unknown" and cli_partial["could_not_run_count"] == 1
    collector["could_not_run"] = 0
    collector["status"] = "observed"
    collector["thermal_zones"][0]["temperature"].update(
        {"status": "ok", "read": {"status": "ok", "value": "42000"}})
    thermal_path.write_text(json.dumps(collector), encoding="utf-8")
    thermal_row["sha256_oracle"]["stdout"] = f"{hashlib.sha256(thermal_path.read_bytes()).hexdigest()}  thermal.json\n"
    (path / "capture.json").write_text(json.dumps(capture_doc), encoding="utf-8")
    _replace_study_rows(path, rows)
    assert verify(CARDS["thermal_coverage"], path)["status"] == "pass"
    study_rows = [json.loads(line) for line in (path / "study.jsonl").read_text(encoding="utf-8").splitlines()]
    study_rows[0]["thermal_sources"][0]["collector_captured_at_utc"] = "2026-10-04T12:00:01+00:00"
    (path / "study.jsonl").write_text("".join(json.dumps(row) + "\n" for row in study_rows), encoding="utf-8")
    _refresh_study_oracle(path)
    mismatch = verify(CARDS["thermal_coverage"], path)
    assert mismatch["status"] == "unknown" and mismatch["could_not_run_count"] == 1
    _replace_study_rows(path, rows)


def test_thermal_coverage_rejects_bad_event_classifiers_and_stale_sensor(tmp_path, capsys):
    from tools.hardware_batch03_controls import main

    rows = _complete_thermal_coverage_rows()
    path = _capture(tmp_path, CARDS["thermal_coverage"], rows, vendor="ASUS", product="GX10")
    _replace_study_rows(path, rows)
    study_rows = [json.loads(line) for line in (path / "study.jsonl").read_text(encoding="utf-8").splitlines()]
    study_rows[1]["journal_text"] = "Out of memory: Killed process 10"
    (path / "study.jsonl").write_text("".join(json.dumps(row) + "\n" for row in study_rows), encoding="utf-8")
    _refresh_study_oracle(path)
    assert verify(CARDS["thermal_coverage"], path)["status"] == "pass"
    _replace_study_rows(path, rows)
    capture_doc = json.loads((path / "capture.json").read_text(encoding="utf-8"))
    complete_capture_doc = json.loads(json.dumps(capture_doc))
    capture_doc["captures"] = [row for row in capture_doc["captures"] if row["name"] != "power_loss_instrument"]
    (path / "capture.json").write_text(json.dumps(capture_doc), encoding="utf-8")
    missing_instrument = verify(CARDS["thermal_coverage"], path)
    assert missing_instrument["status"] == "unknown" and missing_instrument["could_not_run_count"] == 1
    (path / "capture.json").write_text(json.dumps(complete_capture_doc), encoding="utf-8")
    _replace_study_rows(path, rows)
    rows[2]["subject_host_capture_sha256"] = "f" * 64
    _replace_study_rows(path, rows)
    subject_mismatch = verify(CARDS["thermal_coverage"], path)
    assert subject_mismatch["status"] == "fail", subject_mismatch
    rows[2]["subject_host_capture_sha256"] = next(row for row in complete_capture_doc["captures"]
        if row["name"] == "host_diagnostics")["sha256_oracle"]["stdout"].split()[0]
    _replace_study_rows(path, rows)
    rows[1]["journal_text"] = "Out of memory: Killed process 10"
    _replace_study_rows(path, rows)
    assert verify(CARDS["thermal_coverage"], path)["status"] == "fail"
    assert main(["--id", CARDS["thermal_coverage"], "--evidence", str(path)]) == 1
    assert json.loads(capsys.readouterr().out)["status"] == "fail"
    rows[1]["journal_text"] = "GPU thermal slowdown active"
    rows[0]["firmware"]["signature_verification_stdout"] = "Invalid\n"
    _replace_study_rows(path, rows)
    assert verify(CARDS["thermal_coverage"], path)["status"] == "unknown"
    rows[0]["firmware"]["signature_verification_stdout"] = "Valid\n"
    rows[0]["journal_records"] = []
    _replace_study_rows(path, rows)
    _drop_journal_boot(path, "boot-a")
    assert verify(CARDS["thermal_coverage"], path)["status"] == "unknown"
    rows[0]["journal_records"] = ["sampled"]
    rows[4]["observed_at_ns"] = 200
    _replace_study_rows(path, rows)
    assert verify(CARDS["thermal_coverage"], path)["status"] == "fail"


def test_native_journal_json_rows_are_bound_to_boot_identity_and_capture_window(tmp_path):
    rows = _complete_thermal_coverage_rows()
    path = _capture(tmp_path, CARDS["thermal_coverage"], rows, vendor="ASUS", product="GX10")
    _replace_study_rows(path, rows)
    journal_path = path / "journal.jsonl"
    journal_rows = [json.loads(line) for line in journal_path.read_text(encoding="utf-8").splitlines()]
    journal_rows[1]["_BOOT_ID"] = "unrelated-boot"
    _rewrite_capture_artifact(path, "journal_events", "journal.jsonl",
        "".join(json.dumps(row) + "\n" for row in journal_rows).encode())
    mismatch = verify(CARDS["thermal_coverage"], path)
    assert mismatch["status"] == "fail" and any("different boot" in item for item in mismatch["findings"])

    _replace_study_rows(path, rows)
    journal_rows = [json.loads(line) for line in journal_path.read_text(encoding="utf-8").splitlines()]
    del journal_rows[0]["__REALTIME_TIMESTAMP"]
    _rewrite_capture_artifact(path, "journal_events", "journal.jsonl",
        "".join(json.dumps(row) + "\n" for row in journal_rows).encode())
    malformed = verify(CARDS["thermal_coverage"], path)
    assert malformed["status"] == "unknown" and malformed["could_not_run_count"] == 1

    _replace_study_rows(path, rows)
    study_rows = [json.loads(line) for line in (path / "study.jsonl").read_text(encoding="utf-8").splitlines()]
    del study_rows[1]["subject_host_capture_sha256"]
    (path / "study.jsonl").write_text("".join(json.dumps(row) + "\n" for row in study_rows), encoding="utf-8")
    _refresh_study_oracle(path)
    absent_identity = verify(CARDS["thermal_coverage"], path)
    assert absent_identity["status"] == "unknown" and absent_identity["could_not_run_count"] == 1


def test_journal_query_bounds_and_independent_power_loss_recorder_fail_open_to_unknown(tmp_path):
    rows = _complete_thermal_coverage_rows()
    path = _capture(tmp_path, CARDS["thermal_coverage"], rows, vendor="ASUS", product="GX10")
    _replace_study_rows(path, rows)
    doc = json.loads((path / "capture.json").read_text(encoding="utf-8"))
    journal = next(item for item in doc["captures"] if item["name"] == "journal_events")
    journal["command"][4] = "2026-10-04T12:01:00+00:00"
    (path / "capture.json").write_text(json.dumps(doc), encoding="utf-8")
    out_of_scope = verify(CARDS["thermal_coverage"], path)
    assert out_of_scope["status"] == "unknown" and out_of_scope["could_not_run_count"] == 1

    journal["command"][4] = "2026-10-04T12:00:00+00:00"
    (path / "capture.json").write_text(json.dumps(doc), encoding="utf-8")
    _replace_study_rows(path, rows)
    power_path = path / "power-loss.json"
    power_record = json.loads(power_path.read_text(encoding="utf-8"))
    power_record["observed_at_utc"] = "2026-10-04T12:04:00+00:00"
    _rewrite_capture_artifact(path, "power_loss_instrument", "power-loss.json",
        (json.dumps(power_record) + "\n").encode())
    misplaced = verify(CARDS["thermal_coverage"], path)
    assert misplaced["status"] == "fail" and any("outside" in item for item in misplaced["findings"])


def test_raw_journal_parser_and_window_reject_malformed_or_unbounded_capture(tmp_path):
    from tools.hardware_batch03_controls import (
        MissingEvidence,
        _journal_capture_rows,
        _journal_command_window,
        _journal_rows_in_run_window,
        _parse_utc_interval,
        _parse_utc_point,
        _validate_soak_sample_window,
    )

    record = {"__REALTIME_TIMESTAMP": "1791115201000000", "_BOOT_ID": "boot-a", "MESSAGE": "thermal slowdown"}
    command = ["journalctl", "--no-pager", "--output=json", "--since", "2026-10-04T12:00:00+00:00",
        "--until", "2026-10-04T12:04:00+00:00"]
    capture = {"command": command, "text": json.dumps(record) + "\n"}
    assert _journal_capture_rows({"journal_events": capture}) == [record]
    with pytest.raises(MissingEvidence, match="capture is required"):
        _journal_capture_rows({})
    with pytest.raises(MissingEvidence, match="bounded journalctl JSON argv"):
        _journal_capture_rows({"journal_events": {"command": ["cat", "journal.jsonl"], "text": "{}\n"}})
    with pytest.raises(MissingEvidence, match="valid JSON Lines"):
        _journal_capture_rows({"journal_events": {**capture, "text": "{broken\n"}})
    with pytest.raises(MissingEvidence, match="are absent"):
        _journal_capture_rows({"journal_events": {**capture, "text": ""}})
    with pytest.raises(MissingEvidence, match="decimal __REALTIME_TIMESTAMP"):
        _journal_capture_rows({"journal_events": {**capture, "text": json.dumps({"MESSAGE": "x"})}})
    with pytest.raises(MissingEvidence, match="outside the supported"):
        _journal_capture_rows({"journal_events": {**capture,
            "text": json.dumps({**record, "__REALTIME_TIMESTAMP": "9" * 100})}})

    assert _journal_command_window(["journalctl", "--since=2026-10-04T12:00:00+00:00",
        "--until=2026-10-04T12:04:00+00:00"])[0].minute == 0
    for bad in (None, ["--since", "2026-10-04T12:00:00+00:00"],
                ["--since", "2026-10-04T12:00:00+00:00", "--since", "2026-10-04T12:00:01+00:00",
                 "--until", "2026-10-04T12:04:00+00:00"],
                ["--since=", "--until=2026-10-04T12:04:00+00:00"]):
        with pytest.raises(MissingEvidence):
            _journal_command_window(bad)
    with pytest.raises(MissingEvidence, match="timestamps required"):
        _parse_utc_interval(None, "2026-10-04T12:04:00+00:00", "test")
    with pytest.raises(MissingEvidence, match="malformed"):
        _parse_utc_interval("invalid", "2026-10-04T12:04:00+00:00", "test")
    with pytest.raises(MissingEvidence, match="ordered UTC"):
        _parse_utc_interval("2026-10-04T12:00:00-05:00", "2026-10-04T12:04:00-05:00", "test")
    run = {"boot_id": "boot-a", "started_at_utc": "2026-10-04T12:00:00+00:00",
        "ended_at_utc": "2026-10-04T12:04:00+00:00"}
    with pytest.raises(ValueError, match="different boot"):
        _journal_rows_in_run_window([{**record, "_BOOT_ID": "boot-b"}], run, "test run")
    with pytest.raises(MissingEvidence, match="could not be parsed"):
        _journal_rows_in_run_window([{**record, "__REALTIME_TIMESTAMP": "bad"}], run, "test run")
    with pytest.raises(MissingEvidence, match="boot identity"):
        _journal_rows_in_run_window([record], {**run, "boot_id": ""}, "test run")
    sample = {"timestamp_utc": "2026-10-04T12:00:01+00:00", "boot_id": "boot-a"}
    _validate_soak_sample_window({**run, "samples": [sample, {**sample, "timestamp_utc": "2026-10-04T12:00:02+00:00"}]})
    with pytest.raises(ValueError, match="sample boot id"):
        _validate_soak_sample_window({**run, "samples": [{**sample, "boot_id": "other"}]})
    with pytest.raises(MissingEvidence, match="wall-clock timestamps"):
        _validate_soak_sample_window({**run, "samples": [{"boot_id": "boot-a"}]})
    with pytest.raises(MissingEvidence, match="must be UTC"):
        _validate_soak_sample_window({**run, "samples": [{**sample, "timestamp_utc": "2026-10-04T12:00:01-05:00"}]})
    with pytest.raises(ValueError, match="not strictly increasing"):
        _validate_soak_sample_window({**run, "samples": [sample, sample]})
    with pytest.raises(ValueError, match="outside the declared"):
        _validate_soak_sample_window({**run, "samples": [{**sample, "timestamp_utc": "2026-10-04T12:05:00+00:00"}]})
    with pytest.raises(MissingEvidence, match="UTC timestamp required"):
        _parse_utc_point(None, "test recorder")
    with pytest.raises(MissingEvidence, match="must be UTC"):
        _parse_utc_point("2026-10-04T12:00:00-05:00", "test recorder")


def test_power_loss_recorder_is_separate_and_bound_to_run_boot_and_host():
    from tools.hardware_batch03_controls import MissingEvidence, _power_loss_instrument

    run = {"boot_id": "boot-d", "started_at_utc": "2026-10-04T12:03:00+00:00",
        "ended_at_utc": "2026-10-04T12:03:10+00:00"}
    record = {"event_kind": "power_loss", "observed_at_utc": "2026-10-04T12:03:05+00:00",
        "run_boot_id": "boot-d", "subject_host_capture_sha256": "a" * 64, "instrument_id": "recorder-1"}
    capture = {"command": ["external-recorder", "read-json"], "text": json.dumps(record)}
    assert _power_loss_instrument({"power_loss_instrument": capture}, run, "a" * 64) is None
    with pytest.raises(MissingEvidence, match="separate captured external recorder"):
        _power_loss_instrument({}, run, "a" * 64)
    with pytest.raises(MissingEvidence, match="non-journal command"):
        _power_loss_instrument({"power_loss_instrument": {**capture,
            "command": ["journalctl", "--output=json"]}}, run, "a" * 64)
    with pytest.raises(MissingEvidence, match="one JSON event"):
        _power_loss_instrument({"power_loss_instrument": {**capture, "text": "{"}}, run, "a" * 64)
    with pytest.raises(MissingEvidence, match="must be a JSON object"):
        _power_loss_instrument({"power_loss_instrument": {**capture, "text": "[]"}}, run, "a" * 64)
    mismatch = _power_loss_instrument({"power_loss_instrument": {**capture,
        "text": json.dumps({**record, "event_kind": "ordinary_shutdown"})}}, run, "a" * 64)
    assert mismatch is not None and mismatch["status"] == "fail"
    mismatch = _power_loss_instrument({"power_loss_instrument": {**capture,
        "text": json.dumps({**record, "subject_host_capture_sha256": "b" * 64})}}, run, "a" * 64)
    assert mismatch is not None and mismatch["status"] == "fail"
    with pytest.raises(MissingEvidence, match="identity is absent"):
        _power_loss_instrument({"power_loss_instrument": {**capture,
            "text": json.dumps({**record, "instrument_id": " "})}}, run, "a" * 64)
    with pytest.raises(MissingEvidence, match="timestamp is malformed"):
        _power_loss_instrument({"power_loss_instrument": {**capture,
            "text": json.dumps({**record, "observed_at_utc": "bad"})}}, run, "a" * 64)


def test_thermal_collector_parser_rejects_malformed_or_contradictory_native_records(tmp_path):
    from copy import deepcopy

    from tools.hardware_batch03_controls import (
        MissingEvidence,
        _collector_header,
        _thermal_collector_state,
    )

    path = _capture(tmp_path, CARDS["thermal_coverage"], [], vendor="ASUS", product="GX10")
    good = json.loads((path / "thermal.json").read_text(encoding="utf-8"))
    assert _thermal_collector_state({"thermal": good})["could_not_run"] == 0
    from tools.thermal_coverage import capture

    empty_sensor_capture = capture(tmp_path / "empty-root")
    empty_result = _thermal_collector_state({"thermal": empty_sensor_capture})
    assert empty_result["could_not_run"] == empty_sensor_capture["could_not_run"] > 0
    assert any("no sensor channels" in item for item in empty_result["diagnostics"])

    for key, value, error in (
        ("could_not_run", True, MissingEvidence),
        ("captured_at_utc", "yesterday", MissingEvidence),
        ("captured_at_utc", "2026-02-31T12:00:00+00:00", MissingEvidence),
        ("captured_at_utc", "2026-10-04T12:00:00-05:00", MissingEvidence),
    ):
        malformed = deepcopy(good)
        malformed[key] = value
        with pytest.raises(error):
            _collector_header(malformed)

    malformed = deepcopy(good)
    malformed["status"] = "partial"
    with pytest.raises(ValueError, match="status disagrees"):
        _thermal_collector_state({"thermal": malformed})
    malformed = deepcopy(good)
    malformed.update({"status": "partial", "could_not_run": 1})
    with pytest.raises(ValueError, match="disagrees with raw channel statuses"):
        _thermal_collector_state({"thermal": malformed})
    malformed = deepcopy(good)
    malformed["thermal_zone_scan"]["count"] = 2
    with pytest.raises(ValueError, match="scan count"):
        _thermal_collector_state({"thermal": malformed})
    malformed = deepcopy(good)
    malformed["thermal_zones"][0]["temperature"]["value"] = 43.0
    with pytest.raises(ValueError, match="raw read bytes"):
        _thermal_collector_state({"thermal": malformed})

    with pytest.raises(MissingEvidence, match="device row malformed"):
        _thermal_collector_state({"thermal": {**good, "hwmon": [None]}})
    with pytest.raises(MissingEvidence, match="channel collections"):
        _thermal_collector_state({"thermal": {**good, "thermal_zones": None}})
    with pytest.raises(MissingEvidence, match="scan record malformed"):
        _thermal_collector_state({"thermal": {**good, "hwmon_scan": {"count": True}}})
    with pytest.raises(MissingEvidence, match="status is unknown"):
        _thermal_collector_state({"thermal": {**good, "hwmon_scan": {"status": "mystery", "count": 0}}})


def test_thermal_collector_inventory_and_trippoint_rows_are_recomputed(tmp_path):
    from copy import deepcopy

    from tools.hardware_batch03_controls import MissingEvidence, _thermal_collector_state

    path = _capture(tmp_path, CARDS["thermal_coverage"], [], vendor="ASUS", product="GX10")
    good = json.loads((path / "thermal.json").read_text(encoding="utf-8"))
    malformed = deepcopy(good)
    malformed["no_sensor_detected"] = "false"
    with pytest.raises(MissingEvidence, match="flag malformed"):
        _thermal_collector_state({"thermal": malformed})
    malformed = deepcopy(good)
    malformed["no_sensor_detected"] = True
    with pytest.raises(ValueError, match="no_sensor_detected disagrees"):
        _thermal_collector_state({"thermal": malformed})
    malformed = deepcopy(good)
    malformed["thermal_zone_scan"] = {"status": "no_thermal_zones", "count": 1}
    with pytest.raises(ValueError, match="scan status"):
        _thermal_collector_state({"thermal": malformed})
    malformed = deepcopy(good)
    malformed["thermal_zones"] = [None]
    with pytest.raises(MissingEvidence, match="thermal-zone row malformed"):
        _thermal_collector_state({"thermal": malformed})
    malformed = deepcopy(good)
    malformed["hwmon"] = [{"temperature_inputs": None, "fan_inputs": []}]
    with pytest.raises(MissingEvidence, match="must be an array"):
        _thermal_collector_state({"thermal": malformed})
    malformed = deepcopy(good)
    malformed["hwmon"] = [{"temperature_inputs": [None], "fan_inputs": []}]
    with pytest.raises(MissingEvidence, match="hwmon channel record malformed"):
        _thermal_collector_state({"thermal": malformed})


def test_thermal_collector_trip_points_and_native_hwmon_scans_are_recomputed(tmp_path):
    from copy import deepcopy

    from tools.hardware_batch03_controls import (
        MissingEvidence,
        _collector_channel_index,
        _thermal_collector_state,
    )

    path = _capture(tmp_path, CARDS["thermal_coverage"], [], vendor="ASUS", product="GX10")
    good = json.loads((path / "thermal.json").read_text(encoding="utf-8"))
    malformed = deepcopy(good)
    malformed["thermal_zones"][0]["trip_point_scan"]["count"] = 1
    with pytest.raises(ValueError, match="trip-point scan count"):
        _thermal_collector_state({"thermal": malformed})
    malformed = deepcopy(good)
    malformed["thermal_zones"][0]["trip_points"] = [None]
    malformed["thermal_zones"][0]["trip_point_scan"]["count"] = 1
    with pytest.raises(MissingEvidence, match="trip-point row malformed"):
        _thermal_collector_state({"thermal": malformed})
    malformed = deepcopy(good)
    malformed["thermal_zones"][0]["trip_point_scan"] = None
    with pytest.raises(MissingEvidence, match="trip-point scan record malformed"):
        _thermal_collector_state({"thermal": malformed})
    malformed = deepcopy(good)
    malformed["thermal_zones"][0]["trip_points"] = [{"type": {"status": "ok"}}]
    malformed["thermal_zones"][0]["trip_point_scan"]["count"] = 1
    malformed["thermal_zones"][0]["trip_points"][0]["temperature"] = {"status": "error"}
    malformed["could_not_run"] = 1
    malformed["status"] = "partial"
    state = _thermal_collector_state({"thermal": malformed})
    assert state["could_not_run"] == 1

    device_thermal = deepcopy(good)
    fan_channel = {"path": "/sys/class/hwmon/hwmon0/fan1_input",
        "read": {"status": "ok", "value": "1200"}, "value_raw": 1200,
        "value": 1200, "unit": "rpm", "status": "ok"}
    device_thermal["hwmon"] = [{"name": "hwmon0", "temperature_inputs": [], "fan_inputs": [fan_channel]}]
    device_thermal["hwmon_scan"] = {"status": "ok", "error": None, "count": 1}
    assert _thermal_collector_state({"thermal": device_thermal})["could_not_run"] == 0
    assert _collector_channel_index(device_thermal)[fan_channel["path"]] == fan_channel
    indexed = _collector_channel_index({"thermal_zones": [], "hwmon": [None,
        {"temperature_inputs": [None], "fan_inputs": [fan_channel]}]})
    assert indexed == {fan_channel["path"]: fan_channel}
    with pytest.raises(MissingEvidence, match="UTC"):
        _thermal_collector_state({"thermal": {**good, "captured_at_utc": "2026-10-04T12:00:00-05:00"}})


def test_thermal_collector_channel_values_and_source_bindings_match_capture(tmp_path):
    from tools.hardware_batch03_controls import (
        MissingEvidence,
        _bind_thermal_inventory,
        _bind_thermal_source,
        _collector_channel,
        _collector_channel_index,
    )

    path = _capture(tmp_path, CARDS["thermal_coverage"], [], vendor="ASUS", product="GX10")
    good = json.loads((path / "thermal.json").read_text(encoding="utf-8"))

    diagnostic: list[str] = []
    _collector_channel({"status": "unreadable", "path": "/sys/x"}, diagnostic, "test channel")
    assert diagnostic == ["test channel /sys/x status='unreadable'"]
    with pytest.raises(MissingEvidence, match="raw read/value/unit fields incomplete"):
        _collector_channel({"status": "ok"}, [], "test channel")
    with pytest.raises(MissingEvidence, match="not an integer"):
        _collector_channel({"status": "ok", "path": "/sys/x", "read": {"status": "ok", "value": "bad"},
            "value_raw": 0, "value": 0, "unit": "celsius"}, [], "test channel")
    with pytest.raises(ValueError, match="parsed numeric fields"):
        _collector_channel({"status": "ok", "path": "/sys/x", "read": {"status": "ok", "value": "1000"},
            "value_raw": 1000, "value": 2, "unit": "celsius"}, [], "test channel")
    assert _collector_channel_index({"thermal_zones": [None], "hwmon": [None, {}]}) == {}
    source = {"collector_sha256": "a", "collector_captured_at_utc": "now", "source": "/sys/x",
        "status": "observed", "unit": "celsius", "value_raw": 1, "value": 0.001}
    _bind_thermal_source(source, {"/sys/x": {"status": "ok", "unit": "celsius", "value_raw": 1,
        "value": 0.001}}, "a", "now")
    with pytest.raises(MissingEvidence, match="bind the exact"):
        _bind_thermal_inventory({"thermal_sources": []},
            {"thermal": good, "identity": {"thermal_capture_sha256": "other"}})

    with pytest.raises(MissingEvidence, match="bind collector bytes"):
        _bind_thermal_source({"source": "/sys/x", "status": "observed"}, {}, "a", "now")
    source = {"collector_sha256": "a", "collector_captured_at_utc": "now", "source": "/sys/x",
        "status": "observed", "unit": "celsius", "value_raw": 1, "value": 0.001}
    with pytest.raises(MissingEvidence, match="no readable matching"):
        _bind_thermal_source(source, {}, "a", "now")
    native = {"/sys/x": {"status": "ok", "unit": "celsius", "value_raw": 1, "value": 0.001}}
    with pytest.raises(ValueError, match="disagrees"):
        _bind_thermal_source({**source, "value": 9}, native, "a", "now")
    with pytest.raises(ValueError, match="contradicts"):
        _bind_thermal_source({**source, "status": "absent"}, native, "a", "now")


def test_usb_raid_recomputes_speeds_identity_and_fail_closed_states(tmp_path):
    from tools.hardware_batch03_controls import MissingEvidence, _usb_raid

    def members(speed):
        return [{"uuid": "uuid-a", "serial": "serial-a", "sysfs_speed_raw": speed},
                {"uuid": "uuid-b", "serial": "serial-b", "sysfs_speed_raw": speed}]
    def case(name, boot, speed, assembled):
        return {"case": name, "boot_id": boot, "cold_boot": True, "array_uuid": "md-uuid", "mountpoint": "/mnt/raid",
            "members": members(speed), "native_commands": {
                "mdadm_detail": {"argv": ["mdadm", "--detail", "/dev/md0"], "returncode": 0,
                    "stdout": "Array UUID : md-uuid\n" if assembled else "", "stderr": ""},
                "findmnt": {"argv": ["findmnt", "--json"], "returncode": 0,
                    "stdout": json.dumps({"filesystems": [{"target": "/mnt/raid", "uuid": "md-uuid"}]} if assembled else {"filesystems": []}), "stderr": ""}}}
    rows = [
        case("healthy_boot_a", "boot-a", "20000", True),
        case("healthy_boot_b", "boot-b", "20000", True),
        case("slow_link", "boot-c", "480", False),
        case("missing_speed", "boot-d", None, False),
        case("negative_identity_swap", "boot-e", "20000", False),
        {"case": "rollback", **_rollback()},
    ]
    rows[4]["members"][0]["uuid"] = "uuid-swapped"
    path = _capture(tmp_path, CARDS["usb"], rows, vendor="Dell Inc.", product="DGX Spark GB10")
    doc = json.loads((path / "capture.json").read_text(encoding="utf-8"))
    doc["operator_declared_floor_mbps"] = 5000
    doc["floor_source"] = "operator_or_OEM_recorded"
    doc["expected_members"] = members("20000")
    (path / "capture.json").write_text(json.dumps(doc), encoding="utf-8")
    assert verify(CARDS["usb"], path)["status"] == "pass"
    rows[2]["native_commands"]["findmnt"]["stdout"] = json.dumps({"filesystems": [{"target": "/mnt/raid", "uuid": "md-uuid"}]})
    _replace_study_rows(path, rows)
    assert verify(CARDS["usb"], path)["status"] == "fail"
    rows[2]["native_commands"]["findmnt"]["stdout"] = json.dumps({"filesystems": []})
    _replace_study_rows(path, rows)
    doc = json.loads((path / "capture.json").read_text(encoding="utf-8"))
    doc["operator_declared_floor_mbps"] = 4000
    (path / "capture.json").write_text(json.dumps(doc), encoding="utf-8")
    assert verify(CARDS["usb"], path)["status"] == "unknown"
    rows[1]["boot_id"] = rows[0]["boot_id"]
    _replace_study_rows(path, rows)
    doc = json.loads((path / "capture.json").read_text(encoding="utf-8"))
    doc["operator_declared_floor_mbps"] = 5000
    (path / "capture.json").write_text(json.dumps(doc), encoding="utf-8")
    assert verify(CARDS["usb"], path)["status"] == "unknown"
    rows[1]["boot_id"] = "boot-b"
    rows[4]["members"][0]["uuid"] = "uuid-a"
    _replace_study_rows(path, rows)
    assert verify(CARDS["usb"], path)["status"] == "fail"
    rows[4]["members"][0]["uuid"] = "uuid-swapped"
    rows[5]["configuration_after"]["airflow"] = "d"*64
    _replace_study_rows(path, rows)
    assert verify(CARDS["usb"], path)["status"] == "unknown"
    study_text = (path / "study.jsonl").read_text(encoding="utf-8")
    with pytest.raises(MissingEvidence, match="two cold boots"):
        _usb_raid({}, {"study": {"text": '{"case":"incomplete"}\n'}}, {})
    with pytest.raises(MissingEvidence, match="floor must be explicitly recorded"):
        _usb_raid({}, {"study": {"text": study_text}}, {})


def test_backup_mount_checks_postboot_uuid_and_never_writes_on_negative_mount_cases(tmp_path):
    from tools.hardware_batch03_controls import MissingEvidence, _backup_case

    digest = "a" * 64
    base = {"mountpoint": "/mnt/backup", "expected_source": "/dev/disk/by-id/usb-SanDisk", "expected_uuid": "uuid-good",
        "backup_sha256_before": digest, "backup_sha256_after": digest, "write_attempts": 0}
    mounted = {"filesystems": [{"target": "/mnt/backup", "source": "/dev/disk/by-id/usb-SanDisk", "uuid": "uuid-good"}]}
    wrong = {"filesystems": [{"target": "/mnt/backup", "source": "/dev/disk/by-id/usb-other", "uuid": "uuid-other"}]}
    empty = {"filesystems": []}
    def findmnt(data):
        return {"argv": ["findmnt", "--json", "-o", "TARGET,SOURCE,UUID", "--target", "/mnt/backup"],
            "returncode": 0, "stdout": json.dumps(data), "stderr": ""}
    rows = [{"case": "mounted_after_boot", **base, "boot_id": "boot-after-restart", "backup_read_sha256": digest,
             "native_commands": {"findmnt": findmnt(mounted)}},
        {"case": "missing_device", **base, "native_commands": {"findmnt": findmnt(empty)}},
        {"case": "wrong_uuid", **base, "native_commands": {"findmnt": findmnt(wrong)}},
        {"case": "mountpoint_only", **base, "native_commands": {"findmnt": findmnt(empty)}}]
    path = _capture(tmp_path, CARDS["backup"], rows, vendor="Dell Inc.", product="DGX Spark GB10")
    assert verify(CARDS["backup"], path)["status"] == "pass"
    rows[1]["write_attempts"] = 1
    _replace_study_rows(path, rows)
    assert verify(CARDS["backup"], path)["status"] == "fail"
    rows[1]["write_attempts"] = 0
    rows[1]["native_commands"]["findmnt"]["returncode"] = 1
    _replace_study_rows(path, rows)
    assert verify(CARDS["backup"], path)["status"] == "unknown"
    rows[1]["native_commands"]["findmnt"]["returncode"] = 0
    rows[2]["native_commands"]["findmnt"] = findmnt(mounted)
    _replace_study_rows(path, rows)
    assert verify(CARDS["backup"], path)["status"] == "fail"
    rows[2]["native_commands"]["findmnt"] = findmnt(empty)
    rows[2]["write_attempts"] = True
    _replace_study_rows(path, rows)
    assert verify(CARDS["backup"], path)["status"] == "unknown"
    rows[2]["write_attempts"] = 0
    rows[0]["backup_read_sha256"] = "0"*64
    _replace_study_rows(path, rows)
    assert verify(CARDS["backup"], path)["status"] == "fail"
    with pytest.raises(MissingEvidence, match="different UUID"):
        _backup_case("wrong_uuid", {**rows[2], "native_commands": {"findmnt": findmnt(empty)}})
    blocked_target = {**rows[1], "native_commands": {"findmnt": findmnt(mounted)}}
    mounted_negative = _backup_case("missing_device", blocked_target)
    assert mounted_negative is not None and mounted_negative["status"] == "fail"
    negative_count = {**rows[0], "write_attempts": -1, "backup_read_sha256": digest,
        "native_commands": {"findmnt": findmnt(mounted)}}
    with pytest.raises(ValueError, match="cannot be negative"):
        _backup_case("mounted_after_boot", negative_count)


def test_display_carveout_requires_reproduced_failure_candidate_stability_and_rollback(tmp_path):
    rows = [{"case": "baseline_6k_failure", "resolution": "6K", "scanout_log": "NV_ERR_NO_MEMORY: scanoutcarveout allocation failed",
        "free_memory_bytes": 109 * 1024**3, "driver_version": "580.159.03"}]
    for case in ("candidate_6k", "candidate_4k", "cache_pressure"):
        rows.append({"case": case, "stack_sha256": "", "driver_version": "580.159.03",
            "reserved_bytes_before": 256 * 1024**2, "reserved_bytes_after": 512 * 1024**2,
            "native_commands": {
                "driver_parameter": {"argv": ["journalctl", "--boot", "--kernel", "--no-pager", "--grep=AdjustableDisplayReservedMemory", "--output=cat"], "returncode": 0,
                    "stdout": "AdjustableDisplayReservedMemory=536870912\n", "stderr": ""},
                "sway": {"argv": ["systemctl", "--user", "is-active", "sway.service"], "returncode": 0, "stdout": "active\n", "stderr": ""},
                "ssh": {"argv": ["ssh", "-o", "BatchMode=yes", "localhost", "true"], "returncode": 0, "stdout": "connected\n", "stderr": ""},
                "scanout_log": {"argv": ["journalctl", "--boot", "--output=cat"], "returncode": 0, "stdout": "scanout completed\n", "stderr": ""},
                "window_events": {"argv": ["cat", "window-events.log"], "returncode": 0, "stdout": "open id1\nclose id1\n", "stderr": ""}}})
    rows.append({"case": "rollback", **_rollback()})
    path = _capture(tmp_path, CARDS["display"], rows, vendor="GIGABYTE", product="AI TOP ATOM")
    doc = json.loads((path / "capture.json").read_text(encoding="utf-8"))
    digest = doc["captures"][1]["sha256_oracle"]["stdout"].split()[0]
    for row in rows:
        if row["case"].startswith("candidate") or row["case"] == "cache_pressure":
            row["stack_sha256"] = digest
    _replace_study_rows(path, rows)
    assert verify(CARDS["display"], path)["status"] == "pass"
    capture_doc = json.loads((path / "capture.json").read_text(encoding="utf-8"))
    stack_sha = next(item for item in capture_doc["captures"] if item["name"] == "thermal_coverage")["sha256_oracle"]["stdout"].split()[0]
    _assert_display_candidate_bad_data(rows[1], stack_sha)
    rows[1]["driver_version"] = " "
    _replace_study_rows(path, rows)
    assert verify(CARDS["display"], path)["status"] == "unknown"
    rows[1]["driver_version"] = "580.159.03"
    rows[1]["reserved_bytes_before"] = rows[1]["reserved_bytes_after"]
    _replace_study_rows(path, rows)
    assert verify(CARDS["display"], path)["status"] == "unknown"
    rows[1]["reserved_bytes_before"] = 256 * 1024**2
    rows[1]["native_commands"]["ssh"]["stdout"] = "disconnected\n"
    _replace_study_rows(path, rows)
    assert verify(CARDS["display"], path)["status"] == "fail"
    rows[1]["native_commands"]["ssh"]["stdout"] = "connected\n"
    rows[1]["native_commands"]["window_events"]["stdout"] = "open id1\nclose id2\n"
    _replace_study_rows(path, rows)
    assert verify(CARDS["display"], path)["status"] == "fail"
    rows[1]["native_commands"]["window_events"]["stdout"] = "open id1\nclose id1\n"
    rows[1]["native_commands"]["scanout_log"]["stdout"] = "NV_ERR_NO_MEMORY\n"
    _replace_study_rows(path, rows)
    assert verify(CARDS["display"], path)["status"] == "fail"
    rows[1]["native_commands"]["scanout_log"]["stdout"] = "scanout completed\n"
    rows[1]["native_commands"]["driver_parameter"]["stdout"] = "unsupported\n"
    _replace_study_rows(path, rows)
    assert verify(CARDS["display"], path)["status"] == "unknown"
    rows[1]["native_commands"]["driver_parameter"]["stdout"] = "AdjustableDisplayReservedMemory=536870912\n"
    rows[0]["driver_version"] = "different-version"
    _replace_study_rows(path, rows)
    assert verify(CARDS["display"], path)["status"] == "unknown"
    rows[0]["driver_version"] = "580.159.03"
    rows[4]["configuration_after"]["airflow"] = "d"*64
    _replace_study_rows(path, rows)
    assert verify(CARDS["display"], path)["status"] == "unknown"
    rows[4] = {"case": "rollback", **_rollback()}
    rows[0]["free_memory_bytes"] = 0
    _replace_study_rows(path, rows)
    assert verify(CARDS["display"], path)["status"] == "fail"


def _assert_display_candidate_bad_data(candidate: dict, stack_sha: str) -> None:
    from tools.hardware_batch03_controls import MissingEvidence, _display_candidate

    context = {"identity": {"thermal_capture_sha256": stack_sha}}
    with pytest.raises(MissingEvidence, match="bound to exact OEM stack"):
        _display_candidate("candidate_6k", {**candidate, "stack_sha256": "wrong"}, context)
    with pytest.raises(MissingEvidence, match="raw integer"):
        _display_candidate("candidate_6k", {**candidate, "reserved_bytes_before": -1}, context)
    with pytest.raises(MissingEvidence, match="does not match the measured after value"):
        _display_candidate("candidate_6k", {**candidate, "reserved_bytes_after": 1}, context)


def test_gx10_cable_candidate_requires_functional_link_not_pci_presence(tmp_path):
    rows = [
        {"case": "original_tuple", "soc_version": "3000006", "ec_version": "20000005", "channel": "LVFS testing", "bundle_sha256": "a"*64, "hotplug_state_raw": "hotplug_enabled=1\n"},
        {"case": "candidate_tuple", "soc_version": "3000007", "ec_version": "20000006", "channel": "LVFS testing", "bundle_sha256": "b"*64, "hotplug_state_raw": "hotplug_enabled=1\n", "vendor_approval_ref": "OEM case id"},
        {"case": "cold_reboot", "boot_id": "boot-a", "soc_version": "3000007", "ec_version": "20000006"},
        {"case": "warm_reboot", "boot_id": "boot-b", "soc_version": "3000007", "ec_version": "20000006"},
        {"case": "rollback", **_rollback()},
    ]
    for row in rows[2:4]:
        row["native_commands"] = {
            "pci_inventory": {"argv": ["lspci", "-nn"], "returncode": 0, "stdout": "0001:01:00.0 Ethernet controller\n", "stderr": ""},
            "module_inventory": {"argv": ["lsmod"], "returncode": 0, "stdout": "mlx5_core 12345 1\n", "stderr": ""},
            "carrier": {"argv": ["cat", "/sys/class/net/eth0/carrier"], "returncode": 0, "stdout": "1\n", "stderr": ""},
            "eeprom": {"argv": ["ethtool", "-m", "eth0"], "returncode": 0, "stdout": "Identifier: QSFP28\nVendor name: OEM\n", "stderr": ""},
            "link": {"argv": ["ethtool", "eth0"], "returncode": 0, "stdout": "Speed: 100000Mb/s\nLink detected: yes\n", "stderr": ""},
            "tx_before": {"argv": ["cat", "/sys/class/net/eth0/statistics/tx_bytes"], "returncode": 0, "stdout": "100\n", "stderr": ""},
            "tx_after": {"argv": ["cat", "/sys/class/net/eth0/statistics/tx_bytes"], "returncode": 0, "stdout": "1124\n", "stderr": ""},
            "rx_before": {"argv": ["cat", "/sys/class/net/eth0/statistics/rx_bytes"], "returncode": 0, "stdout": "100\n", "stderr": ""},
            "rx_after": {"argv": ["cat", "/sys/class/net/eth0/statistics/rx_bytes"], "returncode": 0, "stdout": "1124\n", "stderr": ""},
        }
    path = _capture(tmp_path, CARDS["cable"], rows, vendor="ASUSTeK COMPUTER INC.", product="GX10")
    result = verify(CARDS["cable"], path)
    assert result["status"] == "pass", result
    _exercise_cable_adversarial_rows(path, rows)
    wrong_oem = _capture(tmp_path / "wrong-oem", CARDS["cable"], rows,
        vendor="GIGABYTE", product="AI TOP ATOM")
    assert verify(CARDS["cable"], wrong_oem)["status"] == "fail"


def _exercise_cable_adversarial_rows(path: Path, rows: list[dict]) -> None:
    rows[2]["native_commands"]["carrier"]["stdout"] = "0\n"
    _replace_study_rows(path, rows)
    assert verify(CARDS["cable"], path)["status"] == "fail"
    rows[2]["native_commands"]["carrier"]["stdout"] = "1\n"
    rows[2]["native_commands"]["tx_after"]["stdout"] = "100\n"
    _replace_study_rows(path, rows)
    assert verify(CARDS["cable"], path)["status"] == "fail"
    rows[2]["native_commands"]["tx_after"]["stdout"] = "1124\n"
    rows[2]["native_commands"]["pci_inventory"]["stdout"] = ""
    _replace_study_rows(path, rows)
    assert verify(CARDS["cable"], path)["status"] == "fail"
    rows[2]["native_commands"]["pci_inventory"]["stdout"] = "0001:01:00.0 Ethernet controller\n"
    rows[2]["native_commands"]["eeprom"]["stderr"] = "EEPROM unavailable\n"
    _replace_study_rows(path, rows)
    assert verify(CARDS["cable"], path)["status"] == "fail"
    rows[2]["native_commands"]["eeprom"]["stderr"] = ""
    rows[3]["native_commands"]["link"]["stdout"] = "Link detected: no\n"
    _replace_study_rows(path, rows)
    assert verify(CARDS["cable"], path)["status"] == "fail"
    rows[3]["native_commands"]["link"]["stdout"] = "Speed: 100000Mb/s\nLink detected: yes\n"
    rows[3]["native_commands"]["rx_after"]["stdout"] = "unknown\n"
    _replace_study_rows(path, rows)
    assert verify(CARDS["cable"], path)["status"] == "unknown"
    rows[3]["native_commands"]["rx_after"]["stdout"] = "1124\n"
    rows[3]["boot_id"] = rows[2]["boot_id"]
    _replace_study_rows(path, rows)
    assert verify(CARDS["cable"], path)["status"] == "unknown"
    rows[3]["boot_id"] = "boot-b"
    rows[1].pop("vendor_approval_ref")
    _replace_study_rows(path, rows)
    assert verify(CARDS["cable"], path)["status"] == "unknown"
    rows[1]["vendor_approval_ref"] = "OEM case id"
    rows[1]["soc_version"] = rows[0]["soc_version"]
    rows[1]["ec_version"] = rows[0]["ec_version"]
    _replace_study_rows(path, rows)
    assert verify(CARDS["cable"], path)["status"] == "unknown"
    rows[1]["soc_version"] = "3000007"
    rows[1]["ec_version"] = "20000006"
    rows[0]["soc_version"] = " "
    _replace_study_rows(path, rows)
    assert verify(CARDS["cable"], path)["status"] == "unknown"
    rows[0]["soc_version"] = "3000006"
    _exercise_cable_tuple_and_rollback(path, rows)


def _exercise_cable_tuple_and_rollback(path: Path, rows: list[dict]) -> None:
    from tools.hardware_batch03_controls import MissingEvidence, _validate_cable_boot

    candidate = rows[1]
    wrong_tuple = _validate_cable_boot("cold_reboot", {**rows[2], "soc_version": "bad"}, candidate)
    assert wrong_tuple is not None and wrong_tuple["status"] == "fail"
    with pytest.raises(MissingEvidence, match="boot identity"):
        _validate_cable_boot("cold_reboot", {**rows[2], "boot_id": " "}, candidate)
    rows[4]["configuration_after"]["airflow"] = "d"*64
    _replace_study_rows(path, rows)
    assert verify(CARDS["cable"], path)["status"] == "unknown"
    rows[4] = {"case": "rollback", **_rollback()}


def test_subambient_calculates_dewpoint_and_rejects_humidity_unknown(tmp_path):
    def command(argv, output):
        return {"argv": argv, "returncode": 0, "stdout": output, "stderr": ""}
    def run(case, ambient, humidity, surface):
        return {"case": case, "workload_sha256": "a"*64, "stack_sha256": "", "boot_id": "boot-a",
            "airflow_velocity_mps": [0.5, 0.5], "duct_clearance_raw": "unobstructed around intake/exhaust",
            "humidity_samples": [humidity, humidity], "ambient_samples_c": [ambient, ambient],
            "surface_min_samples_c": [surface, surface],
            "samples": [{"timestamp_ns": 1, "sensor_uncertainty_c": 0.2, "gpu_c": 65, "cpu_c": 74, "soc_c": 60,
                "uma_used_bytes": 1000, "throughput": 100, "journal_text": "",
                "native_commands": {"sway": command(["systemctl", "--user", "is-active", "sway.service"], "active\n"),
                    "ssh": command(["ssh", "-o", "BatchMode=yes", "localhost", "true"], "connected\n")}},
                {"timestamp_ns": 2, "sensor_uncertainty_c": 0.2, "gpu_c": 65, "cpu_c": 74, "soc_c": 60,
                "uma_used_bytes": 1000, "throughput": 100, "journal_text": "",
                "native_commands": {"sway": command(["systemctl", "--user", "is-active", "sway.service"], "active\n"),
                    "ssh": command(["ssh", "-o", "BatchMode=yes", "localhost", "true"], "connected\n")}}]}
    rows = [run("baseline", 24, 45, 24), run("subambient_canary", 18, 45, 18),
        {"case": "negative_unknown_humidity", "ambient_c": 18, "humidity_raw": None},
        {"case": "rollback", **_rollback()}]
    path = _capture(tmp_path, CARDS["subambient"], rows, vendor="NVIDIA", product="DGX Spark GB10")
    doc = json.loads((path / "capture.json").read_text(encoding="utf-8"))
    digest = doc["captures"][1]["sha256_oracle"]["stdout"].split()[0]
    for row in rows[:2]:
        row["stack_sha256"] = digest
    _replace_study_rows(path, rows)
    assert verify(CARDS["subambient"], path)["status"] == "pass"
    _exercise_subambient_trial_edges(path, rows)


def _exercise_subambient_trial_edges(path: Path, rows: list[dict]) -> None:
    from tools.hardware_batch03_controls import MissingEvidence, _subambient_run

    capture_doc = json.loads((path / "capture.json").read_text(encoding="utf-8"))
    stack_digest = next(item for item in capture_doc["captures"] if item["name"] == "thermal_coverage")["sha256_oracle"]["stdout"].split()[0]
    context = {"identity": {"thermal_capture_sha256": stack_digest}}
    assert _subambient_run("baseline", rows[0], context)[0] is not None
    with pytest.raises(MissingEvidence, match="stack identity mismatch"):
        _subambient_run("baseline", {**rows[0], "stack_sha256": "wrong"}, context)
    with pytest.raises(MissingEvidence, match="exact workload hash"):
        _subambient_run("baseline", {**rows[0], "workload_sha256": "bad"}, context)
    rows[2]["humidity_raw"] = 45
    _replace_study_rows(path, rows)
    negative_humidity = verify(CARDS["subambient"], path)
    assert negative_humidity["status"] == "fail", negative_humidity
    rows[2]["humidity_raw"] = None
    _replace_study_rows(path, rows)
    rows[3]["configuration_after"]["airflow"] = "d"*64
    _replace_study_rows(path, rows)
    assert verify(CARDS["subambient"], path)["status"] == "unknown"
    rows[3] = {"case": "rollback", **_rollback()}
    _replace_study_rows(path, rows)
    rows[1]["samples"][0]["uma_used_bytes"] = 2000
    _replace_study_rows(path, rows)
    assert verify(CARDS["subambient"], path)["status"] == "fail"
    rows[1]["samples"][0]["uma_used_bytes"] = 1000
    rows[1]["samples"][0]["throughput"] = 90
    _replace_study_rows(path, rows)
    assert verify(CARDS["subambient"], path)["status"] == "fail"
    rows[1]["samples"][0]["throughput"] = 100
    rows[1]["workload_sha256"] = "b"*64
    _replace_study_rows(path, rows)
    assert verify(CARDS["subambient"], path)["status"] == "unknown"
    rows[1]["workload_sha256"] = "a"*64
    rows[1]["airflow_velocity_mps"] = [0.5]
    _replace_study_rows(path, rows)
    assert verify(CARDS["subambient"], path)["status"] == "unknown"
    rows[1]["airflow_velocity_mps"] = [0.5, 0.5]
    rows[1]["duct_clearance_raw"] = " "
    _replace_study_rows(path, rows)
    assert verify(CARDS["subambient"], path)["status"] == "unknown"
    rows[1]["duct_clearance_raw"] = "unobstructed around intake/exhaust"
    rows[1]["samples"][0]["sensor_uncertainty_c"] = -0.1
    _replace_study_rows(path, rows)
    assert verify(CARDS["subambient"], path)["status"] == "fail"
    rows[1]["samples"][0]["sensor_uncertainty_c"] = 0.2
    rows[1]["surface_min_samples_c"] = [5, 5]
    _replace_study_rows(path, rows)
    assert verify(CARDS["subambient"], path)["status"] == "fail"


def test_subambient_safety_rejects_lost_airflow_oom_and_missing_probes(monkeypatch):
    from tools.hardware_batch03_controls import MissingEvidence, _subambient_negative, _subambient_sample_safety

    command = {"argv": ["systemctl", "--user", "is-active", "sway.service"],
        "returncode": 0, "stdout": "active\n", "stderr": ""}
    ssh = {"argv": ["ssh", "-o", "BatchMode=yes", "localhost", "true"],
        "returncode": 0, "stdout": "connected\n", "stderr": ""}
    sample = {"sensor_uncertainty_c": 0.2, "journal_text": "", "native_commands": {"sway": command, "ssh": ssh}}
    conditions = (20, 40, 19, 0.5)
    assert _subambient_sample_safety("canary", sample, conditions) is None
    stopped_flow = _subambient_sample_safety("canary", sample, (20, 40, 19, 0))
    assert stopped_flow is not None and stopped_flow["status"] == "fail"
    condensation = _subambient_sample_safety("canary", sample, (20, 40, 1, 0.5))
    assert condensation is not None and condensation["status"] == "fail"
    with pytest.raises(MissingEvidence, match="journal window"):
        _subambient_sample_safety("canary", {**sample, "journal_text": None}, conditions)
    oom = _subambient_sample_safety("canary", {**sample, "journal_text": "Out of memory: Killed process 8"}, conditions)
    assert oom is not None and oom["status"] == "fail"
    lost_session = _subambient_sample_safety("canary", {**sample, "native_commands": {"sway": command,
        "ssh": {**ssh, "returncode": 1}}}, conditions)
    assert lost_session is not None and lost_session["status"] == "fail"
    invented_humidity = _subambient_negative({"ambient_c": 20, "humidity_raw": 45})
    assert invented_humidity is not None and invented_humidity["status"] == "fail"
    assert _subambient_negative({"ambient_c": 20, "humidity_raw": None}) is None
    monkeypatch.setattr("tools.hardware_batch03_controls._dew_point", lambda _ambient, _humidity: 0.0)
    broken_negative = _subambient_negative({"ambient_c": 20, "humidity_raw": None})
    assert broken_negative is not None and broken_negative["status"] == "fail"
