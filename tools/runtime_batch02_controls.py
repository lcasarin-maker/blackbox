"""Card-specific raw-data predicates for generated runtime batch 02."""
from __future__ import annotations

import hashlib
import json
import math
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, cast

from tools.capture_io import read_regular_bytes, strict_json_loads
from tools.openclaw_contract import analyze as analyze_openclaw_contract
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

IDS = {
    "DELTA-FORUM-GPTOSS-MULTINODE-RAY-CHANNEL-TIMEOUT-01",
    "DELTA-FORUM-LLAMACPP-RPC-UMA-AND-ORDERLY-TEARDOWN-01",
    "DELTA-FORUM-M2-COMPACTION-STATE-VALIDATION-01",
    "DELTA-FORUM-MINIMAX-TOOLCALL-FUNCTIONAL-CANARY-01",
    "DELTA-FORUM-MTP-ACCEPTANCE-AND-SEMANTIC-CONTROL-01",
    "DELTA-FORUM-MUSE-GLIMMER-DFLASH-MAX-SEQS-GATE-01",
    "DELTA-FORUM-NCCL-TP-ORCHESTRATION-CORRECTION-01",
    "DELTA-FORUM-NEMOTRON-SM121-PREBUILT-KERNEL-01",
    "DELTA-FORUM-OPENCLAW-VLLM-REQUEST-CONTRACT-01",
    "DELTA-FORUM-QWEN-COLD-COMPILE-OOM-01",
}


def _ray(doc: dict[str, Any]) -> None:
    req = _request_binding(doc)
    _stack(doc, ("ray", "vllm", "torch", "cuda", "nccl", "container_commit"))
    nodes = doc.get("nodes")
    _need(isinstance(nodes, list) and len(nodes) == 2, "two-node Ray capture absent")
    nodes = cast(list[Any], nodes)
    node_ids = {n.get("node_id") for n in nodes if isinstance(n, dict)}
    _contradiction(len(node_ids) == 2, "Ray node identities duplicate")
    ranks = doc.get("ranks")
    _need(isinstance(ranks, list) and len(ranks) >= 2, "rank/resource capture absent")
    ranks = cast(list[Any], ranks)
    rank_nodes = set()
    for rank in ranks:
        _need(isinstance(rank, dict) and _text(rank.get("node_id"))
              and _integer(rank.get("gpu_count")) and _integer(rank.get("tp_rank")),
              "rank lacks node/GPU/TP resource data")
        rank_nodes.add(rank["node_id"])
    _contradiction(rank_nodes == node_ids and all(r["gpu_count"] >= 1 for r in ranks),
                   "placement does not reserve GPUs on both target nodes")
    placement = _obj(doc.get("placement_group"), "Ray placement-group details absent")
    _need(placement.get("bundle_count") == 2 and placement.get("tp_size") == 2
          and isinstance(placement.get("bundle_gpu_counts"), list)
          and len(placement["bundle_gpu_counts"]) == 2, "TP2 placement bundles incomplete")
    bundle_gpu_counts = cast(list[Any], placement["bundle_gpu_counts"])
    _need(all(_integer(n) and n >= 0 for n in bundle_gpu_counts), "placement GPU counts must be nonnegative integers")
    _contradiction(all(n >= 1 for n in bundle_gpu_counts),
                   "placement-group bundle lacks a required GPU")
    request = _obj(doc.get("request_trace"), "bounded request trace absent")
    _need(request.get("request_id") == req["request_id"]
          and isinstance(request.get("node_events"), list) and len(request["node_events"]) == 2,
          "inference request is not bound to both nodes")
    node_events = cast(list[Any], request["node_events"])
    start = datetime.fromisoformat(req["started_at"].replace("Z", "+00:00"))
    finish = datetime.fromisoformat(req["finished_at"].replace("Z", "+00:00"))
    first_tokens = []
    for event in node_events:
        _need(_text(event.get("first_token_at")), "per-node first-token timestamp absent")
        first_tokens.append(datetime.fromisoformat(event["first_token_at"].replace("Z", "+00:00")))
    _contradiction(all(start <= token <= finish for token in first_tokens)
                   and all(e.get("finish_reason") == "stop"
                           and e.get("error_class") in (None, "") for e in node_events),
                   "candidate request timed out or failed to progress on a node")
    _need(_integer(request.get("output_tokens")) and request["output_tokens"] > 0,
          "request output count absent")
    _contradiction(request["output_tokens"] <= req["max_tokens"], "output token ceiling exceeded")
    control = _obj(doc.get("timeout_control"), "captured timeout-negative case absent")
    _need(control.get("kind") == "bounded_timeout" and _finite_number(control.get("elapsed_seconds")),
          "bounded timeout control lacks raw elapsed time")
    _contradiction(control.get("error_class") == "RayChannelTimeoutError"
                   and 0 <= control["elapsed_seconds"] <= req["deadline_seconds"],
                   "timeout negative was not rejected within the request budget")
    _rollback(doc)


