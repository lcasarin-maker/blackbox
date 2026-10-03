from __future__ import annotations

import json
import io
from pathlib import Path
import subprocess
import sys
import time

from tools.workload_restart_policy import decide
from tools import workload_restart_policy


def test_restart_budget_persists_per_workload_and_expires(tmp_path: Path) -> None:
    state = tmp_path / "restart-budget.json"
    for attempt in range(3):
        result = decide(state, "owned-container-17", now=100 + attempt, limit=3, window_seconds=60)
        assert result["status"] == "allow" and result["data_touched"] is False
    fourth = decide(state, "owned-container-17", now=103, limit=3, window_seconds=60)
    assert fourth["status"] == "blocked" and fourth["allow"] is False
    assert decide(state, "healthy-service", now=103, limit=3, window_seconds=60)["status"] == "allow"
    assert decide(state, "owned-container-17", now=200, limit=3, window_seconds=60)["status"] == "allow"
    persisted = json.loads(state.read_text(encoding="utf-8"))
    assert "owned-container-17" in persisted["workloads"]


def test_restart_budget_refuses_malformed_state_and_identity(tmp_path: Path) -> None:
    state = tmp_path / "state.json"
    state.write_text("{broken", encoding="utf-8")
    assert decide(state, "owned", now=10)["status"] == "could_not_run"
    assert decide(state, "*", now=10)["status"] == "fail"


def test_clock_rollback_preserves_attempt_history(tmp_path: Path) -> None:
    state = tmp_path / "state.json"
    assert decide(state, "owned", now=100)["status"] == "allow"
    original = state.read_bytes()
    result = decide(state, "owned", now=90)
    assert result["status"] == "could_not_run"
    assert "clock moved behind" in result["reason"]
    assert state.read_bytes() == original
    invalid = decide(state, "owned", now=True)
    assert invalid["status"] == "fail" and invalid["fail"] == 1 and invalid["could_not_run"] == 0


def test_state_write_error_is_could_not_run_and_cleans_temporary_file(
        tmp_path: Path, monkeypatch) -> None:
    state = tmp_path / "state.json"
    def unavailable(_fd: int) -> None:
        raise OSError("sync failed")

    monkeypatch.setattr(workload_restart_policy.os, "fsync", unavailable)
    result = decide(state, "owned", now=10)
    assert result["status"] == "could_not_run"
    assert "sync failed" in result["reason"]
    assert result["could_not_run"] == 1 and result["unknowns"] == [result["reason"]]
    assert not state.exists()
    assert list(tmp_path.glob(".state.json.*")) == []


def test_restart_policy_cli_persists_and_blocks_only_named_workload(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[1]
    state = tmp_path / "budget.json"
    command = [sys.executable, "-m", "tools.workload_restart_policy", "--state", str(state),
               "--workload-id", "owned-model", "--limit", "2", "--window-seconds", "3600"]
    for _ in range(2):
        allowed = subprocess.run(command, cwd=root, capture_output=True, text=True, check=False)
        assert allowed.returncode == 0 and json.loads(allowed.stdout)["state_persisted"] is True
    blocked = subprocess.run(command, cwd=root, capture_output=True, text=True, check=False)
    assert blocked.returncode == 1 and json.loads(blocked.stdout)["status"] == "blocked"
    healthy_command = command.copy()
    healthy_command[healthy_command.index("owned-model")] = "healthy-api"
    healthy = subprocess.run(healthy_command,
                             cwd=root, capture_output=True, text=True, check=False)
    assert healthy.returncode == 0 and json.loads(healthy.stdout)["attempts"] == 1


def test_restart_policy_cli_serializes_concurrent_budget_claims(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[1]
    state = tmp_path / "budget.json"
    command = [sys.executable, "-m", "tools.workload_restart_policy", "--state", str(state),
               "--workload-id", "one-owned-workload", "--limit", "3", "--window-seconds", "600"]
    processes = [subprocess.Popen(command, cwd=root, stdout=subprocess.PIPE,
                                  stderr=subprocess.PIPE, text=True) for _ in range(10)]
    results = [process.communicate(timeout=10) + (process.returncode,) for process in processes]
    assert sum(code == 0 for _stdout, _stderr, code in results) == 3
    assert sum(code == 1 for _stdout, _stderr, code in results) == 7
    assert len(json.loads(state.read_text(encoding="utf-8"))["workloads"]["one-owned-workload"]) == 3


def test_restart_policy_main_emits_allowed_and_denied_verdicts(tmp_path: Path,
                                                               monkeypatch) -> None:
    output = io.StringIO()
    monkeypatch.setattr(sys, "stdout", output)
    state = tmp_path / "state.json"
    args = ["--state", str(state), "--workload-id", "owned", "--limit", "1"]
    assert workload_restart_policy.main(args) == 0
    assert json.loads(output.getvalue())["allow"] is True
    output.seek(0)
    output.truncate(0)
    assert workload_restart_policy.main(args) == 1
    assert json.loads(output.getvalue())["status"] == "blocked"
