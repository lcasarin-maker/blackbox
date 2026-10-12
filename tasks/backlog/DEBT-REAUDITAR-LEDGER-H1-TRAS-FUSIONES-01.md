---
id: DEBT-REAUDITAR-LEDGER-H1-TRAS-FUSIONES-01
kind: task
domain: SECURITY
title: "El libro de auditoria H1 de SPEC.md caduco tras fusionar portero y escalon; re-auditar con /h1"
status: open
severity: P1
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-10-12
close_check: {"cmd": "python3 .simplecode/run.py simplecode.cli audit --root . --gate", "expect": "exit_zero", "porque": "Tras fusionar el portero y el escalon, `audit --gate` sale 1 (afirmaciones caducadas por cambios en tests y en inventario). Cierra cuando el gate salga 0 con un libro completo."}
---

## Medido (2026-10-12)
`python3 .simplecode/run.py simplecode.cli audit --root . --gate` -> rc=1 tras fusionar `d039565` y `674f190`. El agente del escalon lo midio: 7 afirmaciones caducadas (L378-L384) y 2 sin auditar (L385, L386). Falta ademas fusionar el laboratorio OCI antes de re-auditar una sola vez. NO se sellan afirmaciones sin comprobarlas contra el sujeto.