def _llamacpp(doc: dict[str, Any]) -> None:
    req = _request_binding(doc)
    _stack(doc, ("llama_cpp_commit", "os", "kernel", "driver", "ggml_cuda"))
    rpc = _obj(doc.get("rpc"), "llama.cpp RPC process capture absent")
    _need(_integer(rpc.get("client_pid")) and rpc["client_pid"] > 0
          and _integer(rpc.get("server_pid")) and rpc["server_pid"] > 0
          and rpc.get("request_id") == req["request_id"] and _text(rpc.get("transport_observed")),
          "RPC client/server identity or effective transport absent")
    _contradiction(rpc["client_pid"] != rpc["server_pid"], "RPC client/server PID identity collision")
    result = _obj(doc.get("functional_result"), "functional RPC output absent")
    _need(_text(result.get("raw_output")) and _text(result.get("expected_output"))
          and _text(result.get("kv_sha256")) and result.get("finish_reason") == "stop",
          "functional output/KV/finish evidence incomplete")
    _contradiction(result["raw_output"] == result["expected_output"], "functional output differs from oracle")
    uma = doc.get("uma_samples")
    _need(isinstance(uma, list) and len(uma) >= 3, "attributed UMA/cgroup samples absent")
    uma = cast(list[Any], uma)
    for sample in uma:
        _need(isinstance(sample, dict) and sample.get("cgroup_id") == rpc.get("server_cgroup_id")
              and _text(sample.get("timestamp")) and _integer(sample.get("rss_bytes"))
              and _integer(sample.get("psi_some_us")) and sample["rss_bytes"] >= 0 and sample["psi_some_us"] >= 0, "memory/PSI data is not attributed to RPC server")
    teardown = doc.get("teardown_ab")
    _need(isinstance(teardown, list) and {x.get("order") for x in teardown if isinstance(x, dict)}
          == {"client_first", "server_first", "tcp_control"}, "orderly teardown A/B/control missing")
    teardown = cast(list[Any], teardown)
    rows = {x["order"]: x for x in teardown}
    for row in teardown:
        _need(isinstance(row.get("trials"), list) and row["trials"], "teardown trial records absent")
        _need(all(isinstance(t, dict) and _integer(t.get("exit_code"))
                  and t.get("terminating_signal") in (None, "SIGABRT", "SIGTERM", "SIGINT", "")
                  for t in row["trials"]), "teardown wait status or signal malformed")
    _contradiction(all(t.get("exit_code") == 0 and t.get("terminating_signal") in (None, "")
                       for t in rows["client_first"]["trials"]),
                   "client-first orderly teardown aborted")
    _contradiction(all(t.get("terminating_signal") == "SIGABRT" for t in rows["server_first"]["trials"]),
                   "negative server-first teardown did not expose the abort regression")
    _contradiction(all(t.get("exit_code") == 0 and t.get("terminating_signal") in (None, "")
                       for t in rows["tcp_control"]["trials"]),
                   "TCP control teardown aborted")
    _rollback(doc)


