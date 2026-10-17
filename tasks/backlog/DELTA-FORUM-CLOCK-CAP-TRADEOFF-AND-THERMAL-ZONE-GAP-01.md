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

## Clasificación del impedimento — 2026-10-04

- Categoría principal: `workload_or_lab`.
- Impedimento: Inventario lee zonas, pero faltan labels/relación OEM validada y A/B del workload real con cap, clocks efectivos, throughput, frescura y rollback.
- Evidencia faltante para cierre: Inventario lee zonas, pero faltan labels/relación OEM validada y A/B del workload real con cap, clocks efectivos, throughput, frescura y rollback.
- Siguiente acción: Coordinación BB: completar mapeo/captura de fuentes disponibles; operador Luis: aportar perfil OEM y ejecutar A/B canary seleccionado con rollback. Ref explícita: tasks/backlog/DELTA-FORUM-CLOCK-CAP-TRADEOFF-AND-THERMAL-ZONE-GAP-01.md y tests/test_debt_registration_controls.py. Ref explícita: tasks/backlog/DELTA-FORUM-CLOCK-CAP-TRADEOFF-AND-THERMAL-ZONE-GAP-01.md y tasks/evidence/OPEN-96-CLASSIFICATION-2026-10-04/batches/batch_03.json.
- Responsable del siguiente paso: Coordinación BB prepara/implementa; cuando la acción requiere root/lab/hardware, operador Luis aporta y ejecuta el sujeto indicado..
- Cierre completo accionable hoy: no. Preparación coordinable: sí.
- Evidencias de clasificación: `tasks/backlog/DELTA-FORUM-CLOCK-CAP-TRADEOFF-AND-THERMAL-ZONE-GAP-01.md`, `tests/test_debt_registration_controls.py`, `tasks/evidence/OPEN-96-CLASSIFICATION-2026-10-04/batches/batch_03.json`.
- Impedimentos de inspección: 0. El criterio original permanece intacto; esta clasificación conserva la ficha abierta.

## Estado (2026-10-11, /0 + /vote)

Bloqueada por criterio sin implementar: el `close_check` de esta ficha termina en `xfailed` y por eso sale con codigo 0 sin que el criterio real exista. Un `xfail` no es una verificacion y cerrar con el no es cierre. Cerrarla exige implementar la prueba real contra el sujeto (vLLM, NCCL, CX7 u otro hardware) con su control negativo. Decision del dueno el 2026-10-11: dejarla abierta y declarada, no cerrarla como `void_wontfix`.

## Adaptacion a este equipo (clasificacion 2026-10-13)
Aplicabilidad: adaptable · utilidad: media · lectura: completa.

El host tiene 7 thermal zones/11 canales hwmon (inventario de la ficha) y ya hay sensores termico_predictivo y bb reloj (tools/reloj_atascado.py). El A/B de cap de reloj es un estudio de laboratorio en un solo nodo con nemotron-local.

Version para un solo nodo Gigabyte AI TOP ATOM: Estudio A/B de un solo nodo: decode y prefill de nemotron-local a stock vs un cap elegido, registrando todas las zonas termicas; sin governor comunitario ni cap universal.

Perfil contra el que se clasifico: un nodo GB10 Gigabyte, DGX OS 7.2.3, kernel 6.17.0-1032-nvidia, driver 580.178.04, un contenedor vLLM (`nemotron-local`), sin InfiniBand/CX7 en pareja, sin Ray ni llama.cpp RPC. Clasificacion por lectura, sin control negativo: es una propuesta, no una verificacion.

## Avance 2026-10-14 (lote 'cierra las pendientes conforme a la opcion recomendada'): espera un disparador, no una decision
Disparador: la ventana del motor de 60 min que anuncia Luis con sudo de Luis (`nvidia-smi -lgc` es escritura de root; no cabe en un script de solo lectura). La misma ventana sirve a FEATURE-FORUM-GPU-CLOCK-CAP-AB-01. Pasos exactos: A (stock, 300,2800 del `atom-clock-lock`): carga fija de decode y prefill contra `nemotron-local` con `atom_gpu_telemetry` registrando las 7 zonas termicas; B: `sudo nvidia-smi -lgc 300,2100` y la misma carga; rollback `sudo nvidia-smi -lgc 300,2800` y comprobar el reloj aplicado bajo carga. El close_check sigue siendo el xfail original hasta que exista esa captura.

## Avance 2026-10-16 (voto de Luis: el tradeoff debe poder salir PASS)
`tools/verify_clock_cap_tradeoff.verify(evidence, ab_evidence)` ya tiene ruta PASS: compone (llama, no copia) `tools/verify_gpu_clock_cap_ab.verify` y exige en la misma ventana inventario térmico observado, OEM/producto, labels hwmon completos, trip point OEM (passive/hot/critical) sin superar, el A/B en `pass` (que ya incluye stock/cap/rollback con readback) y el inventario tomado dentro del intervalo de la captura A/B con el mismo fabricante/producto que su `dmidecode`. Un A/B en `fail`, una ventana o identidad distinta, o una zona sobre su trip point dan `fail`; A/B ausente o sin readback de rollback, labels incompletos, sin trip point o inventario ausente dan `unknown`. Pasa sólo con fixtures sintéticas (`tests/test_clock_tradeoff_composed_pass.py`, A/B sano de `tests/test_cobertura_g3_hardware.py` con su costura `_csv_policy`); control negativo por mutación (ignorar el veredicto A/B) pone en rojo 3 tests. Ninguna corrida viva: el close_check sigue en xfail y esta ficha sigue abierta.

Falta, en manos de Luis: la ventana del motor de 60 min a `300,2100` con `atom_gpu_telemetry` grabando las 7 zonas y la captura `commands.json` de FEATURE-FORUM-GPU-CLOCK-CAP-AB-01, más un inventario térmico tomado dentro de esa ventana. Dos bloqueos además de la ventana, medidos sobre la captura del 2026-10-03: (1) sólo 3 de 11 entradas hwmon traen label (las de `acpitz` no exponen `temp*_label`), así que `sensor_labels` queda `unknown` en este host aunque la ventana se corra; (2) `verify_gpu_clock_cap_ab._csv_policy` devuelve None en producción porque GB10 no expone el rango `-lgc` activo, así que el A/B real sale `unknown` por readbacks hasta que exista una lectura nativa del rango aplicado.
