"""Per-card raw evidence predicates for generated runtime closure batch 04."""

from __future__ import annotations

import ast
import hashlib
import json
import math
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, cast

from tools.capture_io import read_regular_bytes, strict_json_loads
from tools.runtime_batch01_controls import (
    EVIDENCE,
    _Fail,
    _Unknown,
    _capture,
    _contradiction,
    _need,
    _obj,
    _request_binding,
    _rollback,
    _sse_capture,
    _sse_content,
    _sse_tool_calls,
    _text,
)
from tools.runtime_batch02_controls import _oracle_payload

IDS = {
    "DELTA-ROOT-DSML-PARSER-RECOVERY-BOUNDARY-01",
    "DELTA-ROOT-GLM53-QUEUED-REQUEST-PROGRESS-GATE-01",
    "DELTA-ROOT-MIMO-OVERLAY-AND-PREFILL-FAIRNESS-01",
    "DELTA-ROOT-MIMO-PATCH-SUPERSESSION-GATE-01",
    "DELTA-ROOT-RAY-MULTIENGINE-RANK-PROGRESS-01",
    "DELTA-ROOT-RECIPE-MEMORY-UNKNOWN-AND-RAW-EVIDENCE-01",
    "DELTA-ROOT-TOKENIZER-PATCH-SEMANTIC-GATE-01",
    "DELTA-ROOT-TRITON-ALLOCATOR-PATCH-STATE-GATE-01",
}


def _integer(value: Any) -> bool:
    return type(value) is int


def _finite_nonnegative(value: Any) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
        and value >= 0
    )


def _when(value: Any, what: str) -> datetime:
    _need(_text(value), f"{what} timestamp absent")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (ValueError, TypeError) as exc:
        raise _Unknown(f"{what} timestamp malformed") from exc
    _need(parsed.tzinfo is not None, f"{what} timestamp has no UTC offset")
    return parsed


def _versions(doc: dict[str, Any], keys: tuple[str, ...]) -> None:
    versions = _obj(
        doc["subject"].get("software_versions"), "pinned software stack absent"
    )
    _need(
        all(_text(versions.get(k)) for k in keys),
        f"pinned stack incomplete: {', '.join(keys)}",
    )


def _sha_matches(raw: str, digest: Any) -> bool:
    return (
        isinstance(digest, str)
        and hashlib.sha256(raw.encode("utf-8")).hexdigest() == digest
    )


def _manifest_artifact_digest(doc: dict[str, Any], artifact_ref: Any) -> str:
    _need(_text(artifact_ref), "manifest artifact byte reference absent")
    relative = Path(artifact_ref)
    _need(
        not relative.is_absolute() and ".." not in relative.parts,
        "manifest artifact reference escapes card evidence",
    )
    path = EVIDENCE / doc["card_id"] / "artifacts" / relative
    try:
        content = read_regular_bytes(path, 4 * 1024 * 1024)
    except OSError as exc:
        raise _Unknown(f"manifest artifact bytes unavailable: {exc}") from exc
    _need(len(content) <= 4 * 1024 * 1024, "manifest artifact exceeds 4 MiB")
    return hashlib.sha256(content).hexdigest()


def _dsml(doc: dict[str, Any]) -> None:
    req = _request_binding(doc)
    _versions(doc, ("runtime", "parser", "tokenizer"))
    cases = _rows(doc.get("parser_cases"), 5, "streaming/full parser cases")
    required = {
        "reasoning_incomplete",
        "truncated_arguments",
        "tool_choice_none",
        "quoted_tool_marker",
        "complete_tool",
    }
    _need(
        {row.get("case") for row in cases if isinstance(row, dict)} == required,
        "parser case set incomplete",
    )
    for row in cases:
        _need(
            isinstance(row, dict)
            and row.get("request_id") == req["request_id"]
            and isinstance(row.get("stream_raw"), str)
            and isinstance(row.get("complete_raw"), str)
            and _text(row.get("oracle_ref"))
            and _text(row.get("oracle_sha256")),
            "raw streaming/full response or independent oracle absent",
        )
        oracle = _oracle_payload(
            doc, row["oracle_ref"], row["oracle_sha256"], "DSML parser"
        )
        for field in ("stream_raw", "complete_raw"):
            capture = _sse_capture(row[field], "DSML parser")
            text = _sse_content(row[field], "DSML parser")
            deltas = [
                delta
                for chunk in capture["chunks"]
                for choice in chunk["choices"]
                for delta in (choice.get("tool_calls_delta") or [])
            ]
            calls = _sse_tool_calls(capture, "DSML parser") if deltas else []
            expected = oracle.get(field)
            _need(
                isinstance(expected, dict)
                and isinstance(expected.get("text"), str)
                and isinstance(expected.get("tool_calls"), list),
                "independent parser oracle malformed",
            )
            expected = cast(dict[str, Any], expected)
            _contradiction(
                text == expected["text"] and calls == expected["tool_calls"],
                f"{row['case']} parsed text/tool calls differ from oracle",
            )
            if row["case"] in {
                "reasoning_incomplete",
                "truncated_arguments",
                "tool_choice_none",
                "quoted_tool_marker",
            }:
                _contradiction(
                    not calls, f"{row['case']} produced a spurious tool invocation"
                )
            if row["case"] == "complete_tool":
                _contradiction(bool(calls), "complete tool response was lost by parser")
    _rollback(doc)


