---
id: DELTA-FORUM-DCP4-DECODE-STARVATION-FAIR-SCHEDULER-01
kind: task
domain: VERDICT
title: "Validar forum dcp4 decode starvation fair scheduler 01"
status: done
closed_at: 2026-10-13
closure_type: void_wontfix
reason: "Reporte de GLM-5.2 con TP8/DCP4 sobre ocho GB10 y un parche externo de scheduler; este equipo sirve un solo nemotron-local en un nodo, sin TP ni DCP. Decision de Luis 2026-10-13: deprecar por aplicabilidad, con independencia de la nota del 2026-10-11 (que dejaba abiertas las fichas con xfail porque un xfail no verifica nada)."
evidence: {"pass": "tasks/evidence/DELTA-FORUM-DCP4-DECODE-STARVATION-FAIR-SCHEDULER-01/pass.txt", "fail": "tasks/evidence/DELTA-FORUM-DCP4-DECODE-STARVATION-FAIR-SCHEDULER-01/fail.txt", "e2e": "tasks/evidence/DELTA-FORUM-DCP4-DECODE-STARVATION-FAIR-SCHEDULER-01/e2e.txt"}
severity: P2
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-10-02
close_check: {"cmd": "python -m tools.check_harvest_accepted tasks/done/DELTA-FORUM-DCP4-DECODE-STARVATION-FAIR-SCHEDULER-01.md", "expect": "exit_zero", "porque": "Cerrada por aplicabilidad (void_wontfix, decision de Luis 2026-10-13): no hay fix que probar, lo verificable por maquina es que la decision quedo registrada (closure_type y reason). El close_check anterior apuntaba a un test por ficha que se retiro con la deprecacion."}
---

## Referencia pública

Hilos de los que salió esta ficha (URL pública):

- https://forums.developer.nvidia.com/t/376831/10

El texto de lo que dicen esos hilos se reubicó el 2026-11-01 a la base de conocimiento del dueño, por decisión del dueño: el conocimiento vive en el consumidor de conocimiento. Esta ficha conserva sólo el trabajo sobre la máquina y su registro de verificación; su `close_check` no cambió.

## Registro y responsable

Registro solicitado por Luis el 2026-10-02. Responsable: coordinación de Blackbox. Trabajo o revisión pendiente; la presencia del marcador no demuestra por sí sola un defecto.

## Criterio de cierre y control negativo

Aplicar el alcance y los controles concretos de la evidencia copiada arriba: stack/OEM y versiones fijadas, sujeto real, caso sano y negativo, resultados literales y rollback cuando haya intervención. Si faltan hardware, adjuntos, compatibilidad o permisos, imprimir could_not_run y conservar open. Un score agregado o mero estado de un dispositivo no acredita el resultado funcional. No instalar parches ni provocar fallo del host para registrar la ficha.

## Estado del verificador

La ficha permanece abierta. El test selector del close_check es una especificación pendiente, no una prueba existente ni un resultado ejecutado. Implementarlo exige comprobar el sujeto y su control negativo; la existencia de archivos o esta ficha no basta para cerrar.

Conservar comandos, salida literal y could_not_run incluso cero; una ejecución skipped o inaccesible deja el cierre pendiente. Reutilizar instrumentos nativos y pruebas existentes antes de crear código.

## Evaluación de instrumentos 2026-10-03

Reusa `tools/provider_trace.py` únicamente para la ruta request/provider/worker; no observa cola por paso, scheduler DCP4 ni equidad entre decode largo y prefill. No existe traza local de la carga descrita. Siguiente paso `deferred_lab`: stack TP8/DCP4 fijado, secuencia con decode largo y cuatro prefills concurrentes, orden/espera por cola, tokens/s, throughput, stalls, errores, completitud y corrección, con control stock y rollback. No se ejecutó workload.

## Clasificación del impedimento — 2026-10-04

- Categoría principal: `workload_or_lab`.
- Impedimento: La ficha dice que provider_trace no observa cola por paso/scheduler; no hay traza de la carga TP8 descrita.
- Evidencia faltante para cierre: Stack TP8/DCP4 y digest fijados; decode largo + cuatro prefills; orden/espera, throughput, stalls, errores/completitud/corrección; control stock y rollback.
- Siguiente acción: Preparar una captura temporal de cola por paso solo si el runtime fijado la expone; de lo contrario, solicitar corrida de decode largo + cuatro prefills, stock vs flag de rollback y registros de stalls/throughput en laboratorio.
- Responsable del siguiente paso: BB; operador Luis para workload/lab.
- Cierre completo accionable hoy: no. Preparación coordinable: sí.
- Evidencias de clasificación: `tasks/backlog/DELTA-FORUM-DCP4-DECODE-STARVATION-FAIR-SCHEDULER-01.md`, `tools/provider_trace.py`, `tools/runtime_batch01_controls.py`.
- Impedimentos de inspección: 0. El criterio original permanece intacto; esta clasificación conserva la ficha abierta.

## Estado (2026-10-11, /0 + /vote)

Bloqueada por criterio sin implementar: el `close_check` de esta ficha termina en `xfailed` y por eso sale con codigo 0 sin que el criterio real exista. Un `xfail` no es una verificacion y cerrar con el no es cierre. Cerrarla exige implementar la prueba real contra el sujeto (vLLM, NCCL, CX7 u otro hardware) con su control negativo. Decision del dueno el 2026-10-11: dejarla abierta y declarada, no cerrarla como `void_wontfix`.

## Root Cause
No aplica a este equipo: GLM-5.2 en TP8/DCP4 sobre ocho GB10; aqui hay un contenedor vLLM con nemotron-local y no se sirve GLM ni TP8. (aplicabilidad otro_hardware, utilidad baja).

## Regression Test
Ninguno: la ficha se depreca por no tener sujeto aqui. Los tests que la vigilaban (`test_delta_forum_dcp4_decode_starvation_fair_scheduler_01`, `test_real_capture_close_gate_requires_actual_capture[DELTA-FORUM-DCP4-DECODE-STARVATION-FAIR-SCHEDULER-01]`) se retiran o dejan de parametrizarla, junto con sus entradas de `tests/known_failures.json`.

## Verification Evidence
Tres rutas del frontmatter: `fail` (el close_check era un xfail), `pass` (perfil medido del equipo: sin dispositivos InfiniBand, un solo contenedor vLLM, sin Ray ni llama.cpp RPC) y `e2e` (la clasificacion). Para reabrirla si el equipo cambia (otro nodo, CX7 en pareja, otro modelo): `git mv tasks/done/DELTA-FORUM-DCP4-DECODE-STARVATION-FAIR-SCHEDULER-01.md tasks/backlog/` y `status: open`.
