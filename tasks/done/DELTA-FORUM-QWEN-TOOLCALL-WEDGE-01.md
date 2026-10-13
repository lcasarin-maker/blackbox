---
id: DELTA-FORUM-QWEN-TOOLCALL-WEDGE-01
kind: task
domain: VERDICT
title: "Validar forum qwen toolcall wedge 01"
status: done
closed_at: 2026-10-13
closure_type: void_wontfix
reason: "Reporte de foro 381228 sobre Qwen3.8 con DS4/SGLang y MTP; este equipo sirve nemotron-local y su cuelgue en tool-call lo vigilan tools/canario_motor.py y bin/bb-vigilante-motor. Decision de Luis 2026-10-13: deprecar por aplicabilidad, con independencia de la nota del 2026-10-11 (que dejaba abiertas las fichas con xfail porque un xfail no verifica nada)."
evidence: {"pass": "tasks/evidence/DELTA-FORUM-QWEN-TOOLCALL-WEDGE-01/pass.txt", "fail": "tasks/evidence/DELTA-FORUM-QWEN-TOOLCALL-WEDGE-01/fail.txt", "e2e": "tasks/evidence/DELTA-FORUM-QWEN-TOOLCALL-WEDGE-01/e2e.txt"}
severity: P2
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-10-02
close_check: {"cmd": "python3 -m pytest -q tests/test_debt_registration_controls.py::test_delta_forum_qwen_toolcall_wedge_01", "expect": "exit_zero", "porque": "Aplicar el alcance y los controles concretos de la evidencia copiada arriba: stack/OEM y versiones fijadas, sujeto real, caso sano y negativo, resultados literales y rollback cuando haya intervención. Si faltan hardware, adjuntos, compatibilidad o permisos, imprimir could_not_run y conservar open. Un score agregado o mero estado de un dispositivo no acredita el resultado funcional. No instalar parches ni provocar fallo del host para registrar la ficha."}
---

## Registro y responsable

Registro solicitado por Luis el 2026-10-02. Responsable: coordinación de Blackbox. Trabajo o revisión pendiente; la presencia del marcador no demuestra por sí sola un defecto.

## Evidencia y alcance

Trabajo separado del ámbito de su ficha madre, conservando la fuente original. Los reportes de foro siguen sin validación local y no se convierten en recomendaciones automáticas.

