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
close_check: {"cmd": "python3 -m pytest -q -p no:cacheprovider --runxfail tests/test_debt_registration_controls.py::test_delta_forum_qwen_mtp_parser_cancel_state_check_01", "expect": "exit_zero", "porque": "Aplicar el alcance y los controles concretos de la evidencia copiada arriba: stack/OEM y versiones fijadas, sujeto real, caso sano y negativo, resultados literales y rollback cuando haya intervención. Si faltan hardware, adjuntos, compatibilidad o permisos, imprimir could_not_run y conservar open. Un score agregado o mero estado de un dispositivo no acredita el resultado funcional. No instalar parches ni provocar fallo del host para registrar la ficha."}
---

## Trabajo en la ATOM

Anadir a `tools/canario_motor.py` un caso: cancelar una generacion a media emision y verificar que la siguiente llamada de herramienta en el mismo proceso de `nemotron-local` sigue dando `finish_reason=tool_calls`.

## Referencia pública

Hilos de los que salió esta ficha (URL pública):

- https://forums.developer.nvidia.com/t/366828/80
- http://127.0.0.1:8000/v1/models

El texto de lo que dicen esos hilos se reubicó el 2026-11-01 a la base de conocimiento del dueño, por decisión del dueño: el conocimiento vive en el consumidor de conocimiento. Esta ficha conserva sólo el trabajo sobre la máquina y su registro de verificación; su `close_check` no cambió.

## Registro y responsable

Registro solicitado por Luis el 2026-10-02. Responsable: coordinación de Blackbox. Trabajo o revisión pendiente; la presencia del marcador no demuestra por sí sola un defecto.

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
- No se sostiene: el motor nemotron-local corre con el MISMO parser de herramientas del reporte. `docker inspect nemotron-server --format '{{json .Config.Cmd}}' | grep -oE '"--(tool-call-parser|enable-auto-tool-choice)"(,"[a-z0-9_]+")?'` -> `"--enable-auto-tool-choice"` y `"--tool-call-parser","qwen3_xml"`. El fallo reportado tras cancelar (texto sigue, el parser deja de emitir tool calls hasta reiniciar vLLM) es del parser, y aqui hay clientes que usan herramientas contra ese motor (el investigador del consumidor de conocimiento, ver la medicion de `DELTA-FORUM-CROSS-TURN-SLEEPER-INJECTION-REGRESSION-01`) y `tools/canario_motor.py` pide una tool call en cada ronda.
Decision pendiente de Luis: cerrar solo la mitad MTP y dejar el caso "cancelar mid-stream y comprobar la siguiente tool call con `qwen3_xml`" (la version de un nodo de la adaptacion de 2026-10-13, en `tools/canario_motor.py`), o cerrarla entera como `void_wontfix` sabiendo que el parser si esta en uso.

## Medido 2026-10-20 (boleta de Luis: cerrar void_wontfix solo con AUSENCIA MEDIDA): queda ABIERTA

Regla: `void_wontfix` solo si la ausencia del sujeto se mide en este equipo con control positivo. Solo lectura (sin sudo, sin cargas, sin reiniciar nada). Resultado: el sujeto EXISTE o no es observable desde la maquina, asi que no se cierra.

Se repitio la medicion del 2026-10-14 (sigue igual). Mitad MTP/Qwen, ausente; mitad parser + cancelacion, presente:

```
$ curl -s -m 10 http://127.0.0.1:8000/v1/models | grep -o '"id":"[^"]*"'
"id":"nemotron-local"
"id":"modelperm-8b72c82a39d6372e"
$ docker logs nemotron-server 2>&1 | grep -o 'speculative_config=[A-Za-z]*' | sort -u
speculative_config=None
$ docker inspect nemotron-server --format '{{join .Config.Cmd " "}}' | grep -c speculative
0           (rc=1)
$ printf 'x --speculative-config y' | grep -c speculative      # control positivo
1
$ docker inspect nemotron-server --format '{{json .Config.Cmd}}' | grep -oE '"--(tool-call-parser|enable-auto-tool-choice)"(,"[a-z0-9_]+")?'
"--enable-auto-tool-choice"
"--tool-call-parser","qwen3_xml"
```

Veredicto: ABIERTA. Ausencia medida solo de Qwen y MTP; el motor corre con el mismo `--tool-call-parser qwen3_xml` del reporte, y el fallo descrito (el texto sigue, el parser deja de emitir tool calls tras cancelar) es del parser. La decision de Luis del 2026-10-14 (cerrar solo MTP y dejar el caso cancelacion, o cerrar entera) sigue pendiente; la regla de hoy exige ausencia medida del sujeto y aqui el sujeto parser existe.

## Decision de Luis 2026-10-20 (boleta /vote): se cierra solo la mitad MTP; queda el caso del parser
La mitad MTP del reporte (decodificacion especulativa) queda fuera de alcance: ausente en este equipo (medido el 2026-10-20: `speculative_config=None`, cero `--speculative-config` en el comando del contenedor). La ficha sigue abierta SOLO por el caso "cancelar a mitad del stream y comprobar que la siguiente tool call se emite con `qwen3_xml`" (version de un nodo en `tools/canario_motor.py`), porque el motor corre `--tool-call-parser qwen3_xml`, el mismo parser del reporte.
Limite declarado: el `close_check` sigue siendo el original (evidencia real del sujeto, hoy `could_not_run`). Cuando el caso del parser tenga su prueba, el `close_check` se redefine para medirlo; hasta entonces no se relaja. Descartado por Luis: cerrarla entera como `void_wontfix` (motivo: sin motivo declarado).
