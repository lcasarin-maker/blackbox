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
reason: "Abierta: sin salida raw no hay base para confirmed_defect, false_positive ni controlled_canary; no se usa el cutoff actual para amnistiar eventos viejos."
---

## Registro y responsable

Hallazgo detectado por `telemetry-disposition --report --no-auto-dispose` el 2026-10-03. Responsable: coordinación de Blackbox.

## Evidencia y alcance

Tres eventos bloqueados anteriores al cutoff vigente permanecen en `historical_undisposed`: `92dc63137ae930f3` (pre-commit, rc=1), `a50ae5e52c99c3ab` (pre-commit, rc=1) y `5437b44ce52501ee` (bash-sintaxis, `bash -n bin/bb`, rc=2). Las filas no guardan `run_id`, `could_not_run` ni stdout/stderr; no hay evidencia concreta para elegir uno de los tres estados. La repetición actual del último comando contra el blob de `71ceaef...` pasó, pero no reconstruye los bytes staged del evento original.

## Criterio de cierre

Recuperar output original o reconstruir una reproducción que identifique el defecto concreto en cada fila. Después registrar cada evento con `simplecode.verification.telemetry_dispositions --record <event_id> <state> --evidence ... --source ...` y evidencia verificable. El close_check usa `tools/verify_telemetry_dispositions.py` para exigir los tres IDs con estado admitido y evidencia no vacía.

## Root Cause

El ledger de septiembre conserva estados y códigos de retorno, pero la primera instrumentación de pre-commit no persistía la salida del comando. Dos filas solo dicen que pre-commit falló; la fila Bash indica rc=2, aunque la repetición actual sobre el blob de commit pasa.

## Regression Test

`tests/test_verify_telemetry_dispositions.py` comprueba ledger vacío (fallo), tres dictámenes admitidos (pase), estado pendiente (fallo) y evidencia vacía (fallo). El close_check llama el comprobador sobre el ledger real y falla mientras los eventos carezcan de dictamen.

## Verification Evidence

Las filas raw originales, el reporte del auditor, la repetición Bash y ambos resultados del close_check están en las tres rutas evidence. Resultado actual del órgano nativo: `historical_undisposed: 3`, `could_not_dispose: 0`; el close_check asociado imprime las tres IDs como faltantes y retorna 1.