def _rows(value: Any, minimum: int, label: str) -> list[Any]:
    _need(isinstance(value, list) and len(value) >= minimum, f"{label} raw rows absent")
    return cast(list[Any], value)


def _glm_queue(doc: dict[str, Any]) -> None:
    _request_binding(doc)
    _versions(doc, ("runtime", "scheduler", "model"))
    runs = _rows(
        doc.get("request_stage_samples"), 2, "active and queued request samples"
    )
    seen: dict[str, list[tuple[datetime, int, int, str]]] = {}
    kv: list[float] = []
    for row in runs:
        _need(
            isinstance(row, dict)
            and _text(row.get("request_id"))
            and _text(row.get("stage"))
            and _finite_nonnegative(row.get("kv_used_fraction"))
            and row["kv_used_fraction"] <= 1
            and _integer(row.get("prefill_tokens_total"))
            and _integer(row.get("decode_tokens_total")),
            "per-request stage/counter/KV observation malformed",
        )
        _need(
            row["prefill_tokens_total"] >= 0 and row["decode_tokens_total"] >= 0,
            "token counters must be nonnegative",
        )
        seen.setdefault(row["request_id"], []).append(
            (
                _when(row.get("timestamp"), "request stage"),
                row["prefill_tokens_total"],
                row["decode_tokens_total"],
                row["stage"],
            )
        )
        kv.append(cast(float, row["kv_used_fraction"]))
    _need(
        len(seen) >= 2
        and any(
            any(s[3] == "decode" and s[2] > 0 for s in obs) for obs in seen.values()
        ),
        "no independently progressing active request observed",
    )
    stalled = progressing = False
    threshold = doc.get("queue_stall_seconds")
    threshold = cast(float, threshold)
    _need(
        _finite_nonnegative(threshold) and threshold > 0,
        "bounded queue stall threshold absent",
    )
    _need(
        threshold <= doc["request_bounds"]["deadline_seconds"],
        "queue stall detector exceeds the bounded request deadline",
    )
    for obs in seen.values():
        obs.sort()
        if len(obs) < 2:
            continue
        duration = (obs[-1][0] - obs[0][0]).total_seconds()
        made_prefill = obs[-1][1] > obs[0][1]
        made_decode = obs[-1][2] > obs[0][2]
        stalled |= duration >= threshold and not made_prefill and not made_decode
        progressing |= made_prefill or made_decode
    _contradiction(
        stalled and progressing and max(kv) < 0.99,
        "did not distinguish a blocked queued request from slow progress at low KV use",
    )
    _rollback(doc)


