# Feasibility instrument dispositions — 2026-10-03

This review covers the 18 generated IDs in feasibility batches 07, 08, 11, and
12 in source order. It reads existing cards, repository instruments/tests, and
stored evidence. It adds no instrument or schema: the unresolved items depend
on real model/OEM inputs, vendor contracts, or lab-only changes that this pass
explicitly excludes. No host/GPU/model trace, network action, firmware/hotplug
change, restart, or live drift query was run. All cards remain open, and their
`close_check` values are unchanged.

The verdict files are the machine-readable dispositions:

- `/tmp/bb-inst-feasibility-07-verdict.json` — 5 IDs.
- `/tmp/bb-inst-feasibility-08-verdict.json` — 5 IDs.
- `/tmp/bb-inst-feasibility-11-verdict.json` — 5 IDs.
- `/tmp/bb-inst-feasibility-12-verdict.json` — 3 IDs.

## Batch 07

| ID | Disposition | Evidence and remaining boundary |
|---|---|---|
| `DELTA-FORUM-QWEN35-NVFP4-CUTLASS-FIRST-REQUEST-GATE-01` | `deferred_lab` | `tools/preflight.py` and `tests/test_preflight.py` check runtime architecture compatibility; they do not exercise a real first Qwen3.5 NVFP4 request or semantic fallback. A pinned, recoverable model/GPU run is required. |
| `DELTA-FORUM-RAY-TORCH-GRAPH-HANG-01` | `deferred_lab` | The report requires a two-node Ray/vLLM prompt reproduction and per-rank progress with the exact Torch/CUDA/Ray/NCCL tuple. No such workload was run. |
| `DELTA-FORUM-THERMAL-AUXILIARY-COOLING-AND-CLOCK-CAP-01` | `deferred_lab` | `tools/atom_gpu_telemetry.py` already reads thermal/GPU observations. No matched OEM/workload baseline measures the cooling or clock-cap tradeoff; no physical or clock change was made. |
| `DELTA-ROOT-DISPLAY-CARVEOUT-OEM-FIX-GATE-01` | `needs_contract` | `tools/preflight.py:check_drm` requires the effective modeset and target KMS/recovery declarations. The stored DRM snapshot has `could_not_run=1`; the reported Adjustable Display Reserved Memory capability/value has no verified OEM contract. |
| `DELTA-ROOT-GX10-SOC-EC-CABLE-RECOVERY-CANDIDATE-01` | `needs_contract` | The report records PCI/EEPROM failures and a candidate SoC+EC tuple. `network_inventory` can observe current PCI/driver/RDMA metadata, but no vendor-approved, separated firmware sequence and rollback are established. No firmware or hotplug trial was run. |

## Batch 08

| ID | Disposition | Evidence and remaining boundary |
|---|---|---|
| `DELTA-ROOT-MIMO-OVERLAY-AND-PREFILL-FAIRNESS-01` | `needs_contract` | The proposal needs a trusted per-node image/checkpoint/overlay/draft/tokenizer manifest, a semantic oracle, and per-rank progress definitions. Existing runtime preflight does not define these contracts; a speculative schema would invent inputs. |
| `DELTA-ROOT-MIMO-PATCH-SUPERSESSION-GATE-01` | `needs_contract` | External patch reports span commits, symbols, draft modes, modalities, and image branches that were not audited. A trusted mapping from exact patch identity to effective code and supported behavior is missing. |
| `DELTA-ROOT-SUBAMBIENT-COOLING-AND-UMA-CANARY-01` | `deferred_lab` | Existing telemetry does not establish dew point, airflow, condensation risk, or a matched workload baseline. Physical cooling and long-soak work require OEM limits; none was attempted. |
| `DELTA-ROOT-TOKENIZER-PATCH-SEMANTIC-GATE-01` | `needs_capture` | The exact affected/corrected tokenizer, checkpoint, patch digest, expected token sentinels, and modality inputs are absent from a trusted local capture. No model/tokenizer run was performed. |
| `DELTA-ROOT-TRITON-ALLOCATOR-PATCH-STATE-GATE-01` | `needs_contract` | The proposed global allocator monkeypatch is loaded through `.pth`, depends on a prior commit, and has later supersession reports. External code, wheel/image identity, symbol scope, and memory-lifetime semantics remain unaudited. |

