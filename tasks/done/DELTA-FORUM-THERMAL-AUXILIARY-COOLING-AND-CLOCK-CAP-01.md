---
id: DELTA-FORUM-THERMAL-AUXILIARY-COOLING-AND-CLOCK-CAP-01
kind: task
domain: VERDICT
title: "Validar forum thermal auxiliary cooling and clock cap 01"
status: done
closed_at: 2026-10-14
closure_type: void_wontfix
reason: "El reporte es de un ASUS Ascent GX10 con enfriamiento auxiliar; este equipo es GIGABYTE AI TOP ATOM y no tiene dispositivo USB auxiliar. El A/B de tope de reloj que si aplica aqui lo lleva FEATURE-FORUM-GPU-CLOCK-CAP-AB-01 (abierta). Decision de Luis 2026-10-14: cerrar sin sujeto; reabrir si se instala enfriamiento auxiliar."
evidence: {"pass": "tasks/evidence/DELTA-FORUM-THERMAL-AUXILIARY-COOLING-AND-CLOCK-CAP-01/pass.txt", "fail": "tasks/evidence/DELTA-FORUM-THERMAL-AUXILIARY-COOLING-AND-CLOCK-CAP-01/fail.txt", "e2e": "tasks/evidence/DELTA-FORUM-THERMAL-AUXILIARY-COOLING-AND-CLOCK-CAP-01/e2e.txt"}
severity: P2
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-10-02
close_check: {"cmd": "python -m tools.check_harvest_accepted tasks/done/DELTA-FORUM-THERMAL-AUXILIARY-COOLING-AND-CLOCK-CAP-01.md", "expect": "exit_zero", "porque": "Cerrada sin sujeto en este equipo (void_wontfix, decision de Luis 2026-10-14): no hay fix que probar, lo verificable por maquina es que la decision quedo registrada (closure_type y reason). El close_check anterior era `python3 -m pytest -q tests/test_debt_registration_controls.py::test_delta_forum_thermal_auxiliary_cooling_and_clock_cap_01`, un xfail que se retira con el cierre."}
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

## Estado (2026-10-11, /0 + /vote)

Bloqueada por criterio sin implementar: el `close_check` de esta ficha termina en `xfailed` y por eso sale con codigo 0 sin que el criterio real exista. Un `xfail` no es una verificacion y cerrar con el no es cierre. Cerrarla exige implementar la prueba real contra el sujeto (vLLM, NCCL, CX7 u otro hardware) con su control negativo. Decision del dueno el 2026-10-11: dejarla abierta y declarada, no cerrarla como `void_wontfix`.

## Adaptacion a este equipo (clasificacion 2026-10-13)
Aplicabilidad: adaptable · utilidad: media · lectura: completa.

Hay un problema termico medido aqui (zona 95.7 C en el corte del 11-oct, ver DEBT-CORTES-BAJO-CARGA) y tools/verify_gpu_clock_cap_ab.py y verify_clock_cap_tradeoff.py ya evaluan el A/B; ademas FEATURE-BB-EVALUAR-CAP-DE-CPU-01 existe. Los enfriadores USB/cartulina del foro son de GX10 de ASUS, no de esta ATOM; selector en UNKNOWN/CNR=1 por captura ausente.

Version para un solo nodo Gigabyte AI TOP ATOM: Correr el A/B de tope de reloj de GPU (o ventilador auxiliar) en esta ATOM con las herramientas verify_gpu_clock_cap_ab/verify_clock_cap_tradeoff, midiendo zona, reloj y throughput contra control; sin prototipos del foro.

Perfil contra el que se clasifico: un nodo GB10 Gigabyte, DGX OS 7.2.3, kernel 6.17.0-1032-nvidia, driver 580.178.04, un contenedor vLLM (`nemotron-local`), sin InfiniBand/CX7 en pareja, sin Ray ni llama.cpp RPC. Clasificacion por lectura, sin control negativo: es una propuesta, no una verificacion.

## Root Cause
No aplica a este equipo: los enfriadores auxiliares del reporte son de un ASUS Ascent GX10; aqui `sys_vendor`=GIGABYTE y `product_name`=AI TOP ATOM, y el bus USB no tiene ningun dispositivo auxiliar. El A/B de tope de reloj de GPU, que si aplica a esta maquina, sigue abierto en `FEATURE-FORUM-GPU-CLOCK-CAP-AB-01`.

## Regression Test
Ninguno: la ficha se cierra por no tener sujeto aqui. El test que la vigilaba (`tests/test_debt_registration_controls.py::test_delta_forum_thermal_auxiliary_cooling_and_clock_cap_01`) se retira junto con sus entradas de `tests/known_failures.json`.

## Verification Evidence
Tres rutas del frontmatter: `fail` (control negativo: las ordenes que buscan el sujeto salen con rc distinto de 0), `pass` (perfil medido, con control positivo de que las mismas herramientas encuentran lo que si existe) y `e2e` (la decision registrada). Datos de la maquina redactados con el PATRON de `tests/test_sin_datos_privados.py`. Para reabrirla si el sujeto aparece: `git mv tasks/done/DELTA-FORUM-THERMAL-AUXILIARY-COOLING-AND-CLOCK-CAP-01.md tasks/backlog/` y `status: open`.
