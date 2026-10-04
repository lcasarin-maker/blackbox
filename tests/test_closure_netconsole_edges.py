"""Adversarial netconsole closure tests: evidence fields are recomputed from raw captures."""
from __future__ import annotations

import json
from pathlib import Path

from tools.verify_netconsole import (
    _continuity, _correlation_and_retention, _receiver, _receiver_controls,
    _rollback_states, _unavailable_control,
)



def _asserted_status(result: dict[str, object] | None) -> object:
    assert result is not None, "verifier returned no result object"
    return result["status"]

def test_netconsole_root_counterexample_requires_real_controls_and_enabled_secureboot(tmp_path):
    from test_closure_kernel import _netconsole_case

    boot, _, _, _, before, receipt = _netconsole_case(tmp_path)
    receipt.pop("broken_route_control")
    assert _asserted_status(_receiver(receipt, boot, before)) == "unknown"
    _, _, _, _, before, receipt = _netconsole_case(tmp_path)
    receipt["secure_boot_output"] = "SecureBoot disabled"
    assert _asserted_status(_receiver(receipt, boot, before)) == "fail"


def test_netconsole_correct_module_absent_loaded_absent_rollback_passes(tmp_path):
    from test_closure_kernel import _netconsole_case

    boot, _, _, _, after, receipt = _netconsole_case(tmp_path)
    states = receipt["rollback_capture"]
    assert _asserted_status(states["before"]["module"]) == "absent"
    assert _asserted_status(states["during"]["module"]) == "loaded"
    assert _asserted_status(states["after"]["module"]) == "absent"
    assert _rollback_states(receipt, after) is None
    assert _asserted_status(_receiver(receipt, boot, after)) == "pass"


def test_netconsole_changed_fresh_after_state_and_incomplete_controls_reject(tmp_path):
    from test_closure_kernel import _netconsole_case

    boot, _, _, _, after, receipt = _netconsole_case(tmp_path)
    changed = json.loads(json.dumps(after))
    changed["boot_parameter_present"] = True
    assert _asserted_status(_rollback_states(receipt, changed)) == "fail"
    receipt["unavailable_receiver_control"]["returncode"] = 0
    assert _asserted_status(_receiver(receipt, boot, after)) == "fail"


def test_netconsole_negative_control_raw_log_must_be_absent_and_route_command_real(tmp_path):
    from test_closure_kernel import _netconsole_case

    boot, _, _, _, after, receipt = _netconsole_case(tmp_path)
    route = receipt["broken_route_control"]
    route["command"] = ["false"]
    assert _asserted_status(_receiver(receipt, boot, after)) == "unknown"
    _, _, _, _, after, receipt = _netconsole_case(tmp_path)
    route = receipt["broken_route_control"]
    route["marker"] = "distinct-route-control-marker"
    with open(route["after_log_path"], "a", encoding="utf-8") as stream:
        stream.write(route["marker"] + "\n")
    assert _asserted_status(_receiver(receipt, boot, after)) == "fail"


def test_netconsole_receiver_unavailable_requires_systemd_inactive_raw_output(tmp_path):
    from test_closure_kernel import _netconsole_case

    boot, _, _, _, after, receipt = _netconsole_case(tmp_path)
    receipt["unavailable_receiver_control"]["stdout"] = "active"
    assert _asserted_status(_receiver(receipt, boot, after)) == "unknown"
    _, _, _, _, after, receipt = _netconsole_case(tmp_path)
    receipt["unavailable_receiver_control"]["command"] = ["systemctl", "is-active"]
    assert _asserted_status(_receiver(receipt, boot, after)) == "unknown"


def test_netconsole_journal_and_telemetry_must_span_negative_control_windows(tmp_path):
    from test_closure_kernel import _netconsole_case

    boot, _, _, _, after, receipt = _netconsole_case(tmp_path)
    receipt["local_continuity"]["journal_capture"]["stdout"] = (
        '{"_BOOT_ID":"boot-a","__REALTIME_TIMESTAMP":"1791021600000000","MESSAGE":"only during"}\n')
    assert _asserted_status(_receiver(receipt, boot, after)) == "fail"
    _, _, _, _, after, receipt = _netconsole_case(tmp_path)
    receipt["local_continuity"]["telemetry_capture"]["stdout"] = "{broken}\n"
    assert _asserted_status(_receiver(receipt, boot, after)) == "unknown"