## Batch 11

| ID | Disposition | Evidence and remaining boundary |
|---|---|---|
| `FORUM-00-CX7-HOTPLUG-FAN-PROTECTION` | `deferred_lab` | Existing PCI, kernel-signal, firmware, and thermal instruments cover partial observations. The stored progress says zero fan/CX7 A/B tests and no supported RPM signal. The hotplug/thermal causal test requires an identified lab unit; no change was attempted. |
| `FORUM-00-GB10-THERMAL-RESIDENCY-ADMISSION` | `reused` | Thermal zones, trip points, GPU state, and current corroboration already exist in `tools/atom_gpu_telemetry.py`/`tools/thermal_coverage.py`. Stored progress leaves CPU/idle and model-residency calibration open with zero A/B runs; no thresholds or process actions were added. |
| `FORUM-00-REALTEK-EEE-DIRECT-LINK` | `reused` | Existing host evidence records EEE enabled but inactive for `enP7s7`. It does not report partner-advertised modes or reproduce direct-link stalls. No EEE/network change or rollback test was run. |
| `FORUM-02-GX10-READ-INTEGRITY` | `reused` | `tools/read_integrity.py` already compares bounded buffered and `O_DIRECT` reads against a caller-supplied digest and has positive/negative/error controls. Its fixture reference is not an independent trust anchor; incident data and RAS/NVMe/firmware correlation remain uncaptured. |
| `FORUM-02-USB-UVC-EP0` | `reused` | Existing USB/xHCI forensics detect the failure aftermath. Stored host observation has no UVC EP0 reproduction, identified corrected version, or prevention test. No camera/USB sequence was exercised. |

## Batch 12

| ID | Disposition | Evidence and remaining boundary |
|---|---|---|
| `DEBT-HOST-DEPLOYED-DRIFT-01` | `needs_decision` | Stored `fail.txt` reports 41 subjects reviewed, 2 divergences, 0 absent, and 1 suspended; equality/divergence/absence controls already exist. The card names host synchronization as pending authorization. No deployed file was queried or changed in this pass. |
| `DEBT-JUDGE-THREAT-SWEEP-TOOLS-01` | `needs_contract` | The pinned Simplecode 8.9.6 runtime has artifact SHA-256 `b556a108901d051bf05cb940f350f741f4dcf412a37ce2dc10814a6aea38fe2d`; its `AGENT_THREAT_TREES` excludes `tools/`, and the stored report says the sweep read zero files across no tree. Exact dependency: land the already-proposed upstream source change to `simplecode/verification/adversarial_judge.py` (`AGENT_THREAT_TREES`/`collect_threat_sources`), rebuild through the authoritative producer, publish a matching runtime and `kit.lock`, then prove the `tools/` homoglyph negative control and actual swept-file count. Do not edit the generated bundle or upstream checkout here. |
| `DEBT-PROCESO-SIN-TECHO-TUMBO-LA-MAQUINA-DOS-VECES` | `needs_decision` | The process guardian and 20 offline tests already exist. Its live check is open because the installed service predates current source, and the card says restart awaits the earlier operational decision. No service state was inspected or changed. |

Existing evidence is deliberately reported with its limits. The GSP preflight's
healthy sample returned `pass` with `could_not_run=0`, but did not reproduce a
GSP fault. The stored DRM and kernel-update preflights each retain one
`could_not_run`; the thermal recovery profile retains one; the UVC host
observation retains one. The read-integrity fixture reports zero collection
errors while its reference provenance remains unverified. The threat-sweep
zero is an empty-scope result, not a clean scan. No new measurement or test run
was needed because this pass changed no code; stored literal results above are
not presented as new runs.
