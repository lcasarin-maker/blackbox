---
id: DEBT-REAUDITAR-LEDGER-H1-TRAS-FUSIONES-01
kind: task
domain: SECURITY
title: "El libro de auditoria H1 de SPEC.md caduco tras fusionar portero y escalon; re-auditar con /h1"
status: done
closed_at: 2026-10-13
closure_type: relocated_prior_verification
reason: "La re-auditoria (4 auditores Opus, 14 afirmaciones, 5 textos corregidos y reauditados) y su registro ya estaban commiteados en f160a13f (2026-10-12). Esta ficha mueve el archivo y guarda el antes (rc=1, 7 sin auditar) y el despues (rc=0)."
evidence: {"pass": "tasks/evidence/DEBT-REAUDITAR-LEDGER-H1-TRAS-FUSIONES-01/pass.txt", "fail": "tasks/evidence/DEBT-REAUDITAR-LEDGER-H1-TRAS-FUSIONES-01/fail.txt", "e2e": "tasks/evidence/DEBT-REAUDITAR-LEDGER-H1-TRAS-FUSIONES-01/e2e.txt"}
severity: P1
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-10-12
close_check: {"cmd": "python3 -m simplecode.cli audit --root . --gate", "expect": "exit_zero", "porque": "Tras fusionar el portero y el escalon, `audit --gate` sale 1 (afirmaciones caducadas por cambios en tests y en inventario). Cierra cuando el gate salga 0 con un libro completo."}
---

## Medido (2026-10-12)
`python3 .simplecode/run.py simplecode.cli audit --root . --gate` -> rc=1 tras fusionar `d039565` y `674f190`. El agente del escalon lo midio: 7 afirmaciones caducadas (L378-L384) y 2 sin auditar (L385, L386). Falta ademas fusionar el laboratorio OCI antes de re-auditar una sola vez. NO se sellan afirmaciones sin comprobarlas contra el sujeto.

## Avance 2026-10-12 (re-auditoria en curso)
- 9 afirmaciones sin sello (SPEC-L400 a L408: las filas de Risks, cuyo texto no cambio pero cuyo id por numero de linea se desplazo al anadirse filas de inventario). Dos auditores Opus de solo lectura: 6 PASS y 3 FAIL por cifras viejas (L406: `bb drift` vigila 59 sujetos y no 47; L408: `bin/bb` es el 63 % del bash y no el 67 %; L403: corrida nueva de `calibra_psi` con el colapso real del 2026-10-11 22:44 aun sin etiquetar en `INCIDENTES`). Los tres textos se corrigieron en SPEC.md y un tercer auditor los verifica.
- Costo medido que no debe repetirse: correr `tools/piso_cobertura.sh` en una auditoria uso `maxrss_kb=4162316` (~4 GB), mas de lo permitido tras dos colapsos de memoria. Las auditorias deben recalcular el porcentaje con `git show <commit>:<archivo> | wc -l` y no con ese gate.
- Pendiente de codigo fuera de esta ficha: etiquetar los colapsos del 2026-10-11 (22:02 y 22:44) en `tools/calibra_psi.py` `INCIDENTES` (hoy n=6) y actualizar su test.

## Root Cause
Las afirmaciones de SPEC.md cambiaron de linea y de texto al fusionar portero, escalon y los instrumentos nuevos; sus sellos del libro H1 caducaron y el gate salia 1.

## Regression Test
`python3 .simplecode/run.py simplecode.cli audit --root . --gate` (hook version-bump/H1 del pre-push) y `audit --stale` en 0.

## Verification Evidence
Tres rutas del frontmatter: fail (gate rc=1 en el arbol previo), pass (rc=0 ahora), e2e (`--stale` sobre el sujeto vivo). Pendiente fuera de esta ficha: etiquetar los colapsos del 2026-10-11 en `tools/calibra_psi.py` INCIDENTES.
