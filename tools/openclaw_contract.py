"""Offline check of captured vLLM model discovery and OpenClaw model budgets."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, cast


def _integer(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _reject_json_constant(value: str) -> None:
    raise ValueError(f"invalid JSON constant: {value}")


def _models(response: Any) -> tuple[dict[str, Any], dict[str, Any], list[str], list[str]]:
    issues: list[str] = []
    if not isinstance(response, dict):
        response = {}
    code = response.get("status_code")
    http = {"status": "observed", "observed_status_code": 200} if _integer(code) and code == 200 else {
        "status": "mismatch" if _integer(code) else "unknown",
        "observed_status_code": code if _integer(code) else None,
    }
    if http["status"] == "mismatch":
        issues.append("captured GET /v1/models did not return HTTP 200")
    elif http["status"] == "unknown":
        issues.append("captured GET /v1/models status code is unavailable or malformed")
    body = response.get("body")
    entries = body.get("data") if isinstance(body, dict) else None
    ids: list[str] = []
    if isinstance(entries, list):
        for entry in entries:
            if isinstance(entry, dict) and isinstance(entry.get("id"), str) and entry["id"].strip():
                ids.append(entry["id"])
    if http["status"] != "observed":
        schema = {"status": "unknown", "model_count": 0}
    elif not isinstance(entries, list) or len(ids) != len(entries) or not ids:
        schema = {"status": "unknown", "model_count": len(ids)}
        issues.append("captured /v1/models body lacks a non-empty complete data[].id list")
    elif len(set(ids)) != len(ids):
        schema = {"status": "mismatch", "model_count": len(ids)}
        issues.append("captured /v1/models contains duplicate model IDs")
    else:
        schema = {"status": "observed", "model_count": len(ids)}
    return http, schema, ids, issues


def _openclaw_model(config: Any, model_ids: list[str], model_list_observed: bool) -> tuple[dict[str, Any], str, dict[str, Any], list[str]]:
    issues: list[str] = []
    if not isinstance(config, dict):
        config = {}
    agents = config.get("agents")
    defaults = agents.get("defaults") if isinstance(agents, dict) else None
    active = defaults.get("model") if isinstance(defaults, dict) else None
    primary = active.get("primary") if isinstance(active, dict) else None
    provider_name, separator, model_id = primary.partition("/") if isinstance(primary, str) else ("", "", "")
    model_root = config.get("models")
    providers = model_root.get("providers") if isinstance(model_root, dict) else None
    provider = providers.get(provider_name) if isinstance(providers, dict) and separator else None
    candidates = provider.get("models") if isinstance(provider, dict) else None
    matches = [item for item in candidates
               if isinstance(item, dict) and item.get("id") == model_id] if isinstance(candidates, list) else []
    if len(matches) != 1:
        check = {"status": "unknown", "configured_model_id": model_id or None}
        issues.append("OpenClaw primary model does not resolve to exactly one configured provider model")
        return check, model_id, {}, issues
    if not model_list_observed:
        check = {"status": "unknown", "configured_model_id": model_id}
        issues.append("configured model ID could not be compared because /v1/models was not observed")
    elif model_id not in model_ids:
        check = {"status": "mismatch", "configured_model_id": model_id}
        issues.append("configured OpenClaw model ID is absent from captured /v1/models")
    else:
        check = {"status": "observed", "configured_model_id": model_id}
    return check, model_id, matches[0], issues


def _checkpoint(source: Any, model_id: str) -> tuple[dict[str, Any], int | None, bool, list[str]]:
    if not isinstance(source, dict):
        source = {}
    limit = source.get("context_limit_tokens")
    binding = (isinstance(source.get("checkpoint_id"), str) and bool(source["checkpoint_id"].strip())
               and source.get("served_model_id") == model_id)
    if not binding or not _integer(limit):
        return {"status": "unknown"}, None, binding, [
            "positive context limit explicitly bound to this model/checkpoint is unavailable"
        ]
    resolved_limit = cast(int, limit)
    if resolved_limit <= 0:
        return {"status": "unknown"}, None, binding, [
            "positive context limit explicitly bound to this model/checkpoint is unavailable"
        ]
    return {"status": "observed", "context_limit_tokens": resolved_limit}, resolved_limit, binding, []


def _configured_budget(model: dict[str, Any], limit: int | None,
                      binding: bool) -> tuple[dict[str, Any], list[str]]:
    issues: list[str] = []
    context_window = model.get("contextWindow")
    input_cap = model.get("contextTokens")
    output_cap = model.get("maxTokens")
    if not all(_integer(value) for value in (context_window, input_cap, output_cap)):
        config_budget = {"status": "unknown", "input_cap_tokens": None, "output_budget_tokens": None}
        issues.append("configured contextWindow, contextTokens, or maxTokens is missing or non-integer")
        return config_budget, issues
    context_window = cast(int, context_window)
    input_cap = cast(int, input_cap)
    output_cap = cast(int, output_cap)
    if limit is not None:
        limit = cast(int, limit)
    if min(context_window, input_cap, output_cap) <= 0:
        config_budget = {"status": "mismatch", "input_cap_tokens": input_cap,
                         "output_budget_tokens": output_cap}
        issues.append("configured context or generation token budget is not positive")
    elif not binding or limit is None:
        config_budget = {"status": "unknown", "input_cap_tokens": input_cap, "output_budget_tokens": None}
        issues.append("generation budget cannot be bounded without checkpoint context provenance")
    else:
        effective_limit = min(context_window, limit)
        remaining = effective_limit - input_cap
        budget = min(output_cap, remaining)
        if context_window > limit:
            config_budget = {"status": "mismatch", "input_cap_tokens": input_cap,
                             "output_budget_tokens": budget, "effective_context_limit_tokens": effective_limit}
            issues.append("configured contextWindow exceeds the explicitly bound checkpoint limit")
        elif input_cap > effective_limit or budget <= 0:
            config_budget = {"status": "mismatch", "input_cap_tokens": input_cap,
                             "output_budget_tokens": budget, "effective_context_limit_tokens": effective_limit}
            issues.append("configured input cap leaves no positive generation budget within the effective context limit")
        else:
            config_budget = {"status": "observed", "input_cap_tokens": input_cap,
                             "output_budget_tokens": budget, "effective_context_limit_tokens": effective_limit}

    return config_budget, issues


def _request_budget(model: dict[str, Any], limit: int | None, binding: bool,
                    request: Any, checkpoint: Any) -> tuple[dict[str, Any], list[str]]:
    issues: list[str] = []
    if not isinstance(request, dict):
        request = {}
    prompt_tokens = request.get("prompt_tokens")
    requested_max = request.get("max_tokens")
    request_bound = (isinstance(checkpoint, dict)
                     and request.get("model_id") == checkpoint.get("served_model_id")
                     and request.get("checkpoint_id") == checkpoint.get("checkpoint_id"))
    window = model.get("contextWindow")
    configured_max = model.get("maxTokens")
    if (not request_bound or not _integer(prompt_tokens) or not _integer(requested_max)
            or not _integer(window) or not _integer(configured_max)):
        request_budget = {"status": "unknown", "output_budget_tokens": None}
        issues.append("request-level budget unknown: bound token counts, max_tokens, or configured output cap were not supplied")
    elif not binding or limit is None:
        request_budget = {"status": "mismatch", "output_budget_tokens": None}
        issues.append("request token counts or explicit checkpoint binding are invalid")
    else:
        prompt_tokens = cast(int, prompt_tokens)
        requested_max = cast(int, requested_max)
        window = cast(int, window)
        configured_max = cast(int, configured_max)
        limit = cast(int, limit)
        if prompt_tokens < 0 or requested_max <= 0 or window <= 0 or limit <= 0 or configured_max <= 0:
            request_budget = {"status": "mismatch", "output_budget_tokens": None}
            issues.append("request token counts or explicit checkpoint binding are invalid")
        else:
            effective_limit = min(window, limit)
            remaining = effective_limit - prompt_tokens
            state = ("observed" if prompt_tokens <= effective_limit
                     and requested_max <= remaining and requested_max <= configured_max else "mismatch")
            request_budget = {"status": state, "input_tokens": prompt_tokens,
                              "requested_max_tokens": requested_max,
                              "output_budget_tokens": max(0, remaining),
                              "configured_output_cap_tokens": configured_max}
            if requested_max > remaining:
                issues.append("request max_tokens exceeds available context headroom")
            if requested_max > configured_max:
                issues.append("request max_tokens exceeds the configured OpenClaw output cap")
    request_budget["evidence_provenance"] = "caller_supplied_unverified"
    return request_budget, issues


def analyze(bundle: Any, capture_path: str) -> dict[str, Any]:
    issues: list[str] = []
    if not isinstance(bundle, dict):
        bundle = {}
        issues.append("capture bundle must be an object")
    http, schema, ids, found = _models(bundle.get("models_response"))
    issues.extend(found)
    client_model, model_id, model, found = _openclaw_model(
        bundle.get("openclaw_config"), ids, schema["status"] == "observed"
    )
    issues.extend(found)
    checkpoint, limit, binding, found = _checkpoint(bundle.get("checkpoint_context"), model_id)
    issues.extend(found)
    budget, found = _configured_budget(model, limit, binding)
    issues.extend(found)
    request_budget, found = _request_budget(
        model, limit, binding, bundle.get("request_observation"), bundle.get("checkpoint_context")
    )
    issues.extend(found)
    checks = {"models_http": http, "models_schema": schema, "client_model": client_model,
              "checkpoint_context": checkpoint, "configured_generation_budget": budget,
              "request_generation_budget": request_budget}
    statuses = [check["status"] for check in checks.values()]
    unknown_count = statuses.count("unknown")
    mismatch_count = statuses.count("mismatch")
    overall = "block" if mismatch_count else "unknown" if unknown_count else "observed"
    return {"status": overall, "capture_path": capture_path,
            "capture_path_provenance": "caller_supplied_unverified", "checks": checks,
            "checkpoint_context_provenance": "caller_supplied_unverified",
            "issues": issues, "unresolved_observation_count": unknown_count,
            "blocked_check_count": mismatch_count, "could_not_run_count": unknown_count}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("capture", type=Path, help="saved JSON bundle: models response, OpenClaw config, checkpoint binding")
    args = parser.parse_args(argv)
    try:
        bundle = json.loads(args.capture.read_text(encoding="utf-8"), parse_constant=_reject_json_constant)
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError):
        result = {"status": "unknown", "capture_path": str(args.capture),
                  "capture_path_provenance": "caller_supplied_unverified", "checks": {},
                  "checkpoint_context_provenance": "caller_supplied_unverified",
                  "issues": ["cannot read or parse capture bundle"],
                  "unresolved_observation_count": 1, "blocked_check_count": 0,
                  "could_not_run_count": 1}
    else:
        result = analyze(bundle, str(args.capture))
    print(json.dumps(result, sort_keys=True))
    return 0 if result["status"] == "observed" else 2


if __name__ == "__main__":
    sys.exit(main())
