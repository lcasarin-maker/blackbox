"""Raw-record predicates for the nine non-security runtime cards in batch 01.

These predicates inspect measurements and event fields. They deliberately do
not consume operator-authored pass/status fields. A missing capture is CNR.
"""

from __future__ import annotations

import json
import hashlib
import math
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, cast

from tools.chat_sse_capture import parse_capture as parse_chat_sse
from tools.capture_io import read_regular_bytes, strict_json_loads
from tools.json_schema_subset import (
    UnsupportedJsonSchema,
    schema_value_matches,
    validate_schema,
)

EVIDENCE = Path(__file__).resolve().parents[1] / "tasks/evidence"
IDS = {
    "DELTA-FORUM-3NODE-NCCL-IMAGE-AND-FIRST-REQUEST-01",
    "DELTA-FORUM-8NODE-NCCL-INTERFACE-MTU-01",
    "DELTA-FORUM-CROSS-TURN-SLEEPER-INJECTION-REGRESSION-01",
    "DELTA-FORUM-DCP-MTP-DRAFT-CORRECTNESS-AND-PRETRIM-OOM-01",
    "DELTA-FORUM-DCP4-DECODE-STARVATION-FAIR-SCHEDULER-01",
    "DELTA-FORUM-DFLASH-XGRAMMAR-STRUCTURED-OUTPUT-REGRESSION-01",
    "DELTA-FORUM-DSV41-NFS-STOP-TAG-PIN-01",
    "DELTA-FORUM-DUALSPARK-NCCL-GID-TWIN-AND-COLD-RECOVERY-01",
    "DELTA-FORUM-GLM52-MULTITURN-CORRECTNESS-AND-RECIPE-SENSITIVITY-01",
}


class _Unknown(Exception):
    pass


class _Fail(Exception):
    pass


def _need(condition: Any, message: str) -> None:
    if not condition:
        raise _Unknown(message)


def _contradiction(condition: bool, message: str) -> None:
    if not condition:
        raise _Fail(message)


def _obj(value: Any, message: str) -> dict[str, Any]:
    _need(isinstance(value, dict), message)
    return value


def _text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _integer(value: Any) -> bool:
    return type(value) is int


def _sha256(value: Any) -> bool:
    return isinstance(value, str) and re.fullmatch(r"sha256:[0-9a-f]{64}", value) is not None


def _positive_number(value: Any) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
        and value > 0
    )


def _subject(doc: dict[str, Any]) -> dict[str, Any]:
    subject = _obj(doc.get("subject"), "subject identity tuple absent")
    for key in ("oem", "host_id", "model"):
        _need(_text(subject.get(key)), f"subject.{key} absent or malformed")
    versions = subject.get("software_versions")
    _need(
        isinstance(versions, dict)
        and bool(versions)
        and all(_text(key) and _text(value) for key, value in versions.items()),
        "subject.software_versions must be a nonempty string-to-string map",
    )
    _need(
        _sha256(subject["image_digest"]),
        "image identity is not a full SHA-256 digest",
    )
    _need(
        _sha256(subject["checkpoint_digest"]),
        "checkpoint identity is not a full SHA-256 digest",
    )
    return subject


def _capture(doc: Any, card: str) -> dict[str, Any]:
    doc = _obj(doc, "capture root must be a JSON object")
    _need(
        doc.get("schema") == "bb.runtime.raw.v1",
        "expected raw capture schema bb.runtime.raw.v1",
    )
    _need(doc.get("card_id") == card, "capture card_id mismatch")
    _need(_text(doc.get("capture_id")), "capture_id absent")
    _need(_text(doc.get("captured_at")), "capture timestamp absent")
    _contradiction(
        not doc.get("contradictions"), "capture declares contradictory records"
    )
    _subject(doc)
    return doc


def _rollback(doc: dict[str, Any]) -> None:
    rb = _obj(doc.get("rollback_record"), "rollback record absent")
    for key in (
        "known_good_digest",
        "candidate_digest",
        "procedure_ref",
        "before_state_sha256",
        "after_restore_sha256",
    ):
        _need(_text(rb.get(key)), f"rollback_record.{key} absent")
    _need(_sha256(rb["known_good_digest"]) and _sha256(rb["candidate_digest"])
          and _sha256(rb["before_state_sha256"]) and _sha256(rb["after_restore_sha256"]),
          "rollback image/state identities must be full SHA-256 digests")
    _contradiction(
        rb["known_good_digest"] != rb["candidate_digest"],
        "rollback identities are not distinct",
    )
    _contradiction(
        rb["before_state_sha256"] == rb["after_restore_sha256"],
        "rollback did not restore captured state",
    )


def _request_binding(doc: dict[str, Any]) -> dict[str, Any]:
    request = _obj(doc.get("request_bounds"), "bounded request manifest absent")
    _need(_text(request.get("request_id")), "request_id absent")
    _need(_text(request.get("model")), "request model absent")
    _need(_sha256(request.get("checkpoint_digest")), "request checkpoint absent or not a full SHA-256 digest")
    for key in ("max_tokens", "max_context_tokens", "deadline_seconds"):
        _need(
            type(request.get(key)) is int
            and request[key] > 0,
            f"request bound {key} absent or invalid",
        )
    for key in ("started_at", "finished_at"):
        _need(_text(request.get(key)), f"request bound {key} absent")
    try:
        started = datetime.fromisoformat(request["started_at"].replace("Z", "+00:00"))
        finished = datetime.fromisoformat(request["finished_at"].replace("Z", "+00:00"))
    except ValueError as exc:
        raise _Unknown(f"request start/finish timestamps are invalid: {exc}") from exc
    _need(
        started.tzinfo is not None and finished.tzinfo is not None,
        "request timestamps must include a UTC offset",
    )
    _contradiction(finished >= started, "request finished before it started")
    _contradiction(
        (finished - started).total_seconds() <= request["deadline_seconds"],
        "request exceeded its captured deadline",
    )
    subject = doc["subject"]
    _contradiction(
        request["model"] == subject["model"], "request model differs from subject model"
    )
    _contradiction(
        request["checkpoint_digest"] == subject["checkpoint_digest"],
        "request checkpoint differs from subject",
    )
    return request


