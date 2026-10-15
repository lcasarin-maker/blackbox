---
id: DELTA-FORUM-QWEN35-NVFP4-CUTLASS-FIRST-REQUEST-GATE-01
kind: task
domain: VERDICT
title: "Validar forum qwen35 nvfp4 cutlass first request gate 01"
status: done
closed_at: 2026-10-14
closure_type: void_wontfix
reason: "Qwen3.5 NVFP4 no se sirve aqui y la ruta CUTLASS tampoco: el motor sirve nemotron-local (otro modelo) con backend MoE NVFP4 MARLIN y GEMM MarlinNvFp4LinearKernel, segun el log del contenedor. Decision de Luis 2026-10-14: cerrar sin sujeto; reabrir si se sirve Qwen3.5 o si el motor pasa a un backend CUTLASS NVFP4."
evidence: {"pass": "tasks/evidence/DELTA-FORUM-QWEN35-NVFP4-CUTLASS-FIRST-REQUEST-GATE-01/pass.txt", "fail": "tasks/evidence/DELTA-FORUM-QWEN35-NVFP4-CUTLASS-FIRST-REQUEST-GATE-01/fail.txt", "e2e": "tasks/evidence/DELTA-FORUM-QWEN35-NVFP4-CUTLASS-FIRST-REQUEST-GATE-01/e2e.txt"}
severity: P2
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-10-02
close_check: {"cmd": "python -m tools.check_harvest_accepted tasks/done/DELTA-FORUM-QWEN35-NVFP4-CUTLASS-FIRST-REQUEST-GATE-01.md", "expect": "exit_zero", "porque": "Cerrada sin sujeto en este equipo (void_wontfix, decision de Luis 2026-10-14): no hay fix que probar, lo verificable por maquina es que la decision quedo registrada (closure_type y reason). El close_check anterior era `python3 -m pytest -q tests/test_debt_registration_controls.py::test_delta_forum_qwen35_nvfp4_cutlass_first_request_gate_01`, un xfail que se retira con el cierre."}
---

## Registro y responsable

Registro solicitado por Luis el 2026-10-02. Responsable: coordinación de Blackbox. Trabajo o revisión pendiente; la presencia del marcador no demuestra por sí sola un defecto.

## Evidencia y alcance

Trabajo separado del ámbito de su ficha madre, conservando la fuente original. Los reportes de foro siguen sin validación local y no se convierten en recomendaciones automáticas.

