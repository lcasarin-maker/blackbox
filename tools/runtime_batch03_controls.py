"""Raw log and event predicates for generated runtime batch 03."""

from __future__ import annotations

import json
import hashlib
import math
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, cast

from tools.capture_io import read_regular_bytes, strict_json_loads
from tools.json_schema_subset import UnsupportedJsonSchema, schema_value_matches
from tools.runtime_batch01_controls import (
    EVIDENCE,
    _Fail,
    _Unknown,
    _capture,
    _contradiction,
    _need,
    _obj,
    _sha256,
    _request_binding,
    _rollback,
    _sse_capture,
    _sse_content,
    _sse_tool_calls,
    _text,
)
from tools.chat_sse_capture import parse_capture as _parse_sse_raw
from tools.runtime_batch02_controls import _oracle_payload

IDS = {
    "DELTA-FORUM-QWEN-LONG-AGENT-STOP-01",
    "DELTA-FORUM-QWEN-MTP-PARSER-CANCEL-STATE-CHECK-01",
    "DELTA-FORUM-QWEN-SERVICE-OOMD-CACHE-FAIL-01",
    "DELTA-FORUM-QWEN-TOOLCALL-WEDGE-01",
    "DELTA-FORUM-QWEN35-NVFP4-CUTLASS-FIRST-REQUEST-GATE-01",
    "DELTA-FORUM-QWEN38-LONG-RUN-JSON-CORRECTNESS-CANARY-01",
    "DELTA-FORUM-RAY-TORCH-GRAPH-HANG-01",
    "DELTA-FORUM-VLLM-GB10-ARCH-AND-BUILD-MATRIX-01",
    "DELTA-FORUM-VLLM-RAY-GB10-RESOURCE-FIX-01",
    "DELTA-ROOT-CONTAINER-EFFECTIVE-BUILD-AND-OFFLINE-GATE-01",
}


def _finite(value: Any) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
    )


def _timestamp(value: Any, label: str) -> datetime:
    _need(_text(value), f"{label} timestamp absent")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (TypeError, ValueError) as exc:
        raise _Unknown(f"{label} timestamp is invalid") from exc
    _need(parsed.tzinfo is not None, f"{label} timestamp must include UTC offset")
    return parsed


def _mtp_request_contract(
    request_raw: Any, req: dict[str, Any], subject_model: Any
) -> dict[str, Any]:
    _need(_text(request_raw), "captured OpenAI chat-completions request bytes absent")
    def unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"duplicate JSON key: {key}")
            result[key] = value
        return result

    def reject_constant(value: str) -> None:
        raise ValueError(f"non-finite JSON constant: {value}")

    try:
        body = json.loads(
            request_raw, object_pairs_hook=unique_object, parse_constant=reject_constant
        )
    except (json.JSONDecodeError, RecursionError, ValueError) as exc:
        raise _Fail("captured request is not valid JSON") from exc
    _contradiction(isinstance(body, dict), "captured request is not a JSON object")
    _contradiction(
        _text(subject_model) and body.get("model") == req["model"] == subject_model,
        "request model differs from bound request/subject model",
    )
    _contradiction(
        isinstance(body.get("messages"), list)
        and bool(body["messages"])
        and all(
            isinstance(message, dict)
            and message.get("role") in {"system", "developer", "user", "assistant"}
            and _text(message.get("content"))
            for message in body["messages"]
        )
        and any(message.get("role") == "user" for message in body["messages"]),
        "request lacks valid OpenAI chat-completions messages",
    )
    tools = body.get("tools")
    _contradiction(
        isinstance(tools, list) and bool(tools),
        "request lacks typed OpenAI function-tool schema",
    )
    tool_schemas: dict[str, dict[str, Any]] = {}
    for tool in tools:
        _contradiction(
            isinstance(tool, dict) and tool.get("type") == "function",
            "request tool is not an OpenAI function tool",
        )
        function = tool.get("function")
        _contradiction(
            isinstance(function, dict)
            and _text(function.get("name"))
            and isinstance(function.get("parameters"), dict),
            "request function tool lacks name/parameters schema",
        )
        function = cast(dict[str, Any], function)
        name = function["name"]
        schema = cast(dict[str, Any], function["parameters"])
        properties = schema.get("properties")
        required = schema.get("required", [])
        _contradiction(
            schema.get("type") == "object"
            and isinstance(properties, dict)
            and all(
                _text(key)
                and isinstance(value, dict)
                and value.get("type")
                in {"string", "number", "integer", "boolean", "object", "array", "null"}
                for key, value in properties.items()
            )
            and isinstance(required, list)
            and all(isinstance(key, str) and key in properties for key in required)
            and type(schema.get("additionalProperties", False)) is bool
            and schema.get("additionalProperties", False) is False,
            "request function tool has unsupported or open JSON Schema",
        )
        _contradiction(name not in tool_schemas, "request has duplicate function tool names")
        tool_schemas[name] = schema
    tool_choice = body.get("tool_choice")
    valid_choice = tool_choice in {"required", "auto"} if isinstance(tool_choice, str) else (
        isinstance(tool_choice, dict)
        and tool_choice.get("type") == "function"
        and isinstance(tool_choice.get("function"), dict)
        and tool_choice["function"].get("name") in tool_schemas
    )
    _contradiction(
        tool_choice is None or valid_choice,
        "request tool_choice is malformed",
    )
    budget_keys = [key for key in ("max_completion_tokens", "max_tokens") if key in body]
    _need(
        len(budget_keys) <= 1,
        "request contains conflicting generation-token budgets",
    )
    if not budget_keys:
        raise _Unknown(
            "request has no token budget and no captured effective server config bound to PID/build"
        )
    else:
        generation_budget = body[budget_keys[0]]
    _contradiction(
        type(generation_budget) is int
        and generation_budget > 0
        and generation_budget <= req["max_tokens"]
        and generation_budget <= req["max_context_tokens"],
        "request generation/context budget exceeds captured bounds",
    )
    return {
        "body": body,
        "tool_schemas": tool_schemas,
        "generation_budget": generation_budget,
    }


def _json_schema_value_matches(schema: dict[str, Any], value: Any) -> bool:
    try:
        return schema_value_matches(schema, value)
    except UnsupportedJsonSchema as exc:
        raise _Unknown(str(exc)) from exc


