"""Parser and predicate controls for batch 02; fixtures never count as lab evidence."""
from __future__ import annotations

import copy
import hashlib
import json
from typing import Any

import pytest

from tools import runtime_batch02_controls as controls
from test_openclaw_contract import _bundle as _openclaw_bundle


def _base(card: str) -> dict[str, Any]:
    return {
        "schema": "bb.runtime.raw.v1",
        "card_id": card,
        "capture_id": "unit-only",
        "captured_at": "2026-10-03T00:00:00Z",
        "contradictions": [],
        "subject": {
            "oem": "OEM-X", "host_id": "host-a", "image_digest": "sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
            "model": "model-x", "checkpoint_digest": "sha256:bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
            "software_versions": {
                "engine": "engine-1", "ray": "ray-1", "vllm": "vllm-1", "torch": "torch-1",
                "cuda": "cuda-1", "nccl": "nccl-1", "container_commit": "1111111111111111111111111111111111111111",
                "llama_cpp_commit": "2222222222222222222222222222222222222222", "os": "os-1", "kernel": "kernel-1",
                "driver": "driver-1", "ggml_cuda": "ggml-1", "harness": "harness-1",
                "runtime": "runtime-1", "runtime_commit": "3333333333333333333333333333333333333333", "kv_cache_format": "kv-1",
                "flashinfer": "flashinfer-1", "quantization": "NVFP4", "parser": "parser-1",
                "mtp_tokens": "2", "tokenizer": "tokenizer-1", "image": "image-1",
                "model": "model-x", "backend": "backend-1", "launcher_digest": "4444444444444444444444444444444444444444",
                "sglang": "sglang-1", "sgl_kernel": "sgl-1", "openclaw": "openclaw-1",
                "inductor": "inductor-1", "systemd": "systemd-1", "sampling": "sampling-1",
                "template": "template-1", "kv_cache": "kv-1", "mtp": "mtp-1",
            },
        },
        "request_bounds": {
            "request_id": "req-1", "model": "model-x",
            "checkpoint_digest": "sha256:bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb", "max_tokens": 16,
            "max_context_tokens": 128, "deadline_seconds": 10,
            "started_at": "2026-10-03T00:00:00Z", "finished_at": "2026-10-03T00:00:10Z",
        },
        "rollback_record": {
            "known_good_digest": "sha256:cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc", "candidate_digest": "sha256:dddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddd",
            "procedure_ref": "rollback.md", "before_state_sha256": "sha256:eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee",
            "after_restore_sha256": "sha256:eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee",
        },
    }


def _sse(content: str) -> str:
    frames = [
        {"id": "c1", "object": "chat.completion.chunk", "choices": [
            {"index": 0, "delta": {"content": content}, "finish_reason": None}]},
        {"id": "c1", "object": "chat.completion.chunk", "choices": [
            {"index": 0, "delta": {}, "finish_reason": "stop"}]},
    ]
    return "".join(f"data: {json.dumps(row)}\n\n" for row in frames) + "data: [DONE]\n\n"


def _tool_sse(content: str = "answer", completion_id: str = "c", usage: bool = False) -> str:
    first = {"id": completion_id, "object": "chat.completion.chunk", "choices": [{"index": 0,
        "delta": {"content": content, "tool_calls": [{"index": 0, "id": "t", "type": "function",
                   "function": {"name": "mock", "arguments": '{"ok":true}'}}]},
        "finish_reason": None}]}
    last = {"id": completion_id, "object": "chat.completion.chunk", "choices": [
        {"index": 0, "delta": {}, "finish_reason": "tool_calls"}]}
    if usage:
        last["usage"] = {"prompt_tokens": 7, "completion_tokens": 1, "total_tokens": 8}
    return f"data: {json.dumps(first)}\n\ndata: {json.dumps(last)}\n\ndata: [DONE]\n\n"


def _ray() -> dict[str, Any]:
    card = "DELTA-FORUM-GPTOSS-MULTINODE-RAY-CHANNEL-TIMEOUT-01"
    doc = _base(card)
    doc.update({
        "nodes": [{"node_id": "n1"}, {"node_id": "n2"}],
        "ranks": [
            {"node_id": "n1", "gpu_count": 1, "tp_rank": 0},
            {"node_id": "n2", "gpu_count": 1, "tp_rank": 1},
        ],
        "placement_group": {"bundle_count": 2, "tp_size": 2, "bundle_gpu_counts": [1, 1]},
        "request_trace": {"request_id": "req-1", "node_events": [
            {"first_token_at": "2026-10-03T00:00:00.5Z", "finish_reason": "stop"},
            {"first_token_at": "2026-10-03T00:00:00.6Z", "finish_reason": "stop"}],
            "output_tokens": 4},
        "timeout_control": {"kind": "bounded_timeout", "elapsed_seconds": 1,
            "error_class": "RayChannelTimeoutError"},
    })
    return doc


