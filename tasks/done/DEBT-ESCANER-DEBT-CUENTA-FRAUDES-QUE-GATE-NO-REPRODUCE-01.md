---
id: DEBT-ESCANER-DEBT-CUENTA-FRAUDES-QUE-GATE-NO-REPRODUCE-01
kind: task
domain: VERDICT
title: "El escaner de /debt cuenta 7 fraudes que backlog_verifier no reproduce (gate: 0)"
status: done
severity: P2
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-10-06
closed_at: 2026-10-06
closure_type: void_wontfix
reason: "No reproducido: la prueba de cierre pasa y el gate da 0 fraudes. La causa de los 7 fraudes que el escaner reporto no se identifico. Decision de Luis (2026-10-06): cerrar como no reproducida; reabrir si reaparece."
close_check: {"cmd": "python3 -m pytest -q tests/test_escaner_debt_fraudes.py", "expect": "exit_zero", "porque": "El escaner y el gate deben contar lo mismo sobre el mismo repo: el numero de fraudes del escaner debe igualar el de backlog_verifier --gate, y un fraude real debe aparecer en ambos."}
---

## Registro y responsable

Registro del 2026-10-06 durante /0. Responsable: Luis Casarin, dueno de la skill `/debt` (`~/.claude/skills/debt/scan.py`), que vive fuera de este repo.

## Evidencia y alcance

- Salida del escaner (2026-10-06): `simplecode backlog_verifier 1 abiertas`, con `7 FRAUD DETECTED (cerrada, su close_check ya no reproduce)` y `1 COULD_NOT_RUN`.
- Salida del gate en el mismo repo y momento: `python3 .simplecode/run.py simplecode.verification.backlog_verifier --root . --gate` -> `NOT CLEAN (counts -> frauds: 0 · could_not_run: 1 (1 undeclared) · contract_breaches: 0 · unverified: 0)`.
- El escaner tiene el COULD_NOT_RUN bien y los fraudes mal: su parseo cuenta lineas de otra seccion o de otra corrida como fraude. La causa exacta no esta identificada.

## Criterio de cierre

Escaner y gate dan el mismo conteo de fraudes sobre el mismo repo, y un fraude sembrado en una ficha cerrada aparece en ambos. Hasta entonces, /debt no debe reportar fraudes sin verificarlos con el gate.

## Estado (cerrada como no reproducida)

Cerrada el 2026-10-06 por decision de Luis: la prueba de cierre pasa (escaner y gate cuentan igual) y el gate da 0 fraudes. La causa de los 7 fraudes que el escaner reporto antes NO se identifico. Si reaparece, abrir una ficha nueva con esa salida.

Abierta. La prueba tests/test_escaner_debt_fraudes.py llama a simplecode_backlog_verifier de scan.py y al gate, y falla: el escaner y el gate no cuentan igual (confirmado 2026-10-06). Costo: la prueba tarda ~13 min porque el escaner vuelve a correr el gate; decidir si se queda en la suite o pasa a una comprobacion manual.

## Root Cause

No identificada. El escáner reportó 7 "FRAUD DETECTED" en una corrida del 2026-10-06
mientras `backlog_verifier --gate` daba `frauds: 0` en el mismo repo y hora cercana. No se
reprodujo esa discrepancia en corridas posteriores (confirmado 2 veces: la función del
escáner y el gate coinciden en 0).

## Regression Test

tests/test_escaner_debt_fraudes.py -- compara el regex que el escáner usa para parsear la
salida de `backlog_verifier` contra una captura real guardada (sin invocar el gate en
vivo, para no recursar: esta misma ficha está en `tasks/done/` y `backlog_verifier`
re-ejecuta el close_check de toda ficha cerrada).

## Verification Evidence

tasks/evidence/DEBT-ESCANER-DEBT-CUENTA-FRAUDES-QUE-GATE-NO-REPRODUCE-01.pass.txt y
tests/fixtures/backlog_verifier_gate_capture_20261006.txt (captura real del 2026-10-06
08:44, antes de cerrar esta ficha).
