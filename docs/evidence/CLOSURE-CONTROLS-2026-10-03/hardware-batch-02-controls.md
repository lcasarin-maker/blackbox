# Batch 02 hardware controls — source and evidence matrix

Generated in source order from `tasks/evidence/CLOSURE-CONTROLS-2026-10-03/hardware-batch-02.json` (10 IDs). Card bodies are copied verbatim from the backlog paths in that generated source. Synthetic test fixtures validate predicates only; they do not authenticate or close live hardware findings.

## Requirement mapping and explicit gaps

The generated batch order below is the source of each ID. Predicate names and gaps are mapped to the verbatim card bodies below; PASS-shaped unit captures exercise parsers only.

| Generated card | Source requirements mapped to code | Predicate gaps / live evidence |
|---|---|---|
| 0 — CUTLASS SM121 | `_cutlass_plan` pins CUTLASS/CuTe revisions, backend, op, model/input digests, batch, concurrency, soak and tolerance. `_cutlass_build` checks GB10/SM12x identity, captured build material, rejects forced SM100, and inspects ELF. `_cutlass_canary` recomputes finite logits against reference and checks completed requests, batch, concurrency and soak. `_cutlass_negative` requires a failing tcgen05 path with an unsupported-ISA diagnostic. | Caller-provided build/capture provenance is unauthenticated; no live build, canary, or hardware capture is present, so CNR. Performance is not claimed. |
| 1 — CX7 firmware update guard | `_fw_guard` requires separately trusted exact-plan approval, ASUS GX10 scope, PCI device/PSID/firmware/BME/driver binding, the package’s signed APT Release→Packages→deb hash chain, maintainer-script/indirect-helper scanning, and recovery data. | The approval anchor and a live device/recovery capture are absent (CNR). Script constructs outside the bounded recognized static forms are UNKNOWN. No flash or host change was run. |
| 2 — physical topology alias | `_topology_map` correlates planned PCI BDF, connector, netdev and native inventory; `_topology_traffic` consumes per-link disconnect/loopback controls, sustained peer traffic and NCCL observations, rejecting disconnected or mismatched links. | No physical disconnect/loopback or live peer test was authorized/performed; current evidence is CNR. Caller-supplied captures do not authenticate physical provenance. |
| 3 — post-hotplug | `_posthotplug_pci`, `_posthotplug_services`, and `_posthotplug_traffic` bind the planned endpoint, require fresh identity-bound diagnostics, inspect PCI/AER/driver/link and check bidirectional RDMA plus NCCL completion/error counts. | No actual hotplug action or live post-hotplug capture was performed; CNR. Unit tests only exercise a synthetic captured sequence. |
| 4 — RDMA asymmetry retest | `_asymmetry_plan` requires exactly cold, individual reboot, sequential reboot, and hotplug cases plus a predeclared ratio. `_rdma_stack_identity` compares both OEM/BIOS/kernel/CX7 tuples to the plan and compatibility references. `_asymmetry_pair` parses successful native bidirectional `ib_write_bw`; cable PN and ratio are required. | Approval anchor and every scenario capture are missing, therefore CNR. No reboot/hotplug was performed. The predeclared ratio is an experiment-plan input, not a universal threshold. |
| 5 — Dual Spark power/reset | `_dual_spark` requires two distinct hosts, repeated cycles, OEM shutdown procedure, pinned model/input, separate plan approval, matching stack identity, and before/after/control observations with matched workload identity and positive throughput. `_power_compare` now prints per-cycle after-before and control-before deltas for throughput, watts, clock and link bandwidth. | No power cycle or live capture was performed; CNR. Deltas remain observational and establish no causal claim or universal recovery threshold. Caller-provided source excerpts are digest-consistent, not authenticated. |
| 6 — KV quant metrics | `_kv_contract`, `_kv_snapshots`, `_kv_runs`, and `_kv_quant` require exact workload/mode inputs, separate host/cgroup/RSS/framework-KV counters, baseline and quantized runs, measured prefill/decode and recomputed output error against predeclared tolerance. `_kv_vendor_support` also requires a primary-domain source excerpt binding the actual GB10 manufacturer/product/kernel and exact backend to explicit support language; an explicit incompatibility fails. | No live capture is present (CNR). The preserved URL/text/hash are caller-supplied; they prove byte consistency, not that NVIDIA authored or endorsed the statement. |
| 7 — memory recovery soak | `_memory_soak`, `_memory_samples`, and `_memory_recovery_gate` require a separately approved ≥2-hour predeclared duration/cadence, native `free -b`, PSI and client/server PID/RSS samples, stable process start identities, ordered client-then-server termination, UMA recovery, and a healthy server control series. | No live multi-hour series/termination is present; CNR. No process termination was performed. The minimum duration is taken from the source’s “multihour” requirement as a conservative formalization. |
| 8 — OTA effective tuple | `_ota_observations` parses pre-update, post-update and rollback OTA/build/kernel/loaded+disk driver/CUDA/EC/carveout values. `_ota_compare` checks a complete predeclared supported tuple against OEM references and exact rollback. `_ota_soak` now requires repeated native `free -b`/PSI samples, the planned exact workload argv, completed requests bound to the model/input/PID, live `ps` readback with stable PID start time, bounded per-sample capture windows and planned soak duration/cadence. | No approved plan or live OTA/rollback/soak capture; CNR. The compatibility excerpt remains caller-supplied and digest-consistent, not authenticated. |
| 9 — recovery APT runbook | `_recovery_apt`/`_recovery_packages` require last kernel/driver/package from native dpkg history, OEM primary recovery reference, external console probe, read-only procedure steps (preserve/console/media/rollback/RMA), and native SHA-256 match for recovery media. | No live recovery-console/media capture; CNR. This verifies a recovery runbook and media identity, not an actual boot/recovery intervention. |