def _mtp() -> dict[str, Any]:
    card = "DELTA-FORUM-MTP-ACCEPTANCE-AND-SEMANTIC-CONTROL-01"
    doc = _base(card)
    doc.update({
        "token_pairs": [{"position": 0, "draft_token": "a", "target_token": "a"},
                        {"position": 1, "draft_token": "b", "target_token": "c"}],
        "reported_acceptance_by_position": [True, False],
        "semantic_oracle": {"request_id": "req-1", "observed_output": "correct", "expected_output": "correct"},
        "negative_control": {"draft_token": "x", "target_token": "y", "emitted_token": "y"},
    })
    return doc


def _nemotron() -> dict[str, Any]:
    card = "DELTA-FORUM-NEMOTRON-SM121-PREBUILT-KERNEL-01"
    doc = _base(card)
    doc["subject"]["sm_arch"] = "sm_121"
    doc.update({
        "required_operations": ["rmsnorm", "quant"],
        "architecture_kernel_matrix": [
            {"sm_arch": "sm_121", "operation": op, "kernel_name": f"{op}_sm121",
             "load_exit_code": 0, "first_inference_exit_code": 0, "raw_output": "kernel launched"}
            for op in ("rmsnorm", "quant")
        ],
        "reference_output": {"request_id": "req-1", "observed": "answer", "expected": "answer"},
        "architecture_negative": {"sm_arch": "sm_100", "required_op": "rmsnorm",
            "argv_sha256": "negative-command", "exit_code": 1, "stderr_raw": "unsupported SM"},
    })
    return doc


def _llamacpp() -> dict[str, Any]:
    card = "DELTA-FORUM-LLAMACPP-RPC-UMA-AND-ORDERLY-TEARDOWN-01"
    doc = _base(card)
    doc.update({
        "rpc": {"client_pid": 10, "server_pid": 11, "request_id": "req-1",
                "server_cgroup_id": "rpc.slice", "transport_observed": "tcp"},
        "functional_result": {"raw_output": "ok", "expected_output": "ok", "kv_sha256": "kv", "finish_reason": "stop"},
        "uma_samples": [{"cgroup_id": "rpc.slice", "timestamp": f"t{i}", "rss_bytes": i, "psi_some_us": i}
                        for i in range(3)],
        "teardown_ab": [
            {"order": "client_first", "trials": [{"exit_code": 0, "terminating_signal": ""}]},
            {"order": "server_first", "trials": [{"exit_code": -6, "terminating_signal": "SIGABRT"}]},
            {"order": "tcp_control", "trials": [{"exit_code": 0, "terminating_signal": ""}]},
        ],
    })
    return doc


