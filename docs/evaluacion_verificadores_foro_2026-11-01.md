# Evaluación de los verificadores de foro (2026-11-01)

Decisión del dueño (2026-11-01): el conocimiento que viene de los foros sale de este repositorio y vive en la base de
conocimiento del dueño, porque la enmienda del 2026-10-11 dice que el conocimiento vive sólo en el consumidor de
conocimiento. Aquí se quedan las fichas que piden actuar sobre la máquina, reescritas como trabajo de máquina. Los
verificadores sin consumidor se evalúan con la regla de huérfanos del dueño: «se evalúan, no se retiran en automático;
si atienden una necesidad del diseño se cablean».

Este documento registra las dos tablas de ese trabajo: qué pasó con cada ficha de foro y el veredicto de cada módulo.

## Cómo se buscó el consumidor

Para cada módulo se buscó su nombre en `bin/`, `systemd/`, `adopted/` y `enable-privileged.sh`; los `import` y las
menciones `tools.<módulo>` en el resto de `tools/`; el `close_check` de las fichas abiertas y cerradas; y los tests.
Una ficha cerrada no cuenta como consumidor, salvo que su `close_check` sea el único registro de verificación: en ese
caso el módulo se deja. Un módulo que importa un archivo ajeno a este trabajo (por ejemplo un test de otra área) se
deja aunque no tenga necesidad de diseño, con el motivo escrito.

## Veredictos

Ningún módulo cumple la condición de retiro: todos tienen al menos un consumidor vivo. Líneas retiradas de `tools/` y
`tests/`: **0**.

