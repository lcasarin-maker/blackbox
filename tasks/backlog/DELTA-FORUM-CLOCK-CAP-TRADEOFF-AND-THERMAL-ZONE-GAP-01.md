---
id: DELTA-FORUM-CLOCK-CAP-TRADEOFF-AND-THERMAL-ZONE-GAP-01
kind: task
domain: VERDICT
title: "Validar forum clock cap tradeoff and thermal zone gap 01"
status: open
severity: P2
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-10-02
close_check: {"cmd": "python3 -m pytest -q tests/test_debt_registration_controls.py::test_delta_forum_clock_cap_tradeoff_and_thermal_zone_gap_01", "expect": "exit_zero", "porque": "Aplicar el alcance y los controles concretos de la evidencia copiada arriba: stack/OEM y versiones fijadas, sujeto real, caso sano y negativo, resultados literales y rollback cuando haya intervención. Si faltan hardware, adjuntos, compatibilidad o permisos, imprimir could_not_run y conservar open. Un score agregado o mero estado de un dispositivo no acredita el resultado funcional. No instalar parches ni provocar fallo del host para registrar la ficha."}
---

## Registro y responsable

Registro solicitado por Luis el 2026-10-02. Responsable: coordinación de Blackbox. Trabajo o revisión pendiente; la presencia del marcador no demuestra por sí sola un defecto.

## Evidencia y alcance

Trabajo separado del ámbito de su ficha madre, conservando la fuente original. Los reportes de foro siguen sin validación local y no se convierten en recomendaciones automáticas.

[372662](https://forums.developer.nvidia.com/t/372662) adds workload-specific clock-cap evidence: owner-reported LLM decode tests often show near-no throughput change at ~2GHz, while one image-generation test loses ~12.5%; another TP2/diffusion comparison reports 0–7.5% changes. A controlled, cooled cuBLAS sweep in post 36 reports −4.5% SGEMM throughput at 2GHz and −9% at 1.8GHz without thermal throttling, while an L2-fitting control tracks clocks more directly. In post 45 one owner’s hottest ACPI zone reads 7–17°C above `nvidia-smi` GPU-die temperature. This supports a two-part local study—sample all effective temperature zones with freshness/type/OEM metadata, and compare matched decode, prefill, image-generation, model-load and concurrent workloads at stock versus a user-selected cap. It does not validate the post 43/45 community governor (only three days reported), its thresholds, or a universal 2GHz/80°C policy; its scripts, sudoers/service suggestions and linked source remain unaudited. Roll back to verified original clock policy, confirm applied clocks and workload throughput, and stop the test if OEM thermal/power diagnostics fail. **DELTA-FORUM-CLOCK-CAP-TRADEOFF-AND-THERMAL-ZONE-GAP-01**.

Fuentes: tasks/backlog/FORUM-00-GB10-THERMAL-RESIDENCY-ADMISSION.md.

## Criterio de cierre y control negativo

Aplicar el alcance y los controles concretos de la evidencia copiada arriba: stack/OEM y versiones fijadas, sujeto real, caso sano y negativo, resultados literales y rollback cuando haya intervención. Si faltan hardware, adjuntos, compatibilidad o permisos, imprimir could_not_run y conservar open. Un score agregado o mero estado de un dispositivo no acredita el resultado funcional. No instalar parches ni provocar fallo del host para registrar la ficha.

## Estado del verificador

La ficha permanece abierta. El test selector del close_check es una especificación pendiente, no una prueba existente ni un resultado ejecutado. Implementarlo exige comprobar el sujeto y su control negativo; la existencia de archivos o esta ficha no basta para cerrar.

Conservar comandos, salida literal y could_not_run incluso cero; una ejecución skipped o inaccesible deja el cierre pendiente. Reutilizar instrumentos nativos y pruebas existentes antes de crear código.

### Evidencia de instrumento (2026-10-03)

Estado: `deferred_lab`. Se reutilizó el inventario térmico existente y su captura de 7 thermal zones/11 canales hwmon, CNR=0, pero 8 labels hwmon faltan y la captura no relaciona esos sensores con un perfil OEM validado ni mide clocks/performance bajo cap. Falta ensayo pareado controlado, clocks efectivamente aplicados y rollback. La ficha sigue abierta y `close_check` intacto. Informe: `docs/evidence/BB-INSTRUMENTS-feasibility-runtime.md`.
