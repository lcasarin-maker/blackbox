---
id: DELTA-ROOT-RAY-MULTIENGINE-RANK-PROGRESS-01
kind: task
domain: VERDICT
title: "Validar root ray multiengine rank progress 01"
status: open
severity: P2
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-10-02
close_check: {"cmd": "python3 -m pytest -q tests/test_debt_registration_controls.py::test_delta_root_ray_multiengine_rank_progress_01", "expect": "exit_zero", "porque": "Aplicar el alcance y los controles concretos de la evidencia copiada arriba: stack/OEM y versiones fijadas, sujeto real, caso sano y negativo, resultados literales y rollback cuando haya intervención. Si faltan hardware, adjuntos, compatibilidad o permisos, imprimir could_not_run y conservar open. Un score agregado o mero estado de un dispositivo no acredita el resultado funcional. No instalar parches ni provocar fallo del host para registrar la ficha."}
---

## Registro y responsable

Registro solicitado por Luis el 2026-10-02. Responsable: coordinación de Blackbox. Trabajo o revisión pendiente; la presencia del marcador no demuestra por sí sola un defecto.

## Evidencia y alcance

Trabajo separado del ámbito de su ficha madre, conservando la fuente original. Los reportes de foro siguen sin validación local y no se convierten en recomendaciones automáticas.

### DELTA-ROOT-RAY-MULTIENGINE-RANK-PROGRESS-01

Fuentes: https://forums.developer.nvidia.com/t/377396.

Post101 relata dos vLLM dentro del mismo cluster Ray con NCCL atascado, sin logs ni versión; Distributed mp se propone, sin A/B demostrado.

Acción: Antes de admitir segundo motor, verificar identidades, presupuesto agregado y progreso real de cada rank en ambos motores; medir colectivo y petición real, no solo disponibilidad Ray. Fijar digest y configuración; aislar recursos y recuperación al motor afectado.

Cierre: Fixture un motor sano y otro sin progreso colectivo; detectar el afectado y mantener al primero. A/B efectivo y rollback de cambios de executor.

Riesgos: Relato único sin versión; mp es propuesta, no fix confirmado.

Fuentes: tasks/backlog/FEATURE-FORUM-GB10-RUNTIME-COMPAT-01.md.

## Criterio de cierre y control negativo

Aplicar el alcance y los controles concretos de la evidencia copiada arriba: stack/OEM y versiones fijadas, sujeto real, caso sano y negativo, resultados literales y rollback cuando haya intervención. Si faltan hardware, adjuntos, compatibilidad o permisos, imprimir could_not_run y conservar open. Un score agregado o mero estado de un dispositivo no acredita el resultado funcional. No instalar parches ni provocar fallo del host para registrar la ficha.

## Estado del verificador

La ficha permanece abierta. El test selector del close_check es una especificación pendiente, no una prueba existente ni un resultado ejecutado. Implementarlo exige comprobar el sujeto y su control negativo; la existencia de archivos o esta ficha no basta para cerrar.

Conservar comandos, salida literal y could_not_run incluso cero; una ejecución skipped o inaccesible deja el cierre pendiente. Reutilizar instrumentos nativos y pruebas existentes antes de crear código.