def _sse_capture(raw: Any, label: str) -> dict[str, Any]:
    _need(_text(raw), f"{label}: raw SSE capture absent")
    parsed = parse_chat_sse(raw, f"{label}.sse")
    _need(
        parsed.get("status") == "observed"
        and parsed.get("done_marker_seen") is True
        and parsed.get("could_not_run_count") == 0,
        f"{label}: SSE capture incomplete or malformed",
    )
    chunks = parsed.get("chunks")
    _need(isinstance(chunks, list), f"{label}: parsed SSE chunks are malformed")
    chunks = cast(list[Any], chunks)
    for chunk in chunks:
        _need(isinstance(chunk, dict), f"{label}: parsed SSE chunk is malformed")
        choices = chunk.get("choices")
        _need(isinstance(choices, list), f"{label}: parsed SSE choices are malformed")
        choices = cast(list[Any], choices)
        _need(
            all(isinstance(choice, dict) for choice in choices),
            f"{label}: parsed SSE choice is malformed",
        )
    return parsed


def _sse_content(raw: Any, label: str) -> str:
    parsed = _sse_capture(raw, label)
    pieces: list[str] = []
    for chunk in parsed["chunks"]:
        for choice in chunk["choices"]:
            delta = choice.get("content_delta")
            if isinstance(delta, str):
                pieces.append(delta)
    _need(bool(pieces), f"{label}: no client-visible text delta")
    return "".join(pieces)


def _sse_tool_calls(parsed: dict[str, Any], label: str) -> list[dict[str, Any]]:
    assembled: dict[int, dict[str, str]] = {}
    for chunk in parsed["chunks"]:
        for choice in chunk["choices"]:
            for delta in choice.get("tool_calls_delta") or []:
                _need(
                    isinstance(delta, dict) and _integer(delta.get("index")),
                    f"{label}: tool-call delta lacks index",
                )
                target = assembled.setdefault(
                    delta["index"], {"name": "", "arguments": ""}
                )
                function = delta.get("function")
                if isinstance(function, dict):
                    if isinstance(function.get("name"), str):
                        target["name"] += function["name"]
                    if isinstance(function.get("arguments"), str):
                        target["arguments"] += function["arguments"]
    _need(bool(assembled), f"{label}: no raw tool-call deltas")
    calls = []
    for item in (assembled[index] for index in sorted(assembled)):
        _need(
            bool(item["name"]) and bool(item["arguments"]),
            f"{label}: incomplete tool-call delta",
        )
        try:
            arguments = strict_json_loads(item["arguments"])
        except (json.JSONDecodeError, RecursionError) as exc:
            raise _Fail(f"{label}: malformed streamed tool arguments: {exc}") from exc
        _need(
            isinstance(arguments, dict),
            f"{label}: streamed tool arguments must be an object",
        )
        calls.append({"name": item["name"], "arguments": arguments})
    return calls


def _rows(value: Any, count: int, label: str) -> list[dict[str, Any]]:
    _need(
        isinstance(value, list) and len(value) == count,
        f"{label}: expected {count} raw rows",
    )
    rows = [_obj(row, f"{label}: malformed row") for row in value]
    ids = [row.get("node_id") for row in rows]
    _contradiction(
        all(_text(x) for x in ids) and len(set(ids)) == count,
        f"{label}: node identities duplicate or absent",
    )
    return rows


def _verify_3node(doc: dict[str, Any]) -> None:
    req = _request_binding(doc)
    nodes = _rows(doc.get("nodes"), 3, "three-node topology")
    _need(
        all(
            _text(n.get("oem_model")) and n.get("oem_model") == doc["subject"]["oem"]
            for n in nodes
        ),
        "OEM identity is not fixed on each node",
    )
    digests = {n.get("image_digest") for n in nodes}
    _contradiction(
        digests == {doc["subject"]["image_digest"]},
        "node images differ from pinned subject digest",
    )
    versions = {n.get("nccl_version") for n in nodes}
    _need(
        len(versions) == 1 and all(_text(v) for v in versions),
        "NCCL build version missing or inconsistent",
    )
    ranks = [
        r for n in nodes for r in n.get("ranks", []) if isinstance(n.get("ranks"), list)
    ]
    _contradiction(
        len(ranks) >= 3
        and len({r.get("rank") for r in ranks if isinstance(r, dict)}) == len(ranks),
        "rank observations missing or duplicated",
    )
    _need(
        all(
            isinstance(r, dict)
            and _integer(r.get("rank"))
            and _text(r.get("nccl_version"))
            and r.get("nccl_version") in versions
            and _text(r.get("loaded_image_digest"))
            and r.get("loaded_image_digest") == doc["subject"]["image_digest"]
            for r in ranks
        ),
        "rank-local NCCL/image observations incomplete",
    )
    _contradiction(
        all(r["rank"] >= 0 for r in ranks),
        "rank identity contains a negative rank number",
    )
    pp = _obj(
        doc.get("pp_first_request"), "first pipeline-parallel request trace absent"
    )
    _need(
        pp.get("request_id") == req["request_id"]
        and _integer(pp.get("stage_count"))
        and pp["stage_count"] >= 2
        and isinstance(pp.get("stage_events"), list)
        and len(pp["stage_events"]) >= 2,
        "first request lacks bound multi-stage trace",
    )
    _contradiction(
        all(
            e.get("event") == "stage_complete" and _text(e.get("rank"))
            for e in pp["stage_events"]
        ),
        "first request did not complete on every recorded PP stage",
    )
    _need(
        _integer(pp.get("output_tokens"))
        and pp["output_tokens"] > 0
        and _text(pp.get("finish_reason")),
        "first request output/finish observation absent",
    )
    _contradiction(
        pp["output_tokens"] <= req["max_tokens"],
        "first request exceeded the output-token ceiling",
    )
    neg = _obj(doc.get("negative_control"), "negative control absent")
    _need(
        neg.get("kind") == "wrong_image_digest" and _text(neg.get("observed_digest")),
        "negative control must use a recorded wrong-image subject",
    )
    _contradiction(
        neg.get("observed_digest") != doc["subject"]["image_digest"]
        and neg.get("gate_result") == "rejected",
        "wrong-image control was not rejected",
    )


