---
id: DELTA-FORUM-RUNTIME-VERSION-CAPTURE-01
kind: task
domain: VERDICT
title: "Validar forum runtime version capture 01"
status: open
severity: P2
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-10-02
close_check: {"cmd": "python3 -m pytest -q tests/test_debt_registration_controls.py::test_delta_forum_runtime_version_capture_01", "expect": "exit_zero", "porque": "Aplicar el alcance y los controles concretos de la evidencia copiada arriba: stack/OEM y versiones fijadas, sujeto real, caso sano y negativo, resultados literales y rollback cuando haya intervención. Si faltan hardware, adjuntos, compatibilidad o permisos, imprimir could_not_run y conservar open. Un score agregado o mero estado de un dispositivo no acredita el resultado funcional. No instalar parches ni provocar fallo del host para registrar la ficha."}
---

## Registro y responsable

Registro solicitado por Luis el 2026-10-02. Responsable: coordinación de Blackbox. Trabajo o revisión pendiente; la presencia del marcador no demuestra por sí sola un defecto.

## Evidencia y alcance

Trabajo separado del ámbito de su ficha madre, conservando la fuente original. Los reportes de foro siguen sin validación local y no se convierten en recomendaciones automáticas.

**DELTA-FORUM-RUNTIME-VERSION-CAPTURE-01.** En un Spark con Driver 550.54.15/CUDA 12.4, el autor reporta que inicialmente `nvidia-smi` mostraba GPU 0% y ~5W; después de ejecutar `gpu-burn` y cambiar a Driver 580.95.05/CUDA 13.0, el mismo autor observa 96%/~28W ([356426](https://forums.developer.nvidia.com/t/356426)). No es validación independiente y el ZIP diagnóstico compartido no se leyó. El hilo muestra por qué recoger versión de host, runtime/container, estado GPU antes/después de carga y resultado funcional en una prueba corta. El warning mlx5 27W también aparece en una unidad sana en idle; no usarlo por sí solo como diagnóstico de límite de potencia.

Fuentes: tasks/backlog/FEATURE-FORUM-GB10-RUNTIME-COMPAT-01.md.

## Criterio de cierre y control negativo

Aplicar el alcance y los controles concretos de la evidencia copiada arriba: stack/OEM y versiones fijadas, sujeto real, caso sano y negativo, resultados literales y rollback cuando haya intervención. Si faltan hardware, adjuntos, compatibilidad o permisos, imprimir could_not_run y conservar open. Un score agregado o mero estado de un dispositivo no acredita el resultado funcional. No instalar parches ni provocar fallo del host para registrar la ficha.

## Estado del verificador

La ficha permanece abierta. El test selector del close_check es una especificación pendiente, no una prueba existente ni un resultado ejecutado. Implementarlo exige comprobar el sujeto y su control negativo; la existencia de archivos o esta ficha no basta para cerrar.

Conservar comandos, salida literal y could_not_run incluso cero; una ejecución skipped o inaccesible deja el cierre pendiente. Reutilizar instrumentos nativos y pruebas existentes antes de crear código.

## Root cause

The existing `tools.host_diagnostics.capture` report did not include GPU/runtime version observations, so a host diagnostic could not preserve the effective NVIDIA driver/GPU state beside the container engine and running image tags. The named close-check selector is also absent from `tests/test_debt_registration_controls.py`. A bounded host CUDA buffer-readback check now passed, but the forum's container serving workload and exact vLLM image digest remain unverified.

## Regression test

PASS: `python3 -m pytest -q tests/test_host_diagnostics.py::test_gpu_runtime_capture_uses_bounded_readonly_queries_and_preserves_failures tests/test_host_diagnostics.py::test_capture_uses_fixed_read_only_queries_and_reports_signals tests/test_host_diagnostics.py::test_command_failure_is_preserved` -> `6 passed in 0.03s`. The positive control checks query shape/integration and the negative control proves four unavailable reads remain `could_not_run`.

## Verification evidence

PASS: `python3 -m ruff check tools/host_diagnostics.py tests/test_host_diagnostics.py` -> `All checks passed!`; `pyright tools/host_diagnostics.py` -> `0 errors, 0 warnings, 0 informations`.

PASS: `python3 -m pytest -q tests/test_memory_capture_and_cuda_integrity.py::test_cuda_readback_accepts_known_bytes tests/test_memory_capture_and_cuda_integrity.py::test_cuda_readback_detects_mutated_byte tests/test_memory_capture_and_cuda_integrity.py::test_cuda_readback_detects_truncation` -> `3 passed in 0.04s`; `pyright tools/cuda_integrity.py` -> `0 errors, 0 warnings, 0 informations`; `python3 -m ruff check tools/cuda_integrity.py` -> `All checks passed!`. The negative control corrupts one expected byte and the verifier rejects it at byte 2; truncation is rejected at byte 3.

FAIL: `python3 -m pytest -q tests/test_debt_registration_controls.py::test_delta_forum_runtime_version_capture_01` -> `no tests ran`, selector not found, exit 4. FAIL: complete `tests/test_host_diagnostics.py` -> `24 passed, 1 failed`; the unrelated existing contact-redaction test invokes missing `.simplecode/run.py` in this worktree (exit 2). Targeted affected subset passed as recorded above.

E2E (read-only, elevated local host access): `nvidia-smi --query-gpu=name,driver_version,pci.bus_id,utilization.gpu,power.draw --format=csv,noheader` -> `NVIDIA GB10, 580.178.04, 0000000F:01:00.0, 3 %, 12.42 W`, rc=0. `nvidia-smi` banner reported Driver 580.178.04 and CUDA Version 13.0; that CUDA value is the driver's advertised maximum, not the installed CUDA runtime. `docker version --format '{{.Server.Version}}'` -> `29.6.2`, rc=0. `docker ps --no-trunc --format '{{.ID}} {{.Image}}'` showed active `vllm/vllm-openai:v0.27.1` by tag, with no digest supplied for that image. No inference request or container inspection was performed. The functional request path, exact vLLM image digest, before/after workload result and negative workload control remain unverified; ficha stays open.

E2E (bounded host CUDA integrity test): before, `nvidia-smi` showed GB10, driver 580.178.04, driver-advertised CUDA 13.0, 5% GPU use, 12.81 W; `free -b` showed 58,255,551,616 bytes available and 8,424,747,008 bytes swap free. Memory total/used from the NVIDIA query were `[N/A]`, so UMA headroom is not exposed by that field; the existing tool's 4 MiB worker allocation was below its cgroup `MemoryMax=512M`, `CPUQuota=50%`, `RuntimeMaxSec=60s` bounds. Exact command: `python3 tools/cuda_integrity.py --workers 1 --rounds 1` -> `{"allocations": 6, "full_buffer_readback": true, "library": "libcudart.so.13", "max_aggregate_allocation_bytes": 4194304, "release_between_rounds": true, "rounds_per_worker": 1, "seconds": 0.40612861499539576, "status": "pass", "workers": 1}`, rc=0. Afterward, `nvidia-smi` showed the same GB10/driver, 6% GPU use, 12.98 W; `free -b` showed 58,339,807,232 bytes available and 8,424,749,296 bytes swap free. Active processes and the vLLM container remained separately observed; this CUDA run used host `libcudart.so.13` and does not validate or attribute behavior to the vLLM image. The named close-check still does not exist, so the ficha remains open.
