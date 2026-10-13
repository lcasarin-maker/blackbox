---
id: DELTA-FORUM-M2-COMPACTION-STATE-VALIDATION-01
kind: task
domain: VERDICT
title: "Validar forum m2 compaction state validation 01"
status: done
closed_at: 2026-10-13
closure_type: void_wontfix
reason: "Reporte de operador con MiniMax M2.1 y llama.cpp, no servidos en este equipo (solo nemotron-local en vLLM), sin logs ni reproduccion; el canario multi-turno con cache-reset se registra en DELTA-FORUM-GLM52-MULTITURN-CORRECTNESS-AND-RECIPE-SENSITIVITY-01. Decision de Luis 2026-10-13: deprecar por aplicabilidad, con independencia de la nota del 2026-10-11 (que dejaba abiertas las fichas con xfail porque un xfail no verifica nada)."
evidence: {"pass": "tasks/evidence/DELTA-FORUM-M2-COMPACTION-STATE-VALIDATION-01/pass.txt", "fail": "tasks/evidence/DELTA-FORUM-M2-COMPACTION-STATE-VALIDATION-01/fail.txt", "e2e": "tasks/evidence/DELTA-FORUM-M2-COMPACTION-STATE-VALIDATION-01/e2e.txt"}
severity: P2
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-10-02
close_check: {"cmd": "python3 -m pytest -q tests/test_debt_registration_controls.py::test_delta_forum_m2_compaction_state_validation_01", "expect": "exit_zero", "porque": "Aplicar el alcance y los controles concretos de la evidencia copiada arriba: stack/OEM y versiones fijadas, sujeto real, caso sano y negativo, resultados literales y rollback cuando haya intervención. Si faltan hardware, adjuntos, compatibilidad o permisos, imprimir could_not_run y conservar open. Un score agregado o mero estado de un dispositivo no acredita el resultado funcional. No instalar parches ni provocar fallo del host para registrar la ficha."}
---

## Registro y responsable

Registro solicitado por Luis el 2026-10-02. Responsable: coordinación de Blackbox. Trabajo o revisión pendiente; la presencia del marcador no demuestra por sí sola un defecto.

## Evidencia y alcance

Trabajo separado del ámbito de su ficha madre, conservando la fuente original. Los reportes de foro siguen sin validación local y no se convierten en recomendaciones automáticas.

