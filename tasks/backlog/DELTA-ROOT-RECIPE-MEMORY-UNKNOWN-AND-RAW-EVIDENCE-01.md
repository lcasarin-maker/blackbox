---
id: DELTA-ROOT-RECIPE-MEMORY-UNKNOWN-AND-RAW-EVIDENCE-01
kind: task
domain: VERDICT
title: "Validar root recipe memory unknown and raw evidence 01"
status: open
severity: P2
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-10-02
close_check: {"cmd": "python3 -m pytest -q tests/test_debt_registration_controls.py::test_delta_root_recipe_memory_unknown_and_raw_evidence_01", "expect": "exit_zero", "porque": "Aplicar el alcance y los controles concretos de la evidencia copiada arriba: stack/OEM y versiones fijadas, sujeto real, caso sano y negativo, resultados literales y rollback cuando haya intervención. Si faltan hardware, adjuntos, compatibilidad o permisos, imprimir could_not_run y conservar open. Un score agregado o mero estado de un dispositivo no acredita el resultado funcional. No instalar parches ni provocar fallo del host para registrar la ficha."}
---

## Registro y responsable

Registro solicitado por Luis el 2026-10-02. Responsable: coordinación de Blackbox. Trabajo o revisión pendiente; la presencia del marcador no demuestra por sí sola un defecto.

## Evidencia y alcance

Trabajo separado del ámbito de su ficha madre, conservando la fuente original. Los reportes de foro siguen sin validación local y no se convierten en recomendaciones automáticas.

### DELTA-ROOT-RECIPE-MEMORY-UNKNOWN-AND-RAW-EVIDENCE-01

Fuentes: https://forums.developer.nvidia.com/t/360319/50 y /14–22, /118.

Ejemplo llama.cpp post50 imprime DGX Spark fit:YES usando solo1.58GBweights, pero inmediatamente dice arquitectura ausente y estimaciónKV unavailable; log real agrega896MiBKV y buffers. Posts14–22 vLLMprefixcachecrash/hang tras actualización admite commit previo y mod posterior; throughput positivo de otras máquinas no prueba este workflow.

Acción: Presupuesto de admisión incluye weights, KV, staging, graphs, draft, buffers y reservahost por etapa y runtime. Campos desconocidos impiden afirmar seguro; exigir canario funcional efectivo o perfil medido compatible. Reusar exportaciónconsolidada de receta/comando/resultados de sparkrun como evidencia candidata con versión y digest, no crear otro launcher. Evitar pipupgrade sinpin en cada arranque; validar baseimageefectiva y rollback.

Cierre: Fixture weightsfitperoKVdesconocido reporta unknown y no promete protección. Comparación por hardware/topología/digests/checkpoint/params y rawresults con workload real posterior a warmup; cambio de backend validado funcionalmente y rollback disponible.

Riesgos: Estimaciones y tests de comunidad no sustituyen admisión/soak del host; Exportador/código externo sin auditoría.

Fuentes: tasks/backlog/FEATURE-FORUM-GB10-RUNTIME-COMPAT-01.md.

## Criterio de cierre y control negativo

Aplicar el alcance y los controles concretos de la evidencia copiada arriba: stack/OEM y versiones fijadas, sujeto real, caso sano y negativo, resultados literales y rollback cuando haya intervención. Si faltan hardware, adjuntos, compatibilidad o permisos, imprimir could_not_run y conservar open. Un score agregado o mero estado de un dispositivo no acredita el resultado funcional. No instalar parches ni provocar fallo del host para registrar la ficha.

## Estado del verificador

La ficha permanece abierta. El test selector del close_check es una especificación pendiente, no una prueba existente ni un resultado ejecutado. Implementarlo exige comprobar el sujeto y su control negativo; la existencia de archivos o esta ficha no basta para cerrar.

Conservar comandos, salida literal y could_not_run incluso cero; una ejecución skipped o inaccesible deja el cierre pendiente. Reutilizar instrumentos nativos y pruebas existentes antes de crear código.

## Diagnóstico disponible

`python3 -m tools.recipe_memory` reutiliza `tools.memory_profile.capture` y conserva la captura host completa, sus estados de lectura y un digest del registro que no autentica el origen. Los términos de receta vienen del invocador y se etiquetan `caller_supplied_unverified`; faltantes o desconocidos producen `unknown`, nunca cero. `comparison_only` compara esos valores declarados con MemAvailable, sin afirmar admisión ni protección real, y no prueba workload, canario funcional, compatibilidad, soak ni rollback.

La ejecución local sin términos declarados quedó como `unknown`, rc=2, preservando la captura raw en `tasks/evidence/DELTA-ROOT-RECIPE-MEMORY-UNKNOWN-AND-RAW-EVIDENCE-01/prototype-capture.json`; el comando y hash están en `tasks/evidence/LUNA-98-2026-10-03/batch-03-prototype-runs.json`. No se atribuye una cifra de memoria a la receta comunitaria sin workload real.

## Clasificación del impedimento — 2026-10-04

- Categoría principal: `workload_or_lab`.
- Impedimento: El prototipo de captura no acredita presupuesto KV/staging/graphs ni corrección/soak real posterior a warmup.
- Evidencia faltante para cierre: captura consolidada de receta con digest/params y raw results de workload real; perfil por topología; rollback funcional
- Siguiente acción: Usar exportación existente de receta/sparkrun en canario compatible y medir presupuesto por etapa más corrección/soak; dejar unknown ante campos faltantes.
- Responsable del siguiente paso: coordinación BB prepara; operador Luis ejecuta root/lab.
- Cierre completo accionable hoy: no. Preparación coordinable: sin acción adicional demostrada en esta revisión.
- Evidencias de clasificación: `tasks/backlog/DELTA-ROOT-RECIPE-MEMORY-UNKNOWN-AND-RAW-EVIDENCE-01.md`, `tasks/evidence/OPEN-96-CLASSIFICATION-2026-10-04/batches/batch_02.json`, `tasks/evidence/DELTA-ROOT-RECIPE-MEMORY-UNKNOWN-AND-RAW-EVIDENCE-01/prototype-capture.json`.
- Impedimentos de inspección: 0. El criterio original permanece intacto; esta clasificación conserva la ficha abierta.
