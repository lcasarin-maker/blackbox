"""Read-only summary of saved OpenAI Chat Completions SSE captures."""

from __future__ import annotations

import argparse
import hashlib
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


def _collect_json_responses(chunks: list[dict[str, Any]]) -> tuple[dict[int, dict[str, Any]], list[str]]:
    responses: dict[int, dict[str, Any]] = {}
    malformed: list[str] = []
    for chunk in chunks:
        for choice in chunk.get("choices", []):
            index = choice.get("index")
            if not isinstance(index, int) or isinstance(index, bool) or index < 0:
                malformed.append("choice index is missing or invalid")
                continue
            response = responses.setdefault(index, {
                "parts": [], "finish_reasons": [], "issues": [],
                "tool_calls_observed": False, "refusal_observed": False})
            # _chunk admits only choices with a dictionary delta.
            delta = choice["delta"]
            if response["finish_reasons"]:
                response["issues"].append("choice data follows terminal finish_reason")
            if "content" in delta:
                content = delta["content"]
                if isinstance(content, str):
                    response["parts"].append(content)
                elif content is not None:
                    response["issues"].append("content delta is not plain text")
            response["tool_calls_observed"] |= bool(delta.get("tool_calls"))
            response["refusal_observed"] |= bool(delta.get("refusal"))
            finish_reason = choice.get("finish_reason")
            if finish_reason is not None:
                response["finish_reasons"].append(finish_reason)
    return responses, malformed


def _json_assessment_state(response: dict[str, Any], encoded: bytes | None, text: str,
                           done_marker_seen: bool, issues: list[str]) -> tuple[str, str, str | None]:
    finish_reasons = response["finish_reasons"]
    finish = finish_reasons[0] if len(finish_reasons) == 1 else None
    if response["issues"]:
        return "could_not_run", "could_not_run", "; ".join(response["issues"])
    if encoded is None:
        return "could_not_run", "could_not_run", "response contains a lone Unicode surrogate"
    if issues or not done_marker_seen:
        return "incomplete", "not_assessed", "SSE capture has protocol issues or lacks [DONE]"
    if finish == "content_filter":
        return "content_filtered", "not_assessed", None
    if response["refusal_observed"]:
        return "refusal", "not_assessed", None
    if finish == "tool_calls" or response["tool_calls_observed"]:
        return "tool_calls", "not_assessed", None
    if finish == "length":
        return "incomplete", "not_assessed", None
    if finish != "stop":
        return "incomplete", "could_not_run", "choice lacks one supported terminal finish_reason"
    if not text:
        return "could_not_run", "could_not_run", "choice has no plain-text content"
    return "complete", "pending", None


def _assess_json_syntax(text: str, assessment: dict[str, Any]) -> None:
    try:
        json.loads(text, parse_constant=_reject_json_constant)
    except RecursionError:
        assessment["completion_status"] = "could_not_run"
        assessment["json_syntax_status"] = "could_not_run"
        assessment["reason"] = "JSON nesting exceeded the parser recursion limit"
    except (json.JSONDecodeError, ValueError) as exc:
        assessment["json_syntax_status"] = "invalid_json"
        assessment["json_error"] = type(exc).__name__
        if isinstance(exc, json.JSONDecodeError):
            assessment["json_error_line"] = exc.lineno
            assessment["json_error_column"] = exc.colno
    else:
        assessment["json_syntax_status"] = "valid_json"


def _json_text_assessments(chunks: list[dict[str, Any]], done_marker_seen: bool,
                           issues: list[str]) -> list[dict[str, Any]]:
    responses, malformed = _collect_json_responses(chunks)
    result = []
    for index, response in sorted(responses.items()):
        text = "".join(response["parts"])
        try:
            encoded = text.encode("utf-8")
        except UnicodeEncodeError:
            encoded = None
        finish_reasons = response["finish_reasons"]
        completion, syntax, reason = _json_assessment_state(
            response, encoded, text, done_marker_seen, issues)
        assessment: dict[str, Any] = {
            "choice_index": index,
            "finish_reason": finish_reasons[0] if len(finish_reasons) == 1 else None,
            "tool_calls_observed": response["tool_calls_observed"],
            "refusal_observed": response["refusal_observed"],
            "character_count": len(text),
            "sha256": hashlib.sha256(encoded).hexdigest() if encoded is not None else None,
            "completion_status": completion,
            "json_syntax_status": syntax,
            "provenance": "caller-supplied SSE capture; response text omitted from this assessment",
            "scope": "JSON syntax only; no schema, semantic, or model-safety claim",
        }
        if reason:
            assessment["reason"] = reason
        if syntax == "pending":
            assessment["json_syntax_status"] = "pending"
            _assess_json_syntax(text, assessment)
        result.append(assessment)
    if malformed:
        result.append({"completion_status": "could_not_run",
                       "json_syntax_status": "could_not_run",
                       "reason": "; ".join(malformed),
                       "scope": "JSON syntax only; no schema, semantic, or model-safety claim"})
    if not responses and not malformed:
        result.append({"completion_status": "could_not_run",
                       "json_syntax_status": "could_not_run",
                       "reason": "capture contains no choice response to assess",
                       "scope": "JSON syntax only; no schema, semantic, or model-safety claim"})
    return result


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
    result = {
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
    result["json_text_assessments"] = _json_text_assessments(
        state.chunks, state.done_marker_seen, state.issues)
    assessments = result["json_text_assessments"]
    result["json_assessment_counts"] = {
        "valid_json": sum(a.get("json_syntax_status") == "valid_json" for a in assessments),
        "invalid_json": sum(a.get("json_syntax_status") == "invalid_json" for a in assessments),
        "incomplete": sum(a.get("completion_status") == "incomplete" for a in assessments),
        "not_assessed": sum(a.get("json_syntax_status") == "not_assessed" for a in assessments),
        "could_not_run": sum(
            a.get("completion_status") == "could_not_run"
            or a.get("json_syntax_status") == "could_not_run" for a in assessments),
    }
    return result


def _json_summary_exit_code(counts: dict[str, int]) -> int:
    if counts.get("incomplete", 0) or counts.get("not_assessed", 0) or counts.get("could_not_run", 0):
        return 2
    if counts.get("invalid_json", 0):
        return 1
    return 0 if counts.get("valid_json", 0) else 2


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
    parser.add_argument("--json-summary-only", action="store_true",
                        help="print completion and JSON-syntax metadata without response chunks")
    args = parser.parse_args(argv)
    result = analyze_file(args.capture)
    exit_code = 0 if result["status"] == "observed" else 2
    if args.json_summary_only:
        counts = result.get("json_assessment_counts", {
            "valid_json": 0, "invalid_json": 0, "incomplete": 0,
            "not_assessed": 0, "could_not_run": 1})
        exit_code = _json_summary_exit_code(counts)
        result = {
            "status": result["status"],
            "capture_path": result["capture_path"],
            "capture_path_provenance": result["capture_path_provenance"],
            "issues": result.get("issues", []),
            "could_not_run_count": result.get("could_not_run_count", 1),
            "json_assessment_counts": counts,
            "json_text_assessments": result.get("json_text_assessments", []),
        }
    print(json.dumps(result, sort_keys=True))
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