| Módulo | Líneas | Quién lo llama | Necesidad del diseño | Veredicto |
|---|---|---|---|---|
| `entrega_cosecha_foro` | 140 | `tests/test_cobertura_g3_bordes.py` lo ejecuta como `python -m`; su test propio | No: entregaba conocimiento al consumidor de conocimiento, y la entrega ya se hizo | DEJAR: un test ajeno a este trabajo lo ejecuta. Retirarlo exige quitar ese caso; después queda sin consumidor |
| `verifica_cosecha_foro` | 228 | `entrega_cosecha_foro`; su test propio | No: verificaba la cobertura de la cosecha | DEJAR mientras viva `entrega_cosecha_foro`; se retiran juntos |
| `forum_finding` | 226 | `hardware_evidence`, `verify_forum_finding`; tests de cierre de hardware | Diagnosticar: evalúa los preflights de actualización y arranque contra capturas crudas | DEJAR: lo importa `hardware_evidence` |
| `forum_hardware_subjects` | 1494 | `forum_finding`; `tests/test_bb_root_manifest.py` usa `_parse_fuser` | Diagnosticar: predicados de CX7, watchdog, Realtek y lecturas | DEJAR: lo importa un test ajeno y lo alcanzan doce `close_check` abiertos vía `verify_forum_finding` |
| `hardware_batch02_controls` | 1802 | `hardware_evidence`; `tests/test_debt_registration_controls.py` | Verificar el cierre de tres fichas abiertas | DEJAR: `close_check` de `DELTA-FORUM-KV-QUANT-METRIC-PROVENANCE-GATE-01`, `DELTA-FORUM-OTA-DRIVER-KERNEL-EFFECTIVE-TUPLE-01` y `DELTA-FORUM-RECOVERY-APT-UPDATE-01` |
| `hardware_batch03_controls` | 1300 | `hardware_evidence`; `tests/test_debt_registration_controls.py` | Verificar el cierre de una ficha abierta | DEJAR: `close_check` de `DELTA-ROOT-DISPLAY-CARVEOUT-OEM-FIX-GATE-01` |
| `runtime_batch01_controls` | 1345 | `runtime_batch02/03/04_controls`; `tests/test_runtime_capture_io.py` | Verificar capturas de runtime | DEJAR: lo importan módulos vivos y un test ajeno |
| `runtime_batch02_controls` | 582 | `runtime_batch01/03/04_controls` | Igual | DEJAR: lo importan módulos vivos |
| `runtime_batch03_controls` | 1398 | `tests/test_debt_registration_controls.py`, `tests/test_runtime_capture_io.py` | Verificar el cierre de una ficha abierta | DEJAR: `close_check` de `DELTA-FORUM-QWEN-MTP-PARSER-CANCEL-STATE-CHECK-01` |
| `runtime_batch04_controls` | 972 | `tests/test_runtime_capture_io.py` | Verificar capturas de runtime | DEJAR: lo importa un test ajeno |
| `verify_apt_critical_removals` | 225 | `adopted/root-scripts/apt-guardia-instalar.sh` y `bb-apt-guardia` pendiente de despliegue; `close_check` abierto | Proteger: veta una transacción APT que retira paquetes críticos | DEJAR: ya está cableado en `adopted/` |
| `verify_apt_sources_closure` | 1112 | `hardware_evidence` | Verificar fuentes APT | DEJAR: lo importa `hardware_evidence` |
| `verify_cgroup_plan` | 935 | `close_check` de `FEATURE-1358-CGROUP-05-CUELGUES` (abierta) | Verificar el plan de contención | DEJAR |
| `verify_cgroup_repro` | 134 | `verify_cgroup_plan`; `close_check` de `FEATURE-1358-CGROUP-01-REPRO` (abierta) | Verificar la reproducción | DEJAR |
| `verify_clases_memoria` | 111 | sólo el `close_check` de `FEATURE-DMEM-CLASES-DE-MEMORIA-POR-CGROUP-01` (cerrada) | Registro de verificación | DEJAR: ese `close_check` es el único registro de verificación |
| `verify_clock_cap_tradeoff` | 171 | `hardware_evidence`; `close_check` de una ficha cerrada | Verificar el A/B de reloj | DEJAR: lo importa `hardware_evidence` |
| `verify_cpu_pin_ab` | 295 | `close_check` de `FEATURE-FORUM-CPU-PIN-ECORES-AB-01` (abierta) | Verificar un A/B de una vez | DEJAR |
| `verify_forum_finding` | 36 | `close_check` de doce fichas abiertas y tres cerradas | Verificar capturas de hardware | DEJAR |
| `verify_forum_pstore` | 144 | `forum_finding` | Verificar capturas de pstore de una ficha | DEJAR: lo importa `forum_finding` |
| `verify_gpu_clock_cap_ab` | 438 | `hardware_evidence`, `verify_clock_cap_tradeoff`; `close_check` abiertos | Verificar el A/B de tope de reloj | DEJAR |
| `verify_memory_saver` | 483 | `hardware_evidence`; `close_check` de `FEATURE-MEMORYSAVER-02` y `-04` (abiertas) | Verificar el ahorro de memoria | DEJAR |
| `verify_netconsole` | 537 | `close_check` de `FEATURE-FORUM-NETCONSOLE-01` (abierta) | Verificar la captura fuera del host | DEJAR |
| `verify_rcu_panic_pstore` | 161 | `close_check` de `FEATURE-FORUM-RCU-PANIC-PSTORE-01` (abierta) | Verificar el canario de panic | DEJAR |
| `verify_telemetry_dispositions` | 98 | sólo `close_check` de dos fichas cerradas | Registro de verificación | DEJAR: esos `close_check` son el único registro de verificación |
| `verify_usb_hid_postupdate` | 265 | `hardware_evidence`; `close_check` de `FEATURE-USB-HID-POSTUPDATE-CHECK` (abierta) | Diagnosticar HID tras actualizar | DEJAR |
| `verify_wifi_isolation` | 518 | `hardware_evidence`, `verify_usb_hid_postupdate`; `close_check` abierto | Verificar el aislamiento Wi-Fi | DEJAR |

Fuera de `tools/`, los recolectores `tasks/evidence/SWARM-LUNA-FORUM-2026-10-02/bb_forum_fetch.py` y
`bb_forum_inventory.py` se dejan: `tests/test_bb_forum_collectors.py` los carga y `tests/test_debt_registration_controls.py`
lo usa como `close_check` de dos fichas cerradas, que es su único registro de verificación.

