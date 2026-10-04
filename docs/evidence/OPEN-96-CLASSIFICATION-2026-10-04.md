# Clasificación de las 96 fichas — 2026-10-04

Fuente: los 98 IDs originales; 2 done y 96 abiertas. Los diez lotes generados devolvieron 96 de 96; missing=0, unknown=0, duplicated=0, malformed=0. La clasificación conserva los criterios originales.

| Impedimento principal | Fichas |
| --- | ---: |
| Workload o ensayo de laboratorio | 50 |
| Hardware o equipos pares | 22 |
| Acceso privilegiado | 10 |
| Evidencia histórica ausente | 3 |
| Evidencia o compatibilidad OEM | 8 |
| Decisión del operador | 3 |

Cierres completos acreditados como accionables hoy: 0. Preparación coordinable: 67; esa preparación permite avanzar protocolos o código y conserva las pruebas reales pendientes. Impedimentos de inspección: 14; el informe conserva esas limitaciones y no declara el backlog limpio.

Cada ficha contiene su impedimento, evidencia faltante, siguiente acción, responsable y referencias de clasificación. El JSON completo está en `tasks/evidence/OPEN-96-CLASSIFICATION-2026-10-04/classification-final.json`.

## Validación y publicación

Se corrigió el inventario de SPEC para incluir 22 módulos nuevos; `python3 -m tools.inventario --check` devolvió `[inventario] HALLAZGOS: 0`.

El gate nativo configurado `python3 .simplecode/run.py simplecode.verification.coverage_target -q` terminó rc1: `104 failed, 1983 passed in 202.24s (0:03:22)`, 0 omitidas. Los 136 hashes de código del inicio permanecen iguales. El piso de cobertura no llegó a emitir veredicto porque falló la lane de tests. Recibo: `publication-coverage-native-terminal.json`.

El gate `finding_backlog --gate` terminó rc1 y registra 96 fichas abiertas fuera de la línea base. La configuración pre-push exige este gate y cobertura. La clasificación por impedimento no cambia esos gates ni habilita publicación. Recibo: `publication-ship-freeze-current.json`.

Además siguen pendientes la decisión sobre el derivado redactado de Simplecode y la captura sudo. No hay commit ni push nuevos.

## Contrato de publicación propuesto para decisión

Para publicar desarrollo con investigaciones abiertas hace falta decidir un contrato explícito: validación de software con el mismo target y watermark de cobertura; controles de cierre real ejecutables con sus comandos originales; y admisión temporal de los IDs de investigación clasificados, con responsable y caducidad. Las fichas mantienen status open y sus pruebas físicas pendientes. Los fallos ordinarios de código siguen bloqueando. Esta propuesta exige revisar los cambios de configuración y demostrar que los controles reales continúan fallando ante evidencia ausente; no se aplicó ningún cambio al contrato.

La alternativa es conservar la congelación total actual: el push espera hasta que las 96 investigaciones estén cerradas.

## Índice por ficha

