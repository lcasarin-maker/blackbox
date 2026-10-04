"""Raw-domain fixtures for batch 04; these tests never substitute for runtime captures."""

from __future__ import annotations

import copy
import hashlib
import json
from typing import Any

import pytest

from tools import runtime_batch04_controls as controls
from tools import runtime_batch02_controls as oracle_controls
from tools.runtime_batch01_controls import _sse_capture, _sse_content, _sse_tool_calls
from test_runtime_batch02_controls import _base, _sse, _tool_sse


def _dsml() -> dict[str, Any]:
    card = "DELTA-ROOT-DSML-PARSER-RECOVERY-BOUNDARY-01"
    doc = _base(card)
    doc["subject"]["software_versions"].update(
        {"runtime": "runtime-1", "parser": "parser-1", "tokenizer": "tokenizer-1"}
    )
    doc["parser_cases"] = []
    for case in (
        "reasoning_incomplete",
        "truncated_arguments",
        "tool_choice_none",
        "quoted_tool_marker",
        "complete_tool",
    ):
        raw = _tool_sse() if case == "complete_tool" else _sse("plain")
        capture = _sse_capture(raw, "fixture")
        deltas = [
            delta
            for chunk in capture["chunks"]
            for choice in chunk["choices"]
            for delta in (choice.get("tool_calls_delta") or [])
        ]
        expected = {
            "text": _sse_content(raw, "fixture"),
            "tool_calls": _sse_tool_calls(capture, "fixture") if deltas else [],
        }
        doc["parser_cases"].append(
            {
                "case": case,
                "request_id": "req-1",
                "stream_raw": raw,
                "complete_raw": raw,
                "oracle_ref": f"{case}.json",
                "oracle_sha256": "",
                "_oracle": expected,
            }
        )
    return doc


def _glm() -> dict[str, Any]:
    doc = _base("DELTA-ROOT-GLM53-QUEUED-REQUEST-PROGRESS-GATE-01")
    doc["subject"]["software_versions"].update(
        {"runtime": "runtime-1", "scheduler": "scheduler-1", "model": "model-x"}
    )
    doc["queue_stall_seconds"] = 10
    doc["request_stage_samples"] = (
        [
            {
                "request_id": "active",
                "stage": "decode",
                "timestamp": f"2026-10-03T00:00:{s:02d}Z",
                "prefill_tokens_total": 10,
                "decode_tokens_total": n,
                "kv_used_fraction": 0.37,
            }
            for s, n in ((0, 1), (11, 2))
        ]
        + [
            {
                "request_id": "queued",
                "stage": "prefill",
                "timestamp": f"2026-10-03T00:00:{s:02d}Z",
                "prefill_tokens_total": 0,
                "decode_tokens_total": 0,
                "kv_used_fraction": 0.37,
            }
            for s in (0, 11)
        ]
        + [
            {
                "request_id": "short-lifetime",
                "stage": "queued",
                "timestamp": "2026-10-03T00:00:05Z",
                "prefill_tokens_total": 0,
                "decode_tokens_total": 0,
                "kv_used_fraction": 0.37,
            }
        ]
    )
    return doc


