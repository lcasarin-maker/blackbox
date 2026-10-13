---
id: DELTA-FORUM-LLAMACPP-RPC-UMA-AND-ORDERLY-TEARDOWN-01
kind: task
domain: VERDICT
title: "Validar forum llamacpp rpc uma and orderly teardown 01"
status: done
closed_at: 2026-10-13
closure_type: void_wontfix
reason: "Sujeto es llama.cpp RPC en dos nodos (cierre servidor/cliente, RDMA); este equipo sirve solo vLLM en un nodo y no tiene llama.cpp RPC ni segundo Spark. Decision de Luis 2026-10-13: deprecar por aplicabilidad, con independencia de la nota del 2026-10-11 (que dejaba abiertas las fichas con xfail porque un xfail no verifica nada)."
evidence: {"pass": "tasks/evidence/DELTA-FORUM-LLAMACPP-RPC-UMA-AND-ORDERLY-TEARDOWN-01/pass.txt", "fail": "tasks/evidence/DELTA-FORUM-LLAMACPP-RPC-UMA-AND-ORDERLY-TEARDOWN-01/fail.txt", "e2e": "tasks/evidence/DELTA-FORUM-LLAMACPP-RPC-UMA-AND-ORDERLY-TEARDOWN-01/e2e.txt"}
severity: P2
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-10-02
close_check: {"cmd": "python -m tools.check_harvest_accepted tasks/done/DELTA-FORUM-LLAMACPP-RPC-UMA-AND-ORDERLY-TEARDOWN-01.md", "expect": "exit_zero", "porque": "Cerrada por aplicabilidad (void_wontfix, decision de Luis 2026-10-13): no hay fix que probar, lo verificable por maquina es que la decision quedo registrada (closure_type y reason). El close_check anterior apuntaba a un test por ficha que se retiro con la deprecacion."}
---

## Registro y responsable

Registro solicitado por Luis el 2026-10-02. Responsable: coordinación de Blackbox. Trabajo o revisión pendiente; la presencia del marcador no demuestra por sí sola un defecto.

## Evidencia y alcance

Trabajo separado del ámbito de su ficha madre, conservando la fuente original. Los reportes de foro siguen sin validación local y no se convierten en recomendaciones automáticas.

