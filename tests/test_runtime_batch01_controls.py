"""Parser unit tests use fabricated raw-format examples, never lab evidence.

The evidence selectors remain separate and require PASS from a real capture.
"""

from __future__ import annotations

import copy
import hashlib
import json
from typing import Any, cast

import pytest

from tools import runtime_batch01_controls as controls
from tools import runtime_batch02_controls as oracle_controls


def _sse(
    content: str | None = None, with_tool: bool = False, tool_count: int = 1
) -> str:
    if with_tool:
        delta = {
            "tool_calls": [
                {
                    "index": i,
                    "id": f"call-{i}",
                    "type": "function",
                    "function": {"name": "mock", "arguments": '{"ok":true}'},
                }
                for i in range(tool_count)
            ]
        }
    else:
        delta = {"content": content}
    frames = [
        {
            "id": "cmp-1",
            "object": "chat.completion.chunk",
            "choices": [{"index": 0, "delta": delta, "finish_reason": None}],
        },
        {
            "id": "cmp-1",
            "object": "chat.completion.chunk",
            "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}],
        },
    ]
    return (
        "".join(f"data: {json.dumps(frame)}\n\n" for frame in frames)
        + "data: [DONE]\n\n"
    )


def _base(card: str) -> dict:
    return {
        "schema": "bb.runtime.raw.v1",
        "card_id": card,
        "capture_id": "unit-capture",
        "captured_at": "2026-10-03T00:00:00Z",
        "contradictions": [],
        "subject": {
            "oem": "OEM-X",
            "host_id": "host-a",
            "image_digest": "sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
            "model": "model-x",
            "checkpoint_digest": "sha256:bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
            "software_versions": {"engine": "engine-1"},
        },
        "request_bounds": {
            "request_id": "req-1",
            "model": "model-x",
            "checkpoint_digest": "sha256:bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
            "max_tokens": 16,
            "max_context_tokens": 128,
            "deadline_seconds": 10,
            "started_at": "2026-10-03T00:00:00Z",
            "finished_at": "2026-10-03T00:00:01Z",
        },
        "rollback_record": {
            "known_good_digest": "sha256:cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc",
            "candidate_digest": "sha256:dddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddd",
            "procedure_ref": "rollback.md",
            "before_state_sha256": "sha256:eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee",
            "after_restore_sha256": "sha256:eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee",
        },
    }


def _three_node(d: dict) -> None:
    d["nodes"] = [
        {
            "node_id": f"n{i}",
            "oem_model": "OEM-X",
            "image_digest": "sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
            "nccl_version": "2.30",
            "ranks": [
                {
                    "rank": i,
                    "nccl_version": "2.30",
                    "loaded_image_digest": "sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
                }
            ],
        }
        for i in range(3)
    ]
    d["pp_first_request"] = {
        "request_id": "req-1",
        "stage_count": 2,
        "stage_events": [
            {"event": "stage_complete", "rank": "r0"},
            {"event": "stage_complete", "rank": "r1"},
        ],
        "output_tokens": 2,
        "finish_reason": "stop",
    }
    d["negative_control"] = {
        "kind": "wrong_image_digest",
        "observed_digest": "sha256:wrong",
        "gate_result": "rejected",
    }


def _eight_node(d: dict) -> None:
    plan = [{"node_id": f"n{i}", "interface": "eth0", "mtu": 9000} for i in range(8)]
    d["network_plan"] = {"source_ref": "oem-plan.json", "interfaces": plan}
    d["interfaces"] = [
        {
            "node_id": f"n{i}",
            "interface": "eth0",
            "effective_mtu": 9000,
            "source": "ip-json",
        }
        for i in range(8)
    ]
    d["nccl_operation"] = {
        "request_id": "req-1",
        "unique_nodes": 8,
        "rank_results": [{"exit_code": 0} for _ in range(8)],
    }
    d["first_request"] = {
        "request_id": "req-1",
        "output_tokens": 3,
        "rank_logs": [{} for _ in range(8)],
    }
    d["negative_control"] = {
        "kind": "plan_mismatch",
        "planned_mtu": 9000,
        "observed_mtu": 1500,
        "preflight_result": "rejected",
    }


def _populate_0(d: dict) -> None:
    _three_node(d)


def _populate_1(d: dict) -> None:
    _eight_node(d)


def _populate_2(d: dict) -> None:
    d["repetitions"] = [
        {
            "run_id": f"run-{i}",
            "request_id": "req-1",
            "untrusted_tool_output": "inject",
            "untrusted_output_sha256": "sha256:fixture",
            "context_trace": [
                {
                    "type": "untrusted_tool_result",
                    "content_sha256": "sha256:fixture",
                }
            ],
            "mail_effect": {"tool": "mock_mail", "mutations": []},
        }
        for i in range(5)
    ]
    d["positive_fixture_control"] = {
        "request_id": "req-1",
        "fixture_sha256": "sha256:fixture",
        "reached_context": True,
        "mock_tool_invoked": True,
    }


