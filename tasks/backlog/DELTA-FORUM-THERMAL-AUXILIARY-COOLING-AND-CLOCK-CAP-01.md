---
id: DELTA-FORUM-THERMAL-AUXILIARY-COOLING-AND-CLOCK-CAP-01
kind: task
domain: VERDICT
title: "Validar forum thermal auxiliary cooling and clock cap 01"
status: open
severity: P2
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-10-02
close_check: {"cmd": "python3 -m pytest -q tests/test_debt_registration_controls.py::test_delta_forum_thermal_auxiliary_cooling_and_clock_cap_01", "expect": "exit_zero", "porque": "Aplicar el alcance y los controles concretos de la evidencia copiada arriba: stack/OEM y versiones fijadas, sujeto real, caso sano y negativo, resultados literales y rollback cuando haya intervención. Si faltan hardware, adjuntos, compatibilidad o permisos, imprimir could_not_run y conservar open. Un score agregado o mero estado de un dispositivo no acredita el resultado funcional. No instalar parches ni provocar fallo del host para registrar la ficha."}
---

## Registro y responsable

Registro solicitado por Luis el 2026-10-02. Responsable: coordinación de Blackbox. Trabajo o revisión pendiente; la presencia del marcador no demuestra por sí sola un defecto.

## Evidencia y alcance

Trabajo separado del ámbito de su ficha madre, conservando la fuente original. Los reportes de foro siguen sin validación local y no se convierten en recomendaciones automáticas.

[373199](https://forums.developer.nvidia.com/t/373199) describes user cooling experiments on ASUS GX10: a USB base fan reports roughly 6–8°C lower GPU temperature in one setup; a separate extraction-fan plus 2GHz GPU clock cap reports <1% performance loss and about 10°C lower peaks, explicitly without hard data; another dual-GX10 cardboard/fan prototype claims a 20–25°C drop. The posts mix orientation, fan placement, clocks, ambient conditions and workload, and omit complete firmware/ambient/test controls. The linked STL/ZIP and key images were not inspected. Treat as a low-confidence candidate for an OEM-specific A/B thermal-soak test; do not apply a clock cap or external fan as a universal fix. Measure inlet/zone/GPU/CPU temperature, clocks, wall power, fan behavior and useful throughput against matched controls; test OEM limits, dust, noise, PSU cooling and reversible rollback. **DELTA-FORUM-THERMAL-AUXILIARY-COOLING-AND-CLOCK-CAP-01**.

Fuentes: tasks/backlog/FORUM-00-GB10-THERMAL-RESIDENCY-ADMISSION.md.

## Criterio de cierre y control negativo

Aplicar el alcance y los controles concretos de la evidencia copiada arriba: stack/OEM y versiones fijadas, sujeto real, caso sano y negativo, resultados literales y rollback cuando haya intervención. Si faltan hardware, adjuntos, compatibilidad o permisos, imprimir could_not_run y conservar open. Un score agregado o mero estado de un dispositivo no acredita el resultado funcional. No instalar parches ni provocar fallo del host para registrar la ficha.

## Estado del verificador

La ficha permanece abierta. El selector original ya está integrado y llama a `tools.hardware_batch03_controls.verify` para este ID exacto. La ejecución del 2026-10-04 devolvió UNKNOWN, fail=0, could_not_run=1 por captura requerida ausente o contrato incompleto. El comando literal y su salida están registrados en `tasks/evidence/CLOSURE-CONTROLS-2026-10-03/hardware-batch03-integration/original-selectors-after-reader-hardening.json`. Los tests de fixtures verifican el control; el cierre requiere el sujeto real y su evidencia específica.

Conservar comandos, salida literal y could_not_run incluso cero; una ejecución skipped o inaccesible deja el cierre pendiente. Reutilizar instrumentos nativos y pruebas existentes antes de crear código.

## Clasificación del impedimento — 2026-10-04

- Categoría principal: `hardware_or_peer`.
- Impedimento: Selector ya informa UNKNOWN/CNR=1 por captura del sujeto ausente/incompleta; faltan controles térmicos comparables.
- Evidencia faltante para cierre: temperatura ambiente/entrada/GPU/CPU; clocks, watts, fans y throughput en A/B; límites OEM y rollback
- Siguiente acción: Medir soak A/B con carga repetible y ambiente controlado en GX10 canary, sin imponer cap universal; guardar telemetría completa y recuperación.
- Responsable del siguiente paso: coordinación BB prepara; operador Luis ejecuta root/lab.
- Cierre completo accionable hoy: no. Preparación coordinable: sin acción adicional demostrada en esta revisión.
- Evidencias de clasificación: `tasks/backlog/DELTA-FORUM-THERMAL-AUXILIARY-COOLING-AND-CLOCK-CAP-01.md`, `tasks/evidence/OPEN-96-CLASSIFICATION-2026-10-04/batches/batch_08.json`, `tasks/evidence/DELTA-FORUM-THERMAL-AUXILIARY-COOLING-AND-CLOCK-CAP-01/ (directorio ausente al inspeccionar)`.
- Impedimentos de inspección: 1. El criterio original permanece intacto; esta clasificación conserva la ficha abierta.
