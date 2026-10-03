"""Persistent per-workload restart budget; this module never restarts a workload."""
from __future__ import annotations

import json
import fcntl
import os
from pathlib import Path
import re
import sys
import tempfile
import time
import argparse
from typing import Any

ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:@-]{0,127}$")


def decide(state_path: Path, workload_id: str, *, now: int | None = None,
           limit: int = 3, window_seconds: int = 3600) -> dict[str, Any]:
    """Allow a bounded start only for a named workload, persisting attempts across boots."""
    if (not ID_RE.fullmatch(workload_id) or type(limit) is not int or type(window_seconds) is not int
            or limit < 1 or window_seconds < 1
            or (now is not None and (type(now) is not int or now < 0))):
        return {"status": "fail", "fail": 1, "could_not_run": 0, "unknowns": [],
                "allow": False, "reason": "invalid policy input"}
    timestamp = int(time.time()) if now is None else now
    try:
        state_path.parent.mkdir(parents=True, exist_ok=True)
        lock_fd = os.open(state_path.with_name(state_path.name + ".lock"),
                          os.O_RDWR | os.O_CREAT | os.O_CLOEXEC, 0o600)
    except OSError as exc:
        reason = f"state path unavailable: {type(exc).__name__}: {exc}"
        return {"status": "could_not_run", "fail": 0, "could_not_run": 1,
                "unknowns": [reason], "allow": False, "reason": reason}
    try:
        fcntl.flock(lock_fd, fcntl.LOCK_EX)
        return _decide_locked(state_path, workload_id, timestamp, limit, window_seconds)
    except OSError as exc:
        reason = f"state lock unavailable: {type(exc).__name__}: {exc}"
        return {"status": "could_not_run", "fail": 0, "could_not_run": 1,
                "unknowns": [reason], "allow": False, "reason": reason}
    finally:
        os.close(lock_fd)


def _decide_locked(state_path: Path, workload_id: str, timestamp: int,
                   limit: int, window_seconds: int) -> dict[str, Any]:
    try:
        state = json.loads(state_path.read_text(encoding="utf-8"))
        if not isinstance(state, dict) or state.get("schema") != 1 or not isinstance(state.get("workloads"), dict):
            raise ValueError("invalid state schema")
    except FileNotFoundError:
        state = {"schema": 1, "workloads": {}}
    except (OSError, ValueError) as exc:
        reason = f"state unavailable: {type(exc).__name__}: {exc}"
        return {"status": "could_not_run", "fail": 0, "could_not_run": 1,
                "unknowns": [reason], "allow": False, "reason": reason}
    records = state["workloads"]
    raw = records.get(workload_id, [])
    if not isinstance(raw, list) or any(type(value) is not int or value < 0 for value in raw):
        reason = "workload state malformed"
        return {"status": "could_not_run", "fail": 0, "could_not_run": 1,
                "unknowns": [reason], "allow": False, "reason": reason}
    if any(value > timestamp for value in raw):
        reason = "clock moved behind persisted workload attempt"
        return {"status": "could_not_run", "fail": 0, "could_not_run": 1,
                "unknowns": [reason], "allow": False, "reason": reason}
    attempts = [value for value in raw if timestamp - value < window_seconds]
    if len(attempts) >= limit:
        return {"status": "blocked", "fail": 0, "could_not_run": 0, "unknowns": [],
                "allow": False, "workload_id": workload_id,
                "attempts": len(attempts), "limit": limit, "window_seconds": window_seconds,
                "state_persisted": True}
    attempts.append(timestamp)
    records[workload_id] = attempts
    try:
        fd, temporary = tempfile.mkstemp(prefix=f".{state_path.name}.", dir=state_path.parent)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as stream:
                json.dump(state, stream, sort_keys=True)
                stream.write("\n")
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, state_path)
            dir_fd = os.open(state_path.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
            try:
                os.fsync(dir_fd)
            finally:
                os.close(dir_fd)
        finally:
            Path(temporary).unlink(missing_ok=True)
    except OSError as exc:
        reason = f"state write unavailable: {type(exc).__name__}: {exc}"
        return {"status": "could_not_run", "fail": 0, "could_not_run": 1,
                "unknowns": [reason], "allow": False, "reason": reason}
    return {"status": "allow", "fail": 0, "could_not_run": 0, "unknowns": [],
            "allow": True, "workload_id": workload_id,
            "attempts": len(attempts), "limit": limit, "window_seconds": window_seconds,
            "state_persisted": True, "data_touched": False, "host_restart_attributed": False}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state", type=Path, required=True, help="persistent policy-state file")
    parser.add_argument("--workload-id", required=True, help="exact owned workload identity")
    parser.add_argument("--limit", type=int, default=3)
    parser.add_argument("--window-seconds", type=int, default=3600)
    args = parser.parse_args(argv)
    result = decide(args.state, args.workload_id, limit=args.limit,
                    window_seconds=args.window_seconds)
    sys.stdout.write(json.dumps(result, sort_keys=True) + "\n")
    return 0 if result["status"] == "allow" else 1 if result["status"] == "blocked" else 2


if __name__ == "__main__":
    raise SystemExit(main())
