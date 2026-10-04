"""Fail when requested telemetry events lack an accepted ledger disposition."""

from __future__ import annotations

import argparse
import math
from pathlib import Path

from tools.capture_io import read_regular_bytes, strict_json_loads

SATISFIED_STATES = {"confirmed_defect", "false_positive", "controlled_canary"}
KNOWN_STATES = SATISFIED_STATES | {"pending_grace", "could_not_dispose"}
MAX_LEDGER_BYTES = 16 * 1024 * 1024
PLACEHOLDER_EVIDENCE = {"", "n/a", "none", "pending", "placeholder", "tbd", "todo"}
# Deliberately limited to dispositions that settle an event; review this policy
# if the native ledger adds another terminal disposition.


def check_dispositions(ledger: Path, event_ids: list[str]) -> tuple[int, str]:
    """Check latest ledger rows; corrupt/unreadable ledgers remain COULD_NOT_RUN."""
    if any(not isinstance(event_id, str) or not event_id.strip() for event_id in event_ids):
        return 2, "COULD_NOT_RUN: requested event id is invalid"
    latest, error = _latest_requested_rows(ledger, set(event_ids))
    if error is not None:
        return 2, error
    latest = latest or {}
    unresolved = []
    for event_id in sorted(set(event_ids)):
        row = latest.get(event_id)
        if row is not None and row.get("state") == "could_not_dispose":
            return 2, f"COULD_NOT_RUN: {event_id} is marked could_not_dispose"
        evidence = row.get("evidence") if row is not None else None
        state = row.get("state") if row is not None else None
        if (row is None or not isinstance(state, str) or state not in SATISFIED_STATES
                or not isinstance(evidence, str)
                or evidence.strip().casefold() in PLACEHOLDER_EVIDENCE):
            unresolved.append(event_id)
    if unresolved:
        return 1, "MISSING: " + ", ".join(unresolved)
    return 0, f"OK: {len(set(event_ids))} events have valid dispositions."


def _latest_requested_rows(
        ledger: Path, requested: set[str]) -> tuple[dict[str, dict[str, object]] | None,
                                                    str | None]:
    """Read bounded strict JSONL, retaining the latest row for requested IDs."""
    latest: dict[str, dict[str, object]] = {}
    try:
        raw = read_regular_bytes(ledger, MAX_LEDGER_BYTES)
        if len(raw) > MAX_LEDGER_BYTES:
            return None, "COULD_NOT_RUN: disposition ledger exceeds byte limit"
        text = raw.decode("utf-8")
        for line in text.splitlines():
            if not line.strip():
                continue
            row = strict_json_loads(line)
            if not isinstance(row, dict):
                return None, "COULD_NOT_RUN: ledger row is not a JSON object"
            if _contains_nonfinite_float(row):
                return None, "COULD_NOT_RUN: ledger row contains a non-finite number"
            event_id = row.get("event_id")
            state = row.get("state")
            evidence = row.get("evidence")
            if (not isinstance(event_id, str) or not event_id.strip()
                    or not isinstance(state, str) or state not in KNOWN_STATES
                    or (evidence is not None and not isinstance(evidence, str))):
                return None, "COULD_NOT_RUN: malformed disposition ledger row"
            if event_id in requested:
                latest[event_id] = row
    except (OSError, UnicodeError, ValueError, RecursionError) as exc:
        return None, f"COULD_NOT_RUN: cannot read disposition ledger ({exc})"
    return latest, None


def _contains_nonfinite_float(value: object) -> bool:
    """Reject exponent overflow as well as the non-standard NaN/Infinity tokens."""
    if isinstance(value, float):
        return not math.isfinite(value)
    if isinstance(value, dict):
        return any(_contains_nonfinite_float(item) for item in value.values())
    if isinstance(value, list):
        return any(_contains_nonfinite_float(item) for item in value)
    return False


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
