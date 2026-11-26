---
id: DELTA-ROOT-RECIPE-MEMORY-UNKNOWN-AND-RAW-EVIDENCE-01
kind: task
domain: VERDICT
title: "Validar root recipe memory unknown and raw evidence 01"
status: done
closed_at: 2026-10-14
closure_type: void_wontfix
reason: "El motor corre UNA configuracion fija (/srv/ai/gateway/active_engine.json) con su memoria fijada (container_memory_gb, admission_check_gb, gpu_memory_utilization); no hay recetas intercambiables de vLLM, llama.cpp ni sparkrun con presupuesto desconocido. Decision de Luis 2026-10-14: cerrar sin sujeto; reabrir si se alternan recetas o se sirve con llama.cpp."
evidence: {"pass": "tasks/evidence/DELTA-ROOT-RECIPE-MEMORY-UNKNOWN-AND-RAW-EVIDENCE-01/pass.txt", "fail": "tasks/evidence/DELTA-ROOT-RECIPE-MEMORY-UNKNOWN-AND-RAW-EVIDENCE-01/fail.txt", "e2e": "tasks/evidence/DELTA-ROOT-RECIPE-MEMORY-UNKNOWN-AND-RAW-EVIDENCE-01/e2e.txt"}
severity: P2
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-10-02
close_check: {"cmd": "python -m tools.check_harvest_accepted tasks/done/DELTA-ROOT-RECIPE-MEMORY-UNKNOWN-AND-RAW-EVIDENCE-01.md", "expect": "exit_zero", "porque": "Cerrada sin sujeto en este equipo (void_wontfix, decision de Luis 2026-10-14): no hay fix que probar, lo verificable por maquina es que la decision quedo registrada (closure_type y reason). El close_check anterior apuntaba a tests/test_debt_registration_controls.py::test_delta_root_recipe_memory_unknown_and_raw_evidence_01, un xfail que se retira con el cierre."}
---

## Registro y responsable

Registro solicitado por Luis el 2026-10-02. Responsable: coordinación de Blackbox. Trabajo o revisión pendiente; la presencia del marcador no demuestra por sí sola un defecto.

## Evidencia y alcance

Trabajo separado del ámbito de su ficha madre, conservando la fuente original. Los reportes de foro siguen sin validación local y no se convierten en recomendaciones automáticas.

### DELTA-ROOT-RECIPE-MEMORY-UNKNOWN-AND-RAW-EVIDENCE-01

Fuentes: https://forums.developer.nvidia.com/t/360319/50 y /14–22, /118.

Ejemplo llama.cpp post50 imprime DGX Spark fit:YES usando solo1.58GBweights, pero inmediatamente dice arquitectura ausente y estimaciónKV unavailable; log real agrega896MiBKV y buffers. Posts14–22 vLLMprefixcachecrash/hang tras actualización admite commit previo y mod posterior; throughput positivo de otras máquinas no prueba este workflow.

Acción: Presupuesto de admisión incluye weights, KV, staging, graphs, draft, buffers y reservahost por etapa y runtime. Campos desconocidos impiden afirmar seguro; exigir canario funcional efectivo o perfil medido compatible. Reusar exportaciónconsolidada de receta/comando/resultados de sparkrun como evidencia candidata con versión y digest, no crear otro launcher. Evitar pipupgrade sinpin en cada arranque; validar baseimageefectiva y rollback.

Cierre: Fixture weightsfitperoKVdesconocido reporta unknown y no promete protección. Comparación por hardware/topología/digests/checkpoint/params y rawresults con workload real posterior a warmup; cambio de backend validado funcionalmente y rollback disponible.

Riesgos: Estimaciones y tests de comunidad no sustituyen admisión/soak del host; Exportador/código externo sin auditoría.

Fuentes: tasks/backlog/FEATURE-FORUM-GB10-RUNTIME-COMPAT-01.md.

## Criterio de cierre y control negativo

Aplicar el alcance y los controles concretos de la evidencia copiada arriba: stack/OEM y versiones fijadas, sujeto real, caso sano y negativo, resultados literales y rollback cuando haya intervención. Si faltan hardware, adjuntos, compatibilidad o permisos, imprimir could_not_run y conservar open. Un score agregado o mero estado de un dispositivo no acredita el resultado funcional. No instalar parches ni provocar fallo del host para registrar la ficha.

## Estado del verificador

La ficha permanece abierta. El test selector del close_check es una especificación pendiente, no una prueba existente ni un resultado ejecutado. Implementarlo exige comprobar el sujeto y su control negativo; la existencia de archivos o esta ficha no basta para cerrar.

Conservar comandos, salida literal y could_not_run incluso cero; una ejecución skipped o inaccesible deja el cierre pendiente. Reutilizar instrumentos nativos y pruebas existentes antes de crear código.

## Diagnóstico disponible

`python3 -m tools.recipe_memory` reutiliza `tools.memory_profile.capture` y conserva la captura host completa, sus estados de lectura y un digest del registro que no autentica el origen. Los términos de receta vienen del invocador y se etiquetan `caller_supplied_unverified`; faltantes o desconocidos producen `unknown`, nunca cero. `comparison_only` compara esos valores declarados con MemAvailable, sin afirmar admisión ni protección real, y no prueba workload, canario funcional, compatibilidad, soak ni rollback.