def _m2() -> dict[str, Any]:
    card = "DELTA-FORUM-M2-COMPACTION-STATE-VALIDATION-01"
    doc = _base(card)
    doc.update({
        "sessions": [
            {"mode": "compaction", "request_id": "req-1", "transitions": [
                {"before_state_sha256": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa", "after_state_sha256": "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb", "event": "compaction_complete"},
                {"before_state_sha256": "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb", "after_state_sha256": "cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc", "event": "compaction_complete"}],
             "semantic_tool_checks": [{"oracle_text": "answer", "sse_raw": _tool_sse(),
                 "oracle_tool_calls": [{"name": "mock", "arguments": {"ok": True}}]}]},
            {"mode": "clean_reset", "request_id": "req-1", "kv_state_sha256_before_reset": "eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee",
             "kv_state_sha256_after_reset": "eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee", "semantic_tool_checks": [
                {"oracle_text": "answer", "sse_raw": _tool_sse(),
                 "oracle_tool_calls": [{"name": "mock", "arguments": {"ok": True}}]}]},
            {"mode": "no_compaction_control", "request_id": "req-1", "compaction_count": 0,
             "semantic_tool_checks": [{"oracle_text": "answer", "sse_raw": _tool_sse(),
                 "oracle_tool_calls": [{"name": "mock", "arguments": {"ok": True}}]}]},
        ],
        "rawmetrics": [{"name": name, "mode": mode, "request_id": "req-1", "timestamp": f"2026-10-03T00:00:00.{i+1:06d}Z", "value": 12.5}
                       for i, (mode, name) in enumerate((mode, name) for mode in ("compaction", "clean_reset", "no_compaction_control")
                           for name in ("prefill_tokens_per_second", "decode_tokens_per_second", "process_rss_bytes", "host_uma_bytes"))],
    })
    return doc


def _minimax() -> dict[str, Any]:
    card = "DELTA-FORUM-MINIMAX-TOOLCALL-FUNCTIONAL-CANARY-01"
    doc = _base(card)
    doc["subject"]["process_pid"] = 99
    tool = "data: " + json.dumps({"id": "c", "object": "chat.completion.chunk", "choices": [
        {"index": 0, "delta": {"tool_calls": [{"index": 0, "id": "t", "type": "function",
            "function": {"name": "mock", "arguments": '{"ok":true}'}}]}, "finish_reason": None}]}) + "\n\n"
    tool += "data: " + json.dumps({"id": "c", "object": "chat.completion.chunk", "choices": [
        {"index": 0, "delta": {}, "finish_reason": "tool_calls"}]}) + "\n\n" + "data: [DONE]\n\n"
    doc.update({
        "sequence": [
            {"step": "plain_text", "request_id": "req-1", "http_status": 200, "process_pid": 99,
             "sse_raw": _sse("before"), "finish_reason": "stop"},
            {"step": "mock_tool", "request_id": "req-1", "http_status": 200, "process_pid": 99,
             "sse_raw": tool, "finish_reason": "stop", "mock_result": {"request_id": "req-1"}},
            {"step": "plain_text_after_tool", "request_id": "req-1", "http_status": 200, "process_pid": 99,
             "sse_raw": _sse("after"), "finish_reason": "stop"},
        ],
        "tool_oracle": {"oracle_ref": "tool.json", "oracle_sha256": ""},
        "warmup_ab": [{"mode": mode, "request_id": "req-1", "rank_events": [
                           {"completed_collectives": 1}, {"completed_collectives": 1}],
                       "finish_reason": "stop", "output": "warmup"}
                      for mode in ("graph", "eager")],
        "checkpoint_ple_manifest": [{"name": "ple.weight_scale"}],
        "loader_ab": [{"mode": mode, "loaded_ple_tensors": [
                           {"name": "ple.weight_scale", "dtype": "fp8", "sha256": "tensor"}]}
                       for mode in ("lazy", "eager")],
    })
    return doc


def _muse() -> dict[str, Any]:
    card = "DELTA-FORUM-MUSE-GLIMMER-DFLASH-MAX-SEQS-GATE-01"
    doc = _base(card)
    doc.update({
        "draft_class_resolution": {"checkpoint_digest": "sha256:bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb", "configured_class": "Draft",
                                   "resolved_class": "Draft"},
        "sequence_runs": [
            {"max_num_seqs": n, "request_id": "req-1",
             "raw_metrics": [{"name": "rss", "unit": "bytes", "value": 10.0}],
             "canaries": [{"kind": "untrusted_tool" if n == 32 else "text", "expected": "ok", "observed": "ok"}]}
            for n in (32, 33)
        ],
    })
    return doc


def _nccl() -> dict[str, Any]:
    card = "DELTA-FORUM-NCCL-TP-ORCHESTRATION-CORRECTION-01"
    doc = _base(card)
    doc.update({
        "nodes": [{"node_id": f"n{i}", "launcher_argv_sha256": "argv", "effective_nccl_env_sha256": "env",
                   "interface": "eth0", "subnet": "10.0.0.0/24"} for i in range(2)],
        "nccl_microtest": {"command_sha256": "allreduce", "rank_results": [
            {"exit_code": 0, "bus_bandwidth_gbps": 10.0} for _ in range(2)]},
        "recipe_manual_ab": [{"mode": mode, "request_id": "req-1", "rank_logs": [{}, {}],
                              "output_tokens": 3, "output": "same", "finish_reason": "stop"}
                             for mode in ("recipe_launcher", "manual")],
    })
    return doc


def _openclaw() -> dict[str, Any]:
    card = "DELTA-FORUM-OPENCLAW-VLLM-REQUEST-CONTRACT-01"
    doc = _base(card)
    bundle = _openclaw_bundle()
    doc["openclaw_bundle"] = bundle
    doc["request_negatives"] = [
        {"case": "wrong_model_404", "request_model": "absent", "http_status": 404},
        {"case": "context_overflow", "input_tokens": 131073, "http_status": 400},
        {"case": "negative_max_tokens", "max_tokens": -1, "http_status": 400},
    ]
    tool = "data: " + json.dumps({"id": "c", "object": "chat.completion.chunk", "choices": [
        {"index": 0, "delta": {"tool_calls": [{"index": 0, "id": "t", "type": "function",
            "function": {"name": "mock", "arguments": '{"ok":true}'}}]}, "finish_reason": None}]}) + "\n\n"
    tool += "data: " + json.dumps({"id": "c", "object": "chat.completion.chunk", "choices": [
        {"index": 0, "delta": {}, "finish_reason": "tool_calls"}]}) + "\n\n" + "data: [DONE]\n\n"
    doc["positive_request"] = {"raw_request": {"model": "gpt-oss-120b"}, "raw_response": {"status_code": 200},
                               "sse_raw": tool, "expected_tool_calls": [{"name": "mock", "arguments": {"ok": True}}]}
    return doc


def _cold_compile() -> dict[str, Any]:
    card = "DELTA-FORUM-QWEN-COLD-COMPILE-OOM-01"
    doc = _base(card)
    doc.update({
        "rank_cold_compile": [{"node_id": f"n{i}", "rank": i, "compile_log_sha256": "log",
                               "request_id": "req-1", "compile_exit_code": 0,
                               "memory_series": [{"timestamp": "t0", "available_bytes": 100, "used_bytes": 20},
                                                 {"timestamp": "t1", "available_bytes": 90, "used_bytes": 30}]}
                              for i in range(2)],
        "eager_control": {"request_id": "req-1", "compilation_mode": 0, "output_tokens": 2},
        "remote_access_series": [{"timestamp": "t", "ssh_exit_code": 0, "icmp_exit_code": 0,
                                  "ssh_command_sha256": "ssh", "icmp_command_sha256": "ping"}],
    })
    return doc


def _attach_oracles(doc: dict[str, Any], tmp_path: Any, monkeypatch: Any) -> None:
    root = tmp_path / "evidence"
    card_oracles = root / doc["card_id"] / "oracles"
    card_oracles.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(controls, "EVIDENCE", root)
    if "sessions" in doc:
        for session in doc["sessions"]:
            for check in session.get("semantic_tool_checks", []):
                payload = {"text": check.pop("oracle_text"), "tool_calls": check["oracle_tool_calls"]}
                raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
                check["oracle_ref"] = f"{session['mode']}.json"
                check["oracle_sha256"] = hashlib.sha256(raw).hexdigest()
                (card_oracles / check["oracle_ref"]).write_bytes(raw)
    elif "tool_oracle" in doc:
        payload = {"tool_call": {"name": "mock", "arguments": {"ok": True}}}
        raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        doc["tool_oracle"]["oracle_sha256"] = hashlib.sha256(raw).hexdigest()
        (card_oracles / doc["tool_oracle"]["oracle_ref"]).write_bytes(raw)


@pytest.mark.parametrize("factory", [_ray, _llamacpp, _m2, _minimax, _mtp, _muse, _nccl, _nemotron,
                                     _openclaw, _cold_compile])
def test_raw_domain_fixture_passes_and_mutated_measurement_fails(factory: Any, tmp_path: Any, monkeypatch: Any) -> None:
    valid = factory()
    _attach_oracles(valid, tmp_path, monkeypatch)
    assert controls.assess(valid["card_id"], valid)["status"] == "pass"
    corrupted = copy.deepcopy(valid)
    if "sessions" in corrupted:
        corrupted["sessions"][0]["semantic_tool_checks"][0]["sse_raw"] = _tool_sse("wrong")
    elif "reported_acceptance_by_position" in corrupted:
        corrupted["reported_acceptance_by_position"][0] = False
    elif "architecture_kernel_matrix" in corrupted:
        corrupted["architecture_kernel_matrix"][0]["load_exit_code"] = 127
    elif "teardown_ab" in corrupted:
        corrupted["teardown_ab"][0]["trials"][0]["terminating_signal"] = "SIGABRT"
    elif "sequence" in corrupted:
        corrupted["sequence"][1]["http_status"] = 500
    elif "sequence_runs" in corrupted:
        corrupted["sequence_runs"][1]["canaries"][0]["observed"] = "wrong"
    elif "recipe_manual_ab" in corrupted:
        corrupted["recipe_manual_ab"][1]["output"] = "wrong"
    elif "request_negatives" in corrupted:
        corrupted["request_negatives"][0]["http_status"] = 200
    elif "rank_cold_compile" in corrupted:
        corrupted["remote_access_series"][0]["ssh_exit_code"] = 255
    else:
        corrupted["request_trace"]["output_tokens"] = 17
    result = controls.assess(corrupted["card_id"], corrupted)
    assert result["status"] == "fail", result


@pytest.mark.parametrize("boolean", [False, True])
@pytest.mark.parametrize("field", ["load_exit_code", "first_inference_exit_code"])
def test_nemotron_boolean_kernel_return_codes_are_unknown(field: str, boolean: bool) -> None:
    doc = _nemotron()
    doc["architecture_kernel_matrix"][0][field] = boolean

    result = controls.assess(doc["card_id"], doc)

    assert result["status"] == "unknown", result


@pytest.mark.parametrize("boolean", [False, True])
def test_cold_compile_boolean_return_code_is_unknown(boolean: bool) -> None:
    doc = _cold_compile()
    doc["rank_cold_compile"][0]["compile_exit_code"] = boolean

    result = controls.assess(doc["card_id"], doc)

    assert result["status"] == "unknown", result


def test_malformed_nested_sse_is_unknown_not_an_uncaught_exception(tmp_path: Any, monkeypatch: Any) -> None:
    card = "DELTA-FORUM-M2-COMPACTION-STATE-VALIDATION-01"
    doc = _base(card)
    doc.update({
        "sessions": [
            {"mode": "compaction", "request_id": "req-1", "transitions": [
                {"before_state_sha256": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa", "after_state_sha256": "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb", "event": "compaction_complete"},
                {"before_state_sha256": "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb", "after_state_sha256": "cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc", "event": "compaction_complete"}],
             "semantic_tool_checks": [{"oracle_text": "x", "oracle_sha256": "oracle", "sse_raw": "data: {}\n\n",
                 "oracle_tool_calls": []}]},
            {"mode": "clean_reset", "request_id": "req-1", "kv_state_sha256_before_reset": "eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee",
             "kv_state_sha256_after_reset": "eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee", "semantic_tool_checks": [
                {"oracle_text": "x", "oracle_sha256": "oracle", "sse_raw": "data: {}\n\n", "oracle_tool_calls": []}]},
            {"mode": "no_compaction_control", "request_id": "req-1", "compaction_count": 0,
             "semantic_tool_checks": [{"oracle_text": "x", "oracle_sha256": "oracle", "sse_raw": "data: {}\n\n",
                 "oracle_tool_calls": []}]},
        ],
        "rawmetrics": [{"name": name, "mode": mode, "request_id": "req-1", "timestamp": f"2026-10-03T00:00:00.{i+1:06d}Z", "value": 10}
                       for i, (mode, name) in enumerate((mode, name) for mode in ("compaction", "clean_reset", "no_compaction_control")
                           for name in ("prefill_tokens_per_second", "decode_tokens_per_second", "process_rss_bytes", "host_uma_bytes"))],
    })
    _attach_oracles(doc, tmp_path, monkeypatch)
    result = controls.assess(card, doc)
    assert result["status"] == "unknown"
    assert result["could_not_run"] == 1


def test_unknown_card_and_malformed_nested_record_are_cnr() -> None:
    assert controls.assess("unknown-card", {})["status"] == "unknown"
    card = "DELTA-FORUM-GPTOSS-MULTINODE-RAY-CHANNEL-TIMEOUT-01"
    doc = _ray()
    doc["request_trace"]["node_events"][0] = None
    result = controls.assess(card, doc)
    assert result["status"] == "unknown"
    assert result["could_not_run"] == 1


def test_minimax_missing_process_pid_cannot_pass_via_none_equality(tmp_path: Any, monkeypatch: Any) -> None:
    doc = _minimax()
    _attach_oracles(doc, tmp_path, monkeypatch)
    assert controls.assess(doc["card_id"], doc)["status"] == "pass"
    del doc["subject"]["process_pid"]
    result = controls.assess(doc["card_id"], doc)
    assert result["status"] == "unknown"
    assert result["could_not_run"] == 1
    assert "PID" in result["reason"]


def test_full_sha256_subject_and_pinned_stack_are_required() -> None:
    doc = _ray()
    assert controls.assess(doc["card_id"], doc)["status"] == "pass"
    doc["subject"]["image_digest"] = "sha256:image"
    assert controls.assess(doc["card_id"], doc)["status"] == "unknown"
    doc = _ray()
    assert controls.assess(doc["card_id"], doc)["status"] == "pass"
    del doc["subject"]["software_versions"]["nccl"]
    assert controls.assess(doc["card_id"], doc)["status"] == "unknown"


def test_independent_oracle_missing_or_hash_mismatch_cannot_pass(tmp_path: Any, monkeypatch: Any) -> None:
    doc = _m2()
    _attach_oracles(doc, tmp_path, monkeypatch)
    assert controls.assess(doc["card_id"], doc)["status"] == "pass"
    oracle = tmp_path / "evidence" / doc["card_id"] / "oracles" / "compaction.json"
    oracle.unlink()
    assert controls.assess(doc["card_id"], doc)["status"] == "unknown"
    doc = _m2()
    _attach_oracles(doc, tmp_path / "second", monkeypatch)
    assert controls.assess(doc["card_id"], doc)["status"] == "pass"
    doc["sessions"][0]["semantic_tool_checks"][0]["oracle_sha256"] = "0" * 64
    assert controls.assess(doc["card_id"], doc)["status"] == "fail"


def test_malformed_oracle_json_is_cnr(tmp_path: Any, monkeypatch: Any) -> None:
    doc = _m2()
    _attach_oracles(doc, tmp_path, monkeypatch)
    reference = doc["sessions"][0]["semantic_tool_checks"][0]
    oracle = tmp_path / "evidence" / doc["card_id"] / "oracles" / reference["oracle_ref"]
    oracle.write_bytes(b"\xff")
    reference["oracle_sha256"] = hashlib.sha256(b"\xff").hexdigest()
    result = controls.assess(doc["card_id"], doc)
    assert result["status"] == "unknown"
    assert result["could_not_run"] == 1


def test_ray_rejects_bool_as_gpu_rank_or_token_integer_and_negative_timeout() -> None:
    doc = _ray()
    assert controls.assess(doc["card_id"], doc)["status"] == "pass"
    doc["ranks"][0]["gpu_count"] = True
    result = controls.assess(doc["card_id"], doc)
    assert result["status"] == "unknown"
    doc = _ray()
    assert controls.assess(doc["card_id"], doc)["status"] == "pass"
    doc["timeout_control"]["elapsed_seconds"] = -0.1
    result = controls.assess(doc["card_id"], doc)
    assert result["status"] == "fail"


def test_m2_requires_complete_host_process_and_decode_metric_matrix(tmp_path: Any, monkeypatch: Any) -> None:
    doc = _m2()
    _attach_oracles(doc, tmp_path, monkeypatch)
    assert controls.assess(doc["card_id"], doc)["status"] == "pass"
    doc["rawmetrics"].pop()
    result = controls.assess(doc["card_id"], doc)
    assert result["status"] == "unknown"
    assert "metrics" in result["reason"]
    doc = _m2()
    _attach_oracles(doc, tmp_path / "nan", monkeypatch)
    assert controls.assess(doc["card_id"], doc)["status"] == "pass"
    doc["rawmetrics"][0]["value"] = float("nan")
    result = controls.assess(doc["card_id"], doc)
    assert result["status"] == "unknown"
    assert "metric" in result["reason"]


def test_reader_bounds_raw_json_and_preserves_missing_as_cnr(tmp_path: Any) -> None:
    card = "DELTA-FORUM-GPTOSS-MULTINODE-RAY-CHANNEL-TIMEOUT-01"
    too_large = tmp_path / "large.json"
    too_large.write_bytes(b" " * (4 * 1024 * 1024 + 1))
    assert controls.verify(card, too_large)["status"] == "unknown"
    missing = controls.verify(card, tmp_path / "missing.json")
    assert missing["status"] == "unknown"
    assert missing["could_not_run"] == 1
    invalid_utf8 = tmp_path / "invalid-utf8.json"
    invalid_utf8.write_bytes(b"\xff")
    assert controls.verify(card, invalid_utf8)["status"] == "unknown"
    valid = tmp_path / "valid.json"
    valid.write_text(json.dumps(_ray()), encoding="utf-8")
    assert controls.verify(card, valid)["status"] == "pass"


@pytest.mark.parametrize("card", sorted(controls.IDS))
def test_real_capture_close_gate_requires_raw_capture(card: str) -> None:
    result = controls.verify(card)
    assert result["status"] == "pass", (
        f"{card}: status={result['status']} could_not_run={result['could_not_run']} "
        f"reason={result['reason']} files={result.get('files', [])}"
    )
