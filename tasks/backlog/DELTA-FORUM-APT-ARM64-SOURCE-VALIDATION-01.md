---
id: DELTA-FORUM-APT-ARM64-SOURCE-VALIDATION-01
kind: task
domain: VERDICT
title: "Validar forum apt arm64 source validation 01"
status: open
severity: P2
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-10-02
close_check: {"cmd": "python3 -m pytest -q tests/test_debt_registration_controls.py::test_delta_forum_apt_arm64_source_validation_01", "expect": "exit_zero", "porque": "Aplicar el alcance y los controles concretos de la evidencia copiada arriba: stack/OEM y versiones fijadas, sujeto real, caso sano y negativo, resultados literales y rollback cuando haya intervención. Si faltan hardware, adjuntos, compatibilidad o permisos, imprimir could_not_run y conservar open. Un score agregado o mero estado de un dispositivo no acredita el resultado funcional. No instalar parches ni provocar fallo del host para registrar la ficha."}
---

## Registro y responsable

Registro solicitado por Luis el 2026-10-02. Responsable: coordinación de Blackbox. Trabajo o revisión pendiente; la presencia del marcador no demuestra por sí sola un defecto.

## Evidencia y alcance

Trabajo separado del ámbito de su ficha madre, conservando la fuente original. Los reportes de foro siguen sin validación local y no se convierten en recomendaciones automáticas.

**DELTA-FORUM-APT-ARM64-SOURCE-VALIDATION-01.** En DGX Spark/Noble arm64, un dueño publicó `ubuntu.sources` mezclando `archive.ubuntu.com` (404 en binary-arm64) y `ports.ubuntu.com`; soporte NVIDIA indicó `ports.ubuntu.com/ubuntu-ports` como fuente Ubuntu esperada. En paralelo, un PPA NVIDIA Vulkan reportó tamaño/hash inesperado durante sincronización de espejo, y otro usuario luego obtuvo `apt update` limpio. El autor dijo que retirar el archivo con source incorrecta restauró apt, pero sincronización y cambio de source no quedan aislados ([355471](https://forums.developer.nvidia.com/t/355471)). Validar perfil de repos aprobado y frescura/integridad de índices antes de upgrades; no borrar fuentes automáticamente ni continuar sobre índices stale.

Fuentes: tasks/backlog/FEATURE-APT-CRITICAL-METAPACKAGE-GUARD.md.

## Criterio de cierre y control negativo

Aplicar el alcance y los controles concretos de la evidencia copiada arriba: stack/OEM y versiones fijadas, sujeto real, caso sano y negativo, resultados literales y rollback cuando haya intervención. Si faltan hardware, adjuntos, compatibilidad o permisos, imprimir could_not_run y conservar open. Un score agregado o mero estado de un dispositivo no acredita el resultado funcional. No instalar parches ni provocar fallo del host para registrar la ficha.

## Estado del verificador

La ficha permanece abierta. El test selector del close_check es una especificación pendiente, no una prueba existente ni un resultado ejecutado. Implementarlo exige comprobar el sujeto y su control negativo; la existencia de archivos o esta ficha no basta para cerrar.

Conservar comandos, salida literal y could_not_run incluso cero; una ejecución skipped o inaccesible deja el cierre pendiente. Reutilizar instrumentos nativos y pruebas existentes antes de crear código.
