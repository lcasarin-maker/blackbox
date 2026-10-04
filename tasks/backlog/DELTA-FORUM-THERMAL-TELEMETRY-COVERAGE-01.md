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

La ficha permanece abierta. El selector original ya existe y ejecuta `tools.hardware_batch03_controls.verify` sobre el dossier de esta ficha. La ejecución del 2026-10-04 devolvió UNKNOWN, fail=0, could_not_run=1: el prototipo carece del contrato schema/card identity requerido. El recibo está en `tasks/evidence/CLOSURE-CONTROLS-2026-10-03/hardware-batch03-integration/original-selectors-after-reader-hardening.json`. Falta comprobar el sujeto, su control negativo y el soak; la existencia de archivos no cierra la investigación.

Conservar comandos, salida literal y could_not_run incluso cero; una ejecución skipped o inaccesible deja el cierre pendiente. Reutilizar instrumentos nativos y pruebas existentes antes de crear código.

## Diagnóstico disponible

`python3 -m tools.thermal_coverage` lista zonas thermal, entradas hwmon de temperatura y fan con ruta, identidad OEM disponible, valor raw, etiqueta y estado de lectura; una fuente ausente o ilegible incrementa `could_not_run`. Su estado `observed` solo significa que los canales enumerados se leyeron, no que el sistema esté seguro ni que la matriz OEM o el soak estén validados. No reemplaza los resultados reales requeridos arriba.

La captura local y su comando literal están registrados en `tasks/evidence/DELTA-FORUM-THERMAL-TELEMETRY-COVERAGE-01/prototype-capture.json` y `tasks/evidence/LUNA-98-2026-10-03/batch-03-prototype-runs.json`. La lectura local tuvo `could_not_run=0`; sigue pendiente la validación del sujeto ASUS GX10 y del soak descrito en la ficha.

## Observación nativa actual, 2026-10-04

`python3 -m tools.thermal_coverage` terminó con rc=0 y could_not_run=0. Enumeró 7 zonas térmicas y 3 dispositivos hwmon en GIGABYTE AI TOP ATOM B.1, kernel 6.17.0-1032-nvidia. El resumen minimizado y SHA del original están en `tasks/evidence/DELTA-FORUM-THERMAL-TELEMETRY-COVERAGE-01/current-native-observation-summary.json`; el original queda local para revisión de privacidad. La captura es puntual: faltan el sujeto ASUS GX10, la matriz OEM/versiones, telemetría durante soak, el caso negativo y la atribución de apagados. Estado open conservado.

## Clasificación del impedimento — 2026-10-04

- Categoría principal: `external_oem`.
- Impedimento: Herramienta native thermal_coverage y captura real disponibles con CNR=0; el selector da CNR=1 por schema/card ID incompleto. La enumeración no prueba significado OEM, pero se puede corregir el contrato/selector hoy.
- Evidencia faltante para cierre: Herramienta native thermal_coverage y captura real disponibles con CNR=0; el selector da CNR=1 por schema/card ID incompleto. La enumeración no prueba significado OEM, pero se puede corregir el contrato/selector hoy.
- Siguiente acción: Coordinación BB: completar schema/card-ID exactos, diferenciar observed de cobertura semántica y comprobar canales faltantes; dejar A/B workload/OEM como evidencia separada. Ref explícita: tasks/backlog/DELTA-FORUM-THERMAL-TELEMETRY-COVERAGE-01.md y tests/test_debt_registration_controls.py. Ref explícita: tasks/backlog/DELTA-FORUM-THERMAL-TELEMETRY-COVERAGE-01.md y tasks/evidence/OPEN-96-CLASSIFICATION-2026-10-04/batches/batch_09.json.
- Responsable del siguiente paso: Coordinación BB; para recuperación de históricos, custodio del artifact store si corresponde..
- Cierre completo accionable hoy: no. Preparación coordinable: sí.
- Evidencias de clasificación: `tasks/backlog/DELTA-FORUM-THERMAL-TELEMETRY-COVERAGE-01.md`, `tasks/evidence/DELTA-FORUM-THERMAL-TELEMETRY-COVERAGE-01/current-native-observation-summary.json`, `tasks/evidence/CLOSURE-CONTROLS-2026-10-03/hardware-batch02-03-primary-coverage.json`, `tests/test_debt_registration_controls.py`, `tasks/evidence/OPEN-96-CLASSIFICATION-2026-10-04/batches/batch_09.json`.
- Impedimentos de inspección: 0. El criterio original permanece intacto; esta clasificación conserva la ficha abierta.
