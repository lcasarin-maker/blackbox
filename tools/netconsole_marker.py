"""Classify an explicitly supplied netconsole receiver log marker.

This checks text supplied by the caller. It cannot authenticate the receiver,
prove packet delivery, or establish the kernel configuration that produced it.
"""

from __future__ import annotations

import argparse
import json
import hashlib
from pathlib import Path
import sys
from typing import Any


def classify(log_text: str, expected_marker: str) -> str:
    """Return present, incomplete, or absent for a literal marker in a log."""
    if not expected_marker:
        raise ValueError("expected marker must not be empty")
    if expected_marker in log_text:
        return "present"
    max_prefix = min(len(log_text), len(expected_marker) - 1)
    for size in range(max_prefix, 0, -1):
        if log_text.endswith(expected_marker[:size]):
            return "incomplete"
    return "absent"


MAX_LOG_BYTES = 1024 * 1024
MAX_MARKER_CHARS = 1024


def verify(log_path: Path, expected_marker: str) -> dict[str, Any]:
    """Read a caller-supplied receiver log and report only literal match state."""
    if not expected_marker or len(expected_marker) > MAX_MARKER_CHARS:
        return _unknown("expected marker must contain 1..1024 characters")
    try:
        with log_path.open("rb") as stream:
            raw = stream.read(MAX_LOG_BYTES + 1)
        if len(raw) > MAX_LOG_BYTES:
            return _unknown("receiver log exceeds 1 MiB capture limit; supply a bounded capture")
        content = raw.decode("utf-8")
    except (OSError, UnicodeError) as exc:
        return _unknown(f"receiver log unreadable: {type(exc).__name__}: {exc}")
    return {
        "status": classify(content, expected_marker),
        "capture_sha256": hashlib.sha256(raw).hexdigest(),
        "marker_sha256": hashlib.sha256(expected_marker.encode("utf-8")).hexdigest(),
        "capture_path_provenance": "caller_supplied_unverified",
        "marker_provenance": "caller_supplied_unverified",
        "meaning": "literal marker classification only; delivery, Secure Boot, persistence, and correlation are unverified",
        "closure": "open",
        "findings": [],
        "fail": 0,
        "could_not_run": 0,
    }


def _unknown(reason: str) -> dict[str, Any]:
    return {
        "status": "unknown",
        "capture_path_provenance": "caller_supplied_unverified",
        "marker_provenance": "caller_supplied_unverified",
        "meaning": "receiver evidence could not be classified",
        "closure": "open",
        "findings": [reason],
        "fail": 0,
        "could_not_run": 1,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--log", type=Path, required=True, help="caller-supplied receiver log")
    parser.add_argument("--marker", required=True, help="literal expected kernel marker")
    args = parser.parse_args(argv)
    result = verify(args.log, args.marker)
    print(json.dumps(result, sort_keys=True))
    return {"present": 0, "absent": 1, "incomplete": 2, "unknown": 3}[result["status"]]


if __name__ == "__main__":
    sys.exit(main())
