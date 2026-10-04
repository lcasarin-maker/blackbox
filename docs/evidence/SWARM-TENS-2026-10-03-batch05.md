# Lote 05: desarrollo y alcance de instrumentos

## systemd-oomd

`tools/hitos_incidente.py` ahora reconoce el aviso de presión que el código
fuente de systemd emite al marcar un cgroup para terminación. La plantilla
coincide con `oomd-manager.c` en
[systemd/systemd, líneas 3198–3207](https://github.com/systemd/systemd/blob/main/src/oom/oomd-manager.c#L3198-L3207):
`Marked … for killing due to memory pressure for … being … > … for > … with reclaim activity`.
Esta referencia usa la rama `main`; la captura del sujeto no contiene versión
local de systemd y la coincidencia no afirma que su build sea la misma.

Solo `_SYSTEMD_UNIT` y `_COMM` con identidades compatibles identifican el
emisor del evento; un conflicto no se atribuye a oomd. `SYSLOG_IDENTIFIER`
aislado es caller-supplied y produce `could_not_run`. `Marked` se registra como
marca para matar: el informe no asegura que el proceso haya terminado. Guarda
cgroup víctima y cgroup de presión, porcentaje, umbral, duración, timestamp y
boot_id cuando se ofrecen. Timestamp ausente o inválido incrementa
`could_not_run`; un mensaje oomd desconocido también. La procedencia de journal
se conserva como observada y no autenticada.

Los positivos/negativos de `tests/test_1358_hitos_nvrm.py` solo prueban el
formato del parser, identidad, negativos de `SYSLOG_IDENTIFIER`, mensaje
desconocido y timestamp. No hay journal nativo de oomd aportado ni evento de
oomd que este parser pueda dictaminar en la captura. El análisis no establece
relación causal con prompt cache o con un servicio dependiente.

## JSON en capturas SSE

`tools/chat_sse_capture.py --json-summary-only <capture.sse>` recompone los
deltas de contenido de texto por `choice`, conserva hash SHA-256 y longitud,
`finish_reason`, señal de refusal y señal de tool call, y omite respuestas
crudas del JSON resumen. Requiere un `finish_reason=stop`, `[DONE]`, texto de
contenido y ausencia de datos posteriores al finish para intentar `json.loads`.
`length`, EOF/protocolo incompleto, tool call, refusal, filtro, choice ausente,
índice inválido, Unicode surrogate y profundidad que excede el parser se
separan como no evaluables; JSON malformado se registra como `invalid_json`.
La evaluación solo cubre sintaxis JSON, nunca esquema, semántica, seguridad o
calidad de modelo. El resumen preserva `status`, `issues`, el contador de
captura y `json_assessment_counts` para distinguir el resultado del parser del
resultado de sintaxis.

Los fixtures positivos/negativos reconstruyen JSON dividido entre chunks y
cubren JSON inválido, refusal, content filter, tool calls, `length`, ausencia
de `[DONE]`, datos después de `finish_reason`, choice negativo, Unicode
surrogate, profundidad excesiva y salida sin contenido. No se usaron prompts ni
respuestas de un modelo. No hay captura larga pareada local; las pruebas no
acreditan deriva de formato, exactitud semántica ni comportamiento de una
combinación Qwen.

## Sujeto local y límites

`native-readonly-capture.json` confirma `nvidia-smi` rc 0 con NVIDIA GB10,
driver `580.178.04`, CUDA `13.0`; `ip -j link show` también devolvió rc 0.
Los errores de consultas de inventario hechas dentro del sandbox no significan
GPU ausente. Este lote no ejecutó cargas GPU/LLM, requests, compilación fría,
cancelaciones, sesiones largas, Ray, presión de memoria ni recovery. Tampoco
escribió al host. La captura no contiene versión exacta de systemd.

## Validación focal literal

```text
$ python3 -m pytest -q tests/test_chat_sse_capture.py
....................                                                     [100%]
20 passed in 0.21s

$ python3 -m pytest -q tests/test_1358_hitos_nvrm.py
...............................                                          [100%]
31 passed in 0.17s

$ python3 -m ruff check tools/chat_sse_capture.py tests/test_chat_sse_capture.py tools/hitos_incidente.py tests/test_1358_hitos_nvrm.py
All checks passed!

$ python3 -m pyright tools/chat_sse_capture.py tools/hitos_incidente.py
0 errors, 0 warnings, 0 informations
```

Los diez selectores `close_check` se ejecutaron antes y después del cambio;
ambos pases devolvieron pytest `rc=4`, `no tests ran`, porque esos selectores no
existen en este worktree. Sus salidas literales están en
`close_check_05_before.json` y `close_check_05_after.json`. La raíz debe
revalidar allí; este resultado del worktree no se atribuye al principal.