def _populate_3(d: dict) -> None:
    d["draft_ranks"] = [
        {
            "effective_dcp_size": 2,
            "attention_ops": ["all_gather_q", "merge_lse"],
            "partial_values": [0.1, 0.2],
            "request_id": "req-1",
        }
        for _ in range(2)
    ]
    d["dcp1_reference"] = {
        "request_id": "req-1",
        "atol": 0.01,
        "pairs": [{"reference_values": [1.0, 2.0], "draft_values": [1.001, 1.999]}],
    }
    d["acceptance_by_position"] = [
        {"position": 0, "draft_token": "a", "target_token": "a", "accepted": True}
    ]
    d["pretrim_headroom_case"] = {
        "separate_run": True,
        "peak_bytes": 8,
        "available_before_load_bytes": 16,
        "load_log_sha256": "load",
    }


def _populate_4(d: dict) -> None:
    run = lambda mode, tokens, stall: {
        "mode": mode,
        "decode_samples": [
            {"generated_tokens": tokens, "elapsed_seconds": 1} for _ in range(3)
        ],
        "prefill_completions": [{"finish_reason": "stop"} for _ in range(4)],
        "max_decode_stall_seconds": stall,
        "output_sha256": "out",
    }
    d["workload"] = {
        "request_id": "req-1",
        "long_decode_tokens": 8192,
        "concurrent_prefills": 4,
        "dcp_size": 4,
    }
    d["scheduler_runs"] = [run("stock", 1, 5.0), run("candidate", 10, 1.0)]
    d["correctness_oracle"] = {"request_id": "req-1"}


def _populate_5(d: dict) -> None:
    d["effective_source_commit"] = "a" * 40
    d["patch_state"] = "included"
    d["subject"]["software_versions"]["vllm_commit"] = "a" * 40
    d["request_bounds"]["server_process"] = {
        "pid": 4321,
        "starttime_ticks": 987654,
        "image_digest": d["subject"]["image_digest"],
    }
    names = [
        "json_stream",
        "json_nonstream",
        "tool_stream",
        "tool_nonstream",
        "parallel_tool",
        "tool_followup",
    ]
    d["cases"] = [
        {
            "case": n,
            "request_id": "req-1",
            "http_status": 200,
            "chunks": ["raw"],
            "finish_reason": "stop",
            "process_alive_after": True,
            **(
                {
                    "raw_output": '{"ok":true}',
                    "sse_raw": _sse('{"ok":true}'),
                }
                if n.startswith("json_")
                else {
                    "raw_output": "tool-call stream",
                    "sse_raw": _sse(with_tool=True),
                    "tool_calls": [{"name": "mock", "arguments_json": '{"ok":true}'}],
                    "expected_tool_calls": [
                        {"name": "mock", "arguments": {"ok": True}}
                    ],
                }
            ),
        }
        for n in names
    ]
    for row in d["cases"]:
        if row["case"] in {"tool_stream", "parallel_tool", "tool_followup"}:
            if row["case"] == "parallel_tool":
                row["sse_raw"] = _sse(with_tool=True, tool_count=2)
                row["expected_tool_calls"] = [
                    {"name": "mock", "arguments": {"ok": True}},
                    {"name": "mock", "arguments": {"ok": True}},
                ]
            else:
                row["expected_tool_calls"] = [
                    {"name": "mock", "arguments": {"ok": True}}
                ]
        elif row["case"] == "tool_nonstream":
            row["expected_tool_calls"] = [{"name": "mock", "arguments": {"ok": True}}]
    d["cases"].append(
        {
            "case": "invalid_revision",
            "http_status": 500,
            "parser_error": "syntax",
            "rejected": True,
            "source_commit": "b" * 40,
        }
    )


def _populate_6(d: dict) -> None:
    d["stop_capture"] = {
        "script_sha256": "script",
        "argv": ["stop"],
        "stdout_sha256": "out",
        "exit_code": 0,
    }
    d["containers_before"] = {"nfs_exporter_ids": ["exporter"]}
    d["containers_after"] = {"running_ids": ["exporter"]}
    d["mount_checks"] = [{"mount_id": "m1", "source": "nfs:/export", "mounted": True}]
    d["image_pin"] = {
        "tag": "dev-dsv41",
        "expected_digest": "sha256:pinned",
        "observed_digest": "sha256:pinned",
    }
    d["negative_control"] = {
        "kind": "tag_drift",
        "observed_digest": "sha256:drift",
        "gate_result": "blocked",
    }


def _populate_7(d: dict) -> None:
    d["hosts"] = [
        {"node_id": f"n{i}", "oem_model": "OEM-X", "serial_hash": f"serial-{i}"}
        for i in range(2)
    ]
    d["selected_paths"] = [
        {
            "node_id": f"n{i}",
            "hca": "roce0",
            "interface": "eth0",
            "ipv4": f"10.0.0.{i + 1}",
            "gid_index": 3,
            "gid_value": f"fe80::{i + 1}",
            "mtu": 9000,
            "nccl_env_sha256": f"env-{i}",
        }
        for i in range(2)
    ]
    d["selected_paths_sha256"] = "paths"
    d["collective"] = {
        "request_id": "req-1",
        "selected_path_hash": "paths",
        "rank_exit_codes": [0, 0],
    }
    d["first_inference"] = {
        "request_id": "req-1",
        "selected_path_hash": "paths",
        "output_tokens": 2,
    }
    d["cold_recovery"] = {
        "before_state_sha256": "before",
        "after_state_sha256": "after",
        "no_power_cycle": True,
    }
    d["negative_control"] = {
        "kind": "null_gid_twin",
        "gid_value": "null",
        "preflight_result": "rejected",
    }


