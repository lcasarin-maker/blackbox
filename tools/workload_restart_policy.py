"""Persistent per-workload restart budget; this module never restarts a workload."""
from __future__ import annotations

import json
import os
from pathlib import Path
import re
import tempfile
import time
from typing import Any

ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:@-]{0,127}$")


def decide(state_path: Path, workload_id: str, *, now: int | None = None,
           limit: int = 3, window_seconds: int = 3600) -> dict[str, Any]:
    """Allow a bounded start only for a named workload, persisting attempts across boots."""
    if not ID_RE.fullmatch(workload_id) or limit < 1 or window_seconds < 1:
        return {"status": "fail", "allow": False, "reason": "invalid policy input"}
    timestamp = int(time.time()) if now is None else now
    try:
        state = json.loads(state_path.read_text(encoding="utf-8"))
        if not isinstance(state, dict) or state.get("schema") != 1 or not isinstance(state.get("workloads"), dict):
            raise ValueError("invalid state schema")
    except FileNotFoundError:
        state = {"schema": 1, "workloads": {}}
    except (OSError, ValueError) as exc:
        return {"status": "could_not_run", "allow": False,
                "reason": f"state unavailable: {type(exc).__name__}: {exc}"}
    records = state["workloads"]
    raw = records.get(workload_id, [])
    if not isinstance(raw, list) or any(type(value) is not int for value in raw):
        return {"status": "could_not_run", "allow": False, "reason": "workload state malformed"}
    attempts = [value for value in raw if 0 <= timestamp - value < window_seconds]
    if len(attempts) >= limit:
        return {"status": "blocked", "allow": False, "workload_id": workload_id,
                "attempts": len(attempts), "limit": limit, "window_seconds": window_seconds,
                "state_persisted": True}
    attempts.append(timestamp)
    records[workload_id] = attempts
    state_path.parent.mkdir(parents=True, exist_ok=True)
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
        return {"status": "could_not_run", "allow": False,
                "reason": f"state write unavailable: {type(exc).__name__}: {exc}"}
    return {"status": "allow", "allow": True, "workload_id": workload_id,
            "attempts": len(attempts), "limit": limit, "window_seconds": window_seconds,
            "state_persisted": True, "data_touched": False, "host_restart_attributed": False}