**DELTA-FORUM-QWEN35-NVFP4-CUTLASS-FIRST-REQUEST-GATE-01.** [361639, posts 94 y 173](https://forums.developer.nvidia.com/t/361639/173) informa que un modelo Qwen3.5 NVFP4 llegó a server-ready y falló en la primera petición con CUDA illegal instruction; el autor dice que varias variantes Qwen3.5 NVFP4 compartían el fallo con CUTLASS y que seleccionar `VLLM_NVFP4_GEMM_BACKEND=marlin` y `VLLM_TEST_FORCE_FP8_MARLIN=1` permitió una prueba GPQA sobre Qwen3.5-35B-A3B-NVFP4. El reporte no identifica una combinación universal de modelo, build, backend o driver y no compara semántica/rendimiento pareados. El gate de arquitectura/runtime debe ejecutar una primera inferencia real después de readiness, registrar kernel/backend y CUDA/Xid, y bloquear promoción si aparece una instrucción ilegal. Probar cualquier fallback sobre el modelo y digest exactos contra una referencia semántica, soak y rollback; esos env vars son una hipótesis/workaround del operador, no un default recomendado.

Fuentes: tasks/backlog/FEATURE-FORUM-GB10-RUNTIME-COMPAT-01.md.

## Criterio de cierre y control negativo

Aplicar el alcance y los controles concretos de la evidencia copiada arriba: stack/OEM y versiones fijadas, sujeto real, caso sano y negativo, resultados literales y rollback cuando haya intervención. Si faltan hardware, adjuntos, compatibilidad o permisos, imprimir could_not_run y conservar open. Un score agregado o mero estado de un dispositivo no acredita el resultado funcional. No instalar parches ni provocar fallo del host para registrar la ficha.

## Estado del verificador

La ficha permanece abierta. El test selector del close_check es una especificación pendiente, no una prueba existente ni un resultado ejecutado. Implementarlo exige comprobar el sujeto y su control negativo; la existencia de archivos o esta ficha no basta para cerrar.

Conservar comandos, salida literal y could_not_run incluso cero; una ejecución skipped o inaccesible deja el cierre pendiente. Reutilizar instrumentos nativos y pruebas existentes antes de crear código.

## Clasificación del impedimento — 2026-10-04

- Categoría principal: `workload_or_lab`.
- Impedimento: Falta evidencia de build efectivo y primera request NVFP4/CUTLASS en el sujeto GB10.
- Evidencia faltante para cierre: Digest/arquitectura/deps fijados; primera solicitud y rutas CUTLASS; control de fallo/fallback; outputs/latencia y rollback.
- Siguiente acción: Solicitar corrida primera-request en GB10 con digest y dependencias fijados, ruta CUTLASS más fallback/control; capturar logs raw para el evaluador actual.
- Responsable del siguiente paso: BB; operador Luis para workload/lab.
- Cierre completo accionable hoy: no. Preparación coordinable: sí.
- Evidencias de clasificación: `tasks/backlog/DELTA-FORUM-QWEN35-NVFP4-CUTLASS-FIRST-REQUEST-GATE-01.md`, `tools/runtime_batch03_controls.py`, `tests/test_debt_registration_controls.py`.
- Impedimentos de inspección: 0. El criterio original permanece intacto; esta clasificación conserva la ficha abierta.

## Estado (2026-10-11, /0 + /vote)

Bloqueada por criterio sin implementar: el `close_check` de esta ficha termina en `xfailed` y por eso sale con codigo 0 sin que el criterio real exista. Un `xfail` no es una verificacion y cerrar con el no es cierre. Cerrarla exige implementar la prueba real contra el sujeto (vLLM, NCCL, CX7 u otro hardware) con su control negativo. Decision del dueno el 2026-10-11: dejarla abierta y declarada, no cerrarla como `void_wontfix`.

## Adaptacion a este equipo (clasificacion 2026-10-13)
Aplicabilidad: adaptable · utilidad: media · lectura: completa.

El modelo Qwen3.5 no se sirve aqui, pero el patron (server-ready sin que la primera peticion funcione, illegal instruction/Xid) aplica a cualquier modelo que se cargue en el contenedor vLLM.

Version para un solo nodo Gigabyte AI TOP ATOM: Extender tools/canario_motor.py para registrar CUDA/Xid junto a la primera peticion tras un cambio de modelo o imagen, sin env vars de Marlin.

Perfil contra el que se clasifico: un nodo GB10 Gigabyte, DGX OS 7.2.3, kernel 6.17.0-1032-nvidia, driver 580.178.04, un contenedor vLLM (`nemotron-local`), sin InfiniBand/CX7 en pareja, sin Ray ni llama.cpp RPC. Clasificacion por lectura, sin control negativo: es una propuesta, no una verificacion.

## Root Cause
No aplica a este equipo: el fallo reportado (servidor listo y primera peticion rota con NVFP4 por la ruta CUTLASS) es de Qwen3.5. Aqui el motor sirve nemotron-local y su log dice `Using 'MARLIN' NvFp4 MoE backend` y `Using MarlinNvFp4LinearKernel for NVFP4 GEMM`: ni el modelo ni la ruta CUTLASS estan presentes.

## Regression Test
Ninguno: la ficha se cierra por no tener sujeto aqui. El test que la vigilaba (`tests/test_debt_registration_controls.py::test_delta_forum_qwen35_nvfp4_cutlass_first_request_gate_01` y la parametrizacion `tests/test_runtime_batch03_controls.py::test_real_capture_close_gate_needs_actual_runtime_record[...]` (la filtra `_ficha_abierta`)) se retira junto con sus entradas de `tests/known_failures.json`.

## Verification Evidence
Tres rutas del frontmatter: `fail` (control negativo: las ordenes que buscan el sujeto salen con rc distinto de 0), `pass` (perfil medido, con control positivo de que las mismas herramientas encuentran lo que si existe) y `e2e` (la decision registrada). Datos de la maquina redactados con el PATRON de `tests/test_sin_datos_privados.py`. Para reabrirla si el sujeto aparece: `git mv tasks/done/DELTA-FORUM-QWEN35-NVFP4-CUTLASS-FIRST-REQUEST-GATE-01.md tasks/backlog/` y `status: open`.