def _populate_8(d: dict) -> None:
    d["subject"].update(
        {
            "tokenizer_digest": "tok",
            "template_digest": "template",
            "engine_commit": "engine",
        }
    )
    kinds = [
        "single_turn",
        "prefix_cache_growing",
        "structured_thinking_on",
        "structured_thinking_off",
        "reasoning_on",
        "reasoning_off",
        "required_tool_loop",
    ]
    d["conversation_cases"] = [
        {
            "kind": k,
            "request_id": "req-1",
            "model": "model-x",
            "checkpoint_digest": "sha256:bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
            "tool_iterations": 2,
            "configured_limit": 4,
            "terminated_by_limit": True,
            "turns": [
                {
                    "turn_index": 0,
                    "sse_raw": _sse("expected"),
                    "expected_output": "expected",
                    "finish_reason": "stop",
                    "prompt_tokens": 16,
                    "completion_tokens": 1,
                }
            ],
        }
        for k in kinds
    ]
    d["recipe_ab"] = [
        {
            "thinking": on,
            "request_id": "req-1",
            "recipe_sha256": str(on),
            "raw_metrics": {"source_ref": "metrics.json"},
        }
        for on in (True, False)
    ]


def _record(card: str) -> dict:
    d = _base(card)
    builders = {
        "3NODE-NCCL-IMAGE-AND-FIRST-REQUEST-01": _populate_0,
        "8NODE-NCCL-INTERFACE-MTU-01": _populate_1,
        "CROSS-TURN-SLEEPER-INJECTION-REGRESSION-01": _populate_2,
        "DCP-MTP-DRAFT-CORRECTNESS-AND-PRETRIM-OOM-01": _populate_3,
        "DCP4-DECODE-STARVATION-FAIR-SCHEDULER-01": _populate_4,
        "DFLASH-XGRAMMAR-STRUCTURED-OUTPUT-REGRESSION-01": _populate_5,
        "DSV41-NFS-STOP-TAG-PIN-01": _populate_6,
        "DUALSPARK-NCCL-GID-TWIN-AND-COLD-RECOVERY-01": _populate_7,
        "GLM52-MULTITURN-CORRECTNESS-AND-RECIPE-SENSITIVITY-01": _populate_8,
    }
    builder = next(
        (fn for suffix, fn in builders.items() if card.endswith(suffix)), None
    )
    if builder is None:
        raise AssertionError(card)
    builder(d)
    return d


def _attach_xgrammar_requests(doc: dict, tmp_path, monkeypatch) -> None:
    root = tmp_path / "evidence"
    oracle_dir = root / doc["card_id"] / "oracles"
    oracle_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(controls, "EVIDENCE", root)
    monkeypatch.setattr(oracle_controls, "EVIDENCE", root)
    req = doc["request_bounds"]
    process = req["server_process"]
    json_schema = {
        "type": "object",
        "properties": {"ok": {"type": "boolean"}},
        "required": ["ok"],
        "additionalProperties": False,
    }
    function = {
        "name": "mock",
        "description": "Set the requested boolean.",
        "parameters": json_schema,
    }
    for row in doc["cases"]:
        if row["case"] == "invalid_revision":
            continue
        body = {
            "model": req["model"],
            "messages": [
                {"role": "system", "content": "Return the requested result."},
                {"role": "user", "content": "Set ok to true."},
            ],
            "max_tokens": 8,
            "stream": row["case"] in {
                "json_stream", "tool_stream", "parallel_tool", "tool_followup"
            },
        }
        if row["case"] == "tool_followup":
            body["messages"] = [
                {"role": "user", "content": "Set ok to true."},
                {
                    "role": "assistant",
                    "tool_calls": [
                        {
                            "id": "call-1",
                            "type": "function",
                            "function": {"name": "mock", "arguments": "{}"},
                        }
                    ],
                },
                {
                    "role": "tool",
                    "tool_call_id": "call-1",
                    "content": "done",
                },
            ]
        if row["case"].startswith("json_"):
            body["response_format"] = {
                "type": "json_schema",
                "json_schema": {
                    "name": "result",
                    "strict": True,
                    "schema": json_schema,
                },
            }
        else:
            body["tools"] = [
                {"type": "function", "function": function},
            ]
        request_raw = json.dumps(body, sort_keys=True, separators=(",", ":"))
        sidecar = {
            "request_raw": request_raw,
            "request_id": req["request_id"],
            "server_pid": process["pid"],
            "server_starttime_ticks": process["starttime_ticks"],
            "server_image_digest": process["image_digest"],
        }
        encoded = json.dumps(sidecar, sort_keys=True, separators=(",", ":")).encode()
        ref = f"{row['case']}.request.json"
        (oracle_dir / ref).write_bytes(encoded)
        row["request_ref"] = ref
        row["request_sha256"] = hashlib.sha256(encoded).hexdigest()
        row["input_sha256"] = "sha256:" + hashlib.sha256(request_raw.encode()).hexdigest()