def _mimo() -> dict[str, Any]:
    doc = _base("DELTA-ROOT-MIMO-OVERLAY-AND-PREFILL-FAIRNESS-01")
    doc["subject"]["software_versions"].update(
        {
            "runtime": "runtime-1",
            "draft": "draft-1",
            "tokenizer": "tokenizer-1",
            "overlay": "overlay-1",
        }
    )
    manifest = []
    for node in ("spark-0", "spark-1"):
        for role in (
            "image",
            "checkpoint",
            "overlay",
            "draft",
            "tokenizer",
            "modifications",
        ):
            if role == "image":
                digest = doc["subject"]["image_digest"].removeprefix("sha256:")
                artifact_ref = None
            elif role == "checkpoint":
                digest = doc["subject"]["checkpoint_digest"].removeprefix("sha256:")
                artifact_ref = None
            else:
                artifact_ref = f"{node}-{role}.bin"
                digest = hashlib.sha256(f"{node}:{role}".encode()).hexdigest()
            logical = f"/mnt/{role}"
            resolved = f"/evidence/{node}/{role}"
            manifest.append(
                {
                    "node_id": node,
                    "role": role,
                    "logical_path": logical,
                    "resolved_path": resolved,
                    "resolution_raw": f"{logical} -> {resolved}",
                    "declared_sha256": digest,
                    "actual_sha256": digest,
                    "artifact_ref": artifact_ref,
                }
            )
    doc.update(
        {
            "target_nodes": ["spark-0", "spark-1"],
            "effective_manifest": manifest,
            "missing_overlay_control": {
                "path": "absent",
                "exit_code": 1,
                "stderr_raw": "missing file",
            },
            "unsupported_modality_control": {
                "modality": "audio",
                "exit_code": 1,
                "stderr_raw": "unsupported modality",
            },
            "semantic_canary": {
                "request_id": "req-1",
                "raw_output": "semantic answer",
                "oracle_ref": "semantic.json",
                "oracle_sha256": "",
            },
            "prefill_decode_canary": {
                "request_id": "req-1",
                "samples": [
                    {
                        "request_id": "prefill",
                        "timestamp": f"2026-10-03T00:00:0{s}Z",
                        "prefill_tokens": n,
                        "decode_tokens": 0,
                    }
                    for s, n in ((0, 1), (1, 2))
                ]
                + [
                    {
                        "request_id": "decode",
                        "timestamp": f"2026-10-03T00:00:0{s}Z",
                        "prefill_tokens": 1,
                        "decode_tokens": n,
                    }
                    for s, n in ((0, 1), (1, 2))
                ],
            },
        }
    )
    return doc


def _patch() -> dict[str, Any]:
    doc = _base("DELTA-ROOT-MIMO-PATCH-SUPERSESSION-GATE-01")
    doc["subject"]["software_versions"].update(
        {
            "runtime": "runtime-1",
            "patch_target_commit": "1" * 40,
            "patch_source_commit": "2" * 40,
        }
    )
    doc["patch_cases"] = [
        {
            "case": "affected",
            "source_raw": "def target_symbol(): pass",
            "patch_raw": "target_symbol",
            "target_symbol": "target_symbol",
            "apply_exit_code": 0,
            "source_sha256": hashlib.sha256(b"def target_symbol(): pass").hexdigest(),
            "patch_sha256": hashlib.sha256(b"target_symbol").hexdigest(),
            "source_commit": "1" * 40,
        },
        {
            "case": "superseded",
            "source_raw": "def refactored(): pass",
            "patch_raw": "target_symbol",
            "target_symbol": "target_symbol",
            "apply_exit_code": 1,
            "source_sha256": hashlib.sha256(b"def refactored(): pass").hexdigest(),
            "patch_sha256": hashlib.sha256(b"target_symbol").hexdigest(),
            "source_commit": "2" * 40,
        },
    ]
    doc["modality_canaries"] = [
        {
            "modality": x,
            "raw_output": "ok",
            "exit_code": 0,
            "oracle_ref": f"{x}.json",
            "oracle_sha256": "",
        }
        for x in ("text", "audio")
    ]
    return doc


def _ray() -> dict[str, Any]:
    doc = _base("DELTA-ROOT-RAY-MULTIENGINE-RANK-PROGRESS-01")
    doc["subject"]["software_versions"].update(
        {"ray": "ray-1", "nccl": "nccl-1", "executor": "executor-1"}
    )
    doc["engines"] = [
        {
            "engine_id": "good",
            "image_digest": "sha256:" + "a" * 64,
            "gpu_budget": 1,
            "rank_samples": [
                {
                    "rank": 0,
                    "collective_sequence": n,
                    "timestamp": f"2026-10-03T00:00:0{i}Z",
                }
                for i, n in ((0, 1), (1, 2))
            ],
        },
        {
            "engine_id": "stuck",
            "image_digest": "sha256:" + "b" * 64,
            "gpu_budget": 1,
            "rank_samples": [
                {
                    "rank": 0,
                    "collective_sequence": 4,
                    "timestamp": f"2026-10-03T00:00:0{i}Z",
                }
                for i in (0, 1)
            ],
        },
    ]
    doc["executor_ab_runs"] = [
        {
            "executor": mode,
            "request_id": "req-1",
            "exit_code": 0,
            "raw_output": "answer",
            "rank_count": 2,
        }
        for mode in ("ray", "mp")
    ]
    return doc


