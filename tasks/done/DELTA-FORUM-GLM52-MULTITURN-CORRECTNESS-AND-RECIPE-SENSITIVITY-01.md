---
id: DELTA-FORUM-GLM52-MULTITURN-CORRECTNESS-AND-RECIPE-SENSITIVITY-01
kind: task
domain: VERDICT
title: "Validar forum glm52 multiturn correctness and recipe sensitivity 01"
status: done
closed_at: 2026-10-14
closure_type: void_wontfix
reason: "GLM-5.2 no se sirve aqui ni hay pesos GLM en disco: el motor sirve solo nemotron-local. Decision de Luis 2026-10-14: cerrar sin sujeto; reabrir si se sirve GLM o si el vLLM local muestra texto incoherente en conversaciones crecientes con prefix cache."
evidence: {"pass": "tasks/evidence/DELTA-FORUM-GLM52-MULTITURN-CORRECTNESS-AND-RECIPE-SENSITIVITY-01/pass.txt", "fail": "tasks/evidence/DELTA-FORUM-GLM52-MULTITURN-CORRECTNESS-AND-RECIPE-SENSITIVITY-01/fail.txt", "e2e": "tasks/evidence/DELTA-FORUM-GLM52-MULTITURN-CORRECTNESS-AND-RECIPE-SENSITIVITY-01/e2e.txt"}
severity: P2
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-10-02
close_check: {"cmd": "python -m tools.check_harvest_accepted tasks/done/DELTA-FORUM-GLM52-MULTITURN-CORRECTNESS-AND-RECIPE-SENSITIVITY-01.md", "expect": "exit_zero", "porque": "Cerrada sin sujeto en este equipo (void_wontfix, decision de Luis 2026-10-14): no hay fix que probar, lo verificable por maquina es que la decision quedo registrada (closure_type y reason). El close_check anterior era `python3 -m pytest -q tests/test_debt_registration_controls.py::test_delta_forum_glm52_multiturn_correctness_and_recipe_sensitivity_01`, que sin captura real del sujeto no puede pasar; sin sujeto aqui no hay captura posible."}
---

## Referencia pública

Hilos de los que salió esta ficha (URL pública):

- https://forums.developer.nvidia.com/t/377598/12

El texto de lo que dicen esos hilos se reubicó el 2026-11-01 a la base de conocimiento del dueño, por decisión del dueño: el conocimiento vive en el consumidor de conocimiento. Esta ficha conserva sólo el trabajo sobre la máquina y su registro de verificación; su `close_check` no cambió.

## Registro y responsable

Registro solicitado por Luis el 2026-10-02. Responsable: coordinación de Blackbox. Trabajo o revisión pendiente; la presencia del marcador no demuestra por sí sola un defecto.

## Criterio de cierre y control negativo

Aplicar el alcance y los controles concretos de la evidencia copiada arriba: stack/OEM y versiones fijadas, sujeto real, caso sano y negativo, resultados literales y rollback cuando haya intervención. Si faltan hardware, adjuntos, compatibilidad o permisos, imprimir could_not_run y conservar open. Un score agregado o mero estado de un dispositivo no acredita el resultado funcional. No instalar parches ni provocar fallo del host para registrar la ficha.

## Estado del verificador

La ficha permanece abierta. El test selector del close_check es una especificación pendiente, no una prueba existente ni un resultado ejecutado. Implementarlo exige comprobar el sujeto y su control negativo; la existencia de archivos o esta ficha no basta para cerrar.

Conservar comandos, salida literal y could_not_run incluso cero; una ejecución skipped o inaccesible deja el cierre pendiente. Reutilizar instrumentos nativos y pruebas existentes antes de crear código.

## Evaluación de instrumentos 2026-10-03

Instrumentación local reutilizable: `tools/chat_sse_capture.py` conserva deltas y finish visibles al cliente, pero no mide corrección multivuelta ni prueba tokenizer/logprobs, cache, reasoning on/off o límite de iteraciones de tools. No hay captura local del stack GLM/FP8/MXFP4 ni reproducciones. Estado `deferred_lab`: canario acotado y controlado sobre digest/tokenizer/params fijados, con prompt único vs prefijo creciente y controles separados de formato/razonamiento; comparar finish y resultados literales sin enviar prompts en este informe.

## Clasificación del impedimento — 2026-10-04

