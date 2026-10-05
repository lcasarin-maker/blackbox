# Runtime closure contracts — generated batch 04

Input is a bounded `bb.runtime.raw.v1` capture at
`tasks/evidence/<card-id>/runtime-capture.json`, with subject/image/checkpoint,
effective stack versions, a request bound, and a SHA-256-checked rollback
record. Any referenced oracle is a separate file under the card's `oracles/`
directory and is verified by its content digest. Missing captures remain
`unknown`; only the historical close selector's required `pass` satisfies its
gate.

| Card | Raw predicate |
| --- | --- |
| DSML parser recovery | Streaming and complete responses for partial reasoning, truncated arguments, `tool_choice=none`, quoted tool markers, and complete tool output; parsed text and typed calls match a pinned independent oracle, with no spurious invocation. |
| GLM queued requests | Per-request prefill/decode/KV samples distinguish a queued request with no progress past a bounded interval from a concurrently progressing decode request, while KV remains below saturation. |
| MiMo overlay/prefill fairness | At least two target nodes each bind image/checkpoint/overlay/draft/tokenizer/modification records; image/checkpoint match the request subject, path-resolution output binds logical and resolved paths, and file-backed component hashes are recomputed from bounded evidence artifacts. Missing overlay and unsupported modality controls fail explicitly; semantic output matches a hash-pinned oracle; strictly timed concurrent long-prefill/short-decode requests both progress. |
| MiMo patch supersession | Source and patch text plus actual apply exit distinguish an affected symbol from a refactored/superseded symbol; announced text/audio canaries succeed and rollback is measured. |
| Ray multi-engine progress | Two distinct engine/image/resource tuples have repeated rank/collective observations; the capture identifies one progressing engine and one stalled engine and records request-bound Ray/MP A/B outcomes and rollback. |
| Recipe memory | Measured component vectors recompute fit/exceeds; any unknown component must produce `unknown`; a separate measured fit case, causal post-warmup token/output samples, stack identity, and rollback are present. |
| Tokenizer semantics | Old/fixed text, image below/above prior bound, affected image regression, and Harmony/tool cases derive sentinel counts from the captured prompt/response strings; fixed cases retain sentinels, affected controls reproduce loss, candidate soak matches independent SHA-pinned oracles, and rollback is present. |
| Triton allocator patch state | Source/patch symbols and apply exit derive missing/applied/superseded state; per-rank/thread cold/warm generation canaries, source audit reference, and rollback are required. |

`tests/test_runtime_batch04_controls.py` uses bounded fake captures only to
prove each parser's discrimination. It does not close runtime experiments.