**DELTA-FORUM-M2-COMPACTION-STATE-VALIDATION-01.** En un hilo de MiniMax M2.1, un operador informa que después de varias compactions con OpenCode+llama.cpp cae el throughput de prefill/decode, degrada la calidad y fallan tool calls; dice que vio algo parecido con otro build vLLM. La causa sugerida —corrupción de estado CUDA-graph al limpiar KV— es solo su paráfrasis, sin versión completa, logs ni reproducción; otra respuesta reporta ausencia del fallo hasta 120K ([356118, posts 17 y 20](https://forums.developer.nvidia.com/t/356118/17)). Añadir al canary de runtime, para modelos/harnesses exactos que limpien o compacten KV, una secuencia larga que cruce límites de compaction/cache-reset, seguida de tool calls, salida semántica y métricas prefill/decode/process/host; repetir con reset limpio y control sin compaction. No atribuirlo a GB10/driver ni recomendar una opción NVFP4/graph como fix.

Fuentes: tasks/backlog/FEATURE-FORUM-GB10-RUNTIME-COMPAT-01.md.

## Criterio de cierre y control negativo

Aplicar el alcance y los controles concretos de la evidencia copiada arriba: stack/OEM y versiones fijadas, sujeto real, caso sano y negativo, resultados literales y rollback cuando haya intervención. Si faltan hardware, adjuntos, compatibilidad o permisos, imprimir could_not_run y conservar open. Un score agregado o mero estado de un dispositivo no acredita el resultado funcional. No instalar parches ni provocar fallo del host para registrar la ficha.

## Estado del verificador

La ficha permanece abierta. El test selector del close_check es una especificación pendiente, no una prueba existente ni un resultado ejecutado. Implementarlo exige comprobar el sujeto y su control negativo; la existencia de archivos o esta ficha no basta para cerrar.

Conservar comandos, salida literal y could_not_run incluso cero; una ejecución skipped o inaccesible deja el cierre pendiente. Reutilizar instrumentos nativos y pruebas existentes antes de crear código.
## Evaluación de instrumentos 2026-10-03

Reusa `tools/chat_sse_capture.py` para deltas/finish visibles, pero no identifica compaction/reset del KV, métricas prefill/decode o calidad de tool calls después del límite. No hay log de sesión/versions ni captura local. Estado `deferred_lab`: secuencia fijada que cruce compaction/cache reset, control sin compaction, y observaciones semánticas/finish/pre-fill/decode/proceso con tool calls; la causa CUDA-graph reportada permanece hipótesis.

## Clasificación del impedimento — 2026-10-04

- Categoría principal: `workload_or_lab`.
- Impedimento: No hay log local con stack/modelo fijados, límite de compaction/KV reset, control sin compaction ni tool-call/calidad y métricas posteriores.
- Evidencia faltante para cierre: No hay log local con stack/modelo fijados, límite de compaction/KV reset, control sin compaction ni tool-call/calidad y métricas posteriores.
- Siguiente acción: Coordinación BB: preparar harness y esquema de observación; operador Luis: capturar sesiones canary con/sin compaction sobre sujeto disponible. Ref explícita: tasks/backlog/DELTA-FORUM-M2-COMPACTION-STATE-VALIDATION-01.md y tests/test_debt_registration_controls.py. Ref explícita: tasks/backlog/DELTA-FORUM-M2-COMPACTION-STATE-VALIDATION-01.md y tasks/evidence/CLOSURE-CONTROLS-2026-10-03/DELTA-FORUM-M2-COMPACTION-STATE-VALIDATION-01-original-selector-current.log.
- Responsable del siguiente paso: Coordinación BB prepara/implementa; cuando la acción requiere root/lab/hardware, operador Luis aporta y ejecuta el sujeto indicado..
- Cierre completo accionable hoy: no. Preparación coordinable: sí.
- Evidencias de clasificación: `tasks/backlog/DELTA-FORUM-M2-COMPACTION-STATE-VALIDATION-01.md`, `tests/test_debt_registration_controls.py`, `tasks/evidence/OPEN-96-CLASSIFICATION-2026-10-04/batches/batch_00.json`, `tasks/evidence/CLOSURE-CONTROLS-2026-10-03/DELTA-FORUM-M2-COMPACTION-STATE-VALIDATION-01-original-selector-current.log`.
- Impedimentos de inspección: 0. El criterio original permanece intacto; esta clasificación conserva la ficha abierta.

## Estado (2026-10-11, /0 + /vote)

Bloqueada por criterio sin implementar: el `close_check` de esta ficha termina en `xfailed` y por eso sale con codigo 0 sin que el criterio real exista. Un `xfail` no es una verificacion y cerrar con el no es cierre. Cerrarla exige implementar la prueba real contra el sujeto (vLLM, NCCL, CX7 u otro hardware) con su control negativo. Decision del dueno el 2026-10-11: dejarla abierta y declarada, no cerrarla como `void_wontfix`.

## Root Cause
No aplica a este equipo: Reporte de un operador con MiniMax M2.1 sobre OpenCode+llama.cpp; aqui no hay MiniMax ni llama.cpp, la causa (estado CUDA-graph al limpiar KV) es su parafrasis sin logs y otra respuesta no la reprodujo hasta 120K. La prueba util (sesion larga con cruce de limites de cache-reset y tool calls) queda cubierta por la adaptacion de DELTA-FORUM-GLM52-MULTITURN-CORRECTNESS-AND-RECIPE-SENSITIVITY-01. (aplicabilidad otro_hardware, utilidad baja).

## Regression Test
Ninguno: la ficha se depreca por no tener sujeto aqui. Los tests que la vigilaban (`test_delta_forum_m2_compaction_state_validation_01`, `test_real_capture_close_gate_requires_raw_capture[DELTA-FORUM-M2-COMPACTION-STATE-VALIDATION-01]`) se retiran o dejan de parametrizarla, junto con sus entradas de `tests/known_failures.json`.

## Verification Evidence
Tres rutas del frontmatter: `fail` (el close_check era un xfail), `pass` (perfil medido del equipo: sin dispositivos InfiniBand, un solo contenedor vLLM, sin Ray ni llama.cpp RPC) y `e2e` (la clasificacion). Para reabrirla si el equipo cambia (otro nodo, CX7 en pareja, otro modelo): `git mv tasks/done/DELTA-FORUM-M2-COMPACTION-STATE-VALIDATION-01.md tasks/backlog/` y `status: open`.