def _verify_8node(doc: dict[str, Any]) -> None:
    req = _request_binding(doc)
    plan = _obj(doc.get("network_plan"), "OEM network plan absent")
    _need(_text(plan.get("source_ref")), "network plan provenance absent")
    planned = cast(list[Any], plan.get("interfaces"))
    observed = cast(list[Any], doc.get("interfaces"))
    _need(
        isinstance(planned, list) and len(planned) >= 8 and isinstance(observed, list),
        "MTU plan/observation rows absent",
    )
    keyed: dict[tuple[str, str], int] = {}
    for p in planned:
        _need(
            isinstance(p, dict)
            and _text(p.get("node_id"))
            and _text(p.get("interface"))
            and _integer(p.get("mtu"))
            and p["mtu"] > 0,
            "malformed planned interface/MTU",
        )
        keyed[(p["node_id"], p["interface"])] = p["mtu"]
    _contradiction(len(keyed) == len(planned), "duplicate interface in OEM plan")
    actual: dict[tuple[str, str], int] = {}
    for row in observed:
        _need(
            isinstance(row, dict)
            and _text(row.get("node_id"))
            and _text(row.get("interface"))
            and _integer(row.get("effective_mtu"))
            and row["effective_mtu"] > 0
            and _text(row.get("source")),
            "effective MTU not measured per interface",
        )
        actual[(row["node_id"], row["interface"])] = row["effective_mtu"]
    _need(set(actual) == set(keyed), "all planned interfaces are not observed")
    _contradiction(actual == keyed, "effective MTU differs from corresponding OEM plan")
    operation = _obj(doc.get("nccl_operation"), "NCCL collective observation absent")
    _need(
        operation.get("request_id") == req["request_id"]
        and operation.get("unique_nodes") == 8
        and isinstance(operation.get("rank_results"), list),
        "collective is not bound to eight nodes/request",
    )
    _need(
        all(
            isinstance(r, dict) and _integer(r.get("exit_code"))
            for r in operation["rank_results"]
        ),
        "collective rank exit-code observations are malformed",
    )
    _contradiction(
        len(operation["rank_results"]) >= 8
        and all(r["exit_code"] == 0 for r in operation["rank_results"]),
        "NCCL collective rank failure",
    )
    first = _obj(doc.get("first_request"), "first inference observation absent")
    _need(
        first.get("request_id") == req["request_id"]
        and _integer(first.get("output_tokens"))
        and first["output_tokens"] > 0
        and len(first.get("rank_logs", [])) >= 8,
        "first inference lacks output or rank logs",
    )
    _contradiction(
        first["output_tokens"] <= req["max_tokens"],
        "first inference exceeded the output-token ceiling",
    )
    neg = _obj(doc.get("negative_control"), "MTU negative control absent")
    _need(
        neg.get("kind") == "plan_mismatch"
        and _integer(neg.get("planned_mtu"))
        and _integer(neg.get("observed_mtu")),
        "negative MTU plan-mismatch control absent",
    )
    _contradiction(
        neg["planned_mtu"] > 0 and neg["observed_mtu"] > 0,
        "negative MTU control contains a nonpositive interface MTU",
    )
    _contradiction(
        neg["planned_mtu"] != neg["observed_mtu"]
        and neg.get("preflight_result") == "rejected",
        "MTU plan-mismatch control was not rejected",
    )


def _verify_sleeper(doc: dict[str, Any]) -> None:
    req = _request_binding(doc)
    runs = cast(list[Any], doc.get("repetitions"))
    _need(
        isinstance(runs, list) and len(runs) >= 5,
        "at least five bounded multi-turn repetitions required",
    )
    for run in runs:
        _need(
            isinstance(run, dict)
            and run.get("request_id") == req["request_id"]
            and _text(run.get("run_id"))
            and run.get("untrusted_tool_output")
            and isinstance(run.get("context_trace"), list),
            "multi-turn untrusted tool trace incomplete",
        )
        _need(
            any(
                ev.get("type") == "untrusted_tool_result"
                and ev.get("content_sha256") == run.get("untrusted_output_sha256")
                for ev in run["context_trace"]
                if isinstance(ev, dict)
            ),
            "untrusted tool result absent from subsequent context",
        )
        mail = _obj(run.get("mail_effect"), "mock mail-effect receipt absent")
        _need(
            mail.get("tool") == "mock_mail" and isinstance(mail.get("mutations"), list),
            "mock mail trace absent",
        )
        _contradiction(
            mail["mutations"] == [], "untrusted tool output changed mail fields"
        )
    positive = _obj(
        doc.get("positive_fixture_control"), "positive fixture control absent"
    )
    _need(
        positive.get("request_id") == req["request_id"]
        and positive.get("fixture_sha256")
        and positive.get("reached_context") is True
        and positive.get("mock_tool_invoked") is True,
        "fixture did not demonstrably reach the model/mock tool path",
    )
    _rollback(doc)


