---
id: DELTA-ROOT-GLM53-QUEUED-REQUEST-PROGRESS-GATE-01
kind: task
domain: VERDICT
title: "Validar root glm53 queued request progress gate 01"
status: done
closed_at: 2026-10-14
closure_type: void_wontfix
reason: "GLM no se sirve aqui: el motor sirve solo nemotron-local y no hay pesos GLM en disco. Decision de Luis 2026-10-14: cerrar sin sujeto; reabrir si se sirve GLM o si el vLLM local muestra cola sin progreso de prefill."
evidence: {"pass": "tasks/evidence/DELTA-ROOT-GLM53-QUEUED-REQUEST-PROGRESS-GATE-01/pass.txt", "fail": "tasks/evidence/DELTA-ROOT-GLM53-QUEUED-REQUEST-PROGRESS-GATE-01/fail.txt", "e2e": "tasks/evidence/DELTA-ROOT-GLM53-QUEUED-REQUEST-PROGRESS-GATE-01/e2e.txt"}
severity: P2
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-10-02
close_check: {"cmd": "python -m tools.check_harvest_accepted tasks/done/DELTA-ROOT-GLM53-QUEUED-REQUEST-PROGRESS-GATE-01.md", "expect": "exit_zero", "porque": "Cerrada sin sujeto en este equipo (void_wontfix, decision de Luis 2026-10-14): no hay fix que probar, lo verificable por maquina es que la decision quedo registrada (closure_type y reason). El close_check anterior apuntaba a tests/test_debt_registration_controls.py::test_delta_root_glm53_queued_request_progress_gate_01, un xfail que se retira con el cierre."}
---

## Registro y responsable

Registro solicitado por Luis el 2026-10-02. Responsable: coordinación de Blackbox. Trabajo o revisión pendiente; la presencia del marcador no demuestra por sí sola un defecto.

## Evidencia y alcance

Trabajo separado del ámbito de su ficha madre, conservando la fuente original. Los reportes de foro siguen sin validación local y no se convierten en recomendaciones automáticas.

### DELTA-ROOT-GLM53-QUEUED-REQUEST-PROGRESS-GATE-01

Fuente: https://forums.developer.nvidia.com/t/382939/178 y https://forums.developer.nvidia.com/t/382939/181.

Posts 178/181: tras más de 40 horas, una petición decodifica mientras hasta siete quedan sin prefill durante 14 minutos. Reducir max_num_seqs de 8 a 4 reproduce antes; segundo episodio declara KV máximo 37%, frente a 99% del primero. Endpoint vivo y porcentaje KV por sí solos omiten este hang parcial.

Acción preventiva/correctiva: Canario por petición y etapa: antigüedad de cola, inicio/progreso de prefill, tokens decodificados, concurrencia real y terminación/cancelación. Retención de prefix cache y recompilación se validan con prompts reales repetidos; TTFT largo esperado se distingue por progreso. Cuotas de concurrencia y recuperación acotada deben preservar otras peticiones y registrar causa desconocida.

Cierre: Soak multiusuario por digest/commit/modelo con fixture de una petición activa y otras bloqueadas. Detectar bloqueo con KV bajo, permitir prefill lento que progresa, limitar reintentos y probar rollback. Benchmarks breves o TEB no cierran estabilidad del host.

Riesgo y límites: Un solo propietario; recetas cambiantes y logs externos sin auditoría. Diagnóstico externo central sobre freezes de driver permanece `could_not_run`; ausencia de causa aislada impide convertir una versión de driver en fix universal.

Fuentes: tasks/backlog/FEATURE-FORUM-GB10-RUNTIME-COMPAT-01.md.

## Criterio de cierre y control negativo

Aplicar el alcance y los controles concretos de la evidencia copiada arriba: stack/OEM y versiones fijadas, sujeto real, caso sano y negativo, resultados literales y rollback cuando haya intervención. Si faltan hardware, adjuntos, compatibilidad o permisos, imprimir could_not_run y conservar open. Un score agregado o mero estado de un dispositivo no acredita el resultado funcional. No instalar parches ni provocar fallo del host para registrar la ficha.

## Estado del verificador

La ficha permanece abierta. El test selector del close_check es una especificación pendiente, no una prueba existente ni un resultado ejecutado. Implementarlo exige comprobar el sujeto y su control negativo; la existencia de archivos o esta ficha no basta para cerrar.

Conservar comandos, salida literal y could_not_run incluso cero; una ejecución skipped o inaccesible deja el cierre pendiente. Reutilizar instrumentos nativos y pruebas existentes antes de crear código.

