"""The historical close check must distinguish pending from recorded events."""

import json
import os
from pathlib import Path
import subprocess
import sys

from tools.verify_telemetry_dispositions import main


EVENTS = ["92dc63137ae930f3", "a50ae5e52c99c3ab", "5437b44ce52501ee"]


def test_requested_telemetry_events_require_valid_ledger_rows(tmp_path: Path,
                                                               capsys) -> None:
    ledger = tmp_path / "telemetry.jsonl"
    ledger.write_text("", encoding="utf-8")
    args = ["--ledger", str(ledger)]
    for event_id in EVENTS:
        args.extend(["--event-id", event_id])
    assert main(args) == 1
    output = capsys.readouterr().out
    assert all(event_id in output for event_id in EVENTS)

    with ledger.open("w", encoding="utf-8") as stream:
        stream.write("\n")
        stream.write(json.dumps({"event_id": "unrequested", "state": "confirmed_defect",
                                 "evidence": "irrelevant"}) + "\n")
        for event_id in EVENTS:
            stream.write(json.dumps({"event_id": event_id, "state": "confirmed_defect",
                                     "evidence": "recovered source output"}) + "\n")
    assert main(args) == 0
    assert "3 events have valid dispositions" in capsys.readouterr().out

    rows = [json.loads(line) for line in ledger.read_text(encoding="utf-8").splitlines()
            if line.strip()]
    row = next(item for item in rows if item["event_id"] == EVENTS[1])
    row["state"] = "pending_grace"
    with ledger.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(row) + "\n")
    assert main(args) == 1
    assert EVENTS[1] in capsys.readouterr().out

    row["state"] = "confirmed_defect"
    row["evidence"] = "recovered source output"
    with ledger.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(row) + "\n")
    assert main(args) == 0
    capsys.readouterr()

    row["evidence"] = ""
    with ledger.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(row) + "\n")
    assert main(args) == 1
    assert EVENTS[1] in capsys.readouterr().out

    row["state"] = "could_not_dispose"
    with ledger.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(row) + "\n")
    assert main(args) == 2
    assert "COULD_NOT_RUN" in capsys.readouterr().out

    ledger.write_text("{broken json\n", encoding="utf-8")
    assert main(args) == 2
    assert "COULD_NOT_RUN" in capsys.readouterr().out


def test_unreadable_or_nonobject_ledger_is_could_not_run(tmp_path: Path,
                                                         capsys) -> None:
    missing = tmp_path / "absent.jsonl"
    assert main(["--ledger", str(missing), "--event-id", EVENTS[0]]) == 2
    assert "COULD_NOT_RUN" in capsys.readouterr().out

    malformed = tmp_path / "nonobject.jsonl"
    malformed.write_text("[]\n", encoding="utf-8")
    assert main(["--ledger", str(malformed), "--event-id", EVENTS[0]]) == 2
    assert "not a JSON object" in capsys.readouterr().out


def test_duplicate_pending_then_placeholder_cannot_fabricate_disposition(
        tmp_path: Path, capsys) -> None:
    ledger = tmp_path / "duplicate.jsonl"
    event_id = EVENTS[0]
    pending = {"event_id": event_id, "state": "pending_grace", "evidence": ""}
    confirmed = {"event_id": event_id, "state": "confirmed_defect",
                 "evidence": "raw log at tmp_path/primary.log"}

    def write_rows(final_row: dict[str, str]) -> None:
        ledger.write_text(json.dumps(pending) + "\n" + json.dumps(final_row) + "\n",
                          encoding="utf-8")

    write_rows(confirmed)
    assert main(["--ledger", str(ledger), "--event-id", event_id]) == 0
    capsys.readouterr()
    write_rows({**confirmed, "evidence": "placeholder"})
    assert main(["--ledger", str(ledger), "--event-id", event_id]) == 1
    assert event_id in capsys.readouterr().out