def _mtp_calls_match_request(calls: Any, contract: dict[str, Any]) -> bool:
    if not isinstance(calls, list) or not calls:
        return False
    schemas = contract["tool_schemas"]
    for call in calls:
        if not isinstance(call, dict) or not _text(call.get("name")):
            return False
        schema = schemas.get(call["name"])
        arguments = call.get("arguments")
        if schema is None or not isinstance(arguments, dict):
            return False
        properties = schema["properties"]
        if not set(schema.get("required", [])) <= arguments.keys():
            return False
        if not schema.get("additionalProperties", False) and not arguments.keys() <= properties.keys():
            return False
        if not all(
            key in properties and _json_schema_value_matches(properties[key], value)
            for key, value in arguments.items()
        ):
            return False
    return True


def _rows(value: Any, minimum: int, label: str) -> list[Any]:
    _need(isinstance(value, list) and len(value) >= minimum, f"{label} raw rows absent")
    return cast(list[Any], value)


def _versions(doc: dict[str, Any], required: tuple[str, ...]) -> None:
    versions = _obj(
        doc["subject"].get("software_versions"),
        "pinned effective stack version map absent",
    )
    _need(
        all(_text(versions.get(key)) for key in required),
        f"effective stack versions absent: {', '.join(required)}",
    )


def _long_stop(doc: dict[str, Any]) -> None:
    _request_binding(doc)
    _versions(doc, ("harness", "runtime", "sampling"))
    runs = _rows(doc.get("soak_runs"), 2, "multi-checkpoint long-agent soak")
    checkpoints = {doc["subject"]["checkpoint_digest"]}
    seen: set[str] = set()
    for run in runs:
        _need(
            isinstance(run, dict)
            and _text(run.get("checkpoint_digest"))
            and _text(run.get("task_state_raw"))
            and _text(run.get("checkpoint_variant"))
            and isinstance(run.get("turns"), list),
            "soak run lacks checkpoint/task/turn captures",
        )
        checkpoints.add(run["checkpoint_digest"])
        turns = _rows(run.get("turns"), 1, "agent turn event")
        for turn in turns:
            _need(
                isinstance(turn, dict)
                and _text(turn.get("request_id"))
                and _text(turn.get("task_state_raw"))
                and type(turn.get("tool_call_count")) is int
                and _text(turn.get("finish_reason")),
                "turn boundary record incomplete",
            )
            _need(
                turn["task_state_raw"] in {"open", "complete"},
                "turn task state is unknown",
            )
            if (
                turn["task_state_raw"] == "open"
                and turn["finish_reason"] == "stop"
                and turn["tool_call_count"] == 0
            ):
                _contradiction(
                    turn.get("operator_resume_event") == "resume"
                    and turn.get("mutating_call_replay_count") == 0,
                    "premature stop lacks manual recoverability or replay safety evidence",
                )
            if turn["task_state_raw"] == "complete":
                _contradiction(
                    turn.get("mutating_call_replay_count") == 0,
                    "completed turn repeated a mutating tool call",
                )
            seen.add(turn["request_id"])
    variants = {run["checkpoint_variant"] for run in runs}
    _need(
        {"nvidia_nvfp4", "alternative"} <= variants and len(checkpoints) >= 2 and seen,
        "same-harness NVIDIA/alternative checkpoint soak absent",
    )
    _rollback(doc)


def _validate_mtp_event(
    event: Any,
    run: dict[str, Any],
    req: dict[str, Any],
    oracle: dict[str, Any],
    request_contract: dict[str, Any],
) -> tuple[str, int, int, datetime, str | None, int | None]:
    _need(isinstance(event, dict), "parser event is malformed")
    _need(
        type(event.get("server_pid")) is int
        and event["server_pid"] > 0
        and type(event.get("process_generation")) is int
        and event["process_generation"] >= 0,
        "server process PID/generation absent or invalid",
    )
    _need(
        event.get("logical_request_id") == req["request_id"]
        and _text(event.get("request_id"))
        and event.get("model") == req["model"]
        and event.get("checkpoint_digest") == req["checkpoint_digest"]
        and event.get("input_sha256") == run.get("input_sha256"),
        "parser event is not bound to bounded request/model/checkpoint",
    )
    _need(
        type(event.get("http_status")) is int
        and event["http_status"] == 200
        and (event.get("finish_reason") is None or _text(event.get("finish_reason")))
        and type(event.get("exit_code")) is int,
        "HTTP/finish/exit result absent",
    )
    phase = event["phase"]
    if phase == "cancel":
        _need(
            event.get("finish_reason") is None,
            "cancel action was mislabeled as an inference finish",
        )
        if run["cancel_midstream"]:
            _need(
                _text(event.get("action_raw"))
                and type(event.get("cancel_exit_code")) is int,
                "midstream cancel lacks raw action and exit result",
            )
            _contradiction(
                event["cancel_exit_code"] == 0,
                "midstream cancel action failed and did not establish cancellation",
            )
        else:
            _need(
                event.get("action_raw") == "cancel_not_requested"
                and event.get("cancel_exit_code") is None,
                "no-cancel control does not prove cancellation was withheld",
            )
        return (
            phase,
            event["server_pid"],
            event["process_generation"],
            _timestamp(event.get("timestamp"), "parser event"),
            None,
            None,
        )
    _need(_text(event.get("sse_raw")), "raw parser SSE absent")
    parsed = _parse_sse_raw(event["sse_raw"], "parser-cancel")
    chunks = parsed.get("chunks")
    _need(isinstance(chunks, list) and chunks, "raw parser SSE has no observed chunks")
    chunks = cast(list[Any], chunks)
    response_ids = {
        chunk.get("completion_id") for chunk in chunks if isinstance(chunk, dict)
    }
    _need(
        len(response_ids) == 1 and _text(event.get("response_id")),
        f"{phase} raw SSE completion ID absent",
    )
    _contradiction(
        response_ids == {event["response_id"]},
        f"{phase} response ID differs from raw SSE",
    )
    partial_only = (
        parsed.get("status") == "partial"
        and parsed.get("done_marker_seen") is False
        and parsed.get("incomplete_frame_data") == []
        and parsed.get("issues")
        == ["capture has no [DONE] marker; termination cause unknown"]
    )
    _need(
        parsed.get("status") == "observed"
        and parsed.get("could_not_run_count") == 0
        or phase == "before_cancel"
        and partial_only,
        "raw parser SSE malformed beyond an expected partial response",
    )
    calls = _sse_tool_calls(parsed, "parser-cancel")
    _need(
        calls
        and all(
            _text(call.get("name")) and isinstance(call.get("arguments"), dict)
            for call in calls
        ),
        "typed tool call absent before/after cancellation",
    )
    _contradiction(
        _mtp_calls_match_request(calls, request_contract),
        "typed parser tool call violates the captured request's function schema",
    )
    oracle_key = {
        "before_cancel": "before_calls",
        "after_cancel": "after_cancel_calls",
        "after_restart": "after_restart_calls",
    }[phase]
    _contradiction(
        calls == oracle[oracle_key],
        f"typed parser tool call differs from independent {phase} oracle",
    )
    finish_reasons = [
        choice.get("finish_reason")
        for chunk in chunks
        if isinstance(chunk, dict)
        for choice in chunk.get("choices", [])
        if isinstance(choice, dict) and choice.get("finish_reason") is not None
    ]
    done = parsed.get("done_marker_seen") is True
    prompt_tokens: int | None = None
    if phase == "before_cancel":
        _contradiction(
            not done and not finish_reasons,
            "before-cancel response was complete, not a captured partial stream",
        )
        _contradiction(
            event.get("finish_reason") is None,
            "before-cancel finish reason contradicts the partial SSE response",
        )
        kind = "partial"
    else:
        _contradiction(
            done and finish_reasons == ["tool_calls"],
            f"{phase} response lacks completed tool_calls finish",
        )
        _contradiction(
            event.get("finish_reason") == finish_reasons[0],
            f"{phase} captured finish reason differs from raw SSE",
        )
        usage_rows = [
            chunk.get("usage") for chunk in chunks
            if isinstance(chunk, dict) and chunk.get("usage") is not None
        ]
        _need(len(usage_rows) == 1 and isinstance(usage_rows[0], dict),
              f"{phase} raw SSE completion lacks one token-usage record")
        usage = cast(dict[str, Any], usage_rows[0])
        _need(
            all(type(usage.get(key)) is int and usage[key] >= 0
                for key in ("prompt_tokens", "completion_tokens", "total_tokens")),
            f"{phase} raw SSE token usage is malformed",
        )
        _contradiction(
            usage["total_tokens"] == usage["prompt_tokens"] + usage["completion_tokens"]
            and usage["completion_tokens"] <= request_contract["generation_budget"]
            and usage["total_tokens"] <= req["max_context_tokens"],
            f"{phase} raw SSE token usage exceeds the bounded context/generation budget",
        )
        prompt_tokens = usage["prompt_tokens"]
        kind = "complete"
    return (
        phase,
        event["server_pid"],
        event["process_generation"],
        _timestamp(event.get("timestamp"), "parser event"),
        kind,
        prompt_tokens,
    )


