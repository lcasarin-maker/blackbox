# Runtime closure contracts — generated batch 03

These controls consume one bounded `bb.runtime.raw.v1` record at
`tasks/evidence/<card-id>/runtime-capture.json`. The shared envelope binds a
real subject, full image/checkpoint SHA-256 digests, an effective software
version map, request model/checkpoint, token/context/deadline limits, capture
time, and a rollback record. Selectors require `status == "pass"`; absent raw
records return `unknown` and keep the original close checks visibly red.

| Card | Additional raw observations checked |
| --- | --- |
| QWEN-LONG-AGENT-STOP | At least two checkpoint variants (`nvidia_nvfp4`, `alternative`) under pinned harness/runtime/sampling; turn task state, request, finish reason, tool-call count, explicit manual resume for an open stop, no mutating replay, and rollback. |
| QWEN-MTP-PARSER-CANCEL | Parser/MTP/cancel paired matrix; each pair has before/after raw SSE, correctly typed tool calls matched to a separately hash-pinned oracle, same bounded request, and rollback. |
| QWEN-SERVICE-OOMD-CACHE | Chronological PSI/swap/UMA/cache bytes with UTC timestamps, journal/cgroup OOMD event within the measured interval, dependent-service transition after the event, redacted pre-recovery SHA-256, pinned system/kernel/driver/runtime. |
| QWEN-TOOLCALL-WEDGE | Bounded request/phase, pinned runtime/model, multiple causal timestamp samples for at least two ranks with unchanged collective sequence, raw draft/target tokens and acceptance recomputed from token pairs, and a preserved bundle digest. |
| QWEN35-CUTLASS-FIRST-REQUEST | Pinned driver/vLLM/quant/backend, effective image/model/backend build, readiness before first request, CUDA log and exit, candidate/reference correctness, and rollback. |
| QWEN38-LONG-RUN-JSON | Pinned runtime/tokenizer/template/sampling/KV/MTP, paired BF16/candidate runs on the same checkpoint and request, complete turn JSON compared with an independent hash-pinned oracle and with its paired run, plus rollback. |
| RAY-TORCH-GRAPH-HANG | Exact host/container Torch, CUDA, vLLM, Ray and NCCL versions, graph/eager runs on the same request, per-rank collective progress and bounded GPU utilization samples, plus rollback. |
| VLLM-GB10-ARCH-BUILD | Image/wheel/PTXAS/architecture/resolver/model/backend tuple; exact required operation matrix with build/import/load/first inference raw results and finite output; wrong-toolchain negative control and rollback. |
| VLLM-RAY-GB10-RESOURCE | Pinned Ray/vLLM/driver/kernel versions, per-node GPU resource/image/SM mapping, backend/kernel smoke on the bounded request, unsupported-image negative control. |
| ROOT-CONTAINER-OFFLINE | Two distinct container names/ports with image/model/checkpoint/patch identity, load and inference outcomes, aggregate memory reservation, network-disabled boot and missing-artifact negative capture, plus rollback. |

The fixtures in `tests/test_runtime_batch03_controls.py` exercise parser
discrimination only. They use temporary sidecars and never satisfy a runtime
close check. Existing captures were absent when the selectors were executed;
no hardware experiment, host mutation, network request, or model workload was
run to manufacture closure evidence.