### Candidatos a CABLEAR, fuera de este trabajo

Ningún módulo de la tabla se cablea: los que atienden una necesidad recurrente (proteger antes de reiniciar, diagnosticar
tras un corte) son verificadores de cierre, y lo que corre en la máquina es otro módulo. Esos sí atienden una necesidad
del diseño y no los llama nada que corra solo; se anotan para quien posea esas rutas:

- `tools/update_boot_coherence.py` y `tools/update_drm_coherence.py`: capturan el estado de kernel, initrd y DRM antes de
  reiniciar tras una actualización. Ningún archivo de `bin/`, `systemd/` ni `adopted/` los llama. El sitio natural es la
  guarda de APT ya desplegada.
- Las firmas FPAC, PSCI y SBSA de pstore tras un reinicio no limpio, que pide `FORUM-02-PSTORE-KERNEL-REGRESSION`,
  pertenecen al veredicto de reinicio. Lo que hay en `verify_forum_pstore` sólo valida una captura dada.

## Fichas de foro

Destino «conocimiento» significa que el texto de lo que dicen los hilos se copió a la base de conocimiento del dueño y
salió de la ficha. La ficha conserva su frontmatter y su `close_check` sin cambios, la lista de URL públicas de los
hilos y el registro de verificación de la máquina. Las fichas abiertas llevan además una sección `Trabajo en la ATOM`.
Ninguna ficha se borró: las cerradas son el registro de su verificación y de la decisión que las cerró, y las abiertas
tienen tests que dependen de que sigan en `tasks/backlog/`.

