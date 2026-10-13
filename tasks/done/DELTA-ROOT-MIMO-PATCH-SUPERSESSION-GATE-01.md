---
id: DELTA-ROOT-MIMO-PATCH-SUPERSESSION-GATE-01
kind: task
domain: VERDICT
title: "Validar root mimo patch supersession gate 01"
status: done
closed_at: 2026-10-13
closure_type: void_wontfix
reason: "Hilos 368097/375416/379722 sobre MiMo, GLM-5.2 DCP4 y DFlash en multinodo; este equipo es un solo nodo con nemotron-local sin parches de vLLM aplicados. Decision de Luis 2026-10-13: deprecar por aplicabilidad, con independencia de la nota del 2026-10-11 (que dejaba abiertas las fichas con xfail porque un xfail no verifica nada)."
evidence: {"pass": "tasks/evidence/DELTA-ROOT-MIMO-PATCH-SUPERSESSION-GATE-01/pass.txt", "fail": "tasks/evidence/DELTA-ROOT-MIMO-PATCH-SUPERSESSION-GATE-01/fail.txt", "e2e": "tasks/evidence/DELTA-ROOT-MIMO-PATCH-SUPERSESSION-GATE-01/e2e.txt"}
severity: P2
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-10-02
close_check: {"cmd": "python3 -m pytest -q tests/test_debt_registration_controls.py::test_delta_root_mimo_patch_supersession_gate_01", "expect": "exit_zero", "porque": "Aplicar el alcance y los controles concretos de la evidencia copiada arriba: stack/OEM y versiones fijadas, sujeto real, caso sano y negativo, resultados literales y rollback cuando haya intervención. Si faltan hardware, adjuntos, compatibilidad o permisos, imprimir could_not_run y conservar open. Un score agregado o mero estado de un dispositivo no acredita el resultado funcional. No instalar parches ni provocar fallo del host para registrar la ficha."}
---

## Registro y responsable

Registro solicitado por Luis el 2026-10-02. Responsable: coordinación de Blackbox. Trabajo o revisión pendiente; la presencia del marcador no demuestra por sí sola un defecto.

## Evidencia y alcance

Trabajo separado del ámbito de su ficha madre, conservando la fuente original. Los reportes de foro siguen sin validación local y no se convierten en recomendaciones automáticas.

### DELTA-ROOT-MIMO-PATCH-SUPERSESSION-GATE-01 — Admitir parches según versión y validar modalidades

