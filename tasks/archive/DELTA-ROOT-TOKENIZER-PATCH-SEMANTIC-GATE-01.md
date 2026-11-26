---
id: DELTA-ROOT-TOKENIZER-PATCH-SEMANTIC-GATE-01
kind: task
domain: VERDICT
title: "Validar root tokenizer patch semantic gate 01"
status: done
closed_at: 2026-10-14
closure_type: void_wontfix
reason: "El modelo con el tokenizer parcheado (multimodal truncado a 2048) y el checkpoint MXFP4 parcheado no se sirven aqui: el motor sirve solo nemotron-local (texto, NVFP4) y no hay checkpoint MXFP4 ni modelo de vision en disco. Decision de Luis 2026-10-14: cerrar sin sujeto; reabrir si se sirve uno de esos modelos."
evidence: {"pass": "tasks/evidence/DELTA-ROOT-TOKENIZER-PATCH-SEMANTIC-GATE-01/pass.txt", "fail": "tasks/evidence/DELTA-ROOT-TOKENIZER-PATCH-SEMANTIC-GATE-01/fail.txt", "e2e": "tasks/evidence/DELTA-ROOT-TOKENIZER-PATCH-SEMANTIC-GATE-01/e2e.txt"}
severity: P2
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-10-02
close_check: {"cmd": "python -m tools.check_harvest_accepted tasks/done/DELTA-ROOT-TOKENIZER-PATCH-SEMANTIC-GATE-01.md", "expect": "exit_zero", "porque": "Cerrada sin sujeto en este equipo (void_wontfix, decision de Luis 2026-10-14): no hay fix que probar, lo verificable por maquina es que la decision quedo registrada (closure_type y reason). El close_check anterior apuntaba a tests/test_debt_registration_controls.py::test_delta_root_tokenizer_patch_semantic_gate_01, un xfail que se retira con el cierre."}
---

## Registro y responsable

Registro solicitado por Luis el 2026-10-02. Responsable: coordinación de Blackbox. Trabajo o revisión pendiente; la presencia del marcador no demuestra por sí sola un defecto.

## Evidencia y alcance

Trabajo separado del ámbito de su ficha madre, conservando la fuente original. Los reportes de foro siguen sin validación local y no se convierten en recomendaciones automáticas.

### DELTA-ROOT-TOKENIZER-PATCH-SEMANTIC-GATE-01

Fuentes: https://forums.developer.nvidia.com/t/380244 (26 cuerpos capturados), https://forums.developer.nvidia.com/t/362824 (33 cuerpos). En 380244 el tokenizer limitaba silenciosamente texto a 2048 tokens y rechazaba imágenes de 2280 tokens; el dueño confirma después el fix del proveedor idéntico al cambio de `truncation` a `null`. En 362824 el patch MXFP4 pasa por retractaciones, reparación declarada de una carrera Marlin y cambios de precisión por capa; el último ensayo independiente conserva regresiones de calidad y timeouts. Throughput y arranque exitoso requieren un canary funcional adicional.

Propuesta: registrar revision/hash efectivos de tokenizer, checkpoint, imagen y patch; probar recepción completa de un prompt largo con centinelas verificables, imágenes por encima y debajo del antiguo límite, herramientas/Harmony y generación sostenida. Ante pérdida semántica, rechazar la promoción del candidato y conservar el runtime conocido. Riesgo: cambiar tokenizer completo altera otras reglas; preferir artefacto corregido del proveedor y comparar el delta exacto. Rollback: retirar overlay identificado y restaurar el snapshot/digest previo; verificar el mismo canary. `close_check`: fixture afectado reproduce truncamiento; fixture corregido conserva todos los centinelas y el conteo esperado; patch MXFP4 candidato pasa casos funcionales y soak con resultados/errores explícitos. Parches externos y ensayos en host siguen pendientes; esta ficha registra investigación.

Fuentes: tasks/backlog/FEATURE-FORUM-GB10-RUNTIME-COMPAT-01.md.

## Criterio de cierre y control negativo

Aplicar el alcance y los controles concretos de la evidencia copiada arriba: stack/OEM y versiones fijadas, sujeto real, caso sano y negativo, resultados literales y rollback cuando haya intervención. Si faltan hardware, adjuntos, compatibilidad o permisos, imprimir could_not_run y conservar open. Un score agregado o mero estado de un dispositivo no acredita el resultado funcional. No instalar parches ni provocar fallo del host para registrar la ficha.

## Estado del verificador

