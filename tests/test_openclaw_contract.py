from __future__ import annotations

import json
import runpy
import sys
from pathlib import Path
from typing import Any

from tools import openclaw_contract as contract


def _bundle() -> dict[str, Any]:
    return {
        "models_response": {"status_code": 200, "body": {"object": "list", "data": [{"id": "gpt-oss-120b"}]}},
        "openclaw_config": {
            "agents": {"defaults": {"model": {"primary": "vllm/gpt-oss-120b"}}},
            "models": {"providers": {"vllm": {"models": [{
                "id": "gpt-oss-120b", "contextWindow": 131072,
                "contextTokens": 120000, "maxTokens": 8192,
            }]}}},
        },
        "checkpoint_context": {
            "checkpoint_id": "org/gpt-oss-120b@sha256:abc",
            "served_model_id": "gpt-oss-120b",
            "context_limit_tokens": 131072,
        },
        "request_observation": {
            "model_id": "gpt-oss-120b", "checkpoint_id": "org/gpt-oss-120b@sha256:abc",
            "prompt_tokens": 120000, "max_tokens": 8192,
        },
    }


def test_valid_captured_contract_computes_bounded_generation_budget_without_prompt() -> None:
    result = contract.analyze(_bundle(), "capture.json")
    assert result["status"] == "observed"
    assert result["capture_path_provenance"] == "caller_supplied_unverified"
    assert result["checks"]["client_model"]["configured_model_id"] == "gpt-oss-120b"
    assert result["checks"]["configured_generation_budget"]["output_budget_tokens"] == 8192
    assert result["checks"]["request_generation_budget"]["output_budget_tokens"] == 11072
    assert result["could_not_run_count"] == 0
    assert "prompt" not in json.dumps(result).lower()


def test_http_404_and_model_id_mismatch_block() -> None:
    bundle = _bundle()
    bundle["models_response"]["status_code"] = 404
    bundle["models_response"]["body"] = {"data": [{"id": "other-model"}]}
    result = contract.analyze(bundle, "capture.json")
    assert result["status"] == "block"
    assert result["checks"]["models_http"]["status"] == "mismatch"
    assert result["checks"]["models_schema"]["status"] == "unknown"
    assert result["checks"]["client_model"]["status"] == "unknown"

    bundle = _bundle()
    bundle["openclaw_config"]["agents"]["defaults"]["model"]["primary"] = "vllm/other-model"
    bundle["openclaw_config"]["models"]["providers"]["vllm"]["models"][0]["id"] = "other-model"
    result = contract.analyze(bundle, "capture.json")
    assert result["status"] == "block"
    assert result["checks"]["client_model"]["status"] == "mismatch"


def test_http_status_must_be_integer_and_blank_model_ids_are_not_valid() -> None:
    bundle = _bundle()
    bundle["models_response"]["status_code"] = 200.0
    result = contract.analyze(bundle, "capture.json")
    assert result["checks"]["models_http"]["status"] == "unknown"
    bundle = _bundle()
    bundle["models_response"]["body"]["data"] = [{"id": "  "}]
    result = contract.analyze(bundle, "capture.json")
    assert result["checks"]["models_schema"]["status"] == "unknown"


def test_negative_max_tokens_is_reported_as_invalid_budget() -> None:
    bundle = _bundle()
    bundle["openclaw_config"]["models"]["providers"]["vllm"]["models"][0]["maxTokens"] = -1
    result = contract.analyze(bundle, "capture.json")
    assert result["status"] == "block"
    assert result["checks"]["configured_generation_budget"]["output_budget_tokens"] == -1


def test_context_above_explicit_checkpoint_limit_blocks() -> None:
    bundle = _bundle()
    bundle["openclaw_config"]["models"]["providers"]["vllm"]["models"][0]["contextWindow"] = 200000
    result = contract.analyze(bundle, "capture.json")
    assert result["status"] == "block"
    assert "exceeds" in result["issues"][-1]


def test_context_cap_leaving_no_generation_budget_blocks() -> None:
    bundle = _bundle()
    bundle["openclaw_config"]["models"]["providers"]["vllm"]["models"][0]["contextTokens"] = 131072
    result = contract.analyze(bundle, "capture.json")
    assert result["status"] == "block"
    assert result["checks"]["configured_generation_budget"]["output_budget_tokens"] == 0


def test_context_cap_past_model_window_blocks_even_when_checkpoint_is_larger() -> None:
    bundle = _bundle()
    row = bundle["openclaw_config"]["models"]["providers"]["vllm"]["models"][0]
    row["contextWindow"] = 100
    row["contextTokens"] = 1000
    bundle["checkpoint_context"]["context_limit_tokens"] = 2000
    result = contract.analyze(bundle, "capture.json")
    assert result["status"] == "block"
    assert result["checks"]["configured_generation_budget"]["effective_context_limit_tokens"] == 100