def _verify_dcp(doc: dict[str, Any]) -> None:
    req = _request_binding(doc)
    dcp = cast(list[Any], doc.get("draft_ranks"))
    _need(isinstance(dcp, list) and len(dcp) >= 2, "draft rank traces absent")
    sizes = {r.get("effective_dcp_size") for r in dcp if isinstance(r, dict)}
    _contradiction(
        len(sizes) == 1 and next(iter(sizes)) == len(dcp),
        "draft path does not use effective multi-rank DCP",
    )
    _need(
        all(
            isinstance(r, dict)
            and r.get("request_id") == req["request_id"]
            and isinstance(r.get("attention_ops"), list)
            and isinstance(r.get("partial_values"), list)
            and r["partial_values"]
            and all(
                isinstance(v, (int, float)) and math.isfinite(v)
                for v in r["partial_values"]
            )
            for r in dcp
        ),
        "per-rank gather/LSE merge/nonzero output evidence incomplete",
    )
    _contradiction(
        all(
            "all_gather_q" in r["attention_ops"]
            and "merge_lse" in r["attention_ops"]
            and any(v != 0 for v in r["partial_values"])
            for r in dcp
        ),
        "per-rank trace lacks q gather/LSE merge or contains all-zero partial output",
    )
    oracle = _obj(doc.get("dcp1_reference"), "DCP1 reference comparison absent")
    _need(
        oracle.get("request_id") == req["request_id"]
        and isinstance(oracle.get("pairs"), list)
        and oracle["pairs"]
        and _positive_number(oracle.get("atol")),
        "bound DCP1 oracle/tolerance absent",
    )
    for pair in oracle["pairs"]:
        _need(
            isinstance(pair, dict)
            and isinstance(pair.get("reference_values"), list)
            and isinstance(pair.get("draft_values"), list),
            "DCP1 comparison lacks raw tensor values",
        )
        ref, draft = pair["reference_values"], pair["draft_values"]
        _need(
            bool(ref)
            and len(ref) == len(draft)
            and all(
                isinstance(v, (int, float)) and math.isfinite(v) for v in ref + draft
            ),
            "DCP1 tensor arrays are empty, mismatched, or non-finite",
        )
        error = max(abs(float(a) - float(b)) for a, b in zip(ref, draft, strict=True))
        _contradiction(
            error <= oracle["atol"],
            "draft partial output exceeds DCP1 oracle tolerance",
        )
    acceptance = cast(list[Any], doc.get("acceptance_by_position"))
    _need(
        isinstance(acceptance, list) and acceptance,
        "per-position speculative acceptance absent",
    )
    _need(
        all(
            isinstance(x, dict)
            and _integer(x.get("position"))
            and _text(x.get("draft_token"))
            and _text(x.get("target_token"))
            and isinstance(x.get("accepted"), bool)
            for x in acceptance
        ),
        "acceptance-by-position raw tokens absent",
    )
    _contradiction(
        all(
            x["accepted"] is (x["draft_token"] == x["target_token"]) for x in acceptance
        ),
        "acceptance flags disagree with captured draft/target tokens",
    )
    headroom = _obj(
        doc.get("pretrim_headroom_case"), "separate pre-trim load/headroom case absent"
    )
    _need(
        headroom.get("separate_run") is True
        and _integer(headroom.get("peak_bytes"))
        and _integer(headroom.get("available_before_load_bytes"))
        and _text(headroom.get("load_log_sha256")),
        "pre-trim headroom case lacks separate raw memory/load evidence",
    )
    _contradiction(
        headroom["peak_bytes"] >= 0 and headroom["available_before_load_bytes"] >= 0,
        "pre-trim memory byte measurements are negative",
    )
    _contradiction(
        headroom["peak_bytes"] <= headroom["available_before_load_bytes"],
        "pre-trim observed peak exceeded available headroom",
    )
    _rollback(doc)


def _verify_fairness(doc: dict[str, Any]) -> None:
    req = _request_binding(doc)
    setup = _obj(doc.get("workload"), "workload definition absent")
    _need(
        setup.get("request_id") == req["request_id"]
        and setup.get("long_decode_tokens", 0) >= 8192
        and setup.get("concurrent_prefills") == 4
        and setup.get("dcp_size") == 4,
        "workload is not pinned DCP4 long decode plus four concurrent prefills",
    )
    variants = cast(list[dict[str, Any]], doc.get("scheduler_runs"))
    _need(
        isinstance(variants, list)
        and {x.get("mode") for x in variants if isinstance(x, dict)}
        == {"stock", "candidate"},
        "paired stock/candidate scheduler captures absent",
    )
    for variant in variants:
        samples = cast(list[dict[str, Any]], variant.get("decode_samples"))
        prefill_completions = cast(
            list[dict[str, Any]], variant.get("prefill_completions")
        )
        _need(
            isinstance(samples, list)
            and len(samples) >= 3
            and all(
                isinstance(x, dict)
                and _integer(x.get("generated_tokens"))
                and x["generated_tokens"] > 0
                and _positive_number(x.get("elapsed_seconds"))
                for x in samples
            ),
            "decode progress lacks raw token-count/time samples",
        )
        _need(
            isinstance(prefill_completions, list)
            and len(prefill_completions) == 4
            and all(x.get("finish_reason") == "stop" for x in prefill_completions),
            "all four prefill completions not observed",
        )
        _need(
            _positive_number(variant.get("max_decode_stall_seconds"))
            and _text(variant.get("output_sha256")),
            "stall or semantic-output trace absent",
        )
    candidate = next(x for x in variants if x["mode"] == "candidate")
    stock = next(x for x in variants if x["mode"] == "stock")
    cmin = min(
        x["generated_tokens"] / x["elapsed_seconds"]
        for x in candidate["decode_samples"]
    )
    smin = min(
        x["generated_tokens"] / x["elapsed_seconds"] for x in stock["decode_samples"]
    )
    _contradiction(cmin > 0, "candidate decode starved during prefill")
    _need(
        _obj(doc.get("correctness_oracle"), "quality/error oracle absent").get(
            "request_id"
        )
        == req["request_id"],
        "quality/error oracle not bound to request",
    )
    _contradiction(
        cmin >= smin
        or candidate["max_decode_stall_seconds"] < stock["max_decode_stall_seconds"],
        "candidate shows no measured fairness improvement over stock",
    )
    _rollback(doc)


