---
id: DELTA-FORUM-MTP-ACCEPTANCE-AND-SEMANTIC-CONTROL-01
kind: task
domain: VERDICT
title: "Validar forum mtp acceptance and semantic control 01"
status: done
closed_at: 2026-10-15
closure_type: void_wontfix
reason: "La aceptacion MTP cero del hilo 361163 es de Qwen3-Coder-Next con MTP; aqui el motor sirve nemotron-local sin --speculative-config, asi que no hay MTP ni aceptacion que medir, y ninguna ruta de lanzamiento del repo la activa. Decision de Luis 2026-10-15 (boleta 'Cerrar 3, mantener 2'): cerrar sin sujeto; reabrir si se activa decodificacion especulativa (MTP, DFlash o DSpark) en el motor local."
evidence: {"pass": "tasks/evidence/DELTA-FORUM-MTP-ACCEPTANCE-AND-SEMANTIC-CONTROL-01/pass.txt", "fail": "tasks/evidence/DELTA-FORUM-MTP-ACCEPTANCE-AND-SEMANTIC-CONTROL-01/fail.txt", "e2e": "tasks/evidence/DELTA-FORUM-MTP-ACCEPTANCE-AND-SEMANTIC-CONTROL-01/e2e.txt"}
severity: P2
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-10-02
close_check: {"cmd": "python -m tools.check_harvest_accepted tasks/done/DELTA-FORUM-MTP-ACCEPTANCE-AND-SEMANTIC-CONTROL-01.md", "expect": "exit_zero", "porque": "Cerrada sin sujeto en este equipo (void_wontfix, decision de Luis 2026-10-15): no hay fix que probar, lo verificable por maquina es que la decision quedo registrada (closure_type y reason). El close_check anterior era `python3 -m pytest -q tests/test_debt_registration_controls.py::test_delta_forum_mtp_acceptance_and_semantic_control_01`, un xfail que se retira con el cierre."}
---

## Registro y responsable

Registro solicitado por Luis el 2026-10-02. Responsable: coordinación de Blackbox. Trabajo o revisión pendiente; la presencia del marcador no demuestra por sí sola un defecto.

## Evidencia y alcance

Trabajo separado del ámbito de su ficha madre, conservando la fuente original. Los reportes de foro siguen sin validación local y no se convierten en recomendaciones automáticas.

### DELTA-FORUM-MTP-ACCEPTANCE-AND-SEMANTIC-CONTROL-01

