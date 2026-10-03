---
id: DEBT-TELEMETRY-DISPOSITIONS-RETRO-20261003-01
kind: debt
title: "Nueve bloqueos telemetry del pre-push necesitaban dictamen respaldado"
status: done
closure_type: relocated_prior_verification
closed_at: 2026-10-03
severity: P2
origin: detected
detector: {"rule": "native telemetry-disposition audit: blocked rows without durable evidence-backed verdict", "confidence": 1.0}
satd_family: BLIND_INSTRUMENT
created: 2026-10-03
close_check: {"cmd": "python3 .simplecode/run.py simplecode.verification.telemetry_dispositions --root . --gate", "expect": "exit_zero", "porque": "La puerta nativa requiere dictamen sustentado para cada bloqueo desde el cutoff vigente y devuelve rc=0 solo con could_not_dispose=0."}
evidence:
  fail: tasks/evidence/DEBT-TELEMETRY-DISPOSITIONS-RETRO-20261003-01.fail.txt
  pass: tasks/evidence/DEBT-TELEMETRY-DISPOSITIONS-RETRO-20261003-01.pass.txt
  e2e: tasks/evidence/DEBT-TELEMETRY-DISPOSITIONS-RETRO-20261003-01.e2e.txt
reason: "Cerrado registrando nueve eventos con salidas rawcollector como confirmed_defect. El gate nativo pasa con could_not_dispose=0; tres eventos anteriores al cutoff siguen abiertos como deuda separada."
---

## Root Cause

El rawcollector conservó los eventos bloqueados, pero no se había escrito un dictamen durable para nueve hallazgos posteriores al cutoff. La evidencia concreta muestra fallos detectados; el bloqueo no era una inyección controlada.

## Regression Test

El close_check ejecuta el gate nativo de disposiciones. El auditor mantiene separados confirmed_defect, controlled_canary, false_positive y could_not_dispose; no usa una amnistía ni mueve el cutoff.

## Verification Evidence

Las tres rutas contienen el reporte previo, salida nativa posterior y los nueve IDs con sus run_id/fuentes. Los tres registros pre-cutoff sin salida original quedan documentados en la ficha backlog hermana, fuera de la afirmación de limpieza del gate.
