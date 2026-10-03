---
id: DELTA-FORUM-MTP-ACCEPTANCE-AND-SEMANTIC-CONTROL-01
kind: task
domain: VERDICT
title: "Validar forum mtp acceptance and semantic control 01"
status: open
severity: P2
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-10-02
close_check: {"cmd": "python3 -m pytest -q tests/test_debt_registration_controls.py::test_delta_forum_mtp_acceptance_and_semantic_control_01", "expect": "exit_zero", "porque": "Aplicar el alcance y los controles concretos de la evidencia copiada arriba: stack/OEM y versiones fijadas, sujeto real, caso sano y negativo, resultados literales y rollback cuando haya intervención. Si faltan hardware, adjuntos, compatibilidad o permisos, imprimir could_not_run y conservar open. Un score agregado o mero estado de un dispositivo no acredita el resultado funcional. No instalar parches ni provocar fallo del host para registrar la ficha."}
---

## Registro y responsable

Registro solicitado por Luis el 2026-10-02. Responsable: coordinación de Blackbox. Trabajo o revisión pendiente; la presencia del marcador no demuestra por sí sola un defecto.

## Evidencia y alcance

Trabajo separado del ámbito de su ficha madre, conservando la fuente original. Los reportes de foro siguen sin validación local y no se convierten en recomendaciones automáticas.

### DELTA-FORUM-MTP-ACCEPTANCE-AND-SEMANTIC-CONTROL-01

[361163](https://forums.developer.nvidia.com/t/we-unlocked-nvfp4-on-the-dgx-spark-20-faster-than-awq/361163) adds a direct MTP counterexample: one owner reports Qwen3-Coder-Next NVFP4 at about 38 tok/s without MTP and about 26 tok/s with MTP, with zero acceptance; separate reports vary by model/build, and a cold restart reportedly restored speed without rebuilding. Benchmark labels also differ: speculative accepted output rate and target decode rate are distinct. The repository patches, images, scripts, screenshots and raw result files were not audited, and no matched independent correctness run appears in the thread. A later Qwen/PrismaQuant thread [367085, posts 71–74, 139 and 155–160](https://forums.developer.nvidia.com/t/introducing-prismaquant/367085/71) also reports that MTP/DFlash behavior changes with context pressure, concurrency and backend; one 50%-context-pressure test saw little difference between MTP=2 and 4, while other results changed after DFlash/SWA build changes. This supplies no universal speculative-token count.

For each pinned model/image/backend, compare MTP on/off with the same prompts, output limits, concurrency and warm/cold state. Record per-position acceptance, semantic/tool correctness, prefill and decode latency, target decode rate, user-visible rate and memory. Gate zero acceptance or failed output checks and retain the last known-good recipe for rollback; do not infer a universal NVFP4 or MTP setting from this thread.

Fuentes: tasks/backlog/FEATURE-FORUM-GB10-RUNTIME-COMPAT-01.md.

## Criterio de cierre y control negativo

Aplicar el alcance y los controles concretos de la evidencia copiada arriba: stack/OEM y versiones fijadas, sujeto real, caso sano y negativo, resultados literales y rollback cuando haya intervención. Si faltan hardware, adjuntos, compatibilidad o permisos, imprimir could_not_run y conservar open. Un score agregado o mero estado de un dispositivo no acredita el resultado funcional. No instalar parches ni provocar fallo del host para registrar la ficha.

## Estado del verificador

La ficha permanece abierta. El test selector del close_check es una especificación pendiente, no una prueba existente ni un resultado ejecutado. Implementarlo exige comprobar el sujeto y su control negativo; la existencia de archivos o esta ficha no basta para cerrar.

Conservar comandos, salida literal y could_not_run incluso cero; una ejecución skipped o inaccesible deja el cierre pendiente. Reutilizar instrumentos nativos y pruebas existentes antes de crear código.

### Evidencia de instrumento (2026-10-03)

Estado: `blocked` para aceptación MTP: los chunks Chat Completions no exponen aceptación por posición, y no hay captura backend nativa ni A/B semántico pareado. El lector SSE solo conserva evidencia de salida del cliente y no aporta esa señal. La ficha sigue abierta y el `close_check` original no cambió. Informe: `docs/evidence/BB-INSTRUMENTS-requests.md`.
