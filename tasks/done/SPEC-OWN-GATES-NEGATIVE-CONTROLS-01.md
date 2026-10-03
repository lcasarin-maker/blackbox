---
id: SPEC-OWN-GATES-NEGATIVE-CONTROLS-01
kind: task
domain: VERDICT
title: "Añadir controles negativos a spec-check y no-perder-lineas"
status: done
severity: P2
origin: detected
detector: {"rule": "SPEC-L307 universal claim with four historical could_not_run results", "confidence": 1.0}
satd_family: BLIND_INSTRUMENT
created: 2026-10-03
close_check: {"cmd": "python3 -m pytest -q tests/test_hook_native_controls.py", "expect": "exit_zero", "porque": "Ejecutar los controles positivos y las fallas inyectadas contra los dos hooks nativos; ambos deben pasar la condición válida y rechazar la mutación negativa."}
closed_at: 2026-10-03
closure_type: relocated_prior_verification
reason: "SPEC-L307 y los dos controles nativos quedaron corregidos y probados en el commit 11414544; este commit solo mueve la ficha cerrada y conserva la evidencia ya integrada."
evidence: {"pass":"tasks/evidence/SPEC-OWN-GATES-NEGATIVE-CONTROLS-01/pass.txt","fail":"tasks/evidence/SPEC-OWN-GATES-NEGATIVE-CONTROLS-01/fail.txt","e2e":"tasks/evidence/SPEC-OWN-GATES-NEGATIVE-CONTROLS-01/e2e.txt"}
---

## Root Cause

SPEC-L307 afirmaba que cada hook bloqueante propio tenía control negativo, pero `spec-check` y `no-perder-lineas` no contaban con pruebas que comprobaran el rechazo de una falla. El ledger histórico ya separaba tres bloqueos de `no-perder-lineas` y uno de `spec-check` que terminaron en `could_not_run`; esos eventos no demostraban detección.

## Regression Test

`python3 -m pytest -q tests/test_hook_native_controls.py`

El selector llama los módulos nativos desde el runtime fijado. Verifica `spec-check` con SPEC válido y sin Objective, y `no-perder-lineas` con una ficha trackeada íntegra y con una línea borrada sin inserción. El control negativo comprueba salida no-cero y el hallazgo específico.

## Verification Evidence

`2 passed in 0.34s`; `ruff check` del test pasa. `spec-check` real acepta el SPEC actualizado con 12 comprobaciones positivas. La corrida del hook `no-perder-lineas` sobre el repo dio `278 revisadas`, `0 perdidas` y `could_not_run=0` después del commit con la ficha nueva en backlog.