**DELTA-FORUM-QWEN-TOOLCALL-WEDGE-01.** Otro dueño informa tres wedges de Qwen3.8 durante tool call a través de patched DS4 engine, vLLM y SGLang, con speculative acceptance 0.00; el agente Telegram reinició antes de capturar RCA ([381228, posts 229–230](https://forums.developer.nvidia.com/t/381228/229)). Registrar request-id, etapa tool-call, MTP acceptance, rank/collective progress y digest; preservar bundle acotado antes de reiniciar. Acceptance cero es señal contextual, no causa.

Fuentes: tasks/backlog/FEATURE-1358-CGROUP-05-CUELGUES.md.

## Criterio de cierre y control negativo

Aplicar el alcance y los controles concretos de la evidencia copiada arriba: stack/OEM y versiones fijadas, sujeto real, caso sano y negativo, resultados literales y rollback cuando haya intervención. Si faltan hardware, adjuntos, compatibilidad o permisos, imprimir could_not_run y conservar open. Un score agregado o mero estado de un dispositivo no acredita el resultado funcional. No instalar parches ni provocar fallo del host para registrar la ficha.

## Estado del verificador

La ficha permanece abierta. El test selector del close_check es una especificación pendiente, no una prueba existente ni un resultado ejecutado. Implementarlo exige comprobar el sujeto y su control negativo; la existencia de archivos o esta ficha no basta para cerrar.

Conservar comandos, salida literal y could_not_run incluso cero; una ejecución skipped o inaccesible deja el cierre pendiente. Reutilizar instrumentos nativos y pruebas existentes antes de crear código.

### Evidencia de instrumento (2026-10-03)

Estado: `reused` solo para conservar salida client-visible mediante `tools/chat_sse_capture.py`, incluidos fragmentos tool-call parciales. No hay captura local del wedge; SSE no mide progreso engine/rank/collective ni MTP acceptance y un último delta no prueba cuelgue o causa. La ficha sigue abierta y su `close_check` original no cambió. Informe: `docs/evidence/BB-INSTRUMENTS-contracts.md`.

## Clasificación del impedimento — 2026-10-04

- Categoría principal: `workload_or_lab`.
- Impedimento: SSE capture reutilizable solo conserva deltas visibles; falta captura del wedge real, progreso engine/rank/collective y aceptación MTP en imagen/prompt fijados.
- Evidencia faltante para cierre: SSE capture reutilizable solo conserva deltas visibles; falta captura del wedge real, progreso engine/rank/collective y aceptación MTP en imagen/prompt fijados.
- Siguiente acción: Coordinación BB: especificar caso reproducible y telemetría; operador Luis: ejecutar replay controlado sobre stack real y guardar salida/ranks. Ref explícita: tasks/backlog/DELTA-FORUM-QWEN-TOOLCALL-WEDGE-01.md y tests/test_debt_registration_controls.py. Ref explícita: tasks/backlog/DELTA-FORUM-QWEN-TOOLCALL-WEDGE-01.md y tasks/evidence/CLOSURE-CONTROLS-2026-10-03/DELTA-FORUM-QWEN-TOOLCALL-WEDGE-01-original-selector-current.log.
- Responsable del siguiente paso: Coordinación BB prepara/implementa; cuando la acción requiere root/lab/hardware, operador Luis aporta y ejecuta el sujeto indicado..
- Cierre completo accionable hoy: no. Preparación coordinable: sí.
- Evidencias de clasificación: `tasks/backlog/DELTA-FORUM-QWEN-TOOLCALL-WEDGE-01.md`, `tests/test_debt_registration_controls.py`, `tasks/evidence/OPEN-96-CLASSIFICATION-2026-10-04/batches/batch_03.json`, `tasks/evidence/CLOSURE-CONTROLS-2026-10-03/DELTA-FORUM-QWEN-TOOLCALL-WEDGE-01-original-selector-current.log`.
- Impedimentos de inspección: 0. El criterio original permanece intacto; esta clasificación conserva la ficha abierta.

## Estado (2026-10-11, /0 + /vote)

Bloqueada por criterio sin implementar: el `close_check` de esta ficha termina en `xfailed` y por eso sale con codigo 0 sin que el criterio real exista. Un `xfail` no es una verificacion y cerrar con el no es cierre. Cerrarla exige implementar la prueba real contra el sujeto (vLLM, NCCL, CX7 u otro hardware) con su control negativo. Decision del dueno el 2026-10-11: dejarla abierta y declarada, no cerrarla como `void_wontfix`.

## Root Cause
No aplica a este equipo: Wedges de Qwen3.8 con DS4/vLLM/SGLang y aceptacion especulativa MTP=0; aqui solo hay nemotron-local en vLLM. El cuelgue en tool call queda cubierto por canario_motor (tool-call del motor local) y bb-vigilante-motor. (aplicabilidad otro_hardware, utilidad baja).

## Regression Test
Ninguno: la ficha se depreca por no tener sujeto aqui. Los tests que la vigilaban (`test_delta_forum_qwen_toolcall_wedge_01`, `test_real_capture_close_gate_needs_actual_runtime_record[DELTA-FORUM-QWEN-TOOLCALL-WEDGE-01]`) se retiran o dejan de parametrizarla, junto con sus entradas de `tests/known_failures.json`.

## Verification Evidence
Tres rutas del frontmatter: `fail` (el close_check era un xfail), `pass` (perfil medido del equipo: sin dispositivos InfiniBand, un solo contenedor vLLM, sin Ray ni llama.cpp RPC) y `e2e` (la clasificacion). Para reabrirla si el equipo cambia (otro nodo, CX7 en pareja, otro modelo): `git mv tasks/done/DELTA-FORUM-QWEN-TOOLCALL-WEDGE-01.md tasks/backlog/` y `status: open`.