def _mimo_overlay(doc: dict[str, Any]) -> None:
    req = _request_binding(doc)
    _versions(doc, ("runtime", "draft", "tokenizer", "overlay"))
    target_nodes = _rows(doc.get("target_nodes"), 2, "target node manifest identities")
    _need(
        all(_text(node) for node in target_nodes)
        and len(set(target_nodes)) == len(target_nodes),
        "target node identities are absent or duplicated",
    )
    files = _rows(doc.get("effective_manifest"), 1, "resolved overlay/draft manifest")
    roles = {"image", "checkpoint", "overlay", "draft", "tokenizer", "modifications"}
    observed: set[tuple[str, str]] = set()
    for item in files:
        _need(
            isinstance(item, dict)
            and item.get("node_id") in target_nodes
            and item.get("role") in roles
            and _text(item.get("logical_path"))
            and _text(item.get("resolved_path"))
            and re.fullmatch(r"[0-9a-f]{64}", str(item.get("declared_sha256")))
            is not None
            and re.fullmatch(r"[0-9a-f]{64}", str(item.get("actual_sha256")))
            is not None
            and _text(item.get("resolution_raw")),
            "resolved manifest lacks file identities and SHA-256",
        )
        _need(
            (item["node_id"], item["role"]) not in observed,
            "duplicate node artifact role",
        )
        observed.add((item["node_id"], item["role"]))
        _contradiction(
            item["declared_sha256"] == item["actual_sha256"],
            "overlay/draft manifest hash or symlink target mismatch",
        )
        _contradiction(
            item["logical_path"] in item["resolution_raw"]
            and item["resolved_path"] in item["resolution_raw"],
            "raw path-resolution output does not bind logical and resolved paths",
        )
        if item["role"] == "image":
            _contradiction(
                item["actual_sha256"]
                == doc["subject"]["image_digest"].removeprefix("sha256:"),
                "node image manifest differs from subject image digest",
            )
        elif item["role"] == "checkpoint":
            _contradiction(
                item["actual_sha256"]
                == doc["subject"]["checkpoint_digest"].removeprefix("sha256:"),
                "node checkpoint manifest differs from subject checkpoint digest",
            )
        else:
            _contradiction(
                _manifest_artifact_digest(doc, item.get("artifact_ref"))
                == item["actual_sha256"],
                f"{item['role']} manifest hash differs from captured artifact bytes",
            )
    _need(
        observed == {(node, role) for node in target_nodes for role in roles},
        "effective manifest lacks an image/checkpoint/overlay/draft/tokenizer/modification row per node",
    )
    negative = _obj(
        doc.get("missing_overlay_control"), "missing overlay control absent"
    )
    _need(
        _text(negative.get("path"))
        and _integer(negative.get("exit_code"))
        and _text(negative.get("stderr_raw")),
        "missing-overlay command result absent",
    )
    _contradiction(
        negative["exit_code"] != 0 and "missing" in negative["stderr_raw"].lower(),
        "missing overlay was not rejected before serving",
    )
    modality = _obj(
        doc.get("unsupported_modality_control"), "unsupported modality control absent"
    )
    _need(
        _text(modality.get("modality"))
        and _integer(modality.get("exit_code"))
        and _text(modality.get("stderr_raw")),
        "unsupported modality result absent",
    )
    _contradiction(
        modality["exit_code"] != 0, "unvalidated modality was advertised as successful"
    )
    _need(
        req["request_id"] == doc["prefill_decode_canary"].get("request_id"),
        "fairness canary request differs",
    )
    _fairness(doc["prefill_decode_canary"])
    semantic = _obj(doc.get("semantic_canary"), "real modality semantic canary absent")
    _need(
        semantic.get("request_id") == req["request_id"]
        and _text(semantic.get("raw_output"))
        and _text(semantic.get("oracle_ref"))
        and _text(semantic.get("oracle_sha256")),
        "semantic canary/request/oracle identity absent",
    )
    oracle = _oracle_payload(
        doc, semantic["oracle_ref"], semantic["oracle_sha256"], "MiMo semantic"
    )
    _contradiction(
        semantic["raw_output"] == oracle.get("expected_output"),
        "MiMo semantic canary differs from independent oracle",
    )
    _rollback(doc)