| Ficha | Impedimento | Responsable |
| --- | --- | --- |
| [DEBT-CLOSE-CHECK-VERIFY-CGROUP-PLAN-01](/home/lcasarin/projects/blackbox/tasks/backlog/DEBT-CLOSE-CHECK-VERIFY-CGROUP-PLAN-01.md) | Workload o ensayo de laboratorio | Coordinación BB; para recuperación de históricos, custodio del artifact store si corresponde. |
| [DEBT-CLOSE-CHECK-VERIFY-FORUM-FINDING-01](/home/lcasarin/projects/blackbox/tasks/backlog/DEBT-CLOSE-CHECK-VERIFY-FORUM-FINDING-01.md) | Evidencia histórica ausente | BB |
| [DEBT-CLOSE-CHECK-VERIFY-GPU-CLOCK-CAP-AB-01](/home/lcasarin/projects/blackbox/tasks/backlog/DEBT-CLOSE-CHECK-VERIFY-GPU-CLOCK-CAP-AB-01.md) | Workload o ensayo de laboratorio | coordinación BB prepara el protocolo; operador Luis ejecuta el ensayo en GPU/lab |
| [DEBT-CLOSE-CHECK-VERIFY-MEMORY-SAVER-01](/home/lcasarin/projects/blackbox/tasks/backlog/DEBT-CLOSE-CHECK-VERIFY-MEMORY-SAVER-01.md) | Acceso privilegiado | Coordinación BB prepara/implementa; cuando la acción requiere root/lab/hardware, operador Luis aporta y ejecuta el sujeto indicado. |
| [DEBT-CLOSE-CHECK-VERIFY-NETCONSOLE-01](/home/lcasarin/projects/blackbox/tasks/backlog/DEBT-CLOSE-CHECK-VERIFY-NETCONSOLE-01.md) | Workload o ensayo de laboratorio | BB |
| [DEBT-CLOSE-CHECK-VERIFY-RCU-PANIC-PSTORE-01](/home/lcasarin/projects/blackbox/tasks/backlog/DEBT-CLOSE-CHECK-VERIFY-RCU-PANIC-PSTORE-01.md) | Acceso privilegiado | coordinación BB prepara el canary; operador Luis gestiona acceso root/lab y ejecuta el ciclo |
| [DEBT-CLOSE-CHECK-VERIFY-USB-HID-POSTUPDATE-01](/home/lcasarin/projects/blackbox/tasks/backlog/DEBT-CLOSE-CHECK-VERIFY-USB-HID-POSTUPDATE-01.md) | Hardware o equipos pares | Coordinación BB prepara/implementa; cuando la acción requiere root/lab/hardware, operador Luis aporta y ejecuta el sujeto indicado. |
| [DEBT-CLOSE-CHECK-VERIFY-WIFI-ISOLATION-01](/home/lcasarin/projects/blackbox/tasks/backlog/DEBT-CLOSE-CHECK-VERIFY-WIFI-ISOLATION-01.md) | Hardware o equipos pares | BB |
| [DEBT-HOST-DEPLOYED-DRIFT-01](/home/lcasarin/projects/blackbox/tasks/backlog/DEBT-HOST-DEPLOYED-DRIFT-01.md) | Acceso privilegiado | operador Luis (host); coordinación BB (comparador/código) |
| [DEBT-TELEMETRY-HISTORICAL-UNDISPOSED-20260908-01](/home/lcasarin/projects/blackbox/tasks/backlog/DEBT-TELEMETRY-HISTORICAL-UNDISPOSED-20260908-01.md) | Evidencia histórica ausente | Coordinación BB; para recuperación de históricos, custodio del artifact store si corresponde. |
| [DELTA-FORUM-3NODE-NCCL-IMAGE-AND-FIRST-REQUEST-01](/home/lcasarin/projects/blackbox/tasks/backlog/DELTA-FORUM-3NODE-NCCL-IMAGE-AND-FIRST-REQUEST-01.md) | Workload o ensayo de laboratorio | Coordinación BB prepara/implementa; cuando la acción requiere root/lab/hardware, operador Luis aporta y ejecuta el sujeto indicado. |
| [DELTA-FORUM-8NODE-NCCL-INTERFACE-MTU-01](/home/lcasarin/projects/blackbox/tasks/backlog/DELTA-FORUM-8NODE-NCCL-INTERFACE-MTU-01.md) | Hardware o equipos pares | BB; operador Luis para hardware/peer |
| [DELTA-FORUM-APT-ARM64-SOURCE-VALIDATION-01](/home/lcasarin/projects/blackbox/tasks/backlog/DELTA-FORUM-APT-ARM64-SOURCE-VALIDATION-01.md) | Decisión del operador | Luis para decisión; coordinación BB para implementación |
| [DELTA-FORUM-CLOCK-CAP-TRADEOFF-AND-THERMAL-ZONE-GAP-01](/home/lcasarin/projects/blackbox/tasks/backlog/DELTA-FORUM-CLOCK-CAP-TRADEOFF-AND-THERMAL-ZONE-GAP-01.md) | Workload o ensayo de laboratorio | Coordinación BB prepara/implementa; cuando la acción requiere root/lab/hardware, operador Luis aporta y ejecuta el sujeto indicado. |
| [DELTA-FORUM-CROSS-TURN-SLEEPER-INJECTION-REGRESSION-01](/home/lcasarin/projects/blackbox/tasks/backlog/DELTA-FORUM-CROSS-TURN-SLEEPER-INJECTION-REGRESSION-01.md) | Workload o ensayo de laboratorio | BB; operador Luis para workload/lab |
| [DELTA-FORUM-CUTLASS-SM121-ISA-GATE-01](/home/lcasarin/projects/blackbox/tasks/backlog/DELTA-FORUM-CUTLASS-SM121-ISA-GATE-01.md) | Workload o ensayo de laboratorio | coordinación BB prepara; operador Luis ejecuta root/lab |
| [DELTA-FORUM-CX7-FW-UPDATE-GUARD-01](/home/lcasarin/projects/blackbox/tasks/backlog/DELTA-FORUM-CX7-FW-UPDATE-GUARD-01.md) | Hardware o equipos pares | Coordinación BB prepara/implementa; cuando la acción requiere root/lab/hardware, operador Luis aporta y ejecuta el sujeto indicado. |
| [DELTA-FORUM-CX7-PHYSICAL-TOPOLOGY-ALIAS-CHECK-01](/home/lcasarin/projects/blackbox/tasks/backlog/DELTA-FORUM-CX7-PHYSICAL-TOPOLOGY-ALIAS-CHECK-01.md) | Hardware o equipos pares | BB; operador Luis para hardware/peer |
| [DELTA-FORUM-CX7-POSTHOTPLUG-01](/home/lcasarin/projects/blackbox/tasks/backlog/DELTA-FORUM-CX7-POSTHOTPLUG-01.md) | Hardware o equipos pares | coordinación BB prepara; operador Luis ejecuta root/lab |
| [DELTA-FORUM-CX7-RDMA-ASYMMETRY-RETEST-01](/home/lcasarin/projects/blackbox/tasks/backlog/DELTA-FORUM-CX7-RDMA-ASYMMETRY-RETEST-01.md) | Hardware o equipos pares | Coordinación BB prepara/implementa; cuando la acción requiere root/lab/hardware, operador Luis aporta y ejecuta el sujeto indicado. |
| [DELTA-FORUM-DCP-MTP-DRAFT-CORRECTNESS-AND-PRETRIM-OOM-01](/home/lcasarin/projects/blackbox/tasks/backlog/DELTA-FORUM-DCP-MTP-DRAFT-CORRECTNESS-AND-PRETRIM-OOM-01.md) | Workload o ensayo de laboratorio | Coordinación BB prepara/implementa; cuando la acción requiere root/lab/hardware, operador Luis aporta y ejecuta el sujeto indicado. |
| [DELTA-FORUM-DCP4-DECODE-STARVATION-FAIR-SCHEDULER-01](/home/lcasarin/projects/blackbox/tasks/backlog/DELTA-FORUM-DCP4-DECODE-STARVATION-FAIR-SCHEDULER-01.md) | Workload o ensayo de laboratorio | BB; operador Luis para workload/lab |
| [DELTA-FORUM-DFLASH-XGRAMMAR-STRUCTURED-OUTPUT-REGRESSION-01](/home/lcasarin/projects/blackbox/tasks/backlog/DELTA-FORUM-DFLASH-XGRAMMAR-STRUCTURED-OUTPUT-REGRESSION-01.md) | Workload o ensayo de laboratorio | coordinación BB prepara; operador Luis ejecuta root/lab |
| [DELTA-FORUM-DSV41-NFS-STOP-TAG-PIN-01](/home/lcasarin/projects/blackbox/tasks/backlog/DELTA-FORUM-DSV41-NFS-STOP-TAG-PIN-01.md) | Evidencia o compatibilidad OEM | Coordinación BB solicita al OEM/autor y obtiene el contrato faltante; después implementa la verificación. |
| [DELTA-FORUM-DUALSPARK-NCCL-GID-TWIN-AND-COLD-RECOVERY-01](/home/lcasarin/projects/blackbox/tasks/backlog/DELTA-FORUM-DUALSPARK-NCCL-GID-TWIN-AND-COLD-RECOVERY-01.md) | Hardware o equipos pares | BB; operador Luis para hardware/peer |
| [DELTA-FORUM-DUALSPARK-POWER-RESET-RECOVERY-01](/home/lcasarin/projects/blackbox/tasks/backlog/DELTA-FORUM-DUALSPARK-POWER-RESET-RECOVERY-01.md) | Hardware o equipos pares | coordinación BB prepara; operador Luis ejecuta root/lab |
| [DELTA-FORUM-GLM52-MULTITURN-CORRECTNESS-AND-RECIPE-SENSITIVITY-01](/home/lcasarin/projects/blackbox/tasks/backlog/DELTA-FORUM-GLM52-MULTITURN-CORRECTNESS-AND-RECIPE-SENSITIVITY-01.md) | Workload o ensayo de laboratorio | Coordinación BB prepara/implementa; cuando la acción requiere root/lab/hardware, operador Luis aporta y ejecuta el sujeto indicado. |
| [DELTA-FORUM-GPTOSS-MULTINODE-RAY-CHANNEL-TIMEOUT-01](/home/lcasarin/projects/blackbox/tasks/backlog/DELTA-FORUM-GPTOSS-MULTINODE-RAY-CHANNEL-TIMEOUT-01.md) | Workload o ensayo de laboratorio | BB; operador Luis para workload/lab |
| [DELTA-FORUM-KV-QUANT-METRIC-PROVENANCE-GATE-01](/home/lcasarin/projects/blackbox/tasks/backlog/DELTA-FORUM-KV-QUANT-METRIC-PROVENANCE-GATE-01.md) | Workload o ensayo de laboratorio | coordinación BB prepara; operador Luis ejecuta root/lab |
| [DELTA-FORUM-LLAMACPP-RPC-UMA-AND-ORDERLY-TEARDOWN-01](/home/lcasarin/projects/blackbox/tasks/backlog/DELTA-FORUM-LLAMACPP-RPC-UMA-AND-ORDERLY-TEARDOWN-01.md) | Workload o ensayo de laboratorio | Coordinación BB prepara/implementa; cuando la acción requiere root/lab/hardware, operador Luis aporta y ejecuta el sujeto indicado. |
| [DELTA-FORUM-M2-COMPACTION-STATE-VALIDATION-01](/home/lcasarin/projects/blackbox/tasks/backlog/DELTA-FORUM-M2-COMPACTION-STATE-VALIDATION-01.md) | Workload o ensayo de laboratorio | Coordinación BB prepara/implementa; cuando la acción requiere root/lab/hardware, operador Luis aporta y ejecuta el sujeto indicado. |
| [DELTA-FORUM-MEMORY-RECOVERY-SOAK-01](/home/lcasarin/projects/blackbox/tasks/backlog/DELTA-FORUM-MEMORY-RECOVERY-SOAK-01.md) | Workload o ensayo de laboratorio | BB; operador Luis para workload/lab |
| [DELTA-FORUM-MINIMAX-TOOLCALL-FUNCTIONAL-CANARY-01](/home/lcasarin/projects/blackbox/tasks/backlog/DELTA-FORUM-MINIMAX-TOOLCALL-FUNCTIONAL-CANARY-01.md) | Workload o ensayo de laboratorio | coordinación BB prepara; operador Luis ejecuta root/lab |
| [DELTA-FORUM-MTP-ACCEPTANCE-AND-SEMANTIC-CONTROL-01](/home/lcasarin/projects/blackbox/tasks/backlog/DELTA-FORUM-MTP-ACCEPTANCE-AND-SEMANTIC-CONTROL-01.md) | Workload o ensayo de laboratorio | Coordinación BB prepara/implementa; cuando la acción requiere root/lab/hardware, operador Luis aporta y ejecuta el sujeto indicado. |
| [DELTA-FORUM-MUSE-GLIMMER-DFLASH-MAX-SEQS-GATE-01](/home/lcasarin/projects/blackbox/tasks/backlog/DELTA-FORUM-MUSE-GLIMMER-DFLASH-MAX-SEQS-GATE-01.md) | Workload o ensayo de laboratorio | BB; operador Luis para workload/lab |
| [DELTA-FORUM-NCCL-TP-ORCHESTRATION-CORRECTION-01](/home/lcasarin/projects/blackbox/tasks/backlog/DELTA-FORUM-NCCL-TP-ORCHESTRATION-CORRECTION-01.md) | Workload o ensayo de laboratorio | coordinación BB prepara; operador Luis ejecuta root/lab |
| [DELTA-FORUM-NEMOTRON-SM121-PREBUILT-KERNEL-01](/home/lcasarin/projects/blackbox/tasks/backlog/DELTA-FORUM-NEMOTRON-SM121-PREBUILT-KERNEL-01.md) | Workload o ensayo de laboratorio | Coordinación BB prepara/implementa; cuando la acción requiere root/lab/hardware, operador Luis aporta y ejecuta el sujeto indicado. |
| [DELTA-FORUM-OPENCLAW-VLLM-REQUEST-CONTRACT-01](/home/lcasarin/projects/blackbox/tasks/backlog/DELTA-FORUM-OPENCLAW-VLLM-REQUEST-CONTRACT-01.md) | Workload o ensayo de laboratorio | BB |
| [DELTA-FORUM-OTA-DRIVER-KERNEL-EFFECTIVE-TUPLE-01](/home/lcasarin/projects/blackbox/tasks/backlog/DELTA-FORUM-OTA-DRIVER-KERNEL-EFFECTIVE-TUPLE-01.md) | Evidencia o compatibilidad OEM | coordinación BB gestiona OEM; operador Luis ejecuta canario |
| [DELTA-FORUM-QWEN-COLD-COMPILE-OOM-01](/home/lcasarin/projects/blackbox/tasks/backlog/DELTA-FORUM-QWEN-COLD-COMPILE-OOM-01.md) | Workload o ensayo de laboratorio | Coordinación BB prepara/implementa; cuando la acción requiere root/lab/hardware, operador Luis aporta y ejecuta el sujeto indicado. |
| [DELTA-FORUM-QWEN-LONG-AGENT-STOP-01](/home/lcasarin/projects/blackbox/tasks/backlog/DELTA-FORUM-QWEN-LONG-AGENT-STOP-01.md) | Workload o ensayo de laboratorio | Coordinación BB prepara/implementa; cuando la acción requiere root/lab/hardware, operador Luis aporta y ejecuta el sujeto indicado. |
| [DELTA-FORUM-QWEN-MTP-PARSER-CANCEL-STATE-CHECK-01](/home/lcasarin/projects/blackbox/tasks/backlog/DELTA-FORUM-QWEN-MTP-PARSER-CANCEL-STATE-CHECK-01.md) | Workload o ensayo de laboratorio | BB; operador Luis para workload/lab |
| [DELTA-FORUM-QWEN-SERVICE-OOMD-CACHE-FAIL-01](/home/lcasarin/projects/blackbox/tasks/backlog/DELTA-FORUM-QWEN-SERVICE-OOMD-CACHE-FAIL-01.md) | Workload o ensayo de laboratorio | coordinación BB prepara; operador Luis ejecuta root/lab |
| [DELTA-FORUM-QWEN-TOOLCALL-WEDGE-01](/home/lcasarin/projects/blackbox/tasks/backlog/DELTA-FORUM-QWEN-TOOLCALL-WEDGE-01.md) | Workload o ensayo de laboratorio | Coordinación BB prepara/implementa; cuando la acción requiere root/lab/hardware, operador Luis aporta y ejecuta el sujeto indicado. |
| [DELTA-FORUM-QWEN35-NVFP4-CUTLASS-FIRST-REQUEST-GATE-01](/home/lcasarin/projects/blackbox/tasks/backlog/DELTA-FORUM-QWEN35-NVFP4-CUTLASS-FIRST-REQUEST-GATE-01.md) | Workload o ensayo de laboratorio | BB; operador Luis para workload/lab |
| [DELTA-FORUM-QWEN38-LONG-RUN-JSON-CORRECTNESS-CANARY-01](/home/lcasarin/projects/blackbox/tasks/backlog/DELTA-FORUM-QWEN38-LONG-RUN-JSON-CORRECTNESS-CANARY-01.md) | Workload o ensayo de laboratorio | coordinación BB prepara; operador Luis ejecuta root/lab |
| [DELTA-FORUM-RAY-TORCH-GRAPH-HANG-01](/home/lcasarin/projects/blackbox/tasks/backlog/DELTA-FORUM-RAY-TORCH-GRAPH-HANG-01.md) | Workload o ensayo de laboratorio | Coordinación BB prepara/implementa; cuando la acción requiere root/lab/hardware, operador Luis aporta y ejecuta el sujeto indicado. |
| [DELTA-FORUM-RECOVERY-APT-UPDATE-01](/home/lcasarin/projects/blackbox/tasks/backlog/DELTA-FORUM-RECOVERY-APT-UPDATE-01.md) | Decisión del operador | BB; operador Luis decide recuperación del sujeto |
| [DELTA-FORUM-THERMAL-AUXILIARY-COOLING-AND-CLOCK-CAP-01](/home/lcasarin/projects/blackbox/tasks/backlog/DELTA-FORUM-THERMAL-AUXILIARY-COOLING-AND-CLOCK-CAP-01.md) | Hardware o equipos pares | coordinación BB prepara; operador Luis ejecuta root/lab |
| [DELTA-FORUM-THERMAL-TELEMETRY-COVERAGE-01](/home/lcasarin/projects/blackbox/tasks/backlog/DELTA-FORUM-THERMAL-TELEMETRY-COVERAGE-01.md) | Evidencia o compatibilidad OEM | Coordinación BB; para recuperación de históricos, custodio del artifact store si corresponde. |
| [DELTA-FORUM-USB-RAID-LINK-ADMISSION-01](/home/lcasarin/projects/blackbox/tasks/backlog/DELTA-FORUM-USB-RAID-LINK-ADMISSION-01.md) | Hardware o equipos pares | Coordinación BB prepara/implementa; cuando la acción requiere root/lab/hardware, operador Luis aporta y ejecuta el sujeto indicado. |
| [DELTA-FORUM-VLLM-GB10-ARCH-AND-BUILD-MATRIX-01](/home/lcasarin/projects/blackbox/tasks/backlog/DELTA-FORUM-VLLM-GB10-ARCH-AND-BUILD-MATRIX-01.md) | Evidencia o compatibilidad OEM | BB; coordinación solicita OEM/proveedor |
| [DELTA-FORUM-VLLM-RAY-GB10-RESOURCE-FIX-01](/home/lcasarin/projects/blackbox/tasks/backlog/DELTA-FORUM-VLLM-RAY-GB10-RESOURCE-FIX-01.md) | Workload o ensayo de laboratorio | coordinación BB prepara; operador Luis ejecuta root/lab |
| [DELTA-ROOT-BACKUP-MOUNT-BOOT-IDENTITY-01](/home/lcasarin/projects/blackbox/tasks/backlog/DELTA-ROOT-BACKUP-MOUNT-BOOT-IDENTITY-01.md) | Decisión del operador | Luis decide/aporta la identidad esperada del recurso antes de validar. |
| [DELTA-ROOT-CONTAINER-EFFECTIVE-BUILD-AND-OFFLINE-GATE-01](/home/lcasarin/projects/blackbox/tasks/backlog/DELTA-ROOT-CONTAINER-EFFECTIVE-BUILD-AND-OFFLINE-GATE-01.md) | Workload o ensayo de laboratorio | BB; operador Luis para workload/lab |
| [DELTA-ROOT-DISPLAY-CARVEOUT-OEM-FIX-GATE-01](/home/lcasarin/projects/blackbox/tasks/backlog/DELTA-ROOT-DISPLAY-CARVEOUT-OEM-FIX-GATE-01.md) | Evidencia o compatibilidad OEM | coordinación BB gestiona OEM |
| [DELTA-ROOT-DSML-PARSER-RECOVERY-BOUNDARY-01](/home/lcasarin/projects/blackbox/tasks/backlog/DELTA-ROOT-DSML-PARSER-RECOVERY-BOUNDARY-01.md) | Workload o ensayo de laboratorio | Coordinación BB; para recuperación de históricos, custodio del artifact store si corresponde. |
| [DELTA-ROOT-GLM53-QUEUED-REQUEST-PROGRESS-GATE-01](/home/lcasarin/projects/blackbox/tasks/backlog/DELTA-ROOT-GLM53-QUEUED-REQUEST-PROGRESS-GATE-01.md) | Workload o ensayo de laboratorio | BB; operador Luis para workload/lab |
| [DELTA-ROOT-GX10-SOC-EC-CABLE-RECOVERY-CANDIDATE-01](/home/lcasarin/projects/blackbox/tasks/backlog/DELTA-ROOT-GX10-SOC-EC-CABLE-RECOVERY-CANDIDATE-01.md) | Evidencia o compatibilidad OEM | coordinación BB gestiona OEM; operador Luis ejecuta canario |
| [DELTA-ROOT-MIMO-OVERLAY-AND-PREFILL-FAIRNESS-01](/home/lcasarin/projects/blackbox/tasks/backlog/DELTA-ROOT-MIMO-OVERLAY-AND-PREFILL-FAIRNESS-01.md) | Workload o ensayo de laboratorio | Coordinación BB prepara/implementa; cuando la acción requiere root/lab/hardware, operador Luis aporta y ejecuta el sujeto indicado. |
| [DELTA-ROOT-MIMO-PATCH-SUPERSESSION-GATE-01](/home/lcasarin/projects/blackbox/tasks/backlog/DELTA-ROOT-MIMO-PATCH-SUPERSESSION-GATE-01.md) | Workload o ensayo de laboratorio | Coordinación BB; para recuperación de históricos, custodio del artifact store si corresponde. |
| [DELTA-ROOT-RAY-MULTIENGINE-RANK-PROGRESS-01](/home/lcasarin/projects/blackbox/tasks/backlog/DELTA-ROOT-RAY-MULTIENGINE-RANK-PROGRESS-01.md) | Workload o ensayo de laboratorio | BB; operador Luis para workload/lab |
| [DELTA-ROOT-RECIPE-MEMORY-UNKNOWN-AND-RAW-EVIDENCE-01](/home/lcasarin/projects/blackbox/tasks/backlog/DELTA-ROOT-RECIPE-MEMORY-UNKNOWN-AND-RAW-EVIDENCE-01.md) | Workload o ensayo de laboratorio | coordinación BB prepara; operador Luis ejecuta root/lab |
| [DELTA-ROOT-SUBAMBIENT-COOLING-AND-UMA-CANARY-01](/home/lcasarin/projects/blackbox/tasks/backlog/DELTA-ROOT-SUBAMBIENT-COOLING-AND-UMA-CANARY-01.md) | Workload o ensayo de laboratorio | Coordinación BB prepara/implementa; cuando la acción requiere root/lab/hardware, operador Luis aporta y ejecuta el sujeto indicado. |
| [DELTA-ROOT-TOKENIZER-PATCH-SEMANTIC-GATE-01](/home/lcasarin/projects/blackbox/tasks/backlog/DELTA-ROOT-TOKENIZER-PATCH-SEMANTIC-GATE-01.md) | Evidencia o compatibilidad OEM | BB; coordinación solicita OEM/proveedor |
| [DELTA-ROOT-TRITON-ALLOCATOR-PATCH-STATE-GATE-01](/home/lcasarin/projects/blackbox/tasks/backlog/DELTA-ROOT-TRITON-ALLOCATOR-PATCH-STATE-GATE-01.md) | Workload o ensayo de laboratorio | coordinación BB prepara; operador Luis ejecuta root/lab |
| [FEATURE-1358-CGROUP-01-REPRO](/home/lcasarin/projects/blackbox/tasks/backlog/FEATURE-1358-CGROUP-01-REPRO.md) | Workload o ensayo de laboratorio | Coordinación BB; para recuperación de históricos, custodio del artifact store si corresponde. |
| [FEATURE-1358-CGROUP-02-TRAZA](/home/lcasarin/projects/blackbox/tasks/backlog/FEATURE-1358-CGROUP-02-TRAZA.md) | Acceso privilegiado | BB; operador Luis para acceso root/lab |
| [FEATURE-1358-CGROUP-03-NATIVO](/home/lcasarin/projects/blackbox/tasks/backlog/FEATURE-1358-CGROUP-03-NATIVO.md) | Workload o ensayo de laboratorio | coordinación BB prepara; operador Luis ejecuta root/lab |
| [FEATURE-1358-CGROUP-04-PARCHE](/home/lcasarin/projects/blackbox/tasks/backlog/FEATURE-1358-CGROUP-04-PARCHE.md) | Workload o ensayo de laboratorio | Coordinación BB; para recuperación de históricos, custodio del artifact store si corresponde. |
| [FEATURE-1358-CGROUP-05-CUELGUES](/home/lcasarin/projects/blackbox/tasks/backlog/FEATURE-1358-CGROUP-05-CUELGUES.md) | Workload o ensayo de laboratorio | Coordinación BB prepara/implementa; cuando la acción requiere root/lab/hardware, operador Luis aporta y ejecuta el sujeto indicado. |
| [FEATURE-APT-CRITICAL-METAPACKAGE-GUARD](/home/lcasarin/projects/blackbox/tasks/backlog/FEATURE-APT-CRITICAL-METAPACKAGE-GUARD.md) | Evidencia histórica ausente | BB |
| [FEATURE-FORUM-DESKTOP-SESSION-POSTUPDATE-01](/home/lcasarin/projects/blackbox/tasks/backlog/FEATURE-FORUM-DESKTOP-SESSION-POSTUPDATE-01.md) | Hardware o equipos pares | coordinación BB prepara; operador Luis ejecuta root/lab |
| [FEATURE-FORUM-GB10-RUNTIME-COMPAT-01](/home/lcasarin/projects/blackbox/tasks/backlog/FEATURE-FORUM-GB10-RUNTIME-COMPAT-01.md) | Workload o ensayo de laboratorio | Coordinación BB prepara/implementa; cuando la acción requiere root/lab/hardware, operador Luis aporta y ejecuta el sujeto indicado. |
| [FEATURE-FORUM-GPU-CLOCK-CAP-AB-01](/home/lcasarin/projects/blackbox/tasks/backlog/FEATURE-FORUM-GPU-CLOCK-CAP-AB-01.md) | Workload o ensayo de laboratorio | BB; operador Luis para workload/lab |
| [FEATURE-FORUM-GPU-GSP-BOOT-HEALTH-01](/home/lcasarin/projects/blackbox/tasks/backlog/FEATURE-FORUM-GPU-GSP-BOOT-HEALTH-01.md) | Hardware o equipos pares | coordinación BB prepara; operador Luis ejecuta root/lab |
| [FEATURE-FORUM-NETCONSOLE-01](/home/lcasarin/projects/blackbox/tasks/backlog/FEATURE-FORUM-NETCONSOLE-01.md) | Acceso privilegiado | Coordinación BB prepara/implementa; cuando la acción requiere root/lab/hardware, operador Luis aporta y ejecuta el sujeto indicado. |
| [FEATURE-FORUM-NVME-READONLY-01](/home/lcasarin/projects/blackbox/tasks/backlog/FEATURE-FORUM-NVME-READONLY-01.md) | Hardware o equipos pares | BB; operador Luis para hardware/peer |
| [FEATURE-FORUM-PROVIDER-FALLBACK-REGRESSION-01](/home/lcasarin/projects/blackbox/tasks/backlog/FEATURE-FORUM-PROVIDER-FALLBACK-REGRESSION-01.md) | Workload o ensayo de laboratorio | coordinación BB prepara; operador Luis ejecuta root/lab |
| [FEATURE-FORUM-RCU-PANIC-PSTORE-01](/home/lcasarin/projects/blackbox/tasks/backlog/FEATURE-FORUM-RCU-PANIC-PSTORE-01.md) | Acceso privilegiado | Coordinación BB prepara/implementa; cuando la acción requiere root/lab/hardware, operador Luis aporta y ejecuta el sujeto indicado. |
| [FEATURE-FORUM-RESCUE-RUNBOOK-01](/home/lcasarin/projects/blackbox/tasks/backlog/FEATURE-FORUM-RESCUE-RUNBOOK-01.md) | Hardware o equipos pares | Coordinación BB; para recuperación de históricos, custodio del artifact store si corresponde. |
| [FEATURE-FORUM-SBSA-WATCHDOG-STATE-01](/home/lcasarin/projects/blackbox/tasks/backlog/FEATURE-FORUM-SBSA-WATCHDOG-STATE-01.md) | Acceso privilegiado | BB; operador Luis para acceso root/lab |
| [FEATURE-FORUM-WIFI-ISOLATION-01](/home/lcasarin/projects/blackbox/tasks/backlog/FEATURE-FORUM-WIFI-ISOLATION-01.md) | Hardware o equipos pares | coordinación BB prepara; operador Luis ejecuta root/lab |
| [FEATURE-MEMORYSAVER-02-TRAZADOR](/home/lcasarin/projects/blackbox/tasks/backlog/FEATURE-MEMORYSAVER-02-TRAZADOR.md) | Acceso privilegiado | Coordinación BB prepara/implementa; cuando la acción requiere root/lab/hardware, operador Luis aporta y ejecuta el sujeto indicado. |
| [FEATURE-MEMORYSAVER-04-PACKING-4K](/home/lcasarin/projects/blackbox/tasks/backlog/FEATURE-MEMORYSAVER-04-PACKING-4K.md) | Workload o ensayo de laboratorio | BB; operador Luis para workload/lab |
| [FEATURE-USB-HID-POSTUPDATE-CHECK](/home/lcasarin/projects/blackbox/tasks/backlog/FEATURE-USB-HID-POSTUPDATE-CHECK.md) | Hardware o equipos pares | coordinación BB prepara; operador Luis ejecuta root/lab |
| [FORUM-00-CX7-HOTPLUG-FAN-PROTECTION](/home/lcasarin/projects/blackbox/tasks/backlog/FORUM-00-CX7-HOTPLUG-FAN-PROTECTION.md) | Hardware o equipos pares | Coordinación BB prepara/implementa; cuando la acción requiere root/lab/hardware, operador Luis aporta y ejecuta el sujeto indicado. |
| [FORUM-00-DGX-OTA-DRM-COMPAT-PREFLIGHT](/home/lcasarin/projects/blackbox/tasks/backlog/FORUM-00-DGX-OTA-DRM-COMPAT-PREFLIGHT.md) | Evidencia o compatibilidad OEM | BB; coordinación solicita OEM/proveedor |
| [FORUM-00-DOCKER-OOM-RESTART-LOOP](/home/lcasarin/projects/blackbox/tasks/backlog/FORUM-00-DOCKER-OOM-RESTART-LOOP.md) | Workload o ensayo de laboratorio | coordinación BB prepara; operador Luis ejecuta root/lab |
| [FORUM-00-GB10-THERMAL-RESIDENCY-ADMISSION](/home/lcasarin/projects/blackbox/tasks/backlog/FORUM-00-GB10-THERMAL-RESIDENCY-ADMISSION.md) | Workload o ensayo de laboratorio | Coordinación BB prepara/implementa; cuando la acción requiere root/lab/hardware, operador Luis aporta y ejecuta el sujeto indicado. |
| [FORUM-00-KERNEL-INITRD-UPDATE-GATE](/home/lcasarin/projects/blackbox/tasks/backlog/FORUM-00-KERNEL-INITRD-UPDATE-GATE.md) | Acceso privilegiado | Coordinación BB prepara/implementa; cuando la acción requiere root/lab/hardware, operador Luis aporta y ejecuta el sujeto indicado. |
| [FORUM-00-REALTEK-EEE-DIRECT-LINK](/home/lcasarin/projects/blackbox/tasks/backlog/FORUM-00-REALTEK-EEE-DIRECT-LINK.md) | Hardware o equipos pares | BB; operador Luis para hardware/peer |
| [FORUM-02-GX10-READ-INTEGRITY](/home/lcasarin/projects/blackbox/tasks/backlog/FORUM-02-GX10-READ-INTEGRITY.md) | Hardware o equipos pares | coordinación BB prepara; operador Luis ejecuta root/lab |
| [FORUM-02-PSTORE-KERNEL-REGRESSION](/home/lcasarin/projects/blackbox/tasks/backlog/FORUM-02-PSTORE-KERNEL-REGRESSION.md) | Acceso privilegiado | Coordinación BB prepara/implementa; cuando la acción requiere root/lab/hardware, operador Luis aporta y ejecuta el sujeto indicado. |
| [FORUM-02-USB-UVC-EP0](/home/lcasarin/projects/blackbox/tasks/backlog/FORUM-02-USB-UVC-EP0.md) | Hardware o equipos pares | BB; operador Luis para hardware/peer |
| [FORUM-REALTEK-DRIVER-BINDING-01](/home/lcasarin/projects/blackbox/tasks/backlog/FORUM-REALTEK-DRIVER-BINDING-01.md) | Hardware o equipos pares | coordinación BB prepara; operador Luis ejecuta root/lab |