### Evidencia de instrumento (2026-10-03)

Estado: `blocked` para progreso de cola/prefill/decode: SSE de Chat Completions describe chunks visibles al cliente, no estado interno por petición ni progreso temporal, y no existe captura backend de engine progress. La ficha sigue abierta y el `close_check` original no cambió. Informe: `docs/evidence/BB-INSTRUMENTS-requests.md`.

## Clasificación del impedimento — 2026-10-04

- Categoría principal: `workload_or_lab`.
- Impedimento: El documento dice que SSE no expone estado interno de cola/prefill y no hay captura temporal por solicitud.
- Evidencia faltante para cierre: Runtime/digest y carga fijados; progreso/ETA por solicitud, colas, counters KV; control sano y negativo; salida literal y rollback.
- Siguiente acción: Solicitar traza interna por petición en runtime fijado bajo una activa + siete queued y control max_num_seqs, registrando progreso, cola, KV y salida final.
- Responsable del siguiente paso: BB; operador Luis para workload/lab.
- Cierre completo accionable hoy: no. Preparación coordinable: sí.
- Evidencias de clasificación: `tasks/backlog/DELTA-ROOT-GLM53-QUEUED-REQUEST-PROGRESS-GATE-01.md`, `tools/runtime_batch04_controls.py`, `tests/test_debt_registration_controls.py`.
- Impedimentos de inspección: 0. El criterio original permanece intacto; esta clasificación conserva la ficha abierta.

## Estado (2026-10-11, /0 + /vote)

Bloqueada por criterio sin implementar: el `close_check` de esta ficha termina en `xfailed` y por eso sale con codigo 0 sin que el criterio real exista. Un `xfail` no es una verificacion y cerrar con el no es cierre. Cerrarla exige implementar la prueba real contra el sujeto (vLLM, NCCL, CX7 u otro hardware) con su control negativo. Decision del dueno el 2026-10-11: dejarla abierta y declarada, no cerrarla como `void_wontfix`.

## Adaptacion a este equipo (clasificacion 2026-10-13)
Aplicabilidad: adaptable · utilidad: media · lectura: completa.

GLM-5.3 no se sirve aqui, pero el hang parcial (una peticion decodifica y hasta siete quedan sin prefill 14 min con endpoint vivo y KV al 37%) puede ocurrir en el vLLM local. tools/atom_gpu_telemetry.py ya lee http://127.0.0.1:8000/metrics (VLLM_METRICS_URL_DEFAULT); la ficha dice que SSE no basta y pide estado interno de cola.

Version para un solo nodo Gigabyte AI TOP ATOM: Sensor que lee de /metrics del vLLM local las peticiones en espera y los tokens generados, y marca cola > 0 sin progreso de tokens durante N minutos aun con KV bajo; sin los parametros de GLM-5.3.

Perfil contra el que se clasifico: un nodo GB10 Gigabyte, DGX OS 7.2.3, kernel 6.17.0-1032-nvidia, driver 580.178.04, un contenedor vLLM (`nemotron-local`), sin InfiniBand/CX7 en pareja, sin Ray ni llama.cpp RPC. Clasificacion por lectura, sin control negativo: es una propuesta, no una verificacion.

## Root Cause
No aplica a este equipo: el hang parcial reportado (una peticion decodifica y hasta siete quedan sin prefill 14 min) es de GLM-5.3; aqui `/v1/models` lista solo nemotron-local, ningun contenedor ni directorio de pesos es GLM.

## Regression Test
Ninguno: la ficha se cierra por no tener sujeto aqui. Los tests que la vigilaban (`tests/test_debt_registration_controls.py::test_delta_root_glm53_queued_request_progress_gate_01` y la parametrizacion `tests/test_runtime_batch04_controls.py::test_real_capture_close_gate_requires_runtime_evidence[DELTA-ROOT-GLM53-QUEUED-REQUEST-PROGRESS-GATE-01]` (la filtra `_ficha_abierta`)) se retiran o dejan de parametrizarla, junto con sus entradas de `tests/known_failures.json`.

## Verification Evidence
Tres rutas del frontmatter: `fail` (control negativo: las ordenes que buscan el sujeto salen con rc distinto de 0), `pass` (perfil medido: modelo servido, contenedores, directorios de pesos, con control positivo) y `e2e` (la decision registrada). Para reabrirla si el sujeto aparece: `git mv tasks/done/DELTA-ROOT-GLM53-QUEUED-REQUEST-PROGRESS-GATE-01.md tasks/backlog/` y `status: open`.
