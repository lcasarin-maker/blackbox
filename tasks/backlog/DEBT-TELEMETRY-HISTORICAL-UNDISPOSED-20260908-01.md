---
id: DEBT-TELEMETRY-HISTORICAL-UNDISPOSED-20260908-01
kind: debt
domain: VERDICT
title: "Tres filas telemetry del 8 de septiembre carecen de salida original para dictamen"
status: open
severity: P2
origin: detected
detector: {"rule": "telemetry audit reports historical_undisposed events without stored raw outputs", "confidence": 1.0}
satd_family: BLIND_INSTRUMENT
created: 2026-10-03
close_check: {"cmd": "python3 -m tools.verify_telemetry_dispositions --event-id 92dc63137ae930f3 --event-id a50ae5e52c99c3ab --event-id 5437b44ce52501ee", "expect": "exit_zero", "porque": "Comprueba que cada evento histórico tenga un estado admitido y evidencia no vacía; falla hasta recuperar evidencia y registrar cada dictamen."}
evidence:
  fail: tasks/evidence/DEBT-TELEMETRY-HISTORICAL-UNDISPOSED-20260908-01.fail.txt
  pass: tasks/evidence/DEBT-TELEMETRY-HISTORICAL-UNDISPOSED-20260908-01.pass.txt
  e2e: tasks/evidence/DEBT-TELEMETRY-HISTORICAL-UNDISPOSED-20260908-01.e2e.txt
  recovered_metadata: tasks/evidence/DEBT-TELEMETRY-HISTORICAL-UNDISPOSED-20260908-01/recovered-event-metadata.json
reason: "Abierta: se recuperaron las tres filas originales de telemetría con comando, rc e identidad, pero no stdout/stderr; falta evidencia raw para dictaminar cada evento."
---

## Registro y responsable

Hallazgo detectado por `telemetry-disposition --report --no-auto-dispose` el 2026-10-03. Responsable: coordinación de Blackbox.

## Evidencia y alcance

Tres eventos bloqueados anteriores al cutoff vigente permanecen en `historical_undisposed`: `92dc63137ae930f3` (pre-commit, rc=1), `a50ae5e52c99c3ab` (pre-commit, rc=1) y `5437b44ce52501ee` (bash-sintaxis, `bash -n bin/bb`, rc=2). Las filas originales no guardan stdout/stderr, y no hay evidencia concreta para elegir uno de los tres estados. El metadata raw recuperado desde el ledger host, con hash del archivo y de cada línea, está en `tasks/evidence/DEBT-TELEMETRY-HISTORICAL-UNDISPOSED-20260908-01/recovered-event-metadata.json`; no incluye output de los comandos. La repetición actual del último comando contra el blob de `71ceaef...` pasó, pero no reconstruye los bytes staged del evento original.

## Criterio de cierre

Recuperar output original o reconstruir una reproducción que identifique el defecto concreto en cada fila. Después registrar cada evento con `simplecode.verification.telemetry_dispositions --record <event_id> <state> --evidence ... --source ...` y evidencia verificable. El close_check usa `tools/verify_telemetry_dispositions.py` para exigir los tres IDs con estado admitido y evidencia no vacía.

## Root Cause

El ledger de septiembre conserva estados y códigos de retorno, pero la primera instrumentación de pre-commit no persistía la salida del comando. Dos filas solo dicen que pre-commit falló; la fila Bash indica rc=2, aunque la repetición actual sobre el blob de commit pasa.

## Regression Test

`tests/test_verify_telemetry_dispositions.py` comprueba ledger vacío (fallo), tres dictámenes admitidos (pase), estado pendiente (fallo) y evidencia vacía (fallo). El close_check llama el comprobador sobre el ledger real y falla mientras los eventos carezcan de dictamen.

## Verification Evidence

Las filas raw originales, el reporte del auditor, la repetición Bash y ambos resultados del close_check están en las tres rutas evidence. Resultado actual del órgano nativo: `historical_undisposed: 3`, `could_not_dispose: 0`; el close_check asociado imprime las tres IDs como faltantes y retorna 1.


## Defecto del lector de dictámenes detectado (2026-10-04)

Un control negativo independiente escribió una fila de prueba con claves `state` y `evidence` duplicadas: pending/confirmed_defect y vacío/placeholder. El comprobador devolvió código 0 (`OK: 1 events have valid dispositions.`), perdiendo la ambigüedad. Recibo: `tasks/evidence/CLOSURE-CONTROLS-2026-10-03/telemetry-duplicate-ledger-root-negative.json`. El ledger del host quedó intacto.

La corrección asignada al agente runtime exige JSON estricto por fila y lectura regular acotada, sin bloqueo sobre FIFO. Un ledger ambiguo produce COULD_NOT_RUN; se conservan los estados admitidos y los tres eventos históricos pendientes. Esta reparación del instrumento no recupera los outputs históricos.

## Clasificación del impedimento — 2026-10-04

- Categoría principal: `missing_history`.
- Impedimento: El close_check actual falla porque las tres IDs siguen sin dictamen en el ledger. El metadata recuperado conserva evento, comando, rc e identidad, pero no stdout/stderr original; la repetición del comando Bash sobre el blob actual no restituye la entrada staged histórica. Un negativo adicional detectó claves JSON duplicadas aceptadas indebidamente por el verificador, por lo que el instrumento debe endurecerse antes de confiar en el ledger.
- Evidencia faltante para cierre: Dictámenes con evidencia verificable para 92dc63137ae930f3, a50ae5e52c99c3ab y 5437b44ce52501ee; raw output original o reproducción que identifique el defecto por evento; corrección/verificación de rechazo de claves duplicadas en el lector.
- Siguiente acción: Coordinación BB: recuperar artifacts/logs históricos y, si no existen, reproducir de forma aislada cada comando sobre su kit/subject SHA identificado para respaldar un dictamen (no convertir metadatos solos en evidencia); endurecer JSON duplicado y volver a evaluar el lector. Operador/custodio del artifact store: buscar stdout/stderr y staged blob SHA de los eventos. Ref: tasks/evidence/DEBT-TELEMETRY-HISTORICAL-UNDISPOSED-20260908-01/recovered-event-metadata.json; tasks/evidence/CLOSURE-CONTROLS-2026-10-03/DEBT-TELEMETRY-HISTORICAL-UNDISPOSED-20260908-01-direct-close-current.log; tasks/evidence/CLOSURE-CONTROLS-2026-10-03/telemetry-duplicate-ledger-root-negative.json; tools/verify_telemetry_dispositions.py.
- Responsable del siguiente paso: Coordinación BB; para recuperación de históricos, custodio del artifact store si corresponde..
- Cierre completo accionable hoy: no. Preparación coordinable: sí.
- Evidencias de clasificación: `tasks/backlog/DEBT-TELEMETRY-HISTORICAL-UNDISPOSED-20260908-01.md`, `tasks/evidence/DEBT-TELEMETRY-HISTORICAL-UNDISPOSED-20260908-01/recovered-event-metadata.json`, `tasks/evidence/CLOSURE-CONTROLS-2026-10-03/DEBT-TELEMETRY-HISTORICAL-UNDISPOSED-20260908-01-direct-close-current.log`, `tests/test_debt_registration_controls.py`, `tasks/evidence/CLOSURE-CONTROLS-2026-10-03/telemetry-duplicate-ledger-root-negative.json`, `tools/verify_telemetry_dispositions.py`, `tasks/evidence/OPEN-96-CLASSIFICATION-2026-10-04/batches/batch_09.json`.
- Impedimentos de inspección: 0. El criterio original permanece intacto; esta clasificación conserva la ficha abierta.