def _mtp_admission(
    doc: dict[str, Any], request_sha256: str
) -> tuple[dict[str, Any], set[tuple[str, int]]]:
    _versions(doc, ("vllm", "parser", "mtp_tokens", "tokenizer"))
    versions = doc["subject"]["software_versions"]
    profile = _obj(
        doc.get("admission_profile"), "pinned admitted parser/MTP profile absent"
    )
    stack_binding = {
        "oem": doc["subject"].get("oem"),
        "host_id": doc["subject"].get("host_id"),
        "image_digest": doc["subject"].get("image_digest"),
        "model": doc["subject"].get("model"),
        "checkpoint_digest": doc["subject"].get("checkpoint_digest"),
        "vllm": versions.get("vllm"),
        "parser": versions.get("parser"),
        "tokenizer": versions.get("tokenizer"),
        "request_sha256": request_sha256,
    }
    binding_bytes = json.dumps(
        stack_binding, sort_keys=True, separators=(",", ":")
    ).encode()
    _contradiction(
        hashlib.sha256(binding_bytes).hexdigest()
        == profile.get("stack_binding_sha256"),
        "admission profile is not bound to the exact OEM/image/model/parser stack",
    )
    admitted_rows = _rows(
        profile.get("admitted"), 1, "explicit admitted parser/MTP profile"
    )
    admitted: set[tuple[str, int]] = set()
    for row in admitted_rows:
        _need(
            isinstance(row, dict)
            and _text(row.get("parser"))
            and type(row.get("mtp_tokens")) is int
            and _text(row.get("parser_revision"))
            and _text(row.get("vllm_revision")),
            "admitted parser/MTP profile row malformed",
        )
        _need(
            (row["parser"], row["mtp_tokens"]) not in admitted,
            "duplicate admitted parser/MTP profile row",
        )
        _contradiction(
            row["parser_revision"] == versions["parser"]
            and row["vllm_revision"] == versions["vllm"],
            "admitted parser/MTP profile revision differs from pinned stack",
        )
        admitted.add((row["parser"], row["mtp_tokens"]))
    return versions, admitted


def _mtp_parser_cancel(doc: dict[str, Any]) -> None:
    req = _request_binding(doc)
    runs = _rows(doc.get("matrix_runs"), 1, "parser × MTP × cancellation matrix")
    first_contract, versions, admitted = _mtp_profile(doc, req, runs)
    context: dict[str, Any] = {
        "req": req,
        "versions": versions,
        "first_contract": first_contract,
        "combinations": {},
        "completion_kinds": set(),
        "seen_modes": set(),
        "replay_hashes": set(),
        "prompt_token_counts": set(),
    }
    for run in runs:
        _mtp_run_capture(doc, run, context)
    context["admitted"] = admitted
    _mtp_matrix_summary(doc, context)


def _mtp_profile(
    doc: dict[str, Any], req: dict[str, Any], runs: list[Any]
) -> tuple[dict[str, Any], dict[str, str], set[tuple[str, int]]]:
    first_run = runs[0]
    _need(
        isinstance(first_run, dict)
        and _text(first_run.get("request_ref"))
        and _text(first_run.get("request_sha256")),
        "first matrix request sidecar identity absent",
    )
    first_run = cast(dict[str, Any], first_run)
    first_request = _oracle_payload(
        doc,
        first_run["request_ref"],
        first_run["request_sha256"],
        "first exact replay request",
    )
    first_request_raw = first_request.get("request_raw")
    _need(_text(first_request_raw), "first exact replay request bytes absent")
    first_request_raw = cast(str, first_request_raw)
    request_sha256 = hashlib.sha256(first_request_raw.encode("utf-8")).hexdigest()
    first_contract = _mtp_request_contract(
        first_request_raw, req, doc["subject"].get("model")
    )
    versions, admitted = _mtp_admission(doc, request_sha256)
    return first_contract, versions, admitted


