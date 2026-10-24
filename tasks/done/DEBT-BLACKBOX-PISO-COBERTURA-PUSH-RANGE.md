---
id: DEBT-BLACKBOX-PISO-COBERTURA-PUSH-RANGE
kind: debt
domain: VERDICT
title: "piso_cobertura.sh ejecuta suite completa en pre-push aun sin cambios en código"
status: done
closed_at: 2026-10-24
closure_type: fixed
closure_reason: "tools/piso_cobertura.sh ahora inspecciona PRE_COMMIT_FROM_REF..PRE_COMMIT_TO_REF. Si bin/bb y tests/test_bb_bash.py no cambiaron, sale en 0.013s."
evidence:
  pass: tasks/evidence/DEBT-BLACKBOX-PISO-COBERTURA-PUSH-RANGE/pass.txt
severity: P1
origin: asserted
satd_family: BUILD_DEBT
created: 2026-10-24
close_check: {"cmd": "bash tools/piso_cobertura.sh", "expect": "exit_zero"}
---

## Problema
El hook `piso-cobertura` (`tools/piso_cobertura.sh`) validaba el 90% de cobertura sobre `bin/bb` corriendo la suite entera de tests bash en cada empuje. En cambios donde solo se editaban fichas de tareas o documentación, consumía 25 a 40 segundos innecesariamente.

## Solución
Se agregó soporte para el rango de empuje `PRE_COMMIT_FROM_REF..PRE_COMMIT_TO_REF`. Si los archivos modificados no tocan `bin/bb` ni `tests/test_bb_bash.py`, el hook aprueba inmediatamente en 0.013s.
Commit: `1df1441f`.