**DELTA-FORUM-LLAMACPP-RPC-UMA-AND-ORDERLY-TEARDOWN-01.** Dos Spark con llama.cpp RPC: el autor informa OOM duro con `--fit on` y emplea `--fit off` porque el auto-fit parece tratar UMA como VRAM disponible; también reporta corrupción de KV con `--cache-reuse 256` ([374523, post 1](https://forums.developer.nvidia.com/t/374523/1)). No aporta OS/kernel/driver/commit ni logs de OOM: validar con ese backend/stack exacto antes de fijar la opción, y no generalizar a vLLM u otros runtimes. Un segundo operador reporta que RDMA se habilita automáticamente según el NIC aunque `GGML_RDMA_DEV` esté unset y que cerrar RPC server antes que el PID cliente termine provoca aborto durante liberación de buffers: 11/11 cierres en ese orden vs 0/4 esperando PID, con TCP 6/6 limpio ([post 8](https://forums.developer.nvidia.com/t/374523/8)). Añadir al soak la memoria/cgroup/PSI y respuesta real del endpoint, transporte efectivo observado en lado servidor y prueba de cierre cliente→servidor; rollback a build previa y salida/KV válida. Son resultados de un operador no auditados externamente.

Fuentes: tasks/backlog/FEATURE-1358-CGROUP-05-CUELGUES.md.

## Criterio de cierre y control negativo

Aplicar el alcance y los controles concretos de la evidencia copiada arriba: stack/OEM y versiones fijadas, sujeto real, caso sano y negativo, resultados literales y rollback cuando haya intervención. Si faltan hardware, adjuntos, compatibilidad o permisos, imprimir could_not_run y conservar open. Un score agregado o mero estado de un dispositivo no acredita el resultado funcional. No instalar parches ni provocar fallo del host para registrar la ficha.

## Estado del verificador

La ficha permanece abierta. El test selector del close_check es una especificación pendiente, no una prueba existente ni un resultado ejecutado. Implementarlo exige comprobar el sujeto y su control negativo; la existencia de archivos o esta ficha no basta para cerrar.

Conservar comandos, salida literal y could_not_run incluso cero; una ejecución skipped o inaccesible deja el cierre pendiente. Reutilizar instrumentos nativos y pruebas existentes antes de crear código.
## Evaluación de instrumentos 2026-10-03

Reusa `tools/memory_profile.py`/`tools/atom_gpu_telemetry.py` como muestreo general de memoria/PSI, no como evidencia de RPC server PID, transporte efectivo, validez de salida ni orden de teardown. No hay captura local llama.cpp/RPC del stack o incidente. Estado `deferred_lab`: stack/commit/RPC fijados, endpoint y salida/KV válidos, memoria/cgroup/PSI atribuibles al servidor y A/B de orden de cierre con control TCP/RDMA solo si el backend lo reporta. No se inició ni detuvo procesos.

## Clasificación del impedimento — 2026-10-04

- Categoría principal: `workload_or_lab`.
- Impedimento: Herramientas de memoria/PSI no observan PID RPC, transporte, salida válida ni orden de teardown; no hay captura local del stack llama.cpp/RPC.
- Evidencia faltante para cierre: Herramientas de memoria/PSI no observan PID RPC, transporte, salida válida ni orden de teardown; no hay captura local del stack llama.cpp/RPC.
- Siguiente acción: Coordinación BB: definir lifecycle/health/output contract y negativos offline; operador Luis: ejecutar workload fijado en hosts canary y conservar logs de RPC/teardown. Ref explícita: tasks/backlog/DELTA-FORUM-LLAMACPP-RPC-UMA-AND-ORDERLY-TEARDOWN-01.md y tests/test_debt_registration_controls.py. Ref explícita: tasks/backlog/DELTA-FORUM-LLAMACPP-RPC-UMA-AND-ORDERLY-TEARDOWN-01.md y tasks/evidence/CLOSURE-CONTROLS-2026-10-03/DELTA-FORUM-LLAMACPP-RPC-UMA-AND-ORDERLY-TEARDOWN-01-original-selector-current.log.
- Responsable del siguiente paso: Coordinación BB prepara/implementa; cuando la acción requiere root/lab/hardware, operador Luis aporta y ejecuta el sujeto indicado..
- Cierre completo accionable hoy: no. Preparación coordinable: sí.
- Evidencias de clasificación: `tasks/backlog/DELTA-FORUM-LLAMACPP-RPC-UMA-AND-ORDERLY-TEARDOWN-01.md`, `tests/test_debt_registration_controls.py`, `tasks/evidence/OPEN-96-CLASSIFICATION-2026-10-04/batches/batch_09.json`, `tasks/evidence/CLOSURE-CONTROLS-2026-10-03/DELTA-FORUM-LLAMACPP-RPC-UMA-AND-ORDERLY-TEARDOWN-01-original-selector-current.log`.
- Impedimentos de inspección: 0. El criterio original permanece intacto; esta clasificación conserva la ficha abierta.

## Estado (2026-10-11, /0 + /vote)

Bloqueada por criterio sin implementar: el `close_check` de esta ficha termina en `xfailed` y por eso sale con codigo 0 sin que el criterio real exista. Un `xfail` no es una verificacion y cerrar con el no es cierre. Cerrarla exige implementar la prueba real contra el sujeto (vLLM, NCCL, CX7 u otro hardware) con su control negativo. Decision del dueno el 2026-10-11: dejarla abierta y declarada, no cerrarla como `void_wontfix`.

## Root Cause
No aplica a este equipo: El sujeto es llama.cpp RPC entre dos Spark (hilo 374523, orden de cierre servidor/cliente, RDMA); aqui no hay llama.cpp RPC ni segundo nodo, y la ficha admite 'no hay captura local llama.cpp/RPC'. La memoria/PSI/cgroup general ya la mide tools/memory_profile.py. (aplicabilidad otro_hardware, utilidad baja).

## Regression Test
Ninguno: la ficha se depreca por no tener sujeto aqui. Los tests que la vigilaban (`test_delta_forum_llamacpp_rpc_uma_and_orderly_teardown_01`, `test_real_capture_close_gate_requires_raw_capture[DELTA-FORUM-LLAMACPP-RPC-UMA-AND-ORDERLY-TEARDOWN-01]`) se retiran o dejan de parametrizarla, junto con sus entradas de `tests/known_failures.json`.

## Verification Evidence
Tres rutas del frontmatter: `fail` (el close_check era un xfail), `pass` (perfil medido del equipo: sin dispositivos InfiniBand, un solo contenedor vLLM, sin Ray ni llama.cpp RPC) y `e2e` (la clasificacion). Para reabrirla si el equipo cambia (otro nodo, CX7 en pareja, otro modelo): `git mv tasks/done/DELTA-FORUM-LLAMACPP-RPC-UMA-AND-ORDERLY-TEARDOWN-01.md tasks/backlog/` y `status: open`.
