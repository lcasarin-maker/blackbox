---
id: DELTA-FORUM-DFLASH-XGRAMMAR-STRUCTURED-OUTPUT-REGRESSION-01
kind: task
domain: VERDICT
title: "Validar forum dflash xgrammar structured output regression 01"
status: done
closed_at: 2026-10-15
closure_type: void_wontfix
reason: "El 500 reportado exige decodificacion especulativa (DFlash) con xgrammar recibiendo el bloque especulativo entero, sobre Qwen3.6. Aqui el motor sirve nemotron-local sin --speculative-config (speculative_config=None, cero metricas spec_decode) y ninguna ruta de lanzamiento del repo la activa; el drafter DSpark en disco no esta cableado. Decision de Luis 2026-10-15 (boleta 'Cerrar 3, mantener 2'): cerrar sin sujeto; reabrir si se activa un drafter DFlash/DSpark en el motor local."
evidence: {"pass": "tasks/evidence/DELTA-FORUM-DFLASH-XGRAMMAR-STRUCTURED-OUTPUT-REGRESSION-01/pass.txt", "fail": "tasks/evidence/DELTA-FORUM-DFLASH-XGRAMMAR-STRUCTURED-OUTPUT-REGRESSION-01/fail.txt", "e2e": "tasks/evidence/DELTA-FORUM-DFLASH-XGRAMMAR-STRUCTURED-OUTPUT-REGRESSION-01/e2e.txt"}
severity: P2
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-10-02
close_check: {"cmd": "python -m tools.check_harvest_accepted tasks/done/DELTA-FORUM-DFLASH-XGRAMMAR-STRUCTURED-OUTPUT-REGRESSION-01.md", "expect": "exit_zero", "porque": "Cerrada sin sujeto en este equipo (void_wontfix, decision de Luis 2026-10-15): no hay fix que probar, lo verificable por maquina es que la decision quedo registrada (closure_type y reason). El close_check anterior era `python3 -m pytest -q tests/test_debt_registration_controls.py::test_delta_forum_dflash_xgrammar_structured_output_regression_01`, un xfail que se retira con el cierre."}
---

## Referencia pública

Hilos de los que salió esta ficha (URL pública):

- https://forums.developer.nvidia.com/t/qwen3-6-27b-is-out/367503/292-295
- https://forums.developer.nvidia.com/t/glm-5-2-on-a-4-gb10-cluster-22-tok-s-decode-256k-ctx-recipe/374125/157
- https://forums.developer.nvidia.com/t/glm-5-2-on-a-4-gb10-cluster-22-tok-s-decode-256k-ctx-recipe/374125/202
- https://forums.developer.nvidia.com/t/gemma-4-models-which-vllm-version-any-prs-spotted/365490/114
- https://forums.developer.nvidia.com/t/dgx-spark-performance/356651/52
- https://forums.developer.nvidia.com/t/whats-the-best-speed-we-can-get-with-qwen-3-6-27b-without-quantizing/367561
- https://forums.developer.nvidia.com/t/deepseek-v4-flash-official-fp8-running-across-2x-dgx-spark-tp-2-mtp-200k-ctx-recipe-numbers/370309/195
- https://forums.developer.nvidia.com/t/deepseek-v4-flash-aiden-recipe-from-reddit-1m-token-session-operational-cuda-12-1-tailored-for-dgx-spark-gb10/372268/73
- https://forums.developer.nvidia.com/t/deepseek-v4-flash-vision-exp-is-released-as-open-weights/381911/302
- https://forums.developer.nvidia.com/t/qwen-qwen3-6-35b-a3b-and-fp8-has-landed/366822/213
- https://forums.developer.nvidia.com/t/deepseek-v4-flash-aiden-recipe-from-reddit-1m-token-session-operational-cuda-12-1-tailored-for-dgx-spark-gb10/372268/573
- https://forums.developer.nvidia.com/t/qwen-qwen3-6-35b-a3b-and-fp8-has-landed/366822/221
- https://forums.developer.nvidia.com/t/qwen-qwen3-6-35b-a3b-and-fp8-has-landed/366822/236
- https://forums.developer.nvidia.com/t/qwen-qwen3-6-35b-a3b-and-fp8-has-landed/366822/252
- https://forums.developer.nvidia.com/t/qwen-qwen3-6-35b-a3b-and-fp8-has-landed/366822/305
- https://forums.developer.nvidia.com/t/qwen3-5-122b-a10b-on-single-spark-up-to-51-tok-s-v2-1-patches-quick-start-benchmark/365639/315
- https://forums.developer.nvidia.com/t/fp4-on-dgx-spark-why-it-doesnt-scale-like-youd-expect/360142
- https://forums.developer.nvidia.com/t/deepseek-v4-flash-aiden-recipe-from-reddit-1m-token-session-operational-cuda-12-1-tailored-for-dgx-spark-gb10/372268/607
- https://github.com/tonyd2wild/DeepSeek-v4-Flash-Vision-Exp-DSpark-1M-NVFP4-KV-2x-DGX-Spark
- https://forums.developer.nvidia.com/t/deepseek-v4-flash-aiden-recipe-from-reddit-1m-token-session-operational-cuda-12-1-tailored-for-dgx-spark-gb10/372268/639

