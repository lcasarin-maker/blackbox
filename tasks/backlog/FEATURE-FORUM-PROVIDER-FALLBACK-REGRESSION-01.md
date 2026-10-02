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