def _fairness(canary: Any) -> None:
    canary = _obj(canary, "prefill/decode canary absent")
    samples = _rows(canary.get("samples"), 2, "per-request fairness samples")
    by_req: dict[str, list[tuple[datetime, int, int]]] = {}
    for row in samples:
        _need(
            isinstance(row, dict)
            and _text(row.get("request_id"))
            and _integer(row.get("prefill_tokens"))
            and _integer(row.get("decode_tokens"))
            and row["prefill_tokens"] >= 0
            and row["decode_tokens"] >= 0,
            "fairness sample counters malformed",
        )
        by_req.setdefault(row["request_id"], []).append(
            (
                _when(row.get("timestamp"), "fairness sample"),
                row["prefill_tokens"],
                row["decode_tokens"],
            )
        )
    _need(len(by_req) >= 2, "concurrent prefill/decode requests absent")
    _contradiction(
        all(
            len(seq) >= 2
            and all(seq[i][0] < seq[i + 1][0] for i in range(len(seq) - 1))
            for seq in by_req.values()
        ),
        "fairness samples are not strictly chronological/repeated per request",
    )
    intervals = [(seq[0][0], seq[-1][0]) for seq in by_req.values()]
    _contradiction(
        max(start for start, _ in intervals) < min(end for _, end in intervals),
        "prefill and decode observations are not concurrent",
    )
    _contradiction(
        any(seq[-1][1] > seq[0][1] for seq in by_req.values())
        and any(seq[-1][2] > seq[0][2] for seq in by_req.values()),
        "long-prefill and short-decode did not both progress",
    )


def _patch_supersession(doc: dict[str, Any]) -> None:
    _request_binding(doc)
    _versions(doc, ("runtime", "patch_target_commit", "patch_source_commit"))
    rows = _rows(doc.get("patch_cases"), 2, "affected and refactored patch cases")
    states: dict[str, dict[str, Any]] = {}
    for row in rows:
        _need(
            isinstance(row, dict)
            and row.get("case") in {"affected", "superseded"}
            and _text(row.get("source_raw"))
            and isinstance(row.get("patch_raw"), str)
            and _text(row.get("target_symbol"))
            and _integer(row.get("apply_exit_code"))
            and _sha_matches(row["source_raw"], row.get("source_sha256"))
            and _sha_matches(row["patch_raw"], row.get("patch_sha256"))
            and re.fullmatch(r"[0-9a-f]{40}", str(row.get("source_commit")))
            is not None,
            "patch/source applicability capture incomplete",
        )
        _need(row["case"] not in states, "duplicate patch case")
        states[row["case"]] = row
    _need(
        set(states) == {"affected", "superseded"},
        "affected and superseded revisions required",
    )
    affected, superseded = states["affected"], states["superseded"]
    _contradiction(
        affected["target_symbol"] in affected["source_raw"]
        and affected["target_symbol"] in affected["patch_raw"]
        and affected["apply_exit_code"] == 0,
        "patch does not apply to the pinned affected symbol",
    )
    _contradiction(
        superseded["target_symbol"] not in superseded["source_raw"]
        and superseded["apply_exit_code"] != 0,
        "superseded patch was not rejected against refactored source",
    )
    modalities = _rows(
        doc.get("modality_canaries"), 2, "text and announced modality canaries"
    )
    for row in modalities:
        _need(
            isinstance(row, dict)
            and _text(row.get("modality"))
            and _text(row.get("raw_output"))
            and _integer(row.get("exit_code"))
            and _text(row.get("oracle_ref"))
            and _text(row.get("oracle_sha256")),
            "modality canary result/oracle absent",
        )
        oracle = _oracle_payload(
            doc, row["oracle_ref"], row["oracle_sha256"], "modality canary"
        )
        _contradiction(
            row["exit_code"] == 0
            and row["raw_output"] == oracle.get("expected_output"),
            f"advertised modality {row['modality']} failed semantic oracle",
        )
    _need(
        {x["modality"] for x in modalities} >= {"text", "audio"},
        "text/audio capability canaries absent",
    )
    _rollback(doc)


