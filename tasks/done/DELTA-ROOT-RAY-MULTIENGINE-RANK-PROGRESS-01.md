---
id: DELTA-ROOT-RAY-MULTIENGINE-RANK-PROGRESS-01
kind: task
domain: VERDICT
title: "Validar root ray multiengine rank progress 01"
status: done
closed_at: 2026-10-13
closure_type: void_wontfix
reason: "Presupone dos motores vLLM bajo un cluster Ray con colectivo NCCL; este equipo corre un solo vLLM sin Ray ni segundo rank y el relato fuente carece de version y logs. Decision de Luis 2026-10-13: deprecar por aplicabilidad, con independencia de la nota del 2026-10-11 (que dejaba abiertas las fichas con xfail porque un xfail no verifica nada)."
evidence: {"pass": "tasks/evidence/DELTA-ROOT-RAY-MULTIENGINE-RANK-PROGRESS-01/pass.txt", "fail": "tasks/evidence/DELTA-ROOT-RAY-MULTIENGINE-RANK-PROGRESS-01/fail.txt", "e2e": "tasks/evidence/DELTA-ROOT-RAY-MULTIENGINE-RANK-PROGRESS-01/e2e.txt"}
severity: P2
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-10-02
close_check: {"cmd": "python -m tools.check_harvest_accepted tasks/done/DELTA-ROOT-RAY-MULTIENGINE-RANK-PROGRESS-01.md", "expect": "exit_zero", "porque": "Cerrada por aplicabilidad (void_wontfix, decision de Luis 2026-10-13): no hay fix que probar, lo verificable por maquina es que la decision quedo registrada (closure_type y reason). El close_check anterior apuntaba a un test por ficha que se retiro con la deprecacion."}
---

## Registro y responsable

Registro solicitado por Luis el 2026-10-02. Responsable: coordinación de Blackbox. Trabajo o revisión pendiente; la presencia del marcador no demuestra por sí sola un defecto.

## Evidencia y alcance

Trabajo separado del ámbito de su ficha madre, conservando la fuente original. Los reportes de foro siguen sin validación local y no se convierten en recomendaciones automáticas.

### DELTA-ROOT-RAY-MULTIENGINE-RANK-PROGRESS-01

Fuentes: https://forums.developer.nvidia.com/t/377396.

Post101 relata dos vLLM dentro del mismo cluster Ray con NCCL atascado, sin logs ni versión; Distributed mp se propone, sin A/B demostrado.

Acción: Antes de admitir segundo motor, verificar identidades, presupuesto agregado y progreso real de cada rank en ambos motores; medir colectivo y petición real, no solo disponibilidad Ray. Fijar digest y configuración; aislar recursos y recuperación al motor afectado.

Cierre: Fixture un motor sano y otro sin progreso colectivo; detectar el afectado y mantener al primero. A/B efectivo y rollback de cambios de executor.

Riesgos: Relato único sin versión; mp es propuesta, no fix confirmado.

Fuentes: tasks/backlog/FEATURE-FORUM-GB10-RUNTIME-COMPAT-01.md.

## Criterio de cierre y control negativo

Aplicar el alcance y los controles concretos de la evidencia copiada arriba: stack/OEM y versiones fijadas, sujeto real, caso sano y negativo, resultados literales y rollback cuando haya intervención. Si faltan hardware, adjuntos, compatibilidad o permisos, imprimir could_not_run y conservar open. Un score agregado o mero estado de un dispositivo no acredita el resultado funcional. No instalar parches ni provocar fallo del host para registrar la ficha.

## Estado del verificador

La ficha permanece abierta. El test selector del close_check es una especificación pendiente, no una prueba existente ni un resultado ejecutado. Implementarlo exige comprobar el sujeto y su control negativo; la existencia de archivos o esta ficha no basta para cerrar.

Conservar comandos, salida literal y could_not_run incluso cero; una ejecución skipped o inaccesible deja el cierre pendiente. Reutilizar instrumentos nativos y pruebas existentes antes de crear código.

### Evidencia de instrumento (2026-10-03)

Estado: `reused` únicamente para el contrato existente de `provider_trace.py`: request, worker, proveedor observado, latencia y transición de restart en fixtures declarados. No hay captura nativa con engine/rank/collective progress; la validación multi-engine queda `could_not_run`. La ficha sigue abierta y el `close_check` original no cambió. Informe: `docs/evidence/BB-INSTRUMENTS-requests.md`.

## Clasificación del impedimento — 2026-10-04

- Categoría principal: `workload_or_lab`.
- Impedimento: La evidencia dice que provider_trace observa request/worker/restart, pero no progreso de rank ni agregado entre dos motores; no hay captura multinodo.
- Evidencia faltante para cierre: Digest/config; identidad y recursos de ambos motores/ranks; colectivo y petición real con progreso, control negativo y aislamiento/recuperación.
- Siguiente acción: Solicitar corrida de dos motores Ray con digest/config fijos, recursos por rank, colectivo y petición real; completar campos solo si el recibo actual los reporta faltantes.
- Responsable del siguiente paso: BB; operador Luis para workload/lab.
- Cierre completo accionable hoy: no. Preparación coordinable: sí.
- Evidencias de clasificación: `tasks/backlog/DELTA-ROOT-RAY-MULTIENGINE-RANK-PROGRESS-01.md`, `tools/provider_trace.py`, `tools/runtime_batch04_controls.py`.
- Impedimentos de inspección: 0. El criterio original permanece intacto; esta clasificación conserva la ficha abierta.

## Estado (2026-10-11, /0 + /vote)

Bloqueada por criterio sin implementar: el `close_check` de esta ficha termina en `xfailed` y por eso sale con codigo 0 sin que el criterio real exista. Un `xfail` no es una verificacion y cerrar con el no es cierre. Cerrarla exige implementar la prueba real contra el sujeto (vLLM, NCCL, CX7 u otro hardware) con su control negativo. Decision del dueno el 2026-10-11: dejarla abierta y declarada, no cerrarla como `void_wontfix`.

## Root Cause
No aplica a este equipo: Trata de dos vLLM dentro del mismo cluster Ray con NCCL atascado (hilo 377396, relato unico sin version); aqui hay un solo motor, sin Ray ni NCCL colectivo. Su close_check es un xfail. Nota: el dueno decidio el 2026-10-11 dejarla abierta; se pide reconsiderar. (aplicabilidad otro_hardware, utilidad baja).

## Regression Test
Ninguno: la ficha se depreca por no tener sujeto aqui. Los tests que la vigilaban (`test_delta_root_ray_multiengine_rank_progress_01`, `test_real_capture_close_gate_requires_runtime_evidence[DELTA-ROOT-RAY-MULTIENGINE-RANK-PROGRESS-01]`) se retiran o dejan de parametrizarla, junto con sus entradas de `tests/known_failures.json`.

## Verification Evidence
Tres rutas del frontmatter: `fail` (el close_check era un xfail), `pass` (perfil medido del equipo: sin dispositivos InfiniBand, un solo contenedor vLLM, sin Ray ni llama.cpp RPC) y `e2e` (la clasificacion). Para reabrirla si el equipo cambia (otro nodo, CX7 en pareja, otro modelo): `git mv tasks/done/DELTA-ROOT-RAY-MULTIENGINE-RANK-PROGRESS-01.md tasks/backlog/` y `status: open`.
