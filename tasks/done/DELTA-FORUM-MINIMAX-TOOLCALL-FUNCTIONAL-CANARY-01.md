---
id: DELTA-FORUM-MINIMAX-TOOLCALL-FUNCTIONAL-CANARY-01
kind: task
domain: VERDICT
title: "Validar forum minimax toolcall functional canary 01"
status: done
closed_at: 2026-10-14
closure_type: void_wontfix
reason: "MiniMax no se sirve aqui ni hay pesos MiniMax/Qwen3.8 en disco, y no hay Ray; el gate funcional texto->tool call->texto ya existe como tools/canario_motor.py. Decision de Luis 2026-10-14: cerrar sin sujeto; reabrir si se sirve MiniMax o si el canario local ve una tool call que cuelga el motor."
evidence: {"pass": "tasks/evidence/DELTA-FORUM-MINIMAX-TOOLCALL-FUNCTIONAL-CANARY-01/pass.txt", "fail": "tasks/evidence/DELTA-FORUM-MINIMAX-TOOLCALL-FUNCTIONAL-CANARY-01/fail.txt", "e2e": "tasks/evidence/DELTA-FORUM-MINIMAX-TOOLCALL-FUNCTIONAL-CANARY-01/e2e.txt"}
severity: P2
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-10-02
close_check: {"cmd": "python -m tools.check_harvest_accepted tasks/done/DELTA-FORUM-MINIMAX-TOOLCALL-FUNCTIONAL-CANARY-01.md", "expect": "exit_zero", "porque": "Cerrada sin sujeto en este equipo (void_wontfix, decision de Luis 2026-10-14): no hay fix que probar, lo verificable por maquina es que la decision quedo registrada (closure_type y reason). El close_check anterior era `python3 -m pytest -q tests/test_debt_registration_controls.py::test_delta_forum_minimax_toolcall_functional_canary_01`, que sin captura real del sujeto no puede pasar; sin sujeto aqui no hay captura posible."}
---

## Referencia pública

Hilos de los que salió esta ficha (URL pública):

- https://forums.developer.nvidia.com/t/minimax-m2-7-nfvp4-recipe-benchmarks/366324
- https://forums.developer.nvidia.com/t/qwen3-8-flash-fp8-dual-sparks/381440/40
- https://forums.developer.nvidia.com/t/qwen3-8-flash-fp8-dual-sparks/381440/69

El texto de lo que dicen esos hilos se reubicó el 2026-11-01 a la base de conocimiento del dueño, por decisión del dueño: el conocimiento vive en el consumidor de conocimiento. Esta ficha conserva sólo el trabajo sobre la máquina y su registro de verificación; su `close_check` no cambió.

## Registro y responsable

Registro solicitado por Luis el 2026-10-02. Responsable: coordinación de Blackbox. Trabajo o revisión pendiente; la presencia del marcador no demuestra por sí sola un defecto.

## Criterio de cierre y control negativo

Aplicar el alcance y los controles concretos de la evidencia copiada arriba: stack/OEM y versiones fijadas, sujeto real, caso sano y negativo, resultados literales y rollback cuando haya intervención. Si faltan hardware, adjuntos, compatibilidad o permisos, imprimir could_not_run y conservar open. Un score agregado o mero estado de un dispositivo no acredita el resultado funcional. No instalar parches ni provocar fallo del host para registrar la ficha.

## Estado del verificador

La ficha permanece abierta. El test selector del close_check es una especificación pendiente, no una prueba existente ni un resultado ejecutado. Implementarlo exige comprobar el sujeto y su control negativo; la existencia de archivos o esta ficha no basta para cerrar.

Conservar comandos, salida literal y could_not_run incluso cero; una ejecución skipped o inaccesible deja el cierre pendiente. Reutilizar instrumentos nativos y pruebas existentes antes de crear código.

### Evidencia de instrumento (2026-10-03)

Estado: parcial, con lector offline desarrollado para chunks Chat Completions SSE; conserva deltas de texto/tool call y finish reason. No existe captura SSE nativa del stack fijado ni ejecución observada del mock, vida del proceso o rollback; el canario funcional queda `could_not_run`. La ficha sigue abierta y el `close_check` original no cambió. Informe: `docs/evidence/BB-INSTRUMENTS-requests.md`.

## Clasificación del impedimento — 2026-10-04

