"""Batch 02 parser and adversarial-control tests; fixtures never represent host closure."""
from __future__ import annotations

import errno
import hashlib
import json
import stat
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import pytest

from tools import hardware_batch02_controls as controls


def _status(result: dict[str, Any] | None) -> str:
    assert result is not None
    return str(result["status"])


@pytest.mark.parametrize("finding_id", controls.IDS)
def test_missing_batch02_capture_is_could_not_run(tmp_path: Path, finding_id: str) -> None:
    result = controls.verify(finding_id, tmp_path)
    assert result["status"] == "unknown", result
    assert result["could_not_run"] == 1
    assert result["fail"] == 0


@pytest.mark.parametrize("value", [True, float("nan"), float("inf"), "12",
                                   pytest.param(10**10000, id="integer-overflow")])
def test_numeric_parser_rejects_nonfinite_boolean_and_strings(value: object) -> None:
    assert controls._finite(value) is None


def test_native_output_parsers_reject_missing_and_malformed_identity_data(tmp_path: Path) -> None:
    path = tmp_path / "commands.json"
    dmi = {"argv": ["dmidecode", "-t", "system"], "exit": 0,
           "stdout": "Manufacturer: ACME\nProduct Name: Board\nBIOS Version: 1\n", "stderr": ""}
    kernel = {"argv": ["uname", "-r"], "exit": 0, "stdout": "6.17\n", "stderr": ""}
    identity, error = controls._identity({"commands": [dmi, kernel]}, path)
    assert error is None and identity == {"Manufacturer": "ACME", "Product Name": "Board",
                                         "BIOS Version": "1", "Kernel": "6.17"}
    for rows, phrase in (([kernel], "required raw command missing"),
                         ([{**dmi, "exit": 127}, kernel], "required command failed"),
                         ([{**dmi, "stdout": "Manufacturer: ACME\n"}, kernel], "tuple incomplete"),
                         ([{**dmi, "stdout": "Manufacturer: ACME\nProduct Name: Board\nBIOS Version: 1\nUnknown: ignored\n"},
                           {**kernel, "exit": 127}], "required command failed"),
                         ([dmi, {**kernel, "stdout": "  \n"}], "kernel release is empty")):
        identity, error = controls._identity({"commands": rows}, path)
        assert identity is None and error is not None and phrase in error["reason"]

    parsed, error_text = controls._json_stdout({"stdout": '{"value":NaN}'}, "native result")
    assert parsed is None and error_text is not None and "finite JSON" in error_text
    assert controls._parsed_number("1.25e2") == 125.0
    assert controls._parsed_number("1..2") is None
    assert controls._parsed_number("١") is None


def test_experiment_plan_is_a_first_captured_literal_and_matches_metadata(tmp_path: Path) -> None:
    path = tmp_path / "commands.json"
    plan = {"backend": "cuda"}
    plan_row = {"argv": ["cat", "experiment-plan.json"], "exit": 0, "stdout": json.dumps(plan)}
    valid = {"experiment_plan": plan, "commands": [plan_row]}
    parsed, error = controls._capture_plan(valid, path)
    assert error is None and parsed == plan
    for data, expected in (
        ({"experiment_plan": None, "commands": [plan_row]}, "experiment plan missing"),
        ({"experiment_plan": plan, "commands": []}, "literal captured experiment-plan file missing"),
        ({"experiment_plan": plan, "commands": [{**plan_row, "exit": 1}]}, "literal captured experiment-plan file missing"),
        ({"experiment_plan": plan, "commands": [{"argv": ["uname", "-r"], "exit": 0, "stdout": "6.17"}, plan_row]},
         "first captured after other commands"),
        ({"experiment_plan": plan, "commands": [{**plan_row, "stdout": "not json"}]}, "finite JSON"),
        ({"experiment_plan": {"backend": "rocm"}, "commands": [plan_row]}, "differs from captured plan"),
    ):
        parsed, error = controls._capture_plan(data, path)
        assert parsed is None and error is not None and expected in error["reason"]


def test_rdma_plan_requires_all_four_named_scenarios_and_ratio(tmp_path: Path) -> None:
    path = tmp_path / "commands.json"
    valid = {"scenarios": ["cold", "reboot-individual", "reboot-sequential", "hotplug"],
             "max_directional_ratio": 1.25}
    scenarios, ratio, error = controls._asymmetry_plan(valid, path)
    assert scenarios == sorted(valid["scenarios"]) and ratio == 1.25 and error is None
    for changed in (
        {**valid, "scenarios": ["cold", "reboot", "hotplug"]},
        {**valid, "max_directional_ratio": float("nan")},
    ):
        scenarios, tolerance, error = controls._asymmetry_plan(changed, path)
        assert scenarios is None and tolerance is None and error is not None and error["status"] == "unknown"


def test_native_ib_write_bw_output_is_measured_not_claimed() -> None:
    output = "#bytes #iterations BW peak[MB/sec] BW average[MB/sec]\n1048576 1000 14000.0 13900.0\n"
    assert controls._bandwidth(output) == pytest.approx(111.2)
    assert controls._bandwidth("PASS throughput=999 Gbps") is None
    assert controls._bandwidth("BW average[MB/sec]\ninvalid") is None


def test_nccl_parser_rejects_error_count_and_status_text() -> None:
    good = "# size count time algbw busbw #wrong\n1024 256 1.2 3.4 2.5 0\n"
    assert controls._nccl_completed(good)
    assert not controls._nccl_completed(good.replace(" 0\n", " 1\n"))
    assert not controls._nccl_completed("PASS NCCL completed")


def test_topology_traffic_rejects_missing_positive_path_and_underperforming_workloads(tmp_path: Path) -> None:
    path = tmp_path / "commands.json"
    plan = {"minimum_gbps": 7.0, "traffic_seconds": 30}
    disconnected = {"argv": ["ib_write_bw", "-D", "30"], "exit": 0,
                    "stdout": "BW average[MB/sec]\n1024 10 0 0\n", "stderr": "", "phase": "negative"}
    positive = {"argv": ["ib_write_bw", "-D", "30"], "exit": 0,
                "stdout": "BW average[MB/sec]\n1024 10 1000 1000\n", "stderr": "", "phase": "positive"}
    nccl = {"argv": ["all_reduce_perf"], "exit": 0,
            "stdout": "# size count time algbw busbw error\n8 1 1.0 0.01 0.01 0\n", "stderr": ""}
    assert _status(controls._topology_traffic({"commands": []}, plan, path)) == "unknown"
    leaking = {**disconnected, "stdout": positive["stdout"]}
    result = controls._topology_traffic({"commands": [leaking]}, plan, path)
    assert result is not None and result["status"] == "fail" and "still carries" in result["reason"]

    failed_without_reason = {**disconnected, "exit": 1, "stdout": "", "stderr": ""}
    result = controls._topology_traffic({"commands": [failed_without_reason]}, plan, path)
    assert result is not None and result["status"] == "fail"
    failed_negative = {**disconnected, "exit": 1, "stdout": "", "stderr": "No route to host"}
    missing_positive = controls._topology_traffic({"commands": [failed_negative]}, plan, path)
    assert missing_positive is not None and missing_positive["status"] == "unknown"

    for changed, phrase, status in (
        ({**positive, "argv": ["ib_write_bw", "-D", "30"]}, "NCCL", "unknown"),
        ({**positive, "stdout": "no parsed bandwidth"}, "throughput", "unknown"),
        ({**positive, "argv": ["ib_write_bw", "-D", "10"]}, "duration", "fail"),
        ({**positive, "stdout": "BW average[MB/sec]\n1024 10 100 100\n"}, "below", "fail"),
    ):
        commands = [failed_negative, changed] + ([nccl] if phrase != "NCCL" else [])
        result = controls._topology_traffic({"commands": commands}, plan, path)
        assert result is not None and result["status"] == status and phrase.lower() in result["reason"].lower(), result
    assert controls._topology_traffic({"commands": [failed_negative, positive, nccl]}, plan, path) is None
    bad_nccl = {**nccl, "stdout": "# size count time algbw busbw error\n8 1 1 1 1 1\n"}
    result = controls._topology_traffic({"commands": [failed_negative, positive, bad_nccl]}, plan, path)
    assert result is not None and result["status"] == "fail" and "NCCL" in result["reason"]


def _topology_native_map() -> tuple[list[dict[str, Any]], list[dict[str, str]]]:
    links = [
        {"bdf": "0000:03:00.0", "netdev": "port-a", "local_port": "port-a", "peer_port": "swp1"},
        {"bdf": "0000:03:00.1", "netdev": "port-b", "local_port": "port-b", "peer_port": "swp2"},
    ]
    commands: list[dict[str, Any]] = [{"argv": ["lspci", "-D", "-nn"], "exit": 0,
        "stdout": "0000:03:00.0 Ethernet 15b3:101d\n0000:03:00.1 Ethernet 15b3:101d\n"}]
    commands.extend({"argv": ["ethtool", "-i", link["netdev"]], "exit": 0,
                     "stdout": f"bus-info: {link['bdf']}\n"} for link in links)
    commands.append({"argv": ["lldpctl", "-f", "json"], "exit": 0,
                     "stdout": json.dumps({"ports": [{"local_port": link["local_port"],
                                                        "peer_port": link["peer_port"]} for link in links]})})
    return commands, links


def test_topology_native_map_requires_device_and_physical_peer_consistency(tmp_path: Path) -> None:
    path = tmp_path / "commands.json"
    commands, links = _topology_native_map()
    plan = {"links": links}
    assert controls._topology_map({"commands": commands}, plan, path) is None
    assert _status(controls._topology_map({"commands": commands}, {"links": []}, path)) == "unknown"
    assert controls._validate_link_plan(links, path) is None
    assert _status(controls._validate_link_plan([{**links[0], "peer_port": None}, links[1]], path)) == "unknown"
    assert _status(controls._validate_link_plan([links[0], {**links[1], "local_port": "port-a"}], path)) == "fail"
    assert _status(controls._validate_link_plan([links[0], {**links[1], "bdf": links[0]["bdf"]}], path)) == "fail"
    assert _status(controls._validate_link_plan([links[0], {**links[1], "local_port": "other"}], path)) == "unknown"
    assert _status(controls._topology_map({"commands": []}, plan, path)) == "unknown"

    physical = commands[-1]
    physical["stdout"] = "not JSON"
    assert _status(controls._topology_map({"commands": commands}, plan, path)) == "unknown"
    physical["stdout"] = json.dumps({"ports": [{"local_port": "port-a", "peer_port": "wrong"},
                                                {"local_port": "port-b", "peer_port": "swp2"}]})
    assert _status(controls._topology_map({"commands": commands}, plan, path)) == "fail"
    physical["stdout"] = json.dumps({"ports": [{"local_port": "port-a", "peer_port": "swp1"},
                                                {"local_port": "port-a", "peer_port": "swp-extra"},
                                                {"local_port": "port-b", "peer_port": "swp2"}]})
    result = controls._topology_map({"commands": commands}, plan, path)
    assert result is not None and result["status"] == "fail" and "alias" in result["reason"]


def test_topology_device_binding_rejects_inventory_and_driver_mapping_drift(tmp_path: Path) -> None:
    path = tmp_path / "commands.json"
    commands, links = _topology_native_map()
    assert controls._validate_link_devices({"commands": commands}, links, path) is None
    for rows, link_plan, status, phrase in (
        ([], links, "unknown", "required raw command missing"),
        ([{**commands[0], "stdout": "no Mellanox adapters\n"}], links, "fail", "absent"),
        (commands, [{**links[0], "bdf": "bad"}, links[1]], "fail", "BDF malformed"),
        ([{**commands[0], "stdout": "0000:04:00.0 Ethernet 15b3:101d\n"}, *commands[1:]],
         links, "fail", "absent from native inventory"),
        (commands[:1], links, "unknown", "required raw command missing"),
    ):
        error = controls._validate_link_devices({"commands": rows}, link_plan, path)
        assert error is not None and error["status"] == status and phrase in error["reason"]
    changed = [{**row, "stdout": "bus-info: 0000:04:00.0\n"} if row["argv"][0] == "ethtool" and row["argv"][2] == "port-a" else row
               for row in commands]
    error = controls._validate_link_devices({"commands": changed}, links, path)
    assert error is not None and error["status"] == "fail" and "netdev-to-PCI" in error["reason"]


def test_capture_rejects_self_asserted_outcome(tmp_path: Path) -> None:
    finding_id = controls.IDS[0]
    evidence = tmp_path / finding_id
    evidence.mkdir()
    row = {"argv": ["uname", "-r"], "exit": 0, "stdout": "kernel\n", "stderr": "",
           "captured_at": "2026-10-03T12:00:00Z", "pass": True}
    (evidence / "commands.json").write_text(json.dumps({"schema": 1, "id": finding_id, "commands": [row]}), encoding="utf-8")
    result = controls.verify(finding_id, evidence)
    assert result["status"] == "fail", result
    assert "asserted outcome" in result["reason"]


def test_capture_envelope_rejects_wrong_schema_subject_and_empty_transcript(tmp_path: Path) -> None:
    finding_id = controls.IDS[0]
    evidence = tmp_path / finding_id
    evidence.mkdir()
    capture = evidence / "commands.json"
    row = {"argv": ["uname", "-r"], "exit": 0, "stdout": "6.17\n", "stderr": "",
           "captured_at": "2026-10-03T12:00:00Z"}
    for bundle, status, reason in (
        ({"schema": True, "id": finding_id, "commands": [row]}, "fail", "schema"),
        ({"schema": 1, "id": "another-finding", "commands": [row]}, "fail", "ID mismatch"),
        ({"schema": 1, "id": finding_id, "commands": []}, "unknown", "transcript is absent"),
        ({"schema": 1, "id": finding_id, "commands": [row], "healthy": True}, "fail", "asserted outcome"),
    ):
        capture.write_text(json.dumps(bundle), encoding="utf-8")
        result = controls.verify(finding_id, evidence)
        assert result["status"] == status and reason in result["reason"], result


@pytest.mark.parametrize(("status", "expected_rc"), [("pass", 0), ("fail", 1), ("unknown", 2)])
def test_cli_emits_verdict_and_exit_code_for_each_status(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], status: str, expected_rc: int
) -> None:
    monkeypatch.setattr(controls, "verify", lambda finding_id, evidence, **kwargs: {
        "status": status, "reason": "measured", "files": [], "fail": int(status == "fail"),
        "could_not_run": int(status == "unknown")})
    assert controls.main(["--id", controls.IDS[0]]) == expected_rc
    output = json.loads(capsys.readouterr().out)
    assert output["status"] == status and output["reason"] == "measured"


def test_capture_rejects_parent_symlink_and_malformed_command_rows(tmp_path: Path) -> None:
    target = tmp_path / "actual"
    target.mkdir()
    capture = target / "commands.json"
    row = {"argv": ["uname", "-r"], "exit": 0, "stdout": "6.17\n", "stderr": "",
           "captured_at": "2026-10-03T12:00:00Z"}
    capture.write_text(json.dumps({"schema": 1, "id": controls.IDS[0], "commands": [row]}), encoding="utf-8")
    alias = tmp_path / "alias"
    alias.symlink_to(target, target_is_directory=True)
    result = controls.verify(controls.IDS[0], alias)
    assert result["status"] == "fail" and "symlink" in result["reason"]

    malformed = [dict(row, argv=[]), dict(row, exit=True), dict(row, stdout=3), dict(row, captured_at="yesterday")]
    for bad_row in malformed:
        result = controls._validate_rows([bad_row], capture)
        assert result is not None and result["status"] == "fail"


def test_capture_cannot_smuggle_in_trusted_plan_anchor(tmp_path: Path) -> None:
    finding_id = controls.IDS[0]
    evidence = tmp_path / finding_id
    evidence.mkdir()
    row = {"argv": ["cat", "experiment-plan.json"], "exit": 0, "stdout": "{}", "stderr": "",
           "captured_at": "2026-10-03T12:00:00Z"}
    bundle = {"schema": 1, "id": finding_id, "commands": [row], "_trusted_plan_sha256": "0" * 64}
    (evidence / "commands.json").write_text(json.dumps(bundle), encoding="utf-8")
    result = controls.verify(finding_id, evidence)
    assert result["status"] == "fail", result
    assert "asserted outcome" in result["reason"]


