---
id: DELTA-FORUM-GLM52-MULTITURN-CORRECTNESS-AND-RECIPE-SENSITIVITY-01
kind: task
domain: VERDICT
title: "Validar forum glm52 multiturn correctness and recipe sensitivity 01"
status: open
severity: P2
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-10-02
close_check: {"cmd": "python3 -m pytest -q tests/test_debt_registration_controls.py::test_delta_forum_glm52_multiturn_correctness_and_recipe_sensitivity_01", "expect": "exit_zero", "porque": "Aplicar el alcance y los controles concretos de la evidencia copiada arriba: stack/OEM y versiones fijadas, sujeto real, caso sano y negativo, resultados literales y rollback cuando haya intervención. Si faltan hardware, adjuntos, compatibilidad o permisos, imprimir could_not_run y conservar open. Un score agregado o mero estado de un dispositivo no acredita el resultado funcional. No instalar parches ni provocar fallo del host para registrar la ficha."}
---

## Registro y responsable

Registro solicitado por Luis el 2026-10-02. Responsable: coordinación de Blackbox. Trabajo o revisión pendiente; la presencia del marcador no demuestra por sí sola un defecto.

## Evidencia y alcance

Trabajo separado del ámbito de su ficha madre, conservando la fuente original. Los reportes de foro siguen sin validación local y no se convierten en recomendaciones automáticas.

**DELTA-FORUM-GLM52-MULTITURN-CORRECTNESS-AND-RECIPE-SENSITIVITY-01.** [377598, posts 12–17, 23, 27–36](https://forums.developer.nvidia.com/t/377598/12) aporta dos señales que requieren una prueba fijada por stack: un operador reporta que GLM-5.2 Hybrid FP8/MXFP4 con vLLM `0.11.2.dev279`/fork `b12x284a2ea`, driver/build CUDA 13.2.1 y `VLLM_ADAPTIVE_SPEC_DEPTHS=2,4` empezó a producir texto multilingüe incoherente tras 80–95K tokens y 15+ turnos con prefix caching; sus needle tests de prompt único seguían funcionando. Logprobs cercanos a distribución uniforme son medición del operador, sin archivos de trazas adjuntos. Otro reporte mide la categoría de salida estructurada en 58% con thinking activado y 100% desactivado en seis escenarios A/B de una sola ejecución; la misma publicación registra menor resultado de razonamiento/restricción en el benchmark completo al desactivar thinking. El autor también describe un bucle de unas 200 llamadas con `tool_choice=required`, falsos números de prefill al omitir `--tokenizer`, y una penalización de repetición 1.2 que causaba “word slop” en su GLM-5.2. Son reportes de operadores, no reproducción local ni fix validado. Añadir a la canaria de runtime sesiones multi-turno crecientes con prefix cache, comprobaciones de distribución/finish reason y semántica; separar prompts de formato estricto y razonamiento al probar `enable_thinking`, y limitar iteraciones de herramientas en el harness. Registrar tokenizer, parámetros de generación y entorno efectivos para interpretar resultados. Cierre: repetir en el digest/driver/runtime/model exactos un A/B de conversación creciente y prompt único, ejecutar el canario estructurado y de razonamiento con thinking on/off, y confirmar que el límite/timeout corta el bucle `tool_choice=required`; comparar salidas y recursos, conservar la configuración conocida y revertir únicamente el parámetro probado si causa regresión. Evidencia, versiones y cambios de calidad siguen pendientes de validación independiente.

Fuentes: tasks/backlog/FEATURE-FORUM-GB10-RUNTIME-COMPAT-01.md.

## Criterio de cierre y control negativo

Aplicar el alcance y los controles concretos de la evidencia copiada arriba: stack/OEM y versiones fijadas, sujeto real, caso sano y negativo, resultados literales y rollback cuando haya intervención. Si faltan hardware, adjuntos, compatibilidad o permisos, imprimir could_not_run y conservar open. Un score agregado o mero estado de un dispositivo no acredita el resultado funcional. No instalar parches ni provocar fallo del host para registrar la ficha.

## Estado del verificador

La ficha permanece abierta. El test selector del close_check es una especificación pendiente, no una prueba existente ni un resultado ejecutado. Implementarlo exige comprobar el sujeto y su control negativo; la existencia de archivos o esta ficha no basta para cerrar.

Conservar comandos, salida literal y could_not_run incluso cero; una ejecución skipped o inaccesible deja el cierre pendiente. Reutilizar instrumentos nativos y pruebas existentes antes de crear código.
## Evaluación de instrumentos 2026-10-03

Instrumentación local reutilizable: `tools/chat_sse_capture.py` conserva deltas y finish visibles al cliente, pero no mide corrección multivuelta ni prueba tokenizer/logprobs, cache, reasoning on/off o límite de iteraciones de tools. No hay captura local del stack GLM/FP8/MXFP4 ni reproducciones. Estado `deferred_lab`: canario acotado y controlado sobre digest/tokenizer/params fijados, con prompt único vs prefijo creciente y controles separados de formato/razonamiento; comparar finish y resultados literales sin enviar prompts en este informe.
