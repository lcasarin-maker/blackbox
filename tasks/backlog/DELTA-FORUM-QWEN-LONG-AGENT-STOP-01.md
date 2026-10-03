---
id: DELTA-FORUM-QWEN-LONG-AGENT-STOP-01
kind: task
domain: VERDICT
title: "Validar forum qwen long agent stop 01"
status: open
severity: P2
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-10-02
close_check: {"cmd": "python3 -m pytest -q tests/test_debt_registration_controls.py::test_delta_forum_qwen_long_agent_stop_01", "expect": "exit_zero", "porque": "Aplicar el alcance y los controles concretos de la evidencia copiada arriba: stack/OEM y versiones fijadas, sujeto real, caso sano y negativo, resultados literales y rollback cuando haya intervención. Si faltan hardware, adjuntos, compatibilidad o permisos, imprimir could_not_run y conservar open. Un score agregado o mero estado de un dispositivo no acredita el resultado funcional. No instalar parches ni provocar fallo del host para registrar la ficha."}
---

## Registro y responsable

Registro solicitado por Luis el 2026-10-02. Responsable: coordinación de Blackbox. Trabajo o revisión pendiente; la presencia del marcador no demuestra por sí sola un defecto.

## Evidencia y alcance

Trabajo separado del ámbito de su ficha madre, conservando la fuente original. Los reportes de foro siguen sin validación local y no se convierten en recomendaciones automáticas.

**DELTA-FORUM-QWEN-LONG-AGENT-STOP-01.** En un hilo de Qwen3.8, un operador informa que sesiones Hermes de hasta ~8 h terminaban tareas a mitad: respuesta `finish_reason=stop`, cero `tool_calls`, pese a razonamiento que indicaba continuar ([381228, post 311](https://forums.developer.nvidia.com/t/381228/311)). Su telemetría de 12 días en un deployment cuenta 15 paradas prematuras confirmadas en 24 sesiones y 2.176 turnos con herramientas; el mismo reporte dice que 4 replays controlados pasaron y no reprodujeron el evento. El autor observó también el síntoma con pesos NVIDIA NVFP4; después de pasar a INT4 informó que no lo volvió a ver durante pruebas todavía en curso. Son datos de un operador, sin acceso/auditoría de sus registros o adjunto de reproducción y sin causa atribuida al motor, parser o modelo. Antes de admitir una configuración para agentes de larga duración, ejercitar sesiones largas con herramientas y registrar digest del modelo/imagen, stack de muestreo, turn boundary, `finish_reason` y cantidad de llamadas. Una parada sin llamadas cuando la tarea aún está abierta debe producir un evento verificable y dejar la sesión recuperable por el operador; no reintentar automáticamente a ciegas, porque puede duplicar una acción externa. Cierre: prueba de soak sobre checkpoints NVIDIA y alternativos bajo misma harness, contar paradas prematuras y falsos positivos, confirmar continuidad explícita/manual y verificar que no se repiten llamadas mutantes; preservar versión anterior y rollback. La configuración INT4 no se considera fix validado.

Fuentes: tasks/backlog/FEATURE-FORUM-GB10-RUNTIME-COMPAT-01.md.

## Criterio de cierre y control negativo

Aplicar el alcance y los controles concretos de la evidencia copiada arriba: stack/OEM y versiones fijadas, sujeto real, caso sano y negativo, resultados literales y rollback cuando haya intervención. Si faltan hardware, adjuntos, compatibilidad o permisos, imprimir could_not_run y conservar open. Un score agregado o mero estado de un dispositivo no acredita el resultado funcional. No instalar parches ni provocar fallo del host para registrar la ficha.

## Estado del verificador

La ficha permanece abierta. El test selector del close_check es una especificación pendiente, no una prueba existente ni un resultado ejecutado. Implementarlo exige comprobar el sujeto y su control negativo; la existencia de archivos o esta ficha no basta para cerrar.

Conservar comandos, salida literal y could_not_run incluso cero; una ejecución skipped o inaccesible deja el cierre pendiente. Reutilizar instrumentos nativos y pruebas existentes antes de crear código.
