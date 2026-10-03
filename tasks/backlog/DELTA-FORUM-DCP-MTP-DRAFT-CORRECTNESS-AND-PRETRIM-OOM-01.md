---
id: DELTA-FORUM-DCP-MTP-DRAFT-CORRECTNESS-AND-PRETRIM-OOM-01
kind: task
domain: VERDICT
title: "Validar forum dcp mtp draft correctness and pretrim oom 01"
status: open
severity: P2
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-10-02
close_check: {"cmd": "python3 -m pytest -q tests/test_debt_registration_controls.py::test_delta_forum_dcp_mtp_draft_correctness_and_pretrim_oom_01", "expect": "exit_zero", "porque": "Aplicar el alcance y los controles concretos de la evidencia copiada arriba: stack/OEM y versiones fijadas, sujeto real, caso sano y negativo, resultados literales y rollback cuando haya intervención. Si faltan hardware, adjuntos, compatibilidad o permisos, imprimir could_not_run y conservar open. Un score agregado o mero estado de un dispositivo no acredita el resultado funcional. No instalar parches ni provocar fallo del host para registrar la ficha."}
---

## Registro y responsable

Registro solicitado por Luis el 2026-10-02. Responsable: coordinación de Blackbox. Trabajo o revisión pendiente; la presencia del marcador no demuestra por sí sola un defecto.

## Evidencia y alcance

Trabajo separado del ámbito de su ficha madre, conservando la fuente original. Los reportes de foro siguen sin validación local y no se convierten en recomendaciones automáticas.

[375416](https://forums.developer.nvidia.com/t/375416) reports a correctness failure in a community vLLM V1 speculative/MTP path under DCP4: draft parallel configuration reportedly omitted `decode_context_parallel_size`, leaving draft attention in DCP1 while KV/metadata were DCP-sharded. The operator’s tensor-level probe reportedly found no q all-gather/LSE merge and all-zero attention on 3/4 ranks; TP all-reduce then made corrupted state identical across ranks, so a cross-rank equality check passed. The operator reports a code fix and stronger GLM-5.2 MTP3/4 acceptance/throughput on 4×GB10, but the patch/repositories were not audited or run in BB. Add a pinned-image regression that asserts draft effective DCP size, verifies gather/merge and nonzero partial outputs against a DCP1/reference control, then checks coherent deterministic output and per-position acceptance across repeated prompts; do not rely on rank consensus or acceptance alone. The same thread contains a second operator’s NV_ERR_NO_MEMORY before an after-load trim hook; first operator’s memory advice did not resolve that case, so preserve a separate pre-trim load/host-headroom test and do not generalize one configuration’s 128K success. **DELTA-FORUM-DCP-MTP-DRAFT-CORRECTNESS-AND-PRETRIM-OOM-01**.

Fuentes: tasks/backlog/FEATURE-FORUM-GB10-RUNTIME-COMPAT-01.md.

## Criterio de cierre y control negativo

Aplicar el alcance y los controles concretos de la evidencia copiada arriba: stack/OEM y versiones fijadas, sujeto real, caso sano y negativo, resultados literales y rollback cuando haya intervención. Si faltan hardware, adjuntos, compatibilidad o permisos, imprimir could_not_run y conservar open. Un score agregado o mero estado de un dispositivo no acredita el resultado funcional. No instalar parches ni provocar fallo del host para registrar la ficha.

## Estado del verificador

La ficha permanece abierta. El test selector del close_check es una especificación pendiente, no una prueba existente ni un resultado ejecutado. Implementarlo exige comprobar el sujeto y su control negativo; la existencia de archivos o esta ficha no basta para cerrar.

Conservar comandos, salida literal y could_not_run incluso cero; una ejecución skipped o inaccesible deja el cierre pendiente. Reutilizar instrumentos nativos y pruebas existentes antes de crear código.