Predicate criteria are implemented across all ten cards; no live finding is closed by this work. All ten remain open until real evidence and their original close checks pass.

## Verification snapshot

- `python3 -m pytest -q tests/test_hardware_batch02_controls.py`: 41 passed.
- `ruff check tools/hardware_batch02_controls.py tests/test_hardware_batch02_controls.py`: clean.
- `pyright tools/hardware_batch02_controls.py`: 0 errors, 0 warnings, 0 informations.
- Branch coverage: 75% for the full module; 1,438 statements, 294 missed, 782 branches, 272 partial. The remaining coverage work is open and no lines/branches are excluded.
- Generated verdict: `/tmp/bb-closure-hardware-batch02-verdict.json`, 10 source-ordered rows, 10 `unknown` because this worktree has no live capture directories. SHA-256: `605246296699166b960f8629c37920e438c4113b2f141b8796011e3b3d286688`.
- `python3 /home/lcasarin/.Codex/tools/triage.py merge --dir /tmp/bb-controls-hardware-triage-final --expected tasks/evidence/CLOSURE-CONTROLS-2026-10-03/hardware-batch-02.json --require id,status,reason,files,control_command,evidence_needed`: `returned: 10 of 10`.

## `DELTA-FORUM-CUTLASS-SM121-ISA-GATE-01`

- Control: `tools/hardware_batch02_controls.py::_cutlass`.
- Tests: `tests/test_hardware_batch02_controls.py::test_cutlass_sm121_complete_canary_recomputes_logits_and_rejects_bad_accuracy` exercises a synthetic raw PASS and a contradictory/negative FAIL; `test_missing_batch02_capture_is_could_not_run` confirms missing evidence returns UNKNOWN for this ID.
- Live status: no authenticated complete host capture was verified in this isolated worktree; preserve UNKNOWN/CNR and keep the finding open.
- Source body (verbatim):