def _memory() -> dict[str, Any]:
    doc = _base("DELTA-ROOT-RECIPE-MEMORY-UNKNOWN-AND-RAW-EVIDENCE-01")
    doc["subject"]["software_versions"].update(
        {
            "runtime": "runtime-1",
            "recipe_digest": "sha256:" + "a" * 64,
            "backend": "backend-1",
        }
    )
    names = ("weights", "kv", "staging", "graphs", "draft", "buffers", "host_reserve")
    doc["memory_profiles"] = [
        {
            "case": "unknown_kv",
            "classification": "unknown",
            "components": {k: (None if k == "kv" else 10) for k in names},
            "raw_reason": "KV estimate unavailable",
        },
        {
            "case": "measured_fit",
            "classification": "fit",
            "components": {k: 10 for k in names},
            "available_bytes": 1000,
        },
    ]
    doc["workload_samples"] = [
        {
            "request_id": "req-1",
            "stage": stage,
            "timestamp": f"2026-10-03T00:00:0{i}Z",
            "completed_tokens": n,
            "raw_output": "answer",
        }
        for i, stage, n in ((0, "warmup", 1), (1, "inference", 2))
    ]
    doc.update({"rollback_digest": "sha256:" + "c" * 64})
    return doc


def _tokenizer() -> dict[str, Any]:
    doc = _base("DELTA-ROOT-TOKENIZER-PATCH-SEMANTIC-GATE-01")
    doc["subject"]["software_versions"].update(
        {
            "runtime": "runtime-1",
            "tokenizer_revision": "r1",
            "tokenizer_digest": "sha256:" + "a" * 64,
            "patch_digest": "sha256:" + "b" * 64,
        }
    )
    cases = (
        ("old_text", 8, 3),
        ("fixed_text", 8, 8),
        ("image_below_limit", 4, 4),
        ("image_above_limit", 8, 8),
        ("affected_image_above_limit", 8, 4),
        ("harmony_tool", 4, 4),
    )
    doc["tokenizer_cases"] = [
        {
            "case": c,
            "request_id": "req-1",
            "raw_input": "S1 S2",
            "raw_output": "S1" if actual < expected else "S1 S2",
            "sentinels": ["S1", "S2"],
        }
        for c, expected, actual in cases
    ]
    doc["mx_fp4_candidate_soak"] = [
        {
            "request_id": f"req-{n}",
            "raw_output": "answer",
            "exit_code": 0,
            "finish_reason": "stop",
            "oracle_ref": f"soak-{n}.json",
            "oracle_sha256": "",
        }
        for n in (1, 2)
    ]
    return doc


def _triton() -> dict[str, Any]:
    doc = _base("DELTA-ROOT-TRITON-ALLOCATOR-PATCH-STATE-GATE-01")
    doc["subject"]["software_versions"].update(
        {
            "runtime": "runtime-1",
            "triton": "3.5.0",
            "ray": "ray-1",
            "patch_commit": "3" * 40,
        }
    )
    doc["patch_state_cases"] = [
        {
            "state": "missing",
            "source_raw": "symbol",
            "patch_raw": "",
            "symbol": "symbol",
            "apply_exit_code": 1,
            "source_sha256": hashlib.sha256(b"symbol").hexdigest(),
            "patch_sha256": hashlib.sha256(b"").hexdigest(),
        },
        {
            "state": "applied",
            "source_raw": "symbol",
            "patch_raw": "symbol",
            "symbol": "symbol",
            "apply_exit_code": 0,
            "source_sha256": hashlib.sha256(b"symbol").hexdigest(),
            "patch_sha256": hashlib.sha256(b"symbol").hexdigest(),
        },
        {
            "state": "superseded",
            "source_raw": "refactored",
            "patch_raw": "symbol",
            "symbol": "symbol",
            "apply_exit_code": 1,
            "source_sha256": hashlib.sha256(b"refactored").hexdigest(),
            "patch_sha256": hashlib.sha256(b"symbol").hexdigest(),
        },
    ]
    code = """class NullAllocator:
    def __init__(self):
        self._live = []
    def __call__(self, size, stream):
        storage = torch.cuda.caching_allocator_alloc(size, stream=stream)
        self._live.append(storage)
        return storage
"""
    doc["patch_audit"] = {
        "source_path": "patch.py",
        "source_raw": code,
        "source_sha256": hashlib.sha256(code.encode()).hexdigest(),
        "source_revision": "4" * 40,
    }
    doc["lifetime_canaries"] = []
    for rank in (0, 1):
        for thread in (0, 1):
            doc["lifetime_canaries"].append(
                {
                    "rank": rank,
                    "thread_id": thread,
                    "allocation_id": f"alloc-{rank}-{thread}",
                    "exit_code": 0,
                    "raw_output": "answer",
                    "output_sha256": hashlib.sha256(b"answer").hexdigest(),
                    "events": [
                        {
                            "event": name,
                            "timestamp": f"2026-10-03T00:00:0{i}Z",
                            "allocation_id": f"alloc-{rank}-{thread}",
                            "stream_id": "stream-1",
                            "live_references": refs,
                            "allocated_bytes": 64 if refs else 0,
                        }
                        for i, (name, refs) in enumerate(
                            (
                                ("allocate", 1),
                                ("enqueue", 1),
                                ("complete", 1),
                                ("release", 0),
                            )
                        )
                    ],
                }
            )
            doc["lifetime_canaries"][-1]["generation_requests"] = [
                {
                    "mode": mode,
                    "request_id": "req-1",
                    "prompt_sha256": "b" * 64,
                    "raw_output": "answer",
                    "finish_reason": "stop",
                    "exit_code": 0,
                    "latency_ms": 12.0,
                    "prefix_hit_tokens": 0 if mode == "cold" else 8,
                    "oracle_ref": f"allocator-{rank}-{thread}-{mode}.json",
                    "oracle_sha256": "",
                }
                for mode in ("cold", "warm")
            ]
    return doc


