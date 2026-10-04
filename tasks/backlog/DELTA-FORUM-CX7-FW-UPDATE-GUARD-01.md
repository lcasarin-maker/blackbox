---
id: DELTA-FORUM-CX7-FW-UPDATE-GUARD-01
kind: task
domain: VERDICT
title: "Validar forum cx7 fw update guard 01"
status: open
severity: P2
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-10-02
close_check: {"cmd": "python3 -m pytest -q tests/test_debt_registration_controls.py::test_delta_forum_cx7_fw_update_guard_01", "expect": "exit_zero", "porque": "Aplicar el alcance y los controles concretos de la evidencia copiada arriba: stack/OEM y versiones fijadas, sujeto real, caso sano y negativo, resultados literales y rollback cuando haya intervención. Si faltan hardware, adjuntos, compatibilidad o permisos, imprimir could_not_run y conservar open. Un score agregado o mero estado de un dispositivo no acredita el resultado funcional. No instalar parches ni provocar fallo del host para registrar la ficha."}
---

## Registro y responsable

Registro solicitado por Luis el 2026-10-02. Responsable: coordinación de Blackbox. Trabajo o revisión pendiente; la presencia del marcador no demuestra por sí sola un defecto.

## Evidencia y alcance

Trabajo separado del ámbito de su ficha madre, conservando la fuente original. Los reportes de foro siguen sin validación local y no se convierten en recomendaciones automáticas.

**DELTA-FORUM-CX7-FW-UPDATE-GUARD-01.** En ASUS GX10 PSID NVD0000000087, el dueño atribuye a `dpkg --configure -a`/`mlnx-fw-updater 25.10-1.7.1.0` un flash CX7 de 28.45.4028 a 28.47.1088; después informa ambas NIC en `pre-init`, timeout `-110` y ninguna recuperación con reinstalación. NVIDIA dice que ingeniería sigue investigando. Los logs, `mstdump` y el diagnóstico adjunto no se leyeron, por lo que mecanismo y causalidad siguen sin confirmación ([373900](https://forums.developer.nvidia.com/t/373900)). Hacer que el preflight detecte escrituras de firmware CX7 invocadas indirectamente, verifique OEM/PSID/versión exacta, prerequisitos BME/DMA y canal firmado autorizado, y falle cerrado si falta evidencia. Ensayar primero en hardware reemplazable con captura pre/post y ruta de recuperación; nunca flashear para reproducir.

Fuentes: tasks/backlog/FEATURE-APT-CRITICAL-METAPACKAGE-GUARD.md.

## Criterio de cierre y control negativo

Aplicar el alcance y los controles concretos de la evidencia copiada arriba: stack/OEM y versiones fijadas, sujeto real, caso sano y negativo, resultados literales y rollback cuando haya intervención. Si faltan hardware, adjuntos, compatibilidad o permisos, imprimir could_not_run y conservar open. Un score agregado o mero estado de un dispositivo no acredita el resultado funcional. No instalar parches ni provocar fallo del host para registrar la ficha.

## Estado del verificador

La ficha permanece abierta. El test selector del close_check es una especificación pendiente, no una prueba existente ni un resultado ejecutado. Implementarlo exige comprobar el sujeto y su control negativo; la existencia de archivos o esta ficha no basta para cerrar.

Conservar comandos, salida literal y could_not_run incluso cero; una ejecución skipped o inaccesible deja el cierre pendiente. Reutilizar instrumentos nativos y pruebas existentes antes de crear código.

## Avance de instrumentación 2026-10-03

El inventario usa PCI/sysfs para identidad y binding; firmware RDMA se leería de `fw_ver` solo cuando sysfs exponga ese dispositivo. Este host no expuso HCA RDMA, y el firmware de `enP7s7` queda `UNKNOWN` porque no hay atributo genérico disponible; no se ejecutó ni validó ninguna actualización/guard. Evidencia: [BB-INSTRUMENTS-network](../../docs/evidence/BB-INSTRUMENTS-network.md). La ficha permanece abierta; `close_check` y `status` no cambiaron.

## Clasificación del impedimento — 2026-10-04

- Categoría principal: `hardware_or_peer`.
- Impedimento: Inventario local no expuso HCA RDMA; fw_ver de interfaz queda UNKNOWN y no hubo actualización/guard validado sobre hardware CX7.
- Evidencia faltante para cierre: Inventario local no expuso HCA RDMA; fw_ver de interfaz queda UNKNOWN y no hubo actualización/guard validado sobre hardware CX7.
- Siguiente acción: Coordinación BB: definir lectura/guard según interfaz soportada; operador Luis: aportar inventario de CX7 y firmware/OEM, y ejecutar canario de actualización sólo con rollback documentado. Ref explícita: tasks/backlog/DELTA-FORUM-CX7-FW-UPDATE-GUARD-01.md y tests/test_debt_registration_controls.py. Ref explícita: tasks/backlog/DELTA-FORUM-CX7-FW-UPDATE-GUARD-01.md y tasks/evidence/CLOSURE-CONTROLS-2026-10-03/DELTA-FORUM-CX7-FW-UPDATE-GUARD-01-original-selector-current.log.
- Responsable del siguiente paso: Coordinación BB prepara/implementa; cuando la acción requiere root/lab/hardware, operador Luis aporta y ejecuta el sujeto indicado..
- Cierre completo accionable hoy: no. Preparación coordinable: sí.
- Evidencias de clasificación: `tasks/backlog/DELTA-FORUM-CX7-FW-UPDATE-GUARD-01.md`, `tests/test_debt_registration_controls.py`, `tasks/evidence/OPEN-96-CLASSIFICATION-2026-10-04/batches/batch_06.json`, `tasks/evidence/CLOSURE-CONTROLS-2026-10-03/DELTA-FORUM-CX7-FW-UPDATE-GUARD-01-original-selector-current.log`.
- Impedimentos de inspección: 0. El criterio original permanece intacto; esta clasificación conserva la ficha abierta.
