---
id: DELTA-FORUM-RECOVERY-APT-UPDATE-01
kind: task
domain: VERDICT
title: "Validar forum recovery apt update 01"
status: open
severity: P2
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-10-02
close_check: {"cmd": "python3 -m pytest -q tests/test_debt_registration_controls.py::test_delta_forum_recovery_apt_update_01", "expect": "exit_zero", "porque": "Aplicar el alcance y los controles concretos de la evidencia copiada arriba: stack/OEM y versiones fijadas, sujeto real, caso sano y negativo, resultados literales y rollback cuando haya intervención. Si faltan hardware, adjuntos, compatibilidad o permisos, imprimir could_not_run y conservar open. Un score agregado o mero estado de un dispositivo no acredita el resultado funcional. No instalar parches ni provocar fallo del host para registrar la ficha."}
---

## Registro y responsable

Registro solicitado por Luis el 2026-10-02. Responsable: coordinación de Blackbox. Trabajo o revisión pendiente; la presencia del marcador no demuestra por sí sola un defecto.

## Evidencia y alcance

Trabajo separado del ámbito de su ficha madre, conservando la fuente original. Los reportes de foro siguen sin validación local y no se convierten en recomendaciones automáticas.

**DELTA-FORUM-RECOVERY-APT-UPDATE-01.** Un usuario informa freeze tras actualización APT y luego un bloqueo durante vLLM en Docker con `--restart always`; tras hard resets describe UEFI/USB/SSH poco fiables, flags GRUB/ACPI añadidos por su cuenta y recomendación NVIDIA de recuperación oficial o RMA ([359198](https://forums.developer.nvidia.com/t/359198)). No hay logs suficientes para atribuir causa a APT, Docker o workload. Extender la runbook con captura preservable antes del reset, identificación de último kernel/driver/paquete, vía de consola externa, medio OEM verificado y criterio de recovery/RMA; cualquier rollback de paquetes se ensaya en copia/canary.

Fuentes: tasks/backlog/FEATURE-FORUM-RESCUE-RUNBOOK-01.md.

## Criterio de cierre y control negativo

Aplicar el alcance y los controles concretos de la evidencia copiada arriba: stack/OEM y versiones fijadas, sujeto real, caso sano y negativo, resultados literales y rollback cuando haya intervención. Si faltan hardware, adjuntos, compatibilidad o permisos, imprimir could_not_run y conservar open. Un score agregado o mero estado de un dispositivo no acredita el resultado funcional. No instalar parches ni provocar fallo del host para registrar la ficha.

## Estado del verificador

La ficha permanece abierta. El test selector del close_check es una especificación pendiente, no una prueba existente ni un resultado ejecutado. Implementarlo exige comprobar el sujeto y su control negativo; la existencia de archivos o esta ficha no basta para cerrar.

Conservar comandos, salida literal y could_not_run incluso cero; una ejecución skipped o inaccesible deja el cierre pendiente. Reutilizar instrumentos nativos y pruebas existentes antes de crear código.

## Avance de instrumentación APT — 2026-10-03

Se reutilizó la captura local de fuentes, arquitectura e índices APT para exponer los inputs del host en `tasks/evidence/BB-INSTRUMENTS-2026-10-03/apt-sources-capture.json`. No se ejecutó `apt update`, no hubo fallo/recovery del host ni se probó una consola, medio OEM, rollback o RMA. La captura no discrimina las causas APT/Docker/workload del relato; la ficha permanece abierta.

## Clasificación del impedimento — 2026-10-04

- Categoría principal: `user_decision`.
- Impedimento: No hay captura pre-reset, recovery media/rollback ni base para decidir recovery/RMA del sujeto afectado.
- Evidencia faltante para cierre: Logs pre-reset, último kernel/paquetes, ruta recovery y medios OEM, rollback; reproducción controlada que distinga APT/Docker/workload.
- Siguiente acción: Completar solo la runbook de preservación pre-reset y solicitar al operador logs previos; pedir al OEM ruta oficial de recovery/RMA antes de cualquier acción sobre el dispositivo.
- Responsable del siguiente paso: BB; operador Luis decide recuperación del sujeto.
- Cierre completo accionable hoy: no. Preparación coordinable: sí.
- Evidencias de clasificación: `tasks/backlog/DELTA-FORUM-RECOVERY-APT-UPDATE-01.md`, `tasks/evidence/BB-INSTRUMENTS-2026-10-03/apt-sources-capture.json`, `tools/hardware_batch02_controls.py`.
- Impedimentos de inspección: 0. El criterio original permanece intacto; esta clasificación conserva la ficha abierta.