def _ray_engines(doc: dict[str, Any]) -> None:
    _request_binding(doc)
    _versions(doc, ("ray", "nccl", "executor"))
    engines = _rows(doc.get("engines"), 2, "two engine identity/resource records")
    _need(
        len({x.get("engine_id") for x in engines if isinstance(x, dict)})
        == len(engines),
        "engine identities collide",
    )
    progressed: set[str] = set()
    stalled: set[str] = set()
    for engine in engines:
        _need(
            isinstance(engine, dict)
            and _text(engine.get("engine_id"))
            and _text(engine.get("image_digest"))
            and _finite_nonnegative(engine.get("gpu_budget"))
            and engine["gpu_budget"] > 0,
            "engine effective image/resource tuple absent",
        )
        samples = _rows(engine.get("rank_samples"), 2, "per-rank collective samples")
        by_rank: dict[int, list[tuple[datetime, int]]] = {}
        for row in samples:
            _need(
                isinstance(row, dict)
                and _integer(row.get("rank"))
                and _integer(row.get("collective_sequence"))
                and row["rank"] >= 0
                and row["collective_sequence"] >= 0,
                "collective rank/sequence malformed",
            )
            by_rank.setdefault(row["rank"], []).append(
                (_when(row.get("timestamp"), "collective"), row["collective_sequence"])
            )
        _need(by_rank, "rank observations absent")
        made_progress = all(
            len(seq) >= 2 and seq[-1][0] > seq[0][0] and seq[-1][1] > seq[0][1]
            for seq in by_rank.values()
        )
        progressed.add(engine["engine_id"]) if made_progress else stalled.add(
            engine["engine_id"]
        )
    _contradiction(
        len(progressed) == 1 and len(stalled) == 1,
        "fixture must identify exactly one progressing and one stalled engine",
    )
    ab = _rows(doc.get("executor_ab_runs"), 2, "effective Ray/MP executor A/B")
    _need(
        {row.get("executor") for row in ab if isinstance(row, dict)} == {"ray", "mp"},
        "A/B executor modes absent",
    )
    for run in ab:
        _need(
            isinstance(run, dict)
            and run.get("request_id") == doc["request_bounds"]["request_id"]
            and _integer(run.get("exit_code"))
            and _text(run.get("raw_output"))
            and _integer(run.get("rank_count"))
            and run["rank_count"] >= 1,
            "executor A/B request/result/rank capture incomplete",
        )
        _contradiction(run["exit_code"] == 0, "executor A/B failed")
    _rollback(doc)


def _recipe_memory(doc: dict[str, Any]) -> None:
    _request_binding(doc)
    _versions(doc, ("runtime", "recipe_digest", "backend"))
    profiles = _rows(
        doc.get("memory_profiles"), 2, "measured memory profile and unknown control"
    )
    states = set()
    for profile in profiles:
        _need(
            isinstance(profile, dict)
            and _text(profile.get("case"))
            and _text(profile.get("classification"))
            and isinstance(profile.get("components"), dict),
            "memory profile malformed",
        )
        states.add(profile["case"])
        components = profile["components"]
        required = {
            "weights",
            "kv",
            "staging",
            "graphs",
            "draft",
            "buffers",
            "host_reserve",
        }
        _need(set(components) == required, "memory profile component vector incomplete")
        unknown = any(value is None for value in components.values())
        if unknown:
            _contradiction(
                profile["classification"] == "unknown",
                "unknown memory component was reported as safely fitting",
            )
            _need(_text(profile.get("raw_reason")), "unknown memory reason absent")
        else:
            _need(
                all(_finite_nonnegative(value) for value in components.values()),
                "memory component measurement invalid",
            )
            total = sum(components.values())
            _need(
                _finite_nonnegative(profile.get("available_bytes")),
                "available memory measurement absent",
            )
            expected = "fit" if total <= profile["available_bytes"] else "exceeds"
            _contradiction(
                profile["classification"] == expected,
                "memory admission disagrees with measured components",
            )
    _need(
        {"unknown_kv", "measured_fit"} <= states,
        "unknown-KV and measured-fit cases required",
    )
    workload = _rows(doc.get("workload_samples"), 2, "post-warmup raw workload samples")
    _need(
        workload[0].get("stage") == "warmup"
        and workload[-1].get("stage") == "inference",
        "workload must contain warmup then measured inference",
    )
    samples = []
    for row in workload:
        _need(
            isinstance(row, dict)
            and row.get("request_id") == doc["request_bounds"]["request_id"]
            and _integer(row.get("completed_tokens"))
            and row["completed_tokens"] >= 0
            and _text(row.get("raw_output")),
            "workload request/token/output capture incomplete",
        )
        samples.append(
            (_when(row.get("timestamp"), "recipe workload"), row["completed_tokens"])
        )
    _contradiction(
        samples == sorted(samples)
        and samples[-1][0] > samples[0][0]
        and samples[-1][1] > samples[0][1],
        "post-warmup workload has no causal token progress",
    )
    _rollback(doc)


