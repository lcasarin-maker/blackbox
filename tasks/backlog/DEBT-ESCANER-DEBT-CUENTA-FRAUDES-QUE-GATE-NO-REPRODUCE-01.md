---
id: DEBT-ESCANER-DEBT-CUENTA-FRAUDES-QUE-GATE-NO-REPRODUCE-01
kind: task
domain: VERDICT
title: "El escaner de /debt cuenta 7 fraudes que backlog_verifier no reproduce (gate: 0)"
status: open
severity: P2
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-10-06
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

## Estado

Abierta. Pendiente de identificar la causa del parseo en `scan.py`.