def _mtp_run_capture(
    doc: dict[str, Any],
    run: Any,
    context: dict[str, Any],
) -> None:
    req = context["req"]
    versions = context["versions"]
    first_contract = context["first_contract"]
    combinations = context["combinations"]
    completion_kinds = context["completion_kinds"]
    seen_modes = context["seen_modes"]
    replay_hashes = context["replay_hashes"]
    prompt_token_counts = context["prompt_token_counts"]
    _need(
        isinstance(run, dict)
        and _text(run.get("parser"))
        and type(run.get("mtp_tokens")) is int
        and isinstance(run.get("cancel_midstream"), bool)
        and isinstance(run.get("request_id"), str)
        and isinstance(run.get("events"), list)
        and _text(run.get("oracle_ref"))
        and _text(run.get("oracle_sha256"))
        and _text(run.get("request_ref"))
        and _text(run.get("request_sha256"))
        and _text(run.get("parser_revision"))
        and _text(run.get("vllm_revision")),
        "parser/MTP/cancellation run identity absent",
    )
    _contradiction(run["mtp_tokens"] >= 0, "negative MTP token count was enabled")
    _need(_sha256(run.get("input_sha256")), "exact replay input SHA-256 absent")
    _contradiction(
        run["request_id"] == req["request_id"],
        "matrix request differs from bounded request",
    )
    _contradiction(
        run["parser_revision"] == versions["parser"]
        and run["vllm_revision"] == versions["vllm"],
        "matrix run parser/vLLM build differs from pinned stack",
    )
    request_capture = _oracle_payload(
        doc, run["request_ref"], run["request_sha256"], "exact replay request"
    )
    _need(
        _text(request_capture.get("request_raw")),
        "exact replay request bytes absent",
    )
    request_contract = _mtp_request_contract(
        request_capture["request_raw"], req, doc["subject"].get("model")
    )
    replay_sha = (
        "sha256:"
        + hashlib.sha256(request_capture["request_raw"].encode("utf-8")).hexdigest()
    )
    _contradiction(
        replay_sha == run["input_sha256"],
        "replay request bytes do not match the captured input SHA-256",
    )
    _contradiction(
        request_contract["body"] == first_contract["body"],
        "matrix replay request differs from the profile-bound request body",
    )
    replay_hashes.add(replay_sha)
    combinations.setdefault((run["parser"], run["mtp_tokens"]), set()).add(
        run["cancel_midstream"]
    )
    _mtp_observations(doc, run, req, request_contract, context)


def _mtp_observations(
    doc: dict[str, Any],
    run: dict[str, Any],
    req: dict[str, Any],
    request_contract: dict[str, Any],
    context: dict[str, Any],
) -> None:
    completion_kinds = context["completion_kinds"]
    seen_modes = context["seen_modes"]
    prompt_token_counts = context["prompt_token_counts"]
    events = _rows(run["events"], 4, "pre/cancel/post/restart event")
    oracle = _oracle_payload(
        doc, run["oracle_ref"], run["oracle_sha256"], "MTP parser/cancel"
    )
    _need(
        all(
            isinstance(oracle.get(key), list)
            for key in ("before_calls", "after_cancel_calls", "after_restart_calls")
        ),
        "independent before/cancel/restart tool-call oracle incomplete",
    )
    _contradiction(
        all(
            _mtp_calls_match_request(oracle[key], request_contract)
            for key in ("before_calls", "after_cancel_calls", "after_restart_calls")
        ),
        "independent tool-call oracle violates the captured request schema",
    )
    phases = [
        event.get("phase") if isinstance(event, dict) else None for event in events
    ]
    _need(
        phases == ["before_cancel", "cancel", "after_cancel", "after_restart"],
        "event trace must prove the next same-process call and a post-restart call",
    )
    pids: dict[str, int] = {}
    generations: dict[str, int] = {}
    times: list[datetime] = []
    http_ids: dict[str, str] = {}
    response_ids: dict[str, str] = {}
    prompt_tokens_by_phase: dict[str, int] = {}
    for event in events:
        phase, pid, generation, moment, kind, prompt_tokens = _validate_mtp_event(
            event, run, req, oracle, request_contract
        )
        times.append(moment)
        pids[phase], generations[phase] = pid, generation
        http_ids[phase] = event["request_id"]
        response_ids[phase] = event.get("response_id")
        if prompt_tokens is not None:
            prompt_tokens_by_phase[phase] = prompt_tokens
        if kind:
            completion_kinds.add(kind)
            seen_modes.add("cancel" if run["cancel_midstream"] else "no_cancel")
    _contradiction(
        times == sorted(times) and len(set(times)) == len(times),
        "parser/cancel/restart timestamps are not strictly causal",
    )
    _contradiction(
        times[0] >= datetime.fromisoformat(req["started_at"].replace("Z", "+00:00"))
        and times[-1]
        <= datetime.fromisoformat(req["finished_at"].replace("Z", "+00:00")),
        "parser event falls outside bounded request window",
    )
    _contradiction(
        pids["before_cancel"] == pids["cancel"] == pids["after_cancel"]
        and generations["before_cancel"]
        == generations["cancel"]
        == generations["after_cancel"],
        "same-process post-cancel tool call changed server PID/generation",
    )
    _contradiction(
        pids["after_restart"] != pids["after_cancel"]
        and generations["after_restart"] > generations["after_cancel"],
        "restart recovery did not use a new server process generation",
    )
    _contradiction(
        http_ids["before_cancel"] == http_ids["cancel"]
        and http_ids["after_cancel"] not in {http_ids["before_cancel"], http_ids["cancel"]}
        and http_ids["after_restart"] not in {
            http_ids["before_cancel"], http_ids["cancel"], http_ids["after_cancel"]
        },
        "HTTP request lifecycle does not reuse the partial request and create new follow-up IDs",
    )
    _contradiction(
        response_ids["before_cancel"] == response_ids["cancel"]
        and response_ids["after_cancel"] != response_ids["before_cancel"]
        and response_ids["after_restart"] != response_ids["after_cancel"],
        "response IDs do not track the canceled and retried inference lifecycle",
    )
    _contradiction(
        prompt_tokens_by_phase.get("after_cancel")
        == prompt_tokens_by_phase.get("after_restart"),
        "replayed request prompt token counts differ across cancel/restart",
    )
    prompt_token_counts.add(prompt_tokens_by_phase["after_cancel"])
    _contradiction(
        events[2]["exit_code"] == 0 and events[3]["exit_code"] == 0,
        "post-cancel or post-restart server exited unsuccessfully",
    )