def _xgrammar_request_contract(
    doc: dict[str, Any], row: dict[str, Any], req: dict[str, Any]
) -> dict[str, Any]:
    _need(
        _text(row.get("request_ref"))
        and isinstance(row.get("request_sha256"), str)
        and re.fullmatch(r"[0-9a-f]{64}", row["request_sha256"]) is not None,
        "xgrammar request sidecar reference/SHA-256 absent",
    )
    from tools.runtime_batch02_controls import _oracle_payload

    sidecar = _oracle_payload(
        doc, row["request_ref"], row["request_sha256"], "xgrammar request"
    )
    process = _obj(req.get("server_process"), "bound server process identity absent")
    for key in ("pid", "starttime_ticks"):
        _need(
            type(process.get(key)) is int and process[key] > 0,
            f"bound server process {key} absent or invalid",
        )
    _need(
        _sha256(process.get("image_digest")),
        "bound server process image digest absent or invalid",
    )
    _contradiction(
        process["image_digest"] == doc["subject"]["image_digest"],
        "bound request server image differs from subject image",
    )
    _contradiction(
        row.get("request_id") == req["request_id"]
        and sidecar.get("request_id") == req["request_id"]
        and type(sidecar.get("server_pid")) is int
        and sidecar["server_pid"] == process["pid"]
        and type(sidecar.get("server_starttime_ticks")) is int
        and sidecar["server_starttime_ticks"] == process["starttime_ticks"]
        and sidecar.get("server_image_digest") == process["image_digest"],
        "request bytes are not bound to this request id and serving process",
    )
    request_raw = sidecar.get("request_raw")
    _need(_text(request_raw), "xgrammar sidecar lacks raw OpenAI request bytes")
    request_raw = cast(str, request_raw)
    _contradiction(
        row.get("input_sha256")
        == "sha256:" + hashlib.sha256(request_raw.encode("utf-8")).hexdigest(),
        "request body bytes differ from their input SHA-256",
    )
    try:
        body = strict_json_loads(request_raw)
    except (json.JSONDecodeError, RecursionError) as exc:
        raise _Fail("captured xgrammar request body is invalid strict JSON") from exc
    _contradiction(isinstance(body, dict), "xgrammar request body is not an object")
    _contradiction(
        body.get("model") == req["model"] == doc["subject"]["model"],
        "xgrammar request model differs from bounded subject model",
    )
    stream_required = row["case"] in {
        "json_stream", "tool_stream", "parallel_tool", "tool_followup"
    }
    _contradiction(
        body.get("stream") is stream_required,
        "captured request stream mode differs from the test case",
    )
    messages = _xgrammar_messages(body)
    if row["case"] == "tool_followup":
        _validate_tool_followup_messages(messages)
    generation_budget = _xgrammar_generation_budget(body, req)
    if row["case"].startswith("json_"):
        response_format = body.get("response_format")
        _contradiction(
            isinstance(response_format, dict)
            and response_format.get("type") == "json_schema"
            and isinstance(response_format.get("json_schema"), dict),
            "JSON output request lacks response_format.json_schema",
        )
        json_schema = response_format["json_schema"]
        _contradiction(
            _text(json_schema.get("name"))
            and json_schema.get("strict") is True
            and isinstance(json_schema.get("schema"), dict),
            "request JSON response schema is not strict or lacks its schema body",
        )
        try:
            validate_schema(json_schema["schema"])
        except UnsupportedJsonSchema as exc:
            raise _Unknown(f"request JSON Schema unsupported: {exc}") from exc
        return {
            "body": body,
            "generation_budget": generation_budget,
            "json_schema": json_schema["schema"],
            "tool_schemas": {},
        }

    tools = body.get("tools")
    _contradiction(isinstance(tools, list) and bool(tools), "tool request lacks function schemas")
    tool_schemas: dict[str, dict[str, Any]] = {}
    for tool in tools:
        _contradiction(
            isinstance(tool, dict) and tool.get("type") == "function",
            "tool request contains a non-function tool",
        )
        function = tool.get("function")
        _contradiction(
            isinstance(function, dict)
            and _text(function.get("name"))
            and isinstance(function.get("parameters"), dict),
            "tool request function name or parameters schema absent",
        )
        function = cast(dict[str, Any], function)
        schema = cast(dict[str, Any], function["parameters"])
        try:
            validate_schema(schema)
        except UnsupportedJsonSchema as exc:
            raise _Unknown(f"request function schema unsupported: {exc}") from exc
        name = cast(str, function["name"])
        _contradiction(name not in tool_schemas, "request contains duplicate function names")
        tool_schemas[name] = schema
    return {
        "body": body,
        "generation_budget": generation_budget,
        "json_schema": None,
        "tool_schemas": tool_schemas,
    }


def _xgrammar_messages(body: dict[str, Any]) -> list[Any]:
    messages = body.get("messages")
    _contradiction(
        isinstance(messages, list)
        and bool(messages)
        and all(
            isinstance(message, dict)
            and message.get("role") in {"system", "developer", "user", "assistant", "tool"}
            and (
                _text(message.get("content"))
                or (
                    message.get("role") == "assistant"
                    and isinstance(message.get("tool_calls"), list)
                    and bool(message["tool_calls"])
                )
            )
            for message in messages
        )
        and any(message.get("role") == "user" for message in messages),
        "xgrammar request lacks valid OpenAI chat messages",
    )
    return cast(list[Any], messages)


def _xgrammar_generation_budget(body: dict[str, Any], req: dict[str, Any]) -> int:
    budget_keys = [
        key for key in ("max_completion_tokens", "max_tokens") if key in body
    ]
    _need(len(budget_keys) == 1, "request must carry exactly one explicit token budget")
    generation_budget = body[budget_keys[0]]
    _contradiction(
        type(generation_budget) is int
        and 0 < generation_budget <= req["max_tokens"]
        and generation_budget <= req["max_context_tokens"],
        "request token budget exceeds the bounded generation/context budget",
    )
    return cast(int, generation_budget)


def _validate_tool_followup_messages(messages: list[Any]) -> None:
    prior_calls = [
        call
        for message in messages
        if isinstance(message, dict) and message.get("role") == "assistant"
        for call in message.get("tool_calls", [])
        if isinstance(call, dict)
        and isinstance(call.get("id"), str)
        and isinstance(call.get("function"), dict)
    ]
    tool_results = [
        message
        for message in messages
        if isinstance(message, dict) and message.get("role") == "tool"
    ]
    _contradiction(
        bool(prior_calls)
        and bool(tool_results)
        and all(
            any(result.get("tool_call_id") == call["id"] for result in tool_results)
            for call in prior_calls
        ),
        "tool-followup request lacks matching prior tool-call/result messages",
    )