| Ficha | Estado | Tema | Destino |
|---|---|---|---|
| `DELTA-FORUM-CLOCK-CAP-TRADEOFF-AND-THERMAL-ZONE-GAP-01` | open | acción sobre la máquina | se queda abierta, reescrita como trabajo de máquina; el texto de foro, a la base de conocimiento |
| `DELTA-FORUM-KV-QUANT-METRIC-PROVENANCE-GATE-01` | open | acción sobre la máquina | se queda abierta, reescrita como trabajo de máquina; el texto de foro, a la base de conocimiento |
| `DELTA-FORUM-OTA-DRIVER-KERNEL-EFFECTIVE-TUPLE-01` | open | acción sobre la máquina | se queda abierta, reescrita como trabajo de máquina; el texto de foro, a la base de conocimiento |
| `DELTA-FORUM-QWEN-MTP-PARSER-CANCEL-STATE-CHECK-01` | open | acción sobre la máquina | se queda abierta, reescrita como trabajo de máquina; el texto de foro, a la base de conocimiento |
| `DELTA-FORUM-RECOVERY-APT-UPDATE-01` | open | acción sobre la máquina | se queda abierta, reescrita como trabajo de máquina; el texto de foro, a la base de conocimiento |
| `FEATURE-FORUM-CPU-PIN-ECORES-AB-01` | open | acción sobre la máquina | se queda abierta, reescrita como trabajo de máquina; el texto de foro, a la base de conocimiento |
| `FEATURE-FORUM-DESKTOP-SESSION-POSTUPDATE-01` | open | acción sobre la máquina | se queda abierta, reescrita como trabajo de máquina; el texto de foro, a la base de conocimiento |
| `FEATURE-FORUM-GB10-RUNTIME-COMPAT-01` | open | acción sobre la máquina | se queda abierta, reescrita como trabajo de máquina; el texto de foro, a la base de conocimiento |
| `FEATURE-FORUM-GPU-CLOCK-CAP-AB-01` | open | acción sobre la máquina | se queda abierta, reescrita como trabajo de máquina; el texto de foro, a la base de conocimiento |
| `FEATURE-FORUM-GPU-GSP-BOOT-HEALTH-01` | open | acción sobre la máquina | se queda abierta, reescrita como trabajo de máquina; el texto de foro, a la base de conocimiento |
| `FEATURE-FORUM-NETCONSOLE-01` | open | acción sobre la máquina | se queda abierta, reescrita como trabajo de máquina; el texto de foro, a la base de conocimiento |
| `FEATURE-FORUM-NVME-READONLY-01` | open | acción sobre la máquina | se queda abierta, reescrita como trabajo de máquina; el texto de foro, a la base de conocimiento |
| `FEATURE-FORUM-PROVIDER-FALLBACK-REGRESSION-01` | open | acción sobre la máquina | se queda abierta, reescrita como trabajo de máquina; el texto de foro, a la base de conocimiento |
| `FEATURE-FORUM-RCU-PANIC-PSTORE-01` | open | acción sobre la máquina | se queda abierta, reescrita como trabajo de máquina; el texto de foro, a la base de conocimiento |
| `FEATURE-FORUM-RESCUE-RUNBOOK-01` | open | acción sobre la máquina | se queda abierta, reescrita como trabajo de máquina; el texto de foro, a la base de conocimiento |
| `FEATURE-FORUM-SBSA-WATCHDOG-STATE-01` | open | acción sobre la máquina | se queda abierta, reescrita como trabajo de máquina; el texto de foro, a la base de conocimiento |
| `FEATURE-FORUM-WIFI-ISOLATION-01` | open | acción sobre la máquina | se queda abierta, reescrita como trabajo de máquina; el texto de foro, a la base de conocimiento |
| `FORUM-00-CX7-HOTPLUG-FAN-PROTECTION` | open | acción sobre la máquina | se queda abierta, reescrita como trabajo de máquina; el texto de foro, a la base de conocimiento |
| `FORUM-00-DGX-OTA-DRM-COMPAT-PREFLIGHT` | open | acción sobre la máquina | se queda abierta, reescrita como trabajo de máquina; el texto de foro, a la base de conocimiento |
| `FORUM-00-DOCKER-OOM-RESTART-LOOP` | open | acción sobre la máquina | se queda abierta, reescrita como trabajo de máquina; el texto de foro, a la base de conocimiento |
| `FORUM-00-GB10-THERMAL-RESIDENCY-ADMISSION` | open | acción sobre la máquina | se queda abierta, reescrita como trabajo de máquina; el texto de foro, a la base de conocimiento |
| `FORUM-00-KERNEL-INITRD-UPDATE-GATE` | open | acción sobre la máquina | se queda abierta, reescrita como trabajo de máquina; el texto de foro, a la base de conocimiento |
| `FORUM-02-PSTORE-KERNEL-REGRESSION` | open | acción sobre la máquina | se queda abierta, reescrita como trabajo de máquina; el texto de foro, a la base de conocimiento |
| `FORUM-REALTEK-DRIVER-BINDING-01` | open | acción sobre la máquina | se queda abierta, reescrita como trabajo de máquina; el texto de foro, a la base de conocimiento |
| `BUG-FORUM-STATUS-BUS-UNKNOWN-01` | done (`fixed`) | acción (herramienta propia de bb) | se queda sin cambios (no trae texto de foro) |
| `DEBT-CLOSE-CHECK-VERIFY-FORUM-FINDING-01` | done (`duplicate`) | acción (herramienta propia de bb) | se queda sin cambios (no trae texto de foro) |
| `DEBT-RESEARCH-COLLECTOR-BB-FORUM-FETCH-01` | done | acción (herramienta propia de bb) | se queda sin cambios (no trae texto de foro) |
| `DEBT-RESEARCH-COLLECTOR-BB-FORUM-INVENTORY-01` | done | acción (herramienta propia de bb) | se queda sin cambios (no trae texto de foro) |
| `DELTA-FORUM-3NODE-NCCL-IMAGE-AND-FIRST-REQUEST-01` | done (`void_wontfix`) | conocimiento (cerrada: sin sujeto en esta máquina) | se queda cerrada sin el texto de foro; el texto, a la base de conocimiento |
| `DELTA-FORUM-8NODE-NCCL-INTERFACE-MTU-01` | done (`void_wontfix`) | conocimiento (cerrada: sin sujeto en esta máquina) | se queda cerrada sin el texto de foro; el texto, a la base de conocimiento |
| `DELTA-FORUM-APT-ARM64-SOURCE-VALIDATION-01` | done (`void_wontfix`) | conocimiento (cerrada: sin sujeto en esta máquina) | se queda cerrada sin el texto de foro; el texto, a la base de conocimiento |
| `DELTA-FORUM-CUTLASS-SM121-ISA-GATE-01` | done (`relocated_prior_verification`) | acción sobre la máquina (cerrada) | se queda cerrada sin el texto de foro; el texto, a la base de conocimiento |
| `DELTA-FORUM-CX7-FW-UPDATE-GUARD-01` | done (`void_wontfix`) | conocimiento (cerrada: sin sujeto en esta máquina) | se queda cerrada sin el texto de foro; el texto, a la base de conocimiento |
| `DELTA-FORUM-CX7-PHYSICAL-TOPOLOGY-ALIAS-CHECK-01` | done (`void_wontfix`) | conocimiento (cerrada: sin sujeto en esta máquina) | se queda cerrada sin el texto de foro; el texto, a la base de conocimiento |
| `DELTA-FORUM-CX7-POSTHOTPLUG-01` | done (`void_wontfix`) | conocimiento (cerrada: sin sujeto en esta máquina) | se queda cerrada sin el texto de foro; el texto, a la base de conocimiento |
| `DELTA-FORUM-CX7-RDMA-ASYMMETRY-RETEST-01` | done (`void_wontfix`) | conocimiento (cerrada: sin sujeto en esta máquina) | se queda cerrada sin el texto de foro; el texto, a la base de conocimiento |
| `DELTA-FORUM-DCP-MTP-DRAFT-CORRECTNESS-AND-PRETRIM-OOM-01` | done (`void_wontfix`) | conocimiento (cerrada: sin sujeto en esta máquina) | se queda cerrada sin el texto de foro; el texto, a la base de conocimiento |
| `DELTA-FORUM-DCP4-DECODE-STARVATION-FAIR-SCHEDULER-01` | done (`void_wontfix`) | conocimiento (cerrada: sin sujeto en esta máquina) | se queda cerrada sin el texto de foro; el texto, a la base de conocimiento |
| `DELTA-FORUM-DFLASH-XGRAMMAR-STRUCTURED-OUTPUT-REGRESSION-01` | done (`void_wontfix`) | conocimiento (cerrada: sin sujeto en esta máquina) | se queda cerrada sin el texto de foro; el texto, a la base de conocimiento |
| `DELTA-FORUM-DSV41-NFS-STOP-TAG-PIN-01` | done (`void_wontfix`) | conocimiento (cerrada: sin sujeto en esta máquina) | se queda cerrada sin el texto de foro; el texto, a la base de conocimiento |
| `DELTA-FORUM-DUALSPARK-NCCL-GID-TWIN-AND-COLD-RECOVERY-01` | done (`void_wontfix`) | conocimiento (cerrada: sin sujeto en esta máquina) | se queda cerrada sin el texto de foro; el texto, a la base de conocimiento |
| `DELTA-FORUM-DUALSPARK-POWER-RESET-RECOVERY-01` | done (`void_wontfix`) | conocimiento (cerrada: sin sujeto en esta máquina) | se queda cerrada sin el texto de foro; el texto, a la base de conocimiento |
| `DELTA-FORUM-GLM52-MULTITURN-CORRECTNESS-AND-RECIPE-SENSITIVITY-01` | done (`void_wontfix`) | conocimiento (cerrada: sin sujeto en esta máquina) | se queda cerrada sin el texto de foro; el texto, a la base de conocimiento |
| `DELTA-FORUM-GPTOSS-MULTINODE-RAY-CHANNEL-TIMEOUT-01` | done (`void_wontfix`) | conocimiento (cerrada: sin sujeto en esta máquina) | se queda cerrada sin el texto de foro; el texto, a la base de conocimiento |
| `DELTA-FORUM-LLAMACPP-RPC-UMA-AND-ORDERLY-TEARDOWN-01` | done (`void_wontfix`) | conocimiento (cerrada: sin sujeto en esta máquina) | se queda cerrada sin el texto de foro; el texto, a la base de conocimiento |
| `DELTA-FORUM-M2-COMPACTION-STATE-VALIDATION-01` | done (`void_wontfix`) | conocimiento (cerrada: sin sujeto en esta máquina) | se queda cerrada sin el texto de foro; el texto, a la base de conocimiento |
| `DELTA-FORUM-MEMORY-RECOVERY-SOAK-01` | done (`void_wontfix`) | conocimiento (cerrada: sin sujeto en esta máquina) | se queda cerrada sin el texto de foro; el texto, a la base de conocimiento |
| `DELTA-FORUM-MINIMAX-TOOLCALL-FUNCTIONAL-CANARY-01` | done (`void_wontfix`) | conocimiento (cerrada: sin sujeto en esta máquina) | se queda cerrada sin el texto de foro; el texto, a la base de conocimiento |
| `DELTA-FORUM-MTP-ACCEPTANCE-AND-SEMANTIC-CONTROL-01` | done (`void_wontfix`) | conocimiento (cerrada: sin sujeto en esta máquina) | se queda cerrada sin el texto de foro; el texto, a la base de conocimiento |
| `DELTA-FORUM-MUSE-GLIMMER-DFLASH-MAX-SEQS-GATE-01` | done (`void_wontfix`) | conocimiento (cerrada: sin sujeto en esta máquina) | se queda cerrada sin el texto de foro; el texto, a la base de conocimiento |
| `DELTA-FORUM-NCCL-TP-ORCHESTRATION-CORRECTION-01` | done (`void_wontfix`) | conocimiento (cerrada: sin sujeto en esta máquina) | se queda cerrada sin el texto de foro; el texto, a la base de conocimiento |
| `DELTA-FORUM-NEMOTRON-SM121-PREBUILT-KERNEL-01` | done (`void_wontfix`) | conocimiento (cerrada: sin sujeto en esta máquina) | se queda cerrada sin el texto de foro; el texto, a la base de conocimiento |
| `DELTA-FORUM-OPENCLAW-VLLM-REQUEST-CONTRACT-01` | done (`void_wontfix`) | conocimiento (cerrada: sin sujeto en esta máquina) | se queda cerrada sin el texto de foro; el texto, a la base de conocimiento |
| `DELTA-FORUM-QWEN-COLD-COMPILE-OOM-01` | done (`void_wontfix`) | conocimiento (cerrada: sin sujeto en esta máquina) | se queda cerrada sin el texto de foro; el texto, a la base de conocimiento |
| `DELTA-FORUM-QWEN-LONG-AGENT-STOP-01` | done (`void_wontfix`) | conocimiento (cerrada: sin sujeto en esta máquina) | se queda cerrada sin el texto de foro; el texto, a la base de conocimiento |
| `DELTA-FORUM-QWEN-SERVICE-OOMD-CACHE-FAIL-01` | done (`void_wontfix`) | conocimiento (cerrada: sin sujeto en esta máquina) | se queda cerrada sin el texto de foro; el texto, a la base de conocimiento |
| `DELTA-FORUM-QWEN-TOOLCALL-WEDGE-01` | done (`void_wontfix`) | conocimiento (cerrada: sin sujeto en esta máquina) | se queda cerrada sin el texto de foro; el texto, a la base de conocimiento |
| `DELTA-FORUM-QWEN35-NVFP4-CUTLASS-FIRST-REQUEST-GATE-01` | done (`void_wontfix`) | conocimiento (cerrada: sin sujeto en esta máquina) | se queda cerrada sin el texto de foro; el texto, a la base de conocimiento |
| `DELTA-FORUM-QWEN38-LONG-RUN-JSON-CORRECTNESS-CANARY-01` | done (`void_wontfix`) | conocimiento (cerrada: sin sujeto en esta máquina) | se queda cerrada sin el texto de foro; el texto, a la base de conocimiento |
| `DELTA-FORUM-RAY-TORCH-GRAPH-HANG-01` | done (`void_wontfix`) | conocimiento (cerrada: sin sujeto en esta máquina) | se queda cerrada sin el texto de foro; el texto, a la base de conocimiento |
| `DELTA-FORUM-RUNTIME-VERSION-CAPTURE-01` | done (`relocated_prior_verification`) | acción sobre la máquina (cerrada) | se queda cerrada sin el texto de foro; el texto, a la base de conocimiento |
| `DELTA-FORUM-THERMAL-AUXILIARY-COOLING-AND-CLOCK-CAP-01` | done (`void_wontfix`) | conocimiento (cerrada: sin sujeto en esta máquina) | se queda cerrada sin el texto de foro; el texto, a la base de conocimiento |
| `DELTA-FORUM-THERMAL-TELEMETRY-COVERAGE-01` | done (`void_wontfix`) | conocimiento (cerrada: sin sujeto en esta máquina) | se queda cerrada sin el texto de foro; el texto, a la base de conocimiento |
| `DELTA-FORUM-USB-RAID-LINK-ADMISSION-01` | done (`void_wontfix`) | conocimiento (cerrada: sin sujeto en esta máquina) | se queda cerrada sin el texto de foro; el texto, a la base de conocimiento |
| `DELTA-FORUM-VLLM-GB10-ARCH-AND-BUILD-MATRIX-01` | done (`void_wontfix`) | conocimiento (cerrada: sin sujeto en esta máquina) | se queda cerrada sin el texto de foro; el texto, a la base de conocimiento |
| `DELTA-FORUM-VLLM-RAY-GB10-RESOURCE-FIX-01` | done (`void_wontfix`) | conocimiento (cerrada: sin sujeto en esta máquina) | se queda cerrada sin el texto de foro; el texto, a la base de conocimiento |
| `FORUM-00-REALTEK-EEE-DIRECT-LINK` | done (`void_wontfix`) | conocimiento (cerrada: sin sujeto en esta máquina) | se queda cerrada sin el texto de foro; el texto, a la base de conocimiento |
| `FORUM-02-GX10-READ-INTEGRITY` | done (`void_wontfix`) | conocimiento (cerrada: sin sujeto en esta máquina) | se queda cerrada sin el texto de foro; el texto, a la base de conocimiento |
| `FORUM-02-USB-UVC-EP0` | done (`void_wontfix`) | conocimiento (cerrada: sin sujeto en esta máquina) | se queda cerrada sin el texto de foro; el texto, a la base de conocimiento |

Total: 69 fichas (24 abiertas, 45 cerradas); 65 con texto de foro reubicado.

## Lo demás que salió

- `docs/foro-borradores/` (cuatro borradores ya publicados en el foro y en el issue 1358): se retiraron; su texto vive en la base de conocimiento.
- Evidencia de texto de foro: 3872 archivos de `tasks/evidence/SWARM-LUNA-FORUM-2026-10-02/` y de las tres `FEATURE-COSECHA-FORO-*` (hilos descargados, triaje, lotes, resultados por hilo, inventarios y `cosecha.txt`), copiados con sha256 verificado antes de retirarlos. Se quedan los 23 archivos que son registro de verificación o código: los `pass`/`fail`/`e2e`, los `cobertura-*.txt` y `evaluacion.txt` que leen los `close_check`, las salidas del verificador de cobertura, las mediciones de la máquina (`hallazgo-reloj-atascado-20261012.txt`, `discriminacion-termico.txt`, `repasada-guardia-20261012.json`), los dos prompts, el manifiesto de la entrega y los dos recolectores.