def _tokenizer(doc: dict[str, Any]) -> None:
    req = _request_binding(doc)
    _versions(
        doc, ("runtime", "tokenizer_revision", "tokenizer_digest", "patch_digest")
    )
    cases = _rows(
        doc.get("tokenizer_cases"), 6, "affected/fixed long text/image/tool cases"
    )
    required = {
        "old_text",
        "fixed_text",
        "image_below_limit",
        "image_above_limit",
        "affected_image_above_limit",
        "harmony_tool",
    }
    _need(
        {x.get("case") for x in cases if isinstance(x, dict)} >= required,
        "tokenizer control cases incomplete",
    )
    for row in cases:
        _need(
            isinstance(row, dict)
            and _text(row.get("case"))
            and _text(row.get("raw_input"))
            and _text(row.get("raw_output"))
            and isinstance(row.get("sentinels"), list)
            and all(_text(value) for value in row["sentinels"]),
            "tokenizer raw sentinel capture incomplete",
        )
        sentinels = cast(list[str], row["sentinels"])
        expected = sum(row["raw_input"].count(value) for value in sentinels)
        observed = sum(row["raw_output"].count(value) for value in sentinels)
        if row["case"] in {"old_text", "affected_image_above_limit"}:
            _contradiction(
                observed < expected,
                "affected tokenizer negative did not reproduce sentinel truncation",
            )
        else:
            _contradiction(observed == expected, "fixed tokenizer lost prompt sentinel")
    _need(
        any(x.get("request_id") == req["request_id"] for x in cases),
        "tokenizer cases are not bound to request",
    )
    soak = _rows(doc.get("mx_fp4_candidate_soak"), 2, "candidate MXFP4 soak requests")
    for run in soak:
        _need(
            isinstance(run, dict)
            and _text(run.get("request_id"))
            and _text(run.get("raw_output"))
            and _integer(run.get("exit_code"))
            and _text(run.get("finish_reason"))
            and _text(run.get("oracle_ref"))
            and _text(run.get("oracle_sha256")),
            "candidate MXFP4 raw generation result incomplete",
        )
        oracle = _oracle_payload(
            doc, run["oracle_ref"], run["oracle_sha256"], "MXFP4 candidate soak"
        )
        _contradiction(
            run["exit_code"] == 0
            and run["finish_reason"] == "stop"
            and run["raw_output"] == oracle.get("expected_output"),
            "candidate MXFP4 soak request failed",
        )
    _rollback(doc)


def _triton_patch_states(doc: dict[str, Any]) -> None:
    cases = _rows(
        doc.get("patch_state_cases"),
        3,
        "missing/applied/superseded allocator patch states",
    )
    seen = set()
    for row in cases:
        _need(
            isinstance(row, dict)
            and row.get("state") in {"missing", "applied", "superseded"}
            and _text(row.get("source_raw"))
            and isinstance(row.get("patch_raw"), str)
            and _text(row.get("symbol"))
            and _integer(row.get("apply_exit_code"))
            and _sha_matches(row["source_raw"], row.get("source_sha256"))
            and _sha_matches(row["patch_raw"], row.get("patch_sha256")),
            "allocator patch state record malformed",
        )
        seen.add(row["state"])
        in_source = row["symbol"] in row["source_raw"]
        in_patch = row["symbol"] in row["patch_raw"]
        valid = {
            "missing": in_source and not in_patch and row["apply_exit_code"] != 0,
            "applied": in_source and in_patch and row["apply_exit_code"] == 0,
            "superseded": not in_source and in_patch and row["apply_exit_code"] != 0,
        }[row["state"]]
        _contradiction(
            valid,
            f"{row['state']} patch state disagrees with captured source/apply result",
        )
    _need(
        seen == {"missing", "applied", "superseded"},
        "all patch state controls required",
    )


