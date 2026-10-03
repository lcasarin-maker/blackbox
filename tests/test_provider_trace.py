"""Request-scoped provider trace controls, including a worker respawn."""

import json
from pathlib import Path
import runpy

import pytest

from tools import provider_trace


FIXTURES = Path(__file__).parent / "fixtures" / "provider_trace"


def test_trace_controls() -> None:
    passed = {"status": "pass", "findings": [], "unknowns": [], "could_not_run_count": 0}
    assert provider_trace.analyze_file(FIXTURES / "gpu-healthy.jsonl") == passed
    assert provider_trace.analyze_file(FIXTURES / "cpu-only.jsonl") == passed
    respawn = provider_trace.analyze_file(FIXTURES / "gpu-to-cpu-respawn.jsonl")
    assert respawn["status"] == "block"
    assert "request gpu-after-restart: GPU request was served by CPU on worker worker-after" in respawn["findings"]


def test_request_scope_prevents_aggregate_mixing() -> None:
    lines = [
        '{"event":"request","request_id":"gpu","requested_provider":"gpu"}',
        '{"event":"worker","request_id":"gpu","worker_id":"w1","pid":1}',
        '{"event":"provider","request_id":"gpu","worker_id":"w1","provider":"CUDAExecutionProvider"}',
        '{"event":"latency","request_id":"gpu","worker_id":"w1","milliseconds":1}',
        '{"event":"request","request_id":"cpu","requested_provider":"cpu"}',
        '{"event":"worker","request_id":"cpu","worker_id":"w2","pid":2}',
        '{"event":"provider","request_id":"cpu","worker_id":"w2","provider":"CPUExecutionProvider"}',
        '{"event":"latency","request_id":"cpu","worker_id":"w2","milliseconds":2}',
    ]
    assert provider_trace.analyze_lines(lines)["status"] == "pass"


def test_missing_truncated_unknown_and_bad_records_are_unknown() -> None:
    assert provider_trace.analyze_lines([])["status"] == "unknown"
    assert provider_trace.analyze_lines(['{"event":"request","request_id":"r","requested_provider":"gpu"}'])["status"] == "unknown"
    assert provider_trace.analyze_lines(['{"event":"request","request_id":"r","requested_provider":"vendor-x"}'])["status"] == "unknown"
    assert provider_trace.analyze_lines(['{"event":"request","request_id":"r","requested_provider":"gpu"}', '{"event":'])["status"] == "unknown"
    assert provider_trace.analyze_lines(["[]"])["status"] == "unknown"
    assert provider_trace.analyze_lines(['{"event":"surprise","request_id":"r"}'])["status"] == "unknown"
    assert provider_trace.analyze_lines(['{"event":"request","request_id":"r","requested_provider":null}'])["status"] == "unknown"
    assert provider_trace.analyze_lines(['{"event":"request","request_id":"","requested_provider":"gpu"}'])["status"] == "unknown"
    assert provider_trace.analyze_lines(['{"event":"request","request_id":"r","requested_provider":"gpu"}',
                                         '{"event":"request","request_id":"r","requested_provider":"gpu"}'])["status"] == "unknown"
    assert provider_trace.analyze_lines(["", "  "])["status"] == "unknown"


def test_stale_provider_after_restart_is_unknown() -> None:
    lines = [
        '{"event":"request","request_id":"r","requested_provider":"gpu"}',
        '{"event":"worker","request_id":"r","worker_id":"w1","pid":1}',
        '{"event":"provider","request_id":"r","worker_id":"w1","provider":"cuda"}',
        '{"event":"latency","request_id":"r","worker_id":"w1","milliseconds":1}',
        '{"event":"restart","request_id":"r","old_worker_id":"w1","new_worker_id":"w2"}',
        '{"event":"worker","request_id":"r","worker_id":"w2","pid":2}',
    ]
    result = provider_trace.analyze_lines(lines)
    assert result["status"] == "unknown"
    assert any("missing or stale" in finding for finding in result["unknowns"])


def test_unknown_observed_provider_and_invalid_events_are_unknown() -> None:
    lines = [
        '{"event":"request","request_id":"r","requested_provider":"gpu"}',
        '{"event":"worker","request_id":"r","worker_id":"w","pid":1}',
        '{"event":"provider","request_id":"r","worker_id":"w","provider":"vendor-x"}',
        '{"event":"latency","request_id":"r","worker_id":"w","milliseconds":1}',
        '{"event":"restart","request_id":"r","old_worker_id":"bad","new_worker_id":"w2"}',
    ]
    assert provider_trace.analyze_lines(lines)["status"] == "unknown"
    assert provider_trace.analyze_lines(['{"event":"provider","request_id":"orphan","provider":"cpu"}'])["status"] == "unknown"
    assert provider_trace.analyze_lines(['{"event":"request","request_id":"r","requested_provider":"gpu"}',
                                         '{"event":"worker","request_id":"r","worker_id":"w","pid":1}',
                                         '{"event":"provider","request_id":"r","worker_id":"stale","provider":"cpu"}',
                                         '{"event":"latency","request_id":"r","worker_id":"stale","milliseconds":1}'])["status"] == "unknown"
    for latency in ("slow", -1, True, float("inf")):
        trace = ['{"event":"request","request_id":"r","requested_provider":"gpu"}',
                 '{"event":"worker","request_id":"r","worker_id":"w","pid":1}',
                 '{"event":"provider","request_id":"r","worker_id":"w","provider":"gpu"}',
                 json.dumps({"event": "latency", "request_id": "r", "worker_id": "w", "milliseconds": latency})]
        assert provider_trace.analyze_lines(trace)["status"] == "unknown"
    for pid, worker in ((0, "w"), (1, ""), (True, "w")):
        trace = ['{"event":"request","request_id":"r","requested_provider":"gpu"}',
                 json.dumps({"event": "worker", "request_id": "r", "worker_id": worker, "pid": pid})]
        assert provider_trace.analyze_lines(trace)["status"] == "unknown"
    changed_worker = ['{"event":"request","request_id":"r","requested_provider":"gpu"}',
                      '{"event":"worker","request_id":"r","worker_id":"w1","pid":1}',
                      '{"event":"worker","request_id":"r","worker_id":"w2","pid":2}']
    assert provider_trace.analyze_lines(changed_worker)["status"] == "unknown"
    missing_pid = ['{"event":"request","request_id":"r","requested_provider":"gpu"}',
                   '{"event":"worker","request_id":"r","worker_id":"w1","pid":1}',
                   '{"event":"restart","request_id":"r","old_worker_id":"w1","new_worker_id":"w2"}']
    assert any("replacement worker pid" in item for item in provider_trace.analyze_lines(missing_pid)["unknowns"])


