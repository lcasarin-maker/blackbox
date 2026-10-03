# Runtime instrumentation proof — 2026-10-03

## Instrument result

`tools/runtime_provenance.py` reads saved Prometheus text for the exact five vLLM metric names already consumed by `tools/atom_gpu_telemetry.py`. It preserves the raw value, observed metric name, labels, optional millisecond timestamp, declared `TYPE`, and raw `HELP`. The capture path is caller supplied and explicitly unverified. No `TYPE` line defaults to `untyped`, as specified by Prometheus. Missing unit metadata is recorded as `not_declared_in_capture`; no numeric value is converted to bytes or inferred from RSS or GPU memory.

The reader reports `observed` for parseable series, `partial` when the capture has protocol or interpretation issues, and `unknown` when it has no recognized sample or cannot be read. Malformed samples and duplicate metric/label combinations increment `could_not_run_count`. Contradictory `TYPE` declarations mark affected observations indeterminate and count them as could not run. It is a provenance reader; it does not evaluate any runtime subject or inference contract.

The parser follows the [Prometheus exposition format](https://prometheus.io/docs/instrumenting/exposition_formats/): optional int64 sample timestamps, default `untyped` when `TYPE` is absent, unique metric/label combinations, and the specified label escape forms. Duplicate `TYPE`/`HELP` declarations remain explicit issues.

## Validation

Commands and literal output:

```text
$ python3 .simplecode/run.py --version
simplecode 8.9.6 (content 83760c71c9eb)
  bundle: /tmp/bb-inst-runtime/.simplecode/runtime.zip
  artifact: b556a108901d

$ python3 -m pytest -q tests/test_runtime_provenance.py
.................                                                        [100%]
17 passed in 0.04s

$ ruff check tools/runtime_provenance.py tests/test_runtime_provenance.py
All checks passed!

$ pyright tools/runtime_provenance.py tests/test_runtime_provenance.py
0 errors, 0 warnings, 0 informations

$ python3 -m coverage report --include='tools/runtime_provenance.py'
Name                          Stmts   Miss  Cover
-------------------------------------------------
tools/runtime_provenance.py     197      0   100%
-------------------------------------------------
TOTAL                           197      0   100%

$ python3 -m tools.runtime_provenance tasks/evidence/DELTA-FORUM-RUNTIME-VERSION-CAPTURE-01/runtime-capture.json
{"could_not_run_count": 1, "issues": ["capture contains no recognized vLLM metric samples"], "samples": [], "status": "unknown", "unreadable_observation_count": 0}
```

The last command is a negative format check: the available `runtime-capture.json` is a host/runtime identity capture, not raw Prometheus text. It has no `/metrics` payload, so the parser correctly returned no samples. Native Prometheus capture parse: `could_not_run=1`. The tests use controlled text samples and malformed controls; they do not substitute for a captured runtime scrape.

## Five card proofs

Only the KV provenance card gains a new parser. The other four reuse pre-existing host/runtime capture fields as partial identity evidence; reading Prometheus does not validate their subjects. Each card remains open with its original close check unchanged.

| Card | Status | Evidence and unresolved subject check |
| --- | --- | --- |
| `DELTA-FORUM-KV-QUANT-METRIC-PROVENANCE-GATE-01` | developed | The parser retains the exact KV usage series provenance; raw runtime scrape, exact-stack KV byte measure, functional comparison, and negative hardware control remain `could_not_run`. |
| `DELTA-FORUM-VLLM-GB10-ARCH-AND-BUILD-MATRIX-01` | reused | The existing runtime capture records architecture, driver/CUDA and image identity. Compiler/PTXAS flags, pinned build matrix, model load/generation and mismatch control remain `could_not_run`. |
| `DELTA-FORUM-VLLM-RAY-GB10-RESOURCE-FIX-01` | reused | Existing capture records running image refs and image IDs. Ray per-node resource map and positive/negative admission result remain `could_not_run`. |
| `DELTA-ROOT-CONTAINER-EFFECTIVE-BUILD-AND-OFFLINE-GATE-01` | reused | Existing capture records the runtime version and container image ref/ID. Effective build artifacts, offline build result and rollback remain `could_not_run`. |
| `FEATURE-FORUM-GB10-RUNTIME-COMPAT-01` | reused | Existing capture supplies a partial driver/CUDA/architecture/image tuple. Pinned model/backend compatibility, functional generation and semantic negative control remain `could_not_run`. |

No card is declared closed or functionally validated by these instrument results.