def _write_manifest_artifact_bytes(doc: dict[str, Any], root: Any) -> None:
    artifacts = root / doc["card_id"] / "artifacts"
    for item in doc.get("effective_manifest", []):
        if item.get("artifact_ref"):
            artifacts.mkdir(parents=True, exist_ok=True)
            (artifacts / item["artifact_ref"]).write_bytes(
                f"{item['node_id']}:{item['role']}".encode()
            )


_CASES = [
    (
        _dsml,
        lambda d: d["parser_cases"][3].update(complete_raw=_sse("<tool>mock</tool>")),
        "parsed text/tool calls differ",
    ),
    (
        _glm,
        lambda d: d["request_stage_samples"][3].update(prefill_tokens_total=1),
        "did not distinguish",
    ),
    (
        _mimo,
        lambda d: d["prefill_decode_canary"]["samples"][1].update(
            timestamp="2026-10-03T00:00:00Z"
        ),
        "strictly chronological",
    ),
    (
        _mimo,
        lambda d: d["effective_manifest"][2].update(
            declared_sha256="e" * 64, actual_sha256="e" * 64
        ),
        "manifest hash differs from captured artifact bytes",
    ),
    (
        _patch,
        lambda d: d["patch_cases"][1].update(apply_exit_code=0),
        "superseded patch was not rejected",
    ),
    (
        _ray,
        lambda d: d["engines"][0]["rank_samples"][1].update(collective_sequence=1),
        "exactly one progressing",
    ),
    (
        _memory,
        lambda d: d["memory_profiles"][0].update(classification="fit"),
        "unknown memory component",
    ),
    (
        _tokenizer,
        lambda d: d["tokenizer_cases"][1].update(raw_output="S1"),
        "fixed tokenizer lost prompt sentinel",
    ),
    (
        _triton,
        lambda d: d["patch_audit"].update(
            source_raw="# NullAllocator caching_allocator_alloc",
            source_sha256=hashlib.sha256(
                b"# NullAllocator caching_allocator_alloc"
            ).hexdigest(),
        ),
        "executable NullAllocator",
    ),
]