def test_netconsole_boot_correlation_and_configured_retention_are_required(tmp_path):
    from test_closure_kernel import _netconsole_case

    boot, _, _, _, after, receipt = _netconsole_case(tmp_path)
    receipt["correlation_boot_id"] = "another-boot"
    assert _asserted_status(_receiver(receipt, boot, after)) == "fail"
    _, _, _, _, after, receipt = _netconsole_case(tmp_path)
    receipt["retention_capture"]["stdout"] = "destination=other\nmax_age_hours=72\nmax_bytes=1024\n"
    assert _asserted_status(_receiver(receipt, boot, after)) == "unknown"


def test_netconsole_persistence_and_target_binding_must_match_during_capture(tmp_path):
    from test_closure_kernel import _netconsole_case

    boot, _, _, _, after, receipt = _netconsole_case(tmp_path)
    receipt["persistence_captures"][1]["stdout"] = ""
    assert _asserted_status(_receiver(receipt, boot, after)) == "fail"
    _, _, _, _, after, receipt = _netconsole_case(tmp_path)
    receipt["configured_target_sha256"] = "0" * 64
    assert _asserted_status(_receiver(receipt, boot, after)) == "unknown"


def test_netconsole_persistent_config_requires_exact_parameter_and_restored_mode(tmp_path):
    import hashlib
    from test_closure_kernel import _netconsole_case

    boot, _, _, _, after, receipt = _netconsole_case(tmp_path)
    row = receipt["persistence_captures"][1]
    row["stdout"] = "options netconsole nonsense=1\n"
    row["sha256"] = hashlib.sha256(row["stdout"].encode()).hexdigest()
    assert _asserted_status(_receiver(receipt, boot, after)) == "fail"

    _, _, _, _, after, receipt = _netconsole_case(tmp_path)
    receipt["persistence_captures"][0]["mode"] = 0o600
    assert _asserted_status(_receiver(receipt, boot, after)) == "fail"
    _, _, _, _, after, receipt = _netconsole_case(tmp_path)
    receipt["persistence_captures"][1]["returncode"] = 2
    receipt["persistence_captures"][1]["sha256"] = ""
    assert _asserted_status(_receiver(receipt, boot, after)) == "fail"
    _, _, _, _, after, receipt = _netconsole_case(tmp_path)
    receipt["persistence_captures"][1]["symlink"] = True
    assert _asserted_status(_receiver(receipt, boot, after)) == "fail"


def test_netconsole_conflicting_persistent_options_reject_after_valid_baseline(tmp_path):
    import hashlib
    from test_closure_kernel import _netconsole_case

    boot, _, _, _, after, receipt = _netconsole_case(tmp_path)
    assert _asserted_status(_receiver(receipt, boot, after)) == "pass"
    row = receipt["persistence_captures"][1]
    row["stdout"] += "options netconsole netconsole=6665@dev0,6666@192.0.2.2/aa:bb:cc:dd:ee:ff\n"
    row["sha256"] = hashlib.sha256(row["stdout"].encode()).hexdigest()
    result = _receiver(receipt, boot, after)
    assert isinstance(result, dict), "receiver did not return a verdict"
    assert _asserted_status(result) == "fail"
    assert result["could_not_run_count"] == 0


def test_netconsole_unconfigured_extra_target_cannot_supply_destination_binding(tmp_path):
    from test_closure_kernel import _netconsole_case

    boot, _, _, _, after, receipt = _netconsole_case(tmp_path)
    assert _asserted_status(_receiver(receipt, boot, after)) == "pass"
    during = receipt["rollback_capture"]["during"]
    during["targets"].append({"status": "unconfigured", "name": "unused"})
    assert _asserted_status(_receiver(receipt, boot, after)) == "pass"
    receipt["configured_target_sha256"] = "unused"
    result = _receiver(receipt, boot, after)
    assert isinstance(result, dict), "receiver did not return a verdict"
    assert result["status"] == "unknown"
    assert result["could_not_run_count"] == 1