[361163](https://forums.developer.nvidia.com/t/we-unlocked-nvfp4-on-the-dgx-spark-20-faster-than-awq/361163) adds a direct MTP counterexample: one owner reports Qwen3-Coder-Next NVFP4 at about 38 tok/s without MTP and about 26 tok/s with MTP, with zero acceptance; separate reports vary by model/build, and a cold restart reportedly restored speed without rebuilding. Benchmark labels also differ: speculative accepted output rate and target decode rate are distinct. The repository patches, images, scripts, screenshots and raw result files were not audited, and no matched independent correctness run appears in the thread. A later Qwen/PrismaQuant thread [367085, posts 71–74, 139 and 155–160](https://forums.developer.nvidia.com/t/introducing-prismaquant/367085/71) also reports that MTP/DFlash behavior changes with context pressure, concurrency and backend; one 50%-context-pressure test saw little difference between MTP=2 and 4, while other results changed after DFlash/SWA build changes. This supplies no universal speculative-token count.

For each pinned model/image/backend, compare MTP on/off with the same prompts, output limits, concurrency and warm/cold state. Record per-position acceptance, semantic/tool correctness, prefill and decode latency, target decode rate, user-visible rate and memory. Gate zero acceptance or failed output checks and retain the last known-good recipe for rollback; do not infer a universal NVFP4 or MTP setting from this thread.

Fuentes: tasks/backlog/FEATURE-FORUM-GB10-RUNTIME-COMPAT-01.md.

## Criterio de cierre y control negativo

Aplicar el alcance y los controles concretos de la evidencia copiada arriba: stack/OEM y versiones fijadas, sujeto real, caso sano y negativo, resultados literales y rollback cuando haya intervención. Si faltan hardware, adjuntos, compatibilidad o permisos, imprimir could_not_run y conservar open. Un score agregado o mero estado de un dispositivo no acredita el resultado funcional. No instalar parches ni provocar fallo del host para registrar la ficha.

## Estado del verificador

La ficha permanece abierta. El test selector del close_check es una especificación pendiente, no una prueba existente ni un resultado ejecutado. Implementarlo exige comprobar el sujeto y su control negativo; la existencia de archivos o esta ficha no basta para cerrar.

Conservar comandos, salida literal y could_not_run incluso cero; una ejecución skipped o inaccesible deja el cierre pendiente. Reutilizar instrumentos nativos y pruebas existentes antes de crear código.

### Evidencia de instrumento (2026-10-03)

Estado: `blocked` para aceptación MTP: los chunks Chat Completions no exponen aceptación por posición, y no hay captura backend nativa ni A/B semántico pareado. El lector SSE solo conserva evidencia de salida del cliente y no aporta esa señal. La ficha sigue abierta y el `close_check` original no cambió. Informe: `docs/evidence/BB-INSTRUMENTS-requests.md`.

## Clasificación del impedimento — 2026-10-04

- Categoría principal: `workload_or_lab`.
- Impedimento: No existe captura local fijada de MTP/model/tokenizer/prompt con resultado semántico y aceptación por posición frente a referencia; readiness o score agregado no cubren el criterio.
- Evidencia faltante para cierre: No existe captura local fijada de MTP/model/tokenizer/prompt con resultado semántico y aceptación por posición frente a referencia; readiness o score agregado no cubren el criterio.
- Siguiente acción: Coordinación BB: definir criterios semánticos y salida por posición; operador Luis: ejecutar el canario MTP fijado y aportar resultados sanos/negativos. Ref explícita: tasks/backlog/DELTA-FORUM-MTP-ACCEPTANCE-AND-SEMANTIC-CONTROL-01.md y tests/test_debt_registration_controls.py. Ref explícita: tasks/backlog/DELTA-FORUM-MTP-ACCEPTANCE-AND-SEMANTIC-CONTROL-01.md y tasks/evidence/CLOSURE-CONTROLS-2026-10-03/DELTA-FORUM-MTP-ACCEPTANCE-AND-SEMANTIC-CONTROL-01-original-selector-current.log.
- Responsable del siguiente paso: Coordinación BB prepara/implementa; cuando la acción requiere root/lab/hardware, operador Luis aporta y ejecuta el sujeto indicado..
- Cierre completo accionable hoy: no. Preparación coordinable: sí.
- Evidencias de clasificación: `tasks/backlog/DELTA-FORUM-MTP-ACCEPTANCE-AND-SEMANTIC-CONTROL-01.md`, `tests/test_debt_registration_controls.py`, `tasks/evidence/OPEN-96-CLASSIFICATION-2026-10-04/batches/batch_03.json`, `tasks/evidence/CLOSURE-CONTROLS-2026-10-03/DELTA-FORUM-MTP-ACCEPTANCE-AND-SEMANTIC-CONTROL-01-original-selector-current.log`.
- Impedimentos de inspección: 0. El criterio original permanece intacto; esta clasificación conserva la ficha abierta.

## Estado (2026-10-11, /0 + /vote)

Bloqueada por criterio sin implementar: el `close_check` de esta ficha termina en `xfailed` y por eso sale con codigo 0 sin que el criterio real exista. Un `xfail` no es una verificacion y cerrar con el no es cierre. Cerrarla exige implementar la prueba real contra el sujeto (vLLM, NCCL, CX7 u otro hardware) con su control negativo. Decision del dueno el 2026-10-11: dejarla abierta y declarada, no cerrarla como `void_wontfix`.

## Adaptacion a este equipo (clasificacion 2026-10-13)
Aplicabilidad: adaptable · utilidad: media · lectura: completa.

El hilo 361163 trata de Qwen3-Coder-Next NVFP4 con MTP, que aqui no se sirve; el mecanismo (aceptacion cero que vuelve el modelo mas lento sin error) puede existir en nemotron-local si su receta usa decodificacion especulativa, dato que no pude verificar. tools/canario_motor.py ya comprueba JSON y tool-call pero no tasa de aceptacion.

Version para un solo nodo Gigabyte AI TOP ATOM: Extender canario_motor o un sensor hermano para leer las metricas de aceptacion especulativa de nemotron-local (si la receta las activa) y comparar tok/s on/off con el mismo prompt, marcando aceptacion 0 como FALLA; si la receta no usa MTP, cerrar como no aplicable.

Perfil contra el que se clasifico: un nodo GB10 Gigabyte, DGX OS 7.2.3, kernel 6.17.0-1032-nvidia, driver 580.178.04, un contenedor vLLM (`nemotron-local`), sin InfiniBand/CX7 en pareja, sin Ray ni llama.cpp RPC. Clasificacion por lectura, sin control negativo: es una propuesta, no una verificacion.

## Avance (2026-10-14, "cierra todas las pendientes conforme a la opcion recomendada") -- NO se cierra: dudosa

Regla aplicada: `void_wontfix` solo si se mide que el sujeto no existe aqui. La clasificacion del 2026-10-13 decia "si la receta no usa MTP, cerrar como no aplicable"; medido hoy:

```
$ docker inspect nemotron-server --format '{{json .Args}}' | grep -c -E 'speculative|dflash|dspark'
0   (rc=1)
$ curl -s -m 10 http://127.0.0.1:8000/metrics | grep -c spec_decode
0   (rc=1)
$ docker logs nemotron-server 2>&1 | grep -i -m1 speculative_config   (extracto)
... Initializing a V1 LLM engine (v0.27.1) with config: model='/models/llm/nemotron-3.5-lightning-30b-a3b-nvfp4', speculative_config=None, ...
$ grep -c dflash_config /srv/ai/models/llm/nemotron-3.5-lightning-30b-a3b-nvfp4-dspark/config.json
1   (rc=0; "architectures": ["Qwen3DSparkModel"], un drafter DFlash/DSpark para nemotron-local, en disco y sin usar)
```

- No existe hoy: decodificacion especulativa activa en el motor (ni MTP ni DFlash/DSpark): `speculative_config=None` y cero metricas `spec_decode`, asi que no hay aceptacion que medir.
- Existe: el drafter DSpark de nemotron-local esta en disco (`Qwen3DSparkModel` con `dflash_config`), descargado para activarse. Con el GLM se cerro porque no estaba "ni servido ni en disco"; aqui esta en disco.
- Falta para cerrar o declarar: que Luis decida si el drafter se va a activar. Si no, cerrar `void_wontfix` con la medicion de arriba; si si, el A/B on/off con aceptacion por posicion (las metricas `vllm:spec_decode_*` de /metrics) aplica a nemotron-local.

## Root Cause
No aplica a este equipo: la aceptacion MTP de Qwen3-Coder-Next no tiene sujeto aqui: el motor corre sin --speculative-config (speculative_config=None), no hay metricas de aceptacion y ninguna ruta de lanzamiento del repo la habilita.

## Regression Test
Ninguno: la ficha se cierra por no tener sujeto aqui. Los tests que la vigilaban (`tests/test_debt_registration_controls.py::test_delta_forum_mtp_acceptance_and_semantic_control_01` y la parametrizacion de `tests/test_runtime_batch0*_controls.py` que la filtra `_ficha_abierta`) se retiran junto con sus entradas de `tests/known_failures.json` y de `.simplecode/backlog_baseline.json`.

## Verification Evidence
Tres rutas del frontmatter: `fail` (control negativo: el lanzamiento del motor no contiene `--speculative-config`, con control positivo de que la misma orden da 1 sobre una cadena que la contiene), `pass` (perfil medido del motor y de las rutas de lanzamiento del repo) y `e2e` (la decision registrada). Para reabrirla si el sujeto aparece: mover `tasks/done/DELTA-FORUM-MTP-ACCEPTANCE-AND-SEMANTIC-CONTROL-01.md` a `tasks/backlog/` con `git mv` y poner `status: open`.
