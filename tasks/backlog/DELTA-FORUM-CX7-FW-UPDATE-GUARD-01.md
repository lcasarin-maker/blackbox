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