```text
## Evidencia y alcance

Trabajo separado del ámbito de su ficha madre, conservando la fuente original. Los reportes de foro siguen sin validación local y no se convierten en recomendaciones automáticas.

**DELTA-FORUM-CUTLASS-SM121-ISA-GATE-01.** Un hilo de CUTLASS/Python CuTe debate que las operaciones `tcgen05`/block-scaled FP4 están limitadas intencionalmente a arquitecturas SM100/SM110 y que SM12x (GB10/SM121) no implementa ese instruction path; un maintainer responde que FP4 en SM120/SM121 debe usar sus rutas MMA soportadas, no etiquetar la GPU como SM100 para pasar un guard ([359598, post 18](https://forums.developer.nvidia.com/t/359598/18)). Otra respuesta NVIDIA dice que el trabajo de rendimiento NVFP4 se concentra en backends CUTLASS/FlashInfer/vLLM, sin dar fecha o aceptar una configuración final ([post 40](https://forums.developer.nvidia.com/t/359598/40)). Antes de usar kernels externos, revisar el ISA/arch efectivo y gatear el backend por capacidad real; nunca forzar `CUTE_DSL_ARCH=sm_100a` para ocultar mismatch. El canary debe verificar compilación, logits finitos, exactitud contra referencia, requests/batching y soak bajo SM121. Los enlaces upstream y resultados de terceros del hilo no fueron auditados; no se demuestra rendimiento actual ni un fix listo.

Fuentes: tasks/backlog/FEATURE-FORUM-GB10-RUNTIME-COMPAT-01.md.
```

## `DELTA-FORUM-CX7-FW-UPDATE-GUARD-01`

- Control: `tools/hardware_batch02_controls.py::_fw_guard`.
- Tests: `tests/test_hardware_batch02_controls.py::test_cx7_firmware_guard_scans_exact_signed_package_scripts` exercises a synthetic raw PASS and a contradictory/negative FAIL; `test_missing_batch02_capture_is_could_not_run` confirms missing evidence returns UNKNOWN for this ID.
- Live status: no authenticated complete host capture was verified in this isolated worktree; preserve UNKNOWN/CNR and keep the finding open.
- Source body (verbatim):

```text
## Evidencia y alcance

Trabajo separado del ámbito de su ficha madre, conservando la fuente original. Los reportes de foro siguen sin validación local y no se convierten en recomendaciones automáticas.

**DELTA-FORUM-CX7-FW-UPDATE-GUARD-01.** En ASUS GX10 PSID NVD0000000087, el dueño atribuye a `dpkg --configure -a`/`mlnx-fw-updater 25.10-1.7.1.0` un flash CX7 de 28.45.4028 a 28.47.1088; después informa ambas NIC en `pre-init`, timeout `-110` y ninguna recuperación con reinstalación. NVIDIA dice que ingeniería sigue investigando. Los logs, `mstdump` y el diagnóstico adjunto no se leyeron, por lo que mecanismo y causalidad siguen sin confirmación ([373900](https://forums.developer.nvidia.com/t/373900)). Hacer que el preflight detecte escrituras de firmware CX7 invocadas indirectamente, verifique OEM/PSID/versión exacta, prerequisitos BME/DMA y canal firmado autorizado, y falle cerrado si falta evidencia. Ensayar primero en hardware reemplazable con captura pre/post y ruta de recuperación; nunca flashear para reproducir.

Fuentes: tasks/backlog/FEATURE-APT-CRITICAL-METAPACKAGE-GUARD.md.
```

## `DELTA-FORUM-CX7-PHYSICAL-TOPOLOGY-ALIAS-CHECK-01`

- Control: `tools/hardware_batch02_controls.py::_topology`.
- Tests: `tests/test_hardware_batch02_controls.py::test_physical_topology_native_map_and_disconnected_negative` exercises a synthetic raw PASS and a contradictory/negative FAIL; `test_missing_batch02_capture_is_could_not_run` confirms missing evidence returns UNKNOWN for this ID.
- Live status: no authenticated complete host capture was verified in this isolated worktree; preserve UNKNOWN/CNR and keep the finding open.
- Source body (verbatim):

