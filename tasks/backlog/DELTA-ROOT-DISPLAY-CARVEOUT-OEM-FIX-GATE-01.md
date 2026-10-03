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

La ficha permanece abierta. El test selector del close_check es una especificación pendiente, no una prueba existente ni un resultado ejecutado. Implementarlo exige comprobar el sujeto y su control negativo; la existencia de archivos o esta ficha no basta para cerrar.

Conservar comandos, salida literal y could_not_run incluso cero; una ejecución skipped o inaccesible deja el cierre pendiente. Reutilizar instrumentos nativos y pruebas existentes antes de crear código.