def _verify_xgrammar(doc: dict[str, Any]) -> None:
    req = _request_binding(doc)
    source_commit = doc.get("effective_source_commit")
    versions = _obj(
        doc["subject"].get("software_versions"),
        "subject software-version tuple absent",
    )
    _need(
        isinstance(source_commit, str)
        and re.fullmatch(r"[0-9a-f]{40}", source_commit) is not None
        and isinstance(versions.get("vllm_commit"), str)
        and re.fullmatch(r"[0-9a-f]{40}", versions["vllm_commit"]) is not None,
        "effective vLLM source commit must be pinned to a full git SHA",
    )
    source_commit = cast(str, source_commit)
    _contradiction(
        source_commit == versions["vllm_commit"],
        "effective source commit differs from the pinned vLLM source",
    )
    _validate_xgrammar_patch_state(doc)
    by_name = _xgrammar_cases(doc)
    required = set(by_name)
    for name in required - {"invalid_revision"}:
        row = by_name[name]
        request_contract = _xgrammar_request_contract(doc, row, req)
        _need(
            row.get("request_id") == req["request_id"]
            and type(row.get("http_status")) is int
            and row["http_status"] == 200
            and isinstance(row.get("chunks"), list)
            and _text(row.get("finish_reason"))
            and row.get("process_alive_after") is True
            and _text(row.get("raw_output")),
            f"raw HTTP/stream/process evidence absent for {name}",
        )
        if name in {"json_stream", "tool_stream", "parallel_tool", "tool_followup"}:
            parsed_capture = _sse_capture(row.get("sse_raw"), name)
            if name.startswith("tool_") or name in {"parallel_tool", "tool_followup"}:
                actual_calls = _sse_tool_calls(parsed_capture, name)
                expected_calls = cast(
                    list[dict[str, Any]], row.get("expected_tool_calls")
                )
                _need(
                    isinstance(expected_calls, list) and expected_calls,
                    f"tool fixture oracle absent for {name}",
                )
                _contradiction(
                    actual_calls == expected_calls,
                    f"streamed tool-call arguments differ from fixture oracle for {name}",
                )
                _contradiction(
                    _xgrammar_tool_calls_match(
                        actual_calls, request_contract["tool_schemas"]
                    ),
                    f"streamed tool arguments violate request schema for {name}",
                )
        raw_output = (
            _sse_content(row.get("sse_raw"), name)
            if name == "json_stream"
            else row["raw_output"]
        )
        if name.startswith("json_"):
            try:
                parsed = strict_json_loads(raw_output)
            except (json.JSONDecodeError, RecursionError) as exc:
                raise _Fail(f"JSON grammar parser rejected {name}: {exc}") from exc
            schema = request_contract["json_schema"]
            _need(isinstance(schema, dict), f"request JSON Schema absent for {name}")
            schema_matches = schema_value_matches(schema, parsed)
            _contradiction(
                schema_matches,
                f"JSON schema oracle failed for {name}",
            )
        elif name not in {"tool_stream", "parallel_tool", "tool_followup"}:
            calls = cast(list[dict[str, Any]], row.get("tool_calls"))
            _need(
                isinstance(calls, list) and calls,
                f"raw tool-call arguments absent for {name}",
            )
            actual_calls = []
            for call in calls:
                _need(
                    isinstance(call, dict)
                    and _text(call.get("name"))
                    and _text(call.get("arguments_json")),
                    f"malformed raw tool call for {name}",
                )
                try:
                    args = strict_json_loads(call["arguments_json"])
                except (json.JSONDecodeError, RecursionError) as exc:
                    raise _Fail(
                        f"tool arguments are invalid JSON for {name}: {exc}"
                    ) from exc
                _contradiction(
                    isinstance(args, dict),
                    f"tool arguments are not an object for {name}",
                )
                actual_calls.append({"name": call["name"], "arguments": args})
            expected_calls = cast(list[dict[str, Any]], row.get("expected_tool_calls"))
            _need(
                isinstance(expected_calls, list) and expected_calls,
                f"tool fixture oracle absent for {name}",
            )
            _contradiction(
                actual_calls == expected_calls,
                f"tool-call arguments differ from fixture oracle for {name}",
            )
            _contradiction(
                _xgrammar_tool_calls_match(
                    actual_calls, request_contract["tool_schemas"]
                ),
                f"tool arguments violate request schema for {name}",
            )
    _verify_xgrammar_invalid_revision(by_name["invalid_revision"], source_commit)
    _rollback(doc)


def _verify_xgrammar_invalid_revision(
    invalid: dict[str, Any], source_commit: str
) -> None:
    _need(
        type(invalid.get("http_status")) is int
        and invalid["http_status"] >= 400
        and _text(invalid.get("parser_error")),
        "incompatible revision negative control lacks HTTP/parser failure evidence",
    )
    _contradiction(
        invalid.get("rejected") is True
        and isinstance(invalid.get("source_commit"), str)
        and re.fullmatch(r"[0-9a-f]{40}", invalid["source_commit"]) is not None
        and invalid["source_commit"] != source_commit,
        "known incompatible source revision was not rejected",
    )


def _validate_xgrammar_patch_state(doc: dict[str, Any]) -> None:
    _need(
        doc.get("patch_state") in {"included", "absent", "reverted"},
        "effective source commit/patch state absent",
    )


def _xgrammar_cases(doc: dict[str, Any]) -> dict[str, dict[str, Any]]:
    cases = doc.get("cases")
    required = {
        "json_stream",
        "json_nonstream",
        "tool_stream",
        "tool_nonstream",
        "parallel_tool",
        "tool_followup",
        "invalid_revision",
    }
    _need(
        isinstance(cases, list)
        and {c.get("case") for c in cases if isinstance(c, dict)} == required,
        "structured-output case matrix incomplete",
    )
    return {c["case"]: c for c in cast(list[dict[str, Any]], cases)}


def _xgrammar_tool_calls_match(
    calls: list[dict[str, Any]], schemas: dict[str, dict[str, Any]]
) -> bool:
    if not calls:
        return False
    for call in calls:
        name = call.get("name")
        schema = schemas.get(name) if isinstance(name, str) else None
        arguments = call.get("arguments")
        if schema is None or not isinstance(arguments, dict):
            return False
        if not schema_value_matches(schema, arguments):
            return False
    return True


