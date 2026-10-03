---
id: DELTA-FORUM-LLAMACPP-RPC-UMA-AND-ORDERLY-TEARDOWN-01
kind: task
domain: VERDICT
title: "Validar forum llamacpp rpc uma and orderly teardown 01"
status: open
severity: P2
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-10-02
close_check: {"cmd": "python3 -m pytest -q tests/test_debt_registration_controls.py::test_delta_forum_llamacpp_rpc_uma_and_orderly_teardown_01", "expect": "exit_zero", "porque": "Aplicar el alcance y los controles concretos de la evidencia copiada arriba: stack/OEM y versiones fijadas, sujeto real, caso sano y negativo, resultados literales y rollback cuando haya intervención. Si faltan hardware, adjuntos, compatibilidad o permisos, imprimir could_not_run y conservar open. Un score agregado o mero estado de un dispositivo no acredita el resultado funcional. No instalar parches ni provocar fallo del host para registrar la ficha."}
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