```text
## Evidencia y alcance

Trabajo separado del ámbito de su ficha madre, conservando la fuente original. Los reportes de foro siguen sin validación local y no se convierten en recomendaciones automáticas.

[368726](https://forums.developer.nvidia.com/t/368726) records a failed four-node switchless ConnectX-7 lane-split experiment: after MFT/MFT firmware configuration created an additional interface, the author found F2 aliased to F0 and able to pass traffic despite no physical connection; the mesh proposal was abandoned. A separate owner later says a four-node ring worked with custom networking/vLLM patches at a 10–20% performance cost, but the repository was not audited. Add an exact-OEM preflight after any CX7 lane/MFT changes that maps PCI BDF ↔ physical connector ↔ netdev and proves each intended link by disconnect/loopback control and sustained peer traffic, then runs NCCL collectives on the intended topology before workload admission. Preserve BIOS/MFT state, Secure Boot implications and recovery path; never infer physical paths from visible interfaces or adopt the community split commands as a supported fix. **DELTA-FORUM-CX7-PHYSICAL-TOPOLOGY-ALIAS-CHECK-01**.

Fuentes: tasks/backlog/FEATURE-FORUM-GB10-RUNTIME-COMPAT-01.md.
```

## `DELTA-FORUM-CX7-POSTHOTPLUG-01`

- Control: `tools/hardware_batch02_controls.py::_posthotplug`.
- Tests: `tests/test_hardware_batch02_controls.py::test_posthotplug_requires_fresh_diagnostic_and_healthy_endpoint` exercises a synthetic raw PASS and a contradictory/negative FAIL; `test_missing_batch02_capture_is_could_not_run` confirms missing evidence returns UNKNOWN for this ID.
- Live status: no authenticated complete host capture was verified in this isolated worktree; preserve UNKNOWN/CNR and keep the finding open.
- Source body (verbatim):

```text
## Evidencia y alcance

Trabajo separado del ámbito de su ficha madre, conservando la fuente original. Los reportes de foro siguen sin validación local y no se convierten en recomendaciones automáticas.

**DELTA-FORUM-CX7-POSTHOTPLUG-01.** En un clúster GB10 con CX7 firmware 28.45.4028, kernel 6.17.0-1018-nvidia, driver 580.159.03 y mlx5 26.01-1.0.0, el dueño reporta que tras desconectar/reconectar una NIC el all-gather NCCL cae de ~192 a ~25 Gbit/s; `mlxlink` conserva Active/200G y el dueño muestra AER y reenumeración PCIe, mientras reiniciar restaura throughput ([371031](https://forums.developer.nvidia.com/t/371031)). En [363193](https://forums.developer.nvidia.com/t/363193) hay relatos separados de root-port retraining/endpoint ausente y enlace/cable caído; FieldDiag PASS coexistió con NIC no disponible. El adjunto nvidia-bug-report.log.gz no fue leído y las causas siguen abiertas. Añadir un canary post-hotplug que compruebe tráfico NCCL/RDMA extremo a extremo, endpoint PCIe, AER y resultado/frescura de FieldDiag; el estado Active/200G o 27W aislados no cierran salud. Riesgo: reinicio o cambio de marcador altera el estado; registrar versión/cable/firmware y probar en nodo canary con rollback por OEM.

Fuentes: tasks/backlog/FORUM-00-CX7-HOTPLUG-FAN-PROTECTION.md.
```

## `DELTA-FORUM-CX7-RDMA-ASYMMETRY-RETEST-01`

- Control: `tools/hardware_batch02_controls.py::_rdma_asymmetry`.
- Tests: `tests/test_hardware_batch02_controls.py::test_rdma_complete_observations_pass_and_directional_regression_fails` exercises a synthetic raw PASS and a contradictory/negative FAIL; `test_missing_batch02_capture_is_could_not_run` confirms missing evidence returns UNKNOWN for this ID.
- Live status: no authenticated complete host capture was verified in this isolated worktree; preserve UNKNOWN/CNR and keep the finding open.
- Source body (verbatim):

