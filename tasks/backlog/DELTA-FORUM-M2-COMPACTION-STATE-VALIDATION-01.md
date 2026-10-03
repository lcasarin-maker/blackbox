---
id: DELTA-FORUM-M2-COMPACTION-STATE-VALIDATION-01
kind: task
domain: VERDICT
title: "Validar forum m2 compaction state validation 01"
status: open
severity: P2
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-10-02
close_check: {"cmd": "python3 -m pytest -q tests/test_debt_registration_controls.py::test_delta_forum_m2_compaction_state_validation_01", "expect": "exit_zero", "porque": "Aplicar el alcance y los controles concretos de la evidencia copiada arriba: stack/OEM y versiones fijadas, sujeto real, caso sano y negativo, resultados literales y rollback cuando haya intervención. Si faltan hardware, adjuntos, compatibilidad o permisos, imprimir could_not_run y conservar open. Un score agregado o mero estado de un dispositivo no acredita el resultado funcional. No instalar parches ni provocar fallo del host para registrar la ficha."}
---

## Registro y responsable

Registro solicitado por Luis el 2026-10-02. Responsable: coordinación de Blackbox. Trabajo o revisión pendiente; la presencia del marcador no demuestra por sí sola un defecto.

## Evidencia y alcance

Trabajo separado del ámbito de su ficha madre, conservando la fuente original. Los reportes de foro siguen sin validación local y no se convierten en recomendaciones automáticas.

**DELTA-FORUM-M2-COMPACTION-STATE-VALIDATION-01.** En un hilo de MiniMax M2.1, un operador informa que después de varias compactions con OpenCode+llama.cpp cae el throughput de prefill/decode, degrada la calidad y fallan tool calls; dice que vio algo parecido con otro build vLLM. La causa sugerida —corrupción de estado CUDA-graph al limpiar KV— es solo su paráfrasis, sin versión completa, logs ni reproducción; otra respuesta reporta ausencia del fallo hasta 120K ([356118, posts 17 y 20](https://forums.developer.nvidia.com/t/356118/17)). Añadir al canary de runtime, para modelos/harnesses exactos que limpien o compacten KV, una secuencia larga que cruce límites de compaction/cache-reset, seguida de tool calls, salida semántica y métricas prefill/decode/process/host; repetir con reset limpio y control sin compaction. No atribuirlo a GB10/driver ni recomendar una opción NVFP4/graph como fix.

Fuentes: tasks/backlog/FEATURE-FORUM-GB10-RUNTIME-COMPAT-01.md.

## Criterio de cierre y control negativo

Aplicar el alcance y los controles concretos de la evidencia copiada arriba: stack/OEM y versiones fijadas, sujeto real, caso sano y negativo, resultados literales y rollback cuando haya intervención. Si faltan hardware, adjuntos, compatibilidad o permisos, imprimir could_not_run y conservar open. Un score agregado o mero estado de un dispositivo no acredita el resultado funcional. No instalar parches ni provocar fallo del host para registrar la ficha.

## Estado del verificador

La ficha permanece abierta. El test selector del close_check es una especificación pendiente, no una prueba existente ni un resultado ejecutado. Implementarlo exige comprobar el sujeto y su control negativo; la existencia de archivos o esta ficha no basta para cerrar.

Conservar comandos, salida literal y could_not_run incluso cero; una ejecución skipped o inaccesible deja el cierre pendiente. Reutilizar instrumentos nativos y pruebas existentes antes de crear código.