@pytest.mark.parametrize("factory,mutate,reason", _CASES)
def test_batch04_domain_fixture_passes_then_one_raw_criterion_fails(
    factory: Any, mutate: Any, reason: str, tmp_path: Any, monkeypatch: Any
) -> None:
    valid = factory()
    if "parser_cases" in valid:
        root = tmp_path / "evidence"
        sidecars = root / valid["card_id"] / "oracles"
        sidecars.mkdir(parents=True)
        monkeypatch.setattr(controls, "EVIDENCE", root)
        monkeypatch.setattr(oracle_controls, "EVIDENCE", root)
        for row in valid["parser_cases"]:
            payload = {
                "stream_raw": {
                    "text": row["_oracle"]["text"],
                    "tool_calls": row["_oracle"]["tool_calls"],
                },
                "complete_raw": {
                    "text": row["_oracle"]["text"],
                    "tool_calls": row["_oracle"]["tool_calls"],
                },
            }
            raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
            row["oracle_sha256"] = hashlib.sha256(raw).hexdigest()
            (sidecars / row["oracle_ref"]).write_bytes(raw)
            del row["_oracle"]
    if (
        "modality_canaries" in valid
        or "mx_fp4_candidate_soak" in valid
        or "semantic_canary" in valid
        or "lifetime_canaries" in valid
    ):
        root = tmp_path / "evidence"
        sidecars = root / valid["card_id"] / "oracles"
        sidecars.mkdir(parents=True)
        monkeypatch.setattr(controls, "EVIDENCE", root)
        monkeypatch.setattr(oracle_controls, "EVIDENCE", root)
        _write_manifest_artifact_bytes(valid, root)
        for row in valid.get("modality_canaries", []):
            raw = json.dumps(
                {"expected_output": row["raw_output"]},
                sort_keys=True,
                separators=(",", ":"),
            ).encode()
            row["oracle_sha256"] = hashlib.sha256(raw).hexdigest()
            (sidecars / row["oracle_ref"]).write_bytes(raw)
        for row in valid.get("mx_fp4_candidate_soak", []):
            raw = json.dumps(
                {"expected_output": row["raw_output"]},
                sort_keys=True,
                separators=(",", ":"),
            ).encode()
            row["oracle_sha256"] = hashlib.sha256(raw).hexdigest()
            (sidecars / row["oracle_ref"]).write_bytes(raw)
        if "semantic_canary" in valid:
            row = valid["semantic_canary"]
            raw = json.dumps(
                {"expected_output": row["raw_output"]},
                sort_keys=True,
                separators=(",", ":"),
            ).encode()
            row["oracle_sha256"] = hashlib.sha256(raw).hexdigest()
            (sidecars / row["oracle_ref"]).write_bytes(raw)
        for canary in valid.get("lifetime_canaries", []):
            for row in canary["generation_requests"]:
                raw = json.dumps(
                    {"expected_output": row["raw_output"]},
                    sort_keys=True,
                    separators=(",", ":"),
                ).encode()
                row["oracle_sha256"] = hashlib.sha256(raw).hexdigest()
                (sidecars / row["oracle_ref"]).write_bytes(raw)
    baseline = controls.assess(valid["card_id"], valid)
    assert baseline["status"] == "pass", baseline
    bad = copy.deepcopy(valid)
    mutate(bad)
    result = controls.assess(bad["card_id"], bad)
    assert result["status"] == "fail" and reason in result["reason"], result


def test_mimo_missing_artifact_bytes_are_unknown_after_positive_baseline(
    tmp_path: Any, monkeypatch: Any
) -> None:
    doc = _mimo()
    root = tmp_path / "evidence"
    sidecars = root / doc["card_id"] / "oracles"
    artifacts = root / doc["card_id"] / "artifacts"
    sidecars.mkdir(parents=True)
    artifacts.mkdir(parents=True)
    monkeypatch.setattr(controls, "EVIDENCE", root)
    monkeypatch.setattr(oracle_controls, "EVIDENCE", root)
    semantic = json.dumps(
        {"expected_output": doc["semantic_canary"]["raw_output"]},
        sort_keys=True,
        separators=(",", ":"),
    ).encode()
    doc["semantic_canary"]["oracle_sha256"] = hashlib.sha256(semantic).hexdigest()
    (sidecars / doc["semantic_canary"]["oracle_ref"]).write_bytes(semantic)
    for item in doc["effective_manifest"]:
        if item.get("artifact_ref"):
            raw = f"{item['node_id']}:{item['role']}".encode()
            (artifacts / item["artifact_ref"]).write_bytes(raw)
    baseline = controls.assess(doc["card_id"], doc)
    assert baseline["status"] == "pass", baseline
    (artifacts / doc["effective_manifest"][2]["artifact_ref"]).unlink()
    result = controls.assess(doc["card_id"], doc)
    assert (
        result["status"] == "unknown"
        and "artifact bytes unavailable" in result["reason"]
    ), result