```text
## Evidencia y alcance

Trabajo separado del ámbito de su ficha madre, conservando la fuente original. Los reportes de foro siguen sin validación local y no se convierten en recomendaciones automáticas.

**DELTA-FORUM-CX7-RDMA-ASYMMETRY-RETEST-01.** Un hilo atribuyó una caída direccional RDMA Write (Spark→ASUS GX10 ~13.2 Gbit/s frente a ~111.6 Gbit/s inversa) al kernel ASUS 6.17.0-1029 y reportó vuelta a 6.17.0-1026 ([379303](https://forums.developer.nvidia.com/t/379303)). La atribución pierde fuerza en el propio hilo: tras actualizar/reiniciar el mismo ASUS siguió en 1029 y `ib_write_bw` volvió a ~111.7 Gbit/s; un segundo dueño no reprodujo en Founder Edition. El problema reapareció una vez tras reiniciar y luego se restauró con reinicios de ambos GX10, mientras el propietario sospechó una condición de conectar el DAC con nodos encendidos; esa hipótesis no se controló y otro participante reporta diferencia con cable Amphenol frente a FS.com. No fijar kernel 1026 como workaround. En canary de CX7 compare direcciones en frío, tras reboot individual/secuencial y hotplug, guardando comando/perftest, cable/PN, fw CX7, kernel por OEM, interfaz/IP y estado PCIe/firmware. El resultado de ~13G es reporte temporal de operador; no se leyó issue/bundle externo.

Fuentes: tasks/backlog/FORUM-00-CX7-HOTPLUG-FAN-PROTECTION.md.
```

## `DELTA-FORUM-DUALSPARK-POWER-RESET-RECOVERY-01`

- Control: `tools/hardware_batch02_controls.py::_dual_spark`.
- Tests: `tests/test_hardware_batch02_controls.py::test_dualspark_repeated_ab_control_samples_pass_and_mismatched_input_fails` exercises a synthetic raw PASS and a contradictory/negative FAIL; `test_missing_batch02_capture_is_could_not_run` confirms missing evidence returns UNKNOWN for this ID.
- Live status: no authenticated complete host capture was verified in this isolated worktree; preserve UNKNOWN/CNR and keep the finding open.
- Source body (verbatim):

```text
## Evidencia y alcance

Trabajo separado del ámbito de su ficha madre, conservando la fuente original. Los reportes de foro siguen sin validación local y no se convierten en recomendaciones automáticas.

**DELTA-FORUM-DUALSPARK-POWER-RESET-RECOVERY-01.** En el hilo de dos GB10 [361639, post 293](https://forums.developer.nvidia.com/t/361639/293), un usuario de Qwen3.5-122B-FP8 reportó que, después de apagar y desconectar alimentación USB-C, recuperó SCP sobre ConnectX a >700 MB/s, respuesta general del sistema y benchmark llama-benchy (p. ej. tg32 ~32.5 tok/s en esa configuración). No publicó A/B repetido ni aisló el estado del suministro, CX7, clocks, cableado o workload; cuenta como recuperación reportada, no como causa/fix universal. Añadir la secuencia a la investigación existente de baja potencia/rendimiento: guardar muestras y logs fuera del host, comparar clocks/potencia/rendimiento y enlace CX7 antes/después, y ejecutar shutdown limpio según OEM antes de retirar/reconectar alimentación en un nodo canary. No ejecutar ciclo automático ni recomendarlo como intervención general; preservar datos y rollback de cualquier cambio de cable/configuración.
- **`BB-GX10-HIGHCONTEXT-NO-POST-POWERON`** — An ASUS GX10 owner reports a high-context workload freeze near 120K tokens followed by power-on ending after about two seconds without BIOS; overnight power drain and a second Spark adapter did not restore boot. The proposed internal… Fuente: [383964](https://forums.developer.nvidia.com/t/383964/4).
- **`BB-GB10-OEM-SHUTDOWN-AND-IDLE-THERMAL-CONTROLS`** — Across user reports in a mixed Spark/Gigabyte AI Top Atom discussion: one shutdown attributed to thermal behavior reportedly stopped after BIOS update (versions not stated); a separate owner of two Atoms and two Sparks says both OEMs… Fuente: [372608](https://forums.developer.nvidia.com/t/372608/5).
- **`BB-GB10-THERMAL-SILENT-LOCK-RMA-VALIDATION`** — One A.7 Spark reports repeatable hard power loss under GPU load without pstore, vmcore, OOM, Xid or thermal-trip logs; idle GPU reported at 47–48C and last sample at 79C/82W. In a separate two-FE case, 12 silent locks during 262K… Fuente: [373251](https://forums.developer.nvidia.com/t/373251/1).
- **`BB-FE-THERMAL-FIELDDIAG-POWER-CUTOFF-COVERAGE`** — An MSI GX10 owner reports hard power cutoff around GPU burn temperature 80C and attached no-boot thermal FieldDiag code 020000021139; FE Spark owners elsewhere report similar silent cutoff even while generic FieldDiag passes. Another… Fuente: [358034](https://forums.developer.nvidia.com/t/358034/1).

Fuentes: tasks/backlog/FORUM-00-GB10-THERMAL-RESIDENCY-ADMISSION.md.
```