def _m2(doc: dict[str, Any]) -> None:
    req = _request_binding(doc)
    _stack(doc, ("harness", "runtime", "runtime_commit", "kv_cache_format"))
    sessions = doc.get("sessions")
    _need(isinstance(sessions, list) and len(sessions) >= 3,
          "compaction, clean-reset and no-compaction sessions absent")
    sessions = cast(list[Any], sessions)
    by_mode = {x.get("mode"): x for x in sessions if isinstance(x, dict)}
    _need({"compaction", "clean_reset", "no_compaction_control"} <= by_mode.keys(),
          "compaction/clean-reset/no-compaction control triple incomplete")
    comp = by_mode["compaction"]
    _need(comp.get("request_id") == req["request_id"] and isinstance(comp.get("transitions"), list)
          and len(comp["transitions"]) >= 2, "repeated compaction state trace absent")
    transitions = cast(list[Any], comp["transitions"])
    for transition in transitions:
        _need(isinstance(transition, dict) and _sha_digest(transition.get("before_state_sha256"))
              and _sha_digest(transition.get("after_state_sha256")) and transition.get("event") == "compaction_complete",
              "compaction transition lacks before/after state evidence")
    for mode in ("compaction", "clean_reset", "no_compaction_control"):
        row = by_mode[mode]
        _need(row.get("request_id") == req["request_id"], f"{mode} request not bound to capture")
        if mode == "clean_reset":
            _need(_sha_digest(row.get("kv_state_sha256_before_reset"))
                  and _sha_digest(row.get("kv_state_sha256_after_reset")), "clean-reset KV-state hashes absent")
            _contradiction(row["kv_state_sha256_before_reset"] == row["kv_state_sha256_after_reset"],
                           "clean reset did not restore captured KV state")
        checks = row.get("semantic_tool_checks")
        _need(isinstance(checks, list) and checks and all(
            isinstance(x, dict) and _text(x.get("sse_raw"))
            and isinstance(x.get("oracle_tool_calls"), list) and _text(x.get("oracle_sha256"))
            and _text(x.get("oracle_ref"))
            for x in checks
        ), f"{mode} independent semantic/tool oracle absent")
        checks = cast(list[Any], checks)
        for check in checks:
            oracle = _oracle_payload(doc, check["oracle_ref"], check["oracle_sha256"], f"m2-{mode}")
            _need(_text(oracle.get("text")) and isinstance(oracle.get("tool_calls"), list),
                  f"m2-{mode} independent oracle schema incomplete")
            output = _sse_content(check["sse_raw"], f"m2-{mode}")
            calls = _sse_tool_calls(_sse_capture(check["sse_raw"], f"m2-{mode}"), f"m2-{mode}")
            _contradiction(output == oracle["text"] and calls == oracle["tool_calls"]
                           and calls == check["oracle_tool_calls"],
                           f"{mode} semantic/tool output differs from independent oracle")
    control = by_mode["no_compaction_control"]
    _need(control.get("request_id") == req["request_id"] and control.get("compaction_count") == 0,
          "no-compaction control did not remain un-compacted")
    _need(isinstance(doc.get("rawmetrics"), list) and len(doc["rawmetrics"]) >= 12,
          "prefill/decode/process/host raw metrics for all comparison modes absent")
    metrics = cast(list[Any], doc["rawmetrics"])
    start = datetime.fromisoformat(req["started_at"].replace("Z", "+00:00"))
    finish = datetime.fromisoformat(req["finished_at"].replace("Z", "+00:00"))
    for metric in metrics:
        _need(isinstance(metric, dict) and metric.get("name") in {
            "prefill_tokens_per_second", "decode_tokens_per_second", "process_rss_bytes", "host_uma_bytes"
        } and metric.get("mode") in {"compaction", "clean_reset", "no_compaction_control"}
              and metric.get("request_id") == req["request_id"] and _text(metric.get("timestamp"))
              and _finite_number(metric.get("value")) and metric["value"] >= 0,
              "malformed raw metric sample")
        moment = datetime.fromisoformat(metric["timestamp"].replace("Z", "+00:00"))
        _contradiction(start <= moment <= finish, "M2 measurement timestamp outside bounded request")
    _need({m["name"] for m in metrics} == {
        "prefill_tokens_per_second", "decode_tokens_per_second", "process_rss_bytes", "host_uma_bytes"
    } and {(m["name"], m["mode"]) for m in metrics} == {
        (name, mode) for name in ("prefill_tokens_per_second", "decode_tokens_per_second", "process_rss_bytes", "host_uma_bytes")
        for mode in ("compaction", "clean_reset", "no_compaction_control")
    },
          "comparison metric categories/modes incomplete")


