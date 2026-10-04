from pathlib import Path

from tools.netconsole_marker import classify, verify


def test_marker_classification_distinguishes_literal_and_partial_match() -> None:
    marker = "BLACKBOX-NETCONSOLE-CANARY-7f3a"

    assert classify(f"kernel: {marker}\n", marker) == "present"
    assert classify("kernel: unrelated message\n", marker) == "absent"
    assert classify(f"kernel: {marker[:-4]}", marker) == "incomplete"


def test_caller_supplied_log_never_claims_delivery_or_closure(tmp_path: Path) -> None:
    marker = "BLACKBOX-NETCONSOLE-CANARY-7f3a"
    log = tmp_path / "receiver.log"
    log.write_text(f"kernel: {marker}\n", encoding="utf-8")

    result = verify(log, marker)

    assert result["status"] == "present"
    assert result["capture_path_provenance"] == "caller_supplied_unverified"
    assert result["closure"] == "open"
    assert result["could_not_run"] == 0
    assert "delivery" in result["meaning"]


def test_missing_log_is_could_not_run(tmp_path: Path) -> None:
    result = verify(tmp_path / "missing.log", "marker")

    assert result["status"] == "unknown"
    assert result["could_not_run"] == 1


def test_empty_marker_is_rejected_and_invalid_utf8_is_unknown(tmp_path: Path) -> None:
    import pytest

    with pytest.raises(ValueError, match="must not be empty"):
        classify("anything", "")
    assert verify(tmp_path / "missing", "")["could_not_run"] == 1
    log = tmp_path / "binary.log"
    log.write_bytes(b"\xff")
    assert verify(log, "marker")["status"] == "unknown"


def test_cli_reports_all_literal_states_without_claiming_closure(tmp_path: Path, capsys) -> None:
    import json
    from tools.netconsole_marker import main

    log = tmp_path / "receiver.log"
    for text, marker, expected_status, expected_exit in [
        ("MARKER\n", "MARKER", "present", 0),
        ("unrelated\n", "MARKER", "absent", 1),
        ("kernel: MAR", "MARKER", "incomplete", 2),
        ("", "", "unknown", 3),
    ]:
        log.write_text(text, encoding="utf-8")
        assert main(["--log", str(log), "--marker", marker]) == expected_exit
        row = json.loads(capsys.readouterr().out)
        assert row["status"] == expected_status
        assert row["closure"] == "open"
        assert row["could_not_run"] == int(expected_status == "unknown")


def test_bounded_capture_and_marker_limits_are_explicit(tmp_path: Path) -> None:
    from tools.netconsole_marker import MAX_LOG_BYTES, MAX_MARKER_CHARS

    log = tmp_path / "receiver.log"
    log.write_bytes(b"x" * MAX_LOG_BYTES)
    assert verify(log, "x")["status"] == "present"
    log.write_bytes(b"x" * (MAX_LOG_BYTES + 1))
    row = verify(log, "x")
    assert row["status"] == "unknown"
    assert row["could_not_run"] == 1
    assert "capture limit" in row["findings"][0]
    assert verify(log, "x" * (MAX_MARKER_CHARS + 1))["could_not_run"] == 1


def test_capture_and_marker_digests_track_exact_input(tmp_path: Path) -> None:
    import hashlib

    raw = b"kernel: marker\r\n"
    log = tmp_path / "receiver.log"
    log.write_bytes(raw)
    row = verify(log, "marker")
    assert row["capture_sha256"] == hashlib.sha256(raw).hexdigest()
    assert row["marker_sha256"] == hashlib.sha256(b"marker").hexdigest()


def test_module_entrypoint_emits_capture_receipt(tmp_path: Path, monkeypatch, capsys) -> None:
    import json
    import runpy
    import sys
    import pytest
    from tools import netconsole_marker

    log = tmp_path / "receiver.log"
    log.write_text("kernel: MARKER\n", encoding="utf-8")
    monkeypatch.setattr(sys, "argv", [netconsole_marker.__file__, "--log", str(log), "--marker", "MARKER"])
    with pytest.raises(SystemExit) as exc:
        runpy.run_path(str(netconsole_marker.__file__), run_name="__main__")
    assert exc.value.code == 0
    receipt = json.loads(capsys.readouterr().out)
    assert receipt["status"] == "present"
    assert receipt["closure"] == "open"
    assert len(receipt["capture_sha256"]) == 64