def test_netconsole_rollback_and_controlled_marker_identity_edges(tmp_path):
    from test_closure_kernel import _netconsole_case

    boot, _, _, _, after, receipt = _netconsole_case(tmp_path)
    receipt["broken_route_control"]["marker"] = receipt["marker"]
    assert _asserted_status(_receiver(receipt, boot, after)) == "fail"
    _, _, _, _, after, receipt = _netconsole_case(tmp_path)
    receipt["rollback_capture"]["before"]["module"]["status"] = "loaded"
    assert _asserted_status(_rollback_states(receipt, after)) == "fail"
    _, _, _, _, after, receipt = _netconsole_case(tmp_path)
    receipt["rollback_capture"]["during"]["targets"] = []
    assert _asserted_status(_rollback_states(receipt, after)) == "fail"


def test_netconsole_secureboot_and_raw_module_capture_edges(tmp_path):
    from test_closure_kernel import _netconsole_case

    boot, _, _, _, after, receipt = _netconsole_case(tmp_path)
    receipt["secure_boot_output"] = "secureboot state unavailable"
    assert _asserted_status(_receiver_controls(receipt, boot, after)) == "fail"
    _, _, _, _, after, receipt = _netconsole_case(tmp_path)
    receipt["module_signer_output"] = "  "
    assert _asserted_status(_receiver_controls(receipt, boot, after)) == "fail"
    _, _, _, _, after, receipt = _netconsole_case(tmp_path)
    assert _asserted_status(_receiver_controls(receipt, boot, None)) == "unknown"
    _, _, _, _, after, receipt = _netconsole_case(tmp_path)
    receipt["rollback_capture"]["during"] = None
    assert _asserted_status(_receiver_controls(receipt, boot, after)) == "unknown"


def test_netconsole_route_and_receiver_raw_diagnostics_and_timing_edges(tmp_path):
    from test_closure_kernel import _netconsole_unavailable_control

    base = _netconsole_unavailable_control(tmp_path, "route", ["ip", "route", "get", "receiver"],
                                           "", "Network is unreachable")
    for control, expected in ((None, "unknown"),
        ({**base, "started_ns": True}, "unknown"),
        ({**base, "started_ns": 400_000}, "fail"),
        ({**base, "stderr": "permission denied"}, "unknown"),
        ({**base, "returncode": 0}, "fail"),
        ({**base, "command": ["false"]}, "unknown"),
        ({**base, "before_log_path": str(tmp_path / "missing")}, "unknown"),
        ({**base, "before_log_sha256": "wrong"}, "unknown")):
        outcome = _unavailable_control(control, "route")
        assert outcome is not None and outcome["status"] == expected
    receiver = {**base, "command": ["systemctl", "is-active", "receiver"], "stdout": "inactive", "stderr": ""}
    assert _unavailable_control(receiver, "receiver") is None
    assert _asserted_status(_unavailable_control({**receiver, "stdout": "active"}, "receiver")) == "unknown"
    assert _asserted_status(_unavailable_control({**receiver, "command": ["systemctl", "is-active"]}, "receiver")) == "unknown"