def test_missing_token_usage_keeps_request_budget_unknown() -> None:
    bundle = _bundle()
    del bundle["request_observation"]
    result = contract.analyze(bundle, "capture.json")
    assert result["checks"]["configured_generation_budget"]["status"] == "observed"
    assert result["checks"]["request_generation_budget"]["status"] == "unknown"
    assert result["could_not_run_count"] == 1


def test_request_with_input_over_effective_window_blocks() -> None:
    bundle = _bundle()
    bundle["request_observation"]["prompt_tokens"] = 131073
    result = contract.analyze(bundle, "capture.json")
    assert result["checks"]["request_generation_budget"]["status"] == "mismatch"


def test_request_keeps_oversized_max_tokens_and_reports_headroom_suggestion() -> None:
    bundle = _bundle()
    bundle["request_observation"]["prompt_tokens"] = 131072 - 100
    bundle["request_observation"]["max_tokens"] = 8192
    result = contract.analyze(bundle, "capture.json")
    request_budget = result["checks"]["request_generation_budget"]
    assert request_budget["status"] == "mismatch"
    assert request_budget["requested_max_tokens"] == 8192
    assert request_budget["output_budget_tokens"] == 100


def test_request_budget_enforces_configured_openclaw_output_cap() -> None:
    bundle = _bundle()
    bundle["request_observation"]["prompt_tokens"] = 100000
    bundle["request_observation"]["max_tokens"] = 9000
    result = contract.analyze(bundle, "capture.json")
    request_budget = result["checks"]["request_generation_budget"]
    assert request_budget["output_budget_tokens"] == 31072
    assert request_budget["configured_output_cap_tokens"] == 8192
    assert request_budget["status"] == "mismatch"
    assert "request max_tokens exceeds the configured OpenClaw output cap" in result["issues"]


def test_negative_observed_request_token_count_blocks() -> None:
    bundle = _bundle()
    bundle["request_observation"]["prompt_tokens"] = -1
    result = contract.analyze(bundle, "capture.json")
    assert result["checks"]["request_generation_budget"]["status"] == "mismatch"


def test_missing_checkpoint_binding_preserves_unknown_and_cnr() -> None:
    bundle = _bundle()
    bundle["checkpoint_context"] = {"checkpoint_id": "org/model"}
    result = contract.analyze(bundle, "capture.json")
    assert result["status"] == "unknown"
    assert result["checks"]["checkpoint_context"]["status"] == "unknown"
    assert result["could_not_run_count"] > 0


def test_unreadable_shapes_duplicates_and_incomplete_openclaw_model_are_unknown_or_block() -> None:
    result = contract.analyze({"models_response": {"status_code": 200, "body": {"data": [{"name": "x"}]}},
                               "openclaw_config": {}, "checkpoint_context": {}}, "capture.json")
    assert result["status"] == "unknown"
    assert result["checks"]["models_schema"]["status"] == "unknown"
    assert result["checks"]["client_model"]["status"] == "unknown"

    bundle = _bundle()
    bundle["models_response"]["body"]["data"].append({"id": "gpt-oss-120b"})
    result = contract.analyze(bundle, "capture.json")
    assert result["checks"]["models_schema"]["status"] == "mismatch"


def test_non_object_bundle_and_invalid_context_fields_are_not_trusted() -> None:
    result = contract.analyze([], "capture.json")
    assert result["status"] == "unknown"
    bundle = _bundle()
    checkpoint = bundle["checkpoint_context"]
    checkpoint["context_limit_tokens"] = True
    result = contract.analyze(bundle, "capture.json")
    assert result["checks"]["checkpoint_context"]["status"] == "unknown"
    bundle = _bundle()
    bundle["checkpoint_context"]["context_limit_tokens"] = 0
    result = contract.analyze(bundle, "capture.json")
    assert result["checks"]["checkpoint_context"]["status"] == "unknown"


def test_cli_handles_valid_and_unreadable_capture(tmp_path: Path, capsys, monkeypatch) -> None:
    capture = tmp_path / "capture.json"
    capture.write_text(json.dumps(_bundle()), encoding="utf-8")
    assert contract.main([str(capture)]) == 0
    assert '"status": "observed"' in capsys.readouterr().out
    capture.write_text("{", encoding="utf-8")
    assert contract.main([str(capture)]) == 2
    assert '"status": "unknown"' in capsys.readouterr().out
    assert contract.main([str(tmp_path / "missing.json")]) == 2
    assert '"status": "unknown"' in capsys.readouterr().out
    capture.write_text('{"models_response": NaN}', encoding="utf-8")
    assert contract.main([str(capture)]) == 2
    assert '"status": "unknown"' in capsys.readouterr().out
    monkeypatch.setattr(sys, "argv", [str(contract.__file__), str(capture)])
    try:
        runpy.run_path(str(contract.__file__), run_name="__main__")
    except SystemExit as exc:
        assert exc.code == 2
    else:
        raise AssertionError("module entry point did not exit")