def _mutate_xgrammar_request(
    doc: dict,
    tmp_path,
    case: str,
    mutate,
    *,
    raw_override: str | None = None,
) -> None:
    row = next(item for item in doc["cases"] if item["case"] == case)
    sidecar_path = (
        tmp_path / "evidence" / doc["card_id"] / "oracles" / row["request_ref"]
    )
    sidecar = json.loads(sidecar_path.read_bytes())
    if raw_override is None:
        body = json.loads(sidecar["request_raw"])
        mutate(body)
        request_raw = json.dumps(body, sort_keys=True, separators=(",", ":"))
    else:
        request_raw = raw_override
    sidecar["request_raw"] = request_raw
    encoded = json.dumps(sidecar, sort_keys=True, separators=(",", ":")).encode()
    sidecar_path.write_bytes(encoded)
    row["request_sha256"] = hashlib.sha256(encoded).hexdigest()
    row["input_sha256"] = "sha256:" + hashlib.sha256(request_raw.encode()).hexdigest()


@pytest.mark.parametrize("card", sorted(controls.IDS))
def test_domain_predicate_accepts_complete_raw_shape(card: str, tmp_path, monkeypatch) -> None:
    # Passing this fabricated parser sample says nothing about any real stack.
    raw = _record(card)
    if card.endswith("DFLASH-XGRAMMAR-STRUCTURED-OUTPUT-REGRESSION-01"):
        _attach_xgrammar_requests(raw, tmp_path, monkeypatch)
    assert controls.assess(card, raw)["status"] == "pass"


@pytest.mark.parametrize(
    "card_suffix,path,value",
    [
        ("3NODE-NCCL-IMAGE-AND-FIRST-REQUEST-01", ("nodes", 1, "ranks", 0, "rank"), True),
        ("3NODE-NCCL-IMAGE-AND-FIRST-REQUEST-01", ("pp_first_request", "output_tokens"), True),
        ("8NODE-NCCL-INTERFACE-MTU-01", ("first_request", "output_tokens"), True),
        ("8NODE-NCCL-INTERFACE-MTU-01", ("nccl_operation", "rank_results", 0, "exit_code"), False),
        ("8NODE-NCCL-INTERFACE-MTU-01", ("negative_control", "planned_mtu"), True),
        ("DCP-MTP-DRAFT-CORRECTNESS-AND-PRETRIM-OOM-01", ("acceptance_by_position", 0, "position"), True),
        ("DCP-MTP-DRAFT-CORRECTNESS-AND-PRETRIM-OOM-01", ("pretrim_headroom_case", "peak_bytes"), True),
        ("DCP4-DECODE-STARVATION-FAIR-SCHEDULER-01", ("scheduler_runs", 1, "decode_samples", 0, "generated_tokens"), True),
        ("DSV41-NFS-STOP-TAG-PIN-01", ("stop_capture", "exit_code"), False),
        ("DUALSPARK-NCCL-GID-TWIN-AND-COLD-RECOVERY-01", ("selected_paths", 0, "gid_index"), True),
        ("DUALSPARK-NCCL-GID-TWIN-AND-COLD-RECOVERY-01", ("collective", "rank_exit_codes", 0), False),
        ("DUALSPARK-NCCL-GID-TWIN-AND-COLD-RECOVERY-01", ("first_inference", "output_tokens"), True),
        ("GLM52-MULTITURN-CORRECTNESS-AND-RECIPE-SENSITIVITY-01", ("conversation_cases", 6, "tool_iterations"), True),
        ("GLM52-MULTITURN-CORRECTNESS-AND-RECIPE-SENSITIVITY-01", ("conversation_cases", 0, "turns", 0, "prompt_tokens"), True),
    ],
)
def test_json_boolean_cannot_stand_in_for_integer_after_positive_baseline(
    card_suffix: str, path: tuple[str | int, ...], value: bool
) -> None:
    card = next(card for card in controls.IDS if card.endswith(card_suffix))
    valid = _record(card)
    baseline = controls.assess(card, valid)
    assert baseline["status"] == "pass", baseline

    corrupted = copy.deepcopy(valid)
    target = corrupted
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = value
    result = controls.assess(card, corrupted)
    assert result["status"] == "unknown" and result["could_not_run"] == 1, result