La ejecución local sin términos declarados quedó como `unknown`, rc=2, preservando la captura raw en `tasks/evidence/DELTA-ROOT-RECIPE-MEMORY-UNKNOWN-AND-RAW-EVIDENCE-01/prototype-capture.json`; el comando y hash están en `tasks/evidence/LUNA-98-2026-10-03/batch-03-prototype-runs.json`. No se atribuye una cifra de memoria a la receta comunitaria sin workload real.

## Clasificación del impedimento — 2026-10-04

- Categoría principal: `workload_or_lab`.
- Impedimento: El prototipo de captura no acredita presupuesto KV/staging/graphs ni corrección/soak real posterior a warmup.
- Evidencia faltante para cierre: captura consolidada de receta con digest/params y raw results de workload real; perfil por topología; rollback funcional
- Siguiente acción: Usar exportación existente de receta/sparkrun en canario compatible y medir presupuesto por etapa más corrección/soak; dejar unknown ante campos faltantes.
- Responsable del siguiente paso: coordinación BB prepara; operador Luis ejecuta root/lab.
- Cierre completo accionable hoy: no. Preparación coordinable: sin acción adicional demostrada en esta revisión.
- Evidencias de clasificación: `tasks/backlog/DELTA-ROOT-RECIPE-MEMORY-UNKNOWN-AND-RAW-EVIDENCE-01.md`, `tasks/evidence/OPEN-96-CLASSIFICATION-2026-10-04/batches/batch_02.json`, `tasks/evidence/DELTA-ROOT-RECIPE-MEMORY-UNKNOWN-AND-RAW-EVIDENCE-01/prototype-capture.json`.
- Impedimentos de inspección: 0. El criterio original permanece intacto; esta clasificación conserva la ficha abierta.

## Estado (2026-10-11, /0 + /vote)

Bloqueada por criterio sin implementar: el `close_check` de esta ficha termina en `xfailed` y por eso sale con codigo 0 sin que el criterio real exista. Un `xfail` no es una verificacion y cerrar con el no es cierre. Cerrarla exige implementar la prueba real contra el sujeto (vLLM, NCCL, CX7 u otro hardware) con su control negativo. Decision del dueno el 2026-10-11: dejarla abierta y declarada, no cerrarla como `void_wontfix`.

## Adaptacion a este equipo (clasificacion 2026-10-13)
Aplicabilidad: adaptable · utilidad: media · lectura: completa.

El principio (campos desconocidos de receta dan unknown, no cero) aplica a la admision de memoria en UMA con un solo vLLM; tools/recipe_memory.py ya captura y devuelve unknown rc=2, pero con terminos declarados por el invocador y sin workload real. Los ejemplos del foro (llama.cpp, sparkrun) no corren aqui.

Version para un solo nodo Gigabyte AI TOP ATOM: Usar tools/recipe_memory.py contra la receta real de nemotron-local (pesos, KV, graphs, reserva del host) antes de un reinicio del contenedor, con comparison_only frente a MemAvailable; descartar la parte de sparkrun y de cambio de backend.

Perfil contra el que se clasifico: un nodo GB10 Gigabyte, DGX OS 7.2.3, kernel 6.17.0-1032-nvidia, driver 580.178.04, un contenedor vLLM (`nemotron-local`), sin InfiniBand/CX7 en pareja, sin Ray ni llama.cpp RPC. Clasificacion por lectura, sin control negativo: es una propuesta, no una verificacion.

## Root Cause
No aplica a este equipo: el caso del foro son recetas de comunidad (llama.cpp que imprime fit:YES con KV desconocido, sparkrun) cuyo presupuesto de memoria no se conoce. Aqui la receta activa declara `container_memory_gb: 75`, `admission_check_gb: 68` y `gpu_memory_utilization: 0.3`; no hay llama.cpp ni sparkrun instalados. Las copias `.bak` de `/srv/ai/gateway` son historial de cambios a mano, no recetas que se alternen.

## Regression Test
Ninguno: la ficha se cierra por no tener sujeto aqui. Los tests que la vigilaban (`tests/test_debt_registration_controls.py::test_delta_root_recipe_memory_unknown_and_raw_evidence_01` y la parametrizacion `tests/test_runtime_batch04_controls.py::test_real_capture_close_gate_requires_runtime_evidence[DELTA-ROOT-RECIPE-MEMORY-UNKNOWN-AND-RAW-EVIDENCE-01]` (la filtra `_ficha_abierta`)) se retiran o dejan de parametrizarla, junto con sus entradas de `tests/known_failures.json`. `tools/recipe_memory.py` y su prueba siguen vivos.

## Verification Evidence
Tres rutas del frontmatter: `fail` (control negativo: las ordenes que buscan el sujeto salen con rc distinto de 0), `pass` (perfil medido: `active_engine.json` completo, cuenta de copias .bak, contenedores, modelo servido, con control positivo) y `e2e` (la decision registrada). Para reabrirla si el sujeto aparece: `git mv tasks/done/DELTA-ROOT-RECIPE-MEMORY-UNKNOWN-AND-RAW-EVIDENCE-01.md tasks/backlog/` y `status: open`.
