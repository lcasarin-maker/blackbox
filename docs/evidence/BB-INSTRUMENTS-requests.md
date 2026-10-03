# Request/stream instrumentation proof — 2026-10-03

## Findings and scope

The local evidence tree contains no raw Chat Completions SSE capture, request lifecycle capture, MTP acceptance trace, engine-progress log, or Ray rank trace. `tasks/evidence/DELTA-FORUM-RUNTIME-VERSION-CAPTURE-01/runtime-capture.json` records host/runtime identity and CUDA integrity, not client response chunks or engine lifecycle. `tests/fixtures/provider_trace/*.jsonl` are fixtures for the existing request/worker/provider/restart contract, not native request captures.

Added `tools/chat_sse_capture.py`, a read-only parser for saved OpenAI Chat Completions SSE. OpenAI documents streamed `ChatCompletionChunk` choices, `delta`, `tool_calls`, `finish_reason`, and the `[DONE]` stream sentinel; vLLM documents its OpenAI-compatible Chat Completions endpoint ([OpenAI Chat Completions reference](https://developers.openai.com/api/reference/resources/chat), [vLLM OpenAI-compatible server](https://docs.vllm.ai/en/latest/serving/online_serving/openai_compatible_server/)). The parser preserves raw chunks, text and tool-call deltas, distinguishes absent `tool_calls` from an empty array, and retains `finish_reason`. It labels an absent sentinel as an incomplete capture with unknown termination cause. The supplied path remains unverified.

The reader recognizes UTF-8 BOM and CR/LF/CRLF SSE boundaries while preserving U+2028/U+2029/NEL inside JSON strings; non-standard JSON constants such as NaN and Infinity count as unreadable observations. The output describes client-visible SSE observations only. It does not infer that a stream ending without `[DONE]` was cancelled, that a tool ran, that output was semantically correct, or that internal request/engine/rank progress occurred. Chat Completions chunks expose no MTP accepted-token counter. Existing `provider_trace.py` remains the scoped reader for its JSONL requested/observed provider, worker identity, latency, and restart events.

## Validation

```text
$ python3 -m pytest -q tests/test_chat_sse_capture.py
..........                                                               [100%]
10 passed in 0.04s

$ python3 -m coverage report --include='tools/chat_sse_capture.py'
Name                        Stmts   Miss  Cover
-------------------------------------------------
tools/chat_sse_capture.py     104      0   100%
-------------------------------------------------
TOTAL                         104      0   100%

$ ruff check tools/chat_sse_capture.py tests/test_chat_sse_capture.py tools/runtime_provenance.py tests/test_runtime_provenance.py
All checks passed!

$ pyright tools/chat_sse_capture.py tests/test_chat_sse_capture.py tools/runtime_provenance.py tests/test_runtime_provenance.py
0 errors, 0 warnings, 0 informations

$ python3 -m tools.chat_sse_capture tasks/evidence/DELTA-FORUM-RUNTIME-VERSION-CAPTURE-01/runtime-capture.json
{"capture_path": "tasks/evidence/DELTA-FORUM-RUNTIME-VERSION-CAPTURE-01/runtime-capture.json", "capture_path_provenance": "caller_supplied_unverified", "chunks": [], "could_not_run_count": 1, "done_marker_seen": false, "incomplete_frame_data": [], "issues": ["capture has no [DONE] marker; termination cause unknown", "capture contains no chat completion chunks"], "protocol": "openai_chat_completions_sse", "status": "unknown", "unreadable_observation_count": 1}

$ python3 -m tools.provider_trace tests/fixtures/provider_trace/gpu-healthy.jsonl
{"could_not_run_count": 0, "findings": [], "status": "pass", "unknowns": []}

$ python3 -m tools.provider_trace tests/fixtures/provider_trace/gpu-to-cpu-respawn.jsonl
{"could_not_run_count": 0, "findings": ["request gpu-after-restart: GPU request was served by CPU on worker worker-after"], "status": "block", "unknowns": []}
```

The SSE CLI result is a format check against the only available runtime capture; it reports no response samples and `could_not_run=1`. The provider trace outputs exercise existing fixtures, not a live vLLM request.

## Five card assessments

All cards remain open and retain their original `close_check` definitions.

| Card | Status | Evidence and remaining gap |
| --- | --- | --- |
| `DELTA-FORUM-MINIMAX-TOOLCALL-FUNCTIONAL-CANARY-01` | developed | The parser can retain text/tool-call chunk sequence and final reason from a supplied SSE capture. No raw stack-pinned capture, tool execution result, process health, or rollback was observed. |
| `DELTA-FORUM-MTP-ACCEPTANCE-AND-SEMANTIC-CONTROL-01` | blocked | Chat Completions SSE does not expose the required per-position MTP acceptance signal; no native backend acceptance capture or matched semantic A/B is available. |
| `DELTA-FORUM-QWEN-MTP-PARSER-CANCEL-STATE-CHECK-01` | developed | The parser preserves partial tool-call deltas and whether `[DONE]` was observed. Missing `[DONE]` is only an incomplete capture; cancellation cause, parser recovery, same-process follow-up, and restart behavior remain unobserved. |
| `DELTA-ROOT-GLM53-QUEUED-REQUEST-PROGRESS-GATE-01` | blocked | Client-visible chunks do not expose queue age, prefill progress, decode progress timing, or cancellation state; no backend request-progress capture is present. |
| `DELTA-ROOT-RAY-MULTIENGINE-RANK-PROGRESS-01` | reused | Existing `provider_trace.py` correlates requested/observed provider with worker identity, latency, and restart in its declared JSONL format. Its fixtures contain no Ray engine/rank or collective progress; those native observations remain unavailable. |

Neither `observed` SSE nor provider fixture `pass` closes a card or proves the reported model/runtime behavior.