@pytest.mark.parametrize(
    "card_suffix,path,value,reason",
    [
        (
            "8NODE-NCCL-INTERFACE-MTU-01",
            ("negative_control", "planned_mtu"),
            -1,
            "nonpositive interface MTU",
        ),
        (
            "DCP-MTP-DRAFT-CORRECTNESS-AND-PRETRIM-OOM-01",
            ("pretrim_headroom_case", "peak_bytes"),
            -1,
            "memory byte measurements are negative",
        ),
        (
            "3NODE-NCCL-IMAGE-AND-FIRST-REQUEST-01",
            ("nodes", 0, "ranks", 0, "rank"),
            -1,
            "negative rank number",
        ),
    ],
)
def test_negative_physical_counts_fail_after_positive_baseline(
    card_suffix: str, path: tuple[str | int, ...], value: int, reason: str
) -> None:
    card = next(card for card in controls.IDS if card.endswith(card_suffix))
    valid = _record(card)
    baseline = controls.assess(card, valid)
    assert baseline["status"] == "pass", baseline

    corrupted = copy.deepcopy(valid)
    target = corrupted
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = value
    result = controls.assess(card, corrupted)
    assert result["status"] == "fail" and reason in result["reason"], result


@pytest.mark.parametrize("card", sorted(controls.IDS))
def test_domain_predicate_distinguishes_conflict_from_missing_capture(
    card: str, tmp_path, monkeypatch
) -> None:
    valid = _record(card)
    if card.endswith("DFLASH-XGRAMMAR-STRUCTURED-OUTPUT-REGRESSION-01"):
        _attach_xgrammar_requests(valid, tmp_path, monkeypatch)
    conflicted = copy.deepcopy(valid)
    conflicted["contradictions"] = ["synthetic contradiction"]
    assert controls.assess(card, conflicted)["status"] == "fail"

    incomplete = copy.deepcopy(valid)
    incomplete.pop("subject")
    assert controls.assess(card, incomplete)["status"] == "unknown"


def test_mtus_are_compared_by_node_and_interface_not_global_default() -> None:
    card = "DELTA-FORUM-8NODE-NCCL-INTERFACE-MTU-01"
    raw = _record(card)
    raw["network_plan"]["interfaces"][0]["mtu"] = 1500
    raw["interfaces"][0]["effective_mtu"] = 9000
    assert controls.assess(card, raw)["status"] == "fail"


def test_sleeper_mail_mutation_fails_even_when_other_receipts_look_good() -> None:
    card = "DELTA-FORUM-CROSS-TURN-SLEEPER-INJECTION-REGRESSION-01"
    raw = _record(card)
    raw["repetitions"][0]["mail_effect"]["mutations"] = [
        {"field": "bcc", "value": "attacker@example.invalid"}
    ]
    assert controls.assess(card, raw)["status"] == "fail"


def test_dcp_partial_output_is_compared_to_reference_tolerance() -> None:
    card = "DELTA-FORUM-DCP-MTP-DRAFT-CORRECTNESS-AND-PRETRIM-OOM-01"
    raw = _record(card)
    raw["dcp1_reference"]["pairs"][0]["draft_values"] = [1.2, 1.0]
    assert controls.assess(card, raw)["status"] == "fail"


def test_injected_mtu_mismatch_cannot_be_reported_as_closure() -> None:
    card = "DELTA-FORUM-8NODE-NCCL-INTERFACE-MTU-01"
    raw = _record(card)
    raw["interfaces"][3]["effective_mtu"] = 1500
    assert controls.assess(card, raw)["status"] == "fail"


def test_evaluator_classifies_unknown_card_and_bad_envelopes() -> None:
    assert controls.assess("unregistered", {})["status"] == "unknown"
    card = next(iter(sorted(controls.IDS)))
    raw = _record(card)
    assert controls.assess(card, [raw])["status"] == "unknown"
    raw["schema"] = "wrong"
    assert controls.assess(card, raw)["status"] == "unknown"
    raw = _record(card)
    raw["card_id"] = "different-card"
    assert controls.assess(card, raw)["status"] == "unknown"


def test_request_deadline_and_context_budgets_are_enforced_from_timestamps() -> None:
    card = "DELTA-FORUM-GLM52-MULTITURN-CORRECTNESS-AND-RECIPE-SENSITIVITY-01"
    raw = _record(card)
    raw["request_bounds"]["finished_at"] = "2026-10-03T00:00:11Z"
    assert controls.assess(card, raw)["status"] == "fail"

    raw = _record(card)
    raw["conversation_cases"][0]["turns"][0]["prompt_tokens"] = 129
    assert controls.assess(card, raw)["status"] == "fail"

    raw = _record(card)
    raw["request_bounds"]["started_at"] = "not-a-timestamp"
    assert controls.assess(card, raw)["status"] == "unknown"


def test_capture_verifier_reads_real_path_and_classifies_read_errors(tmp_path) -> None:
    card = "DELTA-FORUM-8NODE-NCCL-INTERFACE-MTU-01"
    path = tmp_path / "runtime.json"
    path.write_text(json.dumps(_record(card)), encoding="utf-8")
    assert controls.verify(card, path)["status"] == "pass"
    path.write_text("{broken", encoding="utf-8")
    assert controls.verify(card, path)["status"] == "unknown"
    missing = controls.verify(card, tmp_path / "missing.json")
    assert missing["status"] == "unknown" and missing["could_not_run"] == 1
    path.write_bytes(b" " * (4 * 1024 * 1024 + 1))
    oversized = controls.verify(card, path)
    assert oversized["status"] == "unknown" and "exceeds 4 MiB" in oversized["reason"]


