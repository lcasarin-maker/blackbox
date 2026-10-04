"""Batch-03 raw predicate fixtures. They validate controls, never close lab cards."""

from __future__ import annotations

import copy
import hashlib
import json
from typing import Any

import pytest

from tools import runtime_batch03_controls as controls
from tools import runtime_batch02_controls as oracle_controls
from test_runtime_batch02_controls import _base, _tool_sse


def _mtp_request_raw() -> str:
    return json.dumps(
        {
            "model": "model-x",
            "messages": [
                {"role": "system", "content": "Use the supplied function tool."},
                {"role": "user", "content": "Call mock with ok set to true."},
            ],
            "tools": [
                {
                    "type": "function",
                    "function": {
                        "name": "mock",
                        "description": "Return the requested boolean.",
                        "parameters": {
                            "type": "object",
                            "properties": {"ok": {"type": "boolean"}},
                            "required": ["ok"],
                            "additionalProperties": False,
                        },
                    },
                }
            ],
            "tool_choice": {"type": "function", "function": {"name": "mock"}},
            "max_tokens": 8,
        },
        sort_keys=True,
        separators=(",", ":"),
    )


def _long_stop() -> dict[str, Any]:
    card = "DELTA-FORUM-QWEN-LONG-AGENT-STOP-01"
    doc = _base(card)
    doc["soak_runs"] = [
        {
            "checkpoint_digest": f"sha256:{n * 64}",
            "checkpoint_variant": variant,
            "task_state_raw": "open",
            "turns": [
                {
                    "request_id": f"req-{n}",
                    "task_state_raw": "open",
                    "tool_call_count": 0,
                    "finish_reason": "stop",
                    "operator_resume_event": "resume",
                    "mutating_call_replay_count": 0,
                },
                {
                    "request_id": f"req-{n}-continue",
                    "task_state_raw": "open",
                    "tool_call_count": 1,
                    "finish_reason": "tool_calls",
                    "mutating_call_replay_count": 0,
                },
                {
                    "request_id": f"req-{n}-done",
                    "task_state_raw": "complete",
                    "tool_call_count": 1,
                    "finish_reason": "stop",
                    "mutating_call_replay_count": 0,
                },
            ],
        }
        for n, variant in (("a", "nvidia_nvfp4"), ("b", "alternative"))
    ]
    return doc