def _minimax(doc: dict[str, Any]) -> None:
    req = _request_binding(doc)
    _stack(doc, ("driver", "vllm", "ray", "flashinfer", "quantization", "parser"))
    process_pid = doc.get("subject", {}).get("process_pid")
    _need(_integer(process_pid) and process_pid > 0, "same-process server PID observation absent")
    events = doc.get("sequence")
    expected_order = ["plain_text", "mock_tool", "plain_text_after_tool"]
    _need(isinstance(events, list) and [x.get("step") for x in events if isinstance(x, dict)] == expected_order,
          "same-process text/tool/text canary sequence incomplete")
    events = cast(list[Any], events)
    _need(all(isinstance(x, dict) and x.get("request_id") == req["request_id"]
              and _integer(x.get("http_status")) and _integer(x.get("process_pid"))
              and x.get("process_pid") == process_pid for x in events),
          "sequence requests not bound to one live process")
    for idx in (0, 2):
        cap = _sse_capture(events[idx].get("sse_raw"), expected_order[idx])
        _need(cap.get("status") == "observed", "plain-text SSE capture incomplete")
        _need(bool(_sse_content(events[idx]["sse_raw"], expected_order[idx])), "plain-text canary returned no content")
    tool = events[1]
    cap = _sse_capture(tool.get("sse_raw"), "mock-tool")
    calls = _sse_tool_calls(cap, "mock-tool")
    tool_oracle = _obj(doc.get("tool_oracle"), "byte-exact mock tool oracle reference absent")
    oracle = _oracle_payload(doc, tool_oracle.get("oracle_ref"), tool_oracle.get("oracle_sha256"), "minimax tool")
    expected = _obj(oracle.get("tool_call"), "independent byte-exact mock tool fixture absent")
    _need(_text(expected.get("name")) and isinstance(expected.get("arguments"), dict), "tool oracle schema incomplete")
    _contradiction(calls == [expected], "streamed tool name/arguments differ from independent fixture")
    _need(isinstance(tool.get("mock_result"), dict) and tool["mock_result"].get("request_id") == req["request_id"],
          "mock tool execution receipt absent")
    _contradiction(all(e.get("http_status") == 200 and e.get("finish_reason") == "stop" for e in events),
                   "same-process request returned HTTP error or did not finish")
    warmup = _rows(doc.get("warmup_ab"), 2, "CUDA graph/eager first-request warmup A/B")
    _need({r.get("mode") for r in warmup if isinstance(r, dict)} == {"graph", "eager"},
          "graph/eager warmup comparison absent")
    for run in warmup:
        _need(run.get("request_id") == req["request_id"] and isinstance(run.get("rank_events"), list)
              and len(run["rank_events"]) >= 2 and run.get("finish_reason") == "stop"
              and _text(run.get("output")), "warmup A/B lacks rank progress or functional response")
        _contradiction(all(r.get("completed_collectives", 0) > 0 for r in run["rank_events"]),
                       "warmup rank failed to make collective progress")
    expected_ple = _rows(doc.get("checkpoint_ple_manifest"), 1, "pinned checkpoint PLE tensor manifest")
    loader_ab = _rows(doc.get("loader_ab"), 2, "lazy/eager PLE loader comparison")
    _need({r.get("mode") for r in loader_ab if isinstance(r, dict)} == {"lazy", "eager"},
          "lazy/eager loader comparison absent")
    expected_names = {x.get("name") for x in expected_ple if isinstance(x, dict)}
    _need(expected_names and all(_text(name) for name in expected_names), "checkpoint PLE manifest names invalid")
    for run in loader_ab:
        actual = _rows(run.get("loaded_ple_tensors"), len(expected_ple), "effective loaded PLE tensors")
        _contradiction({x.get("name") for x in actual} == expected_names,
                       "effective loader tensor set differs from pinned checkpoint PLE manifest")
        _need(all(_text(x.get("dtype")) and _text(x.get("sha256")) for x in actual),
              "loaded PLE tensor dtype/hash evidence absent")
    _rollback(doc)


def _mtp(doc: dict[str, Any]) -> None:
    req = _request_binding(doc)
    _stack(doc, ("vllm", "mtp_tokens", "parser", "tokenizer"))
    pairs = doc.get("token_pairs")
    _need(isinstance(pairs, list) and pairs, "raw target/draft token pairs absent")
    pairs = cast(list[Any], pairs)
    for row in pairs:
        _need(isinstance(row, dict) and _integer(row.get("position")) and row["position"] >= 0
              and _text(row.get("draft_token")) and _text(row.get("target_token")),
              "token pair malformed")
    expected = [row["draft_token"] == row["target_token"] for row in pairs]
    observed = doc.get("reported_acceptance_by_position")
    _need(isinstance(observed, list) and len(observed) == len(expected)
          and all(isinstance(x, bool) for x in observed), "reported per-position acceptance incomplete")
    _contradiction(observed == expected, "reported MTP acceptance differs from captured tokens")
    semantic = _obj(doc.get("semantic_oracle"), "semantic control absent")
    _need(semantic.get("request_id") == req["request_id"] and _text(semantic.get("observed_output"))
          and _text(semantic.get("expected_output")), "semantic output comparison absent")
    _contradiction(semantic["observed_output"] == semantic["expected_output"], "MTP semantic output differs from target control")
    negative = _obj(doc.get("negative_control"), "wrong-draft negative control absent")
    _need(_text(negative.get("draft_token")) and _text(negative.get("target_token"))
          and _text(negative.get("emitted_token")), "negative token pair/output absent")
    _contradiction(negative["draft_token"] != negative["target_token"]
                   and negative["emitted_token"] == negative["target_token"],
                   "mismatched draft token appeared in emitted sequence")
    _rollback(doc)