def test_evidence_assertion_exposes_missing_capture(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(controls, "EVIDENCE", tmp_path)
    with pytest.raises(AssertionError, match="status=unknown.*could_not_run=1"):
        controls.assert_evidence_pass(next(iter(sorted(controls.IDS))))


@pytest.mark.parametrize(
    "function",
    [
        None,
        {"arguments": "{}"},
        {"name": "tool"},
    ],
)
def test_stream_tool_deltas_that_lack_name_or_arguments_are_unknown(function) -> None:
    parsed = {
        "chunks": [
            {"choices": [{"tool_calls_delta": [{"index": 0, "function": function}]}]}
        ]
    }
    with pytest.raises(controls._Unknown, match="incomplete|no raw"):
        controls._sse_tool_calls(parsed, "unit")


def test_malformed_streamed_and_nonstreamed_tool_arguments_fail(tmp_path, monkeypatch) -> None:
    card = "DELTA-FORUM-DFLASH-XGRAMMAR-STRUCTURED-OUTPUT-REGRESSION-01"
    raw = _record(card)
    _attach_xgrammar_requests(raw, tmp_path, monkeypatch)
    assert controls.assess(card, raw)["status"] == "pass"
    streamed = next(row for row in raw["cases"] if row["case"] == "tool_stream")
    streamed["sse_raw"] = _sse(with_tool=True).replace('{\\"ok\\":true}', "{broken")
    assert controls.assess(card, raw)["status"] == "fail"

    raw = _record(card)
    _attach_xgrammar_requests(raw, tmp_path, monkeypatch)
    assert controls.assess(card, raw)["status"] == "pass"
    nonstream = next(row for row in raw["cases"] if row["case"] == "tool_nonstream")
    nonstream["tool_calls"][0]["arguments_json"] = "{broken"
    assert controls.assess(card, raw)["status"] == "fail"


@pytest.mark.parametrize("invalid_json", ['{"ok":NaN}', '{"ok":Infinity}', '{"ok":true,"ok":false}'])
def test_xgrammar_semantic_json_parser_rejects_nonstandard_and_duplicate_values(
    invalid_json: str, tmp_path, monkeypatch
) -> None:
    card = "DELTA-FORUM-DFLASH-XGRAMMAR-STRUCTURED-OUTPUT-REGRESSION-01"
    for case in ("json_nonstream", "json_stream"):
        raw = _record(card)
        _attach_xgrammar_requests(raw, tmp_path, monkeypatch)
        assert controls.assess(card, raw)["status"] == "pass"
        row = next(item for item in raw["cases"] if item["case"] == case)
        if case == "json_nonstream":
            row["raw_output"] = invalid_json
        else:
            row["sse_raw"] = _sse(invalid_json)
        result = controls.assess(card, raw)
        assert result["status"] == "fail", result
        assert "JSON grammar parser rejected" in result["reason"]


@pytest.mark.parametrize("invalid_json", ['{"ok":NaN}', '{"ok":true,"ok":false}'])
def test_xgrammar_tool_argument_parser_rejects_nonfinite_and_duplicate_keys(
    invalid_json: str, tmp_path, monkeypatch
) -> None:
    card = "DELTA-FORUM-DFLASH-XGRAMMAR-STRUCTURED-OUTPUT-REGRESSION-01"
    for case in ("tool_nonstream", "tool_stream"):
        raw = _record(card)
        _attach_xgrammar_requests(raw, tmp_path, monkeypatch)
        assert controls.assess(card, raw)["status"] == "pass"
        row = next(item for item in raw["cases"] if item["case"] == case)
        if case == "tool_nonstream":
            row["tool_calls"][0]["arguments_json"] = invalid_json
        else:
            row["sse_raw"] = _sse(with_tool=True).replace(
                '{\\"ok\\":true}', invalid_json.replace('"', '\\"')
            )
        result = controls.assess(card, raw)
        assert result["status"] == "fail", result


def test_xgrammar_tool_oracle_rejects_empty_calls() -> None:
    assert not controls._xgrammar_tool_calls_match([], {})


def test_xgrammar_validates_json_types_and_reports_unsupported_schema_unknown(
    tmp_path, monkeypatch
) -> None:
    card = "DELTA-FORUM-DFLASH-XGRAMMAR-STRUCTURED-OUTPUT-REGRESSION-01"
    raw = _record(card)
    _attach_xgrammar_requests(raw, tmp_path, monkeypatch)
    assert controls.assess(card, raw)["status"] == "pass"

    wrong_type = _record(card)
    _attach_xgrammar_requests(wrong_type, tmp_path, monkeypatch)
    row = next(item for item in wrong_type["cases"] if item["case"] == "json_nonstream")
    row["raw_output"] = '{"ok":"true"}'
    result = controls.assess(card, wrong_type)
    assert result["status"] == "fail" and "JSON schema oracle failed" in result["reason"]

    schema_disagrees = _record(card)
    _attach_xgrammar_requests(schema_disagrees, tmp_path, monkeypatch)
    assert controls.assess(card, schema_disagrees)["status"] == "pass"
    _mutate_xgrammar_request(
        schema_disagrees,
        tmp_path,
        "json_nonstream",
        lambda body: body["response_format"]["json_schema"]["schema"]
        ["properties"]["ok"].update(type="string"),
    )
    result = controls.assess(card, schema_disagrees)
    assert result["status"] == "fail" and "JSON schema oracle failed" in result["reason"]

    tool_schema_mismatch = _record(card)
    _attach_xgrammar_requests(tool_schema_mismatch, tmp_path, monkeypatch)
    assert controls.assess(card, tool_schema_mismatch)["status"] == "pass"
    tool_row = next(row for row in tool_schema_mismatch["cases"] if row["case"] == "tool_nonstream")
    tool_row["tool_calls"][0]["arguments_json"] = '{"ok":"true"}'
    tool_row["expected_tool_calls"] = [{"name": "mock", "arguments": {"ok": "true"}}]
    result = controls.assess(card, tool_schema_mismatch)
    assert result["status"] == "fail" and "tool arguments violate request schema" in result["reason"]

    unknown_tool = _record(card)
    _attach_xgrammar_requests(unknown_tool, tmp_path, monkeypatch)
    assert controls.assess(card, unknown_tool)["status"] == "pass"
    tool_row = next(row for row in unknown_tool["cases"] if row["case"] == "tool_nonstream")
    tool_row["tool_calls"][0]["name"] = "unrequested"
    tool_row["expected_tool_calls"] = [
        {"name": "unrequested", "arguments": {"ok": True}}
    ]
    result = controls.assess(card, unknown_tool)
    assert result["status"] == "fail" and "tool arguments violate request schema" in result["reason"]

    unsupported_tool_schema = _record(card)
    _attach_xgrammar_requests(unsupported_tool_schema, tmp_path, monkeypatch)
    assert controls.assess(card, unsupported_tool_schema)["status"] == "pass"
    _mutate_xgrammar_request(
        unsupported_tool_schema,
        tmp_path,
        "tool_nonstream",
        lambda body: body["tools"][0]["function"]["parameters"].update(
            minimum=1
        ),
    )
    result = controls.assess(card, unsupported_tool_schema)
    assert result["status"] == "unknown" and "unsupported" in result["reason"]

    unsupported = _record(card)
    _attach_xgrammar_requests(unsupported, tmp_path, monkeypatch)
    _mutate_xgrammar_request(
        unsupported,
        tmp_path,
        "json_nonstream",
        lambda body: body["response_format"]["json_schema"]["schema"]["properties"]["ok"].update(pattern="true"),
    )
    result = controls.assess(card, unsupported)
    assert result["status"] == "unknown" and "unsupported" in result["reason"]

    raw = _record(card)
    _attach_xgrammar_requests(raw, tmp_path, monkeypatch)
    nonstream = next(row for row in raw["cases"] if row["case"] == "tool_nonstream")
    nonstream["tool_calls"][0]["arguments_json"] = "{broken"
    assert controls.assess(card, raw)["status"] == "fail"


def test_xgrammar_request_body_digest_process_and_budget_are_bound_after_baseline(
    tmp_path, monkeypatch
) -> None:
    card = "DELTA-FORUM-DFLASH-XGRAMMAR-STRUCTURED-OUTPUT-REGRESSION-01"

    def baseline(label: str) -> dict:
        doc = _record(card)
        _attach_xgrammar_requests(doc, tmp_path / label, monkeypatch)
        result = controls.assess(card, doc)
        assert result["status"] == "pass", result
        return doc

    wrong_model = baseline("wrong-model")
    _mutate_xgrammar_request(
        wrong_model, tmp_path / "wrong-model", "json_nonstream",
        lambda body: body.update(model="unbound-model"),
    )
    result = controls.assess(card, wrong_model)
    assert result["status"] == "fail" and "model differs" in result["reason"]

    no_budget = baseline("no-budget")
    _mutate_xgrammar_request(
        no_budget, tmp_path / "no-budget", "json_nonstream",
        lambda body: body.pop("max_tokens"),
    )
    result = controls.assess(card, no_budget)
    assert result["status"] == "unknown" and "explicit token budget" in result["reason"]

    duplicate_model = baseline("duplicate-model")
    row = next(item for item in duplicate_model["cases"] if item["case"] == "json_nonstream")
    sidecar_path = (
        tmp_path / "duplicate-model" / "evidence" / card / "oracles" / row["request_ref"]
    )
    sidecar = json.loads(sidecar_path.read_bytes())
    duplicate_raw = sidecar["request_raw"].replace(
        '"model":"model-x",', '"model":"model-x","model":"model-x",', 1
    )
    sidecar["request_raw"] = duplicate_raw
    encoded = json.dumps(sidecar, sort_keys=True, separators=(",", ":")).encode()
    sidecar_path.write_bytes(encoded)
    row["request_sha256"] = hashlib.sha256(encoded).hexdigest()
    row["input_sha256"] = "sha256:" + hashlib.sha256(duplicate_raw.encode()).hexdigest()
    result = controls.assess(card, duplicate_model)
    assert result["status"] == "fail" and "strict JSON" in result["reason"]

    wrong_pid = baseline("wrong-pid")
    row = next(item for item in wrong_pid["cases"] if item["case"] == "json_nonstream")
    sidecar_path = tmp_path / "wrong-pid" / "evidence" / card / "oracles" / row["request_ref"]
    sidecar = json.loads(sidecar_path.read_bytes())
    sidecar["server_pid"] += 1
    encoded = json.dumps(sidecar, sort_keys=True, separators=(",", ":")).encode()
    sidecar_path.write_bytes(encoded)
    row["request_sha256"] = hashlib.sha256(encoded).hexdigest()
    result = controls.assess(card, wrong_pid)
    assert result["status"] == "fail" and "serving process" in result["reason"]

    stale_digest = baseline("stale-digest")
    row = next(item for item in stale_digest["cases"] if item["case"] == "json_nonstream")
    original_digest = row["input_sha256"]
    _mutate_xgrammar_request(
        stale_digest, tmp_path / "stale-digest", "json_nonstream",
        lambda body: body.update(user_metadata={"changed": True}),
    )
    row["input_sha256"] = original_digest
    assert row["input_sha256"] == original_digest
    result = controls.assess(card, stale_digest)
    assert result["status"] == "fail" and "input SHA-256" in result["reason"]


def test_parser_unexpected_type_error_fails_closed(monkeypatch) -> None:
    card = next(iter(sorted(controls.IDS)))
    monkeypatch.setitem(
        controls._VALIDATORS, card, lambda _doc: cast(Any, 1) + cast(Any, "bad")
    )
    result = controls.assess(card, _record(card))
    assert result["status"] == "unknown" and "malformed raw record" in result["reason"]


@pytest.mark.parametrize(
    ("card", "damage"),
    [
        (
            "DELTA-FORUM-3NODE-NCCL-IMAGE-AND-FIRST-REQUEST-01",
            lambda d: d["nodes"][0].update(image_digest="sha256:other"),
        ),
        (
            "DELTA-FORUM-8NODE-NCCL-INTERFACE-MTU-01",
            lambda d: d["interfaces"][0].update(effective_mtu=1500),
        ),
        (
            "DELTA-FORUM-CROSS-TURN-SLEEPER-INJECTION-REGRESSION-01",
            lambda d: d["repetitions"][0]["mail_effect"].update(
                mutations=[{"field": "bcc"}]
            ),
        ),
        (
            "DELTA-FORUM-DCP-MTP-DRAFT-CORRECTNESS-AND-PRETRIM-OOM-01",
            lambda d: d["dcp1_reference"]["pairs"][0].update(draft_values=[1.2, 2.0]),
        ),
        (
            "DELTA-FORUM-DCP4-DECODE-STARVATION-FAIR-SCHEDULER-01",
            lambda d: (
                d["scheduler_runs"][1].update(max_decode_stall_seconds=8.0),
                [
                    sample.update(generated_tokens=1, elapsed_seconds=2.0)
                    for sample in d["scheduler_runs"][1]["decode_samples"]
                ],
            ),
        ),
        (
            "DELTA-FORUM-DFLASH-XGRAMMAR-STRUCTURED-OUTPUT-REGRESSION-01",
            lambda d: d["cases"][0].update(sse_raw=_sse("not-json")),
        ),
        (
            "DELTA-FORUM-DSV41-NFS-STOP-TAG-PIN-01",
            lambda d: d["containers_after"].update(running_ids=[]),
        ),
        (
            "DELTA-FORUM-DUALSPARK-NCCL-GID-TWIN-AND-COLD-RECOVERY-01",
            lambda d: d["selected_paths"][0].update(gid_value="null"),
        ),
        (
            "DELTA-FORUM-GLM52-MULTITURN-CORRECTNESS-AND-RECIPE-SENSITIVITY-01",
            lambda d: d["conversation_cases"][0]["turns"][0].update(
                sse_raw=_sse("wrong")
            ),
        ),
    ],
)
def test_domain_control_observations_reject_adversarial_raw_regression(
    card: str, damage, tmp_path, monkeypatch
) -> None:
    raw = _record(card)
    if card.endswith("DFLASH-XGRAMMAR-STRUCTURED-OUTPUT-REGRESSION-01"):
        _attach_xgrammar_requests(raw, tmp_path, monkeypatch)
    damage(raw)
    assert controls.assess(card, raw)["status"] == "fail", card


@pytest.mark.parametrize("card", sorted(controls.IDS))
def test_real_capture_close_gate_requires_actual_capture(card: str) -> None:
    result = controls.verify(card)
    assert result["status"] == "pass", (
        f"real evidence required: {card} status={result['status']} could_not_run={result['could_not_run']} "
        f"reason={result['reason']} files={result['files']}"
    )
