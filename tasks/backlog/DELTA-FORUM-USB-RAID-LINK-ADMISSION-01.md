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

La ficha permanece abierta. El selector original ya está integrado y llama a `tools.hardware_batch03_controls.verify` para este ID exacto. La ejecución del 2026-10-04 devolvió UNKNOWN, fail=0, could_not_run=1 por captura requerida ausente o contrato incompleto. El comando literal y su salida están registrados en `tasks/evidence/CLOSURE-CONTROLS-2026-10-03/hardware-batch03-integration/original-selectors-after-reader-hardening.json`. Los tests de fixtures verifican el control; el cierre requiere el sujeto real y su evidencia específica.

Conservar comandos, salida literal y could_not_run incluso cero; una ejecución skipped o inaccesible deja el cierre pendiente. Reutilizar instrumentos nativos y pruebas existentes antes de crear código.


## Avance de instrumentación 2026-10-03

`tools.host_diagnostics` ahora recoge identidad USB disponible, serial opcional y velocidad sysfs. Esta captura no evalúa admisión de enlaces RAID ni demuestra una UUID estable; no se observaron entradas HID en el host. Detalle y límites: [BB-INSTRUMENTS-devices](../../docs/evidence/BB-INSTRUMENTS-devices.md). La ficha sigue abierta y el close_check original permanece pendiente.

## Clasificación del impedimento — 2026-10-04

- Categoría principal: `hardware_or_peer`.
- Impedimento: Selector reportó UNKNOWN, fail=0, could_not_run=1; falta captura del enlace/velocidad y matriz/ensamblado sobre los dispositivos NVMe USB reales con control sano y negativo.
- Evidencia faltante para cierre: Selector reportó UNKNOWN, fail=0, could_not_run=1; falta captura del enlace/velocidad y matriz/ensamblado sobre los dispositivos NVMe USB reales con control sano y negativo.
- Siguiente acción: Coordinación BB: completar contrato de captura por dispositivo; operador Luis: conectar el arreglo canary y aportar capturas pre/post reinicio sin escribir datos productivos. Ref explícita: tasks/backlog/DELTA-FORUM-USB-RAID-LINK-ADMISSION-01.md y tests/test_debt_registration_controls.py. Ref explícita: tasks/backlog/DELTA-FORUM-USB-RAID-LINK-ADMISSION-01.md y tasks/evidence/OPEN-96-CLASSIFICATION-2026-10-04/batches/batch_00.json.
- Responsable del siguiente paso: Coordinación BB prepara/implementa; cuando la acción requiere root/lab/hardware, operador Luis aporta y ejecuta el sujeto indicado..
- Cierre completo accionable hoy: no. Preparación coordinable: sí.
- Evidencias de clasificación: `tasks/backlog/DELTA-FORUM-USB-RAID-LINK-ADMISSION-01.md`, `tasks/evidence/CLOSURE-CONTROLS-2026-10-03/hardware-batch02-03-primary-coverage.json`, `tests/test_debt_registration_controls.py`, `tasks/evidence/OPEN-96-CLASSIFICATION-2026-10-04/batches/batch_00.json`.
- Impedimentos de inspección: 0. El criterio original permanece intacto; esta clasificación conserva la ficha abierta.
