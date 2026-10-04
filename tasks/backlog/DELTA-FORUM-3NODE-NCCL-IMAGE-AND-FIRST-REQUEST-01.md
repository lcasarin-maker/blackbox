---
id: DELTA-FORUM-3NODE-NCCL-IMAGE-AND-FIRST-REQUEST-01
kind: task
domain: VERDICT
title: "Validar forum 3node nccl image and first request 01"
status: open
severity: P2
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-10-02
close_check: {"cmd": "python3 -m pytest -q tests/test_debt_registration_controls.py::test_delta_forum_3node_nccl_image_and_first_request_01", "expect": "exit_zero", "porque": "Aplicar el alcance y los controles concretos de la evidencia copiada arriba: stack/OEM y versiones fijadas, sujeto real, caso sano y negativo, resultados literales y rollback cuando haya intervención. Si faltan hardware, adjuntos, compatibilidad o permisos, imprimir could_not_run y conservar open. Un score agregado o mero estado de un dispositivo no acredita el resultado funcional. No instalar parches ni provocar fallo del host para registrar la ficha."}
---

## Registro y responsable

Registro solicitado por Luis el 2026-10-02. Responsable: coordinación de Blackbox. Trabajo o revisión pendiente; la presencia del marcador no demuestra por sí sola un defecto.

## Evidencia y alcance

Trabajo separado del ámbito de su ficha madre, conservando la fuente original. Los reportes de foro siguen sin validación local y no se convierten en recomendaciones automáticas.

**DELTA-FORUM-3NODE-NCCL-IMAGE-AND-FIRST-REQUEST-01.** En una malla de tres Spark con PP, un operador reporta SIGTERM silencioso del worker en la primera inferencia usando el contenedor `vllm-node` con NCCL estándar; en el ensayo incremental, varias variables NCCL, Ray, allocator y loader no cambiaron el fallo. El operador reporta éxito posterior con imagen TF5 que llevaba NCCL de mesh; el mantenedor responde que la funcionalidad ya se integró en NCCL main y que la receta se actualizó ([365296, posts 15–16](https://forums.developer.nvidia.com/t/365296/15)). Validar build/image digest/NCCL por rank y una inferencia PP entre etapas en el topology real; load/HTTP ready no basta. Las fuentes externas no fueron auditadas y la corrección es declarada por usuarios; no tratar el caso como bug driver ni trasladar el umbral 0.85 de Grace Hopper a Spark.

Fuentes: tasks/backlog/FEATURE-FORUM-GB10-RUNTIME-COMPAT-01.md.

## Criterio de cierre y control negativo

Aplicar el alcance y los controles concretos de la evidencia copiada arriba: stack/OEM y versiones fijadas, sujeto real, caso sano y negativo, resultados literales y rollback cuando haya intervención. Si faltan hardware, adjuntos, compatibilidad o permisos, imprimir could_not_run y conservar open. Un score agregado o mero estado de un dispositivo no acredita el resultado funcional. No instalar parches ni provocar fallo del host para registrar la ficha.

## Estado del verificador

La ficha permanece abierta. El test selector del close_check es una especificación pendiente, no una prueba existente ni un resultado ejecutado. Implementarlo exige comprobar el sujeto y su control negativo; la existencia de archivos o esta ficha no basta para cerrar.

Conservar comandos, salida literal y could_not_run incluso cero; una ejecución skipped o inaccesible deja el cierre pendiente. Reutilizar instrumentos nativos y pruebas existentes antes de crear código.

## Avance de instrumentación 2026-10-03

`tools.host_diagnostics` ahora captura MTU de interfaz, estado de enlace disponible y binding PCI/driver con consultas nativas y sysfs. El inventario no observa imagen NCCL por rank ni ejecuta primera inferencia; la captura real tuvo `could_not_run=19` y `ip -j link` quedó inaccesible. Evidencia: [BB-INSTRUMENTS-network](../../docs/evidence/BB-INSTRUMENTS-network.md). La ficha permanece abierta; `close_check` y `status` no cambiaron.

## Clasificación del impedimento — 2026-10-04

- Categoría principal: `workload_or_lab`.
- Impedimento: Falta sujeto real de tres nodos, digest/image y NCCL por rank, primera inferencia PP, control sano/negativo y salida literal; inventario local solo vio MTU/link y reportó CNR=19.
- Evidencia faltante para cierre: Falta sujeto real de tres nodos, digest/image y NCCL por rank, primera inferencia PP, control sano/negativo y salida literal; inventario local solo vio MTU/link y reportó CNR=19.
- Siguiente acción: Coordinación BB: preparar protocolo y captura rank/image-bound; operador Luis: aportar canario Spark de tres nodos y ejecutar primera inferencia con rollback. Ref explícita: tasks/backlog/DELTA-FORUM-3NODE-NCCL-IMAGE-AND-FIRST-REQUEST-01.md y tests/test_debt_registration_controls.py. Ref explícita: tasks/backlog/DELTA-FORUM-3NODE-NCCL-IMAGE-AND-FIRST-REQUEST-01.md y tasks/evidence/CLOSURE-CONTROLS-2026-10-03/DELTA-FORUM-3NODE-NCCL-IMAGE-AND-FIRST-REQUEST-01-original-selector-current.log.
- Responsable del siguiente paso: Coordinación BB prepara/implementa; cuando la acción requiere root/lab/hardware, operador Luis aporta y ejecuta el sujeto indicado..
- Cierre completo accionable hoy: no. Preparación coordinable: sí.
- Evidencias de clasificación: `tasks/backlog/DELTA-FORUM-3NODE-NCCL-IMAGE-AND-FIRST-REQUEST-01.md`, `docs/evidence/BB-INSTRUMENTS-network.md`, `tests/test_debt_registration_controls.py`, `tasks/evidence/OPEN-96-CLASSIFICATION-2026-10-04/batches/batch_00.json`, `tasks/evidence/CLOSURE-CONTROLS-2026-10-03/DELTA-FORUM-3NODE-NCCL-IMAGE-AND-FIRST-REQUEST-01-original-selector-current.log`.
- Impedimentos de inspección: 0. El criterio original permanece intacto; esta clasificación conserva la ficha abierta.