## Preparación de publicación — seguimiento de H1 y sunset

El requisito de publicación sigue pendiente. Las 96 fichas permanecen abiertas; las correcciones de instrumentos y documentación conservan sus criterios de cierre.

- El control focal del servicio produjo `9 passed, 77 deselected`; salida y alcance en `tasks/evidence/OPEN-96-CLASSIFICATION-2026-10-04/heartbeat-and-sunset-correction-root.json`.
- El gate Python `simplecode.worktree.zero_debt --root .` produjo 140 ficheros examinados, cero hallazgos y cero `could_not_run`; tres ficheros ignorados quedan fuera de ese alcance. Recibo: `zero-debt-after-renewals-root.json`.
- Se corrigió la cifra histórica de sondeo de 109 a 130 en el comentario; la salida cruda original se conserva. La prueba de cleanup con terminación demorada se reprodujo: cuatro consultas con pausa, 50 neutralizándola, mismo resultado de desaparición. Estos números describen esa ejecución, no una garantía de rendimiento. Recibo: `publication-sunset/renderer-delayed-root.log`.
- El contrato actual de Simplecode permite versionar runner, runtime y lock; `.gitignore` ahora los rescata explícitamente y conserva la caché y los claims como estado local. Seis controles de inclusión/exclusión pasan. Ambos hashes coinciden con el lock de 9.3.4; la comprobación del ZIP encuentra cero errores CRC. Recibos: `publication-sunset/runtime-ignore-root.json` e `installed-kit-root-integrity.json`.
- Revisión sunset frente a 2.4.0: 23 excepciones vigentes, cero caducadas, cero sin etiqueta y cero sin fecha interpretable. El resultado del lector no contiene error de ejecución. Recibo: `publication-sunset/target-2.4-final-root.json`.
- SPEC distingue ahora la conclusión archivada sobre fechas de creación de los stdout que faltan, y atribuye el rango de cobertura histórica al snapshot de SPEC en vez de al mensaje del commit. El timer de deriva actual está loaded/active/enabled. H1 espera la re-auditoría de las afirmaciones corregidas antes de registrar el ledger.
- El barrido actual de privacidad registra 758 candidatos, 730 textos examinados, 92 coincidencias de correo, 28 binarios sin inspección textual y cero errores de lectura. La revisión de procedencia adicional está en curso; este informe mantiene `report_clean=false`. Recibo: `publication-privacy-current.json`.

La corrida global anterior (1983 pruebas que pasan y 104 que fallan) precede estos últimos cambios y conserva sus límites de alcance. Los controles focales y sunset aquí citados no sustituyen esa validación global ni autorizan dispensas de los experimentos abiertos.