- Categoría principal: `workload_or_lab`.
- Impedimento: SSE conserva salida visible, pero no hay captura local del stack GLM52/FP8/MXFP4 ni comparación multivuelta con tokenizer/cache/reasoning/iteración de herramientas fijados.
- Evidencia faltante para cierre: SSE conserva salida visible, pero no hay captura local del stack GLM52/FP8/MXFP4 ni comparación multivuelta con tokenizer/cache/reasoning/iteración de herramientas fijados.
- Siguiente acción: Coordinación BB: definir canario y salida comparable; operador Luis: ejecutar replay con digest/tokenizer/params fijados y controles de prefijo/formato. Ref explícita: tasks/backlog/DELTA-FORUM-GLM52-MULTITURN-CORRECTNESS-AND-RECIPE-SENSITIVITY-01.md y tests/test_debt_registration_controls.py. Ref explícita: tasks/backlog/DELTA-FORUM-GLM52-MULTITURN-CORRECTNESS-AND-RECIPE-SENSITIVITY-01.md y tasks/evidence/CLOSURE-CONTROLS-2026-10-03/DELTA-FORUM-GLM52-MULTITURN-CORRECTNESS-AND-RECIPE-SENSITIVITY-01-original-selector-current.log.
- Responsable del siguiente paso: Coordinación BB prepara/implementa; cuando la acción requiere root/lab/hardware, operador Luis aporta y ejecuta el sujeto indicado..
- Cierre completo accionable hoy: no. Preparación coordinable: sí.
- Evidencias de clasificación: `tasks/backlog/DELTA-FORUM-GLM52-MULTITURN-CORRECTNESS-AND-RECIPE-SENSITIVITY-01.md`, `tests/test_debt_registration_controls.py`, `tasks/evidence/OPEN-96-CLASSIFICATION-2026-10-04/batches/batch_06.json`, `tasks/evidence/CLOSURE-CONTROLS-2026-10-03/DELTA-FORUM-GLM52-MULTITURN-CORRECTNESS-AND-RECIPE-SENSITIVITY-01-original-selector-current.log`.
- Impedimentos de inspección: 0. El criterio original permanece intacto; esta clasificación conserva la ficha abierta.

## Estado (2026-10-11, /0 + /vote)

Bloqueada por criterio sin implementar: el `close_check` de esta ficha termina en `xfailed` y por eso sale con codigo 0 sin que el criterio real exista. Un `xfail` no es una verificacion y cerrar con el no es cierre. Cerrarla exige implementar la prueba real contra el sujeto (vLLM, NCCL, CX7 u otro hardware) con su control negativo. Decision del dueno el 2026-10-11: dejarla abierta y declarada, no cerrarla como `void_wontfix`.

## Adaptacion a este equipo (clasificacion 2026-10-13)
Aplicabilidad: adaptable · utilidad: media · lectura: completa.

GLM-5.2 FP8/MXFP4 en 4 GB10 no se sirve aqui, pero el mecanismo (texto incoherente tras 80-95K tokens y 15+ turnos con prefix caching, needle tests de prompt unico sanos; bucle de ~200 llamadas con tool_choice=required) puede ocurrir en el vLLM local. tools/chat_sse_capture.py y tools/canario_motor.py no miden conversaciones crecientes ni limite de iteraciones de herramientas.

Version para un solo nodo Gigabyte AI TOP ATOM: Canario de sesion multi-turno creciente con prefix cache sobre nemotron-local (prompt unico vs prefijo creciente, finish_reason, coherencia semantica) y tope de iteraciones con tool_choice=required; sin los parametros de GLM.

Perfil contra el que se clasifico: un nodo GB10 Gigabyte, DGX OS 7.2.3, kernel 6.17.0-1032-nvidia, driver 580.178.04, un contenedor vLLM (`nemotron-local`), sin InfiniBand/CX7 en pareja, sin Ray ni llama.cpp RPC. Clasificacion por lectura, sin control negativo: es una propuesta, no una verificacion.

## Root Cause
No aplica a este equipo: la deriva multiturno reportada es de GLM-5.2 Hybrid FP8/MXFP4 sobre 4 GB10; aqui `/v1/models` lista solo nemotron-local y ningun contenedor ni directorio de pesos es GLM.

## Regression Test
Ninguno: la ficha se cierra por no tener sujeto aqui. El test que la vigilaba (`tests/test_debt_registration_controls.py::test_delta_forum_glm52_multiturn_correctness_and_recipe_sensitivity_01`, un xfail) se retira junto con su entrada de `tests/known_failures.json`, y la parametrizacion `tests/test_runtime_batch01_controls.py::test_real_capture_close_gate_requires_actual_capture[DELTA-FORUM-GLM52-MULTITURN-CORRECTNESS-AND-RECIPE-SENSITIVITY-01]` deja de generarse (la filtra `_ficha_abierta`) y pierde tambien su entrada. El verificador y sus pruebas unitarias con fixtures siguen vivos.

## Verification Evidence
Tres rutas del frontmatter: `fail` (control negativo: las ordenes que buscan el sujeto salen con rc distinto de 0), `pass` (perfil medido, con control positivo de que las mismas herramientas encuentran lo que si existe) y `e2e` (la decision registrada). Datos de la maquina redactados con el PATRON de `tests/test_sin_datos_privados.py`. Para reabrirla si el sujeto aparece: `git mv tasks/done/DELTA-FORUM-GLM52-MULTITURN-CORRECTNESS-AND-RECIPE-SENSITIVITY-01.md tasks/backlog/` y `status: open`.
