---
id: DELTA-FORUM-KV-QUANT-METRIC-PROVENANCE-GATE-01
kind: task
domain: VERDICT
title: "Validar forum kv quant metric provenance gate 01"
status: open
severity: P2
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-10-02
close_check: {"cmd": "python3 -m pytest -q tests/test_debt_registration_controls.py::test_delta_forum_kv_quant_metric_provenance_gate_01", "expect": "exit_zero", "porque": "Aplicar el alcance y los controles concretos de la evidencia copiada arriba: stack/OEM y versiones fijadas, sujeto real, caso sano y negativo, resultados literales y rollback cuando haya intervención. Si faltan hardware, adjuntos, compatibilidad o permisos, imprimir could_not_run y conservar open. Un score agregado o mero estado de un dispositivo no acredita el resultado funcional. No instalar parches ni provocar fallo del host para registrar la ficha."}
---

## Registro y responsable

Registro solicitado por Luis el 2026-10-02. Responsable: coordinación de Blackbox. Trabajo o revisión pendiente; la presencia del marcador no demuestra por sí sola un defecto.

## Evidencia y alcance

Trabajo separado del ámbito de su ficha madre, conservando la fuente original. Los reportes de foro siguen sin validación local y no se convierten en recomendaciones automáticas.

### DELTA-FORUM-KV-QUANT-METRIC-PROVENANCE-GATE-01

[364736](https://forums.developer.nvidia.com/t/why-turboquant-saves-dgx-twice/364736) includes a material correction: the author retracted a claim of 92.5% q4_0 prefill collapse and higher memory use after identifying that the original memory measurement used process RSS instead of the llama.cpp KV buffer. The corrected owner report gives 216 MiB q4_0 versus 768 MiB f16 KV, with no prefill cliff and about 37% lower decode rate at 110K context. Later TurboQuant/RotorQuant timings, quality and kernel claims vary by fork/config and remain unverified; external repositories and result files were not audited.

Keep RSS, cgroup, host available memory/swap, allocator residency and framework KV bytes as separately labeled counters. Compare the exact K/V mode, backend, model, context and concurrency with output correctness and prefill/decode measurements. A KV capacity win does not establish faster or correct generation; the reported values are not universal thresholds.

Fuentes: tasks/backlog/FEATURE-FORUM-GB10-RUNTIME-COMPAT-01.md.

## Criterio de cierre y control negativo

Aplicar el alcance y los controles concretos de la evidencia copiada arriba: stack/OEM y versiones fijadas, sujeto real, caso sano y negativo, resultados literales y rollback cuando haya intervención. Si faltan hardware, adjuntos, compatibilidad o permisos, imprimir could_not_run y conservar open. Un score agregado o mero estado de un dispositivo no acredita el resultado funcional. No instalar parches ni provocar fallo del host para registrar la ficha.

## Estado del verificador

La ficha permanece abierta. El test selector del close_check es una especificación pendiente, no una prueba existente ni un resultado ejecutado. Implementarlo exige comprobar el sujeto y su control negativo; la existencia de archivos o esta ficha no basta para cerrar.

Conservar comandos, salida literal y could_not_run incluso cero; una ejecución skipped o inaccesible deja el cierre pendiente. Reutilizar instrumentos nativos y pruebas existentes antes de crear código.