El texto de lo que dicen esos hilos se reubicó el 2026-11-01 a la base de conocimiento del dueño, por decisión del dueño: el conocimiento vive en el consumidor de conocimiento. Esta ficha conserva sólo el trabajo sobre la máquina y su registro de verificación; su `close_check` no cambió.

## Registro y responsable

Registro solicitado por Luis el 2026-10-02. Responsable: coordinación de Blackbox. Trabajo o revisión pendiente; la presencia del marcador no demuestra por sí sola un defecto.

## Criterio de cierre y control negativo

Aplicar el alcance y los controles concretos de la evidencia copiada arriba: stack/OEM y versiones fijadas, sujeto real, caso sano y negativo, resultados literales y rollback cuando haya intervención. Si faltan hardware, adjuntos, compatibilidad o permisos, imprimir could_not_run y conservar open. Un score agregado o mero estado de un dispositivo no acredita el resultado funcional. No instalar parches ni provocar fallo del host para registrar la ficha.

## Estado del verificador

La ficha permanece abierta. El test selector del close_check es una especificación pendiente, no una prueba existente ni un resultado ejecutado. Implementarlo exige comprobar el sujeto y su control negativo; la existencia de archivos o esta ficha no basta para cerrar.

Conservar comandos, salida literal y could_not_run incluso cero; una ejecución skipped o inaccesible deja el cierre pendiente. Reutilizar instrumentos nativos y pruebas existentes antes de crear código.

## Evaluación de instrumentos 2026-10-03

Reusa `tools/chat_sse_capture.py` para preservar chunks, finish y fragmentos de tool calls visibles al cliente; no valida JSON/argumentos, excepciones de xgrammar, HTTP, salud del proceso ni follow-up. Pruebas existentes del lector: `python3 -m pytest -q tests/test_chat_sse_capture.py` → 13 passed; eso valida el lector, no la regresión. Siguiente paso `deferred_lab`: imagen/model/parser/patch fijados, casos streaming y no-streaming para JSON y tool calls (incluido paralelo/follow-up), y control negativo de revisión/rollback. No hubo request ni tool execution.

## Clasificación del impedimento — 2026-10-04

- Categoría principal: `workload_or_lab`.
- Impedimento: No hay canario funcional real en la combinación DFlash/xgrammar/vLLM fijada; requiere runtime y replay negativo controlado.
- Evidencia faltante para cierre: digest/commits efectivos y capturas HTTP/parser/chunks/finish reason; casos stream/no-stream/tool/parallel/follow-up; rollback
- Siguiente acción: Preparar una matriz reproducible en canario GPU con stack fijado, ejecutar positivo y revisión incompatible como negativo, y guardar respuestas/logs y rollback.
- Responsable del siguiente paso: coordinación BB prepara; operador Luis ejecuta root/lab.
- Cierre completo accionable hoy: no. Preparación coordinable: sin acción adicional demostrada en esta revisión.
- Evidencias de clasificación: `tasks/backlog/DELTA-FORUM-DFLASH-XGRAMMAR-STRUCTURED-OUTPUT-REGRESSION-01.md`, `tasks/evidence/OPEN-96-CLASSIFICATION-2026-10-04/batches/batch_02.json`, `tasks/evidence/DELTA-FORUM-DFLASH-XGRAMMAR-STRUCTURED-OUTPUT-REGRESSION-01/ (directorio ausente al inspeccionar)`.
- Impedimentos de inspección: 1. El criterio original permanece intacto; esta clasificación conserva la ficha abierta.

## Estado (2026-10-11, /0 + /vote)

Bloqueada por criterio sin implementar: el `close_check` de esta ficha termina en `xfailed` y por eso sale con codigo 0 sin que el criterio real exista. Un `xfail` no es una verificacion y cerrar con el no es cierre. Cerrarla exige implementar la prueba real contra el sujeto (vLLM, NCCL, CX7 u otro hardware) con su control negativo. Decision del dueno el 2026-10-11: dejarla abierta y declarada, no cerrarla como `void_wontfix`.

## Adaptacion a este equipo (clasificacion 2026-10-13)
Aplicabilidad: adaptable · utilidad: media · lectura: completa.

