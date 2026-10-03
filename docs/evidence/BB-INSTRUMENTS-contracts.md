# Request contract instrumentation — 2026-10-03

## Scope and evidence

`tools/openclaw_contract.py` reads one saved JSON evidence bundle offline. The bundle contains a recorded HTTP status/body for `GET /v1/models`, the actual documented OpenClaw config paths `agents.defaults.model.primary` and `models.providers.<provider>.models[]`, and an explicit checkpoint binding (`checkpoint_id`, `served_model_id`, `context_limit_tokens`). It emits only status, model identifier, token counts, and fixed issue descriptions; it never copies config bodies, prompts, headers, credentials, or model responses into diagnostics. Every supplied capture, checkpoint binding, and token observation is marked `caller_supplied_unverified`.

The native contract fields come from [OpenClaw's custom provider config reference](https://docs.openclaw.ai/gateway/config-tools/custom-providers#model-catalog-entries), which places `contextWindow` and `contextTokens` on `models.providers.*.models[]` and defines `contextTokens` as an active-input cap. The [agent model configuration reference](https://docs.openclaw.ai/gateway/config-agents/models#model-selection) gives `agents.defaults.model.primary` as `provider/model`. vLLM documents listing models through `GET /v1/models` in its [serving quickstart](https://docs.vllm.ai/en/latest/getting_started/quickstart/) and `--served-model-name` as the API model name in the [`vllm serve` reference](https://docs.vllm.ai/en/latest/cli/serve/). The parser accepts the OpenAI list shape `data[].id`; [OpenAI's model-list reference](https://platform.openai.com/docs/api-reference/models/list) documents that response shape.

The config headroom check is separate from an actual request budget. Configured `contextTokens` is only an input cap; it is not observed token usage. The tool calculates configured output headroom as `min(maxTokens, min(contextWindow, checkpoint_limit) - contextTokens)`, requiring a positive result and explicit checkpoint/model binding. A request-level budget is `unknown` without integer `prompt_tokens` and `max_tokens` observations bound to the same model and checkpoint. For a supplied request, `max_tokens` remains literal; if it exceeds remaining headroom the request check is `mismatch`, while `output_budget_tokens` reports only a suggested headroom and never an implicit clamp. No character/token estimate is made. Neither an `observed` artifact check nor a 200 model-list response proves successful generation or tool execution.

The available local runtime capture contains runtime identity rather than a `/v1/models` response, OpenClaw config, checkpoint context binding, or request token usage. No native model-list capture was available, so no live contract result or completion can be claimed.

## Validation

```text
$ python3 -m pytest -q tests/test_openclaw_contract.py
..............                                                           [100%]
15 passed in 0.04s

$ python3 -m coverage report --include='tools/openclaw_contract.py'
Name                         Stmts   Miss  Cover
------------------------------------------------
tools/openclaw_contract.py     168      0   100%
------------------------------------------------
TOTAL                          168      0   100%

$ ruff check tools/openclaw_contract.py tests/test_openclaw_contract.py
All checks passed!

$ pyright tools/openclaw_contract.py tests/test_openclaw_contract.py
0 errors, 0 warnings, 0 informations

$ python3 -m tools.openclaw_contract tasks/evidence/DELTA-FORUM-RUNTIME-VERSION-CAPTURE-01/runtime-capture.json
{"blocked_check_count": 0, "capture_path": "tasks/evidence/DELTA-FORUM-RUNTIME-VERSION-CAPTURE-01/runtime-capture.json", "capture_path_provenance": "caller_supplied_unverified", "checkpoint_context_provenance": "caller_supplied_unverified", "checks": {"checkpoint_context": {"status": "unknown"}, "client_model": {"configured_model_id": null, "status": "unknown"}, "configured_generation_budget": {"input_cap_tokens": null, "output_budget_tokens": null, "status": "unknown"}, "models_http": {"observed_status_code": null, "status": "unknown"}, "models_schema": {"model_count": 0, "status": "unknown"}, "request_generation_budget": {"evidence_provenance": "caller_supplied_unverified", "output_budget_tokens": null, "status": "unknown"}}, "could_not_run_count": 6, "issues": ["captured GET /v1/models status code is unavailable or malformed", "OpenClaw primary model does not resolve to exactly one configured provider model", "positive context limit explicitly bound to this model/checkpoint is unavailable", "configured contextWindow, contextTokens, or maxTokens is missing or non-integer", "request-level budget unknown: bound tokenizer/usage counts and max_tokens were not supplied"], "status": "unknown", "unresolved_observation_count": 6}
exit 2
```

The positive test bundle is constructed in unit tests and exercises only the captured-file contract. Negative controls cover 404, served-ID mismatch, empty/blank/malformed model lists, negative `maxTokens`, model context greater than the checkpoint bound, input cap greater than the effective context, exhausted budget, bad checkpoint bindings, and absent or over-limit tokenizer counts, and a request whose `max_tokens` exceeds its 100-token headroom (preserving 8192 as requested and marking mismatch). They do not run OpenClaw/vLLM or issue a request.

## Five card assessments

All cards remain open and retain their original `close_check` definitions.

| Card | Status | Evidence and remaining gap |
| --- | --- | --- |
| `DELTA-FORUM-OPENCLAW-VLLM-REQUEST-CONTRACT-01` | developed | Added offline captured-evidence preflight; no local `/v1/models`, OpenClaw config, checkpoint context, or tokenizer/usage capture exists. No endpoint or generation was run. |
| `DELTA-FORUM-QWEN-LONG-AGENT-STOP-01` | reused | Existing SSE reader retains client-visible `finish_reason` and tool-call deltas; there is no native long-session capture and these fields alone do not prove premature stop or recovery. |
| `DELTA-FORUM-QWEN-TOOLCALL-WEDGE-01` | reused | Existing SSE reader can retain visible partial tool-call fragments; no engine/rank/collective progress or MTP acceptance signal is available. |
| `DELTA-FORUM-QWEN38-LONG-RUN-JSON-CORRECTNESS-CANARY-01` | blocked | The SSE reader preserves text fragments but does not reconstruct/validate JSON semantics; no raw long-run response fixture or paired correctness capture exists. |
| `DELTA-ROOT-DSML-PARSER-RECOVERY-BOUNDARY-01` | reused | Existing SSE reader can preserve visible leakage/deltas; no reproducible long-context history or parser-recovery telemetry exists. |

None of the `reused` SSE observations establish cancellation, wedge cause, parser recovery, tool safety, or semantic correctness.
