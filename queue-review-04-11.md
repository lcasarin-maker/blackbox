# Revisión de cola LUNA-98: tandas 04–11

Fecha: 2026-10-03. Worktree: `/tmp/bb-luna98-02`, rama `codex/luna98-02`.

## Resultado de la revisión

Se revisaron las 40 fichas fuente de `batch-04.json` a `batch-11.json` y sus capturas previas. Las 40 capturas tienen `rc=4`, `launcher_timeouts=0`, `subject_could_not_run=0`; el stdout literal dice `no tests ran` y `ERROR: not found` para el selector. Esto significa que pytest no llegó al sujeto. `subject_could_not_run=0` no equivale a una ejecución del equipo. No repetí ningún `close_check`: los selectores no cambiaron y ejecutarlos otra vez produciría la misma resolución fallida.

No se cerró ninguna investigación ni se cambió el estado de las tarjetas. Los ensayos requeridos dependen de hardware Spark/CX7/SM121, despliegues vLLM/Ray/llama.cpp concretos, modelos/checkpoints/digests, o condiciones de recuperación que no están disponibles y algunas están expresamente fuera del alcance seguro. Las pruebas con fixtures solo ejercitarían instrumentos, nunca probarían los sujetos de estos reportes.

El escalón de reutilización se agotó antes de proponer módulos nuevos: `tools/preflight.py` verifica identidad/arquitectura de imagen y manifest de backend; `tools/atom_gpu_telemetry.py` ya toma zonas térmicas, clocks y métricas GPU/vLLM; `tools/host_diagnostics.py` observa el host e imágenes/contenedores; `tools/service_probe.py` está limitado a SSH loopback; las runbooks de recovery, runtime, temperatura, CX7 y read-integrity ya tienen artefactos. Ninguno ejecuta los canarios de modelo/red/hardware exigidos por las fichas. No se modificó código porque un wrapper sin sujeto ni contrato adicional repetiría preflight o presentaría una señal parcial como cierre.

## Disposición por ficha

Todas permanecen `open`; los reportes siguientes documentan bloqueo concreto, no un veredicto de salud.