def test_batch_verifier_exact_id_anchor_and_predicate_exception_contract(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    assert controls.verify("unknown-generated-id", tmp_path)["status"] == "fail"
    finding_id = controls.IDS[0]
    evidence = tmp_path / finding_id
    evidence.mkdir()
    row = {"argv": ["cat", "plan.json"], "exit": 0, "stdout": "{}", "captured_at": "2026-10-03T12:00:00Z"}
    (evidence / "commands.json").write_text(json.dumps({"schema": 1, "id": finding_id, "commands": [row]}), encoding="utf-8")
    received: dict[str, Any] = {}

    def capture(data: dict[str, Any], path: Path) -> dict[str, Any]:
        received.update(data)
        return {"status": "pass", "reason": "unit predicate", "files": []}

    monkeypatch.setitem(controls.PREDICATES, finding_id, capture)
    result = controls.verify(finding_id, evidence, trusted_plan_sha256="c" * 64)
    assert result["status"] == "pass" and received["_trusted_plan_sha256"] == "c" * 64
    monkeypatch.setitem(controls.PREDICATES, finding_id, lambda data, path: (_ for _ in ()).throw(IndexError("truncated")))
    result = controls.verify(finding_id, evidence)
    assert result["status"] == "unknown" and "truncated" in result["reason"]


@pytest.mark.parametrize("kind", ["oversize", "fifo", "symlink"])
def test_capture_filesystem_bounds_reject_before_reading(tmp_path: Path, kind: str) -> None:
    evidence = tmp_path / "evidence"
    evidence.mkdir()
    capture = evidence / "commands.json"
    if kind == "oversize":
        capture.touch()
        capture.open("r+b").truncate(controls.MAX_BYTES + 1)
    elif kind == "fifo":
        import os

        os.mkfifo(capture)
    else:
        target = tmp_path / "target.json"
        target.write_text("{}", encoding="utf-8")
        capture.symlink_to(target)
    result = controls.verify(controls.IDS[0], evidence)
    assert result["status"] == "fail", result
    assert any(word in result["reason"] for word in ("regular file", "symlink", "8 MiB"))


def test_real_payload_over_eight_mib_is_rejected(tmp_path: Path) -> None:
    evidence = tmp_path / "evidence"
    evidence.mkdir()
    capture = evidence / "commands.json"
    capture.write_bytes(b" " * (controls.MAX_BYTES + 1))

    result = controls.verify(controls.IDS[0], evidence)

    assert result["status"] == "fail", result
    assert "8 MiB" in result["reason"]


def test_reader_detects_growth_past_bounded_read(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    capture = tmp_path / "commands.json"
    capture.write_bytes(b"x")
    monkeypatch.setattr(controls, "read_regular_bytes", lambda _path, _limit: b"x" * (controls.MAX_BYTES + 1))
    with pytest.raises(controls.UnsafeCapture, match="8 MiB"):
        controls._read_bounded_regular(capture)


def test_reader_propagates_unclassified_os_error(tmp_path: Path) -> None:
    overlong_name = "x" * 300
    with pytest.raises(OSError) as excinfo:
        controls._read_bounded_regular(tmp_path / overlong_name)
    assert excinfo.value.errno == errno.ENAMETOOLONG


def test_raw_capture_truncation_and_row_count_are_explicit(tmp_path: Path) -> None:
    finding_id = controls.IDS[0]
    evidence = tmp_path / finding_id
    evidence.mkdir()
    capture = evidence / "commands.json"
    capture.write_bytes(b'{"schema":1,"id":"' + finding_id.encode() + b'","commands":[{"argv":')
    result = controls.verify(finding_id, evidence)
    assert result["status"] == "unknown" and result["could_not_run"] == 1

    row = {"argv": ["true"], "exit": 0, "stdout": "", "captured_at": "2026-10-03T12:00:00Z"}
    result = controls._validate_rows([row] * (controls.MAX_ROWS + 1), capture)
    assert result is not None and result["status"] == "fail" and "row count" in result["reason"]


def test_command_timestamps_reject_timezone_absence_and_nonmonotonicity(tmp_path: Path) -> None:
    path = tmp_path / "commands.json"
    base = {"argv": ["uname", "-r"], "exit": 0, "stdout": "6.17\n", "captured_at": "2026-10-03T12:00:00Z"}
    missing_zone = {**base, "captured_at": "2026-10-03T12:00:00"}
    result = controls._validate_rows([missing_zone], path)
    assert result is not None and "timezone" in result["reason"]
    equal = {**base}
    result = controls._validate_rows([base, equal], path)
    assert result is not None and "strictly increasing" in result["reason"]


def test_native_capture_helpers_distinguish_phase_absence_failure_and_finite_values(tmp_path: Path) -> None:
    path = tmp_path / "commands.json"
    rows = [
        {"argv": ["tool", "arg"], "exit": 0, "stdout": "ok", "phase": "before"},
        {"argv": ["tool", "arg"], "exit": 4, "stdout": "bad", "phase": "after"},
    ]
    data = {"commands": rows}
    assert controls._cmd(data, controls._prefix("tool", "arg"), phase="before") is rows[0]
    assert controls._cmd(data, controls._prefix("tool", "arg"), phase="missing") is None
    row, error = controls._need(data, path, "tool", controls._prefix("tool", "arg"), phase="before")
    assert row is rows[0] and error is None
    row, error = controls._need(data, path, "tool", controls._prefix("tool", "arg"), phase="after")
    assert row is None and error is not None and error["status"] == "fail"
    row, error = controls._need(data, path, "absent", controls._prefix("other"))
    assert row is None and error is not None and error["status"] == "unknown"
    assert controls._finite(12) == 12.0 and controls._finite(-3.5) == -3.5
    assert controls._parsed_number("+2.") == 2.0
    assert controls._parsed_number("1e999") is None


def test_capture_row_schema_flags_and_time_order_are_rejected(tmp_path: Path) -> None:
    path = tmp_path / "commands.json"
    timestamp = "2026-10-03T12:00:00Z"
    row = {"argv": ["true"], "exit": 0, "stdout": "", "captured_at": timestamp}
    for malformed in (
        None, {**row, "argv": "true"}, {**row, "argv": ["true", None]},
        {**row, "stderr": 1}, {**row, "captured_at": "yesterday"},
        {**row, "status": "pass"},
    ):
        error = controls._validate_rows([malformed], path)
        assert error is not None and error["status"] == "fail"
    first = {**row, "captured_at": "2026-10-03T12:00:00Z"}
    second = {**row, "captured_at": "2026-10-03T11:59:59Z"}
    error = controls._validate_rows([first, second], path)
    assert error is not None and "strictly increasing" in error["reason"]


def test_vendor_sources_require_https_primary_domain_digest_and_subject_binding(tmp_path: Path) -> None:
    identity = {"Manufacturer": "ASUSTeK", "Product Name": "GX10", "Kernel": "6.17.0"}
    text = "ASUSTeK GX10 running kernel 6.17.0 supported driver and firmware tuple per primary release documentation."
    digest = hashlib.sha256(text.encode()).hexdigest()
    row = {"url": "https://docs.nvidia.com/dgx/", "text": text, "sha256": digest}
    refs, error = controls._vendor_refs({"vendor_sources": [row]}, identity)
    assert error is None and refs is not None

    for bad in (
        {**row, "url": "http://docs.nvidia.com/dgx/"},
        {**row, "url": "https://docs.nvidia.com.attacker.invalid/dgx/"},
        {**row, "sha256": "0" * 64},
        {**row, "text": "NVIDIA support data without the captured model identity"},
    ):
        refs, error = controls._vendor_refs({"vendor_sources": [bad]}, identity)
        assert refs is None and error is not None
    short = {"url": "https://docs.nvidia.com/", "text": "short",
             "sha256": hashlib.sha256(b"short").hexdigest()}
    refs, error = controls._vendor_refs({"vendor_sources": [short]}, identity)
    assert refs is None and error is not None and "too short" in error
    for vendor_sources in (None, [{}], [{"url": "https://docs.nvidia.com/", "text": "short", "sha256": "0" * 64}]):
        refs, error = controls._vendor_refs({"vendor_sources": vendor_sources}, identity)
        assert refs is None and error is not None


def test_firmware_channel_and_release_parsers_fail_closed_on_origin_and_stanza_drift() -> None:
    assert controls._valid_package_origin("nvidia.com")
    assert controls._valid_package_origin("repo.nvidia.com")
    assert controls._valid_package_origin("updates.asus.com")
    assert not controls._valid_package_origin("nvidia.com.attacker.invalid")
    assert controls._valid_package_source_uri("https://repo.nvidia.com/ubuntu", "repo.nvidia.com")
    for source in ("http://repo.nvidia.com/ubuntu", "https://repo.nvidia.com:443/ubuntu",
                   "https://user@repo.nvidia.com/ubuntu", "https://repo.nvidia.com/ubuntu?x=1"):
        assert not controls._valid_package_source_uri(source, "repo.nvidia.com")

    release = "SHA256:\n " + "a" * 64 + " 128 main/binary-arm64/Packages\n MD5Sum:\n"
    assert controls._release_index_entry(release, "main/binary-arm64/Packages") == ("a" * 64, 128)
    assert controls._release_index_entry("MD5Sum:\n", "main/binary-arm64/Packages") is None
    assert controls._release_index_entry("SHA256:\n malformed\n", "main/binary-arm64/Packages") is None
    assert controls._artifact_path(Path("/tmp/capture/commands.json"), "../outside") is None
    assert controls._artifact_path(Path("/tmp/capture/commands.json"), "/absolute") is None
    assert controls._artifact_path(Path("/tmp/capture/commands.json"), "raw/InRelease") == Path("/tmp/capture/raw/InRelease")


def test_signed_firmware_repository_plan_binds_native_apt_policy_to_index_tuple(tmp_path: Path) -> None:
    path = tmp_path / "commands.json"
    plan = {
        "package_origin": "repo.nvidia.com", "package_source_uri": "https://repo.nvidia.com/ubuntu",
        "package_version": "1.2-3", "inrelease_path": "/tmp/InRelease", "keyring_path": "/tmp/keyring.gpg",
        "repository_fingerprint": "A" * 40, "inrelease_artifact": "raw/InRelease", "keyring_artifact": "raw/keyring.gpg",
        "inrelease_sha256": "a" * 64, "keyring_sha256": "b" * 64, "packages_index_path": "/tmp/Packages",
        "package_index_relative": "main/binary-arm64/Packages", "package_filename": "pool/fw.deb",
        "package_size": 123, "package_architecture": "arm64", "package_component": "main", "package_suite": "noble",
    }
    policy = {"argv": ["apt-cache", "policy", "fw"], "exit": 0,
              "stdout": "500 https://repo.nvidia.com/ubuntu noble/main arm64 Packages\n"}
    assert controls._fw_repository_plan({"commands": [policy]}, path, plan, "fw") is None
    incomplete = {key: value for key, value in plan.items() if key != "keyring_sha256"}
    error = controls._fw_repository_plan({"commands": [policy]}, path, incomplete, "fw")
    assert error is not None and error["status"] == "unknown"
    error = controls._fw_repository_plan({"commands": [policy]}, path, {**plan, "package_size": True}, "fw")
    assert error is not None and error["status"] == "unknown"
    error = controls._fw_repository_plan({"commands": [policy]}, path, {**plan, "repository_fingerprint": "lowercase"}, "fw")
    assert error is not None and error["status"] == "unknown"
    error = controls._fw_repository_plan({"commands": [policy]}, path, {**plan, "package_source_uri": "http://repo.nvidia.com/ubuntu"}, "fw")
    assert error is not None and error["status"] == "fail"
    error = controls._fw_repository_plan({"commands": [policy]}, path,
                                         {**plan, "package_index_relative": "main/binary-amd64/Packages"}, "fw")
    assert error is not None and error["status"] == "fail"
    error = controls._fw_repository_plan({"commands": [{**policy, "stdout": "500 https://other.example/ubuntu noble/main arm64 Packages\n"}]},
                                         path, plan, "fw")
    assert error is not None and error["status"] == "fail"


def test_signed_packages_stanza_binds_hash_size_filename_and_local_artifact(tmp_path: Path) -> None:
    path = tmp_path / "commands.json"
    package_path = "/tmp/fw.deb"
    digest = "a" * 64
    plan = {"package_path": package_path, "package_version": "1.2-3", "package_size": 123,
            "package_filename": "pool/fw.deb"}
    stanza = ("Package: fw\nVersion: 1.2-3\nFilename: pool/fw.deb\nSize: 123\nSHA256: " + digest + "\n")
    row = {"argv": ["sha256sum", package_path], "exit": 0, "stdout": f"{digest}  {package_path}\n"}
    data = {"commands": [row]}
    assert controls._verify_packages_stanza(data, stanza, path, "fw", plan) is None
    cases = (
        ("Package: other\nVersion: 1.2-3\n", "exact package/version stanza absent", "unknown", data, plan),
        ("Package: fw\nVersion: 1.2-3\n", "lacks filename", "unknown", data, plan),
        (stanza, "candidate .deb hash readback missing", "unknown", {"commands": []}, plan),
        (stanza, "differs from signed Packages stanza", "fail",
         {"commands": [{**row, "stdout": f"{'b' * 64}  {package_path}\n"}]}, plan),
        (stanza, "differs from signed Packages stanza", "fail", data, {**plan, "package_size": 124}),
        (stanza.replace("pool/fw.deb", "pool/other.deb"), "candidate filename differs", "fail", data, plan),
        (stanza.replace("pool/fw.deb", "pool/other.deb"), "local candidate artifact name differs", "fail",
         data, {**plan, "package_filename": "pool/other.deb"}),
    )
    for text, expected_reason, expected_status, captured, contract in cases:
        result = controls._verify_packages_stanza(captured, text, path, "fw", contract)
        assert result is not None and result["status"] == expected_status and expected_reason in result["reason"]
    no_hash, error = controls._native_file_size({"commands": []}, path, package_path)
    assert no_hash is None and error is not None and error["status"] == "unknown"
    bad_size, error = controls._native_file_size({"commands": [{"argv": ["stat", "-c", "%s", package_path],
        "exit": 0, "stdout": "size\n"}]}, path, package_path)
    assert bad_size is None and error is not None and error["status"] == "fail"


def test_signed_index_parser_binds_packages_bytes_before_package_file_size(tmp_path: Path) -> None:
    path = tmp_path / "commands.json"
    artifact_dir = tmp_path / "refs"
    artifact_dir.mkdir()
    package_data = b"binary package bytes"
    package_digest = hashlib.sha256(package_data).hexdigest()
    package_path = "/tmp/fw.deb"
    stanza = (f"Package: fw\nVersion: 1.2-3\nFilename: pool/fw.deb\nSize: {len(package_data)}\n"
              f"SHA256: {package_digest}\n")
    index_digest = hashlib.sha256(stanza.encode()).hexdigest()
    inrelease = artifact_dir / "InRelease"
    inrelease.write_text(f"SHA256:\n {index_digest} {len(stanza.encode())} main/binary-arm64/Packages\n", encoding="utf-8")
    plan: dict[str, Any] = {"packages_index_path": "/tmp/Packages", "package_index_relative": "main/binary-arm64/Packages",
        "package_path": package_path, "package_version": "1.2-3", "package_size": len(package_data),
        "package_filename": "pool/fw.deb", "inrelease_artifact": "refs/InRelease"}
    commands = [
        {"argv": ["cat", "/tmp/Packages"], "exit": 0, "stdout": stanza},
        {"argv": ["sha256sum", package_path], "exit": 0, "stdout": f"{package_digest}  {package_path}\n"},
        {"argv": ["stat", "-c", "%s", package_path], "exit": 0, "stdout": f"{len(package_data)}\n"},
    ]
    assert controls._verify_signed_package_index({"commands": commands}, path, plan, "fw", package_path) is None
    result = controls._verify_signed_package_index({"commands": commands[1:]}, path, plan, "fw", package_path)
    assert result is not None and result["status"] == "unknown"
    missing_release = {**plan, "inrelease_artifact": "refs/absent"}
    result = controls._verify_signed_package_index({"commands": commands}, path, missing_release, "fw", package_path)
    assert result is not None and result["status"] == "unknown"
    changed_index = [{**commands[0], "stdout": stanza + "# drift\n"}, *commands[1:]]
    result = controls._verify_signed_package_index({"commands": changed_index}, path, plan, "fw", package_path)
    assert result is not None and result["status"] == "fail"
    wrong_file_size = [commands[0], commands[1], {**commands[2], "stdout": "999\n"}]
    result = controls._verify_signed_package_index({"commands": wrong_file_size}, path, plan, "fw", package_path)
    assert result is not None and result["status"] == "fail"


def test_firmware_writer_scanner_ignores_comments_and_detects_direct_or_exec_writers() -> None:
    assert not controls._contains_firmware_writer("# mlxfwupdater --flash\necho safe\n")
    assert controls._contains_firmware_writer("/usr/bin/mlxfwupdater --query\n")
    assert controls._contains_firmware_writer("exec /opt/vendor/mstflint -d 03:00.0 q\n")
    assert not controls._contains_firmware_writer("echo flint is mentioned here\n")


def test_firmware_script_analysis_distinguishes_static_helpers_from_dynamic_execution() -> None:
    direct, helpers, ambiguous = controls._firmware_script_analysis("#!/bin/sh\nmlxfwupdater --flash\n")
    assert direct and not helpers and not ambiguous
    direct, helpers, ambiguous = controls._firmware_script_analysis("#!/bin/sh\n. /usr/lib/vendor/helper.sh\n")
    assert not direct and helpers == {"/usr/lib/vendor/helper.sh"} and not ambiguous
    direct, helpers, ambiguous = controls._firmware_script_analysis("#!/bin/sh\nsh $HELPER\n")
    assert not direct and not helpers and ambiguous
    direct, helpers, ambiguous = controls._firmware_script_analysis("#!/bin/sh\n/usr/lib/vendor/helper.sh\n")
    assert not direct and helpers == {"/usr/lib/vendor/helper.sh"} and not ambiguous
    direct, helpers, ambiguous = controls._firmware_script_analysis("#!/bin/sh\neval \"$COMMAND\"\n")
    assert not direct and not helpers and ambiguous
    direct, helpers, ambiguous = controls._firmware_script_analysis("#!/bin/sh\nsh '/unterminated\n")
    assert not direct and not helpers and ambiguous


def test_firmware_pci_and_hca_bindings_require_same_canonical_device() -> None:
    path = Path("/tmp/commands.json")
    bdf, hca, fw = "0000:03:00.0", "mlx5_0", "28.45.1"
    pci = {"argv": ["lspci", "-s", bdf, "-vv"], "exit": 0,
           "stdout": f"{bdf} Ethernet controller: 15b3:101d\n\tBusMaster+\n\tKernel driver in use: mlx5_core\n"}
    inventory = {"argv": ["lspci", "-D", "-nn"], "exit": 0,
                 "stdout": f"{bdf} Ethernet controller: 15b3:101d\n"}
    data = {"commands": [pci, inventory]}
    assert controls._fw_pci_binding(data, path, bdf) is None
    for broken, expected in (
        ({**pci, "stdout": pci["stdout"].replace(bdf, "0000:04:00.0")}, "uniquely bind"),
        ({**inventory, "stdout": "0000:04:00.0 Ethernet controller: 15b3:101d\n"}, "uniquely normalized"),
        ({**pci, "stdout": pci["stdout"].replace("15b3:101d", "10de:1234")}, "Mellanox vendor"),
        ({**pci, "stdout": pci["stdout"].replace("BusMaster+", "BusMaster-")}, "bus mastering"),
        ({**pci, "stdout": pci["stdout"].replace("mlx5_core", "vfio-pci")}, "native mlx5_core"),
    ):
        rows = [pci, broken] if expected == "uniquely normalized" else [broken, inventory]
        error = controls._fw_pci_binding({"commands": rows}, path, bdf)
        assert error is not None and expected in error["reason"]

    sysfs = {"argv": ["readlink", "-f", f"/sys/class/infiniband/{hca}/device"], "exit": 0,
             "stdout": f"/sys/devices/pci0000:00/{bdf}\n"}
    rdma = {"argv": ["ibv_devinfo", "-v", "-d", hca], "exit": 0,
            "stdout": f"state: PORT_ACTIVE\nfw_ver: {fw}\n"}
    assert controls._fw_hca_binding({"commands": [sysfs, rdma]}, path, bdf, hca, fw) is None
    for changed, expected in (
        ({**sysfs, "stdout": "/sys/devices/pci0000:00/0000:04:00.0\n"}, "different PCI BDF"),
        ({**rdma, "stdout": "state: PORT_DOWN\nfw_ver: 28.45.1\n"}, "no active port"),
        ({**rdma, "stdout": "state: PORT_ACTIVE\nfw_ver: 28.45.2\n"}, "readbacks disagree"),
    ):
        rows = [changed, rdma] if expected == "different PCI BDF" else [sysfs, changed]
        error = controls._fw_hca_binding({"commands": rows}, path, bdf, hca, fw)
        assert error is not None and expected in error["reason"]


def test_firmware_target_query_package_digest_and_recovery_inputs_fail_closed(tmp_path: Path) -> None:
    path = tmp_path / "commands.json"
    assert _status(controls._fw_device_target({"bdf": "03:00.0", "rdma_hca": "mlx5_0"}, path)[1]) == "unknown"
    assert _status(controls._fw_device_target({"bdf": "0000:03:00.0", "rdma_hca": "other"}, path)[1]) == "unknown"
    assert controls._fw_device_target({"bdf": "0000:03:00.0", "rdma_hca": "mlx5_0"}, path) == (("0000:03:00.0", "mlx5_0"), None)

    query = {"argv": ["flint", "q", "-d"], "exit": 0, "stdout": "PSID: X\n"}
    result, error = controls._fw_query({"commands": [query]}, path, "0000:03:00.0")
    assert result is None and error is not None and error["status"] == "fail"
    query["argv"] = ["flint", "-d", "04:00.0", "q"]
    result, error = controls._fw_query({"commands": [query]}, path, "0000:03:00.0")
    assert result is None and error is not None and error["status"] == "fail"

    contract = {"package_path": "/tmp/fw.deb", "package_name": "fw", "package_origin": "repo.nvidia.com",
                "script_extract_dir": "/tmp/fw-control", "package_sha256": "a" * 64}
    assert controls._fw_package_contract(contract, path)[1] is None
    assert _status(controls._fw_package_contract({**contract, "package_origin": "attacker.invalid"}, path)[1]) == "fail"
    assert _status(controls._fw_package_contract({**contract, "script_extract_dir": "/usr/tmp/fw-control"}, path)[1]) == "unknown"
    assert _status(controls._fw_package_contract({**contract, "package_sha256": "bad"}, path)[1]) == "unknown"
    row = {"argv": ["sha256sum", "/tmp/fw.deb"], "exit": 0, "stdout": f"{'a' * 64}  /tmp/fw.deb\n"}
    assert controls._fw_package_digest({"commands": [row]}, path, "/tmp/fw.deb", "a" * 64) is None
    mismatch = controls._fw_package_digest({"commands": [row]}, path, "/tmp/fw.deb", "b" * 64)
    assert mismatch is not None and mismatch["status"] == "fail"
    assert controls._fw_recovery({"commands": [{"argv": ["cat", "runbook"], "exit": 0,
        "stdout": "OEM recovery steps" , "phase": "recovery-procedure"}]}, path) is None
    empty = controls._fw_recovery({"commands": [{"argv": ["cat", "runbook"], "exit": 0,
        "stdout": " ", "phase": "recovery-procedure"}]}, path)
    assert empty is not None and empty["status"] == "unknown"


def test_firmware_guard_stops_on_identity_or_first_device_prerequisite(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "commands.json"
    plan = {"package_name": "fw", "package_version": "1", "repository_fingerprint": "A" * 40}
    monkeypatch.setattr(controls, "_capture_plan", lambda data, evidence: (plan, None))
    monkeypatch.setattr(controls, "_plan_approval", lambda data, evidence, captured: None)
    monkeypatch.setattr(controls, "_identity", lambda data, evidence: (
        {"Manufacturer": "ASUS", "Product Name": "GX10"}, None))
    monkeypatch.setattr(controls, "_fw_device", lambda data, evidence, captured: {"status": "fail", "reason": "BDF conflict"})
    monkeypatch.setattr(controls, "_fw_package_guard", lambda *args: (_ for _ in ()).throw(AssertionError("later gate ran")))
    result = controls._fw_guard({}, path)
    assert result["status"] == "fail" and result["reason"] == "BDF conflict"
    monkeypatch.setattr(controls, "_identity", lambda data, evidence: (
        {"Manufacturer": "other", "Product Name": "GX10"}, None))
    result = controls._fw_guard({}, path)
    assert result["status"] == "fail" and "scoped ASUS GX10" in result["reason"]
    monkeypatch.setattr(controls, "_capture_plan", lambda data, evidence: (None, {"status": "unknown", "reason": "plan missing"}))
    assert controls._fw_guard({}, path)["reason"] == "plan missing"
    monkeypatch.setattr(controls, "_capture_plan", lambda data, evidence: (plan, None))
    monkeypatch.setattr(controls, "_identity", lambda data, evidence: (
        {"Manufacturer": "ASUS", "Product Name": "GX10"}, None))
    monkeypatch.setattr(controls, "_fw_device", lambda data, evidence, captured: None)
    monkeypatch.setattr(controls, "_fw_package_guard", lambda data, evidence, captured: None)
    monkeypatch.setattr(controls, "_fw_recovery", lambda data, evidence: None)
    no_tuple = controls._fw_guard({"commands": [{"argv": ["flint", "-d", "03:00.0", "q"],
        "stdout": "query output without PSID/firmware"}]}, path)
    assert no_tuple["status"] == "unknown" and "exact firmware tuple" in no_tuple["reason"]
    no_reference = controls._fw_guard({"commands": [{"argv": ["flint", "-d", "03:00.0", "q"],
        "stdout": "PSID: NVD0000000087\nFW Version: 28.45.1\n"}]}, path)
    assert no_reference["status"] == "unknown" and "primary vendor" in no_reference["reason"]


def test_firmware_subcontrols_return_could_not_run_when_native_inputs_are_absent(tmp_path: Path) -> None:
    path = tmp_path / "commands.json"
    data = {"commands": []}
    checks = (
        controls._fw_device(data, path, {}),
        controls._fw_query(data, path, "0000:03:00.0")[1],
        controls._fw_pci_binding(data, path, "0000:03:00.0"),
        controls._fw_hca_binding(data, path, "0000:03:00.0", "mlx5_0", "28.45.1"),
        controls._fw_package_guard({}, path, {}),
        controls._fw_package_digest(data, path, "/tmp/fw.deb", "a" * 64),
        controls._fw_package_scripts(data, path, "/tmp/fw.deb", "/tmp/fw-control")[1],
        controls._native_file_size(data, path, "/tmp/fw.deb")[1],
        controls._fw_recovery({"commands": []}, path),
    )
    assert all(result is not None and result["status"] == "unknown" for result in checks)


def test_fresh_capture_timing_uses_explicit_bounded_nonzero_window() -> None:
    a = {"captured_at": "2026-10-03T12:00:00Z"}
    b = {"captured_at": "2026-10-03T12:01:00Z"}
    assert controls._fresh(a, b, 60)
    assert controls._fresh(a, a, 60)
    assert not controls._fresh(a, b, 0)
    assert not controls._fresh(a, b, 3601)
    assert not controls._fresh({}, b, 60)
    assert not controls._fresh({"captured_at": "bad"}, b, 60)
def test_separate_trust_anchor_must_bind_exact_canonical_plan(tmp_path: Path) -> None:
    import hashlib

    plan = {"max_directional_ratio": 1.2, "scenarios": ["cold"]}
    digest = hashlib.sha256(json.dumps(plan, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    result = controls._plan_approval({"_trusted_plan_sha256": digest}, tmp_path / "commands.json", plan)
    assert result is None
    result = controls._plan_approval({"_trusted_plan_sha256": "0" * 64}, tmp_path / "commands.json", plan)
    assert result is not None and result["status"] == "fail"
    result = controls._plan_approval({}, tmp_path / "commands.json", plan)
    assert result is not None and result["status"] == "unknown"


def test_native_memory_sample_recomputes_counters_and_pid_states(tmp_path: Path) -> None:
    def row(argv: list[str], stdout: str) -> dict[str, Any]:
        return {"argv": argv, "exit": 0, "stdout": stdout, "stderr": "",
                "captured_at": "2026-10-03T12:00:00Z", "phase": "soak", "sample": "s1"}

    data = {"experiment_plan": {"rpc_server_pid": 101, "client_pid": 202}}
    rows = [
        row(["free", "-b"], "Mem: 100000 20000 30000 4000 5000 60000\nSwap: 8000 2000 6000\n"),
        row(["cat", "/proc/pressure/memory"], "some avg10=0.10 avg60=0.05 avg300=0.01 total=123\n"),
        row(["ps", "-p", "101", "-o", "pid=,stat=,rss=,lstart="], "101 S 4096 Sat Oct  3 11:00:00 2026\n"),
        row(["ps", "-p", "202", "-o", "pid=,stat=,rss=,lstart="], "202 R 2048 Sat Oct  3 11:01:00 2026\n"),
    ]
    parsed, error = controls._parse_memory_group(data, tmp_path / "commands.json", "soak", rows)
    assert error is None and parsed is not None
    _, _, measured = parsed
    assert measured["mem_available_bytes"] == 60000
    assert measured["swap_free_bytes"] == 6000
    assert measured["rpc_server_pid"] == 101 and measured["rpc_server_state"] == "running"
    assert measured["client_pid"] == 202 and measured["client_state"] == "running"

    rows[2]["stdout"] = "999 S 4096\n"
    parsed, error = controls._parse_memory_group(data, tmp_path / "commands.json", "soak", rows)
    assert parsed is None and error is not None and error["status"] == "fail"


def test_memory_sample_parser_rejects_incomplete_counters_and_pid_contradictions(tmp_path: Path) -> None:
    path = tmp_path / "commands.json"
    data: dict[str, Any] = {"experiment_plan": {"rpc_server_pid": 101, "client_pid": 202}}
    free = {"argv": ["free", "-b"], "exit": 0,
            "stdout": "Mem: 100000 20000 30000 4000 5000 60000\nSwap: 8000 2000 6000\n",
            "captured_at": "2026-10-03T12:00:00Z"}
    psi = {"argv": ["cat", "/proc/pressure/memory"], "exit": 0,
           "stdout": "some avg10=0.10 avg60=0.05 avg300=0.01 total=123\n",
           "captured_at": "2026-10-03T12:00:01Z"}
    server = {"argv": ["ps", "-p", "101", "-o", "pid=,stat=,rss=,lstart="], "exit": 0,
              "stdout": "101 S 4096 Sat Oct  3 11:00:00 2026\n", "captured_at": "2026-10-03T12:00:02Z"}
    client = {"argv": ["ps", "-p", "202", "-o", "pid=,stat=,rss=,lstart="], "exit": 0,
              "stdout": "202 R 2048 Sat Oct  3 11:01:00 2026\n", "captured_at": "2026-10-03T12:00:03Z"}
    rows = [free, psi, server, client]
    assert controls._parse_memory_group(data, path, "soak", rows)[1] is None
    for changed_rows, expected_status, phrase in (
        ([psi, server, client], "unknown", "needs native free"),
        ([{**free, "exit": 1}, psi, server, client], "fail", "query failed"),
        ([{**free, "stdout": "Mem: malformed\n"}, psi, server, client], "unknown", "lacks available"),
        ([free, psi, {**server, "argv": ["ps", "-p", "oops", "-o", "pid=,stat=,rss=,lstart="]}, client], "fail", "numeric PID"),
        ([free, psi, server, {**client, "stdout": "999 R 2048 Sat Oct  3 11:01:00 2026\n"}], "fail", "does not match"),
        ([free, psi, server, {**client, "argv": server["argv"], "stdout": server["stdout"]}], "fail", "not distinct"),
    ):
        parsed, error = controls._parse_memory_group(data, path, "soak", changed_rows)
        assert parsed is None and error is not None and error["status"] == expected_status and phrase in error["reason"]
    parsed, error = controls._parse_memory_group({"experiment_plan": {}}, path, "soak", rows)
    assert parsed is None and error is not None and error["status"] == "unknown"


def test_dualspark_uses_repeated_observations_without_universal_threshold(tmp_path: Path) -> None:
    records = {}
    for host in ("spark-a", "spark-b"):
        for cycle in (1, 2):
            for phase, rate in (("before-reset", 20.0), ("after-reset", 30.0), ("control", 19.0)):
                records[(host, cycle, phase)] = {"throughput_tokens_s": rate, "power_w": 80.0,
                                                  "clock_mhz": 2000.0, "link_gbps": 100.0}
    result = controls._power_compare(records, tmp_path / "commands.json", ["spark-a", "spark-b"], 2)
    assert result["status"] == "pass"
    assert "throughput_tokens_s after-before=[+10.000,+10.000,+10.000,+10.000]" in result["reason"]
    assert "power_w after-before=[+0.000" in result["reason"]
    assert "clock_mhz after-before=[+0.000" in result["reason"]
    assert "link_gbps after-before=[+0.000" in result["reason"]
    result = controls._power_compare(records, tmp_path / "commands.json", ["spark-a", "spark-b"], 3)
    assert result["status"] == "unknown"
    records[("spark-a", 1, "after-reset")]["throughput_tokens_s"] = 0
    result = controls._power_compare(records, tmp_path / "commands.json", ["spark-a", "spark-b"], 2)
    assert result["status"] == "fail" and "non-positive" in result["reason"]


def test_dualspark_native_capture_rejects_out_of_plan_host_and_failed_queries(tmp_path: Path) -> None:
    path = tmp_path / "commands.json"
    plan = {"model_sha256": "a" * 64, "input_sha256": "b" * 64, "concurrency": 1}
    row: dict[str, Any] = {"phase": "before-reset", "host": "other", "cycle": 1, "exit": 0,
                              "argv": ["cat", "sample.json"], "stdout": "{}"}
    records, error = controls._power_records({"commands": [row]}, path, ["spark"], 1, plan)
    assert records is None and error is not None and error["status"] == "fail"
    row.update({"host": "spark", "exit": 1})
    records, error = controls._power_records({"commands": [row]}, path, ["spark"], 1, plan)
    assert records is None and error is not None and "measurement failed" in error["reason"]
    row.update({"exit": 0, "stdout": "invalid json"})
    records, error = controls._power_records({"commands": [row]}, path, ["spark"], 1, plan)
    assert error is None and records == {}


def test_kv_metric_parser_keeps_baseline_and_quantized_native_counters_separate(tmp_path: Path) -> None:
    metric_output = ("process_resident_memory_bytes 1000\n"
                    "container_memory_working_set_bytes 1200\n"
                    "node_memory_MemAvailable_bytes 9000\n"
                    "node_memory_SwapFree_bytes 8000\n"
                    "vllm_kv_cache_usage_perc 0.25\n")
    rows = [
        {"argv": ["curl", "-fsS", "http://127.0.0.1:8000/metrics"], "exit": 0, "stdout": metric_output,
         "stderr": "", "captured_at": "2026-10-03T12:00:00Z", "phase": "baseline"},
        {"argv": ["curl", "-fsS", "http://127.0.0.1:8000/metrics"], "exit": 0, "stdout": metric_output.replace("1000", "800"),
         "stderr": "", "captured_at": "2026-10-03T12:01:00Z", "phase": "quantized"},
    ]
    snapshots, error = controls._kv_snapshots({"commands": rows}, tmp_path / "commands.json")
    assert error is None and snapshots is not None
    assert snapshots["baseline"][0]["process_resident_memory_bytes"] == 1000
    assert snapshots["quantized"][0]["process_resident_memory_bytes"] == 800

    rows.pop()
    snapshots, error = controls._kv_snapshots({"commands": rows}, tmp_path / "commands.json")
    assert snapshots is None and error is not None and error["status"] == "unknown"


def test_kv_contract_and_primary_source_denial_are_distinct(tmp_path: Path) -> None:
    path = tmp_path / "commands.json"
    complete = {"model_sha256": "a" * 64, "backend": "vllm", "baseline_kv_mode": "fp16",
                "quantized_kv_mode": "fp8", "input_sha256": "b" * 64,
                "context_tokens": 4096, "concurrency": 2}
    assert controls._kv_contract(complete, path) is None
    invalid = controls._kv_contract({**complete, "quantized_kv_mode": "fp16"}, path)
    assert invalid is not None and invalid["status"] == "fail"
    invalid = controls._kv_contract({**complete, "context_tokens": True}, path)
    assert invalid is not None and invalid["status"] == "unknown"

    identity = {"Manufacturer": "ASUS", "Product Name": "GX10", "BIOS Version": "1",
                "Kernel": "6.17"}
    positive_text = "GB10 vllm backend supported for ASUS GX10 BIOS 1 Linux kernel 6.17; validated deployment."
    denied_text = "GB10 vllm backend unsupported on ASUS GX10 BIOS 1 Linux kernel 6.17; validated exclusion."
    def ref(text: str) -> dict[str, str]:
        return {"url": "https://nvidia.com/support/gb10", "text": text,
                "sha256": hashlib.sha256(text.encode()).hexdigest()}
    refs, error = controls._kv_vendor_support({"vendor_sources": [ref(positive_text)]}, path,
                                               identity, {"backend": "vllm"})
    assert refs and error is None
    refs, error = controls._kv_vendor_support({"vendor_sources": [ref(denied_text)]}, path,
                                               identity, {"backend": "vllm"})
    assert refs is None and error is not None and error.startswith("source explicitly denies")
    unrelated_text = positive_text.replace("backend supported", "backend is listed").replace("validated", "documented")
    refs, error = controls._kv_vendor_support({"vendor_sources": [ref(unrelated_text)]},
                                               path, identity, {"backend": "vllm"})
    assert refs is None and error is not None and "directly connect" in error


def test_kv_snapshots_and_runs_reject_wrong_modes_and_incomplete_native_metrics(tmp_path: Path) -> None:
    path = tmp_path / "commands.json"
    metric = ("process_resident_memory_bytes 1000\ncontainer_memory_working_set_bytes 1200\n"
              "node_memory_MemAvailable_bytes 9000\nnode_memory_SwapFree_bytes 8000\n"
              "vllm_kv_cache_usage_perc 0.25\n")
    rows = [{"argv": ["curl", "-fsS", "http://localhost/metrics"], "exit": 0,
             "stdout": metric, "phase": phase} for phase in ("baseline", "quantized")]
    snapshots, error = controls._kv_snapshots({"commands": rows}, path)
    assert snapshots and error is None
    rows[1]["phase"] = "other"
    snapshots, error = controls._kv_snapshots({"commands": rows}, path)
    assert snapshots is None and error is not None and "phase binding" in error["reason"]
    rows[1]["phase"] = "quantized"
    rows[1]["stdout"] = "process_resident_memory_bytes NaN\n"
    snapshots, error = controls._kv_snapshots({"commands": rows}, path)
    assert snapshots is None and error is not None and "must remain separate" in error["reason"]

    plan = {"model_sha256": "a" * 64, "backend": "vllm", "baseline_kv_mode": "fp16",
            "quantized_kv_mode": "fp8", "input_sha256": "b" * 64,
            "context_tokens": 4096, "concurrency": 2}
    outputs = {"argv": ["cat", "result.json"], "exit": 0, "stdout": json.dumps({
        "model_sha256": "a" * 64, "backend": "vllm", "kv_mode": "fp16", "context_tokens": 4096,
        "concurrency": 2, "input_sha256": "b" * 64, "prefill_tokens_s": 10, "decode_tokens_s": 9,
        "correct_tokens": 10, "total_tokens": 10, "max_abs_error": 0.01})}
    baseline = {**outputs, "phase": "baseline"}
    quantized = {**outputs, "phase": "quantized", "stdout": outputs["stdout"].replace("fp16", "fp8")}
    results, error = controls._kv_runs({"commands": [baseline, quantized]}, path, plan)
    assert results and error is None
    quantized["exit"] = 9
    results, error = controls._kv_runs({"commands": [baseline, quantized]}, path, plan)
    assert results is None and error is not None and error["status"] == "fail"


def test_kv_orchestrator_preserves_unknown_and_negative_gate_order(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "commands.json"
    plan = {"reference_max_abs_error": 0.1}
    identity = {"Manufacturer": "ASUS"}
    snapshots = {"baseline": [{"rss": 10}], "quantized": [{"rss": 9}]}
    good_runs = [{"kv_mode": "fp16", "max_abs_error": 0.01},
                 {"kv_mode": "fp8", "max_abs_error": 0.02}]
    monkeypatch.setattr(controls, "_capture_plan", lambda data, evidence: (plan, None))
    monkeypatch.setattr(controls, "_kv_contract", lambda captured, evidence: None)
    monkeypatch.setattr(controls, "_identity", lambda data, evidence: (identity, None))
    monkeypatch.setattr(controls, "_kv_vendor_support", lambda data, evidence, captured_identity, captured_plan: ([{}], None))
    monkeypatch.setattr(controls, "_kv_snapshots", lambda data, evidence: (snapshots, None))
    monkeypatch.setattr(controls, "_kv_runs", lambda data, evidence, captured_plan: (good_runs, None))

    def evaluate() -> dict[str, Any]:
        return controls._kv_quant({}, path)

    assert evaluate()["status"] == "pass"
    monkeypatch.setattr(controls, "_capture_plan", lambda data, evidence: (None, {"status": "unknown", "reason": "no plan"}))
    assert evaluate()["status"] == "unknown"
    monkeypatch.setattr(controls, "_capture_plan", lambda data, evidence: (plan, None))
    monkeypatch.setattr(controls, "_kv_contract", lambda captured, evidence: {"status": "fail", "reason": "bad contract"})
    assert evaluate()["status"] == "fail"
    monkeypatch.setattr(controls, "_kv_contract", lambda captured, evidence: None)
    monkeypatch.setattr(controls, "_identity", lambda data, evidence: (None, {"status": "unknown", "reason": "no identity"}))
    assert evaluate()["status"] == "unknown"
    monkeypatch.setattr(controls, "_identity", lambda data, evidence: (identity, None))
    monkeypatch.setattr(controls, "_kv_vendor_support", lambda *args: (None, "source explicitly denies backend"))
    assert evaluate()["status"] == "fail"
    monkeypatch.setattr(controls, "_kv_vendor_support", lambda *args: (None, "no primary source"))
    assert evaluate()["status"] == "unknown"
    monkeypatch.setattr(controls, "_kv_vendor_support", lambda *args: ([{}], None))
    monkeypatch.setattr(controls, "_kv_snapshots", lambda data, evidence: (None, {"status": "unknown", "reason": "metrics absent"}))
    assert evaluate()["status"] == "unknown"
    monkeypatch.setattr(controls, "_kv_snapshots", lambda data, evidence: ({"baseline": [], "quantized": [{}]}, None))
    assert evaluate()["status"] == "unknown"
    monkeypatch.setattr(controls, "_kv_snapshots", lambda data, evidence: (snapshots, None))
    monkeypatch.setattr(controls, "_kv_runs", lambda data, evidence, captured_plan: (None, {"status": "fail", "reason": "bad run"}))
    assert evaluate()["status"] == "fail"
    monkeypatch.setattr(controls, "_kv_runs", lambda data, evidence, captured_plan: ([{"kv_mode": "fp16"}], None))
    assert evaluate()["status"] == "unknown"
    monkeypatch.setattr(controls, "_kv_runs", lambda data, evidence, captured_plan: (good_runs, None))
    plan.pop("reference_max_abs_error")
    assert evaluate()["status"] == "unknown"
    plan["reference_max_abs_error"] = 0.005
    assert evaluate()["status"] == "fail"


def test_ota_tuple_fields_require_their_native_readback_sources() -> None:
    assert controls._ota_fields_from_row({"argv": ["cat", "/tmp/invented.txt"], "stdout": "Linux host 6.17\n"}) == {}
    assert controls._ota_fields_from_row({"argv": ["uname", "-r"], "stdout": "6.17.0-1029\n"}) == {
        "kernel_release": "6.17.0-1029"}
    assert controls._ota_fields_from_row({"argv": ["modinfo", "-F", "version", "nvidia"], "stdout": "580.178.04\n"}) == {
        "disk_driver": "580.178.04"}


def test_ota_soak_contract_rejects_missing_and_ill_typed_plan_fields(tmp_path: Path) -> None:
    path = tmp_path / "commands.json"
    spec = {"argv": ["python", "infer.py"], "model_sha256": "a" * 64,
            "input_sha256": "b" * 64, "pid": 42, "duration_seconds": 3600,
            "max_sample_gap_seconds": 60}
    assert controls._ota_soak_contract({"workload_soak": spec}, path) == (spec, None)
    for altered in (
        {}, {"workload_soak": []}, {"workload_soak": {**spec, "argv": ["python", ""]}},
        {"workload_soak": {**spec, "model_sha256": "a" * 63}},
        {"workload_soak": {**spec, "pid": True}},
        {"workload_soak": {**spec, "duration_seconds": 0}},
        {"workload_soak": {**spec, "max_sample_gap_seconds": True}},
    ):
        parsed, error = controls._ota_soak_contract(altered, path)
        assert parsed is None and error is not None and error["status"] == "unknown"


def test_ota_native_soak_samples_reject_missing_bad_and_false_workload_rows(tmp_path: Path) -> None:
    path = tmp_path / "commands.json"
    spec = {"argv": ["python", "infer.py"], "model_sha256": "a" * 64,
            "input_sha256": "b" * 64, "pid": 42, "duration_seconds": 3600,
            "max_sample_gap_seconds": 60}

    def sample_rows(options: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        options = options or {}
        pid, state = options.get("pid", 42), options.get("state", "R")
        requests, completed = options.get("requests", 4), options.get("completed", 4)
        model = options.get("model", "a" * 64)
        captured_at = options.get("captured_at", "2026-10-03T12:00:00Z")
        common = {"exit": 0, "stderr": "", "captured_at": captured_at}
        return [
            {**common, "argv": ["free", "-b"],
             "stdout": "Mem: 100000 20000 30000 4000 5000 60000\n"},
            {**common, "argv": ["cat", "/proc/pressure/memory"],
             "stdout": "some avg10=0.10 avg60=0.05 avg300=0.01 total=100\n"},
            {**common, "argv": ["python", "infer.py"],
             "stdout": json.dumps({"pid": 42, "model_sha256": model, "input_sha256": "b" * 64,
                                   "requests": requests, "completed": completed})},
            {**common, "argv": ["ps", "-p", "42", "-o", "pid=,stat=,lstart="],
             "stdout": f"{pid} {state} 4096 Sat Oct  3 11:00:00 2026\n"},
        ]

    parsed, error = controls._ota_soak_sample(sample_rows(), "s1", spec, path)
    assert parsed is not None and error is None
    for rows, phrase, expected in (
        (sample_rows()[:3], "lacks native", "unknown"),
        ([{**row, "exit": 2} if row["argv"][0] == "free" else row for row in sample_rows()], "command failed", "fail"),
        (sample_rows({"captured_at": "invalid"}), "invalid command times", "unknown"),
        ([{**row, "stdout": "bad"} if row["argv"][0] == "free" else row for row in sample_rows()], "parseable", "unknown"),
        (sample_rows({"pid": 43}), "PID is absent", "fail"),
        (sample_rows({"state": "Z"}), "PID is absent", "fail"),
        (sample_rows({"model": "c" * 64}), "does not bind", "fail"),
        (sample_rows({"completed": 3}), "did not complete", "fail"),
    ):
        parsed, error = controls._ota_soak_sample(rows, "s1", spec, path)
        assert parsed is None and error is not None and error["status"] == expected and phrase in error["reason"], error


def test_rdma_complete_observations_pass_and_directional_regression_fails(tmp_path: Path) -> None:
    finding_id = "DELTA-FORUM-CX7-RDMA-ASYMMETRY-RETEST-01"
    host_tuples = {
        "spark": {"manufacturer": "NVIDIA", "product": "DGX Spark", "bios": "1.0", "kernel": "6.17.0", "firmware": "28.45.1"},
        "gx10": {"manufacturer": "ASUS", "product": "GX10", "bios": "2.0", "kernel": "6.17.1", "firmware": "28.45.2"},
    }
    plan = {"scenarios": ["cold", "reboot-individual", "reboot-sequential", "hotplug"],
            "max_directional_ratio": 1.5, "hosts": ["spark", "gx10"], "host_tuples": host_tuples}
    rows: list[dict[str, Any]] = []

    def add(argv: list[str], stdout: str, phase: str | None = None) -> None:
        row: dict[str, Any] = {"argv": argv, "exit": 0, "stdout": stdout, "stderr": "",
                                  "captured_at": f"2026-10-03T12:{len(rows):02d}:00Z"}
        if phase is not None:
            row["phase"] = phase
        rows.append(row)

    add(["cat", "experiment-plan.json"], json.dumps(plan))
    scope_hash = __import__("hashlib").sha256(json.dumps(plan, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    for host, values in host_tuples.items():
        add(["ssh", host, "dmidecode", "-t", "system"],
            f"Manufacturer: {values['manufacturer']}\nProduct Name: {values['product']}\nBIOS Version: {values['bios']}\n")
        add(["ssh", host, "uname", "-r"], values["kernel"])
        add(["ssh", host, "ethtool", "-i", "enp1s0"], f"firmware-version: {values['firmware']}\n")
    source_text = "Primary OEM compatibility data. " + " ".join(value for host in host_tuples.values() for value in host.values())
    import hashlib
    refs = [{"url": "https://nvidia.com/support/cx7", "text": source_text,
             "sha256": hashlib.sha256(source_text.encode()).hexdigest()}]
    for scenario in plan["scenarios"]:
        for direction in ("spark_to_gx10", "gx10_to_spark"):
            add(["ib_write_bw", "-D", "30", "--report_gbits"],
                "#bytes #iterations BW peak[MB/sec] BW average[MB/sec]\n1048576 1000 15000.0 14000.0\n",
                f"{scenario}:{direction}")
    add(["mlxlink", "-d", "03:00.0", "-m"], "PN: DAC-PN-42\n")
    bundle = {"schema": 1, "id": finding_id, "experiment_plan": plan, "vendor_sources": refs, "commands": rows}
    evidence = tmp_path / finding_id
    evidence.mkdir()
    capture_path = evidence / "commands.json"
    capture_path.write_text(json.dumps(bundle), encoding="utf-8")
    result = controls.verify(finding_id, evidence, trusted_plan_sha256=scope_hash)
    assert result["status"] == "pass", result

    original_reference = source_text
    mismatched_reference = source_text.replace("6.17.0", "6.17.9")
    refs[0]["text"] = mismatched_reference
    refs[0]["sha256"] = hashlib.sha256(mismatched_reference.encode()).hexdigest()
    capture_path.write_text(json.dumps(bundle), encoding="utf-8")
    result = controls.verify(finding_id, evidence, trusted_plan_sha256=scope_hash)
    assert result["status"] == "unknown" and "does not cite captured tuple" in result["reason"]
    refs[0]["text"] = original_reference
    refs[0]["sha256"] = hashlib.sha256(original_reference.encode()).hexdigest()

    for row in rows:
        if str(row.get("phase")) == "hotplug:spark_to_gx10":
            row["stdout"] = "#bytes #iterations BW peak[MB/sec] BW average[MB/sec]\n1048576 1000 15000.0 100.0\n"
            break
    capture_path.write_text(json.dumps(bundle), encoding="utf-8")
    result = controls.verify(finding_id, evidence, trusted_plan_sha256=scope_hash)
    assert result["status"] == "fail", result


def test_rdma_stack_identity_recomputes_each_remote_oem_firmware_tuple(tmp_path: Path) -> None:
    path = tmp_path / "commands.json"
    hosts = ["spark", "gx10"]
    tuples = {
        "spark": {"manufacturer": "NVIDIA", "product": "DGX Spark", "bios": "1.0", "kernel": "6.17.0", "firmware": "28.45.1"},
        "gx10": {"manufacturer": "ASUS", "product": "GX10", "bios": "2.0", "kernel": "6.17.1", "firmware": "28.45.2"},
    }
    commands: list[dict[str, Any]] = []
    for host, values in tuples.items():
        commands.extend([
            {"argv": ["ssh", host, "dmidecode", "-t", "system"], "exit": 0,
             "stdout": f"Manufacturer: {values['manufacturer']}\nProduct Name: {values['product']}\nBIOS Version: {values['bios']}\n"},
            {"argv": ["ssh", host, "uname", "-r"], "exit": 0, "stdout": values["kernel"]},
            {"argv": ["ssh", host, "ethtool", "-i", "eth0"], "exit": 0,
             "stdout": f"firmware-version: {values['firmware']}\n"},
        ])
    text = "Primary OEM support reference " + " ".join(str(value) for fields in tuples.values() for value in fields.values())
    plan = {"hosts": hosts, "host_tuples": tuples}
    data = {"commands": commands, "vendor_sources": [{"url": "https://nvidia.com/support/cx7", "text": text,
                                                          "sha256": hashlib.sha256(text.encode()).hexdigest()}]}
    assert controls._rdma_stack_identity(data, path, plan) is None
    missing = {**data, "commands": commands[:-1]}
    error = controls._rdma_stack_identity(missing, path, plan)
    assert error is not None and error["status"] == "unknown"
    failed = {**data, "commands": [{**row, "exit": 2} if row["argv"][:3] == ["ssh", "gx10", "uname"] else row
                                    for row in commands]}
    error = controls._rdma_stack_identity(failed, path, plan)
    assert error is not None and error["status"] == "fail"
    incomplete = {**data, "commands": [{**row, "stdout": "Manufacturer: ASUS\n"}
                                       if row["argv"][:3] == ["ssh", "gx10", "dmidecode"] else row for row in commands]}
    error = controls._rdma_stack_identity(incomplete, path, plan)
    assert error is not None and error["status"] == "unknown"
    wrong_plan = {**plan, "host_tuples": {**tuples, "gx10": {**tuples["gx10"], "bios": "3.0"}}}
    error = controls._rdma_stack_identity(data, path, wrong_plan)
    assert error is not None and error["status"] == "fail"
    no_source = {**data, "vendor_sources": []}
    error = controls._rdma_stack_identity(no_source, path, plan)
    assert error is not None and error["status"] == "unknown"


def test_rdma_asymmetry_requires_plan_approval_cable_and_all_scenario_pairs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "commands.json"
    scenarios = ["cold", "reboot-individual", "reboot-sequential", "hotplug"]
    plan = {"scenarios": scenarios, "max_directional_ratio": 1.5}
    monkeypatch.setattr(controls, "_capture_plan", lambda data, evidence: (plan, None))
    monkeypatch.setattr(controls, "_plan_approval", lambda data, evidence, captured: None)
    monkeypatch.setattr(controls, "_rdma_stack_identity", lambda data, evidence, captured: None)
    monkeypatch.setattr(controls, "_asymmetry_pair", lambda data, scenario, evidence: ({"spark_to_gx10": 100.0,
                       "gx10_to_spark": 90.0}, None))
    cable = {"argv": ["mlxlink", "-m"], "exit": 0, "stdout": "PN: DAC-42\n"}
    assert controls._rdma_asymmetry({"commands": [cable]}, path)["status"] == "pass"
    assert controls._rdma_asymmetry({"commands": []}, path)["status"] == "unknown"
    assert controls._rdma_asymmetry({"commands": [{**cable, "exit": 1}]}, path)["status"] == "unknown"
    assert controls._rdma_asymmetry({"commands": [{**cable, "stdout": "no part number"}]}, path)["status"] == "unknown"

    monkeypatch.setattr(controls, "_asymmetry_pair", lambda data, scenario, evidence: (
        None, {"status": "fail", "reason": "failed directional measurement"}))
    assert controls._rdma_asymmetry({"commands": [cable]}, path)["status"] == "fail"
    monkeypatch.setattr(controls, "_asymmetry_pair", lambda data, scenario, evidence: (
        {"spark_to_gx10": 100.0, "gx10_to_spark": 10.0}, None))
    assert controls._rdma_asymmetry({"commands": [cable]}, path)["status"] == "fail"
    monkeypatch.setattr(controls, "_asymmetry_pair", lambda data, scenario, evidence: (
        {"spark_to_gx10": 100.0, "gx10_to_spark": 90.0}, None))
    monkeypatch.setattr(controls, "_plan_approval", lambda data, evidence, captured: {"status": "unknown"})
    assert controls._rdma_asymmetry({"commands": [cable]}, path)["status"] == "unknown"


def test_recovery_runbook_complete_native_reads_pass_hash_mismatch_fails(tmp_path: Path) -> None:
    finding_id = "DELTA-FORUM-RECOVERY-APT-UPDATE-01"
    media_path = "/mnt/recovery/oem-media.iso"
    digest = "a" * 64
    plan = {"last_kernel": "6.17.0-1029", "last_driver": "580.178.04", "last_package": "nvidia-driver-580",
            "console_route": "recovery-console", "recovery_media_path": media_path,
            "recovery_media_sha256": digest, "oem_recovery_url": "https://asus.com/gx10/recovery"}
    source_text = ("ASUS GX10 recovery instructions for kernel 6.17.0-1029 driver 580.178.04 package "
                   "nvidia-driver-580: preserve crash data, use external console and recovery image, then rollback or RMA.")
    rows: list[dict[str, Any]] = []

    def add(argv: list[str], stdout: str) -> None:
        rows.append({"argv": argv, "exit": 0, "stdout": stdout, "stderr": "",
                     "captured_at": f"2026-10-03T12:{len(rows):02d}:00Z"})

    add(["cat", "experiment-plan.json"], json.dumps(plan))
    add(["zgrep", "nvidia-driver-580", "/var/log/dpkg.log*"],
        "2026-10-01 install linux-image-6.17.0-1029\n2026-10-01 install nvidia-driver-580\n")
    add(["ssh", "recovery-console", "true"], "console reachable\n")
    rows.append({"argv": ["cat", "/mnt/recovery/runbook.md"], "exit": 0,
                 "stdout": "Preserve logs and preserve crash data. Connect external console. Verify media. Rollback to known kernel. Contact OEM for RMA.\n",
                 "stderr": "", "captured_at": f"2026-10-03T12:{len(rows):02d}:00Z", "phase": "recovery-runbook"})
    add(["sha256sum", media_path], f"{digest}  {media_path}\n")
    bundle = {"schema": 1, "id": finding_id, "experiment_plan": plan,
              "vendor_sources": [{"url": plan["oem_recovery_url"], "text": source_text,
                                  "sha256": __import__("hashlib").sha256(source_text.encode()).hexdigest()}],
              "commands": rows}
    evidence = tmp_path / finding_id
    evidence.mkdir()
    capture = evidence / "commands.json"
    capture.write_text(json.dumps(bundle), encoding="utf-8")
    result = controls.verify(finding_id, evidence)
    assert result["status"] == "pass", result

    bundle["commands"][-1]["stdout"] = f"{'b' * 64}  {media_path}\n"
    capture.write_text(json.dumps(bundle), encoding="utf-8")
    result = controls.verify(finding_id, evidence)
    assert result["status"] == "fail", result
    bundle["commands"][-1]["stdout"] = f"{digest}  {media_path}\n"
    plan["recovery_media_sha256"] = "malformed"
    bundle["commands"][0]["stdout"] = json.dumps(plan)
    capture.write_text(json.dumps(bundle), encoding="utf-8")
    result = controls.verify(finding_id, evidence)
    assert result["status"] == "fail" and "digest malformed" in result["reason"]
    plan["recovery_media_sha256"] = digest
    plan.pop("last_kernel")
    bundle["commands"][0]["stdout"] = json.dumps(plan)
    capture.write_text(json.dumps(bundle), encoding="utf-8")
    result = controls.verify(finding_id, evidence)
    assert result["status"] == "unknown" and "lacks kernel" in result["reason"]


def test_recovery_subcontrols_reject_unbound_package_console_and_media_records(tmp_path: Path) -> None:
    path = tmp_path / "commands.json"
    plan: dict[str, Any] = {"last_kernel": "6.17.0", "last_driver": "580.1", "last_package": "fw-pkg",
        "console_route": "serial-console", "recovery_media_path": "/mnt/oem/recovery.iso",
        "recovery_media_sha256": "a" * 64, "oem_recovery_url": "https://asus.com/recovery"}
    text = "ASUS OEM recovery guide for kernel 6.17.0 driver 580.1 fw-pkg at recovery URL; verified media instructions."
    ref = {"url": plan["oem_recovery_url"], "text": text,
           "sha256": hashlib.sha256(text.encode()).hexdigest()}
    good_dpkg = {"argv": ["zgrep", "fw-pkg", "/var/log/dpkg.log"], "exit": 0,
                 "stdout": "install linux 6.17.0\ninstall nvidia 580.1\ninstall fw-pkg\n"}
    data = {"vendor_sources": [ref], "commands": [good_dpkg]}
    assert controls._recovery_packages(data, path, plan) is None
    no_tuple = controls._recovery_packages({**data, "commands": [{**good_dpkg, "stdout": "no package history\n"}]}, path, plan)
    assert no_tuple is not None and no_tuple["status"] == "unknown"
    no_source = controls._recovery_packages({**data, "vendor_sources": []}, path, plan)
    assert no_source is not None and no_source["status"] == "unknown"
    wrong_url = controls._recovery_packages({**data, "vendor_sources": [{**ref, "url": "https://nvidia.com/recovery"}]}, path, plan)
    assert wrong_url is not None and wrong_url["status"] == "unknown"

    runbook = {"argv": ["cat", "runbook.md"], "exit": 0,
               "stdout": "Preserve evidence. External console. Verify media. Rollback to kernel. RMA path.",
               "phase": "recovery-runbook"}
    console = {"argv": ["ssh", "serial-console", "true"], "exit": 0, "stdout": "reachable"}
    assert controls._recovery_access({"experiment_plan": plan, "commands": [console, runbook]}, path) is None
    unreachable = controls._recovery_access({"experiment_plan": plan,
        "commands": [{**console, "stdout": "failed"}, runbook]}, path)
    assert unreachable is not None and unreachable["status"] == "fail"
    incomplete = controls._recovery_access({"experiment_plan": plan,
        "commands": [console, {**runbook, "stdout": "Rollback only"}]}, path)
    assert incomplete is not None and incomplete["status"] == "fail"

    digest = {"argv": ["sha256sum", "/mnt/oem/recovery.iso"], "exit": 0,
              "stdout": f"{'a' * 64}  /mnt/oem/recovery.iso\n"}
    assert controls._recovery_media({"experiment_plan": plan, "commands": [digest]}, path, plan) is None
    malformed = controls._recovery_media({"experiment_plan": plan,
        "commands": [{**digest, "stdout": "hash unavailable"}]}, path, plan)
    assert malformed is not None and malformed["status"] == "unknown"


def test_dualspark_repeated_ab_control_samples_pass_and_mismatched_input_fails(tmp_path: Path) -> None:
    finding_id = "DELTA-FORUM-DUALSPARK-POWER-RESET-RECOVERY-01"
    hosts = ["spark-a", "spark-b"]
    tuples = {host: {"manufacturer": "NVIDIA", "product": "DGX Spark", "bios": "1.0", "kernel": "6.17.0", "firmware": "28.45.1"} for host in hosts}
    model_hash, input_hash = "c" * 64, "d" * 64
    plan = {"hosts": hosts, "host_tuples": tuples, "cycles": 2, "oem_power_procedure": "https://nvidia.com/support/spark/shutdown",
            "model_sha256": model_hash, "input_sha256": input_hash, "concurrency": 4}
    rows: list[dict[str, Any]] = []

    def add(argv: list[str], stdout: str, phase: str | None = None, **metadata: Any) -> None:
        row: dict[str, Any] = {"argv": argv, "exit": 0, "stdout": stdout, "stderr": "",
                                  "captured_at": f"2026-10-03T12:{len(rows):02d}:00Z", **metadata}
        if phase is not None:
            row["phase"] = phase
        rows.append(row)

    add(["cat", "experiment-plan.json"], json.dumps(plan))
    scope_hash = __import__("hashlib").sha256(json.dumps(plan, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    for host, values in tuples.items():
        add(["ssh", host, "dmidecode", "-t", "system"], f"Manufacturer: {values['manufacturer']}\nProduct Name: {values['product']}\nBIOS Version: {values['bios']}\n")
        add(["ssh", host, "uname", "-r"], values["kernel"])
        add(["ssh", host, "ethtool", "-i", "enp1s0"], f"firmware-version: {values['firmware']}\n")
    text = "Primary NVIDIA compatibility source " + " ".join(v for item in tuples.values() for v in item.values())
    refs = [{"url": "https://nvidia.com/support/spark/shutdown", "text": text,
             "sha256": __import__("hashlib").sha256(text.encode()).hexdigest()}]
    for host in hosts:
        for cycle in (1, 2):
            for phase, throughput in (("before-reset", 20.0), ("after-reset", 21.0), ("control", 19.5)):
                sample = {"power_w": 80.0, "clock_mhz": 2100.0, "throughput_tokens_s": throughput,
                          "link_gbps": 100.0, "model_sha256": model_hash, "input_sha256": input_hash,
                          "concurrency": 4}
                add(["cat", f"/evidence/{host}-{cycle}-{phase}.json"], json.dumps(sample), phase,
                    host=host, cycle=cycle)
    bundle = {"schema": 1, "id": finding_id, "experiment_plan": plan, "vendor_sources": refs, "commands": rows}
    evidence = tmp_path / finding_id
    evidence.mkdir()
    capture = evidence / "commands.json"
    capture.write_text(json.dumps(bundle), encoding="utf-8")
    result = controls.verify(finding_id, evidence, trusted_plan_sha256=scope_hash)
    assert result["status"] == "pass", result

    for row in rows:
        if row.get("phase") == "after-reset" and row.get("host") == "spark-a" and row.get("cycle") == 1:
            sample = json.loads(str(row["stdout"]))
            sample["input_sha256"] = "e" * 64
            row["stdout"] = json.dumps(sample)
            break
    capture.write_text(json.dumps(bundle), encoding="utf-8")
    result = controls.verify(finding_id, evidence, trusted_plan_sha256=scope_hash)
    assert result["status"] == "fail", result


def test_dualspark_preconditions_and_identity_gates_stop_before_measurement(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "commands.json"
    plan: dict[str, Any] = {"hosts": ["spark-a", "spark-b"], "cycles": 2,
        "oem_power_procedure": "https://nvidia.com/power", "model_sha256": "a" * 64,
        "input_sha256": "b" * 64}
    monkeypatch.setattr(controls, "_capture_plan", lambda data, evidence: (plan, None))
    monkeypatch.setattr(controls, "_plan_approval", lambda data, evidence, captured: None)
    monkeypatch.setattr(controls, "_rdma_stack_identity", lambda data, evidence, captured: None)
    monkeypatch.setattr(controls, "_power_records", lambda data, evidence, hosts, cycles, captured: ({}, None))
    monkeypatch.setattr(controls, "_power_compare", lambda records, evidence, hosts, cycles: {"status": "pass"})

    def evaluate() -> dict[str, Any]:
        return controls._dual_spark({}, path)

    assert evaluate()["status"] == "pass"
    for key, bad in (("hosts", ["spark-a"]), ("hosts", ["same", "same"]),
                     ("cycles", 1), ("oem_power_procedure", ""),
                     ("model_sha256", "bad"), ("input_sha256", "bad")):
        original = plan[key]
        plan[key] = bad
        assert evaluate()["status"] == "unknown"
        plan[key] = original
    monkeypatch.setattr(controls, "_plan_approval", lambda data, evidence, captured: {"status": "unknown"})
    assert evaluate()["status"] == "unknown"
    monkeypatch.setattr(controls, "_plan_approval", lambda data, evidence, captured: None)
    monkeypatch.setattr(controls, "_rdma_stack_identity", lambda data, evidence, captured: {"status": "fail"})
    assert evaluate()["status"] == "fail"
    monkeypatch.setattr(controls, "_rdma_stack_identity", lambda data, evidence, captured: None)
    monkeypatch.setattr(controls, "_power_records", lambda data, evidence, hosts, cycles, captured: (None, {"status": "unknown"}))
    assert evaluate()["status"] == "unknown"


def test_physical_topology_native_map_and_disconnected_negative(tmp_path: Path) -> None:
    finding_id = "DELTA-FORUM-CX7-PHYSICAL-TOPOLOGY-ALIAS-CHECK-01"
    plan = {"links": [{"bdf": "0000:03:00.0", "netdev": "enp3s0f0np0", "local_port": "enp3s0f0np0", "peer_port": "swp1"},
                       {"bdf": "0000:03:00.1", "netdev": "enp3s0f1np1", "local_port": "enp3s0f1np1", "peer_port": "swp2"}],
            "minimum_gbps": 50.0, "traffic_seconds": 10}
    rows: list[dict[str, Any]] = []

    def add(argv: list[str], stdout: str, phase: str | None = None, exit_code: int = 0) -> None:
        row: dict[str, Any] = {"argv": argv, "exit": exit_code, "stdout": stdout, "stderr": "",
                                  "captured_at": f"2026-10-03T12:{len(rows):02d}:00Z"}
        if phase is not None:
            row["phase"] = phase
        rows.append(row)

    add(["cat", "experiment-plan.json"], json.dumps(plan))
    add(["dmidecode", "-t", "system"], "Manufacturer: NVIDIA\nProduct Name: DGX Spark\nBIOS Version: 1.0\n")
    add(["uname", "-r"], "6.17.0-1029\n")
    add(["lspci", "-D", "-nnk"], "0000:03:00.0 Ethernet controller: Mellanox 15b3:101d\n0000:03:00.1 Ethernet controller: Mellanox 15b3:101d\n")
    add(["ethtool", "-i", "enp3s0f0np0"], "bus-info: 0000:03:00.0\n")
    add(["ethtool", "-i", "enp3s0f1np1"], "bus-info: 0000:03:00.1\n")
    peers = {"interfaces": [{"local_port": "enp3s0f0np0", "peer_port": "swp1"},
                             {"local_port": "enp3s0f1np1", "peer_port": "swp2"}]}
    add(["lldpctl", "-f", "json"], json.dumps(peers))
    add(["ib_write_bw", "-D", "10"], "No route to host\n", "negative", 1)
    add(["ib_write_bw", "-D", "10", "--report_gbits"],
        "#bytes #iterations BW peak[MB/sec] BW average[MB/sec]\n1048576 1000 8000.0 7000.0\n", "positive")
    add(["all_reduce_perf", "-b", "8", "-e", "1G"], "# size count time algbw busbw #wrong\n1024 256 1.2 3.4 2.5 0\n")
    bundle = {"schema": 1, "id": finding_id, "experiment_plan": plan, "commands": rows}
    evidence = tmp_path / finding_id
    evidence.mkdir()
    capture = evidence / "commands.json"
    capture.write_text(json.dumps(bundle), encoding="utf-8")
    result = controls.verify(finding_id, evidence)
    assert result["status"] == "pass", result

    plan["links"][1]["bdf"] = plan["links"][0]["bdf"]
    capture.write_text(json.dumps(bundle), encoding="utf-8")
    result = controls.verify(finding_id, evidence)
    assert result["status"] == "fail", result


def test_cutlass_sm121_complete_canary_recomputes_logits_and_rejects_bad_accuracy(tmp_path: Path) -> None:
    finding_id = "DELTA-FORUM-CUTLASS-SM121-ISA-GATE-01"
    plan = {"cutlass_revision": "cutlass-abc123", "cute_revision": "cute-def456", "backend": "cuda",
            "operation": "gemm-f16", "model_sha256": "a" * 64, "input_sha256": "b" * 64,
            "batch_size": 2, "concurrency": 2, "soak_seconds": 10, "reference_max_abs_error": 0.01}
    rows: list[dict[str, Any]] = []

    def add(argv: list[str], stdout: str, phase: str | None = None, exit_code: int = 0) -> None:
        row: dict[str, Any] = {"argv": argv, "exit": exit_code, "stdout": stdout, "stderr": "",
                                  "captured_at": f"2026-10-03T12:{len(rows):02d}:00Z"}
        if phase is not None:
            row["phase"] = phase
        rows.append(row)

    add(["cat", "experiment-plan.json"], json.dumps(plan))
    add(["dmidecode", "-t", "system"], "Manufacturer: NVIDIA\nProduct Name: DGX Spark\nBIOS Version: 1.0\n")
    add(["uname", "-r"], "6.17.0-1029\n")
    add(["nvidia-smi", "--query-gpu=name,compute_cap,driver_version", "--format=csv,noheader"], "GB10, 12.1, 580.178.04\n")
    add(["cmake", "-DCUTLASS_REVISION=cutlass-abc123", "-DCUTE_REVISION=cute-def456", "-DBACKEND=cuda", "-DOPERATION=gemm-f16"],
        "CUTLASS cutlass-abc123 CuTe cute-def456 backend cuda operation gemm-f16\n", "build")
    add(["cuobjdump", "--list-elf", "kernel.so"], "ELF image: sm_121\n")
    canary = {"requests": 20, "completed": 20, "batch_size": 2, "concurrency": 2,
              "duration_seconds": 12.0, "logits": [1.0, 2.0], "reference_logits": [1.001, 2.002]}
    add(["cat", "/tmp/sm121-canary.json"], json.dumps(canary), "canary")
    add(["nvcc", "--gpu-architecture=sm_121", "tcgen05"], "unsupported instruction requires sm_100", "negative", 1)
    bundle = {"schema": 1, "id": finding_id, "experiment_plan": plan, "commands": rows}
    evidence = tmp_path / finding_id
    evidence.mkdir()
    capture = evidence / "commands.json"
    capture.write_text(json.dumps(bundle), encoding="utf-8")
    result = controls.verify(finding_id, evidence)
    assert result["status"] == "pass", result

    canary["logits"] = [1.2, 2.0]
    rows[-2]["stdout"] = json.dumps(canary)
    capture.write_text(json.dumps(bundle), encoding="utf-8")
    result = controls.verify(finding_id, evidence)
    assert result["status"] == "fail", result



def test_cutlass_invalid_contract_and_negative_isa_are_discriminated(tmp_path: Path) -> None:
    path = tmp_path / "commands.json"
    plan = {"cutlass_revision": "abc", "cute_revision": "def", "backend": "cuda", "operation": "gemm",
            "model_sha256": "a" * 64, "input_sha256": "b" * 64, "batch_size": 1, "concurrency": 1,
            "soak_seconds": 10, "reference_max_abs_error": 0.1}
    assert _status(controls._cutlass_plan({**plan, "batch_size": True}, path)) == "unknown"
    assert _status(controls._cutlass_plan({**plan, "backend": " "}, path)) == "unknown"
    canary = {"argv": ["cat", "result.json"], "exit": 0,
              "stdout": json.dumps({"requests": 1, "completed": 1, "batch_size": 1, "concurrency": 1,
                                    "duration_seconds": 10, "logits": [1.0], "reference_logits": []}),
              "phase": "canary"}
    result = controls._cutlass_canary({"commands": [canary]}, path, plan)
    assert result is not None and result["status"] == "unknown" and "aligned finite logits" in result["reason"]
    canary["stdout"] = "not-json"
    result = controls._cutlass_canary({"commands": [canary]}, path, plan)
    assert result is not None and result["status"] == "fail" and "finite JSON" in result["reason"]
    assert _status(controls._cutlass_negative({"commands": []}, path)) == "unknown"
    negative = {"argv": ["nvcc", "tcgen05"], "exit": 0, "stdout": "", "stderr": "", "phase": "negative"}
    result = controls._cutlass_negative({"commands": [negative]}, path)
    assert result is not None and result["status"] == "fail" and "accepted" in result["reason"]
    negative.update({"exit": 1, "stderr": "compiler crashed"})
    result = controls._cutlass_negative({"commands": [negative]}, path)
    assert result is not None and result["status"] == "fail" and "early ISA rejection" in result["reason"]


def test_cutlass_canary_binds_workload_counts_shape_and_predeclared_error_bound(tmp_path: Path) -> None:
    path = tmp_path / "commands.json"
    plan = {"batch_size": 1, "concurrency": 2, "soak_seconds": 30, "reference_max_abs_error": 0.1}
    base = {"requests": 10, "completed": 10, "batch_size": 1, "concurrency": 2,
            "duration_seconds": 30, "logits": [0.4, 0.6], "reference_logits": [0.4, 0.6]}
    row = {"argv": ["cat", "canary.json"], "exit": 0, "phase": "canary", "stdout": json.dumps(base)}
    assert controls._cutlass_canary({"commands": [row]}, path, plan) is None
    missing = controls._cutlass_canary({"commands": []}, path, plan)
    assert missing is not None and missing["status"] == "unknown"
    no_measurements = controls._cutlass_canary({"commands": [{**row, "stdout": "{}"}]}, path, plan)
    assert no_measurements is not None and no_measurements["status"] == "unknown"
    for payload, status, phrase in (
        ({**base, "requests": 0}, "fail", "canary requests"),
        ({**base, "completed": 9}, "fail", "canary requests"),
        ({**base, "batch_size": 4}, "fail", "canary requests"),
        ({**base, "duration_seconds": 5}, "fail", "canary requests"),
        ({**base, "reference_logits": [0.4, 0.8]}, "fail", "exceeds predeclared"),
    ):
        error = controls._cutlass_canary({"commands": [{**row, "stdout": json.dumps(payload)}]}, path, plan)
        assert error is not None and error["status"] == status and phrase in error["reason"]
    no_tolerance = controls._cutlass_canary({"commands": [row]}, path, {**plan, "reference_max_abs_error": None})
    assert no_tolerance is not None and no_tolerance["status"] == "unknown"


def test_cutlass_orchestrator_stops_on_first_missing_gate(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    path = tmp_path / "commands.json"
    plan = {"cutlass_revision": "c1", "cute_revision": "t1", "backend": "cuda", "operation": "gemm",
            "model_sha256": "a" * 64, "input_sha256": "b" * 64, "batch_size": 1,
            "concurrency": 1, "soak_seconds": 1}
    monkeypatch.setattr(controls, "_capture_plan", lambda data, evidence: (plan, None))
    monkeypatch.setattr(controls, "_cutlass_plan", lambda captured, evidence: None)
    monkeypatch.setattr(controls, "_cutlass_build", lambda data, evidence, captured: {"status": "unknown", "reason": "build unavailable"})
    assert controls._cutlass({}, path)["reason"] == "build unavailable"
    monkeypatch.setattr(controls, "_cutlass_build", lambda data, evidence, captured: None)
    monkeypatch.setattr(controls, "_cutlass_canary", lambda data, evidence, captured: {"status": "fail", "reason": "canary failed"})
    assert controls._cutlass({}, path)["reason"] == "canary failed"
    monkeypatch.setattr(controls, "_cutlass_canary", lambda data, evidence, captured: None)
    monkeypatch.setattr(controls, "_cutlass_negative", lambda data, evidence: {"status": "unknown", "reason": "negative missing"})
    assert controls._cutlass({}, path)["reason"] == "negative missing"


def test_cutlass_orchestrator_passes_only_after_each_sequential_gate(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "commands.json"
    plan = {"cutlass_revision": "c1", "cute_revision": "t1", "backend": "cuda", "operation": "gemm",
            "model_sha256": "a" * 64, "input_sha256": "b" * 64, "batch_size": 1,
            "concurrency": 1, "soak_seconds": 1}
    monkeypatch.setattr(controls, "_capture_plan", lambda data, evidence: (None, {"status": "unknown", "reason": "no plan"}))
    assert controls._cutlass({}, path)["reason"] == "no plan"
    monkeypatch.setattr(controls, "_capture_plan", lambda data, evidence: (plan, None))
    monkeypatch.setattr(controls, "_cutlass_plan", lambda captured, evidence: {"status": "unknown", "reason": "bad plan"})
    assert controls._cutlass({}, path)["reason"] == "bad plan"
    monkeypatch.setattr(controls, "_cutlass_plan", lambda captured, evidence: None)
    monkeypatch.setattr(controls, "_cutlass_build", lambda data, evidence, captured: None)
    monkeypatch.setattr(controls, "_cutlass_canary", lambda data, evidence, captured: None)
    monkeypatch.setattr(controls, "_cutlass_negative", lambda data, evidence: None)
    assert controls._cutlass({}, path)["status"] == "pass"


def test_cutlass_build_rejects_architecture_mismatch_and_unbound_artifacts(tmp_path: Path) -> None:
    path = tmp_path / "commands.json"
    plan = {"cutlass_revision": "cutlass-r1", "cute_revision": "cute-r1", "backend": "cuda",
            "operation": "gemm", "model_sha256": "a" * 64, "input_sha256": "b" * 64,
            "batch_size": 1, "concurrency": 1, "soak_seconds": 1}
    commands = [
        {"argv": ["dmidecode", "-t", "system"], "exit": 0,
         "stdout": "Manufacturer: NVIDIA\nProduct Name: DGX Spark GB10\nBIOS Version: 1\n"},
        {"argv": ["uname", "-r"], "exit": 0, "stdout": "6.17.0\n"},
        {"argv": ["nvidia-smi", "--query-gpu=name,compute_cap,driver_version"], "exit": 0,
         "stdout": "GB10, 12.1, 580.178.04\n"},
        {"argv": ["cmake", "cutlass-r1", "cute-r1", "cuda", "gemm"], "exit": 0,
         "stdout": "build done", "stderr": "", "phase": "build"},
        {"argv": ["cuobjdump", "--list-elf", "kernel.so"], "exit": 0, "stdout": "sm_121\n"},
    ]
    assert controls._cutlass_build({"commands": commands}, path, plan) is None
    gpu = commands[2]
    gpu["stdout"] = "GB10, unknown, 580.178.04\n"
    assert _status(controls._cutlass_build({"commands": commands}, path, plan)) == "fail"
    gpu["stdout"] = "GB10, 12.1, 580.178.04\n"
    build = commands[3]
    build["argv"].append("CUTE_DSL_ARCH=sm_100a")
    assert _status(controls._cutlass_build({"commands": commands}, path, plan)) == "fail"
    build["argv"].pop()
    commands[-1]["stdout"] = "sm_100\n"
    assert _status(controls._cutlass_build({"commands": commands}, path, plan)) == "fail"
    commands[-1]["stdout"] = "sm_121\n"
    assert _status(controls._cutlass_build({"commands": commands[:2]}, path, plan)) == "unknown"
    assert _status(controls._cutlass_build({"commands": commands[:-3]}, path, plan)) == "unknown"
    original_build = dict(build)
    build["stdout"] = "build done without pinned revisions"
    build["argv"] = ["cmake"]
    assert _status(controls._cutlass_build({"commands": commands}, path, plan)) == "unknown"
    build.update(original_build)
    build["exit"] = 1
    assert _status(controls._cutlass_build({"commands": commands}, path, plan)) == "fail"
    build.update(original_build)
    assert _status(controls._cutlass_build({"commands": commands[:-1]}, path, plan)) == "unknown"


def _signed_release_artifacts(directory: Path) -> tuple[str, Path, Path, str]:
    fixture = Path(__file__).parent / "fixtures/firmware-signed-repository"
    refs = directory / "refs"
    refs.mkdir()
    manifest = refs / "InRelease"
    manifest.write_bytes((fixture / "InRelease").read_bytes())
    packages = (fixture / "Packages").read_text(encoding="utf-8")
    keyring = refs / "repository-keyring.gpg"
    keyring.write_bytes((fixture / "keyring.gpg").read_bytes())
    return "5E62373C3E8236A0D1123818208CE844D9F220AD", manifest, keyring, packages


def test_signed_release_inputs_are_bounded_and_bound_to_separate_digests(tmp_path: Path) -> None:
    fingerprint, manifest, keyring, _ = _signed_release_artifacts(tmp_path)
    evidence = tmp_path / "evidence"
    evidence.mkdir()
    release = evidence / "InRelease"
    keys = evidence / "keyring.gpg"
    release.write_bytes(manifest.read_bytes())
    keys.write_bytes(keyring.read_bytes())
    plan: dict[str, Any] = {
        "inrelease_artifact": "InRelease", "keyring_artifact": "keyring.gpg",
        "repository_fingerprint": fingerprint,
        "inrelease_sha256": hashlib.sha256(release.read_bytes()).hexdigest(),
        "keyring_sha256": hashlib.sha256(keys.read_bytes()).hexdigest(),
    }
    paths = controls._signature_inputs(evidence / "commands.json", plan)
    assert paths[0] == release and paths[1] == keys and paths[2] == release.read_bytes()
    assert paths[3] == fingerprint and paths[4] is None
    for altered, status in (
        ({**plan, "inrelease_artifact": "../outside"}, "unknown"),
        ({**plan, "repository_fingerprint": "bad"}, "unknown"),
        ({**plan, "inrelease_sha256": "f" * 64}, "fail"),
        ({**plan, "keyring_sha256": "f" * 64}, "fail"),
        ({**plan, "keyring_artifact": "missing.gpg"}, "unknown"),
    ):
        result = controls._signature_inputs(evidence / "commands.json", altered)
        error = result[4]
        assert error is not None and error["status"] == status


def test_signed_inrelease_replay_binds_manifest_and_keyring_bytes(tmp_path: Path) -> None:
    fingerprint, manifest, keyring, _ = _signed_release_artifacts(tmp_path)
    plan = {"inrelease_artifact": "refs/InRelease", "keyring_artifact": "refs/repository-keyring.gpg",
            "repository_fingerprint": fingerprint,
            "inrelease_sha256": hashlib.sha256(manifest.read_bytes()).hexdigest(),
            "keyring_sha256": hashlib.sha256(keyring.read_bytes()).hexdigest()}
    text, error = controls._verify_signed_release({}, tmp_path / "commands.json", plan)
    assert text and error is None
    manifest.write_bytes(manifest.read_bytes().replace(b"Origin: Base OS", b"Origin: Base OX"))
    plan["inrelease_sha256"] = hashlib.sha256(manifest.read_bytes()).hexdigest()
    text, error = controls._verify_signed_release({}, tmp_path / "commands.json", plan)
    assert text is None and error is not None and error["status"] == "fail"


def test_signed_inrelease_verdict_requires_native_full_validsig_and_exact_input_receipts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    evidence = tmp_path / "signed"
    evidence.mkdir()
    manifest = evidence / "InRelease"
    keyring = evidence / "keyring.gpg"
    manifest.write_text("Origin: NVIDIA\n", encoding="utf-8")
    keyring.write_bytes(b"explicit keyring")
    fingerprint = "A" * 40
    plan = {"inrelease_artifact": "InRelease", "keyring_artifact": "keyring.gpg",
            "repository_fingerprint": fingerprint,
            "inrelease_sha256": hashlib.sha256(manifest.read_bytes()).hexdigest(),
            "keyring_sha256": hashlib.sha256(keyring.read_bytes()).hexdigest()}
    valid = {"status": "pass", "manifest_sha256": plan["inrelease_sha256"],
             "keyring_sha256": [plan["keyring_sha256"]],
             "validsig_records": [f"[GNUPG:] VALIDSIG {fingerprint} 20261003 1234 0 4 0 1 8 00"]}
    monkeypatch.setattr(controls, "verify_release_signature", lambda manifest_path, keyrings: valid)
    text, error = controls._verify_signed_release({}, evidence / "commands.json", plan)
    assert text == "Origin: NVIDIA\n" and error is None
    for response, status in (
        ({**valid, "status": "could_not_run"}, "unknown"),
        ({**valid, "status": "fail"}, "fail"),
        ({**valid, "manifest_sha256": "0" * 64}, "fail"),
        ({**valid, "keyring_sha256": ["wrong"]}, "fail"),
        ({**valid, "validsig_records": [f"[GNUPG:] VALIDSIG {fingerprint} incomplete"]}, "fail"),
    ):
        monkeypatch.setattr(controls, "verify_release_signature", lambda manifest_path, keyrings, value=response: value)
        text, error = controls._verify_signed_release({}, evidence / "commands.json", plan)
        assert text is None and error is not None and error["status"] == status
    manifest.write_bytes(b"\xff\xfe")
    plan["inrelease_sha256"] = hashlib.sha256(manifest.read_bytes()).hexdigest()
    monkeypatch.setattr(controls, "verify_release_signature", lambda manifest_path, keyrings: {
        **valid, "manifest_sha256": plan["inrelease_sha256"]})
    text, error = controls._verify_signed_release({}, evidence / "commands.json", plan)
    assert text is None and error is not None and error["status"] == "unknown"


def _cx7_firmware_bundle(evidence: Path) -> tuple[str, dict[str, Any], list[dict[str, Any]]]:
    finding_id = "DELTA-FORUM-CX7-FW-UPDATE-GUARD-01"
    package_path = "/tmp/nvidia-spark-mlnx-firmware-manager_5.0.8-1_arm64.deb"
    package_name = "nvidia-spark-mlnx-firmware-manager"
    package_hash = "8d18daf0b40b5209aede72e4c57c16f7f45479fc2daa98efb876791b989df1fa"
    package_version, package_size = "5.0.8-1", 8993136
    package_filename = "pool/dgx/n/nvidia-spark-mlnx-firmware-manager/nvidia-spark-mlnx-firmware-manager_5.0.8-1_arm64.deb"
    index_path = "/var/lib/apt/lists/repo.download.nvidia.com_baseos_ubuntu_noble_arm64_dists_noble-updates_dgx_binary-arm64_Packages"
    fingerprint, inrelease_artifact, keyring_artifact, packages_text = _signed_release_artifacts(evidence)
    inrelease_bytes = inrelease_artifact.read_bytes()
    keyring_bytes = keyring_artifact.read_bytes()
    plan = {"package_path": package_path, "package_sha256": package_hash, "package_name": package_name,
            "package_origin": "repo.download.nvidia.com", "script_extract_dir": "/tmp/cx7-controls",
            "package_source_uri": "https://repo.download.nvidia.com/baseos/ubuntu/noble/arm64",
            "bdf": "0000:03:00.0", "rdma_hca": "mlx5_0", "package_version": package_version,
            "package_size": package_size, "inrelease_path": "/var/lib/apt/lists/repo_nvidia_com_dists_noble_InRelease",
            "keyring_path": "/usr/share/keyrings/nvidia-archive-keyring.gpg",
            "repository_fingerprint": fingerprint, "inrelease_artifact": "refs/InRelease",
            "keyring_artifact": "refs/repository-keyring.gpg",
            "inrelease_sha256": hashlib.sha256(inrelease_bytes).hexdigest(),
            "keyring_sha256": hashlib.sha256(keyring_bytes).hexdigest(), "packages_index_path": index_path,
            "package_index_relative": "dgx/binary-arm64/Packages", "package_component": "dgx",
            "package_architecture": "arm64", "package_suite": "noble-updates",
            "package_filename": package_filename}
    rows: list[dict[str, Any]] = []

    def add(argv: list[str], stdout: str, phase: str | None = None) -> None:
        row: dict[str, Any] = {"argv": argv, "exit": 0, "stdout": stdout, "stderr": "",
                                  "captured_at": f"2026-10-03T12:{len(rows):02d}:00Z"}
        if phase is not None:
            row["phase"] = phase
        rows.append(row)

    add(["cat", "experiment-plan.json"], json.dumps(plan))
    add(["dmidecode", "-t", "system"], "Manufacturer: ASUSTeK COMPUTER INC.\nProduct Name: GX10\nBIOS Version: 1.0\n")
    add(["uname", "-r"], "6.17.0-1029\n")
    add(["mstflint", "-d", "03:00.0", "q"], "PSID: NVD0000000087\nFW Version: 28.45.1\n")
    add(["lspci", "-vv", "-s", "0000:03:00.0"], "0000:03:00.0 Ethernet controller: Mellanox 15b3:101d\nBusMaster+\nKernel driver in use: mlx5_core\n")
    add(["lspci", "-D", "-nn"], "0000:03:00.0 Ethernet controller: Mellanox 15b3:101d\n")
    add(["readlink", "-f", "/sys/class/infiniband/mlx5_0/device"], "/sys/devices/pci0000:00/0000:00:01.0/0000:03:00.0\n")
    add(["ibv_devinfo", "-d", "mlx5_0", "-v"], "hca_id: mlx5_0\nfw_ver: 28.45.1\nstate: PORT_ACTIVE\n")
    add(["sha256sum", package_path], f"{package_hash}  {package_path}\n")
    add(["dpkg-deb", "--control", package_path, "/tmp/cx7-controls"], "")
    for script in ("preinst", "postinst", "prerm", "postrm"):
        contents = "#!/bin/sh\nsh /usr/lib/vendor/fw-helper.sh\n" if script == "postinst" else "#!/bin/sh\nexit 0\n"
        add(["cat", f"/tmp/cx7-controls/{script}"], contents, "maintainer-script")
    add(["cat", "/usr/lib/vendor/fw-helper.sh"], "#!/bin/sh\nexit 0\n", "helper-source")
    add(["apt-cache", "policy", package_name], "500 https://repo.download.nvidia.com/baseos/ubuntu/noble/arm64 noble-updates/dgx arm64 Packages\n")
    add(["cat", index_path], packages_text)
    add(["stat", "-c", "%s", index_path], f"{len(packages_text.encode())}\n")
    add(["stat", "-c", "%s", package_path], f"{package_size}\n")
    add(["cat", "recovery-runbook.md"], "NVIDIA CX7 recovery instructions\n", "recovery-procedure")
    text = f"NVIDIA CX7 package compatibility PSID NVD0000000087 firmware 28.45.1 {package_name} {package_version} {fingerprint}. Verify recovery channel."
    bundle = {"schema": 1, "id": finding_id, "experiment_plan": plan,
              "vendor_sources": [{"url": "https://nvidia.com/cx7/firmware", "text": text,
                                  "sha256": __import__("hashlib").sha256(text.encode()).hexdigest()}],
              "commands": rows}
    return finding_id, bundle, rows


def _fw_result(capture: Path, finding_id: str, evidence: Path,
               bundle: dict[str, Any], anchor: str) -> dict[str, Any]:
    capture.write_text(json.dumps(bundle), encoding="utf-8")
    return controls.verify(finding_id, evidence, trusted_plan_sha256=anchor)


def _assert_wrong_apt_origin(capture: Path, finding_id: str, evidence: Path,
                             bundle: dict[str, Any], anchor: str) -> None:
    commands = bundle["commands"]
    assert isinstance(commands, list)
    policy = next(row for row in commands if isinstance(row, dict) and row["argv"][0] == "apt-cache")
    policy["stdout"] = policy["stdout"].replace("baseos", "spark")
    assert _fw_result(capture, finding_id, evidence, bundle, anchor)["status"] == "fail"
    policy["stdout"] = policy["stdout"].replace("spark", "baseos")


def test_cx7_firmware_guard_scans_exact_signed_package_scripts(tmp_path: Path) -> None:
    evidence = tmp_path / "DELTA-FORUM-CX7-FW-UPDATE-GUARD-01"
    evidence.mkdir()
    finding_id, bundle, rows = _cx7_firmware_bundle(evidence)
    capture = evidence / "commands.json"
    plan = bundle["experiment_plan"]
    anchor = hashlib.sha256(json.dumps(plan, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    result = _fw_result(capture, finding_id, evidence, bundle, anchor)
    assert result["status"] == "pass", result

    _assert_wrong_apt_origin(capture, finding_id, evidence, bundle, anchor)

    release_path = evidence / str(bundle["experiment_plan"]["inrelease_artifact"])
    original_release = release_path.read_bytes()
    release_path.write_bytes(original_release.replace(b"Origin: Base OS", b"Origin: Base OX"))
    plan["inrelease_sha256"] = hashlib.sha256(release_path.read_bytes()).hexdigest()
    rows[0]["stdout"] = json.dumps(plan)
    anchor = hashlib.sha256(json.dumps(plan, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    assert _fw_result(capture, finding_id, evidence, bundle, anchor)["status"] == "fail"
    release_path.write_bytes(original_release)
    plan["inrelease_sha256"] = hashlib.sha256(original_release).hexdigest()
    rows[0]["stdout"] = json.dumps(plan)
    anchor = hashlib.sha256(json.dumps(plan, sort_keys=True, separators=(",", ":")).encode()).hexdigest()

    index_row = next(row for row in rows if row["argv"] == ["cat", "/var/lib/apt/lists/repo.download.nvidia.com_baseos_ubuntu_noble_arm64_dists_noble-updates_dgx_binary-arm64_Packages"])
    index_row["stdout"] += "# altered index\n"
    assert _fw_result(capture, finding_id, evidence, bundle, anchor)["status"] == "fail"
    index_row["stdout"] = index_row["stdout"].replace("# altered index\n", "")

    pci_row = next(row for row in rows if row["argv"][:2] == ["lspci", "-vv"])
    pci_row["stdout"] = pci_row["stdout"].replace("0000:03:00.0", "0000:04:00.0")
    result = _fw_result(capture, finding_id, evidence, bundle, anchor)
    assert result["status"] == "fail", result
    pci_row["stdout"] = pci_row["stdout"].replace("0000:04:00.0", "0000:03:00.0")

    helper_row = next(row for row in rows if row.get("phase") == "helper-source")
    helper_row["stdout"] = "#!/bin/sh\nexec /usr/sbin/mlxfwupdater --force\n"
    result = _fw_result(capture, finding_id, evidence, bundle, anchor)
    assert result["status"] == "fail", result
    helper_row["stdout"] = "#!/bin/sh\nexit 0\n"
    helper_index = rows.index(helper_row)
    rows.remove(helper_row)
    result = _fw_result(capture, finding_id, evidence, bundle, anchor)
    assert result["status"] == "unknown", result
    rows.insert(helper_index, helper_row)

    postinst = next(row for row in rows if row.get("phase") == "maintainer-script" and row["argv"][-1].endswith("postinst"))
    postinst["stdout"] = "#!/bin/sh\nif [ -x /usr/lib/vendor/hidden-helper ]; then /usr/lib/vendor/hidden-helper; fi\n"
    assert _fw_result(capture, finding_id, evidence, bundle, anchor)["status"] == "unknown"
    postinst["stdout"] = "#!/bin/sh\nsh /usr/lib/vendor/fw-helper.sh\n"

    for row in rows:
        if row.get("phase") == "maintainer-script" and row["argv"][-1].endswith("postinst"):
            row["stdout"] = "#!/bin/sh\nexec /usr/sbin/mlxfwupdater --force\n"
            break
    assert _fw_result(capture, finding_id, evidence, bundle, anchor)["status"] == "fail"


def test_cx7_signed_release_rejects_mutated_repository_keyring(tmp_path: Path) -> None:
    evidence = tmp_path / "fw-evidence"
    evidence.mkdir()
    finding_id, bundle, _rows = _cx7_firmware_bundle(evidence)
    capture = evidence / "commands.json"
    plan = bundle["experiment_plan"]
    assert isinstance(plan, dict)
    keyring_path = evidence / str(plan["keyring_artifact"])
    original = keyring_path.read_bytes()
    corrupted = bytearray(original)
    corrupted[len(corrupted) // 2] ^= 1
    keyring_path.write_bytes(corrupted)
    plan["keyring_sha256"] = hashlib.sha256(corrupted).hexdigest()
    rows = bundle["commands"]
    assert isinstance(rows, list)
    rows[0]["stdout"] = json.dumps(plan)
    anchor = hashlib.sha256(json.dumps(plan, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    result = _fw_result(capture, finding_id, evidence, bundle, anchor)
    assert result["status"] in {"fail", "unknown"} and result["status"] != "pass", result


def test_cx7_guard_requires_separate_plan_approval_and_exact_device_identity(tmp_path: Path) -> None:
    evidence = tmp_path / "fw-guard"
    evidence.mkdir()
    finding_id, bundle, rows = _cx7_firmware_bundle(evidence)
    capture = evidence / "commands.json"
    plan = bundle["experiment_plan"]
    assert isinstance(plan, dict)
    anchor = hashlib.sha256(json.dumps(plan, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    assert _fw_result(capture, finding_id, evidence, bundle, "")["status"] == "unknown"
    dmi = next(row for row in rows if row["argv"][:2] == ["dmidecode", "-t"])
    original_dmi = dmi["stdout"]
    dmi["stdout"] = original_dmi.replace("ASUSTeK", "Lenovo")
    assert _fw_result(capture, finding_id, evidence, bundle, anchor)["status"] == "fail"
    dmi["stdout"] = original_dmi
    device = next(row for row in rows if row["argv"][0] == "mstflint")
    device["stdout"] = "PSID: NVD0000000087\n"
    result = _fw_result(capture, finding_id, evidence, bundle, anchor)
    assert result["status"] == "unknown" and "firmware version" in result["reason"]


def test_memory_recovery_soak_native_series_and_ordered_termination(tmp_path: Path) -> None:
    from datetime import datetime, timedelta, timezone

    finding_id = "DELTA-FORUM-MEMORY-RECOVERY-SOAK-01"
    plan = {"soak_seconds": 7200, "max_sample_gap_seconds": 3600,
            "rpc_server_pid": 101, "client_pid": 202}
    rows: list[dict[str, Any]] = []

    def add(capture: tuple[list[str], str, str | None, str | None, datetime | None, int]) -> None:
        argv, stdout, phase, sample, stamp, exit_code = capture
        row: dict[str, Any] = {"argv": argv, "exit": exit_code, "stdout": stdout, "stderr": "",
                                  "captured_at": (stamp or datetime(2026, 10, 3, 11, 59, tzinfo=timezone.utc)
                                                  + timedelta(seconds=len(rows))).isoformat()}
        if phase is not None:
            row["phase"] = phase
        if sample is not None:
            row["sample"] = sample
        rows.append(row)

    add((["cat", "experiment-plan.json"], json.dumps(plan), None, None, None, 0))
    digest = __import__("hashlib").sha256(json.dumps(plan, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    base = datetime(2026, 10, 3, 12, 0, tzinfo=timezone.utc)
    samples = [("soak", f"s{i}", base + timedelta(hours=i), "running", "running", 50000) for i in range(3)]
    samples += [("control", f"c{i}", base + timedelta(hours=i, minutes=5), "running", "running", 50000) for i in range(3)]
    samples += [("client-terminated", "client-exit", base + timedelta(hours=2, minutes=10), "running", "stopped", 60000),
                ("server-terminated", "server-exit", base + timedelta(hours=2, minutes=15), "stopped", "stopped", 80000)]
    for phase, sample, anchor, server_state, client_state, available in sorted(samples, key=lambda item: item[2]):
        lines = f"Mem: 100000 30000 20000 5000 5000 {available}\nSwap: 12000 2000 10000\n"
        for offset, (argv, output) in enumerate([
            (["free", "-b"], lines),
            (["cat", "/proc/pressure/memory"], "some avg10=0.10 avg60=0.05 avg300=0.01 total=1\n"),
            (["ps", "-p", "101", "-o", "pid=,stat=,rss=,lstart="], "" if server_state == "stopped" else "101 S 4096 Sat Oct  3 11:00:00 2026\n"),
            (["ps", "-p", "202", "-o", "pid=,stat=,rss=,lstart="], "" if client_state == "stopped" else "202 R 2048 Sat Oct  3 11:01:00 2026\n"),
        ]):
            pid_is_gone = phase == "client-terminated" and argv[0] == "ps" and argv[2] == "202" or phase == "server-terminated" and argv[0] == "ps"
            add((argv, output, phase, sample, anchor + timedelta(seconds=offset), 1 if pid_is_gone else 0))
    bundle = {"schema": 1, "id": finding_id, "experiment_plan": plan, "commands": rows}
    evidence = tmp_path / finding_id
    evidence.mkdir()
    capture = evidence / "commands.json"
    capture.write_text(json.dumps(bundle), encoding="utf-8")
    result = controls.verify(finding_id, evidence, trusted_plan_sha256=digest)
    assert result["status"] == "pass", result

    server_sample = next(row for row in rows if row.get("phase") == "soak" and row["argv"][0] == "ps" and row["argv"][2] == "101")
    server_sample["stdout"] = "101 S 4096 Sun Oct  4 12:00:00 2026\n"
    capture.write_text(json.dumps(bundle), encoding="utf-8")
    result = controls.verify(finding_id, evidence, trusted_plan_sha256=digest)
    assert result["status"] == "fail", result
    server_sample["stdout"] = "101 S 4096 Sat Oct  3 11:00:00 2026\n"

    next(row for row in rows if row.get("sample") == "client-exit" and row["argv"][0] == "ps" and row["argv"][2] == "202")["stdout"] = "202 S 2048 Sat Oct  3 11:01:00 2026\n"
    capture.write_text(json.dumps(bundle), encoding="utf-8")
    result = controls.verify(finding_id, evidence, trusted_plan_sha256=digest)
    assert result["status"] == "fail", result

    invalid_pid = next(row for row in rows if row.get("phase") == "soak" and row["argv"][0] == "ps" and row["argv"][2] == "202")
    invalid_pid["argv"][2] = "4194305"
    invalid_pid["stdout"] = ""
    invalid_pid["exit"] = 1
    capture.write_text(json.dumps(bundle), encoding="utf-8")
    result = controls.verify(finding_id, evidence, trusted_plan_sha256=digest)
    assert result["status"] == "fail", result
    assert controls.verify(finding_id, evidence)["status"] == "unknown"


def _ota_bundle() -> tuple[str, dict[str, Any], dict[str, Any]]:
    finding_id = "DELTA-FORUM-OTA-DRIVER-KERNEL-EFFECTIVE-TUPLE-01"
    values = {
        "before-update": ("7.5", "7.5.0", "6.17.0-1029", "580.178.04", "580.178.04", "13.0.96", "EC-1.2", 4_294_967_296),
        "after-update": ("7.6", "7.6.0", "6.17.0-1032", "580.178.04", "580.178.04", "13.0.96", "EC-1.3", 2_147_483_648),
        "rollback": ("7.5", "7.5.0", "6.17.0-1029", "580.178.04", "580.178.04", "13.0.96", "EC-1.2", 4_294_967_296),
    }
    keys = ("ota_release", "dgx_os_build", "kernel_release", "loaded_driver", "disk_driver",
            "cuda_runtime", "ec_version", "carveout_bytes")
    supported = dict(zip(keys, values["after-update"], strict=True))
    plan: dict[str, Any] = {"supported_tuple": supported, "update_channel": "OEM OTA stable",
                              "workload_soak": {"argv": ["vllm", "bench", "serve"],
                                                "model_sha256": "c" * 64, "input_sha256": "d" * 64,
                                                "pid": 4242, "duration_seconds": 3600,
                                                "max_sample_gap_seconds": 3600}}
    rows: list[dict[str, Any]] = [{"argv": ["cat", "experiment-plan.json"], "exit": 0,
                                     "stdout": json.dumps(plan), "stderr": "", "captured_at": "2026-10-03T12:00:00Z"}]
    rows.extend([
        {"argv": ["dmidecode", "-t", "system"], "exit": 0,
         "stdout": "Manufacturer: ASUSTeK COMPUTER INC.\nProduct Name: GX10\nBIOS Version: 1.0\n", "stderr": ""},
        {"argv": ["uname", "-r"], "exit": 0, "stdout": "6.17.0-1032\n", "stderr": ""},
    ])
    for phase, record in values.items():
        ota, build, kernel, loaded, disk, cuda, ec, carveout = record
        rows.extend([
            {"argv": ["nvsm", "show", "system"], "exit": 0,
             "stdout": f"OTA Release: {ota}\nDGX OS Build: {build}\nEC Version: {ec}\nCarveout Bytes: {carveout}\n", "stderr": "", "phase": phase},
            {"argv": ["uname", "-r"], "exit": 0, "stdout": f"{kernel}\n", "stderr": "", "phase": phase},
            {"argv": ["cat", "/proc/driver/nvidia/version"], "exit": 0,
             "stdout": f"NVRM version: NVIDIA UNIX Kernel Module {loaded}\n", "stderr": "", "phase": phase},
            {"argv": ["modinfo", "-F", "version", "nvidia"], "exit": 0, "stdout": f"{disk}\n", "stderr": "", "phase": phase},
            {"argv": ["dpkg-query", "-W", "cuda-cudart-13-0"], "exit": 0,
             "stdout": f"cuda-cudart-13-0 {cuda}\n", "stderr": "", "phase": phase},
        ])
    for sample, timestamp in (("ota-a", "2026-10-03T13:00:00Z"), ("ota-b", "2026-10-03T14:00:00Z")):
        samples = [
            (["free", "-b"], "Mem: 100000 20000 30000 4000 5000 60000\nSwap: 8000 2000 6000\n"),
            (["cat", "/proc/pressure/memory"], "some avg10=0.10 avg60=0.05 avg300=0.01 total=123\n"),
            (["vllm", "bench", "serve"], json.dumps({"pid": 4242, "model_sha256": "c" * 64,
                "input_sha256": "d" * 64, "requests": 100, "completed": 100})),
            (["ps", "-p", "4242", "-o", "pid=,stat=,rss=,lstart="],
             "4242 S 4096 Sat Oct  3 11:00:00 2026\n"),
        ]
        for offset, (argv, stdout) in enumerate(samples):
            rows.append({"argv": argv, "exit": 0, "stdout": stdout, "stderr": "",
                         "phase": "workload-soak", "sample": sample,
                         "captured_at": f"{timestamp[:-1]}.{offset:06d}Z"})
    for index, row in enumerate(rows):
        row.setdefault("captured_at", f"2026-10-03T12:{index:02d}:00Z")
    reference = ("ASUSTeK COMPUTER INC. GX10 BIOS 1.0 DGX OS build 7.6.0 OTA 7.6 kernel 6.17.0-1032 "
                 "NVIDIA loaded and disk driver 580.178.04 CUDA 13.0.96 EC-1.3 carveout 2147483648 bytes; "
                 "OEM-supported tuple and recovery channel metadata.")
    bundle: dict[str, Any] = {"schema": 1, "id": finding_id, "experiment_plan": plan,
                                 "vendor_sources": [{"url": "https://docs.nvidia.com/dgx/dgx-os/", "text": reference,
                                                     "sha256": __import__("hashlib").sha256(reference.encode()).hexdigest()}],
                                 "commands": rows}
    return finding_id, bundle, plan


def test_ota_tuple_requires_supported_readback_and_verified_rollback(tmp_path: Path) -> None:
    finding_id, bundle, plan = _ota_bundle()
    evidence = tmp_path / finding_id
    evidence.mkdir()
    capture = evidence / "commands.json"
    capture.write_text(json.dumps(bundle), encoding="utf-8")
    digest = __import__("hashlib").sha256(json.dumps(plan, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    assert controls.verify(finding_id, evidence, trusted_plan_sha256=digest)["status"] == "pass"
    rollback = next(row for row in bundle["commands"] if isinstance(row, dict) and row.get("phase") == "rollback" and row["argv"][0] == "uname")
    rollback["stdout"] = "6.17.0-1032\n"
    capture.write_text(json.dumps(bundle), encoding="utf-8")
    assert controls.verify(finding_id, evidence, trusted_plan_sha256=digest)["status"] == "fail"


def test_ota_tuple_comparison_rejects_absent_source_and_tuple_mismatch(tmp_path: Path) -> None:
    finding_id, bundle, plan = _ota_bundle()
    path = tmp_path / "commands.json"
    phases, error = controls._ota_observations(bundle, path)
    assert phases is not None and error is None
    identity, error = controls._identity(bundle, path)
    assert identity is not None and error is None
    source = bundle["vendor_sources"][0]
    assert isinstance(source, dict)
    source["text"] += " Captured previous tuple " + " ".join(str(value) for value in phases["before-update"].values())
    source["sha256"] = hashlib.sha256(source["text"].encode()).hexdigest()
    assert controls._ota_compare(bundle, path, plan, phases, identity)["status"] == "pass"
    absent = controls._ota_compare({"commands": bundle["commands"]}, path, plan, phases, identity)
    assert absent["status"] == "unknown"
    unchanged = {**phases, "after-update": dict(phases["before-update"])}
    assert controls._ota_compare(bundle, path, plan, unchanged, identity)["status"] == "fail"
    unapproved = {key: value for key, value in plan.items() if key != "supported_tuple"}
    assert controls._ota_compare(bundle, path, unapproved, phases, identity)["status"] == "unknown"
    wrong_supported = {**plan, "supported_tuple": {**plan["supported_tuple"], "kernel_release": "unsupported"}}
    assert controls._ota_compare(bundle, path, wrong_supported, phases, identity)["status"] == "fail"


def _memory_gate_samples() -> list[tuple[dict[str, Any], datetime, dict[str, Any]]]:
    base = datetime(2026, 10, 3, 12, 0, tzinfo=timezone.utc)
    values = {"rpc_server_pid": 101, "rpc_server_state": "running", "rpc_server_start": "server-start",
              "client_pid": 202, "client_state": "running", "client_start": "client-start",
              "mem_available_bytes": 50000, "swap_free_bytes": 10000, "rss_bytes": 6000000,
              "psi_memory_some_avg10": 0.1}
    samples = [("soak", base + timedelta(hours=hour + 0.01), values) for hour in range(3)]
    samples += [("control", base + timedelta(hours=hour, minutes=5), values) for hour in range(3)]
    samples += [("client-terminated", base + timedelta(hours=2, minutes=10),
                 {**values, "client_state": "stopped", "mem_available_bytes": 60000}),
                ("server-terminated", base + timedelta(hours=2, minutes=15),
                 {**values, "client_state": "stopped", "rpc_server_state": "stopped",
                  "mem_available_bytes": 80000})]
    return [({"phase": phase}, stamp, dict(measurement)) for phase, stamp, measurement in samples]


def test_memory_recovery_gate_rejects_identity_order_and_recovery_contradictions(tmp_path: Path) -> None:
    path = tmp_path / "commands.json"
    baseline = _memory_gate_samples()
    assert controls._memory_recovery_gate(baseline, path, 7200, 3600)["status"] == "pass"
    variants: list[tuple[list[tuple[dict[str, Any], datetime, dict[str, Any]]], str, str]] = []

    too_few = [sample for sample in baseline if sample[0]["phase"] != "soak"]
    variants.append((too_few, "multihour", "unknown"))
    changed_pid = _memory_gate_samples()
    changed_pid[-1][2]["rpc_server_pid"] = 303
    variants.append((changed_pid, "identity changed", "fail"))
    reused = _memory_gate_samples()
    reused[1][2]["rpc_server_start"] = "new-server-start"
    variants.append((reused, "start times changed", "fail"))
    missing_close = [sample for sample in _memory_gate_samples() if sample[0]["phase"] != "server-terminated"]
    variants.append((missing_close, "termination observations missing", "unknown"))
    out_of_order = _memory_gate_samples()
    client = next(sample for sample in out_of_order if sample[0]["phase"] == "client-terminated")
    client_row = out_of_order[-1]
    out_of_order[out_of_order.index(client)] = (client[0], client_row[1] + timedelta(minutes=1), client[2])
    variants.append((out_of_order, "terminated before the client", "fail"))
    wrong_client = _memory_gate_samples()
    next(sample for sample in wrong_client if sample[0]["phase"] == "client-terminated")[2]["rpc_server_state"] = "stopped"
    variants.append((wrong_client, "while the identified RPC server remained alive", "fail"))
    wrong_server = _memory_gate_samples()
    wrong_server[-1][2]["rpc_server_state"] = "running"
    variants.append((wrong_server, "termination was not observed", "fail"))
    no_recovery = _memory_gate_samples()
    no_recovery[-1][2]["mem_available_bytes"] = 60000
    variants.append((no_recovery, "did not increase", "fail"))
    short_control = _memory_gate_samples()
    one_control = [sample for sample in short_control if sample[0]["phase"] == "control"][:1]
    short_control = [sample for sample in short_control if sample[0]["phase"] != "control"] + one_control
    variants.append((short_control, "healthy RPC-server control series missing", "unknown"))

    for samples, reason, status in variants:
        result = controls._memory_recovery_gate(samples, path, 7200, 3600)
        assert result["status"] == status and reason in result["reason"], result


def test_memory_soak_orchestrator_rejects_untrusted_or_short_contracts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "commands.json"
    plan: dict[str, Any] = {"soak_seconds": 7200, "max_sample_gap_seconds": 3600}
    samples = _memory_gate_samples()
    monkeypatch.setattr(controls, "_capture_plan", lambda data, evidence: (plan, None))
    monkeypatch.setattr(controls, "_plan_approval", lambda data, evidence, captured: None)
    monkeypatch.setattr(controls, "_memory_samples", lambda data, evidence: (samples, None))
    monkeypatch.setattr(controls, "_memory_recovery_gate", lambda observations, evidence, duration, gap: {
        "status": "pass", "reason": "gated"})
    assert controls._memory_soak({}, path)["status"] == "pass"
    monkeypatch.setattr(controls, "_capture_plan", lambda data, evidence: (None, {"status": "unknown", "reason": "plan missing"}))
    assert controls._memory_soak({}, path)["reason"] == "plan missing"
    monkeypatch.setattr(controls, "_capture_plan", lambda data, evidence: (plan, None))
    monkeypatch.setattr(controls, "_plan_approval", lambda data, evidence, captured: {"status": "unknown", "reason": "approval missing"})
    assert controls._memory_soak({}, path)["reason"] == "approval missing"
    monkeypatch.setattr(controls, "_plan_approval", lambda data, evidence, captured: None)
    for key, value in (("soak_seconds", 7199), ("max_sample_gap_seconds", True)):
        old = plan[key]
        plan[key] = value
        assert controls._memory_soak({}, path)["status"] == "unknown"
        plan[key] = old
    monkeypatch.setattr(controls, "_memory_samples", lambda data, evidence: (None, {"status": "unknown", "reason": "raw samples missing"}))
    assert controls._memory_soak({}, path)["reason"] == "raw samples missing"


def test_ota_source_digest_or_tuple_mismatch_remains_could_not_run(tmp_path: Path) -> None:
    finding_id, bundle, plan = _ota_bundle()
    digest = hashlib.sha256(json.dumps(plan, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    evidence = tmp_path / finding_id
    evidence.mkdir()
    capture = evidence / "commands.json"
    source = bundle["vendor_sources"][0]
    source["text"] = source["text"].replace("6.17.0-1032", "6.17.0-9999")
    source["sha256"] = hashlib.sha256(source["text"].encode()).hexdigest()
    capture.write_text(json.dumps(bundle), encoding="utf-8")
    result = controls.verify(finding_id, evidence, trusted_plan_sha256=digest)
    assert result["status"] == "unknown" and result["could_not_run"] == 1, result


def test_ota_soak_requires_pid_bound_native_memory_pressure_and_workload(tmp_path: Path) -> None:
    finding_id, bundle, plan = _ota_bundle()
    digest = hashlib.sha256(json.dumps(plan, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    evidence = tmp_path / finding_id
    evidence.mkdir()
    capture = evidence / "commands.json"
    capture.write_text(json.dumps(bundle), encoding="utf-8")
    result = controls.verify(finding_id, evidence, trusted_plan_sha256=digest)
    assert result["status"] == "pass", result
    workload = next(row for row in bundle["commands"] if isinstance(row, dict)
                    and row.get("phase") == "workload-soak" and row["argv"][0] == "vllm")
    payload = json.loads(workload["stdout"])
    payload["pid"] = 9
    workload["stdout"] = json.dumps(payload)
    capture.write_text(json.dumps(bundle), encoding="utf-8")
    result = controls.verify(finding_id, evidence, trusted_plan_sha256=digest)
    assert result["status"] == "fail", result


def test_ota_soak_rejects_missing_contract_and_unbounded_sample_window(tmp_path: Path) -> None:
    path = tmp_path / "commands.json"
    missing = controls._ota_soak({"commands": []}, path, {})
    assert missing["status"] == "unknown" and "contract missing" in missing["reason"]

    finding_id, bundle, plan = _ota_bundle()
    rows = bundle["commands"]
    assert isinstance(rows, list)
    first = next(row for row in rows if isinstance(row, dict) and row.get("phase") == "workload-soak"
                 and row["argv"][0] == "vllm")
    first["captured_at"] = "2026-10-03T15:00:00Z"
    result = controls._ota_soak(bundle, path, plan)
    assert result["status"] == "unknown" and "capture interval" in result["reason"]


def test_ota_soak_rejects_pid_reuse_and_incomplete_request_completion(tmp_path: Path) -> None:
    path = tmp_path / "commands.json"
    _, bundle, plan = _ota_bundle()
    rows = bundle["commands"]
    assert isinstance(rows, list)
    ps_rows = [row for row in rows if isinstance(row, dict) and row.get("phase") == "workload-soak"
               and row["argv"][0] == "ps"]
    ps_rows[1]["stdout"] = "4242 S 4096 Sun Oct  4 11:00:00 2026\n"
    result = controls._ota_soak(bundle, path, plan)
    assert result["status"] == "fail" and "start identity changed" in result["reason"]

    _, bundle, plan = _ota_bundle()
    rows = bundle["commands"]
    assert isinstance(rows, list)
    sample_rows = [row for row in rows if isinstance(row, dict) and row.get("phase") == "workload-soak"
                   and row["argv"][0] == "vllm"]
    payload = json.loads(sample_rows[0]["stdout"])
    payload["completed"] = 99
    sample_rows[0]["stdout"] = json.dumps(payload)
    result = controls._ota_soak(bundle, path, plan)
    assert result["status"] == "fail" and "requests did not complete" in result["reason"]


def _kv_bundle() -> tuple[str, dict[str, Any]]:
    finding_id = "DELTA-FORUM-KV-QUANT-METRIC-PROVENANCE-GATE-01"
    plan = {"model_sha256": "a" * 64, "backend": "llama.cpp", "baseline_kv_mode": "f16",
            "quantized_kv_mode": "q4_0", "input_sha256": "b" * 64, "context_tokens": 110000,
            "concurrency": 1, "reference_max_abs_error": 0.01}
    commands: list[dict[str, Any]] = [{"argv": ["cat", "experiment-plan.json"], "exit": 0,
                                         "stdout": json.dumps(plan), "stderr": "",
                                         "captured_at": "2026-10-03T12:00:00Z"},
        {"argv": ["dmidecode", "-t", "system"], "exit": 0,
         "stdout": "Manufacturer: NVIDIA Corporation\nProduct Name: DGX Spark GB10\nBIOS Version: 1.0\n",
         "stderr": "", "captured_at": "2026-10-03T12:00:01Z"},
        {"argv": ["uname", "-r"], "exit": 0, "stdout": "6.17.0\n", "stderr": "",
         "captured_at": "2026-10-03T12:00:02Z"}]
    for phase, mode, kv_bytes, error in (("baseline", "f16", 805306368, 0.0),
                                          ("quantized", "q4_0", 226492416, 0.001)):
        metrics = ("process_resident_memory_bytes 900000000\ncontainer_memory_working_set_bytes 1000000000\n"
                   "node_memory_MemAvailable_bytes 80000000000\nnode_memory_SwapFree_bytes 16000000000\n"
                   f"llamacpp_kv_cache_bytes {kv_bytes}\n")
        commands.append({"argv": ["curl", "-fsS", "http://127.0.0.1:8080/metrics"], "exit": 0,
                         "stdout": metrics, "stderr": "", "phase": phase,
                         "captured_at": f"2026-10-03T12:0{'1' if phase == 'baseline' else '2'}:00Z"})
        run = {"model_sha256": plan["model_sha256"], "backend": plan["backend"], "kv_mode": mode,
               "context_tokens": plan["context_tokens"], "concurrency": plan["concurrency"],
               "input_sha256": plan["input_sha256"], "prefill_tokens_s": 500.0,
               "decode_tokens_s": 25.0, "correct_tokens": 1000, "total_tokens": 1000,
               "max_abs_error": error}
        commands.append({"argv": ["cat", f"{phase}-result.json"], "exit": 0,
                         "stdout": json.dumps(run), "stderr": "", "phase": phase,
                         "captured_at": f"2026-10-03T12:0{'1' if phase == 'baseline' else '2'}:01Z"})
    reference = ("NVIDIA Corporation DGX Spark GB10 kernel 6.17.0 backend llama.cpp is validated and supported for the "
                 "captured product tuple and documented baseline and quantized KV modes.")
    source = {"url": "https://docs.nvidia.com/dgx/dgx-spark/", "text": reference,
              "sha256": hashlib.sha256(reference.encode()).hexdigest()}
    return finding_id, {"schema": 1, "id": finding_id, "experiment_plan": plan,
                        "vendor_sources": [source], "commands": commands}


def test_kv_quant_pairs_separate_counters_and_correctness(tmp_path: Path) -> None:
    finding_id, bundle = _kv_bundle()
    evidence = tmp_path / finding_id
    evidence.mkdir()
    capture = evidence / "commands.json"
    capture.write_text(json.dumps(bundle), encoding="utf-8")
    result = controls.verify(finding_id, evidence)
    assert result["status"] == "pass", result
    run = next(row for row in bundle["commands"] if row["argv"][0] == "cat" and row["argv"][1] == "quantized-result.json")
    output = json.loads(run["stdout"])
    output["correct_tokens"] -= 1
    run["stdout"] = json.dumps(output)
    capture.write_text(json.dumps(bundle), encoding="utf-8")
    assert controls.verify(finding_id, evidence)["status"] == "fail"


def test_kv_quant_requires_primary_gb10_backend_support_reference(tmp_path: Path) -> None:
    finding_id, bundle = _kv_bundle()
    evidence = tmp_path / finding_id
    evidence.mkdir()
    capture = evidence / "commands.json"
    bundle["vendor_sources"] = []
    capture.write_text(json.dumps(bundle), encoding="utf-8")
    result = controls.verify(finding_id, evidence)
    assert result["status"] == "unknown" and result["could_not_run"] == 1, result

    reference = ("NVIDIA Corporation DGX Spark GB10 kernel 6.17.0 backend llama.cpp is unsupported on the "
                 "captured product tuple according to this primary source excerpt.")
    bundle["vendor_sources"] = [{"url": "https://docs.nvidia.com/dgx/dgx-spark/", "text": reference,
                                 "sha256": hashlib.sha256(reference.encode()).hexdigest()}]
    capture.write_text(json.dumps(bundle), encoding="utf-8")
    result = controls.verify(finding_id, evidence)
    assert result["status"] == "fail" and result["fail"] == 1, result


def test_kv_raw_metrics_and_runs_reject_unpaired_or_unmeasured_values(tmp_path: Path) -> None:
    path = tmp_path / "commands.json"
    finding_id, bundle = _kv_bundle()
    plan = bundle["experiment_plan"]
    rows = bundle["commands"]
    assert isinstance(plan, dict) and isinstance(rows, list)
    metric_rows = [row for row in rows if row["argv"][0] == "curl"]
    metric_rows[0]["phase"] = "unknown"
    snapshots, error = controls._kv_snapshots({"commands": metric_rows}, path)
    assert snapshots is None and error is not None and "phase binding" in error["reason"]

    metric_rows[0]["phase"] = "baseline"
    metric_rows[0]["stdout"] = "process_resident_memory_bytes nan\n"
    snapshots, error = controls._kv_snapshots({"commands": metric_rows}, path)
    assert snapshots is None and error is not None and "must remain separate" in error["reason"]

    workloads = [row for row in rows if row["argv"][0] == "cat" and row.get("phase") in {"baseline", "quantized"}]
    first = workloads[0]
    first["exit"] = 1
    result, error = controls._kv_runs({"commands": workloads}, path, plan)
    assert result is None and error is not None and "returned nonzero" in error["reason"]
    first["exit"] = 0
    payload = json.loads(first["stdout"])
    payload["backend"] = "other-backend"
    first["stdout"] = json.dumps(payload)
    result, error = controls._kv_runs({"commands": workloads}, path, plan)
    assert result is None and error is not None and error["status"] == "fail"


def _posthotplug_bundle() -> tuple[str, dict[str, Any], dict[str, Any]]:
    finding_id = "DELTA-FORUM-CX7-POSTHOTPLUG-01"
    hosts = ["spark-a", "gx10-b"]
    host_tuples = {
        "spark-a": {"manufacturer": "NVIDIA", "product": "DGX Spark", "bios": "1.4", "kernel": "6.17.0-1018", "firmware": "28.45.4028"},
        "gx10-b": {"manufacturer": "ASUSTeK", "product": "GX10", "bios": "1.0", "kernel": "6.17.0-1018", "firmware": "28.45.4028"},
    }
    plan: dict[str, Any] = {"bdf": "0000:03:00.0", "hosts": hosts, "host_tuples": host_tuples,
                              "minimum_gbps": 25, "fielddiag_max_age_seconds": 600,
                              "device_serial": "GX10-CX7-001", "netdev": "enp3s0f0"}
    rows: list[dict[str, Any]] = []

    def add(argv: list[str], stdout: str, phase: str | None = None, timestamp: str | None = None) -> None:
        row: dict[str, Any] = {"argv": argv, "exit": 0, "stdout": stdout, "stderr": "",
                                  "captured_at": timestamp or f"2026-10-03T12:{len(rows):02d}:00Z"}
        if phase is not None:
            row["phase"] = phase
        rows.append(row)

    add(["cat", "experiment-plan.json"], json.dumps(plan), timestamp="2026-10-03T12:00:00Z")
    for host, identity in host_tuples.items():
        add(["ssh", host, "dmidecode", "-t", "system"],
            f"Manufacturer: {identity['manufacturer']}\nProduct Name: {identity['product']}\nBIOS Version: {identity['bios']}\n")
        add(["ssh", host, "uname", "-r"], f"{identity['kernel']}\n")
        add(["ssh", host, "ethtool", "-i", "enp3s0f0"], f"firmware-version: {identity['firmware']}\n")
    pci_before = "0000:03:00.0 Ethernet controller: Mellanox 15b3:101d\nUESta: 0000\nCESta: 0000\nLnkSta: Speed 16GT/s, Width x16\nDevSta: CorrErr- UncorrErr-\n"
    add(["lspci", "-vv", "-s", "0000:03:00.0"], pci_before, "before", "2026-10-03T12:07:00Z")
    add(["lspci", "-vv", "-s", "0000:03:00.0"], pci_before, "after-hotplug", "2026-10-03T12:08:00Z")
    add(["fielddiag", "--device", "GX10-CX7-001"], "Serial: GX10-CX7-001\nStatus: PASS\n", "after-hotplug", "2026-10-03T12:08:30Z")
    bw = "#bytes #iterations BW peak[MB/sec] BW average[MB/sec]\n32768 1000 18000 17000\n"
    add(["ib_write_bw", "-D", "60"], bw, "after-hotplug:local-to-peer")
    add(["ib_write_bw", "-D", "60"], bw, "after-hotplug:peer-to-local")
    add(["all_reduce_perf", "-b", "8", "-e", "1048576", "-f", "2"],
        "# size count time algbw busbw error\n8 1 1.0 0.01 0.01 0\n", "after-hotplug")
    add(["lspci", "-D", "-nn"], "0000:03:00.0 Ethernet controller: Mellanox 15b3:101d\n", "rollback")
    add(["ethtool", "enp3s0f0"], "Settings for enp3s0f0:\n\tLink detected: yes\n", "rollback")
    body = " ".join(value for record in host_tuples.values() for value in record.values())
    reference = f"NVIDIA and ASUS GB10 CX7 supported tuple for hotplug; {body}; recovery and post-event compatibility."
    bundle: dict[str, Any] = {"schema": 1, "id": finding_id, "experiment_plan": plan,
                                 "vendor_sources": [{"url": "https://nvidia.com/dgx/spark/", "text": reference,
                                                     "sha256": hashlib.sha256(reference.encode()).hexdigest()}],
                                 "commands": rows}
    return finding_id, bundle, plan


def test_posthotplug_requires_fresh_diagnostic_and_healthy_endpoint(tmp_path: Path) -> None:
    finding_id, bundle, plan = _posthotplug_bundle()
    evidence = tmp_path / finding_id
    evidence.mkdir()
    capture = evidence / "commands.json"
    capture.write_text(json.dumps(bundle), encoding="utf-8")
    anchor = hashlib.sha256(json.dumps(plan, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    assert controls.verify(finding_id, evidence, trusted_plan_sha256=anchor)["status"] == "pass"
    post = next(row for row in bundle["commands"] if row["argv"][0] == "lspci" and row.get("phase") == "after-hotplug")
    post["stdout"] = post["stdout"].replace("UESta: 0000", "UESta: 0008 (UncorrErr+)")
    capture.write_text(json.dumps(bundle), encoding="utf-8")
    assert controls.verify(finding_id, evidence, trusted_plan_sha256=anchor)["status"] == "fail"


def test_posthotplug_rejects_missing_endpoint_diagnostic_traffic_and_rollback(tmp_path: Path) -> None:
    variants = (
        ("endpoint", "fail"), ("stale", "fail"), ("serial", "unknown"),
        ("direction", "unknown"), ("low-rate", "fail"), ("nccl", "fail"), ("rollback", "unknown"),
    )
    for name, expected in variants:
        finding_id, bundle, plan = _posthotplug_bundle()
        rows = bundle["commands"]
        assert isinstance(rows, list)
        post = next(row for row in rows if row.get("phase") == "after-hotplug" and row["argv"][0] == "lspci")
        if name == "endpoint":
            post["stdout"] = post["stdout"].replace("0000:03:00.0", "0000:04:00.0")
        elif name == "stale":
            next(row for row in rows if row.get("phase") == "after-hotplug" and row["argv"][0] == "fielddiag")["captured_at"] = "2026-10-03T10:00:00Z"
        elif name == "serial":
            next(row for row in rows if row.get("phase") == "after-hotplug" and row["argv"][0] == "fielddiag")["stdout"] = "Serial: wrong\nStatus: PASS\n"
        elif name == "direction":
            rows.remove(next(row for row in rows if row.get("phase") == "after-hotplug:peer-to-local"))
        elif name == "low-rate":
            next(row for row in rows if row.get("phase") == "after-hotplug:local-to-peer")["stdout"] = "BW average[MB/sec]\n1024 10 1 1\n"
        elif name == "nccl":
            next(row for row in rows if row.get("phase") == "after-hotplug" and row["argv"][0] == "all_reduce_perf")["stdout"] = "# size count time algbw busbw error\n8 1 1.0 0.01 0.01 1\n"
        else:
            rows.remove(next(row for row in rows if row.get("phase") == "rollback" and row["argv"][0] == "lspci"))
        evidence = tmp_path / f"{finding_id}-{name}"
        evidence.mkdir()
        (evidence / "commands.json").write_text(json.dumps(bundle), encoding="utf-8")
        anchor = hashlib.sha256(json.dumps(plan, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        result = controls.verify(finding_id, evidence, trusted_plan_sha256=anchor)
        assert result["status"] == expected, result


def test_posthotplug_pci_gate_requires_endpoint_and_clean_aer_before_after(tmp_path: Path) -> None:
    path = tmp_path / "commands.json"
    bdf = "0000:03:00.0"
    before = {"argv": ["lspci", "-vv", "-s", bdf], "exit": 0, "phase": "before",
              "stdout": f"{bdf} CX7\nUESta: 0\nCESta: 0\nLnkSta: 16GT/s\nDevSta: 0\n"}
    after = {**before, "phase": "after-hotplug"}
    plan = {"bdf": bdf}
    assert controls._posthotplug_pci({"commands": [before, after]}, path, plan) is None
    cases = (
        ([], plan, "unknown", "captures missing"),
        ([{**before, "exit": 2}, after], plan, "fail", "inventory failed"),
        ([before, after], {"bdf": "not-a-bdf"}, "unknown", "exact CX7 PCI BDF missing"),
        ([before, {**after, "stdout": "0000:04:00.0 CX7\nUESta:0\nCESta:0\nLnkSta:0\nDevSta:0\n"}],
         plan, "fail", "disappeared"),
        ([before, {**after, "stdout": f"{bdf} CX7\nUESta:0\n"}], plan, "unknown", "fields are not fully captured"),
        ([before, {**after, "stdout": f"{bdf} CX7\nUESta: CorrErr+\nCESta:0\nLnkSta:0\nDevSta:0\n"}],
         plan, "fail", "AER reports"),
    )
    for rows, contract, status, phrase in cases:
        error = controls._posthotplug_pci({"commands": rows}, path, contract)
        assert error is not None and error["status"] == status and phrase in error["reason"]


def test_posthotplug_service_admission_checks_fresh_serial_bound_fielddiag(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "commands.json"
    pci = {"argv": ["lspci", "-vv"], "exit": 0, "phase": "after-hotplug",
           "captured_at": "2026-10-03T12:00:00Z", "stdout": "PCI state"}
    diagnostic = {"argv": ["fielddiag", "--device", "serial-1"], "exit": 0,
                  "phase": "after-hotplug", "captured_at": "2026-10-03T12:01:00Z",
                  "stdout": "Serial: serial-1\nStatus: PASS\n"}
    plan = {"fielddiag_max_age_seconds": 600, "device_serial": "serial-1"}
    monkeypatch.setattr(controls, "_posthotplug_traffic", lambda data, evidence, captured: None)
    assert controls._posthotplug_services({"commands": [pci, diagnostic]}, path, plan) is None
    for rows, status, phrase in (
        ([diagnostic], "unknown", "PCI timestamp missing"),
        ([pci], "unknown", "FieldDiag capture missing"),
        ([pci, {**diagnostic, "captured_at": "2026-10-03T10:00:00Z"}], "fail", "stale"),
        ([pci, {**diagnostic, "stdout": "Serial: serial-1\nStatus: FAIL\n"}], "fail", "failed or unavailable"),
        ([pci, {**diagnostic, "stdout": "Status: PASS\n"}], "unknown", "not bound"),
    ):
        error = controls._posthotplug_services({"commands": rows}, path, plan)
        assert error is not None and error["status"] == status and phrase in error["reason"]


def test_secondary_orchestrators_preserve_first_gate_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Orchestrators stop at the first missing prerequisite instead of claiming later gates."""
    path = tmp_path / "commands.json"
    plan = {"required": "plan"}
    missing = controls._result("unknown", "first prerequisite absent", path)

    monkeypatch.setattr(controls, "_capture_plan", lambda _data, _path: (None, missing))
    assert controls._fw_guard({"commands": []}, path) == missing
    assert controls._posthotplug({"commands": []}, path) == missing
    assert controls._ota_tuple({"commands": []}, path) == missing
    assert controls._recovery_apt({"commands": []}, path) == missing

    monkeypatch.setattr(controls, "_capture_plan", lambda _data, _path: (plan, None))
    monkeypatch.setattr(controls, "_plan_approval", lambda _data, _path, _plan: missing)
    assert controls._fw_guard({"commands": []}, path) == missing
    assert controls._posthotplug({"commands": []}, path) == missing
    assert controls._ota_tuple({"commands": []}, path) == missing

    monkeypatch.setattr(controls, "_plan_approval", lambda _data, _path, _plan: None)
    monkeypatch.setattr(controls, "_identity", lambda _data, _path: (None, missing))
    assert controls._fw_guard({"commands": []}, path) == missing
    assert controls._ota_tuple({"commands": []}, path) == missing


def test_firmware_suborchestrators_return_the_first_native_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "commands.json"
    error = controls._result("unknown", "target mapping unavailable", path)
    monkeypatch.setattr(controls, "_fw_device_target", lambda _plan, _path: (None, error))
    assert controls._fw_device({"commands": []}, path, {}) == error

    monkeypatch.setattr(controls, "_fw_device_target", lambda _plan, _path: (("0000:03:00.0", "mlx5_0"), None))
    monkeypatch.setattr(controls, "_fw_query", lambda _data, _path, _bdf: (None, error))
    assert controls._fw_device({"commands": []}, path, {}) == error

    package_error = controls._result("unknown", "package digest unavailable", path)
    monkeypatch.setattr(controls, "_fw_package_contract", lambda _plan, _path: (None, package_error))
    assert controls._fw_package_guard({"commands": []}, path, {}) == package_error


def test_memory_series_and_ota_soak_contract_reject_unobserved_intervals(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "commands.json"
    rows = [{"phase": "soak", "sample": f"sample-{index}"} for index in range(6)]
    parsed, error = controls._memory_samples({"commands": rows}, path)
    assert parsed is None and error is not None and "time series" in error["reason"]
    parsed, error = controls._memory_samples({"commands": [{"phase": "soak"}]}, path)
    assert parsed is None and error is not None and "grouping" in error["reason"]

    plan = {"workload_soak": {"argv": ["bench", "--read-only"], "model_sha256": "a" * 64,
                              "input_sha256": "b" * 64, "pid": 123, "duration_seconds": 60,
                              "max_sample_gap_seconds": 30}}
    absent = controls._ota_soak({"commands": [{"phase": "workload-soak"}]}, path, plan)
    assert absent["status"] == "unknown" and "grouping" in absent["reason"]

    stamp = datetime(2026, 10, 4, tzinfo=timezone.utc)
    observation = (stamp, 4096, "123 (worker) S 100")
    monkeypatch.setattr(controls, "_ota_soak_sample", lambda *_args: (observation, None))
    too_short = controls._ota_soak(
        {"commands": [{"phase": "workload-soak", "sample": "one"},
                      {"phase": "workload-soak", "sample": "two"}]}, path, plan)
    assert too_short["status"] == "unknown" and "span" in too_short["reason"]


def test_ota_native_field_extractor_ignores_unrecognized_nvsm_lines() -> None:
    assert controls._ota_nvsm_fields("unrelated status line\n") == {}
    assert controls._ota_fields_from_row({"argv": ["nvsm", "show", "firmware"], "stdout": ""}) == {}


def test_firmware_helper_scanner_distinguishes_ambiguous_missing_and_safe_chains(tmp_path: Path) -> None:
    path = tmp_path / "commands.json"
    script = {"stdout": "#!/bin/sh\neval \"$ACTION\"\n"}
    result = controls._fw_script_helpers({"commands": []}, path, [script])
    assert result is not None and result["status"] == "unknown" and "dynamic" in result["reason"]
    assert controls._fw_script_helpers({"commands": []}, path, [{"stdout": "#!/bin/sh\ntrue\n"}]) is None

    helper = "/usr/lib/vendor/fw-helper.sh"
    invoked = {"argv": ["sh", helper], "stdout": f"#!/bin/sh\nexec sh {helper}\n"}
    result = controls._fw_script_helpers({"commands": [invoked]}, path, [invoked])
    assert result is not None and result["status"] == "unknown" and "bytes" in result["reason"]
    capture = {"argv": ["cat", helper], "exit": 1, "stdout": "", "phase": "helper-source"}
    result = controls._check_helper_source({"commands": [capture]}, path, helper)
    assert result is not None and result["status"] == "fail" and "read failed" in result["reason"]
    for source, status, phrase in (
        ("#!/bin/sh\nexec sh /usr/lib/vendor/inner.sh\n", "unknown", "nested"),
        ("#!/bin/sh\nflint -d 03:00.0 burn fw.bin\n", "fail", "writer"),
        ("plain text helper", "unknown", "recognized shell"),
    ):
        capture = {"argv": ["cat", helper], "exit": 0, "stdout": source, "phase": "helper-source"}
        result = controls._check_helper_source({"commands": [capture]}, path, helper)
        assert result is not None and result["status"] == status and phrase in result["reason"]


def test_firmware_identity_and_binding_error_paths_remain_distinct(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    path = tmp_path / "commands.json"
    identity = {"argv": ["dmidecode", "-t", "system"], "exit": 0,
                "stdout": "not a key/value row\nManufacturer: ASUS\nProduct Name: GX10\nBIOS Version: 1\n"}
    kernel = {"argv": ["uname", "-r"], "exit": 0, "stdout": "6.17\n"}
    parsed, error = controls._identity({"commands": [identity, kernel]}, path)
    assert error is None and parsed is not None and parsed["Kernel"] == "6.17"

    missing = controls._fw_pci_binding({"commands": []}, path, "0000:03:00.0")
    assert missing is not None and missing["status"] == "unknown"
    missing = controls._fw_hca_binding({"commands": []}, path, "0000:03:00.0", "mlx5_0", "28.45.1")
    assert missing is not None and missing["status"] == "unknown"

    error = controls._result("unknown", "recovery missing", path)
    monkeypatch.setattr(controls, "_capture_plan", lambda _data, _path: ({}, None))
    monkeypatch.setattr(controls, "_plan_approval", lambda _data, _path, _plan: None)
    monkeypatch.setattr(controls, "_identity", lambda _data, _path: ({"Manufacturer": "ASUS", "Product Name": "GX10"}, None))
    monkeypatch.setattr(controls, "_fw_device", lambda *_args: None)
    monkeypatch.setattr(controls, "_fw_package_guard", lambda *_args: None)
    monkeypatch.setattr(controls, "_fw_recovery", lambda *_args: error)
    assert controls._fw_guard({"commands": []}, path) == error


def test_ota_and_recovery_orchestrators_preserve_domain_gate_failures(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "commands.json"
    plan: dict[str, Any] = {
        "last_kernel": "6.17", "last_driver": "580.1", "last_package": "pkg",
        "console_route": "external-console", "recovery_media_path": "/media/oem.iso",
        "recovery_media_sha256": "a" * 64, "oem_recovery_url": "https://asus.com/recovery",
    }
    missing = controls._result("unknown", "domain input missing", path)
    monkeypatch.setattr(controls, "_capture_plan", lambda _data, _path: (plan, None))
    monkeypatch.setattr(controls, "_plan_approval", lambda _data, _path, _plan: None)
    monkeypatch.setattr(controls, "_identity", lambda _data, _path: ({"Manufacturer": "ASUS"}, None))
    monkeypatch.setattr(controls, "_ota_observations", lambda _data, _path: (None, missing))
    assert controls._ota_tuple({"commands": []}, path) == missing

    monkeypatch.setattr(controls, "_ota_observations", lambda _data, _path: ({}, None))
    comparison = controls._result("unknown", "supported tuple unavailable", path)
    monkeypatch.setattr(controls, "_ota_compare", lambda *_args: comparison)
    assert controls._ota_tuple({"commands": []}, path) == comparison

    for gate in ("_recovery_packages", "_recovery_access", "_recovery_media"):
        monkeypatch.setattr(controls, gate, lambda *_args: missing)
        assert controls._recovery_apt({"experiment_plan": plan, "commands": []}, path) == missing


def test_firmware_package_guard_checks_each_package_stage_before_channel_validation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "commands.json"
    package = ("/tmp/cx7.deb", "cx7-firmware", "a" * 64)
    monkeypatch.setattr(controls, "_fw_package_contract", lambda *_args: (package, None))
    assert controls._fw_package_guard({"commands": []}, path, {}) is not None  # package bytes absent

    monkeypatch.setattr(controls, "_fw_package_digest", lambda *_args: None)
    error = controls._result("unknown", "extract unavailable", path)
    monkeypatch.setattr(controls, "_fw_package_scripts", lambda *_args: (None, error))
    assert controls._fw_package_guard({"commands": []}, path, {"script_extract_dir": "/tmp/scripts"}) == error

    monkeypatch.setattr(controls, "_fw_package_scripts", lambda *_args: ([{"argv": ["dpkg", "preinst"], "exit": 0, "stdout": "#!/bin/sh\n"}], None))
    missing_stage = controls._fw_package_guard({"commands": []}, path, {"script_extract_dir": "/tmp/scripts"})
    assert missing_stage is not None and missing_stage["status"] == "unknown" and "scripts missing" in missing_stage["reason"]

    stages = [{"argv": ["dpkg", stage], "exit": 0, "stdout": "#!/bin/sh\n"}
              for stage in ("preinst", "postinst", "prerm", "postrm")]
    helper_error = controls._result("unknown", "helper unresolved", path)
    monkeypatch.setattr(controls, "_fw_package_scripts", lambda *_args: (stages, None))
    monkeypatch.setattr(controls, "_fw_script_helpers", lambda *_args: helper_error)
    assert controls._fw_package_guard({"commands": []}, path, {"script_extract_dir": "/tmp/scripts"}) == helper_error

    monkeypatch.setattr(controls, "_fw_package_scripts", lambda *_args: (stages, None))
    monkeypatch.setattr(controls, "_fw_script_helpers", lambda *_args: None)
    monkeypatch.setattr(controls, "_fw_signature_source", lambda *_args: None)
    assert controls._fw_package_guard({"commands": []}, path, {"script_extract_dir": "/tmp/scripts"}) is None
    assert controls._firmware_script_analysis("#!/bin/sh\npython3 /tmp/helper.py\n")[2]


def test_module_entrypoint_prints_unknown_and_returns_exit_two(tmp_path: Path) -> None:
    finding_id = controls.IDS[0]
    completed = subprocess.run(
        [sys.executable, "-m", "tools.hardware_batch02_controls", "--id", finding_id, "--evidence", str(tmp_path)],
        check=False, capture_output=True, text=True, cwd=controls.ROOT,
    )
    assert completed.returncode == 2
    parsed = json.loads(completed.stdout)
    assert parsed["status"] == "unknown" and parsed["could_not_run"] == 1


def test_topology_orchestrator_preserves_map_and_traffic_verdicts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "commands.json"
    plan = {"links": []}
    monkeypatch.setattr(controls, "_capture_plan", lambda _data, _path: (plan, None))
    monkeypatch.setattr(controls, "_identity", lambda _data, _path: ({"Product Name": "test"}, None))
    topology_error = controls._result("unknown", "physical map missing", path)
    monkeypatch.setattr(controls, "_topology_map", lambda *_args: topology_error)
    assert controls._topology({"commands": []}, path) == topology_error

    monkeypatch.setattr(controls, "_topology_map", lambda *_args: None)
    traffic_error = controls._result("fail", "measured negative traffic", path)
    monkeypatch.setattr(controls, "_topology_traffic", lambda *_args: traffic_error)
    assert controls._topology({"commands": []}, path) == traffic_error

    monkeypatch.setattr(controls, "_topology_traffic", lambda *_args: None)
    result = controls._topology({"commands": []}, path)
    assert result["status"] == "pass" and "LLDP" in result["reason"]


def test_firmware_and_rdma_pair_predicates_fail_on_wrong_subject_or_failed_direction(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    path = tmp_path / "commands.json"
    monkeypatch.setattr(controls, "_fw_device_target", lambda *_args: (("0000:03:00.0", "mlx5_0"), None))
    query = {"argv": ["flint", "-d", "03:00.0", "q"], "exit": 0,
             "stdout": "PSID: WRONG\nFW Version: 28.45.1\n"}
    monkeypatch.setattr(controls, "_fw_query", lambda *_args: (query, None))
    result = controls._fw_device({"commands": []}, path, {})
    assert result is not None and result["status"] == "fail" and "PSID" in result["reason"]

    for rows, status, phrase in (
        ([], "unknown", "missing raw"),
        ([{"argv": ["ib_write_bw"], "phase": "cold:spark_to_gx10", "exit": 1, "stdout": "", "stderr": ""}], "fail", "failed"),
        ([{"argv": ["ib_write_bw"], "phase": "cold:spark_to_gx10", "exit": 0, "stdout": "no measurement"}], "fail", "invalid bandwidth"),
    ):
        rates, error = controls._asymmetry_pair({"commands": rows}, "cold", path)
        assert rates is None and error is not None and error["status"] == status and phrase in error["reason"]


def test_power_records_reject_out_of_plan_identity_and_ignore_unmeasured_rows(tmp_path: Path) -> None:
    path = tmp_path / "commands.json"
    plan = {"model_sha256": "a" * 64, "input_sha256": "b" * 64, "concurrency": 1}
    bad_host = {"phase": "before-reset", "host": "other", "cycle": 1, "exit": 0,
                "argv": ["cat"], "stdout": "{}"}
    records, error = controls._power_records({"commands": [bad_host]}, path, ["host-a"], 1, plan)
    assert records is None and error is not None and error["status"] == "fail"

    unmeasured = {**bad_host, "host": "host-a", "stdout": "not JSON"}
    records, error = controls._power_records({"commands": [unmeasured]}, path, ["host-a"], 1, plan)
    assert records == {} and error is None


def test_signed_package_verifier_propagates_each_integrity_failure(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    path = tmp_path / "commands.json"
    err = controls._result("unknown", "signature inputs unavailable", path)
    monkeypatch.setattr(controls, "_signature_inputs", lambda *_args: (None, None, None, None, err))
    assert controls._verify_signed_release({"commands": []}, path, {}) == (None, err)

    index_path = "/var/lib/apt/lists/vendor_Packages"
    plan = {"packages_index_path": index_path, "inrelease_artifact": "raw/InRelease",
            "package_index_relative": "main/binary-arm64/Packages", "package_size": 7}
    index_row = {"argv": ["cat", index_path], "exit": 0, "stdout": "signed index bytes"}
    capture = tmp_path / "commands.json"
    (tmp_path / "raw").mkdir()
    (tmp_path / "raw/InRelease").write_text("SHA256:\n " + "0" * 64 + " 17 main/binary-arm64/Packages\n", encoding="utf-8")
    error = controls._verify_signed_package_index({"commands": [index_row]}, capture, plan, "pkg", "/tmp/pkg.deb")
    assert error is not None and error["status"] == "fail" and "signed InRelease" in error["reason"]

    (tmp_path / "raw/InRelease").write_text("SHA256:\n " + hashlib.sha256(b"signed index bytes").hexdigest()
                                             + " 18 main/binary-arm64/Packages\n", encoding="utf-8")
    stanza_error = controls._result("unknown", "stanza unavailable", capture)
    monkeypatch.setattr(controls, "_verify_packages_stanza", lambda *_args: stanza_error)
    error = controls._verify_signed_package_index({"commands": [index_row]}, capture, plan, "pkg", "/tmp/pkg.deb")
    assert error == stanza_error

    monkeypatch.setattr(controls, "_verify_packages_stanza", lambda *_args: None)
    size_error = controls._result("unknown", "deb size query unavailable", capture)
    monkeypatch.setattr(controls, "_native_file_size", lambda *_args: (None, size_error))
    error = controls._verify_signed_package_index({"commands": [index_row]}, capture, plan, "pkg", "/tmp/pkg.deb")
    assert error == size_error


def test_signed_release_parsers_stop_at_section_boundary_and_missing_artifacts(tmp_path: Path) -> None:
    digest = "a" * 64
    assert controls._release_index_entry(f"SHA256:\n {digest} 7 main/Packages\nMD5Sum:\n {digest} 7 ignored\n", "main/Packages") == (digest, 7)
    assert controls._release_index_entry(f"SHA256:\n {digest} 7 main/Packages\nSHA1:\n {digest} 7 other\n", "other") is None
    assert controls._captured_inrelease(tmp_path, {"inrelease_artifact": "../escape"}) == ""


def test_kv_metrics_keep_native_comments_and_ignore_unrelated_samples(tmp_path: Path) -> None:
    path = tmp_path / "commands.json"
    metric = ("# HELP process metrics\nnot a native counter row\nunknown_vendor_metric 12\n"
              "process_resident_memory_bytes 4096\ncontainer_memory_working_set_bytes 8192\n"
              "node_memory_MemAvailable_bytes 16384\nnode_memory_SwapFree_bytes 2048\n"
              "llamacpp_kv_cache_bytes 1024\n")
    rows = [{"argv": ["curl", "http://localhost/metrics"], "exit": 0,
             "stdout": metric, "phase": phase} for phase in ("baseline", "quantized")]
    snapshots, error = controls._kv_snapshots({"commands": rows}, path)
    assert error is None and snapshots is not None
    assert snapshots["baseline"][0]["process_resident_memory_bytes"] == 4096
    assert "unknown_vendor_metric" not in snapshots["baseline"][0]


def test_cx7_binding_requires_domain_inventory_and_active_hca_readback(tmp_path: Path) -> None:
    path = tmp_path / "commands.json"
    bdf = "0000:03:00.0"
    targeted = {"argv": ["lspci", "-s", bdf, "-vv"], "exit": 0,
                "stdout": f"{bdf} Ethernet 15b3:101d\nBusMaster+\nKernel driver in use: mlx5_core\n"}
    missing_inventory = controls._fw_pci_binding({"commands": [targeted]}, path, bdf)
    assert missing_inventory is not None and missing_inventory["status"] == "unknown"

    sysfs = {"argv": ["readlink", "-f", "/sys/class/infiniband/mlx5_0/device"], "exit": 0,
             "stdout": f"/sys/devices/pci0000:00/{bdf}"}
    missing_rdma = controls._fw_hca_binding({"commands": [sysfs]}, path, bdf, "mlx5_0", "28.45.1")
    assert missing_rdma is not None and missing_rdma["status"] == "unknown"


def test_native_repository_and_recovery_queries_keep_could_not_run_distinct(tmp_path: Path) -> None:
    path = tmp_path / "commands.json"
    plan = {
        "package_origin": "repo.nvidia.com", "package_source_uri": "https://repo.nvidia.com/ubuntu",
        "package_version": "1.0", "inrelease_path": "/tmp/InRelease", "keyring_path": "/tmp/keyring.gpg",
        "repository_fingerprint": "A" * 40, "inrelease_artifact": "raw/InRelease",
        "keyring_artifact": "raw/keyring.gpg", "inrelease_sha256": "a" * 64, "keyring_sha256": "b" * 64,
        "packages_index_path": "/tmp/Packages", "package_index_relative": "main/binary-arm64/Packages",
        "package_filename": "pool/fw.deb", "package_size": 100,
        "package_architecture": "arm64", "package_component": "main", "package_suite": "noble",
    }
    result = controls._fw_repository_plan({"commands": []}, path, plan, "fw")
    assert result is not None and result["status"] == "unknown" and "required raw command" in result["reason"]
    incomplete = {**plan, "package_component": None}
    policy = {"argv": ["apt-cache", "policy", "fw"], "exit": 0,
              "stdout": "500 https://repo.nvidia.com/ubuntu noble/main arm64 Packages\n"}
    result = controls._fw_repository_plan({"commands": [policy]}, path, incomplete, "fw")
    assert result is not None and result["status"] == "unknown" and "tuple is incomplete" in result["reason"]


def test_cutlass_and_topology_stop_when_subject_or_map_is_unknown(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    path = tmp_path / "commands.json"
    error = controls._result("unknown", "subject identity absent", path)
    monkeypatch.setattr(controls, "_identity", lambda *_args: (None, error))
    assert controls._cutlass_build({"commands": []}, path, {}) == error

    rows, links = _topology_native_map()
    plan = {"links": links}
    link_error = controls._result("unknown", "link plan unresolved", path)
    monkeypatch.setattr(controls, "_validate_link_plan", lambda *_args: link_error)
    assert controls._topology_map({"commands": rows}, plan, path) == link_error

    monkeypatch.setattr(controls, "_validate_link_plan", lambda *_args: None)
    monkeypatch.setattr(controls, "_validate_link_devices", lambda *_args: None)
    no_peer = controls._topology_map({"commands": rows[:-1]}, plan, path)
    assert no_peer is not None and no_peer["status"] == "unknown" and "required raw" in no_peer["reason"]


def test_posthotplug_and_asymmetry_orchestrators_stop_before_measurement(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    path = tmp_path / "commands.json"
    plan = {"hosts": ["a", "b"], "scenarios": ["cold", "reboot-individual", "reboot-sequential", "hotplug"],
            "max_directional_ratio": 1.25}
    error = controls._result("unknown", "stack tuple absent", path)
    monkeypatch.setattr(controls, "_capture_plan", lambda *_args: (plan, None))
    monkeypatch.setattr(controls, "_plan_approval", lambda *_args: None)
    monkeypatch.setattr(controls, "_rdma_stack_identity", lambda *_args: error)
    assert controls._posthotplug({"commands": []}, path) == error
    assert controls._rdma_asymmetry({"commands": []}, path) == error

    monkeypatch.setattr(controls, "_capture_plan", lambda *_args: (None, error))
    assert controls._rdma_asymmetry({"commands": []}, path) == error


def test_posthotplug_traffic_rejects_missing_measurements_before_ncccl(tmp_path: Path) -> None:
    path = tmp_path / "commands.json"
    missing = controls._posthotplug_traffic({"commands": []}, path, {"minimum_gbps": 10})
    assert missing is not None and missing["status"] == "unknown" and "incomplete" in missing["reason"]

    def rate(phase: str) -> dict[str, Any]:
        return {"argv": ["ib_write_bw"], "phase": phase, "exit": 0,
                "stdout": "BW average: 20 Gbps", "stderr": ""}

    rows = [rate("after-hotplug:local-to-peer"), rate("after-hotplug:peer-to-local")]
    no_collective = controls._posthotplug_traffic({"commands": rows}, path, {"minimum_gbps": 10})
    assert no_collective is not None and no_collective["status"] == "unknown" and "NCCL" in no_collective["reason"]


def test_remaining_plan_and_capture_gaps_are_explicit_could_not_run(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    path = tmp_path / "commands.json"
    error = controls._result("unknown", "predeclared plan missing", path)
    monkeypatch.setattr(controls, "_capture_plan", lambda *_args: (None, error))
    assert controls._dual_spark({"commands": []}, path) == error
    monkeypatch.setattr(controls, "_identity", lambda *_args: (None, error))
    assert controls._topology({"commands": []}, path) == error

    assert _status(controls._rdma_stack_identity({"commands": []}, path, {"hosts": ["one"]})) == "unknown"
    plan = {"workload_soak": {"argv": ["bench"], "model_sha256": "a" * 64,
                              "input_sha256": "b" * 64, "pid": 1, "duration_seconds": 1,
                              "max_sample_gap_seconds": 1}}
    absent = controls._ota_soak({"commands": []}, path, plan)
    assert absent["status"] == "unknown" and "repeated" in absent["reason"]

    phases, incomplete = controls._ota_observations({"commands": []}, path)
    assert phases is None and incomplete is not None and "tuple incomplete" in incomplete["reason"]


def test_kv_run_parser_preserves_absent_malformed_and_unmeasured_states(tmp_path: Path) -> None:
    path = tmp_path / "commands.json"
    plan = {"model_sha256": "a" * 64, "backend": "vllm", "baseline_kv_mode": "fp16",
            "quantized_kv_mode": "fp8", "context_tokens": 1024, "concurrency": 1,
            "input_sha256": "b" * 64}
    result, error = controls._kv_runs({"commands": []}, path, plan)
    assert result is None and error is not None and "matched baseline" in error["reason"]
    rows = [{"argv": ["cat", "result.json"], "phase": phase, "exit": 0, "stdout": "[]"}
            for phase in ("baseline", "quantized")]
    result, error = controls._kv_runs({"commands": rows}, path, plan)
    assert result is None and error is not None and "malformed" in error["reason"]
    rows[0]["stdout"] = json.dumps({"model_sha256": "a" * 64, "backend": "vllm",
                                  "kv_mode": "fp16", "context_tokens": 1024, "concurrency": 1,
                                  "input_sha256": "b" * 64})
    result, error = controls._kv_runs({"commands": rows}, path, plan)
    assert result is None and error is not None and "prefill_tokens_s" in error["reason"]


def test_remaining_native_negative_rows_remain_distinct(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    path = tmp_path / "commands.json"
    assert not controls._contains_firmware_writer("#!/bin/sh\nflint 'unterminated\n")

    rates = [{"argv": ["ib_write_bw"], "phase": phase, "exit": 0, "stdout": "unparsed native report"}
             for phase in ("after-hotplug:local-to-peer", "after-hotplug:peer-to-local")]
    result = controls._posthotplug_traffic({"commands": rates}, path, {"minimum_gbps": 1})
    assert result is not None and result["status"] == "unknown" and "measured traffic" in result["reason"]

    error = controls._result("unknown", "scenario plan malformed", path)
    monkeypatch.setattr(controls, "_capture_plan", lambda *_args: ({}, None))
    monkeypatch.setattr(controls, "_asymmetry_plan", lambda *_args: (None, None, error))
    assert controls._rdma_asymmetry({"commands": []}, path) == error

    plan = {"model_sha256": "a" * 64, "input_sha256": "b" * 64, "concurrency": 1}
    row = {"phase": "before-reset", "host": "host-a", "cycle": 1, "exit": 0,
           "argv": ["cat"], "stdout": json.dumps({"power_w": 1})}
    records, error = controls._power_records({"commands": [row]}, path, ["host-a"], 1, plan)
    assert records == {} and error is None


def test_kv_support_source_must_bind_subject_and_backend(tmp_path: Path) -> None:
    path = tmp_path / "commands.json"
    text = "ASUS DGX Spark board product, kernel 6.17.0, backend vllm support is documented here." + (" " * 100)
    ref = {"url": "https://docs.nvidia.com/dgx/guide", "text": text,
           "sha256": hashlib.sha256(text.encode()).hexdigest()}
    identity = {"Manufacturer": "ASUS", "Product Name": "DGX Spark", "Kernel": "6.17.0"}
    refs, error = controls._kv_vendor_support({"vendor_sources": [ref]}, path, identity, {"backend": "vllm"})
    assert refs is None and error is not None and "does not bind" in error


def test_recovery_orchestrator_evaluates_each_gate_in_order(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    path = tmp_path / "commands.json"
    plan = {"last_kernel": "6.17", "last_driver": "580.1", "last_package": "pkg",
            "console_route": "console", "recovery_media_path": "/media/oem.iso",
            "recovery_media_sha256": "a" * 64, "oem_recovery_url": "https://asus.com/recovery"}
    missing = controls._result("unknown", "one required capture absent", path)
    recovery_access = controls._recovery_access
    recovery_packages = controls._recovery_packages
    recovery_media = controls._recovery_media
    monkeypatch.setattr(controls, "_capture_plan", lambda *_args: (plan, None))
    monkeypatch.setattr(controls, "_recovery_packages", lambda *_args: None)
    monkeypatch.setattr(controls, "_recovery_access", lambda *_args: missing)
    monkeypatch.setattr(controls, "_recovery_media", lambda *_args: None)
    assert controls._recovery_apt({"commands": []}, path) == missing

    monkeypatch.setattr(controls, "_recovery_access", lambda *_args: None)
    assert controls._recovery_apt({"commands": []}, path) == controls._result(
        "pass", "last package tuple, hashed OEM media path, external console and recovery/rollback/RMA runbook parsed", path)

    access = recovery_access({"experiment_plan": plan, "commands": []}, path)
    assert access is not None and access["status"] == "unknown" and "required raw command" in access["reason"]
    package_text = "ASUS recovery guide confirms kernel 6.17 driver 580.1 package pkg compatibility." + (" " * 80)
    package_ref = {"url": "https://asus.com/recovery", "text": package_text,
                   "sha256": hashlib.sha256(package_text.encode()).hexdigest()}
    package = recovery_packages({"vendor_sources": [package_ref], "commands": []}, path, plan)
    assert package is not None and package["status"] == "unknown" and "dpkg transaction" in package["reason"]

    console = {"argv": ["ssh", "console"], "exit": 0, "stdout": "connected", "stderr": ""}
    runbook = recovery_access({"experiment_plan": plan, "commands": [console]}, path)
    assert runbook is not None and runbook["status"] == "unknown" and "recovery procedure" in runbook["reason"]
    media = recovery_media({"experiment_plan": plan, "commands": []}, path, plan)
    assert media is not None and media["status"] == "unknown" and "required raw command" in media["reason"]


def test_duplicate_native_capture_keys_are_rejected(tmp_path: Path) -> None:
    evidence = tmp_path / "evidence"
    evidence.mkdir()
    capture = evidence / "commands.json"
    capture.write_text(
        '{"schema":1,"id":"' + controls.IDS[0] + '","commands":[],"commands":[]}',
        encoding="utf-8",
    )
    result = controls.verify(controls.IDS[0], evidence)
    assert result["status"] == "unknown" and result["could_not_run"] == 1
    assert "duplicate object key" in result["reason"]
