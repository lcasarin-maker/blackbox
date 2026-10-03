"""Read-only summary of saved OpenAI Chat Completions SSE captures."""

from __future__ import annotations

import argparse
import io
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class Capture:
    chunks: list[dict[str, Any]] = field(default_factory=list)
    issues: list[str] = field(default_factory=list)
    incomplete_frame_data: list[str] = field(default_factory=list)
    done_marker_seen: bool = False
    unreadable_observation_count: int = 0


def _reject_json_constant(value: str) -> None:
    raise ValueError(f"invalid JSON constant: {value}")


def _chunk(raw: str, event_number: int, state: Capture) -> None:
    if raw == "[DONE]":
        if state.done_marker_seen:
            state.issues.append(f"event {event_number}: duplicate [DONE] marker")
        state.done_marker_seen = True
        return
    if state.done_marker_seen:
        state.issues.append(f"event {event_number}: data after [DONE] marker")
        state.unreadable_observation_count += 1
        return
    try:
        payload = json.loads(raw, parse_constant=_reject_json_constant)
    except (json.JSONDecodeError, ValueError):
        state.issues.append(f"event {event_number}: malformed chunk JSON")
        state.unreadable_observation_count += 1
        return
    if not isinstance(payload, dict) or not isinstance(payload.get("choices"), list):
        state.issues.append(f"event {event_number}: chunk must be an object with choices")
        state.unreadable_observation_count += 1
        return
    choices = []
    invalid_choice = False
    for choice in payload["choices"]:
        if not isinstance(choice, dict) or not isinstance(choice.get("delta"), dict):
            state.issues.append(f"event {event_number}: choice must contain a delta object")
            state.unreadable_observation_count += 1
            invalid_choice = True
            continue
        delta = choice["delta"]
        choices.append({
            "index": choice.get("index"),
            "content_present": "content" in delta,
            "content_delta": delta.get("content"),
            "tool_calls_present": "tool_calls" in delta,
            "tool_calls_delta": delta.get("tool_calls"),
            "finish_reason": choice.get("finish_reason"),
            "delta": delta,
        })
    if invalid_choice and not choices:
        return
    state.chunks.append({
        "event_number": event_number,
        "completion_id": payload.get("id"),
        "object": payload.get("object"),
        "choices": choices,
        "usage": payload.get("usage"),
        "observed_chunk": payload,
    })


def _dispatch(data: list[str], event_number: int, state: Capture) -> int:
    if not data:
        return event_number
    event_number += 1
    _chunk("\n".join(data), event_number, state)
    return event_number


def parse_capture(text: str, capture_path: str) -> dict[str, Any]:
    """Preserve client-visible deltas; do not infer cancellation or engine progress."""
    state = Capture()
    data: list[str] = []
    event_number = 0
    # SSE line endings are CR, LF, or CRLF. Universal newline handling maps
    # those to LF without splitting JSON string characters such as U+2028.
    for raw_line in io.StringIO(text.removeprefix("\ufeff"), newline=None):
        line = raw_line.removesuffix("\n")
        if line == "":
            event_number = _dispatch(data, event_number, state)
            data = []
        elif line.startswith(":"):
            continue
        else:
            field_name, separator, value = line.partition(":")
            if field_name == "data":
                if separator and value.startswith(" "):
                    value = value[1:]
                data.append(value if separator else "")
    if data:
        state.incomplete_frame_data.append("\n".join(data))
        state.issues.append("capture ends before the final SSE frame delimiter")
        state.unreadable_observation_count += 1
    if not state.done_marker_seen:
        state.issues.append("capture has no [DONE] marker; termination cause unknown")
        state.unreadable_observation_count += 1
    if not state.chunks:
        state.issues.append("capture contains no chat completion chunks")
        status = "unknown"
        could_not_run_count = max(1, state.unreadable_observation_count)
    elif state.issues:
        status = "partial"
        could_not_run_count = state.unreadable_observation_count
    else:
        status = "observed"
        could_not_run_count = 0
    return {
        "status": status,
        "capture_path": capture_path,
        "capture_path_provenance": "caller_supplied_unverified",
        "protocol": "openai_chat_completions_sse",
        "chunks": state.chunks,
        "done_marker_seen": state.done_marker_seen,
        "incomplete_frame_data": state.incomplete_frame_data,
        "issues": state.issues,
        "unreadable_observation_count": state.unreadable_observation_count,
        "could_not_run_count": could_not_run_count,
    }


def analyze_file(path: Path) -> dict[str, Any]:
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        return {"status": "unknown", "capture_path": str(path),
                "capture_path_provenance": "caller_supplied_unverified",
                "protocol": "openai_chat_completions_sse", "chunks": [],
                "done_marker_seen": False, "incomplete_frame_data": [],
                "issues": [f"cannot read capture: {exc}"],
                "unreadable_observation_count": 0, "could_not_run_count": 1}
    return parse_capture(text, str(path))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("capture", type=Path, help="saved Chat Completions SSE text")
    args = parser.parse_args(argv)
    result = analyze_file(args.capture)
    print(json.dumps(result, sort_keys=True))
    return 0 if result["status"] == "observed" else 2


if __name__ == "__main__":
    sys.exit(main())