| ID | Motivo y trabajo que falta |
|---|---|
| `DELTA-FORUM-3NODE-NCCL-IMAGE-AND-FIRST-REQUEST-01` | Clúster de 3 Spark, digest/NCCL por rank y primera inferencia PP; no hay canario multi-node. |
| `DELTA-FORUM-8NODE-NCCL-INTERFACE-MTU-01` | 8 nodos y MTU comparado con plan OEM por interfaz; luego NCCL y primera inferencia; sin valor MTU universal. |
| `DELTA-FORUM-CLOCK-CAP-TRADEOFF-AND-THERMAL-ZONE-GAP-01` | Reutilizar telemetría térmica existente; falta A/B de workload/cap OEM y rollback. No cambiar clocks. |
| `DELTA-FORUM-CROSS-TURN-SLEEPER-INJECTION-REGRESSION-01` | Modelo/parser/template real y canario multi-turn con herramienta mock, controles positivo y negativo; nada equivalente en el runtime local. |
| `DELTA-FORUM-CUTLASS-SM121-ISA-GATE-01` | Build/ejecución SM121, comparación numérica; no hay GPU/stack sujeto. |
| `DELTA-FORUM-CX7-FW-UPDATE-GUARD-01` | Valida updater/PSID/prerequisitos y rollback OEM; flash prohibido y hardware reemplazable ausente. |
| `DELTA-FORUM-CX7-PHYSICAL-TOPOLOGY-ALIAS-CHECK-01` | PCI BDF↔conector y control físico de enlace en CX7; inventario lógico no prueba cableado. |
| `DELTA-FORUM-CX7-POSTHOTPLUG-01` | Canary RDMA/NCCL post-hotplug con PCIe/AER/FieldDiag; no hay NIC canary ni ciclos autorizados. |
| `DELTA-FORUM-CX7-RDMA-ASYMMETRY-RETEST-01` | Repeticiones direccionales en dos GX10 por estado/cable/firmware; no hay pareja de nodos ni reboot/hotplug aprobado. |
| `DELTA-FORUM-DCP-MTP-DRAFT-CORRECTNESS-AND-PRETRIM-OOM-01` | DCP/MTP por rank, referencia DCP1 y cold-load/headroom con stack 4×GB10; patch externo no auditado. |
| `DELTA-FORUM-DCP4-DECODE-STARVATION-FAIR-SCHEDULER-01` | Fairness/throughput/stalls de decode largo + prefills en TP8/DCP4; scheduler comunitario no está en el repo ni clúster disponible. |
| `DELTA-FORUM-DFLASH-XGRAMMAR-STRUCTURED-OUTPUT-REGRESSION-01` | Matriz modelo/parser/versión con streaming, JSON, paralelo y follow-up tool calls; fixtures no prueban la regresión real. |
| `DELTA-FORUM-DSV41-NFS-STOP-TAG-PIN-01` | El script stop/exportador del que depende la ficha no está en el repo; contrato externo no definido para auditar. |
| `DELTA-FORUM-DUALSPARK-NCCL-GID-TWIN-AND-COLD-RECOVERY-01` | GID/NCCL sin IPv4, collective, inferencia y cold recovery en dos Spark; sin sujeto ni recovery autorizado. |
| `DELTA-FORUM-DUALSPARK-POWER-RESET-RECOVERY-01` | Requiere cortar/restaurar alimentación y validar recovery; ensayo prohibido. |
| `DELTA-FORUM-GLM52-MULTITURN-CORRECTNESS-AND-RECIPE-SENSITIVITY-01` | Soak de 80–95K/15+ turnos y pares de receta con checkpoint/runtime GLM fijados; no disponible. |
| `DELTA-FORUM-GPTOSS-MULTINODE-RAY-CHANNEL-TIMEOUT-01` | Dos Spark, resource placement Ray y petición funcional sobre digest fijado; el preflight no observa placement. |
| `DELTA-FORUM-KV-QUANT-METRIC-PROVENANCE-GATE-01` | Hay counters de host/cgroup/GPU/vLLM, pero falta lectura de bytes KV del allocator/modelo exactos y comparación pareada. |
| `DELTA-FORUM-LLAMACPP-RPC-UMA-AND-ORDERLY-TEARDOWN-01` | Medir llama.cpp RPC, transporte y cierre cliente→servidor en dos nodos; deployment ausente, sin OOM/kill permitido. |
| `DELTA-FORUM-M2-COMPACTION-STATE-VALIDATION-01` | Runtime que compacte KV y sesión larga M2 con tools/control limpio; no hay harness/checkpoint. |
| `DELTA-FORUM-MEMORY-RECOVERY-SOAK-01` | Soak multihora llama.cpp RPC y recuperación cliente/servidor; telemetría genérica existente no demuestra la recuperación. |
| `DELTA-FORUM-MINIMAX-TOOLCALL-FUNCTIONAL-CANARY-01` | Mismo proceso Minimax: texto→tool mock→texto, argumentos byte-exactos/vida del proceso; no hay servicio ni digest. |
| `DELTA-FORUM-MTP-ACCEPTANCE-AND-SEMANTIC-CONTROL-01` | Pares MTP on/off y aceptación posicional más semántica sobre stack fijado; no hay generación MTP disponible. |
| `DELTA-FORUM-MUSE-GLIMMER-DFLASH-MAX-SEQS-GATE-01` | Boundary de concurrencia 32/33 más canarios semánticos en modelo/runtime exactos; no se infiere cap universal. |
| `DELTA-FORUM-NCCL-TP-ORCHESTRATION-CORRECTION-01` | Contrastar launcher/entorno por rank, NCCL e inferencia con dos Spark; no hay cluster. |
| `DELTA-FORUM-NEMOTRON-SM121-PREBUILT-KERNEL-01` | Build/kernel e inferencia sobre SM121 contra referencia/negativo; artefactos y GPU ausentes. |
| `DELTA-FORUM-OPENCLAW-VLLM-REQUEST-CONTRACT-01` | Hace falta contrato OpenClaw↔vLLM/endpoint definido; no inventar schema; `preflight.py` solo cubre identidad/arquitectura. |
| `DELTA-FORUM-QWEN-COLD-COMPILE-OOM-01` | Reproducción cold compile puede perder acceso remoto; dos Spark/logs originales ausentes y provocar OOM no autorizado. |
| `DELTA-FORUM-QWEN-LONG-AGENT-STOP-01` | Soak real de agente/checkpoints y continuidad sin duplicar herramientas mutantes; no hay agente/datos. |
| `DELTA-FORUM-QWEN-MTP-PARSER-CANCEL-STATE-CHECK-01` | Matriz parser×MTP×cancelación y siguiente tool call dentro del mismo server; runtime exacto ausente. |
| `DELTA-FORUM-QWEN-SERVICE-OOMD-CACHE-FAIL-01` | Presión/OOMD real en Studio/Hermes; no inducir presión, no desactivar OOMD ni reiniciar. |
| `DELTA-FORUM-QWEN-TOOLCALL-WEDGE-01` | Wedge vivo requiere capturar el bundle antes de recovery; no hay incidente y no se provocará. |
| `DELTA-FORUM-QWEN35-NVFP4-CUTLASS-FIRST-REQUEST-GATE-01` | Primera inferencia NVFP4 y referencia semántica sobre combinación SM121/kernel fijada; sujeto ausente. |
| `DELTA-FORUM-QWEN38-LONG-RUN-JSON-CORRECTNESS-CANARY-01` | Canario JSON largo repetido con checkpoint/backend/KV/MTP fijados; no hay modelo/harness. |
| `DELTA-FORUM-RAY-TORCH-GRAPH-HANG-01` | Matriz Torch/Ray/vLLM multi-node y progreso por rank; requiere dos Spark, no basta uso GPU. |
| `DELTA-FORUM-RECOVERY-APT-UPDATE-01` | La runbook existe, pero cierre requiere validar vía consola/medio OEM y captura previa en canary; no recovery/apt mutante autorizado. |
| `DELTA-FORUM-THERMAL-AUXILIARY-COOLING-AND-CLOCK-CAP-01` | Reutilizar telemetría; falta A/B OEM de cooling/cap, potencia y rendimiento; no aplicar cambios universales. |
| `DELTA-FORUM-USB-RAID-LINK-ADMISSION-01` | Observación USB existente no bloquea assemble/mount mdadm por identidad/link speed; sin contrato fiable no inventar guard, no tocar array. |
| `DELTA-FORUM-VLLM-GB10-ARCH-AND-BUILD-MATRIX-01` | `preflight.py` ya valida arch/manifest; cierre pide toolchain/wheel/build/import/load/generación real por digest sobre SM121. |
| `DELTA-FORUM-VLLM-RAY-GB10-RESOURCE-FIX-01` | Mapa Ray por nodo y smoke funcional del tag elegido; reportes históricos 25.11/26.01 no prueban el stack actual. |

## Evidencia y cambios

Los veredictos por tanda están en `/tmp/bb-luna98-verdict_04.json` … `/tmp/bb-luna98-verdict_11.json`. Cada uno conserva los cinco IDs fuente, comando/rc iniciales y referencia a stdout capturado; `after_cmd`/`after_rc` son null porque no se repitieron invocaciones sin cambios. `commit` por ficha es null: no se cambió ninguna tarjeta ni evidencia original.
