from __future__ import annotations

import json
from pathlib import Path

from tools.workload_restart_policy import decide


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
