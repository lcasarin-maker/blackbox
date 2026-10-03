---
id: DELTA-FORUM-QWEN-MTP-PARSER-CANCEL-STATE-CHECK-01
kind: task
domain: VERDICT
title: "Validar forum qwen mtp parser cancel state check 01"
status: open
severity: P2
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-10-02
close_check: {"cmd": "python3 -m pytest -q tests/test_debt_registration_controls.py::test_delta_forum_qwen_mtp_parser_cancel_state_check_01", "expect": "exit_zero", "porque": "Aplicar el alcance y los controles concretos de la evidencia copiada arriba: stack/OEM y versiones fijadas, sujeto real, caso sano y negativo, resultados literales y rollback cuando haya intervención. Si faltan hardware, adjuntos, compatibilidad o permisos, imprimir could_not_run y conservar open. Un score agregado o mero estado de un dispositivo no acredita el resultado funcional. No instalar parches ni provocar fallo del host para registrar la ficha."}
---

## Registro y responsable

Registro solicitado por Luis el 2026-10-02. Responsable: coordinación de Blackbox. Trabajo o revisión pendiente; la presencia del marcador no demuestra por sí sola un defecto.

## Evidencia y alcance

Trabajo separado del ámbito de su ficha madre, conservando la fuente original. Los reportes de foro siguen sin validación local y no se convierten en recomendaciones automáticas.

**DELTA-FORUM-QWEN-MTP-PARSER-CANCEL-STATE-CHECK-01.** [366828, posts 25–26, 42, 72–74, 80–90, 96–99, 105–106](https://forums.developer.nvidia.com/t/366828/80) aporta tres señales de corrección/recuperación en Qwen3.x/vLLM: un tool-eval de Qwen3.6-35B-A3B INT4 AutoRound reporta de nuevo el fallo crítico TC-60 de sleeper injection; enlaza al delta `DELTA-FORUM-CROSS-TURN-SLEEPER-INJECTION-REGRESSION-01`. Por separado, un operador de Qwen3.5-122B dice que MTP con más de 1 token rompía tool calls (`Expected function.name to be a string`) bajo vLLM `0.19.2rc1` y `qwen3_xml`; en su ensayo, MTP=1 evitó los errores, pero otro usuario reportó MTP=3 estable con vLLM 0.20.2 y luego autor atribuyó resolución a cambiar parser a `qwen3_coder`, sin A/B compartido. El autor también informa un fallo intermitente tras cancelar generación en curso: el texto continúa, pero el parser deja de producir tool calls hasta reiniciar vLLM; el wrapper descrito reinicia el proceso en bucle cuando sale. Los reportes no aíslan parser, MTP, cancelación o cambio de build como causa; imágenes externas de benchmark no fueron inspeccionadas. Añadir a la compatibilidad fijada una matriz reducida de parser × MTP × cancelación con herramienta mock: respuestas parciales/completas, una cancelación mid-stream y el siguiente tool call en el mismo proceso. Registrar salida del parser, finish reason, exit/restart y alertar en transición `HTTP 200`/inferencia viva pero 0 tool calls inesperados. Cierre: bajo un digest/version exactos, cada combinación admitida conserva llamadas correctamente tipadas antes y después de cancelar; repetir tras reinicio distingue recuperación del proceso de recuperación del parser. No convertir `MTP=1`, `qwen3_coder` ni auto-restart en arreglos universales; mantener el límite probado o bloquear el combo defectuoso con rollback fijado.

Fuentes: tasks/backlog/FEATURE-FORUM-GB10-RUNTIME-COMPAT-01.md.

## Criterio de cierre y control negativo

Aplicar el alcance y los controles concretos de la evidencia copiada arriba: stack/OEM y versiones fijadas, sujeto real, caso sano y negativo, resultados literales y rollback cuando haya intervención. Si faltan hardware, adjuntos, compatibilidad o permisos, imprimir could_not_run y conservar open. Un score agregado o mero estado de un dispositivo no acredita el resultado funcional. No instalar parches ni provocar fallo del host para registrar la ficha.

## Estado del verificador

La ficha permanece abierta. El test selector del close_check es una especificación pendiente, no una prueba existente ni un resultado ejecutado. Implementarlo exige comprobar el sujeto y su control negativo; la existencia de archivos o esta ficha no basta para cerrar.

Conservar comandos, salida literal y could_not_run incluso cero; una ejecución skipped o inaccesible deja el cierre pendiente. Reutilizar instrumentos nativos y pruebas existentes antes de crear código.
