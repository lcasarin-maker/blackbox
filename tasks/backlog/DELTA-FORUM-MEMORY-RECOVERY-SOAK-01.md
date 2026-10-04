---
id: DELTA-FORUM-MEMORY-RECOVERY-SOAK-01
kind: task
domain: VERDICT
title: "Validar forum memory recovery soak 01"
status: open
severity: P2
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-10-02
close_check: {"cmd": "python3 -m pytest -q tests/test_debt_registration_controls.py::test_delta_forum_memory_recovery_soak_01", "expect": "exit_zero", "porque": "Aplicar el alcance y los controles concretos de la evidencia copiada arriba: stack/OEM y versiones fijadas, sujeto real, caso sano y negativo, resultados literales y rollback cuando haya intervención. Si faltan hardware, adjuntos, compatibilidad o permisos, imprimir could_not_run y conservar open. Un score agregado o mero estado de un dispositivo no acredita el resultado funcional. No instalar parches ni provocar fallo del host para registrar la ficha."}
---

## Registro y responsable

Registro solicitado por Luis el 2026-10-02. Responsable: coordinación de Blackbox. Trabajo o revisión pendiente; la presencia del marcador no demuestra por sí sola un defecto.

## Evidencia y alcance

Trabajo separado del ámbito de su ficha madre, conservando la fuente original. Los reportes de foro siguen sin validación local y no se convierten en recomendaciones automáticas.

**DELTA-FORUM-MEMORY-RECOVERY-SOAK-01.** Dos operadores reportan que `llama.cpp` RPC conserva memoria tras la inferencia y que matar el proceso principal no libera la memoria del nodo remoto; detener `llama-rpc-server` o reiniciar la recupera. No aportan series temporales/versiones y otro reporte del hilo trata aparte un error de configuración Marlin ([361862](https://forums.developer.nvidia.com/t/361862)). Añadir soak multihora con memoria UMA/swap/PSI, estado de proceso servidor y recuperación comprobada tras terminar cliente y servidor; evitar matar/reiniciar automáticamente sin capturar evidencia.

Fuentes: tasks/backlog/FEATURE-1358-CGROUP-05-CUELGUES.md.

## Criterio de cierre y control negativo

Aplicar el alcance y los controles concretos de la evidencia copiada arriba: stack/OEM y versiones fijadas, sujeto real, caso sano y negativo, resultados literales y rollback cuando haya intervención. Si faltan hardware, adjuntos, compatibilidad o permisos, imprimir could_not_run y conservar open. Un score agregado o mero estado de un dispositivo no acredita el resultado funcional. No instalar parches ni provocar fallo del host para registrar la ficha.

## Estado del verificador

La ficha permanece abierta. El test selector del close_check es una especificación pendiente, no una prueba existente ni un resultado ejecutado. Implementarlo exige comprobar el sujeto y su control negativo; la existencia de archivos o esta ficha no basta para cerrar.

Conservar comandos, salida literal y could_not_run incluso cero; una ejecución skipped o inaccesible deja el cierre pendiente. Reutilizar instrumentos nativos y pruebas existentes antes de crear código.
## Evaluación de instrumentos 2026-10-03

Reusa `tools/atom_gpu_telemetry.py` y `tools/memory_profile.py` para observaciones puntuales del host; no hay serie temporal, identidad de proceso RPC remoto ni recuperación atribuible adjunta. Estado `deferred_lab`: soak multihora en stack/servidor fijado, series UMA/swap/PSI/RSS y PID/vida del RPC server, cliente y servidor cerrados en orden con medición pre/post y control sano. No se mató proceso ni reinició nodo; no se convirtió memoria desconocida en cero.

## Clasificación del impedimento — 2026-10-04

- Categoría principal: `workload_or_lab`.
- Impedimento: La ficha documenta solo telemetría puntual; falta serie temporal y PID/vida del RPC remoto.
- Evidencia faltante para cierre: Stack/servidor/versiones; series UMA/swap/PSI/RSS y PID RPC; cierre ordenado cliente/servidor con medidas antes/después y control sano.
- Siguiente acción: Pedir al operador soak en stack fijado con serie UMA/swap/PSI/RSS atribuida a PID y cierre cliente/servidor ordenado, midiendo recuperación contra control sano.
- Responsable del siguiente paso: BB; operador Luis para workload/lab.
- Cierre completo accionable hoy: no. Preparación coordinable: sí.
- Evidencias de clasificación: `tasks/backlog/DELTA-FORUM-MEMORY-RECOVERY-SOAK-01.md`, `tools/atom_gpu_telemetry.py`, `tools/memory_profile.py`, `tools/hardware_batch02_controls.py`.
- Impedimentos de inspección: 0. El criterio original permanece intacto; esta clasificación conserva la ficha abierta.
