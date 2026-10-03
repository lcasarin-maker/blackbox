---
id: DELTA-FORUM-THERMAL-TELEMETRY-COVERAGE-01
kind: task
domain: VERDICT
title: "Validar forum thermal telemetry coverage 01"
status: open
severity: P2
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-10-02
close_check: {"cmd": "python3 -m pytest -q tests/test_debt_registration_controls.py::test_delta_forum_thermal_telemetry_coverage_01", "expect": "exit_zero", "porque": "Aplicar el alcance y los controles concretos de la evidencia copiada arriba: stack/OEM y versiones fijadas, sujeto real, caso sano y negativo, resultados literales y rollback cuando haya intervención. Si faltan hardware, adjuntos, compatibilidad o permisos, imprimir could_not_run y conservar open. Un score agregado o mero estado de un dispositivo no acredita el resultado funcional. No instalar parches ni provocar fallo del host para registrar la ficha."}
---

## Registro y responsable

Registro solicitado por Luis el 2026-10-02. Responsable: coordinación de Blackbox. Trabajo o revisión pendiente; la presencia del marcador no demuestra por sí sola un defecto.

## Evidencia y alcance

Trabajo separado del ámbito de su ficha madre, conservando la fuente original. Los reportes de foro siguen sin validación local y no se convierten en recomendaciones automáticas.

**DELTA-FORUM-THERMAL-TELEMETRY-COVERAGE-01.** Un dueño de ASUS GX10 EC 0x02000005/UEFI 0x03000006 publica telemetría a 1 s con GPU ~90°C, dos zonas ACPI hasta 96.6°C y `tviol=1` en 68 muestras; fan telemetry aparece N/A y no encuentra evento térmico en journal. El hilo reúne también apagados bajo carga, un caso con reloj limitado a 2GHz y temperaturas distintas; adjuntos de zonas, logs, ZIP y cápsulas no se leyeron, y la causa térmica frente a OOM/potencia queda sin resolver ([377044](https://forums.developer.nvidia.com/t/377044)). Verificar canales efectivos por OEM/versión y registrar muestra/frescura, temperatura CPU/GPU/zonas, fan, clocks, potencia y motivo de apagado durante soak; no fijar umbral comunitario como política universal.

Fuentes: tasks/backlog/FORUM-00-GB10-THERMAL-RESIDENCY-ADMISSION.md.

## Criterio de cierre y control negativo

Aplicar el alcance y los controles concretos de la evidencia copiada arriba: stack/OEM y versiones fijadas, sujeto real, caso sano y negativo, resultados literales y rollback cuando haya intervención. Si faltan hardware, adjuntos, compatibilidad o permisos, imprimir could_not_run y conservar open. Un score agregado o mero estado de un dispositivo no acredita el resultado funcional. No instalar parches ni provocar fallo del host para registrar la ficha.

## Estado del verificador

La ficha permanece abierta. El test selector del close_check es una especificación pendiente, no una prueba existente ni un resultado ejecutado. Implementarlo exige comprobar el sujeto y su control negativo; la existencia de archivos o esta ficha no basta para cerrar.

Conservar comandos, salida literal y could_not_run incluso cero; una ejecución skipped o inaccesible deja el cierre pendiente. Reutilizar instrumentos nativos y pruebas existentes antes de crear código.