def _muse(doc: dict[str, Any]) -> None:
    req = _request_binding(doc)
    _stack(doc, ("image", "model", "backend", "parser"))
    resolution = _obj(doc.get("draft_class_resolution"), "effective DFlash draft class lookup absent")
    _need(_text(resolution.get("checkpoint_digest")) and _text(resolution.get("configured_class"))
          and _text(resolution.get("resolved_class")), "draft class identity incomplete")
    _contradiction(resolution["checkpoint_digest"] == doc["subject"]["checkpoint_digest"],
                   "draft class lookup is detached from pinned checkpoint")
    _contradiction(resolution["resolved_class"] == resolution["configured_class"],
                   "effective DFlash class does not resolve to configured draft class")
    runs = doc.get("sequence_runs")
    _need(isinstance(runs, list) and {x.get("max_num_seqs") for x in runs if isinstance(x, dict)} == {32, 33},
          "required max-seqs 32/33 boundary pair absent")
    runs = cast(list[Any], runs)
    by_size = {x["max_num_seqs"]: x for x in runs}
    for n in (32, 33):
        row = by_size[n]
        _need(row.get("request_id") == req["request_id"] and isinstance(row.get("raw_metrics"), list)
              and row["raw_metrics"] and isinstance(row.get("canaries"), list),
              f"max_num_seqs={n} raw metrics or semantic canaries absent")
        _need(all(isinstance(m, dict) and _text(m.get("name")) and _text(m.get("unit"))
                  and _finite_number(m.get("value")) for m in row["raw_metrics"]),
              f"max_num_seqs={n} resource measurements malformed")
        _need(bool(row["canaries"]) and all(isinstance(c, dict) and "expected" in c and "observed" in c
                                             for c in row["canaries"]),
              f"max_num_seqs={n} semantic canaries incomplete")
        _contradiction(all(c["expected"] == c["observed"] for c in row["canaries"]),
                       f"sequence-{n} semantic canary failed")
    _need(any(c.get("kind") == "untrusted_tool" for c in by_size[32]["canaries"] if isinstance(c, dict)),
          "untrusted-tool semantic canary absent")
    _rollback(doc)


def _nccl_tp(doc: dict[str, Any]) -> None:
    req = _request_binding(doc)
    _stack(doc, ("os", "kernel", "driver", "torch", "cuda", "nccl", "launcher_digest"))
    nodes = doc.get("nodes")
    _need(isinstance(nodes, list) and len(nodes) == 2, "two-node launcher capture absent")
    nodes = cast(list[Any], nodes)
    _need(all(isinstance(n, dict) and _text(n.get("node_id")) and _text(n.get("launcher_argv_sha256"))
              and _text(n.get("effective_nccl_env_sha256")) and _text(n.get("interface"))
              and _text(n.get("subnet")) for n in nodes), "per-node launcher/interface/env evidence incomplete")
    _contradiction(len({n["node_id"] for n in nodes}) == 2, "node launcher identities duplicate")
    micro = _obj(doc.get("nccl_microtest"), "NCCL all-reduce microtest absent")
    _need(isinstance(micro.get("rank_results"), list) and len(micro["rank_results"]) >= 2
          and _text(micro.get("command_sha256")), "raw collective command/rank output absent")
    rank_results = cast(list[Any], micro["rank_results"])
    _contradiction(all(_integer(r.get("exit_code")) and r.get("exit_code") == 0
                       and _finite_number(r.get("bus_bandwidth_gbps")) and r["bus_bandwidth_gbps"] > 0
                       for r in rank_results),
                   "NCCL microtest failed or lacked measured bandwidth")
    ab = doc.get("recipe_manual_ab")
    _need(isinstance(ab, list) and {x.get("mode") for x in ab if isinstance(x, dict)} == {"recipe_launcher", "manual"},
          "same-stack recipe/manual A/B absent")
    ab = cast(list[Any], ab)
    for run in ab:
        _need(run.get("request_id") == req["request_id"] and isinstance(run.get("rank_logs"), list)
              and len(run["rank_logs"]) >= 2 and _integer(run.get("output_tokens"))
              and _text(run.get("output")),
              "launcher A/B lacks request/rank/output data")
    _contradiction(all(x["output_tokens"] > 0 and x.get("finish_reason") == "stop" for x in ab),
                   "recipe/manual launcher A/B failed functional generation")
    _contradiction(next(x for x in ab if x["mode"] == "recipe_launcher")["output"]
                   == next(x for x in ab if x["mode"] == "manual")["output"],
                   "recipe/manual launcher output differs on functional canary")
    _rollback(doc)


