# Raw runtime evidence contract, batch 02

This contract defines input to the card-specific predicates in
`tools/runtime_batch02_controls.py`. It does not constitute runtime evidence;
the historical close-check selectors require a separate capture produced by the
relevant host/runtime and stay red while that capture is absent.

All files use a UTF-8 JSON object, schema `bb.runtime.raw.v1`, exact `card_id`,
capture id/time, a contradiction list, subject identity (`oem`, host, image
full `sha256:<64 hex>` digest, model, full checkpoint digest, software versions
required by that card), bounded request identity
(`request_id`, model/checkpoint, token/context/deadline bounds and UTC start/end)
and, if the candidate modifies the runtime, a rollback record with distinct
known-good/candidate digests and equal pre-change/restored state hashes. The
reader caps the raw file at 4 MiB. Missing fields yield `unknown`/CNR; measured
contradictions yield `fail`.

| Card | Additional raw fields and derived predicate |
|---|---|
| GPT-OSS/Ray | Two node identities; per-rank node/GPU/TP allocation; TP=2 placement bundles each reserving GPU; bounded request with a first-token timestamp inside request interval and stop on both nodes; output count under `max_tokens`; captured timeout control with RayChannelTimeoutError inside deadline. |
| llama.cpp RPC | Distinct client/server PIDs and request-bound effective transport; exact functional output oracle, finish and KV digest; >=3 timestamped UMA/PSI samples attributed to server cgroup; trial exit/signal records for client-first, server-first and TCP teardown; known-good rollback. |
| M2 compaction | Same request across >=2 state-digest transitions; separate compaction, clean-reset and no-compaction sessions; clean reset matches captured KV-state hashes; each session's raw SSE is parsed by `chat_sse_capture` and checked against a SHA-256-pinned independent JSON oracle under `tasks/evidence/<id>/oracles/`; all 12 cells of the request-bound prefill/decode/process/host metric matrix have finite timestamped values. |
| MiniMax canary | Three ordered requests in the same observed process PID: text, mock tool, text; raw SSE parsed and tool args JSON reconstructed from deltas then compared to a SHA-256-pinned independent oracle sidecar; same-stack graph/eager warmup with rank progress; lazy/eager loader A/B tensor names compared against pinned checkpoint PLE manifest plus effective dtype/hash; successful HTTP/finish for every request; rollback. |
| MTP acceptance | Captured draft/target tokens are the source of per-position acceptance (`draft == target`); reported vector must match; semantic output equals exact reference; negative mismatched pair is rejected; rollback. |
| Muse/DFlash | Resolved class equals configured class and is bound to checkpoint digest; two measured runs at `max_num_seqs=32/33`; finite raw metrics and nonempty semantic canaries at both sizes; untrusted-tool canary at 32; rollback. |
| NCCL TP orchestration | Per-node launcher/env/interface/subnet identities; rank-level all-reduce exit and measured bandwidth; same bounded request and per-rank logs under recipe and manual launch; both return output and stop, outputs match; rollback. |
| Nemotron SM121 | Subject architecture is SM121; captured operation list matched to required operations; each operation has kernel name, load and first-inference exit codes and raw output; output equals pinned reference; unsupported-architecture negative control is rejected. |
| OpenClaw/vLLM | Existing `openclaw_contract.analyze` derives served model, checkpoint context and generation-budget compatibility from captured raw bundle; raw negative requests demonstrate wrong-model 404, context overflow 400 and nonpositive max_tokens 400; positive request returns 200 and streamed tool args match exact oracle. |
| Qwen cold compile | Rank-specific cold-compile logs and timestamped memory/headroom series bound to request; eager mode 0 functional control; timestamped SSH and ICMP command exit codes with command hashes stay zero across compile; rollback. |

Positive unit fixtures exercise parsing and predicate branches only. They never
populate evidence directories or satisfy a real close-check selector.
