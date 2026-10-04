---
id: DELTA-FORUM-DCP4-DECODE-STARVATION-FAIR-SCHEDULER-01
kind: task
domain: VERDICT
title: "Validar forum dcp4 decode starvation fair scheduler 01"
status: open
severity: P2
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-10-02
close_check: {"cmd": "python3 -m pytest -q tests/test_debt_registration_controls.py::test_delta_forum_dcp4_decode_starvation_fair_scheduler_01", "expect": "exit_zero", "porque": "Aplicar el alcance y los controles concretos de la evidencia copiada arriba: stack/OEM y versiones fijadas, sujeto real, caso sano y negativo, resultados literales y rollback cuando haya intervención. Si faltan hardware, adjuntos, compatibilidad o permisos, imprimir could_not_run y conservar open. Un score agregado o mero estado de un dispositivo no acredita el resultado funcional. No instalar parches ni provocar fallo del host para registrar la ficha."}
---

## Registro y responsable

Registro solicitado por Luis el 2026-10-02. Responsable: coordinación de Blackbox. Trabajo o revisión pendiente; la presencia del marcador no demuestra por sí sola un defecto.

## Evidencia y alcance

Trabajo separado del ámbito de su ficha madre, conservando la fuente original. Los reportes de foro siguen sin validación local y no se convierten en recomendaciones automáticas.

**DELTA-FORUM-DCP4-DECODE-STARVATION-FAIR-SCHEDULER-01.** En GLM-5.2 sobre TP8/DCP4 en ocho GB10, un operador reporta que prefills simultáneos hacen caer decode activo a 0–0.2 tok/s hasta que termina el prefill; describe un parche scheduler decode-aware con budget de prefill 16,384 tokens en idle y 1,024 bajo decode activo, máximo un long-prefill por step y rotación round-robin. El autor reporta para vLLM `local-inference-lab` commit `a663653d8cf3a66ee3c0060aea8c2fd28e3f1362`: 3 tests nuevos, 7 regresiones, ruff y 4 checks CLI pasando; prueba de hardware reportada: 4/4 prefills terminan, máximo stall 1.64 s, decode 2.74 tok/s bajo presión (no 0.0–0.2), luego 26 tok/s al acabar; idle prefill 831.6 t/s y pressure prefill 735.8 t/s ([376831, posts 7, 10–11](https://forums.developer.nvidia.com/t/376831/10)). Evidencia del foro; el patch adjunto y repo externo no se auditaron ni ejecutaron en BB. Evaluar como alternativa específica a DCP4, comparar fairness y throughput en la revisión fijada del runtime con un decode largo + 4 prefills ~8K, además de calidad/errores, máximos stalls y todos los completions; rollback configurado con `ENABLE_DECODE_AWARE_PREFILL=0`. No reclamar aumento de capacidad ni adoptar budgets como universales.

Fuentes: tasks/backlog/FEATURE-FORUM-GB10-RUNTIME-COMPAT-01.md.

## Criterio de cierre y control negativo

Aplicar el alcance y los controles concretos de la evidencia copiada arriba: stack/OEM y versiones fijadas, sujeto real, caso sano y negativo, resultados literales y rollback cuando haya intervención. Si faltan hardware, adjuntos, compatibilidad o permisos, imprimir could_not_run y conservar open. Un score agregado o mero estado de un dispositivo no acredita el resultado funcional. No instalar parches ni provocar fallo del host para registrar la ficha.

## Estado del verificador

La ficha permanece abierta. El test selector del close_check es una especificación pendiente, no una prueba existente ni un resultado ejecutado. Implementarlo exige comprobar el sujeto y su control negativo; la existencia de archivos o esta ficha no basta para cerrar.

Conservar comandos, salida literal y could_not_run incluso cero; una ejecución skipped o inaccesible deja el cierre pendiente. Reutilizar instrumentos nativos y pruebas existentes antes de crear código.

## Evaluación de instrumentos 2026-10-03

Reusa `tools/provider_trace.py` únicamente para la ruta request/provider/worker; no observa cola por paso, scheduler DCP4 ni equidad entre decode largo y prefill. No existe traza local de la carga descrita. Siguiente paso `deferred_lab`: stack TP8/DCP4 fijado, secuencia con decode largo y cuatro prefills concurrentes, orden/espera por cola, tokens/s, throughput, stalls, errores, completitud y corrección, con control stock y rollback. No se ejecutó workload.

## Clasificación del impedimento — 2026-10-04

- Categoría principal: `workload_or_lab`.
- Impedimento: La ficha dice que provider_trace no observa cola por paso/scheduler; no hay traza de la carga TP8 descrita.
- Evidencia faltante para cierre: Stack TP8/DCP4 y digest fijados; decode largo + cuatro prefills; orden/espera, throughput, stalls, errores/completitud/corrección; control stock y rollback.
- Siguiente acción: Preparar una captura temporal de cola por paso solo si el runtime fijado la expone; de lo contrario, solicitar corrida de decode largo + cuatro prefills, stock vs flag de rollback y registros de stalls/throughput en laboratorio.
- Responsable del siguiente paso: BB; operador Luis para workload/lab.
- Cierre completo accionable hoy: no. Preparación coordinable: sí.
- Evidencias de clasificación: `tasks/backlog/DELTA-FORUM-DCP4-DECODE-STARVATION-FAIR-SCHEDULER-01.md`, `tools/provider_trace.py`, `tools/runtime_batch01_controls.py`.
- Impedimentos de inspección: 0. El criterio original permanece intacto; esta clasificación conserva la ficha abierta.