def _triton_lifetime_canaries(doc: dict[str, Any]) -> None:
    ranks = _rows(doc.get("lifetime_canaries"), 4, "allocator stream/lifetime canaries")
    observed: set[tuple[int, int]] = set()
    for row in ranks:
        _need(
            isinstance(row, dict)
            and _integer(row.get("rank"))
            and _integer(row.get("thread_id"))
            and _text(row.get("allocation_id"))
            and isinstance(row.get("events"), list)
            and type(row.get("exit_code")) is int
            and _text(row.get("raw_output"))
            and re.fullmatch(r"[0-9a-f]{64}", str(row.get("output_sha256"))) is not None
            and _sha_matches(row["raw_output"], row.get("output_sha256")),
            "rank/thread lifetime canary record incomplete",
        )
        _contradiction(
            row["exit_code"] == 0, "allocator candidate failed cold/warm canary"
        )
        events = _rows(row["events"], 4, "allocation/enqueue/complete/release events")
        _need(
            [event.get("event") for event in events if isinstance(event, dict)]
            == ["allocate", "enqueue", "complete", "release"],
            "lifetime trace must capture allocation, enqueue, consumer completion, and release",
        )
        parsed = []
        for event in events:
            _need(
                isinstance(event, dict)
                and _text(event.get("stream_id"))
                and event.get("allocation_id") == row["allocation_id"]
                and _integer(event.get("live_references"))
                and _integer(event.get("allocated_bytes")),
                "raw allocation/stream/lifetime counters malformed",
            )
            _need(
                event["live_references"] >= 0 and event["allocated_bytes"] >= 0,
                "negative live-reference/allocation counter",
            )
            parsed.append(
                (_when(event.get("timestamp"), "allocator lifetime event"), event)
            )
        _contradiction(
            all(parsed[i][0] < parsed[i + 1][0] for i in range(3)),
            "allocator lifetime events are not strictly causal",
        )
        _contradiction(
            all(
                parsed[i][1]["stream_id"] == parsed[i + 1][1]["stream_id"]
                for i in range(3)
            )
            and parsed[1][1]["live_references"] > 0
            and parsed[2][1]["live_references"] > 0
            and parsed[3][1]["live_references"] == 0
            and parsed[0][1]["allocated_bytes"] > 0
            and parsed[1][1]["allocated_bytes"] == parsed[0][1]["allocated_bytes"]
            and parsed[2][1]["allocated_bytes"] == parsed[0][1]["allocated_bytes"]
            and parsed[3][1]["allocated_bytes"] == 0,
            "storage lifetime/stream ownership failed before async consumer completion",
        )
        requests = _rows(
            row.get("generation_requests"), 2, "cold/warm prefix canary requests"
        )
        modes: dict[str, dict[str, Any]] = {}
        for request in requests:
            _need(
                isinstance(request, dict)
                and request.get("mode") in {"cold", "warm"}
                and request.get("request_id") == doc["request_bounds"]["request_id"]
                and _text(request.get("prompt_sha256"))
                and _text(request.get("raw_output"))
                and _text(request.get("finish_reason"))
                and type(request.get("exit_code")) is int
                and _finite_nonnegative(request.get("latency_ms"))
                and _integer(request.get("prefix_hit_tokens"))
                and request["prefix_hit_tokens"] >= 0
                and _text(request.get("oracle_ref"))
                and _text(request.get("oracle_sha256")),
                "cold/warm semantic request record malformed",
            )
            _need(request["mode"] not in modes, "duplicate cold/warm request mode")
            oracle = _oracle_payload(
                doc,
                request["oracle_ref"],
                request["oracle_sha256"],
                "allocator generation",
            )
            _contradiction(
                request["exit_code"] == 0
                and request["finish_reason"] == "stop"
                and request["raw_output"] == oracle.get("expected_output"),
                "cold/warm allocator generation differs from independent semantic oracle",
            )
            modes[request["mode"]] = request
        _need(
            set(modes) == {"cold", "warm"},
            "cold and warm allocator requests are both required",
        )
        _contradiction(
            modes["cold"]["prompt_sha256"] == modes["warm"]["prompt_sha256"]
            and modes["cold"]["raw_output"] == modes["warm"]["raw_output"]
            and modes["cold"]["prefix_hit_tokens"] == 0
            and modes["warm"]["prefix_hit_tokens"] > 0,
            "warm prefix hit changed answer or was not measured against a cold run",
        )
        observed.add((row["rank"], row["thread_id"]))
    _need(
        {(rank, thread) for rank in (0, 1) for thread in (0, 1)} <= observed,
        "stream/lifetime evidence lacks each target rank/thread pair",
    )