- Categoría principal: `workload_or_lab`.
- Impedimento: No hay captura SSE nativa ni ejecución observada del mock, salud del proceso o rollback para digest de imagen fijado.
- Evidencia faltante para cierre: respuesta HTTP/SSE cruda; argumentos byte-exactos; resultado mock; finish reason; continuidad del proceso y rollback
- Siguiente acción: Ejecutar en canario GPU el ciclo texto→tool mock→texto en digest fijado y control negativo; conservar SSE y logs de RPC/timeout.
- Responsable del siguiente paso: coordinación BB prepara; operador Luis ejecuta root/lab.
- Cierre completo accionable hoy: no. Preparación coordinable: sin acción adicional demostrada en esta revisión.
- Evidencias de clasificación: `tasks/backlog/DELTA-FORUM-MINIMAX-TOOLCALL-FUNCTIONAL-CANARY-01.md`, `tasks/evidence/OPEN-96-CLASSIFICATION-2026-10-04/batches/batch_02.json`, `tasks/evidence/DELTA-FORUM-MINIMAX-TOOLCALL-FUNCTIONAL-CANARY-01/ (directorio ausente al inspeccionar)`.
- Impedimentos de inspección: 1. El criterio original permanece intacto; esta clasificación conserva la ficha abierta.

## Estado (2026-10-11, /0 + /vote)

Bloqueada por criterio sin implementar: el `close_check` de esta ficha termina en `xfailed` y por eso sale con codigo 0 sin que el criterio real exista. Un `xfail` no es una verificacion y cerrar con el no es cierre. Cerrarla exige implementar la prueba real contra el sujeto (vLLM, NCCL, CX7 u otro hardware) con su control negativo. Decision del dueno el 2026-10-11: dejarla abierta y declarada, no cerrarla como `void_wontfix`.

## Adaptacion a este equipo (clasificacion 2026-10-13)
Aplicabilidad: ya_cubierta · utilidad: media · lectura: completa.

El gate funcional texto->tool-call->texto ya existe como tools/canario_motor.py (`bb canario`, SPEC.md ~fila 287: nombre servido, JSON estricto, tool-call con finish_reason=tool_calls). No hay MiniMax ni dos GB10; el residuo es verificar argumentos byte-exactos con nombre de archivo puntuado y vida del proceso tras la segunda peticion, y el delta Qwen3.8 dual-Spark/cudagraph no aplica.

Version para un solo nodo Gigabyte AI TOP ATOM: Extender canario_motor con la secuencia texto->tool-call con nombre de archivo puntuado->texto verificando argumentos byte-exactos y vida del proceso; descartar las partes dual-Spark/MiniMax/Ray.

Perfil contra el que se clasifico: un nodo GB10 Gigabyte, DGX OS 7.2.3, kernel 6.17.0-1032-nvidia, driver 580.178.04, un contenedor vLLM (`nemotron-local`), sin InfiniBand/CX7 en pareja, sin Ray ni llama.cpp RPC. Clasificacion por lectura, sin control negativo: es una propuesta, no una verificacion.

## Root Cause
No aplica a este equipo: el cuelgue en la primera tool call es de MiniMax-M2.7 con Ray (y el delta Qwen3.8 dual-Spark); aqui no hay pesos MiniMax ni Qwen3.8, el contenedor no tiene Ray y la secuencia texto -> tool call -> texto ya la ejercita `tools/canario_motor.py`.

## Regression Test
Ninguno: la ficha se cierra por no tener sujeto aqui. El test que la vigilaba (`tests/test_debt_registration_controls.py::test_delta_forum_minimax_toolcall_functional_canary_01`, un xfail) se retira junto con su entrada de `tests/known_failures.json`, y la parametrizacion `tests/test_runtime_batch02_controls.py::test_real_capture_close_gate_requires_raw_capture[DELTA-FORUM-MINIMAX-TOOLCALL-FUNCTIONAL-CANARY-01]` deja de generarse (la filtra `_ficha_abierta`) y pierde tambien su entrada. El verificador y sus pruebas unitarias con fixtures siguen vivos.

## Verification Evidence
Tres rutas del frontmatter: `fail` (control negativo: las ordenes que buscan el sujeto salen con rc distinto de 0), `pass` (perfil medido, con control positivo de que las mismas herramientas encuentran lo que si existe) y `e2e` (la decision registrada). Datos de la maquina redactados con el PATRON de `tests/test_sin_datos_privados.py`. Para reabrirla si el sujeto aparece: `git mv tasks/done/DELTA-FORUM-MINIMAX-TOOLCALL-FUNCTIONAL-CANARY-01.md tasks/backlog/` y `status: open`.