Ficha-contenedor de ~12 hallazgos de foro sobre Qwen3.6/DFlash/DeepSeek/GLM/Gemma, ninguno servido aqui (solo nemotron-local en :8000). El riesgo transferible es JSON estricto, tool calls streamed/no streamed, paralelas y follow-up: tools/canario_motor.py (una ronda: nombre servido, JSON estricto, una llamada de herramienta) cubre solo la primera parte y no tiene streaming, paralelas ni follow-up.

Version para un solo nodo Gigabyte AI TOP ATOM: Extender tools/canario_motor.py con tool call streamed, llamadas paralelas, follow-up tras respuesta de herramienta y `tool_calls: []` vacio en deltas, contra nemotron-local; dividir los hallazgos de otros modelos (DFlash, DSpark, GLM, Gemma) en una ficha aparte o cerrarlos.

Perfil contra el que se clasifico: un nodo GB10 Gigabyte, DGX OS 7.2.3, kernel 6.17.0-1032-nvidia, driver 580.178.04, un contenedor vLLM (`nemotron-local`), sin InfiniBand/CX7 en pareja, sin Ray ni llama.cpp RPC. Clasificacion por lectura, sin control negativo: es una propuesta, no una verificacion.

## Avance (2026-10-14, "cierra todas las pendientes conforme a la opcion recomendada") -- NO se cierra: dudosa

Regla aplicada: `void_wontfix` solo si se mide que el sujeto no existe aqui. Aqui existe la mitad del sujeto:

```
$ docker exec nemotron-server pip show xgrammar | head -2
Name: xgrammar
Version: 0.2.3
$ docker exec nemotron-server python3 -c 'from vllm.config import StructuredOutputsConfig as S;print(S().backend)'
auto
$ docker inspect nemotron-server --format '{{json .Args}}' | grep -c -E 'speculative|dflash|dspark'
0   (rc=1)
$ curl -s -m 10 http://127.0.0.1:8000/metrics | grep -c spec_decode
0   (rc=1)
$ docker logs nemotron-server 2>&1 | grep -i -m1 speculative_config   (extracto)
... Initializing a V1 LLM engine (v0.27.1) with config: model='/models/llm/nemotron-3.5-lightning-30b-a3b-nvfp4', speculative_config=None, ...
$ grep -c dflash_config /srv/ai/models/llm/nemotron-3.5-lightning-30b-a3b-nvfp4-dspark/config.json
1   (rc=0; "architectures": ["Qwen3DSparkModel"], un drafter DFlash/DSpark para nemotron-local, en disco y sin usar)
```

- Existe: xgrammar 0.2.3 dentro de la imagen servida y el backend de salidas estructuradas en `auto` (el log de arranque dice `structured_outputs_config=StructuredOutputsConfig(backend='auto', ...)`), y un drafter DFlash para nemotron-local en disco (`nemotron-3.5-lightning-30b-a3b-nvfp4-dspark`, `dflash_config`).
- No existe hoy: decodificacion especulativa activa (`speculative_config=None`, cero metricas `spec_decode`), que es la condicion del 500 reportado (xgrammar recibiendo el bloque especulativo entero). Tampoco se sirve Qwen3.6, GLM ni Gemma.
- Falta para cerrar o declarar: que Luis decida si el drafter DSpark se va a activar. Si no se activa, el sujeto es solo "xgrammar sin especulacion", que es otra ficha; si se activa, la matriz JSON/tool calls streamed y no streamed con DFlash aplica tal cual a nemotron-local.

## Root Cause
No aplica a este equipo: la regresion DFlash+xgrammar reportada de Qwen3.6 requiere decodificacion especulativa; aqui el motor corre nemotron-3.5-lightning sin --speculative-config y ninguna ruta de lanzamiento del repo la habilita. xgrammar 0.2.3 sin especulacion es otra ficha, no esta.

## Regression Test
Ninguno: la ficha se cierra por no tener sujeto aqui. Los tests que la vigilaban (`tests/test_debt_registration_controls.py::test_delta_forum_dflash_xgrammar_structured_output_regression_01` y la parametrizacion de `tests/test_runtime_batch0*_controls.py` que la filtra `_ficha_abierta`) se retiran junto con sus entradas de `tests/known_failures.json` y de `.simplecode/backlog_baseline.json`.

## Verification Evidence
Tres rutas del frontmatter: `fail` (control negativo: el lanzamiento del motor no contiene `--speculative-config`, con control positivo de que la misma orden da 1 sobre una cadena que la contiene), `pass` (perfil medido del motor y de las rutas de lanzamiento del repo) y `e2e` (la decision registrada). Para reabrirla si el sujeto aparece: mover `tasks/done/DELTA-FORUM-DFLASH-XGRAMMAR-STRUCTURED-OUTPUT-REGRESSION-01.md` a `tasks/backlog/` con `git mv` y poner `status: open`.
