---
id: DELTA-ROOT-DISPLAY-CARVEOUT-OEM-FIX-GATE-01
kind: task
domain: VERDICT
title: "Validar root display carveout oem fix gate 01"
status: open
severity: P2
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-10-02
close_check: {"cmd": "python3 -m pytest -q tests/test_debt_registration_controls.py::test_delta_root_display_carveout_oem_fix_gate_01", "expect": "exit_zero", "porque": "Aplicar el alcance y los controles concretos de la evidencia copiada arriba: stack/OEM y versiones fijadas, sujeto real, caso sano y negativo, resultados literales y rollback cuando haya intervención. Si faltan hardware, adjuntos, compatibilidad o permisos, imprimir could_not_run y conservar open. Un score agregado o mero estado de un dispositivo no acredita el resultado funcional. No instalar parches ni provocar fallo del host para registrar la ficha."}
---

## Registro y responsable

Registro solicitado por Luis el 2026-10-02. Responsable: coordinación de Blackbox. Trabajo o revisión pendiente; la presencia del marcador no demuestra por sí sola un defecto.

## Evidencia y alcance

Trabajo separado del ámbito de su ficha madre, conservando la fuente original. Los reportes de foro siguen sin validación local y no se convierten en recomendaciones automáticas.

## DELTA-ROOT-DISPLAY-CARVEOUT-OEM-FIX-GATE-01

[Hilo 370458](https://forums.developer.nvidia.com/t/370458): terminales Sway quedan congeladas por `NV_ERR_NO_MEMORY` en la ruta `scanoutcarveout`, con 109 GiB libres. El dueño reproduce el problema tras pasar de driver 580.142 a 580.159.03; bajar de 6K a 4K permite abrir más ventanas pero conserva el fallo. NVIDIA propone la actualización de julio con `Adjustable Display Reserved Memory` y mejoras de manejo UMA. Falta un resultado posterior del dueño; el gist completo y las capturas quedaron sin inspeccionar.

Propuesta: comprobar soporte y valor efectivo de la reserva en el OEM ATOM, registrar versión de driver y repetir aperturas y cierres de ventanas a 6K y 4K, además de presión de caché. Distinguir la asignación de display del agotamiento general de memoria.

Riesgos: la reserva reduce memoria disponible para las cargas; atribuir el fallo a presión global puede matar procesos ajenos. Close check: reproducir el fallo, comprobar que la corrección mantiene sesión y SSH durante el ensayo y restaurar el valor previo mediante rollback verificado.

Fuentes: tasks/backlog/FEATURE-FORUM-DESKTOP-SESSION-POSTUPDATE-01.md.

## Criterio de cierre y control negativo

Aplicar el alcance y los controles concretos de la evidencia copiada arriba: stack/OEM y versiones fijadas, sujeto real, caso sano y negativo, resultados literales y rollback cuando haya intervención. Si faltan hardware, adjuntos, compatibilidad o permisos, imprimir could_not_run y conservar open. Un score agregado o mero estado de un dispositivo no acredita el resultado funcional. No instalar parches ni provocar fallo del host para registrar la ficha.

## Estado del verificador

La ficha permanece abierta. El selector original ya está integrado y llama a `tools.hardware_batch03_controls.verify` para este ID exacto. La ejecución del 2026-10-04 devolvió UNKNOWN, fail=0, could_not_run=1 por captura requerida ausente o contrato incompleto. El comando literal y su salida están registrados en `tasks/evidence/CLOSURE-CONTROLS-2026-10-03/hardware-batch03-integration/original-selectors-after-reader-hardening.json`. Los tests de fixtures verifican el control; el cierre requiere el sujeto real y su evidencia específica.

Conservar comandos, salida literal y could_not_run incluso cero; una ejecución skipped o inaccesible deja el cierre pendiente. Reutilizar instrumentos nativos y pruebas existentes antes de crear código.

## Clasificación del impedimento — 2026-10-04

- Categoría principal: `external_oem`.
- Impedimento: Falta matriz OEM autorizada y ensayo reversible para ajuste de carveout; modificar firmware/UEFI puede comprometer arranque.
- Evidencia faltante para cierre: release notes del OEM/modelo; tuple EC/UEFI/OTA; baseline de memoria; canario y rollback OEM
- Siguiente acción: Solicitar a coordinación BB que obtenga matriz/release notes y ventana de canario del OEM; ejecutar solo con rollback confirmado.
- Responsable del siguiente paso: coordinación BB gestiona OEM.
- Cierre completo accionable hoy: no. Preparación coordinable: sin acción adicional demostrada en esta revisión.
- Evidencias de clasificación: `tasks/backlog/DELTA-ROOT-DISPLAY-CARVEOUT-OEM-FIX-GATE-01.md`, `tasks/evidence/OPEN-96-CLASSIFICATION-2026-10-04/batches/batch_05.json`, `tasks/evidence/DELTA-ROOT-DISPLAY-CARVEOUT-OEM-FIX-GATE-01/ (directorio ausente al inspeccionar)`.
- Impedimentos de inspección: 1. El criterio original permanece intacto; esta clasificación conserva la ficha abierta.