def _nemotron(doc: dict[str, Any]) -> None:
    req = _request_binding(doc)
    _stack(doc, ("sglang", "sgl_kernel", "cuda", "driver"))
    _need(doc["subject"].get("sm_arch") == "sm_121", "subject is not pinned to SM121")
    matrix = doc.get("architecture_kernel_matrix")
    _need(isinstance(matrix, list) and matrix, "required operation/kernel matrix absent")
    matrix = cast(list[Any], matrix)
    required = set(doc.get("required_operations", []))
    _need(required and all(_text(op) for op in required), "model/backend required operation list absent")
    required = cast(set[str], required)
    rows = [r for r in matrix if isinstance(r, dict) and r.get("sm_arch") == "sm_121"]
    _need({r.get("operation") for r in rows} == required, "SM121 matrix does not cover every required operation")
    _contradiction(all(_text(r.get("kernel_name")) and r.get("load_exit_code") == 0
                       and r.get("first_inference_exit_code") == 0 and _text(r.get("raw_output")) for r in rows),
                   "required SM121 operation has no executable kernel at load/first inference")
    output = _obj(doc.get("reference_output"), "reference correctness comparison absent")
    _need(output.get("request_id") == req["request_id"] and _text(output.get("observed"))
          and _text(output.get("expected")), "reference output is not tied to bounded request")
    _contradiction(output["observed"] == output["expected"], "Nemotron output differs from reference")
    negative = _obj(doc.get("architecture_negative"), "unsupported architecture negative control absent")
    _need(_text(negative.get("sm_arch")) and isinstance(negative.get("required_op"), str)
          and _text(negative.get("argv_sha256")) and _integer(negative.get("exit_code"))
          and _text(negative.get("stderr_raw")), "wrong-architecture command/exit capture absent")
    _contradiction(negative["sm_arch"] != "sm_121" and negative["exit_code"] != 0,
                   "unsupported architecture control was not rejected")


