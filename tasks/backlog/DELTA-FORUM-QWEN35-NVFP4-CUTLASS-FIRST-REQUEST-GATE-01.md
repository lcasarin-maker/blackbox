---
id: DELTA-FORUM-QWEN35-NVFP4-CUTLASS-FIRST-REQUEST-GATE-01
kind: task
domain: VERDICT
title: "Validar forum qwen35 nvfp4 cutlass first request gate 01"
status: open
severity: P2
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-10-02
close_check: {"cmd": "python3 -m pytest -q tests/test_debt_registration_controls.py::test_delta_forum_qwen35_nvfp4_cutlass_first_request_gate_01", "expect": "exit_zero", "porque": "Aplicar el alcance y los controles concretos de la evidencia copiada arriba: stack/OEM y versiones fijadas, sujeto real, caso sano y negativo, resultados literales y rollback cuando haya intervención. Si faltan hardware, adjuntos, compatibilidad o permisos, imprimir could_not_run y conservar open. Un score agregado o mero estado de un dispositivo no acredita el resultado funcional. No instalar parches ni provocar fallo del host para registrar la ficha."}
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