def test_unknown_timestamp_and_missing_stack_become_unknown_after_positive_baseline() -> (
    None
):
    valid = _glm()
    assert controls.assess(valid["card_id"], valid)["status"] == "pass"
    bad_time = copy.deepcopy(valid)
    bad_time["request_stage_samples"][0]["timestamp"] = "bad-timestamp"
    result = controls.assess(bad_time["card_id"], bad_time)
    assert result["status"] == "unknown" and "timestamp malformed" in result["reason"]
    bad_stack = copy.deepcopy(valid)
    del bad_stack["subject"]["software_versions"]["scheduler"]
    result = controls.assess(bad_stack["card_id"], bad_stack)
    assert (
        result["status"] == "unknown" and "pinned stack incomplete" in result["reason"]
    )


def test_non_executable_allocator_artifact_fails_after_positive_baseline(
    tmp_path: Any, monkeypatch: Any
) -> None:
    valid = _triton()
    root = tmp_path / "evidence"
    sidecars = root / valid["card_id"] / "oracles"
    sidecars.mkdir(parents=True)
    monkeypatch.setattr(controls, "EVIDENCE", root)
    monkeypatch.setattr(oracle_controls, "EVIDENCE", root)
    for canary in valid["lifetime_canaries"]:
        for row in canary["generation_requests"]:
            raw = json.dumps(
                {"expected_output": row["raw_output"]},
                sort_keys=True,
                separators=(",", ":"),
            ).encode()
            row["oracle_sha256"] = hashlib.sha256(raw).hexdigest()
            (sidecars / row["oracle_ref"]).write_bytes(raw)
    assert controls.assess(valid["card_id"], valid)["status"] == "pass"
    bad = copy.deepcopy(valid)
    bad["patch_audit"]["source_raw"] = "def ("
    bad["patch_audit"]["source_sha256"] = hashlib.sha256(b"def (").hexdigest()
    result = controls.assess(bad["card_id"], bad)
    assert (
        result["status"] == "fail"
        and "not executable Python source" in result["reason"]
    )


def test_verify_default_capture_path_and_json_syntax_unknown(
    tmp_path: Any, monkeypatch: Any
) -> None:
    doc = _glm()
    root = tmp_path / "evidence"
    capture = root / doc["card_id"] / "runtime-capture.json"
    capture.parent.mkdir(parents=True)
    capture.write_text(json.dumps(doc), encoding="utf-8")
    monkeypatch.setattr(controls, "EVIDENCE", root)
    assert controls.verify(doc["card_id"])["status"] == "pass"
    capture.write_text("{", encoding="utf-8")
    result = controls.verify(doc["card_id"])
    assert (
        result["status"] == "unknown" and "raw capture unavailable" in result["reason"]
    )
    capture.write_text("[" * 3000 + "0" + "]" * 3000, encoding="utf-8")
    recursive = controls.verify(doc["card_id"])
    assert (
        recursive["status"] == "unknown"
        and "capture root must be a JSON object" in recursive["reason"]
    )


def test_assess_unknown_id_and_unexpected_shape_are_cnr(monkeypatch: Any) -> None:
    assert controls.assess("unknown-card", {})["status"] == "unknown"
    monkeypatch.setattr(
        controls,
        "_capture",
        lambda _raw, _card: (_ for _ in ()).throw(AttributeError("bad shape")),
    )
    result = controls.assess("DELTA-ROOT-GLM53-QUEUED-REQUEST-PROGRESS-GATE-01", {})
    assert result["status"] == "unknown" and "malformed raw record" in result["reason"]


def test_verify_rejects_oversized_capture(tmp_path: Any) -> None:
    huge = tmp_path / "oversized.json"
    huge.write_bytes(b" " * (4 * 1024 * 1024 + 1))
    result = controls.verify("DELTA-ROOT-GLM53-QUEUED-REQUEST-PROGRESS-GATE-01", huge)
    assert result["status"] == "unknown" and "exceeds 4 MiB" in result["reason"]


@pytest.mark.parametrize("card", sorted(controls.IDS))
def test_real_capture_close_gate_requires_runtime_evidence(card: str) -> None:
    result = controls.verify(card)
    assert result["status"] == "pass", (
        f"{card}: status={result['status']} could_not_run={result['could_not_run']} "
        f"reason={result['reason']} files={result.get('files', [])}"
    )