def _openclaw(doc: dict[str, Any]) -> None:
    _stack(doc, ("openclaw", "vllm", "driver"))
    bundle = doc.get("openclaw_bundle")
    _need(isinstance(bundle, dict), "raw OpenClaw/vLLM contract bundle absent")
    bundle = cast(dict[str, Any], bundle)
    result = analyze_openclaw_contract(bundle, "runtime-batch02-capture.json")
    _need(result.get("could_not_run_count") == 0, "OpenClaw contract analyzer could not evaluate raw bundle")
    checks = result.get("checks")
    _need(isinstance(checks, dict), "OpenClaw contract analyzer returned no derived checks")
    checks = cast(dict[str, Any], checks)
    for name in ("models_http", "models_schema", "client_model", "checkpoint_context", "configured_generation_budget",
                 "request_generation_budget"):
        _need(isinstance(checks.get(name), dict), f"OpenClaw check {name} absent")
    _contradiction(all(checks[name].get("status") == "observed" for name in
                       ("models_http", "models_schema", "client_model", "checkpoint_context",
                        "configured_generation_budget", "request_generation_budget")),
                   "OpenClaw model/context contract mismatch")
    negative = doc.get("request_negatives")
    _need(isinstance(negative, list) and {x.get("case") for x in negative if isinstance(x, dict)}
          == {"wrong_model_404", "context_overflow", "negative_max_tokens"},
          "404/context/token-budget negative captures incomplete")
    negative = cast(list[Any], negative)
    models_response = _obj(bundle.get("models_response"), "captured /v1/models response absent")
    models_body = _obj(models_response.get("body"), "captured /v1/models body absent")
    model_entries_value = models_body.get("data")
    _need(isinstance(model_entries_value, list), "captured /v1/models data array absent")
    model_entries = cast(list[Any], model_entries_value)
    model_ids = {x.get("id") for x in model_entries if isinstance(x, dict)}
    checkpoint_context = _obj(bundle.get("checkpoint_context"), "checkpoint context record absent")
    checkpoint_limit = checkpoint_context.get("context_limit_tokens")
    by_case = {x["case"]: x for x in negative}
    wrong = by_case["wrong_model_404"]
    _need(_text(wrong.get("request_model")) and _integer(wrong.get("http_status")),
          "wrong-model raw HTTP control is incomplete")
    _contradiction(wrong["request_model"] not in model_ids and wrong["http_status"] == 404,
                   "wrong-model request did not produce expected 404")
    overflow = by_case["context_overflow"]
    _need(_integer(checkpoint_limit) and _integer(overflow.get("input_tokens"))
          and _integer(overflow.get("http_status")), "context-overflow control lacks checkpoint/token/HTTP data")
    _contradiction(overflow["input_tokens"] > checkpoint_limit and overflow["http_status"] == 400,
                   "over-limit request was not rejected")
    negative_tokens = by_case["negative_max_tokens"]
    _need(_integer(negative_tokens.get("max_tokens")) and _integer(negative_tokens.get("http_status")),
          "negative max_tokens control lacks request/HTTP data")
    _contradiction(negative_tokens["max_tokens"] <= 0 and negative_tokens["http_status"] == 400,
                   "non-positive output budget was not rejected")
    positive = _obj(doc.get("positive_request"), "bounded positive chat/tool request capture absent")
    _need(isinstance(positive.get("raw_request"), dict) and isinstance(positive.get("raw_response"), dict),
          "positive request/response body capture absent")
    _contradiction(positive["raw_response"].get("status_code") == 200,
                   "positive OpenClaw chat/tool request returned non-200")
    capture = _sse_capture(positive.get("sse_raw"), "openclaw-positive-tool")
    actual_calls = _sse_tool_calls(capture, "openclaw-positive-tool")
    expected_calls = positive.get("expected_tool_calls")
    _need(isinstance(expected_calls, list) and expected_calls, "positive OpenClaw tool oracle absent")
    _contradiction(actual_calls == expected_calls, "positive OpenClaw tool arguments differ from fixture")


def _cold_compile(doc: dict[str, Any]) -> None:
    req = _request_binding(doc)
    _stack(doc, ("vllm", "torch", "cuda", "driver", "inductor"))
    ranks = doc.get("rank_cold_compile")
    _need(isinstance(ranks, list) and len(ranks) >= 2, "per-rank cold compile observations absent")
    ranks = cast(list[Any], ranks)
    for rank in ranks:
        _need(isinstance(rank, dict) and _text(rank.get("node_id")) and _integer(rank.get("rank"))
              and _text(rank.get("compile_log_sha256")) and isinstance(rank.get("memory_series"), list)
              and len(rank["memory_series"]) >= 2, "rank cold compile/headroom capture incomplete")
        for sample in rank["memory_series"]:
            _need(isinstance(sample, dict) and _text(sample.get("timestamp"))
                  and _integer(sample.get("available_bytes")) and _integer(sample.get("used_bytes"))
                  and sample["available_bytes"] >= 0 and sample["used_bytes"] >= 0,
                  "memory headroom sample malformed")
    _contradiction(all(r.get("compile_exit_code") == 0 and r.get("request_id") == req["request_id"] for r in ranks),
                   "cold compile failed on a rank")
    eager = _obj(doc.get("eager_control"), "same-stack eager control absent")
    _need(eager.get("request_id") == req["request_id"] and eager.get("compilation_mode") == 0
          and _integer(eager.get("output_tokens")), "eager comparison not bound to same request")
    _contradiction(eager["output_tokens"] > 0, "eager control failed functional request")
    remote = doc.get("remote_access_series")
    _need(isinstance(remote, list) and remote and all(isinstance(x, dict) and _text(x.get("timestamp"))
          and _integer(x.get("ssh_exit_code")) and _integer(x.get("icmp_exit_code"))
          and _text(x.get("ssh_command_sha256")) and _text(x.get("icmp_command_sha256")) for x in remote),
          "remote access observations missing around cold compile")
    remote = cast(list[Any], remote)
    _contradiction(all(x["ssh_exit_code"] == 0 and x["icmp_exit_code"] == 0 for x in remote),
                   "host access was lost during compile capture")
    _rollback(doc)


def _finite_number(value: Any) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
    )


def _integer(value: Any) -> bool:
    return type(value) is int