La ficha permanece abierta. El test selector del close_check es una especificación pendiente, no una prueba existente ni un resultado ejecutado. Implementarlo exige comprobar el sujeto y su control negativo; la existencia de archivos o esta ficha no basta para cerrar.

Conservar comandos, salida literal y could_not_run incluso cero; una ejecución skipped o inaccesible deja el cierre pendiente. Reutilizar instrumentos nativos y pruebas existentes antes de crear código.

## Clasificación del impedimento — 2026-10-04

- Categoría principal: `external_oem`.
- Impedimento: No se aportó patch/build exacto del proveedor ni corpus/resultados semánticos reproducibles.
- Evidencia faltante para cierre: Versiones/digest del tokenizer y patch; corpus boundary/texto-imagen; semántica, precisión, negativos y reversión por build.
- Siguiente acción: Solicitar al proveedor patch, build digests y reproducer; revisar con evaluador actual y pedir corrida del corpus de límites text/image con control y rollback.
- Responsable del siguiente paso: BB; coordinación solicita OEM/proveedor.
- Cierre completo accionable hoy: no. Preparación coordinable: sí.
- Evidencias de clasificación: `tasks/backlog/DELTA-ROOT-TOKENIZER-PATCH-SEMANTIC-GATE-01.md`, `tools/runtime_batch04_controls.py`, `tests/test_debt_registration_controls.py`.
- Impedimentos de inspección: 0. El criterio original permanece intacto; esta clasificación conserva la ficha abierta.

## Estado (2026-10-11, /0 + /vote)

Bloqueada por criterio sin implementar: el `close_check` de esta ficha termina en `xfailed` y por eso sale con codigo 0 sin que el criterio real exista. Un `xfail` no es una verificacion y cerrar con el no es cierre. Cerrarla exige implementar la prueba real contra el sujeto (vLLM, NCCL, CX7 u otro hardware) con su control negativo. Decision del dueno el 2026-10-11: dejarla abierta y declarada, no cerrarla como `void_wontfix`.

## Adaptacion a este equipo (clasificacion 2026-10-13)
Aplicabilidad: adaptable · utilidad: baja · lectura: completa.

El truncamiento a 2048 tokens era de un modelo/tokenizer multimodal concreto y el patch MXFP4 es de otro checkpoint; ninguno corre aqui (nemotron-local). La idea de un canary de prompt largo con centinelas aplica a cualquier motor y no esta en tools/canario_motor.py (solo nombre, JSON y tool-call). Depende de proveedor sin artefacto.

Version para un solo nodo Gigabyte AI TOP ATOM: Anadir al canario_motor una ronda de prompt largo con centinelas al inicio/medio/fin para detectar truncamiento silencioso de nemotron-local; ignorar patch MXFP4 e imagenes.

Perfil contra el que se clasifico: un nodo GB10 Gigabyte, DGX OS 7.2.3, kernel 6.17.0-1032-nvidia, driver 580.178.04, un contenedor vLLM (`nemotron-local`), sin InfiniBand/CX7 en pareja, sin Ray ni llama.cpp RPC. Clasificacion por lectura, sin control negativo: es una propuesta, no una verificacion.

## Root Cause
No aplica a este equipo: el truncamiento a 2048 tokens era de un tokenizer multimodal concreto y el patch MXFP4 de otro checkpoint. Aqui `/v1/models` lista solo nemotron-local (NVFP4, texto), no hay directorios `*mxfp4*` y `/srv/ai/models/vision` esta vacio.

## Regression Test
Ninguno: la ficha se cierra por no tener sujeto aqui. Los tests que la vigilaban (`tests/test_debt_registration_controls.py::test_delta_root_tokenizer_patch_semantic_gate_01` y la parametrizacion `tests/test_runtime_batch04_controls.py::test_real_capture_close_gate_requires_runtime_evidence[DELTA-ROOT-TOKENIZER-PATCH-SEMANTIC-GATE-01]` (la filtra `_ficha_abierta`)) se retiran o dejan de parametrizarla, junto con sus entradas de `tests/known_failures.json`.

## Verification Evidence
Tres rutas del frontmatter: `fail` (control negativo: las ordenes que buscan el sujeto salen con rc distinto de 0), `pass` (perfil medido: modelo servido con su raiz y contexto, directorios de pesos y de tokenizers, con control positivo) y `e2e` (la decision registrada). Para reabrirla si el sujeto aparece: `git mv tasks/done/DELTA-ROOT-TOKENIZER-PATCH-SEMANTIC-GATE-01.md tasks/backlog/` y `status: open`.
