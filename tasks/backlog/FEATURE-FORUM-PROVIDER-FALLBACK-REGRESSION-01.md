---
id: FEATURE-FORUM-PROVIDER-FALLBACK-REGRESSION-01
kind: task
domain: RUNTIME
title: "Validar fallback a CPU tras respawn y el fix reportado del stack NVIDIA"
status: open
severity: P2
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-10-02
close_check: {"cmd": "python3 -m tools.verify_forum_finding --id FEATURE-FORUM-PROVIDER-FALLBACK-REGRESSION-01 --evidence tasks/evidence/FEATURE-FORUM-PROVIDER-FALLBACK-REGRESSION-01", "expect": "exit_zero", "porque": "Verificador propuesto pendiente: requiere evidencia del caso positivo, controles negativos, compatibilidad OEM y recuperación/rollback; la ficha registra trabajo abierto."}
---

## Fuente y evidencia

[380948](https://forums.developer.nvidia.com/t/380948). ONNX reporta cuDNN FE11/cuBLAS internal, respawn, fallo cudaGetDeviceCount y CPU silencioso. El mismo batch pasó tras OTA OS7.5/kernel6.17-1031/driver580.173 en tres OEM según el autor. NVIDIA dice que la actualización pudo resolverlo; el bundle deja pendiente aislar driver como causa.

## Delta y prevención/resolución

FEATURE-GPU-UTIL-CERO-FALLBACK-CPU existe. Validar transición de worker y provider requiere una prueba de extremo a extremo antes de construir otro detector.

Verificar versión soportada OEM y validar requests, provider, PID/respawn, CPU/GPU y latencia en una cronología. Probar detector existente sin forzar downgrade; preservar evidencia y ofrecer reinicio acotado del servicio solo con recuperación y ownership definidos.

## Validación, riesgo y cierre

fallback tras reemplazo de worker, GPU idle sin requests, CPU intencional y GPU sana. Documentar comandos/output; si ya se detecta registrar covered. Una prueba fallida identifica el mínimo delta y mantiene la ficha abierta.

El verificador de close_check todavía debe implementarse; ejecutar esta ficha exige evidencia adicional y deja registradas las consultas que no pueden correr. Ningún cambio del host se aplica al registrar la propuesta. Detalle fuente preservado en tasks/evidence/SWARM-LUNA-FORUM-2026-10-02/findings_*.json y threads/.

[382922](https://forums.developer.nvidia.com/t/382922) añade tres recurrencias con nvidia-smi sano y fallo de creación del contexto CUDA; llama-server termina sirviendo CPU. Hubo distro upgrade parcial no soportado y NVIDIA indicó revertir. Incorporar fixture de GPU enumerada pero offload efectivo fallido, sin recomendar ese stack ni un rollback universal.

[372486](https://forums.developer.nvidia.com/t/372486) reports a GX10 idle hang despite a GPU cap, persistence setting and firmware state; the author says `cgroupfs` ran for 24 hours without a hang, but gives no weekly soak confirmation and binary logs remain unread. Do not change Blackbox systemd/cgroup-v2 behavior from this anecdote; retain it as a provider-specific reproducer and compare the same workload, cgroup provider and longer predeclared soak before proposing fallback changes.

## Progreso de preflight (2026-10-02)

Se implementó `python3 -m tools.preflight fallback <snapshot.json>` para detectar solicitudes GPU atendidas por CPU, exigir solicitudes observadas y rechazar observaciones malformadas. El host tiene un contenedor vLLM en ejecución con contador de reinicios cero y un proceso `VLLM::EngineCore` usando GPU; estos datos no identifican el proveedor de cada solicitud tras un respawn. El resultado queda `unknown`. Comandos y salidas literales: `tasks/evidence/FEATURE-FORUM-PROVIDER-FALLBACK-REGRESSION-01/commands.json`; evaluación: `preflight.json` y `validator-run.json`.

La ficha sigue abierta: faltan cronología request/provider/PID/respawn/latencia, control CPU intencional, validación del update OEM y recuperación/rollback acotados. No se generó carga de inferencia nueva.

## Progreso del analizador JSONL (2026-10-02)

Se añadió `python3 -m tools.provider_trace <trace.jsonl>`, un analizador de solo lectura que conserva cada petición separada y exige observaciones de worker/PID, proveedor y latencia asociadas al worker activo. El historial del proveedor conserva las transiciones por worker: una observación CPU seguida de GPU sigue bloqueando y se atribuye al worker donde apareció; un CPU anterior al respawn nunca se atribuye al replacement. Si faltan observaciones del worker actual, el resultado incluye `unknowns` aparte de los hallazgos; la salida también declara `could_not_run_count` (0 normalmente, 1 cuando la lectura/decodificación falla). Proveedores desconocidos, eventos huérfanos, campos inválidos, UTF-8 inválido y JSON truncado producen `unknown`; un cambio de PID sin evento restart también queda `unknown`. Fixtures sintéticos cubren GPU sano, CPU intencional y GPU→CPU tras respawn. La evaluación registrada en `tasks/evidence/FEATURE-FORUM-PROVIDER-FALLBACK-REGRESSION-01/provider-trace-run.json` muestra 100% de cobertura de `tools/provider_trace.py`, Ruff y Pyright limpios, y los controles esperados. No se obtuvo una traza de workload real, ni se validaron los tres OEM ni recuperación/rollback; la ficha permanece abierta.

[353683](https://forums.developer.nvidia.com/t/dgx-spark-gpu-usage-0-after-24-hours-open-webui/353683) reports an Open-WebUI/Ollama container falling back to CPU after more than 24 hours; Docker restart or host reboot restored GPU use temporarily, but the author never posted closure logs. A separate reporter in the thread confirms `systemctl daemon-reload` preceded container NVML `Unknown Error` and that a documented NVIDIA Container Toolkit workaround prevented recurrence. Keep the two incidents distinct; test exact driver/toolkit/cgroup state around daemon reload, collect host and container GPU health before recovery, and do not force cgroupfs or restart workloads automatically from this evidence.


## Índice de propuestas registradas del swarm NVIDIA categoría 721

- **`BB-DOCKER-GPU-LIVENESS-DAEMON-RELOAD`** — Open-WebUI/Ollama owner reports GPU utilization falling to zero and workload reverting to CPU after >24 hours; a separate reporter confirms `systemctl daemon-reload` triggers container NVML Unknown Error and NVIDIA Container Toolkit… Fuente: [353683](https://forums.developer.nvidia.com/t/353683/1).


## Índice de hallazgos asociados

- **`BB-GPU-PROVIDER-SILENT-FALLBACK`** — A reported ONNX Runtime service crashed with cuDNN FE 11/cuBLAS internal errors on older GB10 stacks; a respawned worker then failed cudaGetDeviceCount and silently fell back to CPU, degrading inference by multiple times until container… Fuente: [380948](https://forums.developer.nvidia.com/t/gb10-dgx-spark-cudnn-fe-failure-11-and-cublas-status-internal-error-under-batch-load-fixed-by-driver-580-173/380948/1).

[360785](https://forums.developer.nvidia.com/t/build-sglang-from-source-on-blackwell-pro-6000-dgx-spark/360785/8) is a negative control for health and provider telemetry: SGLang’s post-decode `pynvml.NVMLError_NotSupported` coincides with a saved image, and the author later confirms that the HTTP response succeeded with a corrected curl (post 14). The SGLang commit is not pinned. Keep request delivery, provider selection, and unsupported metric errors as separate observations; report provider `unknown` when native telemetry is unsupported. This does not establish CPU fallback.


## Defecto de ambigüedad y lectura detectado (2026-10-04)

El control sano JSONL devuelve `pass`. Al sustituir su observación de proveedor por un objeto con `provider: CPUExecutionProvider` seguido de otra clave `provider: CUDAExecutionProvider`, el analizador también devuelve `pass`: `json.loads` conserva el último valor y pierde la observación contradictoria. Reproducción literal: `tasks/evidence/CLOSURE-CONTROLS-2026-10-03/provider-duplicate-key-root-negative.json`.

La corrección requiere decodificación JSON estricta por línea y lectura regular acotada sin seguir symlinks, reutilizando `tools.capture_io`. El lector actual `read_text` carece de límite y puede bloquear sobre FIFO. El agente runtime tiene asignados controles negativos de duplicados, constantes no finitas, FIFO, ancestros y tamaño. El 100% histórico de cobertura no demuestra estas garantías. La ficha conserva su close_check y permanece abierta por este defecto y por la traza real/OEM/recuperación pendientes.

## Clasificación del impedimento — 2026-10-04

- Categoría principal: `workload_or_lab`.
- Impedimento: Analizador tiene controles de fixtures, pero no hay traza real request/provider/PID/respawn/latencia ni validación OEM/rollback; hay defecto de JSON duplicado pendiente.
- Evidencia faltante para cierre: corrección/negative tests de JSON estricto y lector acotado; trace real tras respawn; control CPU intencional, GPU sana y OEM/rollback
- Siguiente acción: Cerrar primero la ambigüedad del parser/lectura con controles requeridos; después capturar trace real de request y proveedor en canario sin generar fallback por downgrade.
- Responsable del siguiente paso: coordinación BB prepara; operador Luis ejecuta root/lab.
- Cierre completo accionable hoy: no. Preparación coordinable: sin acción adicional demostrada en esta revisión.
- Evidencias de clasificación: `tasks/backlog/FEATURE-FORUM-PROVIDER-FALLBACK-REGRESSION-01.md`, `tasks/evidence/OPEN-96-CLASSIFICATION-2026-10-04/batches/batch_08.json`, `tasks/evidence/FEATURE-FORUM-PROVIDER-FALLBACK-REGRESSION-01/commands.json`, `tasks/evidence/FEATURE-FORUM-PROVIDER-FALLBACK-REGRESSION-01/preflight.json`, `tasks/evidence/FEATURE-FORUM-PROVIDER-FALLBACK-REGRESSION-01/provider-trace-run.json`, `tasks/evidence/FEATURE-FORUM-PROVIDER-FALLBACK-REGRESSION-01/validator-run.json`.
- Impedimentos de inspección: 0. El criterio original permanece intacto; esta clasificación conserva la ficha abierta.
