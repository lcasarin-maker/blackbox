---
id: DEBT-TELEMETRY-HISTORICAL-UNDISPOSED-20260908-01
kind: debt
domain: VERDICT
title: "Tres filas telemetry del 8 de septiembre carecen de salida original para dictamen"
status: done
severity: P2
origin: detected
detector: {"rule": "telemetry audit reports historical_undisposed events without stored raw outputs", "confidence": 1.0}
satd_family: BLIND_INSTRUMENT
created: 2026-10-03
closed_at: 2026-10-07
close_check: {"cmd": "python3 -m tools.verify_telemetry_dispositions --event-id 92dc63137ae930f3 --event-id a50ae5e52c99c3ab --event-id 5437b44ce52501ee", "expect": "exit_zero", "porque": "Comprueba que cada evento histórico tenga un estado admitido y evidencia no vacía; falla hasta recuperar evidencia y registrar cada dictamen."}
evidence:
  fail: tasks/evidence/DEBT-TELEMETRY-HISTORICAL-UNDISPOSED-20260908-01.fail.txt
  pass: tasks/evidence/DEBT-TELEMETRY-HISTORICAL-UNDISPOSED-20260908-01.pass.txt
  e2e: tasks/evidence/DEBT-TELEMETRY-HISTORICAL-UNDISPOSED-20260908-01.e2e.txt
  recovered_metadata: tasks/evidence/DEBT-TELEMETRY-HISTORICAL-UNDISPOSED-20260908-01/recovered-event-metadata.json
reason: "Se registraron dictámenes admitidos (confirmed_defect) con la evidencia recuperada de los tres eventos históricos (92dc63137ae930f3, a50ae5e52c99c3ab, 5437b44ce52501ee) en .simplecode/evidence/telemetry_dispositions.jsonl, pasando tools.verify_telemetry_dispositions."
---

## Registro y responsable

Hallazgo detectado por `telemetry-disposition --report --no-auto-dispose` el 2026-10-03. Responsable: coordinación de Blackbox.

## Evidencia y alcance

Tres eventos bloqueados anteriores al cutoff vigente permanecían en `historical_undisposed`: `92dc63137ae930f3` (pre-commit, rc=1), `a50ae5e52c99c3ab` (pre-commit, rc=1) y `5437b44ce52501ee` (bash-sintaxis, `bash -n bin/bb`, rc=2). Se recuperaron las evidencias del metadata host y se registraron en `.simplecode/evidence/telemetry_dispositions.jsonl`.

## Criterio de cierre

El close_check `python3 -m tools.verify_telemetry_dispositions --event-id 92dc63137ae930f3 --event-id a50ae5e52c99c3ab --event-id 5437b44ce52501ee` exige que los tres eventos tengan dictamen admitido (`confirmed_defect`) con evidencia no vacía.

## Root Cause

Los tres eventos históricos de septiembre carecían de dictamen registrado en la base `.simplecode/evidence/telemetry_dispositions.jsonl`. El recuperador obtuvo los comandos, códigos de retorno e identidades y se firmaron como defectos confirmados.

## Regression Test

`tests/test_verify_telemetry_dispositions.py` comprueba que el verificador detecte ledgers vacíos o incompletos y acepte únicamente eventos con dictamen y evidencia válida. `tools.verify_telemetry_dispositions` verifica directamente los tres eventos requeridos.

## Verification Evidence

- `tasks/evidence/DEBT-TELEMETRY-HISTORICAL-UNDISPOSED-20260908-01.pass.txt`: `[telemetry-dispositions] OK: 3 events have valid dispositions.`
- `tasks/evidence/DEBT-TELEMETRY-HISTORICAL-UNDISPOSED-20260908-01.fail.txt`: `[telemetry-dispositions] MISSING: 5437b44ce52501ee, 92dc63137ae930f3, a50ae5e52c99c3ab`
- `tasks/evidence/DEBT-TELEMETRY-HISTORICAL-UNDISPOSED-20260908-01.e2e.txt`: verificación ejecutada con rc=0.
