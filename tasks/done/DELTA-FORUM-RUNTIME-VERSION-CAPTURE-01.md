---
id: DELTA-FORUM-RUNTIME-VERSION-CAPTURE-01
kind: task
domain: VERDICT
title: "Validar forum runtime version capture 01"
status: done
closed_at: 2026-10-03
closure_type: relocated_prior_verification
reason: "Source and semantic regression test landed in 37ea339ed6c76571cacfa1787c4b58a9ec6ffc68; root independently ran the literal close_check successfully. This commit completes evidence indexing and relocates the already-verified capture task."
evidence: {"fail": "tasks/evidence/DELTA-FORUM-RUNTIME-VERSION-CAPTURE-01.fail.txt", "pass": "tasks/evidence/DELTA-FORUM-RUNTIME-VERSION-CAPTURE-01.pass.txt", "e2e": "tasks/evidence/DELTA-FORUM-RUNTIME-VERSION-CAPTURE-01.e2e.txt"}
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

## Root Cause

`tools.host_diagnostics.capture` omitted the effective CUDA Runtime API version and bounded runtime/container identity observations needed to preserve the host stack beside a short functional GPU check. The report now records host/runtime snapshots before and after the existing bounded CUDA integrity test, including exact CUDART version, loaded driver, OS/kernel/OEM releases, GPU state, Docker server version, tagged container candidates and image IDs when available. Container inspection reads only the image ID field, with a four-container cap and explicit incomplete status.

## Regression Test

PASS: `python3 -m pytest -q tests/test_debt_registration_controls.py::test_delta_forum_runtime_version_capture_01 tests/test_host_diagnostics.py::test_gpu_runtime_capture_uses_bounded_readonly_queries_and_preserves_failures tests/test_memory_capture_and_cuda_integrity.py::test_cuda_readback_accepts_known_bytes tests/test_memory_capture_and_cuda_integrity.py::test_cuda_readback_detects_mutated_byte tests/test_memory_capture_and_cuda_integrity.py::test_cuda_readback_detects_truncation` -> `5 passed in 0.11s`. The selector audits the saved real capture and rejects missing, unavailable, wrong-subject, changed-boot, mismatched-container, and corrupted-result evidence; a separately neutralized verifier fails the byte-corruption control.

## Verification Evidence

PASS: `python3 -m ruff check tools/host_diagnostics.py tests/test_host_diagnostics.py tests/test_debt_registration_controls.py` -> `All checks passed!`; `pyright tools/host_diagnostics.py` -> `0 errors, 0 warnings, 0 informations`; `git diff --check` -> exit 0.

FAIL control: the selector mutates raw capture copies to represent missing capture, `could_not_run`, wrong GPU subject, changed boot identity, empty image identities and corrupted CUDA output; every mutation is rejected. It also proves that a status-only PASS does not validate as evidence.

E2E: the independent elevated local-host capture is stored in `tasks/evidence/DELTA-FORUM-RUNTIME-VERSION-CAPTURE-01/runtime-capture.json`, with raw digest sidecar, exact collector command, and archived collector/implementation source snapshots plus hashes. It recorded DGX Spark, loaded driver 580.178.04, CUDA Runtime API version 13000, Docker 29.6.2, tagged vLLM container image identity, before/after host/runtime observations, and `python3 tools/cuda_integrity.py --workers 1 --rounds 1` returning pass with six allocations, with a maximum aggregate of 4 MiB and full readback under 512 MiB / 50% CPU / 60 second wrapper limits. The negative byte-corruption control rejected byte 2. Root independently reran the literal close-check selector successfully after the archived evidence and controls were finalized (`1 passed`). This closes runtime capture only; forum serving-workload compatibility remains in the parent feature ficha.
