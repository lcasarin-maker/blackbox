"""Parser controls; these strings test formatting, not hardware charge behavior."""
from __future__ import annotations

import runpy
import sys
from pathlib import Path

import pytest

from tools import kernel_charge_observations as observations


def _capture(*, final: str = "", owner: str = "unknown") -> str:
    return f"""READY abi=linux-6.17-kmem-page-charge page_size=4096 scope_cgroup_id=44 attribution=executor-cgroup-only owner={owner}
SNAPSHOT t=1 owner=unknown attribution=executor-task-cgroup
@charge_events[44, worker]: 2
@uncharge_events[44, worker]: 1
@live_bytes_by_executor[44, worker]: 4096
@live_pages_by_executor[44, worker]: 1
@charge_failures: 0
@duplicate_charge: 0
@order_mismatch: 0
@page_bytes[0xabc]: 4096
@pending_page: empty
FINAL owner=unknown attribution=executor-task-cgroup
@charge_events[44, worker]: 3
@uncharge_events[44, worker]: 2
@live_bytes_by_executor[44, worker]: 4096
@live_pages_by_executor[44, worker]: 1
@charge_failures: 0
@duplicate_charge: 0
@order_mismatch: 0
@page_bytes[0xabc]: 4096
@pending_page: empty
{final}"""


def test_parse_real_format_derives_final_maps_and_owner_limit() -> None:
    result = observations.parse_stdout(_capture())
    assert result["status"] == "pass", result
    assert result["charge_events"] == 3
    assert result["uncharge_events"] == 2
    assert result["duplicate_charges"] == 0
    assert result["outstanding_bytes"] == 4096
    assert result["executor_cgroup_id"] == 44
    assert result["owner"] == "unknown"
    assert result["closure"] == "open"


def test_truncated_stdout_is_unknown_could_not_run() -> None:
    result = observations.parse_stdout(_capture().split("FINAL ")[0])
    assert result["status"] == "unknown"
    assert result["fail"] == 0 and result["could_not_run"] == 1


def test_duplicate_map_key_fails() -> None:
    raw = _capture().replace("@duplicate_charge: 0\n", "@duplicate_charge: 0\n@duplicate_charge: 1\n")
    result = observations.parse_stdout(raw)
    assert result["status"] == "fail"
    assert result["fail"] == 1 and result["could_not_run"] == 0


def test_live_aggregate_disagreement_fails() -> None:
    raw = _capture().replace("@live_bytes_by_executor[44, worker]: 4096\n@live_pages_by_executor[44, worker]: 1\n@charge_failures: 0\n@duplicate_charge: 0",
                             "@live_bytes_by_executor[44, worker]: 8192\n@live_pages_by_executor[44, worker]: 1\n@charge_failures: 0\n@duplicate_charge: 0")
    result = observations.parse_stdout(raw)
    assert result["status"] == "fail"
    assert result["fail"] == 1


def test_nonzero_probe_and_owner_claim_are_not_pass() -> None:
    assert observations.parse_stdout(_capture(), returncode=1)["status"] == "unknown"
    owner_claim = observations.parse_stdout(_capture(owner="observed"))
    assert owner_claim["status"] == "fail"


def test_probe_reported_charge_errors_fail() -> None:
    raw = _capture().replace("@charge_failures: 0\n", "@charge_failures: 1\n")
    result = observations.parse_stdout(raw)
    assert result["status"] == "fail"
    assert result["fail"] == 1 and result["could_not_run"] == 0
    assert result["charge_failures"] == 1


def test_current_evidence_has_no_probe_stdout_capture() -> None:
    evidence = Path(__file__).resolve().parent.parent / "tasks/evidence/FEATURE-MEMORYSAVER-02-TRAZADOR"
    result = observations.verify_directory(evidence)
    assert result["status"] == "unknown", result
    assert result["fail"] == 0 and result["could_not_run"] == 1
    assert result["owner"] == "unknown" and result["closure"] == "open"


