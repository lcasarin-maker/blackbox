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
close_check: {"cmd": "python3 -m tools.verify_telemetry_dispositions --event-id 29ac411d67e0c8e7 --event-id 72cac1e581e4c2ad --event-id bad62df306de815c --event-id 8aebe7815048e5ad --event-id 694e380f85c05252 --event-id f95c29dcff8be347 --event-id be8bb3f2adada251 --event-id 19e221b050ec8938 --event-id ad175dcf781b890c", "expect": "exit_zero", "porque": "Exige los nueve IDs de la fuente de esta ficha con disposición terminal y evidencia. Los eventos nuevos y los tres históricos se evalúan por sus propios gates/fichas; el gate global de publicación conserva todos sus bloqueos."}
evidence:
  fail: tasks/evidence/DEBT-TELEMETRY-DISPOSITIONS-RETRO-20261003-01.fail.txt
  pass: tasks/evidence/DEBT-TELEMETRY-DISPOSITIONS-RETRO-20261003-01.pass.txt
  e2e: tasks/evidence/DEBT-TELEMETRY-DISPOSITIONS-RETRO-20261003-01.e2e.txt
reason: "Cerrado registrando nueve eventos con salidas rawcollector como confirmed_defect. El gate nativo pasa con could_not_dispose=0; tres eventos anteriores al cutoff siguen abiertos como deuda separada."
---

## Root Cause

El rawcollector conservó los eventos bloqueados, pero no se había escrito un dictamen durable para nueve hallazgos posteriores al cutoff. La evidencia concreta muestra fallos detectados; el bloqueo no era una inyección controlada.

## Regression Test

El close_check ejecuta el comprobador de disposiciones sobre los nueve IDs concretos de la fuente. El auditor mantiene separados confirmed_defect, controlled_canary, false_positive y could_not_dispose; no usa una amnistía ni mueve el cutoff.

## Verification Evidence

Las tres rutas contienen el reporte previo, salida nativa posterior y los nueve IDs con sus run_id/fuentes. Los tres registros pre-cutoff sin salida original quedan documentados en la ficha backlog hermana, fuera de la afirmación de limpieza del gate.

## Corrección del criterio

El pre-push de b6ca7ba produjo nuevos bloqueos por los recolectores y el backlog abierto. El criterio global inicial atribuía esos eventos nuevos a los nueve históricos de esta ficha y produjo un fallo de cierre. Se corrigió el alcance a los nueve IDs fuente, reutilizando el comprobador que exige último estado y evidencia. El gate global de publicación sigue activo; los eventos nuevos conservan su dictamen y sus deudas originales.