def _sha_digest(value: Any) -> bool:
    return isinstance(value, str) and re.fullmatch(r"(?:[0-9a-f]{64}|sha256:[0-9a-f]{64})", value) is not None


def _rows(value: Any, minimum: int, label: str) -> list[Any]:
    _need(isinstance(value, list) and len(value) >= minimum, f"{label} rows absent")
    return cast(list[Any], value)


def _oracle_payload(doc: dict[str, Any], oracle_ref: Any, digest: Any, label: str) -> dict[str, Any]:
    _need(_text(oracle_ref) and _text(digest), f"{label} independent oracle reference/hash absent")
    relative = Path(oracle_ref)
    _need(
        not relative.is_absolute() and ".." not in relative.parts,
        f"{label} oracle reference escapes card evidence",
    )
    path = EVIDENCE / doc["card_id"] / "oracles" / relative
    try:
        raw = read_regular_bytes(path, 1024 * 1024)
    except OSError as exc:
        raise _Unknown(f"{label} oracle fixture unavailable: {exc}") from exc
    _need(len(raw) <= 1024 * 1024, f"{label} oracle fixture exceeds 1 MiB")
    _contradiction(hashlib.sha256(raw).hexdigest() == digest, f"{label} oracle fixture hash mismatch")
    try:
        value = strict_json_loads(raw.decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError, RecursionError) as exc:
        raise _Unknown(f"{label} oracle fixture malformed: {exc}") from exc
    return _obj(value, f"{label} oracle must be a JSON object")


def _stack(doc: dict[str, Any], keys: tuple[str, ...]) -> None:
    versions = _obj(doc["subject"].get("software_versions"), "effective stack version map absent")
    _need(all(_text(versions.get(key)) for key in keys),
          f"pinned stack tuple incomplete; required: {', '.join(keys)}")
    for key in keys:
        if key.endswith(("_commit", "_digest")):
            _need(re.fullmatch(r"(?:[0-9a-f]{40}|sha256:[0-9a-f]{64})", versions[key]) is not None,
                  f"{key} must be a pinned git or SHA-256 digest")


_VALIDATORS: dict[str, Callable[[dict[str, Any]], None]] = {
    "DELTA-FORUM-GPTOSS-MULTINODE-RAY-CHANNEL-TIMEOUT-01": _ray,
    "DELTA-FORUM-LLAMACPP-RPC-UMA-AND-ORDERLY-TEARDOWN-01": _llamacpp,
    "DELTA-FORUM-M2-COMPACTION-STATE-VALIDATION-01": _m2,
    "DELTA-FORUM-MINIMAX-TOOLCALL-FUNCTIONAL-CANARY-01": _minimax,
    "DELTA-FORUM-MTP-ACCEPTANCE-AND-SEMANTIC-CONTROL-01": _mtp,
    "DELTA-FORUM-MUSE-GLIMMER-DFLASH-MAX-SEQS-GATE-01": _muse,
    "DELTA-FORUM-NCCL-TP-ORCHESTRATION-CORRECTION-01": _nccl_tp,
    "DELTA-FORUM-NEMOTRON-SM121-PREBUILT-KERNEL-01": _nemotron,
    "DELTA-FORUM-OPENCLAW-VLLM-REQUEST-CONTRACT-01": _openclaw,
    "DELTA-FORUM-QWEN-COLD-COMPILE-OOM-01": _cold_compile,
}


def assess(card_id: str, raw_document: Any) -> dict[str, Any]:
    validator = _VALIDATORS.get(card_id)
    if validator is None:
        return {"status": "unknown", "could_not_run": 1, "reason": "no batch-02 validator for card"}
    try:
        doc = _capture(raw_document, card_id)
        validator(doc)
    except _Fail as exc:
        return {"status": "fail", "could_not_run": 0, "reason": str(exc)}
    except _Unknown as exc:
        return {"status": "unknown", "could_not_run": 1, "reason": str(exc)}
    except (AttributeError, IndexError, KeyError, TypeError, ValueError, StopIteration) as exc:
        return {"status": "unknown", "could_not_run": 1, "reason": f"malformed raw record: {exc}"}
    return {"status": "pass", "could_not_run": 0, "reason": "raw batch-02 measurements satisfy domain predicate"}


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
        return {"status": "unknown", "could_not_run": 1, "reason": f"raw capture unavailable: {exc}", "files": [str(p)]}
    result = assess(card_id, raw)
    result["files"] = [str(p)]
    return result