def test_netconsole_local_continuity_requires_raw_monotonic_journal_and_telemetry(tmp_path):
    from test_closure_kernel import _netconsole_case

    _, _, _, _, _, receipt = _netconsole_case(tmp_path)
    controls = (receipt["broken_route_control"], receipt["unavailable_receiver_control"])
    continuity = receipt["local_continuity"]
    assert _continuity(continuity, "boot-a", controls) is None
    assert _asserted_status(_continuity({}, "boot-a", controls)) == "unknown"
    assert _asserted_status(_continuity({**continuity, "telemetry_capture": {"command": [], "stdout": ""}}, "boot-a", controls)) == "unknown"
    malformed = {**continuity, "journal_capture": {**continuity["journal_capture"], "stdout": "{"}}
    assert _asserted_status(_continuity(malformed, "boot-a", controls)) == "unknown"
    empty = {**continuity, "journal_capture": {**continuity["journal_capture"], "stdout": ""}}
    assert _asserted_status(_continuity(empty, "boot-a", controls)) == "unknown"
    untimed = {**continuity, "telemetry_capture": {**continuity["telemetry_capture"], "stdout": "{}\n"}}
    assert _asserted_status(_continuity(untimed, "boot-a", controls)) == "unknown"
    stopped = {**continuity, "telemetry_capture": {**continuity["telemetry_capture"], "returncode": 2}}
    assert _asserted_status(_continuity(stopped, "boot-a", controls)) == "unknown"
    wrong_command = {**continuity, "telemetry_capture": {**continuity["telemetry_capture"],
        "command": ["bb", "telemetry", "--recent-jsonl"]}}
    assert _asserted_status(_continuity(wrong_command, "boot-a", controls)) == "unknown"
    wrong_boot = {**continuity, "telemetry_capture": {**continuity["telemetry_capture"],
        "stdout": continuity["telemetry_capture"]["stdout"].replace("boot-a", "other-boot")}}
    assert _asserted_status(_continuity(wrong_boot, "boot-a", controls)) == "unknown"
    wrong_epoch = {**continuity, "journal_capture": {**continuity["journal_capture"],
        "stdout": continuity["journal_capture"]["stdout"].replace("1791021599000000", "100").replace("1791021602000000", "200")}}
    assert _asserted_status(_continuity(wrong_epoch, "boot-a", controls)) == "fail"
    oversize = {**continuity, "journal_capture": {**continuity["journal_capture"], "stdout": "x" * (1024 * 1024 + 1)}}
    assert _asserted_status(_continuity(oversize, "boot-a", controls)) == "unknown"
    naive = {**continuity, "telemetry_capture": {**continuity["telemetry_capture"],
        "stdout": continuity["telemetry_capture"]["stdout"].replace("Z", "")}}
    assert _asserted_status(_continuity(naive, "boot-a", controls)) == "unknown"
    malformed_time = {**continuity, "telemetry_capture": {**continuity["telemetry_capture"],
        "stdout": continuity["telemetry_capture"]["stdout"].replace("2026-10-03T09:59:59Z", "bad-time")}}
    assert _asserted_status(_continuity(malformed_time, "boot-a", controls)) == "unknown"
    missing_control_time = dict(controls[0]); missing_control_time.pop("started_at")
    assert _asserted_status(_continuity(continuity, "boot-a", (missing_control_time, controls[1]))) == "unknown"
    invalid_control_time = {**controls[0], "ended_at": "2026-10-03T09:59:00Z"}
    assert _asserted_status(_continuity(continuity, "boot-a", (invalid_control_time, controls[1]))) == "unknown"


def test_netconsole_timestamp_boot_and_retention_edge_decisions(tmp_path):
    from test_closure_kernel import _netconsole_case

    boot, _, _, _, _, receipt = _netconsole_case(tmp_path)
    assert _asserted_status(_correlation_and_retention(receipt, boot)) == "pass"
    assert _asserted_status(_correlation_and_retention(receipt, "other")) == "fail"
    receipt.pop("correlation_boot_id")
    assert _asserted_status(_correlation_and_retention(receipt, boot)) == "unknown"
    _, _, _, _, _, receipt = _netconsole_case(tmp_path)
    receipt.pop("capture_timestamps")
    assert _asserted_status(_correlation_and_retention(receipt, boot)) == "unknown"
    _, _, _, _, _, receipt = _netconsole_case(tmp_path)
    receipt["capture_timestamps"].pop("target_end")
    assert _asserted_status(_correlation_and_retention(receipt, boot)) == "unknown"
    _, _, _, _, _, receipt = _netconsole_case(tmp_path)
    receipt["capture_timestamps"]["marker"] = "2026-10-03T10:00:00"
    assert _asserted_status(_correlation_and_retention(receipt, boot)) == "unknown"
    _, _, _, _, _, receipt = _netconsole_case(tmp_path)
    receipt["capture_timestamps"]["marker"] = "2026-10-03T10:01:00Z"
    assert _asserted_status(_correlation_and_retention(receipt, boot)) == "fail"
    _, _, _, _, _, receipt = _netconsole_case(tmp_path)
    receipt.pop("retention_capture")
    assert _asserted_status(_correlation_and_retention(receipt, boot)) == "unknown"