def test_strict_json_rejects_duplicate_keys_and_nonfinite_values(
        tmp_path: Path, capsys) -> None:
    ledger = tmp_path / "malformed.jsonl"
    for line in (
        '{"event_id":"' + EVENTS[0] + '","state":"pending_grace",'
        '"state":"confirmed_defect","evidence":"real output"}',
        '{"event_id":"' + EVENTS[0] + '","state":"confirmed_defect",'
        '"evidence":"real output","metric":NaN}',
        '{"event_id":"' + EVENTS[0] + '","state":"confirmed_defect",'
        '"evidence":"real output","metric":1e999}',
    ):
        ledger.write_text(line + "\n", encoding="utf-8")
        assert main(["--ledger", str(ledger), "--event-id", EVENTS[0]]) == 2
        assert "COULD_NOT_RUN" in capsys.readouterr().out


def test_malformed_row_types_and_unknown_states_are_could_not_run(
        tmp_path: Path, capsys) -> None:
    ledger = tmp_path / "bad-shapes.jsonl"
    invalid_rows = (
        {"state": "confirmed_defect", "evidence": "raw output"},
        {"event_id": EVENTS[0], "state": "invented_terminal", "evidence": "raw output"},
        {"event_id": EVENTS[0], "state": "confirmed_defect", "evidence": []},
    )
    for row in invalid_rows:
        ledger.write_text(json.dumps(row) + "\n", encoding="utf-8")
        assert main(["--ledger", str(ledger), "--event-id", EVENTS[0]]) == 2
        assert "malformed disposition ledger row" in capsys.readouterr().out


def test_fifo_ledger_returns_could_not_run_without_blocking(tmp_path: Path) -> None:
    ledger = tmp_path / "fifo.jsonl"
    os.mkfifo(ledger)
    run = subprocess.run(
        [sys.executable, "-c",
         "from pathlib import Path; from tools.verify_telemetry_dispositions import "
         "check_dispositions; print(check_dispositions(Path(" + repr(str(ledger))
         + "), [" + repr(EVENTS[0]) + "]))"],
        capture_output=True, text=True, timeout=2, check=False,
    )
    assert run.returncode == 0
    assert "COULD_NOT_RUN" in run.stdout


def test_symlink_ancestor_ledger_is_rejected_after_regular_baseline(
        tmp_path: Path) -> None:
    actual = tmp_path / "actual"
    actual.mkdir()
    ledger = actual / "telemetry.jsonl"
    ledger.write_text(json.dumps({"event_id": EVENTS[0],
                                  "state": "confirmed_defect",
                                  "evidence": "raw output"}) + "\n",
                      encoding="utf-8")
    assert main(["--ledger", str(ledger), "--event-id", EVENTS[0]]) == 0

    alias = tmp_path / "alias"
    alias.symlink_to(actual, target_is_directory=True)
    assert main(["--ledger", str(alias / ledger.name), "--event-id", EVENTS[0]]) == 2


def test_oversized_ledger_and_invalid_event_id_are_could_not_run(
        tmp_path: Path, capsys, monkeypatch) -> None:
    ledger = tmp_path / "oversized.jsonl"
    ledger.write_text("{}", encoding="utf-8")
    monkeypatch.setattr("tools.verify_telemetry_dispositions.MAX_LEDGER_BYTES", 1)
    assert main(["--ledger", str(ledger), "--event-id", EVENTS[0]]) == 2
    assert "byte limit" in capsys.readouterr().out
    assert main(["--ledger", str(ledger), "--event-id", " "]) == 2
    assert "event id is invalid" in capsys.readouterr().out


def test_entrypoint_exits_with_reported_rc(tmp_path: Path) -> None:
    import subprocess
    import sys

    root = Path(__file__).resolve().parent.parent
    missing = tmp_path / "absent.jsonl"
    run = subprocess.run(
        [sys.executable, "-m", "tools.verify_telemetry_dispositions", "--ledger", str(missing),
         "--event-id", EVENTS[0]], cwd=root, capture_output=True, text=True, check=False,
    )
    assert run.returncode == 2, run.stdout + run.stderr
    assert "COULD_NOT_RUN" in run.stdout