Fuente: [hilo 368097](https://forums.developer.nvidia.com/t/368097); cuerpos capturados leídos, sin auditoría de binarios ni repos externos.

MiMo FP8 sobre GB10: PR41834 evita crash de MTP en 0.20.1rc1, pero su función fue refactorizada en 0.21.1rc1.dev30+g4db300e95 y el owner declara innecesario el parche. CUTLASS block FP8 pasa el gate de capability y falla can_implement; un bypass a Triton reporta éxito. Torchcodec ABI incompatible fue reemplazado por stub text-only, que bloquea audio. MTP/EAGLE producen OOM locks; primer inicio _load_w2 puede quedarse detenido y owner reinicia contenedor.

Propuesta: Gate por digest/revisión y símbolo objetivo: rechazar parche obsoleto, probar backend real SM121 con primera petición y modalidades anunciadas. Registrar carga fría y memoria de draft por rank; recuperación de contenedor propia y acotada. Conservar imagen conocida y rollback exacto. Los repos externos y estado upstream siguen sin auditar.

Riesgo: Stub oculta capacidad audio; copiar swapoff, apagar GUI/servicios o asumir umbral universal amenaza disponibilidad.

Cierre: Reproducir crash en versión afectada y comprobar que versión refactorizada rechaza parche obsoleto; canarios de texto, herramientas y modalidades habilitadas; medir soak con errores y contexto real. Benchmark máximo 100K en el hilo queda separado de configuración 1M.

[375416](https://forums.developer.nvidia.com/t/375416) reports a correctness failure in a community vLLM V1 speculative/MTP path under DCP4: draft parallel configuration reportedly omitted `decode_context_parallel_size`, leaving draft attention in DCP1 while KV/metadata were DCP-sharded. The operator’s tensor-level probe reportedly found no q all-gather/LSE merge and all-zero attention on 3/4 ranks; TP all-reduce then made corrupted state identical across ranks, so a cross-rank equality check passed. The operator reports a code fix and stronger GLM-5.2 MTP3/4 acceptance/throughput on 4×GB10, but the patch/repositories were not audited or run in BB. Add a pinned-image regression that asserts draft effective DCP size, verifies gather/merge and nonzero partial outputs against a DCP1/reference control, then checks coherent deterministic output and per-position acceptance across repeated prompts; do not rely on rank consensus or acceptance alone. The same thread contains a second operator’s NV_ERR_NO_MEMORY before an after-load trim hook; first operator’s memory advice did not resolve that case, so preserve a separate pre-trim load/host-headroom test and do not generalize one configuration’s 128K success. **DELTA-FORUM-DCP-MTP-DRAFT-CORRECTNESS-AND-PRETRIM-OOM-01**.

[379722](https://forums.developer.nvidia.com/t/379722) adds Muse-Glimmer/DFlash admission details. An initial NVIDIA/vLLM image reportedly failed because the draft class was missing; a later owner says their DFlash-enabled vLLM muse-glimmer tag only worked with `max_num_seqs <= 32`, reproduced on their setup. A GB10 report says a patched stack completed an 84-scenario tool eval but still had prompt-injection/hallucination and long-horizon failures; other BFCL measurements swung sharply when the prompt required parallel same-turn calls. Repositories, PRs and benchmark captures were not audited. For the pinned image/model/parser/template, preflight draft class resolution and run an A/B at the reported 32/33 sequence boundary, including bounded resource/CPU/GPU tests and semantic canaries for single-tool, parallel calls, token truncation and untrusted tool output. Treat this as a candidate compatibility limit for the exact branch; never set a universal DFlash concurrency cap or infer product safety from an aggregate benchmark score. **DELTA-FORUM-MUSE-GLIMMER-DFLASH-MAX-SEQS-GATE-01**.

Fuentes: tasks/backlog/FEATURE-FORUM-GB10-RUNTIME-COMPAT-01.md.

## Criterio de cierre y control negativo

Aplicar el alcance y los controles concretos de la evidencia copiada arriba: stack/OEM y versiones fijadas, sujeto real, caso sano y negativo, resultados literales y rollback cuando haya intervención. Si faltan hardware, adjuntos, compatibilidad o permisos, imprimir could_not_run y conservar open. Un score agregado o mero estado de un dispositivo no acredita el resultado funcional. No instalar parches ni provocar fallo del host para registrar la ficha.

## Estado del verificador

La ficha permanece abierta. El test selector del close_check es una especificación pendiente, no una prueba existente ni un resultado ejecutado. Implementarlo exige comprobar el sujeto y su control negativo; la existencia de archivos o esta ficha no basta para cerrar.

Conservar comandos, salida literal y could_not_run incluso cero; una ejecución skipped o inaccesible deja el cierre pendiente. Reutilizar instrumentos nativos y pruebas existentes antes de crear código.

## Clasificación del impedimento — 2026-10-04

- Categoría principal: `workload_or_lab`.
- Impedimento: El gate de obsolescencia/revisión, símbolo objetivo y rechazo de parche se puede implementar y verificar localmente; la primera inferencia SM121 sigue siendo validación posterior de runtime.
- Evidencia faltante para cierre: El gate de obsolescencia/revisión, símbolo objetivo y rechazo de parche se puede implementar y verificar localmente; la primera inferencia SM121 sigue siendo validación posterior de runtime.
- Siguiente acción: Coordinación BB: implementar gate determinista de digest/revisión/símbolo con parche obsoleto negativo y dejar canario real como evidencia separada. Ref explícita: tasks/backlog/DELTA-ROOT-MIMO-PATCH-SUPERSESSION-GATE-01.md y tests/test_debt_registration_controls.py. Ref explícita: tasks/backlog/DELTA-ROOT-MIMO-PATCH-SUPERSESSION-GATE-01.md y tasks/evidence/CLOSURE-CONTROLS-2026-10-03/DELTA-ROOT-MIMO-PATCH-SUPERSESSION-GATE-01-original-selector-current.log.
- Responsable del siguiente paso: Coordinación BB; para recuperación de históricos, custodio del artifact store si corresponde..
- Cierre completo accionable hoy: no. Preparación coordinable: sí.
- Evidencias de clasificación: `tasks/backlog/DELTA-ROOT-MIMO-PATCH-SUPERSESSION-GATE-01.md`, `tests/test_debt_registration_controls.py`, `tasks/evidence/OPEN-96-CLASSIFICATION-2026-10-04/batches/batch_00.json`, `tasks/evidence/CLOSURE-CONTROLS-2026-10-03/DELTA-ROOT-MIMO-PATCH-SUPERSESSION-GATE-01-original-selector-current.log`.
- Impedimentos de inspección: 0. El criterio original permanece intacto; esta clasificación conserva la ficha abierta.

## Estado (2026-10-11, /0 + /vote)

Bloqueada por criterio sin implementar: el `close_check` de esta ficha termina en `xfailed` y por eso sale con codigo 0 sin que el criterio real exista. Un `xfail` no es una verificacion y cerrar con el no es cierre. Cerrarla exige implementar la prueba real contra el sujeto (vLLM, NCCL, CX7 u otro hardware) con su control negativo. Decision del dueno el 2026-10-11: dejarla abierta y declarada, no cerrarla como `void_wontfix`.

## Root Cause
No aplica a este equipo: Parches PR41834, DCP4 en 4xGB10, GLM-5.2, Muse-Glimmer/DFlash: ninguno corre aqui (un nodo, nemotron-local). El patron general 'parche obsoleto' no tiene sujeto parcheado en este equipo. (aplicabilidad otro_hardware, utilidad baja).

## Regression Test
Ninguno: la ficha se depreca por no tener sujeto aqui. Los tests que la vigilaban (`test_delta_root_mimo_patch_supersession_gate_01`, `test_real_capture_close_gate_requires_runtime_evidence[DELTA-ROOT-MIMO-PATCH-SUPERSESSION-GATE-01]`) se retiran o dejan de parametrizarla, junto con sus entradas de `tests/known_failures.json`.

## Verification Evidence
Tres rutas del frontmatter: `fail` (el close_check era un xfail), `pass` (perfil medido del equipo: sin dispositivos InfiniBand, un solo contenedor vLLM, sin Ray ni llama.cpp RPC) y `e2e` (la clasificacion). Para reabrirla si el equipo cambia (otro nodo, CX7 en pareja, otro modelo): `git mv tasks/done/DELTA-ROOT-MIMO-PATCH-SUPERSESSION-GATE-01.md tasks/backlog/` y `status: open`.
