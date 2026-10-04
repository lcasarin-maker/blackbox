"""The hardware router preserves the signed-source evaluator's exact gate counts."""
from pathlib import Path

import pytest

from tools import hardware_evidence
from tools import verify_forum_finding


def test_missing_apt_capture_delegates_to_twelve_gate_evaluator(tmp_path: Path) -> None:
    result = hardware_evidence.verify("DELTA-FORUM-APT-ARM64-SOURCE-VALIDATION-01", tmp_path)

    assert result["status"] == "unknown", result
    assert result["could_not_run"] == 12, result
    assert result["fail"] == 0, result
    assert result["files"] == [str(tmp_path / "commands.json")]
    assert result["criteria_unimplemented"]


def test_apt_router_passes_commands_path_to_domain_evaluator(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    observed: list[Path] = []

    def evaluate(path: Path, decision_sha256: str | None = None) -> dict[str, object]:
        observed.append(path)
        assert decision_sha256 is None
        return {"id": "DELTA-FORUM-APT-ARM64-SOURCE-VALIDATION-01", "status": "unknown",
                "could_not_run": 12, "fail": 0, "gates": []}

    from tools import verify_apt_sources_closure
    monkeypatch.setattr(verify_apt_sources_closure, "verify", evaluate)

    result = hardware_evidence.verify("DELTA-FORUM-APT-ARM64-SOURCE-VALIDATION-01", tmp_path)

    assert observed == [tmp_path / "commands.json"]
    assert result["status"] == "unknown" and result["could_not_run"] == 12


def test_forum_cli_adapter_forwards_only_external_environment_anchor(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    observed: list[str | None] = []

    def evaluate(_finding_id: str, _evidence: str | Path | None = None, *,
                 decision_sha256: str | None = None) -> dict[str, object]:
        observed.append(decision_sha256)
        return {"status": "unknown", "could_not_run": 12, "fail": 0, "files": []}

    monkeypatch.setattr(verify_forum_finding, "verify", evaluate)
    anchor = "a" * 64
    monkeypatch.setenv("BB_APT_APPROVED_DECISION_SHA256", anchor)

    result = verify_forum_finding.verify_forum_finding(
        "DELTA-FORUM-APT-ARM64-SOURCE-VALIDATION-01", tmp_path
    )

    assert observed == [anchor]
    assert result["status"] == "unknown" and result["could_not_run"] == 12
