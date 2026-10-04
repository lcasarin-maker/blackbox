---
id: DELTA-FORUM-QWEN-COLD-COMPILE-OOM-01
kind: task
domain: VERDICT
title: "Validar forum qwen cold compile oom 01"
status: open
severity: P2
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-10-02
close_check: {"cmd": "python3 -m pytest -q tests/test_debt_registration_controls.py::test_delta_forum_qwen_cold_compile_oom_01", "expect": "exit_zero", "porque": "Aplicar el alcance y los controles concretos de la evidencia copiada arriba: stack/OEM y versiones fijadas, sujeto real, caso sano y negativo, resultados literales y rollback cuando haya intervención. Si faltan hardware, adjuntos, compatibilidad o permisos, imprimir could_not_run y conservar open. Un score agregado o mero estado de un dispositivo no acredita el resultado funcional. No instalar parches ni provocar fallo del host para registrar la ficha."}
---

## Registro y responsable

Registro solicitado por Luis el 2026-10-02. Responsable: coordinación de Blackbox. Trabajo o revisión pendiente; la presencia del marcador no demuestra por sí sola un defecto.

## Evidencia y alcance

Trabajo separado del ámbito de su ficha madre, conservando la fuente original. Los reportes de foro siguen sin validación local y no se convierten en recomendaciones automáticas.

**DELTA-FORUM-QWEN-COLD-COMPILE-OOM-01.** En el primer arranque de Qwen3.8-Flash-Next FP8 con imagen oficial vLLM `qwen38-flash-next` y TP2 en dos Spark, un operador informa que el `torch.compile`/Inductor predeterminado agota memoria en ambos nodos, pierde SSH/ICMP y requiere power-cycle; eager con compilation mode 0 permite arrancar, más lento ([381228, post 64](https://forums.developer.nvidia.com/t/381228/64)). El relato no incluye versión exacta de kernel/driver/torch y los logs adjuntos no se han revisado. Probar cold-start con el stack exacto, medir UMA/PSI y estado remoto por rank, preservar log fuera del host y bloquear la segunda etapa si el canary ya pierde headroom. Eager es fallback solo tras A/B del mismo stack; `gpu_memory_utilization=0.82` reportado no es umbral universal.

Fuentes: tasks/backlog/FEATURE-1358-CGROUP-05-CUELGUES.md.

## Criterio de cierre y control negativo

Aplicar el alcance y los controles concretos de la evidencia copiada arriba: stack/OEM y versiones fijadas, sujeto real, caso sano y negativo, resultados literales y rollback cuando haya intervención. Si faltan hardware, adjuntos, compatibilidad o permisos, imprimir could_not_run y conservar open. Un score agregado o mero estado de un dispositivo no acredita el resultado funcional. No instalar parches ni provocar fallo del host para registrar la ficha.

## Estado del verificador

La ficha permanece abierta. El test selector del close_check es una especificación pendiente, no una prueba existente ni un resultado ejecutado. Implementarlo exige comprobar el sujeto y su control negativo; la existencia de archivos o esta ficha no basta para cerrar.

Conservar comandos, salida literal y could_not_run incluso cero; una ejecución skipped o inaccesible deja el cierre pendiente. Reutilizar instrumentos nativos y pruebas existentes antes de crear código.
## Evaluación de instrumentos 2026-10-03

Reusa `tools/memory_profile.py`/`tools/atom_gpu_telemetry.py` para observación de memoria/PSI del host, pero no hay series por etapa/rank ni logs de compilación adjuntos de esta reproducción; tampoco se correlaciona pérdida de acceso remoto. Estado `deferred_lab`: cold-start del stack exacto con captura externa por nodo/rank, headroom y control eager en el mismo stack. No se compiló ni se provocó presión/OOM.

## Clasificación del impedimento — 2026-10-04

- Categoría principal: `workload_or_lab`.
- Impedimento: Muestreo general de memoria/PSI no contiene series por etapa/rank ni logs de compilación de la reproducción; pérdida de acceso remoto tampoco está correlacionada.
- Evidencia faltante para cierre: Muestreo general de memoria/PSI no contiene series por etapa/rank ni logs de compilación de la reproducción; pérdida de acceso remoto tampoco está correlacionada.
- Siguiente acción: Coordinación BB: preparar límites y telemetría preflight; operador Luis: ejecutar compilación fría acotada sólo en lab canary con captura externa y rollback. Ref explícita: tasks/backlog/DELTA-FORUM-QWEN-COLD-COMPILE-OOM-01.md y tests/test_debt_registration_controls.py. Ref explícita: tasks/backlog/DELTA-FORUM-QWEN-COLD-COMPILE-OOM-01.md y tasks/evidence/CLOSURE-CONTROLS-2026-10-03/DELTA-FORUM-QWEN-COLD-COMPILE-OOM-01-original-selector-current.log.
- Responsable del siguiente paso: Coordinación BB prepara/implementa; cuando la acción requiere root/lab/hardware, operador Luis aporta y ejecuta el sujeto indicado..
- Cierre completo accionable hoy: no. Preparación coordinable: sí.
- Evidencias de clasificación: `tasks/backlog/DELTA-FORUM-QWEN-COLD-COMPILE-OOM-01.md`, `tests/test_debt_registration_controls.py`, `tasks/evidence/OPEN-96-CLASSIFICATION-2026-10-04/batches/batch_09.json`, `tasks/evidence/CLOSURE-CONTROLS-2026-10-03/DELTA-FORUM-QWEN-COLD-COMPILE-OOM-01-original-selector-current.log`.
- Impedimentos de inspección: 0. El criterio original permanece intacto; esta clasificación conserva la ficha abierta.