## `DELTA-FORUM-KV-QUANT-METRIC-PROVENANCE-GATE-01`

- Control: `tools/hardware_batch02_controls.py::_kv_quant`.
- Tests: `tests/test_hardware_batch02_controls.py::test_kv_quant_pairs_separate_counters_and_correctness` exercises a synthetic raw PASS and a contradictory/negative FAIL; `test_missing_batch02_capture_is_could_not_run` confirms missing evidence returns UNKNOWN for this ID.
- Live status: no authenticated complete host capture was verified in this isolated worktree; preserve UNKNOWN/CNR and keep the finding open.
- Source body (verbatim):

```text
## Evidencia y alcance

Trabajo separado del ámbito de su ficha madre, conservando la fuente original. Los reportes de foro siguen sin validación local y no se convierten en recomendaciones automáticas.

### DELTA-FORUM-KV-QUANT-METRIC-PROVENANCE-GATE-01

[364736](https://forums.developer.nvidia.com/t/why-turboquant-saves-dgx-twice/364736) includes a material correction: the author retracted a claim of 92.5% q4_0 prefill collapse and higher memory use after identifying that the original memory measurement used process RSS instead of the llama.cpp KV buffer. The corrected owner report gives 216 MiB q4_0 versus 768 MiB f16 KV, with no prefill cliff and about 37% lower decode rate at 110K context. Later TurboQuant/RotorQuant timings, quality and kernel claims vary by fork/config and remain unverified; external repositories and result files were not audited.

Keep RSS, cgroup, host available memory/swap, allocator residency and framework KV bytes as separately labeled counters. Compare the exact K/V mode, backend, model, context and concurrency with output correctness and prefill/decode measurements. A KV capacity win does not establish faster or correct generation; the reported values are not universal thresholds.

Fuentes: tasks/backlog/FEATURE-FORUM-GB10-RUNTIME-COMPAT-01.md.
```

## `DELTA-FORUM-MEMORY-RECOVERY-SOAK-01`

- Control: `tools/hardware_batch02_controls.py::_memory_soak`.
- Tests: `tests/test_hardware_batch02_controls.py::test_memory_recovery_soak_native_series_and_ordered_termination` exercises a synthetic raw PASS and a contradictory/negative FAIL; `test_missing_batch02_capture_is_could_not_run` confirms missing evidence returns UNKNOWN for this ID.
- Live status: no authenticated complete host capture was verified in this isolated worktree; preserve UNKNOWN/CNR and keep the finding open.
- Source body (verbatim):

```text
## Evidencia y alcance

Trabajo separado del ámbito de su ficha madre, conservando la fuente original. Los reportes de foro siguen sin validación local y no se convierten en recomendaciones automáticas.

**DELTA-FORUM-MEMORY-RECOVERY-SOAK-01.** Dos operadores reportan que `llama.cpp` RPC conserva memoria tras la inferencia y que matar el proceso principal no libera la memoria del nodo remoto; detener `llama-rpc-server` o reiniciar la recupera. No aportan series temporales/versiones y otro reporte del hilo trata aparte un error de configuración Marlin ([361862](https://forums.developer.nvidia.com/t/361862)). Añadir soak multihora con memoria UMA/swap/PSI, estado de proceso servidor y recuperación comprobada tras terminar cliente y servidor; evitar matar/reiniciar automáticamente sin capturar evidencia.

Fuentes: tasks/backlog/FEATURE-1358-CGROUP-05-CUELGUES.md.
```

## `DELTA-FORUM-OTA-DRIVER-KERNEL-EFFECTIVE-TUPLE-01`