def test_gpu_request_to_cpu_blocks_even_with_other_unknowns() -> None:
    lines = [
        '{"event":"request","request_id":"r","requested_provider":"gpu"}',
        '{"event":"worker","request_id":"r","worker_id":"w","pid":1}',
        '{"event":"provider","request_id":"r","worker_id":"w","provider":"cpu"}',
        '{"event":"latency","request_id":"r","worker_id":"w","milliseconds":1}',
        '{"event":"request","request_id":"incomplete","requested_provider":"gpu"}',
    ]
    result = provider_trace.analyze_lines(lines)
    assert result["status"] == "block"
    assert any("served by CPU" in finding for finding in result["findings"])
    assert any("incomplete" in finding for finding in result["unknowns"])


def test_cli_reports_status_and_read_errors(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    trace = tmp_path / "trace.jsonl"
    trace.write_text((FIXTURES / "gpu-healthy.jsonl").read_text(encoding="utf-8"), encoding="utf-8")
    assert provider_trace.main([str(trace)]) == 0
    assert json.loads(capsys.readouterr().out)["status"] == "pass"
    assert provider_trace.main([str(tmp_path / "absent.jsonl")]) == 2
    unreadable = json.loads(capsys.readouterr().out)
    assert unreadable["status"] == "unknown"
    assert unreadable["could_not_run_count"] == 1


def test_module_entrypoint(tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
                           capsys: pytest.CaptureFixture[str]) -> None:
    trace = tmp_path / "trace.jsonl"
    trace.write_text((FIXTURES / "cpu-only.jsonl").read_text(encoding="utf-8"), encoding="utf-8")
    monkeypatch.setattr("sys.argv", ["tools.provider_trace", str(trace)])
    with pytest.raises(SystemExit) as exit_info:
        runpy.run_path(str(Path(provider_trace.__file__)), run_name="__main__")
    assert exit_info.value.code == 0
    result = json.loads(capsys.readouterr().out)
    assert result["status"] == "pass"
    assert result["could_not_run_count"] == 0


def test_invalid_utf8_is_captured_as_unknown(tmp_path: Path) -> None:
    trace = tmp_path / "invalid.jsonl"
    trace.write_bytes(b"\xff")
    result = provider_trace.analyze_file(trace)
    assert result["status"] == "unknown"
    assert result["could_not_run_count"] == 1


def test_fallback_history_keeps_original_worker_attribution() -> None:
    lines = [
        '{"event":"request","request_id":"r","requested_provider":"gpu"}',
        '{"event":"worker","request_id":"r","worker_id":"w1","pid":1}',
        '{"event":"provider","request_id":"r","worker_id":"w1","provider":"CPUExecutionProvider"}',
        '{"event":"latency","request_id":"r","worker_id":"w1","milliseconds":10}',
        '{"event":"restart","request_id":"r","old_worker_id":"w1","new_worker_id":"w2"}',
        '{"event":"worker","request_id":"r","worker_id":"w2","pid":2}',
        '{"event":"provider","request_id":"r","worker_id":"w2","provider":"CUDAExecutionProvider"}',
        '{"event":"latency","request_id":"r","worker_id":"w2","milliseconds":8}',
    ]
    result = provider_trace.analyze_lines(lines)
    assert result["status"] == "block"
    assert result["findings"] == ["request r: GPU request was served by CPU on worker w1"]


def test_later_gpu_observation_does_not_erase_cpu_fallback() -> None:
    lines = [
        '{"event":"request","request_id":"r","requested_provider":"gpu"}',
        '{"event":"worker","request_id":"r","worker_id":"w","pid":1}',
        '{"event":"provider","request_id":"r","worker_id":"w","provider":"cpu"}',
        '{"event":"provider","request_id":"r","worker_id":"w","provider":"gpu"}',
        '{"event":"latency","request_id":"r","worker_id":"w","milliseconds":10}',
    ]
    assert provider_trace.analyze_lines(lines)["status"] == "block"


def test_worker_pid_change_without_restart_is_unknown() -> None:
    lines = [
        '{"event":"request","request_id":"r","requested_provider":"gpu"}',
        '{"event":"worker","request_id":"r","worker_id":"w","pid":1}',
        '{"event":"worker","request_id":"r","worker_id":"w","pid":2}',
    ]
    result = provider_trace.analyze_lines(lines)
    assert result["status"] == "unknown"
    assert any("pid changed without restart" in item for item in result["unknowns"])
