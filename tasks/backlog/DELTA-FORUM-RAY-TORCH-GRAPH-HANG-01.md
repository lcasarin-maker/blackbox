---
id: DELTA-FORUM-RAY-TORCH-GRAPH-HANG-01
kind: task
domain: VERDICT
title: "Validar forum ray torch graph hang 01"
status: open
severity: P2
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-10-02
close_check: {"cmd": "python3 -m pytest -q tests/test_debt_registration_controls.py::test_delta_forum_ray_torch_graph_hang_01", "expect": "exit_zero", "porque": "Aplicar el alcance y los controles concretos de la evidencia copiada arriba: stack/OEM y versiones fijadas, sujeto real, caso sano y negativo, resultados literales y rollback cuando haya intervención. Si faltan hardware, adjuntos, compatibilidad o permisos, imprimir could_not_run y conservar open. Un score agregado o mero estado de un dispositivo no acredita el resultado funcional. No instalar parches ni provocar fallo del host para registrar la ficha."}
---

## Registro y responsable

Registro solicitado por Luis el 2026-10-02. Responsable: coordinación de Blackbox. Trabajo o revisión pendiente; la presencia del marcador no demuestra por sí sola un defecto.

## Evidencia y alcance

Trabajo separado del ámbito de su ficha madre, conservando la fuente original. Los reportes de foro siguen sin validación local y no se convierten en recomendaciones automáticas.

**DELTA-FORUM-RAY-TORCH-GRAPH-HANG-01.** En un clúster de dos Spark, un dueño reporta que Ray/vLLM tensor-parallel perdía un nodo tras el primer prompt mientras el peer quedaba con GPU al 100% sin progreso; `--enforce-eager` alteró el síntoma y luego el autor identificó torch 2.10.0 en vez de 2.9.1 en su build, tras lo cual informó que funcionó ([358755](https://forums.developer.nvidia.com/t/358755)). No hay A/B repetido ni digest exacto para atribución independiente. Gatear combinaciones host/container Torch-CUDA-vLLM-Ray-NCCL verificadas y capturar progreso por rank/collective junto al uso GPU; 100% GPU por sí solo no prueba cuelgue. Eager es diagnóstico A/B, no default.

Fuentes: tasks/backlog/FEATURE-FORUM-GB10-RUNTIME-COMPAT-01.md.

## Criterio de cierre y control negativo

Aplicar el alcance y los controles concretos de la evidencia copiada arriba: stack/OEM y versiones fijadas, sujeto real, caso sano y negativo, resultados literales y rollback cuando haya intervención. Si faltan hardware, adjuntos, compatibilidad o permisos, imprimir could_not_run y conservar open. Un score agregado o mero estado de un dispositivo no acredita el resultado funcional. No instalar parches ni provocar fallo del host para registrar la ficha.

## Estado del verificador

La ficha permanece abierta. El test selector del close_check es una especificación pendiente, no una prueba existente ni un resultado ejecutado. Implementarlo exige comprobar el sujeto y su control negativo; la existencia de archivos o esta ficha no basta para cerrar.

Conservar comandos, salida literal y could_not_run incluso cero; una ejecución skipped o inaccesible deja el cierre pendiente. Reutilizar instrumentos nativos y pruebas existentes antes de crear código.

## Clasificación del impedimento — 2026-10-04

- Categoría principal: `workload_or_lab`.
- Impedimento: Falta reproducción local con stack/model/versión Ray-Torch fijados, comparación graph/eager y telemetría de hang; el reporte de foro no acredita causa.
- Evidencia faltante para cierre: Falta reproducción local con stack/model/versión Ray-Torch fijados, comparación graph/eager y telemetría de hang; el reporte de foro no acredita causa.
- Siguiente acción: Coordinación BB: preparar caso mínimo, watchdog seguro y logging; operador Luis: ejecutar workload canary y entregar capturas comparativas, sin provocar fallos del host. Ref explícita: tasks/backlog/DELTA-FORUM-RAY-TORCH-GRAPH-HANG-01.md y tests/test_debt_registration_controls.py. Ref explícita: tasks/backlog/DELTA-FORUM-RAY-TORCH-GRAPH-HANG-01.md y tasks/evidence/CLOSURE-CONTROLS-2026-10-03/DELTA-FORUM-RAY-TORCH-GRAPH-HANG-01-original-selector-current.log.
- Responsable del siguiente paso: Coordinación BB prepara/implementa; cuando la acción requiere root/lab/hardware, operador Luis aporta y ejecuta el sujeto indicado..
- Cierre completo accionable hoy: no. Preparación coordinable: sí.
- Evidencias de clasificación: `tasks/backlog/DELTA-FORUM-RAY-TORCH-GRAPH-HANG-01.md`, `tests/test_debt_registration_controls.py`, `tasks/evidence/OPEN-96-CLASSIFICATION-2026-10-04/batches/batch_06.json`, `tasks/evidence/CLOSURE-CONTROLS-2026-10-03/DELTA-FORUM-RAY-TORCH-GRAPH-HANG-01-original-selector-current.log`.
- Impedimentos de inspección: 0. El criterio original permanece intacto; esta clasificación conserva la ficha abierta.
