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

### Evidencia de instrumento (2026-10-03)

Estado: parcial, con lector offline que preserva fragmentos de tool call y si se observó `[DONE]`. La ausencia del marcador queda como captura incompleta de causa desconocida; no prueba cancelación, recuperación del parser, tool call posterior ni recuperación tras restart. Esos sujetos quedan `could_not_run`; la ficha sigue abierta y el `close_check` original no cambió. Informe: `docs/evidence/BB-INSTRUMENTS-requests.md`.

## Clasificación del impedimento — 2026-10-04

- Categoría principal: `workload_or_lab`.
- Impedimento: La evidencia actual etiqueta lector offline parcial: conserva fragmentos y [DONE], pero no demuestra siguiente tool call post-cancelación en runtime.
- Evidencia faltante para cierre: Matriz parser×MTP×cancelación, llamada mock tipada antes/después de cancelación, finish reason/exit/restart y control de recuperación tras reinicio.
- Siguiente acción: Completar solo los campos faltantes del recibo cancelación/finish reason si el selector los señala; luego pedir corrida fijada con mock tool, cancel mid-stream y llamada siguiente en mismo proceso.
- Responsable del siguiente paso: BB; operador Luis para workload/lab.
- Cierre completo accionable hoy: no. Preparación coordinable: sí.
- Evidencias de clasificación: `tasks/backlog/DELTA-FORUM-QWEN-MTP-PARSER-CANCEL-STATE-CHECK-01.md`, `tools/runtime_batch03_controls.py`, `tests/test_debt_registration_controls.py`.
- Impedimentos de inspección: 0. El criterio original permanece intacto; esta clasificación conserva la ficha abierta.

## Estado (2026-10-11, /0 + /vote)

Bloqueada por criterio sin implementar: el `close_check` de esta ficha termina en `xfailed` y por eso sale con codigo 0 sin que el criterio real exista. Un `xfail` no es una verificacion y cerrar con el no es cierre. Cerrarla exige implementar la prueba real contra el sujeto (vLLM, NCCL, CX7 u otro hardware) con su control negativo. Decision del dueno el 2026-10-11: dejarla abierta y declarada, no cerrarla como `void_wontfix`.

## Adaptacion a este equipo (clasificacion 2026-10-13)
Aplicabilidad: adaptable · utilidad: media · lectura: completa.

Qwen/MTP/qwen3_xml no se sirven aqui, pero el fallo 'HTTP 200 con inferencia viva y 0 tool calls tras cancelar' es una clase de falla del parser de vLLM que tools/canario_motor.py no cubre; los clientes reintentan en tropel (DEBT-MOTOR-VLLM-ATASCO).

Version para un solo nodo Gigabyte AI TOP ATOM: Anadir a canario_motor un caso: cancelar una generacion mid-stream y verificar que la siguiente llamada de herramienta en el mismo proceso sigue dando finish_reason=tool_calls.

Perfil contra el que se clasifico: un nodo GB10 Gigabyte, DGX OS 7.2.3, kernel 6.17.0-1032-nvidia, driver 580.178.04, un contenedor vLLM (`nemotron-local`), sin InfiniBand/CX7 en pareja, sin Ray ni llama.cpp RPC. Clasificacion por lectura, sin control negativo: es una propuesta, no una verificacion.

## Medicion contra el voto de cierre (2026-10-14): queda ABIERTA
El voto de Luis del 2026-10-14 pedia cerrarla como `void_wontfix` porque "Qwen no se sirve aqui, solo nemotron-local". Medido en solo lectura, la premisa cubre la mitad MTP de la ficha y no la mitad parser + cancelacion, asi que no se cierra y vuelve a Luis:
- Cierto: no hay modelo Qwen servido ni MTP. `curl -s -m 10 http://127.0.0.1:8000/v1/models | grep -qi qwen` -> rc=1; `docker logs nemotron-server 2>&1 | grep -o 'speculative_config=[A-Za-z]*' | sort -u` -> `speculative_config=None`; `docker logs nemotron-server 2>&1 | grep -ciE 'num_speculative_tokens|\bmtp\b'` -> 0.
- No se sostiene: el motor nemotron-local corre con el MISMO parser de herramientas del reporte. `docker inspect nemotron-server --format '{{json .Config.Cmd}}' | grep -oE '"--(tool-call-parser|enable-auto-tool-choice)"(,"[a-z0-9_]+")?'` -> `"--enable-auto-tool-choice"` y `"--tool-call-parser","qwen3_xml"`. El fallo reportado tras cancelar (texto sigue, el parser deja de emitir tool calls hasta reiniciar vLLM) es del parser, y aqui hay clientes que usan herramientas contra ese motor (el investigador de Atlas, ver la medicion de `DELTA-FORUM-CROSS-TURN-SLEEPER-INJECTION-REGRESSION-01`) y `tools/canario_motor.py` pide una tool call en cada ronda.
Decision pendiente de Luis: cerrar solo la mitad MTP y dejar el caso "cancelar mid-stream y comprobar la siguiente tool call con `qwen3_xml`" (la version de un nodo de la adaptacion de 2026-10-13, en `tools/canario_motor.py`), o cerrarla entera como `void_wontfix` sabiendo que el parser si esta en uso.
