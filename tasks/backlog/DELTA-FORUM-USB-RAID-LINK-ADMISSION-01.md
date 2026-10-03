---
id: DELTA-FORUM-USB-RAID-LINK-ADMISSION-01
kind: task
domain: VERDICT
title: "Validar forum usb raid link admission 01"
status: open
severity: P2
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-10-02
close_check: {"cmd": "python3 -m pytest -q tests/test_debt_registration_controls.py::test_delta_forum_usb_raid_link_admission_01", "expect": "exit_zero", "porque": "Aplicar el alcance y los controles concretos de la evidencia copiada arriba: stack/OEM y versiones fijadas, sujeto real, caso sano y negativo, resultados literales y rollback cuando haya intervención. Si faltan hardware, adjuntos, compatibilidad o permisos, imprimir could_not_run y conservar open. Un score agregado o mero estado de un dispositivo no acredita el resultado funcional. No instalar parches ni provocar fallo del host para registrar la ficha."}
---

## Registro y responsable

Registro solicitado por Luis el 2026-10-02. Responsable: coordinación de Blackbox. Trabajo o revisión pendiente; la presencia del marcador no demuestra por sí sola un defecto.

## Evidencia y alcance

Trabajo separado del ámbito de su ficha madre, conservando la fuente original. Los reportes de foro siguen sin validación local y no se convierten en recomendaciones automáticas.

**DELTA-FORUM-USB-RAID-LINK-ADMISSION-01.** En un Dell GB10 con dos unidades NVMe USB, el dueño describe renegociación intermitente a USB 2 de 480Mbps tras reinicios y una matriz mdadm que no se ensambla/monta si cualquiera de sus miembros queda por debajo de 5000Mbps; advierte riesgo de timeouts/corrupción al montar en ese estado. Otro usuario informa varios meses estable con UAS deshabilitado para VID:PID concretos y ventilación adicional, pero su A/B térmico quedó pendiente ([349121](https://forums.developer.nvidia.com/t/349121)). Proteger primero el montaje: comprobar link speed efectivo por identidad estable antes de assemble/mount y mantener array detenido si falta o queda bajo el piso acordado. Validar cualquier quirk UAS solo en canary del mismo enclosure/kernel con reversión. Esta observación corresponde a medios USB externos, no demuestra fallo del NVMe interno ni su causa.


Fuentes: tasks/backlog/FORUM-02-GX10-READ-INTEGRITY.md.

## Criterio de cierre y control negativo

Aplicar el alcance y los controles concretos de la evidencia copiada arriba: stack/OEM y versiones fijadas, sujeto real, caso sano y negativo, resultados literales y rollback cuando haya intervención. Si faltan hardware, adjuntos, compatibilidad o permisos, imprimir could_not_run y conservar open. Un score agregado o mero estado de un dispositivo no acredita el resultado funcional. No instalar parches ni provocar fallo del host para registrar la ficha.

## Estado del verificador

La ficha permanece abierta. El test selector del close_check es una especificación pendiente, no una prueba existente ni un resultado ejecutado. Implementarlo exige comprobar el sujeto y su control negativo; la existencia de archivos o esta ficha no basta para cerrar.

Conservar comandos, salida literal y could_not_run incluso cero; una ejecución skipped o inaccesible deja el cierre pendiente. Reutilizar instrumentos nativos y pruebas existentes antes de crear código.
