"""Fail when requested telemetry events lack an accepted ledger disposition."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

SATISFIED_STATES = {"confirmed_defect", "false_positive", "controlled_canary"}
# Deliberately limited to dispositions that settle an event; review this policy
# if the native ledger adds another terminal disposition.


def check_dispositions(ledger: Path, event_ids: list[str]) -> tuple[int, str]:
    """Check latest ledger rows; corrupt/unreadable ledgers remain COULD_NOT_RUN."""
    latest: dict[str, dict[str, object]] = {}
    try:
        for line in ledger.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            if not isinstance(row, dict):
                return 2, "COULD_NOT_RUN: ledger row is not a JSON object"
            event_id = row.get("event_id")
            if event_id in event_ids:
                latest[event_id] = row
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        return 2, f"COULD_NOT_RUN: cannot read disposition ledger ({exc})"
    unresolved = []
    for event_id in sorted(set(event_ids)):
        row = latest.get(event_id)
        if row is not None and row.get("state") == "could_not_dispose":
            return 2, f"COULD_NOT_RUN: {event_id} is marked could_not_dispose"
        evidence = row.get("evidence") if row is not None else None
        state = row.get("state") if row is not None else None
        if (row is None or not isinstance(state, str) or state not in SATISFIED_STATES
                or not isinstance(evidence, str) or not evidence.strip()):
            unresolved.append(event_id)
    if unresolved:
        return 1, "MISSING: " + ", ".join(unresolved)
    return 0, f"OK: {len(set(event_ids))} events have valid dispositions."


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ledger", type=Path,
                        default=Path(".simplecode/evidence/telemetry_dispositions.jsonl"))
    parser.add_argument("--event-id", action="append", required=True)
    args = parser.parse_args(argv)
    result, detail = check_dispositions(args.ledger, args.event_id)
    print("[telemetry-dispositions] " + detail)
    return result


if __name__ == "__main__":
    raise SystemExit(main())