def _verify_dsv41(doc: dict[str, Any]) -> None:
    stop = _obj(doc.get("stop_capture"), "raw stop command capture absent")
    _need(
        _text(stop.get("script_sha256"))
        and isinstance(stop.get("argv"), list)
        and stop["argv"]
        and _text(stop.get("stdout_sha256"))
        and _integer(stop.get("exit_code")),
        "stop invocation/output is not auditable",
    )
    before = _obj(doc.get("containers_before"), "pre-stop container inventory absent")
    after = _obj(doc.get("containers_after"), "post-stop container inventory absent")
    exporter_ids = cast(list[str], before.get("nfs_exporter_ids"))
    _need(
        isinstance(exporter_ids, list)
        and exporter_ids
        and all(_text(x) for x in exporter_ids),
        "NFS exporter identity absent",
    )
    _contradiction(
        set(exporter_ids) <= set(cast(list[str], after.get("running_ids", []))),
        "stop operation removed an NFS exporter",
    )
    mounts = cast(list[dict[str, Any]], doc.get("mount_checks"))
    _need(
        isinstance(mounts, list)
        and mounts
        and all(
            isinstance(x, dict)
            and x.get("mount_id")
            and x.get("source")
            and x.get("mounted") is True
            for x in mounts
        ),
        "persistent mount/export checks absent",
    )
    pin = _obj(doc.get("image_pin"), "container tag-to-digest capture absent")
    _need(
        _text(pin.get("tag"))
        and _text(pin.get("expected_digest"))
        and _text(pin.get("observed_digest")),
        "image tag and resolved digest absent",
    )
    _contradiction(
        pin["expected_digest"] == pin["observed_digest"],
        "floating tag resolves to unexpected digest",
    )
    neg = _obj(doc.get("negative_control"), "unsafe tag/stop negative control absent")
    _need(
        neg.get("kind") == "tag_drift" and _text(neg.get("observed_digest")),
        "tag drift negative absent",
    )
    _contradiction(
        neg["observed_digest"] != pin["expected_digest"]
        and neg.get("gate_result") == "blocked",
        "tag drift control was not blocked",
    )
    _rollback(doc)


def _verify_dualspark(doc: dict[str, Any]) -> None:
    req = _request_binding(doc)
    hosts = _rows(doc.get("hosts"), 2, "OEM twin hosts")
    _need(
        all(
            h.get("oem_model") == doc["subject"]["oem"] and _text(h.get("serial_hash"))
            for h in hosts
        ),
        "two OEM hosts are not individually identified",
    )
    _contradiction(
        len({h["serial_hash"] for h in hosts}) == 2,
        "twin hosts resolve to same identity",
    )
    paths = cast(list[dict[str, Any]], doc.get("selected_paths"))
    _need(
        isinstance(paths, list) and len(paths) >= 2,
        "effective NCCL path per host absent",
    )
    for row in paths:
        _need(
            isinstance(row, dict)
            and _text(row.get("node_id"))
            and _text(row.get("hca"))
            and _text(row.get("interface"))
            and _text(row.get("ipv4"))
            and _integer(row.get("gid_index"))
            and _text(row.get("gid_value"))
            and _integer(row.get("mtu"))
            and _text(row.get("nccl_env_sha256")),
            "HCA/RoCE twin/IPv4/GID/MTU selection incomplete",
        )
        _contradiction(
            row["gid_value"] not in ("::", "0.0.0.0", "null"),
            "selected NCCL GID is null",
        )
    _contradiction(
        {x["node_id"] for x in paths} == {h["node_id"] for h in hosts},
        "selected path host mapping mismatch",
    )
    collective = _obj(doc.get("collective"), "same-path NCCL collective absent")
    _need(
        collective.get("request_id") == req["request_id"]
        and collective.get("selected_path_hash") == doc.get("selected_paths_sha256")
        and isinstance(collective.get("rank_exit_codes"), list)
        and len(collective["rank_exit_codes"]) >= 2,
        "collective not bound to captured paths/request",
    )
    _need(
        all(_integer(code) for code in collective["rank_exit_codes"]),
        "collective rank exit-code observations are malformed",
    )
    _contradiction(
        all(code == 0 for code in collective["rank_exit_codes"]),
        "collective failed on selected GID path",
    )
    infer = _obj(doc.get("first_inference"), "first inference on selected path absent")
    _need(
        infer.get("request_id") == req["request_id"]
        and infer.get("selected_path_hash") == doc.get("selected_paths_sha256")
        and _integer(infer.get("output_tokens"))
        and infer["output_tokens"] > 0,
        "first inference not tied to verified NCCL paths",
    )
    _contradiction(
        infer["output_tokens"] <= req["max_tokens"],
        "first inference exceeded the output-token ceiling",
    )
    recovery = _obj(doc.get("cold_recovery"), "cold recovery capture absent")
    _need(
        _text(recovery.get("before_state_sha256"))
        and _text(recovery.get("after_state_sha256"))
        and recovery.get("no_power_cycle") is True,
        "cold recovery evidence is absent or used an uncontrolled power cycle",
    )
    neg = _obj(doc.get("negative_control"), "null-GID negative control absent")
    _need(
        neg.get("kind") == "null_gid_twin" and _text(neg.get("gid_value")),
        "null GID control absent",
    )
    _contradiction(
        neg["gid_value"] in ("::", "0.0.0.0", "null")
        and neg.get("preflight_result") == "rejected",
        "null-GID twin control was not rejected",
    )
    _rollback(doc)