def _mtp_matrix_summary(doc: dict[str, Any], summary: dict[str, Any]) -> None:
    combinations = summary["combinations"]
    admitted = summary["admitted"]
    replay_hashes = summary["replay_hashes"]
    prompt_token_counts = summary["prompt_token_counts"]
    seen_modes = summary["seen_modes"]
    completion_kinds = summary["completion_kinds"]
    _need(
        combinations
        and all(cancel_modes == {False, True} for cancel_modes in combinations.values()),
        "each parser/MTP combination needs paired cancel/no-cancel observations",
    )
    _contradiction(
        set(combinations) == admitted,
        "observed parser/MTP matrix differs from the explicitly admitted profile",
    )
    _need(len(replay_hashes) == 1, "matrix/restart request bytes differ across observations")
    _need(
        len(prompt_token_counts) == 1,
        "same request has inconsistent tokenizer context counts across matrix modes",
    )
    _need(
        seen_modes == {"cancel", "no_cancel"}
        and completion_kinds == {"partial", "complete"},
        "matrix lacks both cancellation modes and partial/complete response observations",
    )
    unsupported = _rows(doc.get("unsupported_combinations"), 1, "rejected parser/MTP combination controls")
    for attempt in unsupported:
        _need(
            isinstance(attempt, dict)
            and _text(attempt.get("parser"))
            and type(attempt.get("mtp_tokens")) is int
            and attempt["mtp_tokens"] >= 0
            and type(attempt.get("exit_code")) is int
            and attempt["exit_code"] != 0
            and _text(attempt.get("stderr_raw"))
            and _text(attempt.get("argv_raw")),
            "unsupported parser/MTP combo lacks literal rejected launch evidence",
        )
    _rollback(doc)


def _oomd_cache(doc: dict[str, Any]) -> None:
    _request_binding(doc)
    _versions(doc, ("systemd", "kernel", "driver", "runtime"))
    samples = _rows(
        doc.get("pressure_series"), 2, "time-correlated PSI/swap/UMA series"
    )
    times: list[datetime] = []
    for row in samples:
        _need(
            isinstance(row, dict)
            and _text(row.get("timestamp"))
            and _finite(row.get("psi_some_avg10"))
            and _finite(row.get("swap_in_bytes"))
            and _finite(row.get("uma_used_bytes"))
            and _finite(row.get("prompt_cache_bytes")),
            "pressure sample lacks measured PSI/swap/UMA/cache bytes",
        )
        _need(
            all(
                row[k] >= 0
                for k in (
                    "psi_some_avg10",
                    "swap_in_bytes",
                    "uma_used_bytes",
                    "prompt_cache_bytes",
                )
            ),
            "pressure sample contains negative measurements",
        )
        times.append(_timestamp(row["timestamp"], "pressure sample"))
    _contradiction(
        len(set(times)) == len(times) and times == sorted(times),
        "pressure samples are duplicated or not chronological",
    )
    kills = _rows(doc.get("oomd_events"), 1, "systemd-oomd event capture")
    _need(
        all(
            isinstance(x, dict)
            and _text(x.get("timestamp"))
            and _text(x.get("unit"))
            and _text(x.get("victim_cgroup"))
            and _text(x.get("journal_cursor"))
            for x in kills
        ),
        "oomd kill event lacks journal/cgroup identity",
    )
    effects = _rows(doc.get("dependent_effects"), 1, "dependent service effects")
    _need(
        all(
            isinstance(x, dict)
            and _text(x.get("unit"))
            and _text(x.get("timestamp"))
            and type(x.get("exit_status")) is int
            for x in effects
        ),
        "dependent service transition not captured",
    )
    _contradiction(
        any(x["exit_status"] != 0 for x in effects),
        "measured dependent-service failure was not captured",
    )
    kill_times = [_timestamp(x["timestamp"], "oomd event") for x in kills]
    effect_times = [
        _timestamp(x["timestamp"], "dependent service effect") for x in effects
    ]
    _contradiction(
        all(times[0] <= moment <= times[-1] for moment in kill_times)
        and all(any(kill <= effect for kill in kill_times) for effect in effect_times)
        and any(
            x["unit"] == "systemd-oomd" or "oomd" in x["victim_cgroup"] for x in kills
        ),
        "OOMD event is not time-correlated with measured pressure series",
    )
    _need(
        isinstance(doc.get("redacted_state_archive_sha256"), str)
        and re.fullmatch(r"[0-9a-f]{64}", doc["redacted_state_archive_sha256"])
        is not None,
        "redacted pre-recovery state archive SHA-256 absent",
    )


