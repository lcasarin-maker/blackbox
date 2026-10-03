"""The historical close check must distinguish pending from recorded events."""

import json
from pathlib import Path

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
