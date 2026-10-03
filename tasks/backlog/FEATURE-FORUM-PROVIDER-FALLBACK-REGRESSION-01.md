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

## Índice de propuestas registradas del swarm NVIDIA categoría 721

- **`BB-DOCKER-GPU-LIVENESS-DAEMON-RELOAD`** — Open-WebUI/Ollama owner reports GPU utilization falling to zero and workload reverting to CPU after >24 hours; a separate reporter confirms `systemctl daemon-reload` triggers container NVML Unknown Error and NVIDIA Container Toolkit… Fuente: [353683](1).


## Índice de hallazgos asociados

- **`BB-GPU-PROVIDER-SILENT-FALLBACK`** — A reported ONNX Runtime service crashed with cuDNN FE 11/cuBLAS internal errors on older GB10 stacks; a respawned worker then failed cudaGetDeviceCount and silently fell back to CPU, degrading inference by multiple times until container… Fuente: [380948](https://forums.developer.nvidia.com/t/gb10-dgx-spark-cudnn-fe-failure-11-and-cublas-status-internal-error-under-batch-load-fixed-by-driver-580-173/380948/1).

[360785](https://forums.developer.nvidia.com/t/build-sglang-from-source-on-blackwell-pro-6000-dgx-spark/360785/8) is a negative control for health and provider telemetry: SGLang’s post-decode `pynvml.NVMLError_NotSupported` coincides with a saved image, and the author later confirms that the HTTP response succeeded with a corrected curl (post 14). The SGLang commit is not pinned. Keep request delivery, provider selection, and unsupported metric errors as separate observations; report provider `unknown` when native telemetry is unsupported. This does not establish CPU fallback.

## Estado de publicación de esta investigación

Propuesta abierta. Los comandos de cierre describen el verificador y evidencia requeridos; esta rama publica investigación y fichas, sin implementación ni resultados de ejecución de los mecanismos propuestos.