def _tool_wedge(doc: dict[str, Any]) -> None:
    req = _request_binding(doc)
    _versions(doc, ("runtime", "runtime_commit", "model"))
    trace = _obj(doc.get("wedge_trace"), "bounded tool-call wedge trace absent")
    _need(
        trace.get("request_id") == req["request_id"]
        and _text(trace.get("phase"))
        and isinstance(trace.get("events"), list),
        "wedge phase/request binding absent",
    )
    events = cast(list[Any], trace["events"])
    _need(len(events) >= 2, "wedge trace needs progress samples")
    ranks = set()
    for row in events:
        _need(
            isinstance(row, dict)
            and _text(row.get("timestamp"))
            and type(row.get("rank")) is int
            and type(row.get("collective_sequence")) is int
            and _text(row.get("event")),
            "per-rank/collective progress record incomplete",
        )
        ranks.add(row["rank"])
    by_rank: dict[int, set[int]] = {}
    rank_samples: dict[int, list[datetime]] = {}
    for row in events:
        by_rank.setdefault(row["rank"], set()).add(row["collective_sequence"])
        try:
            rank_samples.setdefault(row["rank"], []).append(
                datetime.fromisoformat(row["timestamp"].replace("Z", "+00:00"))
            )
        except (TypeError, ValueError) as exc:
            raise _Unknown(
                "wedge timestamps are not parseable UTC observations"
            ) from exc
    _need(
        len(by_rank) >= 2
        and all(len(sequences) == 1 for sequences in by_rank.values())
        and all(
            len(samples) >= 2
            and samples == sorted(samples)
            and len(set(samples)) == len(samples)
            for samples in rank_samples.values()
        ),
        "wedge trace must show no collective progress across repeated samples on multiple ranks",
    )
    acceptance_rows = _rows(doc.get("token_pairs"), 1, "draft/target tokens at wedge")
    _need(
        all(
            isinstance(x, dict)
            and _text(x.get("draft_token"))
            and _text(x.get("target_token"))
            for x in acceptance_rows
        ),
        "raw speculative token capture malformed",
    )
    derived = sum(x["draft_token"] == x["target_token"] for x in acceptance_rows) / len(
        acceptance_rows
    )
    reported = doc.get("reported_acceptance")
    _need(_finite(reported), "acceptance measurement absent")
    _contradiction(
        math.isclose(cast(float, reported), derived, rel_tol=0, abs_tol=1e-9),
        "reported speculative acceptance disagrees with raw token pairs",
    )
    _need(
        ranks and _text(doc.get("bundle_sha256")),
        "rank progress or bounded pre-restart bundle absent",
    )


def _cutlass_first(doc: dict[str, Any]) -> None:
    req = _request_binding(doc)
    _versions(doc, ("driver", "vllm", "quantization", "backend"))
    build = _obj(doc.get("build"), "effective build/backend capture absent")
    _need(
        _text(build.get("image_digest"))
        and _text(build.get("backend"))
        and _text(build.get("model_digest"))
        and build.get("request_id") == req["request_id"],
        "build tuple not pinned to model/request",
    )
    _contradiction(
        build["image_digest"] == doc["subject"]["image_digest"]
        and build["model_digest"] == doc["subject"]["checkpoint_digest"],
        "first-request build image/model differs from the subject digests",
    )
    readiness = _obj(doc.get("readiness"), "server readiness event absent")
    first = _obj(
        doc.get("first_inference"), "first functional request after readiness absent"
    )
    _need(
        _text(readiness.get("timestamp"))
        and _text(first.get("timestamp"))
        and first.get("request_id") == req["request_id"]
        and _text(first.get("kernel_backend")),
        "readiness/first-request timestamps and backend incomplete",
    )
    ready_at = datetime.fromisoformat(readiness["timestamp"].replace("Z", "+00:00"))
    request_at = datetime.fromisoformat(first["timestamp"].replace("Z", "+00:00"))
    _contradiction(request_at >= ready_at, "first request predates server readiness")
    _need(
        isinstance(first.get("exit_code"), int) and _text(first.get("cuda_log_raw")),
        "first request CUDA result/log absent",
    )
    _contradiction(
        first["kernel_backend"] == build["backend"]
        and re.search(
            r"illegal instruction|CUDA_ERROR_ILLEGAL_ADDRESS|Xid\s+\d+",
            first["cuda_log_raw"],
            re.I,
        )
        is None,
        "first request backend mismatch or CUDA/Xid failure signal",
    )
    candidate = _obj(doc.get("candidate_output"), "candidate correctness output absent")
    reference = _obj(doc.get("reference_output"), "paired reference output absent")
    _need(
        _text(candidate.get("raw_output"))
        and _text(reference.get("raw_output"))
        and _text(candidate.get("oracle_ref"))
        and _text(candidate.get("oracle_sha256")),
        "paired output/oracle missing",
    )
    oracle = _oracle_payload(
        doc,
        candidate["oracle_ref"],
        candidate["oracle_sha256"],
        "first-request semantic",
    )
    _contradiction(
        first["exit_code"] == 0
        and candidate["raw_output"] == reference["raw_output"]
        and candidate["raw_output"] == oracle.get("expected_output"),
        "first inference failed or candidate correctness differs from reference",
    )
    _rollback(doc)


def _json_soak(doc: dict[str, Any]) -> None:
    req = _request_binding(doc)
    _versions(doc, ("runtime", "tokenizer", "template", "sampling", "kv_cache", "mtp"))
    pairs = _rows(doc.get("paired_runs"), 2, "BF16/candidate long-run pairs")
    checkpoints: set[str] = set()
    seen_by_mode: dict[str, dict[str, Any]] = {}
    modes: set[str] = set()
    for pair in pairs:
        _need(
            isinstance(pair, dict)
            and pair.get("request_id") == req["request_id"]
            and _text(pair.get("checkpoint_digest"))
            and _text(pair.get("tokenizer_digest"))
            and _text(pair.get("template_digest"))
            and _text(pair.get("mode"))
            and _text(pair.get("oracle_ref"))
            and _text(pair.get("oracle_sha256"))
            and isinstance(pair.get("turns"), list),
            "pair identity/sample config absent",
        )
        mode = pair["mode"]
        _need(
            mode in {"bf16", "candidate"}, "paired run mode must be BF16 or candidate"
        )
        _need(mode not in modes, "duplicate BF16/candidate run")
        modes.add(mode)
        checkpoints.add(pair["checkpoint_digest"])
        oracle = _oracle_payload(
            doc, pair["oracle_ref"], pair["oracle_sha256"], "long-run JSON"
        )
        _need(
            isinstance(oracle.get("turns"), dict),
            "independent turn-id to JSON oracle absent",
        )
        mode_turns: dict[str, Any] = {}
        for turn in _rows(pair["turns"], 1, "long-run structured output"):
            _need(
                isinstance(turn, dict)
                and _text(turn.get("raw_output"))
                and _text(turn.get("turn_id")),
                "raw output or turn identity absent",
            )
            try:
                actual = strict_json_loads(turn["raw_output"])
            except (json.JSONDecodeError, RecursionError) as exc:
                raise _Fail(f"long-run output is invalid JSON: {exc}") from exc
            expected = oracle["turns"].get(turn["turn_id"])
            _need(
                expected is not None,
                f"independent oracle missing turn {turn['turn_id']}",
            )
            _contradiction(
                actual == expected,
                "long-run JSON/content differs from predeclared oracle",
            )
            mode_turns[turn["turn_id"]] = actual
        seen_by_mode[mode] = mode_turns
    _need(
        modes == {"bf16", "candidate"} and len(checkpoints) == 1,
        "same-checkpoint BF16/candidate comparison absent",
    )
    _contradiction(
        seen_by_mode["bf16"] == seen_by_mode["candidate"],
        "candidate long-run JSON/content differs from BF16 paired run",
    )
    _rollback(doc)


