---
id: DELTA-FORUM-MUSE-GLIMMER-DFLASH-MAX-SEQS-GATE-01
kind: task
domain: VERDICT
title: "Validar forum muse glimmer dflash max seqs gate 01"
status: open
severity: P2
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-10-02
close_check: {"cmd": "python3 -m pytest -q tests/test_debt_registration_controls.py::test_delta_forum_muse_glimmer_dflash_max_seqs_gate_01", "expect": "exit_zero", "porque": "Aplicar el alcance y los controles concretos de la evidencia copiada arriba: stack/OEM y versiones fijadas, sujeto real, caso sano y negativo, resultados literales y rollback cuando haya intervención. Si faltan hardware, adjuntos, compatibilidad o permisos, imprimir could_not_run y conservar open. Un score agregado o mero estado de un dispositivo no acredita el resultado funcional. No instalar parches ni provocar fallo del host para registrar la ficha."}
---

## Registro y responsable

Registro solicitado por Luis el 2026-10-02. Responsable: coordinación de Blackbox. Trabajo o revisión pendiente; la presencia del marcador no demuestra por sí sola un defecto.

## Evidencia y alcance

Trabajo separado del ámbito de su ficha madre, conservando la fuente original. Los reportes de foro siguen sin validación local y no se convierten en recomendaciones automáticas.

[379722](https://forums.developer.nvidia.com/t/379722) adds Muse-Glimmer/DFlash admission details. An initial NVIDIA/vLLM image reportedly failed because the draft class was missing; a later owner says their DFlash-enabled vLLM muse-glimmer tag only worked with `max_num_seqs <= 32`, reproduced on their setup. A GB10 report says a patched stack completed an 84-scenario tool eval but still had prompt-injection/hallucination and long-horizon failures; other BFCL measurements swung sharply when the prompt required parallel same-turn calls. Repositories, PRs and benchmark captures were not audited. For the pinned image/model/parser/template, preflight draft class resolution and run an A/B at the reported 32/33 sequence boundary, including bounded resource/CPU/GPU tests and semantic canaries for single-tool, parallel calls, token truncation and untrusted tool output. Treat this as a candidate compatibility limit for the exact branch; never set a universal DFlash concurrency cap or infer product safety from an aggregate benchmark score. **DELTA-FORUM-MUSE-GLIMMER-DFLASH-MAX-SEQS-GATE-01**.

Fuentes: tasks/backlog/FEATURE-FORUM-GB10-RUNTIME-COMPAT-01.md.

## Criterio de cierre y control negativo

Aplicar el alcance y los controles concretos de la evidencia copiada arriba: stack/OEM y versiones fijadas, sujeto real, caso sano y negativo, resultados literales y rollback cuando haya intervención. Si faltan hardware, adjuntos, compatibilidad o permisos, imprimir could_not_run y conservar open. Un score agregado o mero estado de un dispositivo no acredita el resultado funcional. No instalar parches ni provocar fallo del host para registrar la ficha.

## Estado del verificador

La ficha permanece abierta. El test selector del close_check es una especificación pendiente, no una prueba existente ni un resultado ejecutado. Implementarlo exige comprobar el sujeto y su control negativo; la existencia de archivos o esta ficha no basta para cerrar.

Conservar comandos, salida literal y could_not_run incluso cero; una ejecución skipped o inaccesible deja el cierre pendiente. Reutilizar instrumentos nativos y pruebas existentes antes de crear código.
## Evaluación de instrumentos 2026-10-03

Reusa `tools/chat_sse_capture.py` para conservar deltas/finish del cliente, pero no valida resolución de draft class, límite de concurrencia, presión de recursos ni semántica/inyección de tools. No existe captura local de los tags/PR citados ni del borde 32/33. Estado `deferred_lab`: fijar imagen/modelo/parser/template, probar carga acotada en 32 y 33 y controles semánticos/negativos antes de proponer un límite específico; sin universalizar el cap del hilo.

## Clasificación del impedimento — 2026-10-04

- Categoría principal: `workload_or_lab`.
- Impedimento: No hay captura de concurrency sweep del build/modelo Glimmer/dFlash con max_seqs efectivo.
- Evidencia faltante para cierre: Build y modelo exactos; concurrency sweep; latencia/throughput/memoria/calidad; control sin dFlash y rollback.
- Siguiente acción: Solicitar benchmark en stack fijado con sweep de secuencias, medidas de latencia/throughput/calidad y control sin dFlash; usar selector actual al recibir recibos.
- Responsable del siguiente paso: BB; operador Luis para workload/lab.
- Cierre completo accionable hoy: no. Preparación coordinable: sí.
- Evidencias de clasificación: `tasks/backlog/DELTA-FORUM-MUSE-GLIMMER-DFLASH-MAX-SEQS-GATE-01.md`, `tools/runtime_batch02_controls.py`, `tests/test_debt_registration_controls.py`.
- Impedimentos de inspección: 0. El criterio original permanece intacto; esta clasificación conserva la ficha abierta.