def test_unavailable_command_or_stdout_is_unknown() -> None:
    assert observations.parse_stdout(_capture(), returncode=True)["status"] == "unknown"
    assert observations.parse_stdout(_capture(), stderr="permission denied")["status"] == "unknown"
    assert observations.parse_stdout("")["status"] == "unknown"


def test_unexpected_or_malformed_map_rows_fail() -> None:
    for line in ("@alien: 2", "@charge_events[44]: nope", "diagnostic text"):
        result = observations.parse_stdout(_capture().replace("FINAL owner=unknown", f"{line}\nFINAL owner=unknown"))
        assert result["status"] == "fail", (line, result)


def test_empty_and_duplicate_maps_fail() -> None:
    unknown = _capture().replace("@pending_page: empty", "@alien: empty")
    duplicate = _capture().replace("@pending_page: empty", "@charge_failures: empty")
    assert observations.parse_stdout(unknown)["status"] == "fail"
    assert observations.parse_stdout(duplicate)["status"] == "fail"


def test_negative_counter_and_nonpositive_identity_fail() -> None:
    negative = _capture().replace("@charge_failures: 0\n@duplicate_charge: 0",
                                  "@charge_failures: -1\n@duplicate_charge: 0")
    invalid_page = _capture().replace("page_size=4096", "page_size=0")
    assert observations.parse_stdout(negative)["status"] == "fail"
    assert observations.parse_stdout(invalid_page)["status"] == "fail"


def test_bad_headers_and_final_structure_are_rejected() -> None:
    missing_ready = _capture().replace(
        "READY abi=linux-6.17-kmem-page-charge page_size=4096 scope_cgroup_id=44 attribution=executor-cgroup-only owner=unknown\n", "")
    malformed_snapshot = _capture().replace("SNAPSHOT t=1", "SNAPSHOT t=x")
    repeated_snapshot = _capture().replace("FINAL owner=unknown", "SNAPSHOT t=1 owner=unknown attribution=executor-task-cgroup\nFINAL owner=unknown")
    repeated_final = _capture() + "\nFINAL owner=unknown attribution=executor-task-cgroup\n"
    after_final = _capture().replace("FINAL owner=unknown", "FINAL owner=unknown", 1) + "SNAPSHOT t=2 owner=unknown attribution=executor-task-cgroup\n"
    for raw in (missing_ready, malformed_snapshot, repeated_snapshot, repeated_final, after_final):
        assert observations.parse_stdout(raw)["status"] in {"fail", "unknown"}


def test_missing_maps_and_pending_return_are_unknown() -> None:
    missing = _capture().replace("@order_mismatch: 0\n", "")
    pending = _capture().replace("@pending_page: empty", "@pending_page[10]: 1")
    assert observations.parse_stdout(missing)["status"] == "unknown"
    assert observations.parse_stdout(pending)["status"] == "unknown"


def test_capture_directory_sidecars_and_cli(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch,
) -> None:
    (tmp_path / "kernel-charges.stdout").write_text(_capture(), encoding="utf-8")
    (tmp_path / "kernel-charges.stderr").write_text("", encoding="utf-8")
    (tmp_path / "kernel-charges.exit").write_text("0\n", encoding="ascii")
    assert observations.verify_directory(tmp_path)["status"] == "pass"
    assert observations.main(["--evidence", str(tmp_path)]) == 0
    assert '"owner": "unknown"' in capsys.readouterr().out
    script = Path(observations.__file__)
    monkeypatch.setattr(sys, "argv", [str(script), "--evidence", str(tmp_path)])
    with pytest.raises(SystemExit) as raised:
        runpy.run_path(str(script), run_name="__main__")
    assert raised.value.code == 0
    capsys.readouterr()
    (tmp_path / "kernel-charges.exit").write_text("not-an-exit\n", encoding="ascii")
    assert observations.verify_directory(tmp_path)["status"] == "unknown"
    (tmp_path / "kernel-charges.exit").write_bytes(b"\xff")
    assert observations.verify_directory(tmp_path)["status"] == "unknown"