def _mtp_parser() -> dict[str, Any]:
    card = "DELTA-FORUM-QWEN-MTP-PARSER-CANCEL-STATE-CHECK-01"
    doc = _base(card)
    request_raw = _mtp_request_raw()
    input_sha = "sha256:" + hashlib.sha256(request_raw.encode()).hexdigest()
    stack_binding = {
        "oem": doc["subject"].get("oem"),
        "host_id": doc["subject"].get("host_id"),
        "image_digest": doc["subject"].get("image_digest"),
        "model": doc["subject"].get("model"),
        "checkpoint_digest": doc["subject"].get("checkpoint_digest"),
        "vllm": "vllm-1",
        "parser": "parser-1",
        "tokenizer": "tokenizer-1",
        "request_sha256": input_sha.removeprefix("sha256:"),
    }
    profile_hash = hashlib.sha256(
        json.dumps(stack_binding, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    events = []
    for phase, second, pid, generation, call_no in (
        ("before_cancel", 1, 100, 1, 1),
        ("cancel", 2, 100, 1, 1),
        ("after_cancel", 3, 100, 1, 2),
        ("after_restart", 4, 101, 2, 3),
    ):
        run_label = "cancel"
        request_id = f"http-{run_label}-{call_no}"
        response_id = f"completion-{run_label}-{call_no}"
        events.append(
            {
                "phase": phase,
                "server_pid": pid,
                "process_generation": generation,
                "logical_request_id": "req-1",
                "request_id": request_id,
                "response_id": response_id,
                "model": "model-x",
                "checkpoint_digest": doc["subject"]["checkpoint_digest"],
                "input_sha256": input_sha,
                "http_status": 200,
                "finish_reason": "tool_calls"
                if phase in {"after_cancel", "after_restart"}
                else None,
                "exit_code": 0,
                "timestamp": f"2026-10-03T00:00:0{second}Z",
                "action_raw": "cancel generation"
                if phase == "cancel"
                else ("cancel_not_requested" if phase == "cancel" else None),
                "cancel_exit_code": 0 if phase == "cancel" else None,
                "sse_raw": _tool_sse(completion_id=response_id, usage=True),
            }
        )
    events[0]["sse_raw"] = _tool_sse(
        completion_id=events[0]["response_id"], usage=True
    ).split("data: {", 1)[1]
    events[0]["sse_raw"] = (
        "data: {" + events[0]["sse_raw"].split("\n\ndata: {", 1)[0] + "\n\n"
    )
    doc["admission_profile"] = {
        "stack_binding_sha256": profile_hash,
        "admitted": [
            {
                "parser": "xml",
                "mtp_tokens": 1,
                "parser_revision": "parser-1",
                "vllm_revision": "vllm-1",
            }
        ],
    }
    doc["subject"]["software_versions"]["mtp_tokens"] = "1"
    doc["matrix_runs"] = []
    for cancel in (False, True):
        run_events = copy.deepcopy(events)
        run_label = "cancel" if cancel else "control"
        for event in run_events:
            call_no = 1 if event["phase"] in {"before_cancel", "cancel"} else (
                2 if event["phase"] == "after_cancel" else 3
            )
            response_id = f"completion-{run_label}-{call_no}"
            event["request_id"] = f"http-{run_label}-{call_no}"
            event["response_id"] = response_id
            if event["sse_raw"]:
                event["sse_raw"] = event["sse_raw"].replace(
                    '"id": "completion-cancel-', f'"id": "completion-{run_label}-'
                )
                event["sse_raw"] = event["sse_raw"].replace(
                    '"id": "completion-control-', f'"id": "completion-{run_label}-'
                )
        if not cancel:
            run_events[1]["action_raw"] = "cancel_not_requested"
            run_events[1]["cancel_exit_code"] = None
        doc["matrix_runs"].append(
            {
                "parser": "xml",
                "mtp_tokens": 1,
                "cancel_midstream": cancel,
                "request_id": "req-1",
                "oracle_ref": f"xml-{cancel}.json",
                "oracle_sha256": "",
                "request_ref": f"request-{cancel}.json",
                "request_sha256": "",
                "parser_revision": "parser-1",
                "vllm_revision": "vllm-1",
                "input_sha256": input_sha,
                "events": run_events,
            }
        )
    doc["unsupported_combinations"] = [
        {
            "parser": "xml",
            "mtp_tokens": 3,
            "argv_raw": "launch --parser xml --mtp 3",
            "exit_code": 1,
            "stderr_raw": "typed tool call malformed",
        }
    ]
    return doc


def _oomd() -> dict[str, Any]:
    card = "DELTA-FORUM-QWEN-SERVICE-OOMD-CACHE-FAIL-01"
    doc = _base(card)
    doc.update(
        {
            "pressure_series": [
                {
                    "timestamp": t,
                    "psi_some_avg10": 0.1,
                    "swap_in_bytes": 0,
                    "uma_used_bytes": 100,
                    "prompt_cache_bytes": 95,
                }
                for t in ("2026-10-03T00:00:00Z", "2026-10-03T00:00:01Z")
            ],
            "oomd_events": [
                {
                    "timestamp": "2026-10-03T00:00:01Z",
                    "unit": "systemd-oomd",
                    "victim_cgroup": "studio.slice",
                    "journal_cursor": "cursor",
                }
            ],
            "dependent_effects": [
                {
                    "unit": "hermes.service",
                    "timestamp": "2026-10-03T00:00:02Z",
                    "exit_status": 1,
                }
            ],
            "redacted_state_archive_sha256": "a" * 64,
        }
    )
    return doc


def _wedge() -> dict[str, Any]:
    card = "DELTA-FORUM-QWEN-TOOLCALL-WEDGE-01"
    doc = _base(card)
    doc.update(
        {
            "wedge_trace": {
                "request_id": "req-1",
                "phase": "tool_call",
                "events": [
                    {
                        "timestamp": "2026-10-03T00:00:00Z",
                        "rank": 0,
                        "collective_sequence": 1,
                        "event": "progress",
                    },
                    {
                        "timestamp": "2026-10-03T00:00:01Z",
                        "rank": 1,
                        "collective_sequence": 1,
                        "event": "progress",
                    },
                    {
                        "timestamp": "2026-10-03T00:00:02Z",
                        "rank": 0,
                        "collective_sequence": 1,
                        "event": "stall",
                    },
                    {
                        "timestamp": "2026-10-03T00:00:03Z",
                        "rank": 1,
                        "collective_sequence": 1,
                        "event": "stall",
                    },
                ],
            },
            "token_pairs": [
                {"draft_token": "a", "target_token": "a"},
                {"draft_token": "b", "target_token": "c"},
            ],
            "reported_acceptance": 0.5,
            "bundle_sha256": "bundle",
        }
    )
    return doc


def _cutlass() -> dict[str, Any]:
    card = "DELTA-FORUM-QWEN35-NVFP4-CUTLASS-FIRST-REQUEST-GATE-01"
    doc = _base(card)
    doc.update(
        {
            "build": {
                "image_digest": doc["subject"]["image_digest"],
                "backend": "marlin",
                "model_digest": doc["subject"]["checkpoint_digest"],
                "request_id": "req-1",
            },
            "readiness": {"timestamp": "2026-10-03T00:00:00Z"},
            "first_inference": {
                "timestamp": "2026-10-03T00:00:01Z",
                "request_id": "req-1",
                "kernel_backend": "marlin",
                "exit_code": 0,
                "cuda_log_raw": "no Xid",
            },
            "candidate_output": {
                "raw_output": "answer",
                "oracle_ref": "first.json",
                "oracle_sha256": "",
            },
            "reference_output": {"raw_output": "answer"},
        }
    )
    return doc


def _json_soak() -> dict[str, Any]:
    card = "DELTA-FORUM-QWEN38-LONG-RUN-JSON-CORRECTNESS-CANARY-01"
    doc = _base(card)
    doc["paired_runs"] = [
        {
            "mode": mode,
            "request_id": "req-1",
            "oracle_ref": f"{mode}.json",
            "oracle_sha256": "",
            "checkpoint_digest": doc["subject"]["checkpoint_digest"],
            "tokenizer_digest": "tokenizer",
            "template_digest": "template",
            "turns": [{"turn_id": "turn-1", "raw_output": '{"ok":true}'}],
        }
        for mode in ("bf16", "candidate")
    ]
    return doc


def _ray_graph() -> dict[str, Any]:
    card = "DELTA-FORUM-RAY-TORCH-GRAPH-HANG-01"
    doc = _base(card)
    doc.update(
        {
            "host_torch": "2.9.1",
            "container_torch": "2.9.1",
            "cuda_version": "12.8",
            "vllm_version": "0.22",
            "ray_version": "2.40",
            "nccl_version": "2.29",
            "graph_eager_runs": [
                {
                    "mode": mode,
                    "request_id": "req-1",
                    "rank_events": [
                        {
                            "rank": rank,
                            "completed_collective": count,
                            "timestamp": f"2026-10-03T00:00:0{count}Z",
                        }
                        for rank in (0, 1)
                        for count in (1, 2)
                    ],
                    "gpu_samples": [{"utilization_percent": 100.0}],
                }
                for mode in ("graph", "eager")
            ],
        }
    )
    return doc


def _build_matrix() -> dict[str, Any]:
    card = "DELTA-FORUM-VLLM-GB10-ARCH-AND-BUILD-MATRIX-01"
    doc = _base(card)
    doc.update(
        {
            "effective_build": {
                key: value
                for key, value in (
                    ("image_digest", "image"),
                    ("wheel_sha256", "wheel"),
                    ("ptxas_version", "ptxas"),
                    ("architecture_flags", "sm_121a"),
                    ("resolver_log_sha256", "resolver"),
                    ("model_digest", "model"),
                    ("backend", "cutlass"),
                )
            },
            "required_operations": ["gemm", "rmsnorm"],
            "operation_matrix": [
                {
                    "operation": op,
                    "request_id": "req-1",
                    "kernel_name": f"{op}_sm121",
                    "build_exit_code": 0,
                    "import_exit_code": 0,
                    "load_exit_code": 0,
                    "first_inference_exit_code": 0,
                    "raw_output": "ok",
                    "finite_output_value": 1.0,
                }
                for op in ("gemm", "rmsnorm")
            ],
            "wrong_toolchain_control": {
                "exit_code": 1,
                "stderr_raw": "wrong arch",
                "compiler_digest": "compiler",
            },
        }
    )
    return doc


def _ray_resource() -> dict[str, Any]:
    card = "DELTA-FORUM-VLLM-RAY-GB10-RESOURCE-FIX-01"
    doc = _base(card)
    doc["ray_nodes"] = [
        {
            "node_id": f"n{i}",
            "resources": {"GPU": 1},
            "image_digest": doc["subject"]["image_digest"],
            "sm_arch": "sm_121",
        }
        for i in range(2)
    ]
    doc.update(
        {
            "backend_smoke": {
                "request_id": "req-1",
                "sm_arch": "sm_121",
                "kernel_name": "gemm",
                "exit_code": 0,
                "raw_output": "answer",
            },
            "unsupported_tag_control": {
                "image_digest": "sha256:" + "c" * 64,
                "exit_code": 1,
                "stderr_raw": "no schedulable GPU",
            },
        }
    )
    return doc


def _container() -> dict[str, Any]:
    card = "DELTA-ROOT-CONTAINER-EFFECTIVE-BUILD-AND-OFFLINE-GATE-01"
    doc = _base(card)
    doc["containers"] = [
        {
            "name": f"model-{i}",
            "image_digest": doc["subject"]["image_digest"],
            "model_digest": doc["subject"]["checkpoint_digest"],
            "checkpoint_digest": doc["subject"]["checkpoint_digest"],
            "patches_sha256": "patches",
            "request_id": "req-1",
            "port": 8000 + i,
            "memory_budget_bytes": 100,
            "load_exit_code": 0,
            "output_raw": "answer",
        }
        for i in range(2)
    ]
    doc.update(
        {
            "memory_reservation": {"available_bytes": 1000, "reserve_bytes": 100},
            "offline_boot": {
                "network_disabled_exit_code": 0,
                "argv_sha256": "argv",
                "image_digest": doc["subject"]["image_digest"],
            },
            "missing_artifact_negative": {
                "artifact_sha256": "artifact",
                "exit_code": 1,
                "stderr_raw": "missing",
            },
        }
    )
    return doc


def _attach_matrix_oracles(
    doc: dict[str, Any], tmp_path: Any, monkeypatch: Any
) -> None:
    root = tmp_path / "evidence"
    oracles = root / doc["card_id"] / "oracles"
    oracles.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(controls, "EVIDENCE", root)
    monkeypatch.setattr(oracle_controls, "EVIDENCE", root)
    payload = {
        "before_calls": [{"name": "mock", "arguments": {"ok": True}}],
        "after_cancel_calls": [{"name": "mock", "arguments": {"ok": True}}],
        "after_restart_calls": [{"name": "mock", "arguments": {"ok": True}}],
    }
    for row in doc.get("matrix_runs", []):
        raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        row["oracle_sha256"] = hashlib.sha256(raw).hexdigest()
        (oracles / row["oracle_ref"]).write_bytes(raw)
        request_bytes = json.dumps(
            {"request_raw": _mtp_request_raw()},
            sort_keys=True,
            separators=(",", ":"),
        ).encode()
        row["request_sha256"] = hashlib.sha256(request_bytes).hexdigest()
        (oracles / row["request_ref"]).write_bytes(request_bytes)


def test_long_run_json_output_rejects_nonfinite_and_duplicate_keys_after_baseline(
    tmp_path: Any, monkeypatch: Any
) -> None:
    valid = _json_soak()
    root = tmp_path / "json-soak-evidence"
    oracle_dir = root / valid["card_id"] / "oracles"
    oracle_dir.mkdir(parents=True)
    monkeypatch.setattr(controls, "EVIDENCE", root)
    monkeypatch.setattr(oracle_controls, "EVIDENCE", root)
    for pair in valid["paired_runs"]:
        raw = json.dumps(
            {"turns": {"turn-1": {"ok": True}}},
            sort_keys=True,
            separators=(",", ":"),
        ).encode()
        (oracle_dir / pair["oracle_ref"]).write_bytes(raw)
        pair["oracle_sha256"] = hashlib.sha256(raw).hexdigest()
    baseline = controls.assess(valid["card_id"], valid)
    assert baseline["status"] == "pass", baseline

    for invalid in ('{"ok":NaN}', '{"ok":true,"ok":false}'):
        bad = copy.deepcopy(valid)
        bad["paired_runs"][1]["turns"][0]["raw_output"] = invalid
        result = controls.assess(bad["card_id"], bad)
        assert result["status"] == "fail", result
        assert "long-run output is invalid JSON" in result["reason"]


def _replace_mtp_request(doc: dict[str, Any], request_raw: str) -> None:
    oracle_dir = controls.EVIDENCE / doc["card_id"] / "oracles"
    request_digest = hashlib.sha256(request_raw.encode()).hexdigest()
    for row in doc["matrix_runs"]:
        request_bytes = json.dumps(
            {"request_raw": request_raw}, sort_keys=True, separators=(",", ":")
        ).encode()
        (oracle_dir / row["request_ref"]).write_bytes(request_bytes)
        row["request_sha256"] = hashlib.sha256(request_bytes).hexdigest()
        row["input_sha256"] = "sha256:" + request_digest
    subject = doc["subject"]
    versions = subject["software_versions"]
    stack_binding = {
        "oem": subject.get("oem"),
        "host_id": subject.get("host_id"),
        "image_digest": subject.get("image_digest"),
        "model": subject.get("model"),
        "checkpoint_digest": subject.get("checkpoint_digest"),
        "vllm": versions.get("vllm"),
        "parser": versions.get("parser"),
        "tokenizer": versions.get("tokenizer"),
        "request_sha256": request_digest,
    }
    doc["admission_profile"]["stack_binding_sha256"] = hashlib.sha256(
        json.dumps(stack_binding, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


_CASES = [
    (
        _long_stop,
        lambda d: d["soak_runs"][0]["turns"][0].update(mutating_call_replay_count=1),
    ),
    (
        _mtp_parser,
        lambda d: d["matrix_runs"][1]["events"][2].update(
            sse_raw=d["matrix_runs"][1]["events"][2]["sse_raw"].replace(
                '"name": "mock"', '"name": "other"'
            )
        ),
    ),
    (_oomd, lambda d: d["oomd_events"][0].update(timestamp="2026-10-04T00:00:00Z")),
    (_wedge, lambda d: d.update(reported_acceptance=0.0)),
    (_cutlass, lambda d: d["first_inference"].update(exit_code=132)),
    (_json_soak, lambda d: d["paired_runs"][1]["turns"][0].update(raw_output="{")),
    (
        _ray_graph,
        lambda d: d["graph_eager_runs"][0]["rank_events"][0].update(
            completed_collective=0
        ),
    ),
    (_build_matrix, lambda d: d["operation_matrix"][0].update(build_exit_code=1)),
    (_ray_resource, lambda d: d["backend_smoke"].update(exit_code=1)),
    (_container, lambda d: d["memory_reservation"].update(reserve_bytes=1000)),
]


@pytest.mark.parametrize("factory,mutate", _CASES)
def test_raw_domain_fixture_passes_then_single_criterion_mutation_fails(
    factory: Any, mutate: Any, tmp_path: Any, monkeypatch: Any
) -> None:
    valid = factory()
    if "matrix_runs" in valid or "paired_runs" in valid or "candidate_output" in valid:
        root = tmp_path / "evidence"
        oracles = root / valid["card_id"] / "oracles"
        oracles.mkdir(parents=True)
        monkeypatch.setattr(controls, "EVIDENCE", root)
        monkeypatch.setattr(oracle_controls, "EVIDENCE", root)
        if "matrix_runs" in valid:
            _attach_matrix_oracles(valid, tmp_path, monkeypatch)
        for row in valid.get("matrix_runs", []):
            payload = {
                "before_calls": [{"name": "mock", "arguments": {"ok": True}}],
                "after_cancel_calls": [{"name": "mock", "arguments": {"ok": True}}],
                "after_restart_calls": [{"name": "mock", "arguments": {"ok": True}}],
            }
            raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
            row["oracle_sha256"] = hashlib.sha256(raw).hexdigest()
            (oracles / row["oracle_ref"]).write_bytes(raw)
        for row in valid.get("paired_runs", []):
            raw = json.dumps(
                {"turns": {"turn-1": {"ok": True}}},
                sort_keys=True,
                separators=(",", ":"),
            ).encode()
            row["oracle_sha256"] = hashlib.sha256(raw).hexdigest()
            (oracles / row["oracle_ref"]).write_bytes(raw)
        if "candidate_output" in valid:
            raw = json.dumps(
                {"expected_output": "answer"}, sort_keys=True, separators=(",", ":")
            ).encode()
            valid["candidate_output"]["oracle_sha256"] = hashlib.sha256(raw).hexdigest()
            (oracles / valid["candidate_output"]["oracle_ref"]).write_bytes(raw)
    baseline = controls.assess(valid["card_id"], valid)
    assert baseline["status"] == "pass", baseline
    bad = copy.deepcopy(valid)
    mutate(bad)
    result = controls.assess(bad["card_id"], bad)
    assert result["status"] == "fail", result


@pytest.mark.parametrize(
    ("mutate", "reason"),
    [
        (
            lambda d: d["matrix_runs"][1]["events"][2].update(server_pid=200),
            "same-process post-cancel tool call changed server PID/generation",
        ),
        (
            lambda d: d["matrix_runs"][1].update(mtp_tokens=-1),
            "negative MTP token count was enabled",
        ),
        (
            lambda d: d["matrix_runs"][1]["events"][3].update(
                server_pid=100, process_generation=1
            ),
            "restart recovery did not use a new server process generation",
        ),
        (
            lambda d: d["matrix_runs"][1]["events"][1].update(
                timestamp="2026-10-03T00:00:05Z"
            ),
            "parser/cancel/restart timestamps are not strictly causal",
        ),
        (
            lambda d: d["matrix_runs"][1]["events"][1].update(cancel_exit_code=1),
            "midstream cancel action failed and did not establish cancellation",
        ),
        (
            lambda d: d["matrix_runs"][1]["events"][2].update(
                request_id=d["matrix_runs"][1]["events"][0]["request_id"]
            ),
            "HTTP request lifecycle does not reuse the partial request and create new follow-up IDs",
        ),
        (
            lambda d: d["matrix_runs"][1]["events"][2].update(
                response_id="unbound-response"
            ),
            "response ID differs from raw SSE",
        ),
    ],
)
def test_mtp_cancel_state_mutations_fail_after_positive_baseline(
    mutate: Any, reason: str, tmp_path: Any, monkeypatch: Any
) -> None:
    valid = _mtp_parser()
    _attach_matrix_oracles(valid, tmp_path, monkeypatch)
    baseline = controls.assess(valid["card_id"], valid)
    assert baseline["status"] == "pass", baseline
    bad = copy.deepcopy(valid)
    mutate(bad)
    result = controls.assess(bad["card_id"], bad)
    assert result["status"] == "fail" and reason in result["reason"], result


def test_mtp_replay_hash_is_recomputed_from_request_bytes_after_positive_baseline(
    tmp_path: Any, monkeypatch: Any
) -> None:
    valid = _mtp_parser()
    _attach_matrix_oracles(valid, tmp_path, monkeypatch)
    baseline = controls.assess(valid["card_id"], valid)
    assert baseline["status"] == "pass", baseline
    row = valid["matrix_runs"][1]
    path = controls.EVIDENCE / valid["card_id"] / "oracles" / row["request_ref"]
    changed_request = _mtp_request_raw().replace(
        "Call mock with ok set to true.", "Call mock with a different value."
    )
    changed = json.dumps(
        {"request_raw": changed_request},
        sort_keys=True,
        separators=(",", ":"),
    ).encode()
    path.write_bytes(changed)
    row["request_sha256"] = hashlib.sha256(changed).hexdigest()
    result = controls.assess(valid["card_id"], valid)
    assert (
        result["status"] == "fail" and "request bytes do not match" in result["reason"]
    ), result


def _invalid_mtp_requests() -> list[tuple[str, str]]:
    valid_body = json.loads(_mtp_request_raw())
    missing_model = copy.deepcopy(valid_body)
    del missing_model["model"]
    missing_tools = copy.deepcopy(valid_body)
    del missing_tools["tools"]
    malformed_schema = copy.deepcopy(valid_body)
    malformed_schema["tools"][0]["function"]["parameters"]["additionalProperties"] = True
    wrong_tool_choice = copy.deepcopy(valid_body)
    wrong_tool_choice["tool_choice"]["function"]["name"] = "not-declared"
    wrong_model = copy.deepcopy(valid_body)
    wrong_model["model"] = "other-model"
    oversized = copy.deepcopy(valid_body)
    oversized["max_tokens"] = 17
    encode = lambda value: json.dumps(value, sort_keys=True, separators=(",", ":"))
    return [
        ("this is not an inference request", "captured request is not valid JSON"),
        (encode(missing_model), "request model differs from bound request/subject model"),
        (encode(missing_tools), "request lacks typed OpenAI function-tool schema"),
        (encode(malformed_schema), "request function tool has unsupported or open JSON Schema"),
        (encode(wrong_tool_choice), "request tool_choice is malformed"),
        (encode(wrong_model), "request model differs from bound request/subject model"),
        (encode(oversized), "request generation/context budget exceeds captured bounds"),
    ]


@pytest.mark.parametrize(("request_raw", "reason"), _invalid_mtp_requests())
def test_mtp_request_contract_rejects_rehashed_invalid_request_after_positive_baseline(
    request_raw: str,
    reason: str,
    tmp_path: Any,
    monkeypatch: Any,
) -> None:
    valid = _mtp_parser()
    _attach_matrix_oracles(valid, tmp_path, monkeypatch)
    baseline = controls.assess(valid["card_id"], valid)
    assert baseline["status"] == "pass", baseline
    bad = copy.deepcopy(valid)
    _replace_mtp_request(bad, request_raw)
    result = controls.assess(bad["card_id"], bad)
    assert result["status"] == "fail" and reason in result["reason"], result


def test_mtp_request_duplicate_model_key_is_rejected_after_positive_baseline(
    tmp_path: Any, monkeypatch: Any
) -> None:
    valid = _mtp_parser()
    _attach_matrix_oracles(valid, tmp_path, monkeypatch)
    baseline = controls.assess(valid["card_id"], valid)
    assert baseline["status"] == "pass", baseline
    duplicate_model = _mtp_request_raw().replace(
        '"model":"model-x"', '"model":"model-x","model":"other-model"'
    )
    bad = copy.deepcopy(valid)
    _replace_mtp_request(bad, duplicate_model)
    result = controls.assess(bad["card_id"], bad)
    assert result["status"] == "fail" and "not valid JSON" in result["reason"], result


def test_mtp_nonfinite_json_constant_is_rejected_after_positive_baseline(
    tmp_path: Any, monkeypatch: Any
) -> None:
    valid = _mtp_parser()
    _attach_matrix_oracles(valid, tmp_path, monkeypatch)
    baseline = controls.assess(valid["card_id"], valid)
    assert baseline["status"] == "pass", baseline
    raw = _mtp_request_raw().replace('"max_tokens":8', '"max_tokens":NaN')
    bad = copy.deepcopy(valid)
    _replace_mtp_request(bad, raw)
    result = controls.assess(bad["card_id"], bad)
    assert result["status"] == "fail" and "not valid JSON" in result["reason"], result


def test_mtp_request_without_budget_is_unknown_without_effective_server_capture(
    tmp_path: Any, monkeypatch: Any
) -> None:
    valid = _mtp_parser()
    _attach_matrix_oracles(valid, tmp_path, monkeypatch)
    baseline = controls.assess(valid["card_id"], valid)
    assert baseline["status"] == "pass", baseline
    body = json.loads(_mtp_request_raw())
    del body["max_tokens"]
    bad = copy.deepcopy(valid)
    _replace_mtp_request(bad, json.dumps(body, sort_keys=True, separators=(",", ":")))
    result = controls.assess(bad["card_id"], bad)
    assert (
        result["status"] == "unknown"
        and "no captured effective server config bound to PID/build" in result["reason"]
    ), result


@pytest.mark.parametrize(
    ("keyword", "value"), [("minimum", 1), ("pattern", "^true$")]
)
def test_mtp_unsupported_json_schema_constraints_are_unknown_after_positive_baseline(
    keyword: str,
    value: Any,
    tmp_path: Any,
    monkeypatch: Any,
) -> None:
    valid = _mtp_parser()
    _attach_matrix_oracles(valid, tmp_path, monkeypatch)
    baseline = controls.assess(valid["card_id"], valid)
    assert baseline["status"] == "pass", baseline
    body = json.loads(_mtp_request_raw())
    body["tools"][0]["function"]["parameters"]["properties"]["ok"][keyword] = value
    bad = copy.deepcopy(valid)
    _replace_mtp_request(
        bad, json.dumps(body, sort_keys=True, separators=(",", ":"))
    )
    result = controls.assess(bad["card_id"], bad)
    assert result["status"] == "unknown" and f"unsupported keyword(s): {keyword}" in result["reason"], result


def test_mtp_tool_call_schema_matcher_rejects_invalid_call_shapes_after_baseline() -> None:
    contract = {
        "tool_schemas": {
            "mock": {
                "type": "object",
                "properties": {"ok": {"type": "boolean"}},
                "required": ["ok"],
                "additionalProperties": False,
            }
        }
    }
    valid = [{"name": "mock", "arguments": {"ok": True}}]
    assert controls._mtp_calls_match_request(valid, contract)

    for calls in (
        None,
        [],
        [None],
        [{"name": "missing", "arguments": {"ok": True}}],
        [{"name": "mock", "arguments": []}],
        [{"name": "mock", "arguments": {}}],
        [{"name": "mock", "arguments": {"ok": True, "extra": 1}}],
        [{"name": "mock", "arguments": {"ok": "true"}}],
    ):
        assert not controls._mtp_calls_match_request(calls, contract)


def test_mtp_oracle_tool_name_must_exist_in_request_schema_after_positive_baseline(
    tmp_path: Any, monkeypatch: Any
) -> None:
    valid = _mtp_parser()
    _attach_matrix_oracles(valid, tmp_path, monkeypatch)
    baseline = controls.assess(valid["card_id"], valid)
    assert baseline["status"] == "pass", baseline
    bad = copy.deepcopy(valid)
    row = bad["matrix_runs"][0]
    path = controls.EVIDENCE / bad["card_id"] / "oracles" / row["oracle_ref"]
    payload = json.loads(path.read_bytes())
    payload["after_cancel_calls"][0]["name"] = "not-declared"
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    path.write_bytes(raw)
    row["oracle_sha256"] = hashlib.sha256(raw).hexdigest()
    result = controls.assess(bad["card_id"], bad)
    assert (
        result["status"] == "fail"
        and "independent tool-call oracle violates" in result["reason"]
    ), result


def test_mtp_raw_sse_usage_must_fit_bounded_context_after_positive_baseline(
    tmp_path: Any, monkeypatch: Any
) -> None:
    valid = _mtp_parser()
    _attach_matrix_oracles(valid, tmp_path, monkeypatch)
    baseline = controls.assess(valid["card_id"], valid)
    assert baseline["status"] == "pass", baseline
    bad = copy.deepcopy(valid)
    event = bad["matrix_runs"][0]["events"][2]
    event["sse_raw"] = event["sse_raw"].replace('"prompt_tokens": 7', '"prompt_tokens": 130')
    event["sse_raw"] = event["sse_raw"].replace('"total_tokens": 8', '"total_tokens": 131')
    result = controls.assess(bad["card_id"], bad)
    assert (
        result["status"] == "fail"
        and "exceeds the bounded context/generation budget" in result["reason"]
    ), result


@pytest.mark.parametrize("card", sorted(controls.IDS))
def test_real_capture_close_gate_needs_actual_runtime_record(card: str) -> None:
    result = controls.verify(card)
    assert result["status"] == "pass", (
        f"{card}: status={result['status']} could_not_run={result['could_not_run']} "
        f"reason={result['reason']} files={result.get('files', [])}"
    )


def test_malformed_pressure_timestamps_are_unknown_after_positive_baseline() -> None:
    valid = _oomd()
    assert controls.assess(valid["card_id"], valid)["status"] == "pass"
    bad = copy.deepcopy(valid)
    bad["oomd_events"][0]["timestamp"] = "not-a-timestamp"
    result = controls.assess(bad["card_id"], bad)
    assert result["status"] == "unknown" and "timestamp is invalid" in result["reason"]


def test_wedge_timestamp_parse_failure_is_unknown_after_positive_baseline() -> None:
    valid = _wedge()
    assert controls.assess(valid["card_id"], valid)["status"] == "pass"
    bad = copy.deepcopy(valid)
    bad["wedge_trace"]["events"][0]["timestamp"] = "invalid"
    result = controls.assess(bad["card_id"], bad)
    assert result["status"] == "unknown" and "not parseable UTC" in result["reason"]


def test_unknown_card_and_bounded_capture_reader(tmp_path: Any) -> None:
    assert controls.assess("unknown-card", {})["status"] == "unknown"
    missing = controls.verify(
        "DELTA-FORUM-QWEN-SERVICE-OOMD-CACHE-FAIL-01", tmp_path / "missing.json"
    )
    assert (
        missing["status"] == "unknown"
        and "raw capture unavailable" in missing["reason"]
    )
    huge = tmp_path / "huge.json"
    huge.write_bytes(b" " * (4 * 1024 * 1024 + 1))
    oversized = controls.verify("DELTA-FORUM-QWEN-SERVICE-OOMD-CACHE-FAIL-01", huge)
    assert oversized["status"] == "unknown" and "exceeds 4 MiB" in oversized["reason"]
    invalid = tmp_path / "invalid.json"
    invalid.write_bytes(b"\xff")
    unreadable = controls.verify("DELTA-FORUM-QWEN-SERVICE-OOMD-CACHE-FAIL-01", invalid)
    assert (
        unreadable["status"] == "unknown"
        and "raw capture unavailable" in unreadable["reason"]
    )


def test_assess_converts_unexpected_raw_shape_error_to_unknown(
    monkeypatch: Any,
) -> None:
    monkeypatch.setattr(
        controls,
        "_capture",
        lambda _raw, _card: (_ for _ in ()).throw(AttributeError("bad shape")),
    )
    result = controls.assess("DELTA-FORUM-QWEN-SERVICE-OOMD-CACHE-FAIL-01", {})
    assert result["status"] == "unknown" and "malformed raw record" in result["reason"]


def test_verify_returns_pass_only_for_a_valid_raw_capture(tmp_path: Any) -> None:
    doc = _oomd()
    path = tmp_path / "runtime-capture.json"
    path.write_text(json.dumps(doc), encoding="utf-8")
    result = controls.verify(doc["card_id"], path)
    assert result["status"] == "pass" and result["files"] == [str(path)]