def _verify_glm52(doc: dict[str, Any]) -> None:
    req = _request_binding(doc)
    subject = doc["subject"]
    for key in ("tokenizer_digest", "template_digest", "engine_commit"):
        _need(_text(subject.get(key)), f"subject.{key} absent")
    cases = cast(list[dict[str, Any]], doc.get("conversation_cases"))
    _need(isinstance(cases, list) and cases, "raw GLM multi-turn cases absent")
    by_kind = {c.get("kind") for c in cases if isinstance(c, dict)}
    required = {
        "single_turn",
        "prefix_cache_growing",
        "structured_thinking_on",
        "structured_thinking_off",
        "reasoning_on",
        "reasoning_off",
        "required_tool_loop",
    }
    _need(
        required <= by_kind,
        "conversation/cache/structured/reasoning/tool-bound cases incomplete",
    )
    for case in cases:
        _need(
            case.get("request_id") == req["request_id"]
            and case.get("model") == subject["model"]
            and case.get("checkpoint_digest") == subject["checkpoint_digest"]
            and isinstance(case.get("turns"), list)
            and case["turns"],
            "conversation is not bound to request/checkpoint",
        )
        for turn in case["turns"]:
            _need(
                isinstance(turn, dict)
                and _integer(turn.get("turn_index"))
                and turn["turn_index"] >= 0
                and _text(turn.get("sse_raw"))
                and _integer(turn.get("prompt_tokens"))
                and turn["prompt_tokens"] >= 0
                and _integer(turn.get("completion_tokens"))
                and turn["completion_tokens"] > 0,
                "turn trace lacks raw SSE/token count observations",
            )
            _contradiction(
                turn["prompt_tokens"] <= req["max_context_tokens"]
                and turn["completion_tokens"] <= req["max_tokens"],
                "turn exceeded context or output-token ceiling",
            )
        _need(
            all(_text(t.get("expected_output")) for t in case["turns"]),
            "per-turn expected-output oracle absent",
        )
        for turn in case["turns"]:
            capture = _sse_capture(
                turn["sse_raw"], f"{case['kind']}/turn-{turn['turn_index']}"
            )
            finishes = [
                choice.get("finish_reason")
                for chunk in capture["chunks"]
                for choice in chunk["choices"]
                if choice.get("finish_reason") is not None
            ]
            _need(bool(finishes), "SSE finish reason missing")
            _contradiction(finishes == ["stop"], "SSE finish reason was not stop")
            output = _sse_content(
                turn["sse_raw"], f"{case['kind']}/turn-{turn['turn_index']}"
            )
            _contradiction(
                output == turn["expected_output"], "per-turn correctness oracle failure"
            )
    loop = next(c for c in cases if c["kind"] == "required_tool_loop")
    iteration_limit = cast(int, loop.get("configured_limit"))
    _need(
        _integer(loop.get("tool_iterations"))
        and _integer(iteration_limit)
        and iteration_limit > 0,
        "required-tool iteration bound absent",
    )
    _contradiction(
        loop["tool_iterations"] <= loop["configured_limit"]
        and loop.get("terminated_by_limit") is True,
        "required-tool loop exceeded its enforced limit",
    )
    ab = cast(list[dict[str, Any]], doc.get("recipe_ab"))
    _need(
        isinstance(ab, list)
        and {x.get("thinking") for x in ab if isinstance(x, dict)} == {True, False},
        "paired recipe sensitivity A/B missing",
    )
    for run in ab:
        _need(
            run.get("request_id") == req["request_id"]
            and _text(run.get("recipe_sha256"))
            and isinstance(run.get("raw_metrics"), dict)
            and _text(run.get("raw_metrics", {}).get("source_ref")),
            "recipe A/B raw metrics/provenance missing",
        )


_VALIDATORS: dict[str, Callable[[dict[str, Any]], None]] = {
    "DELTA-FORUM-3NODE-NCCL-IMAGE-AND-FIRST-REQUEST-01": _verify_3node,
    "DELTA-FORUM-8NODE-NCCL-INTERFACE-MTU-01": _verify_8node,
    "DELTA-FORUM-CROSS-TURN-SLEEPER-INJECTION-REGRESSION-01": _verify_sleeper,
    "DELTA-FORUM-DCP-MTP-DRAFT-CORRECTNESS-AND-PRETRIM-OOM-01": _verify_dcp,
    "DELTA-FORUM-DCP4-DECODE-STARVATION-FAIR-SCHEDULER-01": _verify_fairness,
    "DELTA-FORUM-DFLASH-XGRAMMAR-STRUCTURED-OUTPUT-REGRESSION-01": _verify_xgrammar,
    "DELTA-FORUM-DSV41-NFS-STOP-TAG-PIN-01": _verify_dsv41,
    "DELTA-FORUM-DUALSPARK-NCCL-GID-TWIN-AND-COLD-RECOVERY-01": _verify_dualspark,
    "DELTA-FORUM-GLM52-MULTITURN-CORRECTNESS-AND-RECIPE-SENSITIVITY-01": _verify_glm52,
}


def assess(card_id: str, raw_document: Any) -> dict[str, Any]:
    validator = _VALIDATORS.get(card_id)
    if validator is None:
        return {
            "status": "unknown",
            "could_not_run": 1,
            "reason": "no batch-01 validator for card",
        }
    try:
        doc = _capture(raw_document, card_id)
        validator(doc)
    except _Fail as exc:
        return {"status": "fail", "could_not_run": 0, "reason": str(exc)}
    except _Unknown as exc:
        return {"status": "unknown", "could_not_run": 1, "reason": str(exc)}
    except (KeyError, TypeError, ValueError, StopIteration, RecursionError) as exc:
        return {
            "status": "unknown",
            "could_not_run": 1,
            "reason": f"malformed raw record: {exc}",
        }
    return {
        "status": "pass",
        "could_not_run": 0,
        "reason": "raw domain measurements satisfy card predicates",
    }


def verify(card_id: str, path: Path | None = None) -> dict[str, Any]:
    p = path or EVIDENCE / card_id / "runtime-capture.json"
    if card_id not in _VALIDATORS:
        result = assess(card_id, {})
        result["files"] = [str(p)]
        return result
    try:
        encoded = read_regular_bytes(p, 4 * 1024 * 1024)
        if len(encoded) > 4 * 1024 * 1024:
            return {
                "status": "unknown",
                "could_not_run": 1,
                "reason": "raw capture exceeds 4 MiB safety bound",
                "files": [str(p)],
            }
        raw = strict_json_loads(encoded.decode("utf-8"))
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


def assert_evidence_pass(card_id: str) -> None:
    result = verify(card_id)
    assert result["status"] == "pass", (
        f"{card_id}: status={result['status']} could_not_run={result['could_not_run']} "
        f"reason={result['reason']} files={result.get('files', [])}"
    )