def test_netconsole_remaining_rollback_route_log_and_continuity_edges(tmp_path):
    from test_closure_kernel import _netconsole_case, _netconsole_unavailable_control

    boot, _, _, _, after, receipt = _netconsole_case(tmp_path)
    receipt["rollback_capture"]["before"]["module"]["status"] = "loaded"
    current_after = json.loads(json.dumps(receipt["rollback_capture"]["after"]))
    assert _asserted_status(_rollback_states(receipt, current_after)) == "fail"
    _, _, _, _, after, receipt = _netconsole_case(tmp_path)
    during = receipt["rollback_capture"]["during"]
    during["static_parameter"] = {"status": "read", "configured": True, "configuration_sha256": "c" * 64}
    during["targets"] = []
    receipt["configured_target_sha256"] = "c" * 64
    assert _rollback_states(receipt, after) is None
    _, _, _, _, after, receipt = _netconsole_case(tmp_path)
    receipt["rollback_capture"]["during"]["module"]["status"] = "absent"
    assert _asserted_status(_rollback_states(receipt, after)) == "fail"

    route = _netconsole_unavailable_control(tmp_path, "route", ["ip", "route", "get", "receiver"], "", "Network is unreachable")
    assert _asserted_status(_unavailable_control({**route, "command": []}, "route")) == "unknown"
    assert _asserted_status(_unavailable_control({**route, "stdout": "", "stderr": ""}, "route")) == "unknown"
    assert _asserted_status(_unavailable_control({**route, "marker": "", "before_log_path": None}, "route")) == "unknown"
    route["marker"] = "present-marker"
    with open(route["after_log_path"], "a", encoding="utf-8") as stream:
        stream.write("present-marker\n")
    from tools.netconsole_marker import verify
    route["after_log_sha256"] = verify(Path(route["after_log_path"]), "present-marker")["capture_sha256"]
    assert _asserted_status(_unavailable_control(route, "route")) == "fail"

    _, _, _, _, _, receipt = _netconsole_case(tmp_path)
    assert _asserted_status(_continuity(None, "boot-a", (receipt["broken_route_control"], receipt["unavailable_receiver_control"]))) == "unknown"
    continuity = receipt["local_continuity"]
    continuity["journal_capture"]["stdout"] = (
        '{"_BOOT_ID":"boot-a","__REALTIME_TIMESTAMP":"1791021602000000","MESSAGE":"late"}\n'
        '{"_BOOT_ID":"boot-a","__REALTIME_TIMESTAMP":"1791021599000000","MESSAGE":"early"}\n')
    assert _asserted_status(_continuity(continuity, "boot-a", (receipt["broken_route_control"], receipt["unavailable_receiver_control"]))) == "fail"


def test_netconsole_persistent_files_are_compared_before_during_and_after(tmp_path):
    from test_closure_kernel import _netconsole_case
    from tools.verify_netconsole import _persistent_configuration

    _, _, _, _, _, receipt = _netconsole_case(tmp_path)
    assert _persistent_configuration(receipt) is None
    captures = receipt["persistence_captures"]
    changed = json.loads(json.dumps(captures))
    changed[-1]["returncode"] = 0
    changed[-1]["stdout"] = "netconsole\n"
    assert _asserted_status(_persistent_configuration({"persistence_captures": changed})) == "fail"
    changed = json.loads(json.dumps(captures)); changed[1]["stdout"] = ""
    assert _asserted_status(_persistent_configuration({"persistence_captures": changed})) == "fail"
    changed = json.loads(json.dumps(captures)); changed.pop()
    assert _asserted_status(_persistent_configuration({"persistence_captures": changed})) == "unknown"
    changed = json.loads(json.dumps(captures)); changed[0]["returncode"] = True
    assert _asserted_status(_persistent_configuration({"persistence_captures": changed})) == "unknown"
    changed = json.loads(json.dumps(captures)); changed[0]["returncode"] = 2
    changed[2]["returncode"] = 2
    assert _asserted_status(_persistent_configuration({"persistence_captures": changed})) == "unknown"
    changed = json.loads(json.dumps(captures)); changed[0]["stderr"] = "permission denied"
    changed[2]["stderr"] = "permission denied"
    assert _asserted_status(_persistent_configuration({"persistence_captures": changed})) == "unknown"
    changed = json.loads(json.dumps(captures)); changed[1]["returncode"] = 1
    assert _asserted_status(_persistent_configuration({"persistence_captures": changed})) == "fail"
    changed = json.loads(json.dumps(captures)); changed[1]["stdout"] = "other option\n"
    assert _asserted_status(_persistent_configuration({"persistence_captures": changed})) == "fail"
    changed = json.loads(json.dumps(captures)); changed[0]["stderr"] = None
    assert _asserted_status(_persistent_configuration({"persistence_captures": changed})) == "unknown"
    changed = json.loads(json.dumps(captures)); changed[0]["phase"] = "unknown"
    assert _asserted_status(_persistent_configuration({"persistence_captures": changed})) == "unknown"