def _ray_graph(doc: dict[str, Any]) -> None:
    req = _request_binding(doc)
    _need(
        _text(doc.get("host_torch"))
        and _text(doc.get("container_torch"))
        and _text(doc.get("cuda_version"))
        and _text(doc.get("vllm_version"))
        and _text(doc.get("ray_version"))
        and _text(doc.get("nccl_version")),
        "host/container software tuple incomplete",
    )
    runs = _rows(doc.get("graph_eager_runs"), 2, "graph/eager paired runs")
    _need(
        {x.get("mode") for x in runs if isinstance(x, dict)} == {"graph", "eager"},
        "graph/eager A/B absent",
    )
    for run in runs:
        _need(
            run.get("request_id") == req["request_id"]
            and isinstance(run.get("rank_events"), list)
            and isinstance(run.get("gpu_samples"), list),
            "rank progress/GPU series absent",
        )
        events = _rows(run["rank_events"], 2, "per-rank progress")
        _need(
            all(
                isinstance(e, dict)
                and type(e.get("rank")) is int
                and type(e.get("completed_collective")) is int
                and _text(e.get("timestamp"))
                for e in events
            ),
            "rank collective progress malformed",
        )
        by_rank: dict[int, list[tuple[datetime, int]]] = {}
        for event in events:
            by_rank.setdefault(event["rank"], []).append(
                (
                    _timestamp(event["timestamp"], "graph rank"),
                    event["completed_collective"],
                )
            )
        _need(
            set(by_rank) >= {0, 1} and all(len(seq) >= 2 for seq in by_rank.values()),
            "graph/eager capture needs repeated progress samples for both ranks",
        )
        _contradiction(
            all(
                seq == sorted(seq) and seq[-1][0] > seq[0][0] and seq[-1][1] > seq[0][1]
                for seq in by_rank.values()
            ),
            "rank collective sequence failed to progress",
        )
        gpu = _rows(run["gpu_samples"], 1, "GPU utilization series")
        _need(
            all(
                isinstance(x, dict) and _finite(x.get("utilization_percent"))
                for x in gpu
            ),
            "GPU samples malformed",
        )
        _contradiction(
            all(e["completed_collective"] > 0 for e in events),
            "rank stalled before completing a collective",
        )
    _rollback(doc)


def _build_matrix(doc: dict[str, Any]) -> None:
    req = _request_binding(doc)
    build = _obj(
        doc.get("effective_build"), "effective wheel/PTXAS/compiler provenance absent"
    )
    _need(
        all(
            _text(build.get(key))
            for key in (
                "image_digest",
                "wheel_sha256",
                "ptxas_version",
                "architecture_flags",
                "resolver_log_sha256",
                "model_digest",
                "backend",
            )
        ),
        "exact build/toolchain tuple incomplete",
    )
    matrix = _rows(doc.get("operation_matrix"), 1, "architecture operation matrix")
    required = _rows(
        doc.get("required_operations"), 1, "required model/backend operation list"
    )
    required_names = {x for x in required if _text(x)}
    _contradiction(
        {x.get("operation") for x in matrix if isinstance(x, dict)} == required_names,
        "build matrix does not cover the required operations exactly",
    )
    for row in matrix:
        _need(
            row.get("request_id") == req["request_id"]
            and _text(row.get("kernel_name"))
            and all(
                type(row.get(k)) is int
                for k in (
                    "build_exit_code",
                    "import_exit_code",
                    "load_exit_code",
                    "first_inference_exit_code",
                )
            )
            and _text(row.get("raw_output")),
            "build/import/load/first inference row incomplete",
        )
        _contradiction(
            all(
                row[k] == 0
                for k in (
                    "build_exit_code",
                    "import_exit_code",
                    "load_exit_code",
                    "first_inference_exit_code",
                )
            ),
            "required operation failed in build/import/load/first inference",
        )
        _need(_finite(row.get("finite_output_value")), "finite output sample absent")
    negative = _obj(
        doc.get("wrong_toolchain_control"), "wrong-toolchain negative absent"
    )
    _need(
        isinstance(negative.get("exit_code"), int)
        and _text(negative.get("stderr_raw"))
        and _text(negative.get("compiler_digest")),
        "wrong-toolchain raw command outcome absent",
    )
    _contradiction(
        negative["exit_code"] != 0,
        "mismatched toolchain control unexpectedly succeeded",
    )
    _rollback(doc)


def _ray_resource(doc: dict[str, Any]) -> None:
    req = _request_binding(doc)
    _versions(doc, ("ray", "vllm", "driver", "sgl_kernel"))
    nodes = _rows(doc.get("ray_nodes"), 2, "two-node effective Ray resource map")
    _need(
        len({node.get("node_id") for node in nodes if isinstance(node, dict)})
        == len(nodes),
        "Ray node identities collide",
    )
    for node in nodes:
        _need(
            _text(node.get("node_id"))
            and isinstance(node.get("resources"), dict)
            and _text(node.get("image_digest"))
            and _text(node.get("sm_arch")),
            "per-node effective resource/image/architecture absent",
        )
        gpu_count = node["resources"].get("GPU", 0)
        _need(_finite(gpu_count), "Ray GPU resource count is malformed")
        _contradiction(
            gpu_count >= 1 and node["image_digest"] == doc["subject"]["image_digest"],
            "GB10 node has no schedulable GPU or wrong effective image",
        )
    backend = _obj(doc.get("backend_smoke"), "vLLM backend/kernel smoke absent")
    _need(
        backend.get("request_id") == req["request_id"]
        and isinstance(backend.get("sm_arch"), str)
        and _text(backend.get("kernel_name"))
        and type(backend.get("exit_code")) is int
        and _text(backend.get("raw_output")),
        "backend smoke lacks request/kernel result",
    )
    _contradiction(
        backend["exit_code"] == 0 and backend["sm_arch"] == "sm_121",
        "backend smoke/kernel architecture failed",
    )
    negative = _obj(
        doc.get("unsupported_tag_control"), "unsupported-tag negative capture absent"
    )
    _need(
        _text(negative.get("image_digest"))
        and isinstance(negative.get("exit_code"), int)
        and _text(negative.get("stderr_raw")),
        "unsupported-tag raw failure capture absent",
    )
    _contradiction(
        negative["image_digest"] != doc["subject"]["image_digest"]
        and negative["exit_code"] != 0,
        "unsupported tag control did not fail against its captured digest",
    )