def _triton_source_audit(doc: dict[str, Any]) -> None:
    audit = _obj(doc.get("patch_audit"), "allocator monkeypatch source audit absent")
    _need(
        _text(audit.get("source_path"))
        and _text(audit.get("source_raw"))
        and _sha_matches(audit["source_raw"], audit.get("source_sha256")),
        "allocator source audit hash mismatch",
    )
    _contradiction(
        re.search(r"except\s+Exception\s*:\s*pass", audit["source_raw"]) is None,
        "allocator patch hides failures with broad silent exception",
    )
    try:
        tree = ast.parse(audit["source_raw"])
    except SyntaxError as exc:
        raise _Fail("allocator artifact is not executable Python source") from exc
    cls = next(
        (
            node
            for node in tree.body
            if isinstance(node, ast.ClassDef) and node.name == "NullAllocator"
        ),
        None,
    )
    _contradiction(
        cls is not None,
        "effective source has no executable NullAllocator implementation",
    )
    cls = cast(ast.ClassDef, cls)
    call_method = next(
        (
            node
            for node in cls.body
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            and node.name == "__call__"
        ),
        None,
    )
    _contradiction(
        call_method is not None,
        "NullAllocator has no executable allocation implementation",
    )
    call_method = cast(ast.FunctionDef | ast.AsyncFunctionDef, call_method)
    calls = [node for node in ast.walk(call_method) if isinstance(node, ast.Call)]
    alloc_call = next(
        (
            node
            for node in calls
            if ast.unparse(node.func).endswith("caching_allocator_alloc")
        ),
        None,
    )
    _need(
        alloc_call is not None
        and any(keyword.arg == "stream" for keyword in alloc_call.keywords),
        "allocator does not allocate on the caller's explicit stream",
    )
    retained = any(
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "append"
        and isinstance(node.func.value, ast.Attribute)
        and isinstance(node.func.value.value, ast.Name)
        and node.func.value.value.id == "self"
        for node in ast.walk(call_method)
    )
    _need(
        retained,
        "allocator does not retain live storage through asynchronous consumers",
    )
    _need(
        _text(audit.get("source_revision"))
        and re.fullmatch(r"[0-9a-f]{40}", audit["source_revision"]) is not None,
        "allocator source revision is not pinned",
    )


def _triton_allocator(doc: dict[str, Any]) -> None:
    _request_binding(doc)
    _versions(doc, ("runtime", "triton", "ray", "patch_commit"))
    _triton_patch_states(doc)
    _triton_lifetime_canaries(doc)
    _triton_source_audit(doc)
    _rollback(doc)


_VALIDATORS: dict[str, Callable[[dict[str, Any]], None]] = {
    "DELTA-ROOT-DSML-PARSER-RECOVERY-BOUNDARY-01": _dsml,
    "DELTA-ROOT-GLM53-QUEUED-REQUEST-PROGRESS-GATE-01": _glm_queue,
    "DELTA-ROOT-MIMO-OVERLAY-AND-PREFILL-FAIRNESS-01": _mimo_overlay,
    "DELTA-ROOT-MIMO-PATCH-SUPERSESSION-GATE-01": _patch_supersession,
    "DELTA-ROOT-RAY-MULTIENGINE-RANK-PROGRESS-01": _ray_engines,
    "DELTA-ROOT-RECIPE-MEMORY-UNKNOWN-AND-RAW-EVIDENCE-01": _recipe_memory,
    "DELTA-ROOT-TOKENIZER-PATCH-SEMANTIC-GATE-01": _tokenizer,
    "DELTA-ROOT-TRITON-ALLOCATOR-PATCH-STATE-GATE-01": _triton_allocator,
}


def assess(card_id: str, raw_document: Any) -> dict[str, Any]:
    validator = _VALIDATORS.get(card_id)
    if validator is None:
        return {
            "status": "unknown",
            "could_not_run": 1,
            "reason": "no batch-04 predicate",
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
        "reason": "batch-04 raw predicates satisfied",
    }


def verify(card_id: str, path: Path | None = None) -> dict[str, Any]:
    capture = path or EVIDENCE / card_id / "runtime-capture.json"
    if card_id not in _VALIDATORS:
        result = assess(card_id, {})
        result["files"] = [str(capture)]
        return result
    try:
        content = read_regular_bytes(capture, 4 * 1024 * 1024)
        if len(content) > 4 * 1024 * 1024:
            return {
                "status": "unknown",
                "could_not_run": 1,
                "reason": "capture exceeds 4 MiB",
                "files": [str(capture)],
            }
        raw = strict_json_loads(content.decode("utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError, RecursionError) as exc:
        return {
            "status": "unknown",
            "could_not_run": 1,
            "reason": f"raw capture unavailable: {exc}",
            "files": [str(capture)],
        }
    result = assess(card_id, raw)
    result["files"] = [str(capture)]
    return result