- Control: `tools/hardware_batch02_controls.py::_ota_tuple`.
- Tests: `tests/test_hardware_batch02_controls.py::test_ota_tuple_requires_supported_readback_and_verified_rollback` exercises a synthetic raw PASS and a contradictory/negative FAIL; `test_missing_batch02_capture_is_could_not_run` confirms missing evidence returns UNKNOWN for this ID.
- Live status: no authenticated complete host capture was verified in this isolated worktree; preserve UNKNOWN/CNR and keep the finding open.
- Source body (verbatim):

```text
## Evidencia y alcance

Trabajo separado del ámbito de su ficha madre, conservando la fuente original. Los reportes de foro siguen sin validación local y no se convierten en recomendaciones automáticas.

**DELTA-FORUM-OTA-DRIVER-KERNEL-EFFECTIVE-TUPLE-01.** Durante el rollout DGX OS 7.4, los usuarios observaron OTA 7.4 con kernel 6.14; después el kernel 6.17.0-1008 llegó por la ruta de paquetes mientras la versión/fecha del OTA, kernel y driver avanzaban desincronizados ([359550](https://forums.developer.nvidia.com/t/359550)). El hilo recoge aviso de que Driver 590.48.01 no estaba listo para GB10 y un propietario reporta después una unidad casi inutilizable con ~5.5 GiB libres de 121 GiB, que recuperó al volver a 580.126.09; otra respuesta aclara que GB10 usa memoria unificada y que `nvidia-smi` devuelve `[N/A]` para memoria. Son relatos de usuarios; no se inspeccionaron logs adjuntos ni se demostró causalidad independiente. NVIDIA dijo que el carveout UEFI baja 4→2 GiB con OTA2 en equipos partner una vez que OEM lo adopta, mientras un post previo confundía el cambio con firmware EC; diferenciar EC/build, release OTA, kernel activo, driver activo y carveout observado. Prevención: admitir únicamente el tuple kernel/driver/CUDA/DGX OS soportado por release notes y la variante OEM; leer metadatos efectivos tras actualización y medir `MemAvailable`/PSI desde Linux, no usar memoria GPU de nvidia-smi. No instalar drivers/kernel manualmente desde `proposed` como default. Validar en OEM canary el rollout parcial, boot/recovery, memory baseline y workloads bajo soak; rollback por canal OEM conocido.

Fuentes: tasks/backlog/FEATURE-FORUM-GB10-RUNTIME-COMPAT-01.md.
```

## `DELTA-FORUM-RECOVERY-APT-UPDATE-01`

- Control: `tools/hardware_batch02_controls.py::_recovery_apt`.
- Tests: `tests/test_hardware_batch02_controls.py::test_recovery_runbook_complete_native_reads_pass_hash_mismatch_fails` exercises a synthetic raw PASS and a contradictory/negative FAIL; `test_missing_batch02_capture_is_could_not_run` confirms missing evidence returns UNKNOWN for this ID.
- Live status: no authenticated complete host capture was verified in this isolated worktree; preserve UNKNOWN/CNR and keep the finding open.
- Source body (verbatim):

```text
## Evidencia y alcance

Trabajo separado del ámbito de su ficha madre, conservando la fuente original. Los reportes de foro siguen sin validación local y no se convierten en recomendaciones automáticas.

**DELTA-FORUM-RECOVERY-APT-UPDATE-01.** Un usuario informa freeze tras actualización APT y luego un bloqueo durante vLLM en Docker con `--restart always`; tras hard resets describe UEFI/USB/SSH poco fiables, flags GRUB/ACPI añadidos por su cuenta y recomendación NVIDIA de recuperación oficial o RMA ([359198](https://forums.developer.nvidia.com/t/359198)). No hay logs suficientes para atribuir causa a APT, Docker o workload. Extender la runbook con captura preservable antes del reset, identificación de último kernel/driver/paquete, vía de consola externa, medio OEM verificado y criterio de recovery/RMA; cualquier rollback de paquetes se ensaya en copia/canary.

Fuentes: tasks/backlog/FEATURE-FORUM-RESCUE-RUNBOOK-01.md.
```