def _container_offline(doc: dict[str, Any]) -> None:
    req = _request_binding(doc)
    containers = _rows(doc.get("containers"), 2, "effective container/build records")
    names: set[str] = set()
    ports: set[int] = set()
    budgets = []
    for row in containers:
        _need(
            all(
                _text(row.get(key))
                for key in (
                    "name",
                    "image_digest",
                    "model_digest",
                    "checkpoint_digest",
                    "patches_sha256",
                )
            )
            and row.get("request_id") == req["request_id"]
            and type(row.get("port")) is int
            and type(row.get("memory_budget_bytes")) is int,
            "container model/build/request tuple incomplete",
        )
        names.add(row["name"])
        ports.add(row["port"])
        budgets.append(row["memory_budget_bytes"])
        _need(
            type(row.get("load_exit_code")) is int
            and isinstance(row.get("output_raw"), str),
            "per-container model load/generation evidence absent",
        )
        _contradiction(
            row["load_exit_code"] == 0 and bool(row["output_raw"]),
            "container failed actual model load or functional generation",
        )
    _contradiction(
        len(names) == len(containers) and len(ports) == len(containers),
        "container instance names/ports collide",
    )
    reservation = _obj(
        doc.get("memory_reservation"), "combined memory reservation absent"
    )
    _need(
        type(reservation.get("available_bytes")) is int
        and type(reservation.get("reserve_bytes")) is int,
        "available-memory/reserve measurements absent",
    )
    _contradiction(
        sum(budgets) + reservation["reserve_bytes"] <= reservation["available_bytes"],
        "combined instance budget exceeds available memory and reserve",
    )
    offline = _obj(doc.get("offline_boot"), "offline startup capture absent")
    _need(
        type(offline.get("network_disabled_exit_code")) is int
        and _text(offline.get("argv_sha256"))
        and _text(offline.get("image_digest")),
        "network-disabled boot command/image evidence absent",
    )
    _contradiction(
        offline["network_disabled_exit_code"] == 0,
        "complete precached container failed offline startup",
    )
    missing = _obj(
        doc.get("missing_artifact_negative"), "missing-artifact negative capture absent"
    )
    _need(
        _text(missing.get("artifact_sha256"))
        and type(missing.get("exit_code")) is int
        and _text(missing.get("stderr_raw")),
        "missing artifact command failure evidence absent",
    )
    _contradiction(
        missing["exit_code"] != 0, "offline boot silently accepted missing artifact"
    )
    _rollback(doc)


_VALIDATORS: dict[str, Callable[[dict[str, Any]], None]] = {
    "DELTA-FORUM-QWEN-LONG-AGENT-STOP-01": _long_stop,
    "DELTA-FORUM-QWEN-MTP-PARSER-CANCEL-STATE-CHECK-01": _mtp_parser_cancel,
    "DELTA-FORUM-QWEN-SERVICE-OOMD-CACHE-FAIL-01": _oomd_cache,
    "DELTA-FORUM-QWEN-TOOLCALL-WEDGE-01": _tool_wedge,
    "DELTA-FORUM-QWEN35-NVFP4-CUTLASS-FIRST-REQUEST-GATE-01": _cutlass_first,
    "DELTA-FORUM-QWEN38-LONG-RUN-JSON-CORRECTNESS-CANARY-01": _json_soak,
    "DELTA-FORUM-RAY-TORCH-GRAPH-HANG-01": _ray_graph,
    "DELTA-FORUM-VLLM-GB10-ARCH-AND-BUILD-MATRIX-01": _build_matrix,
    "DELTA-FORUM-VLLM-RAY-GB10-RESOURCE-FIX-01": _ray_resource,
    "DELTA-ROOT-CONTAINER-EFFECTIVE-BUILD-AND-OFFLINE-GATE-01": _container_offline,
}


def assess(card_id: str, raw_document: Any) -> dict[str, Any]:
    validator = _VALIDATORS.get(card_id)
    if validator is None:
        return {
            "status": "unknown",
            "could_not_run": 1,
            "reason": "no batch-03 validator for card",
        }
    try:
        validator(_capture(raw_document, card_id))
    except _Fail as exc:
        return {"status": "fail", "could_not_run": 0, "reason": str(exc)}
    except _Unknown as exc:
        return {"status": "unknown", "could_not_run": 1, "reason": str(exc)}
    except (
        AttributeError,
        IndexError,
        KeyError,
        TypeError,
        ValueError,
        StopIteration,
        RecursionError,
    ) as exc:
        return {
            "status": "unknown",
            "could_not_run": 1,
            "reason": f"malformed raw record: {exc}",
        }
    return {
        "status": "pass",
        "could_not_run": 0,
        "reason": "raw batch-03 measurements satisfy domain predicate",
    }


def verify(card_id: str, path: Path | None = None) -> dict[str, Any]:
    p = path or EVIDENCE / card_id / "runtime-capture.json"
    if card_id not in _VALIDATORS:
        result = assess(card_id, {})
        result["files"] = [str(p)]
        return result
    try:
        content = read_regular_bytes(p, 4 * 1024 * 1024)
        if len(content) > 4 * 1024 * 1024:
            return {
                "status": "unknown",
                "could_not_run": 1,
                "reason": "capture exceeds 4 MiB",
                "files": [str(p)],
            }
        raw = strict_json_loads(content.decode("utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError, RecursionError) as exc:
        return {
            "status": "unknown",
            "could_not_run": 1,
            "reason": f"raw capture unavailable: {exc}",
            "files": [str(p)],
        }
    result = assess(card_id, raw)
    result["files"] = [str(p)]
    return result
