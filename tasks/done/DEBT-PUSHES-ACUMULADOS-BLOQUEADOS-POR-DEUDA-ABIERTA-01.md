---
id: DEBT-PUSHES-ACUMULADOS-BLOQUEADOS-POR-DEUDA-ABIERTA-01
kind: task
domain: SECURITY
title: "Commits de bb y Atlas sin publicar: el pre-push bloquea por deuda y por riesgo de memoria"
status: done
closed_at: 2026-10-14
closure_type: relocated_prior_verification
reason: "bb publicado (0 commits adelante de origin/master, medido), portero desplegado en actuar y medido (3 suites en serie), baseline de ship-freeze con dueno y fecha 2026-11-06. Atlas: 1 commit automatico de su propia cola en vuelo, que publica su sesion; declarado, no es de bb."
evidence: {"pass": "tasks/evidence/DEBT-PUSHES-ACUMULADOS-BLOQUEADOS-POR-DEUDA-ABIERTA-01/pass.txt", "fail": "tasks/evidence/DEBT-PUSHES-ACUMULADOS-BLOQUEADOS-POR-DEUDA-ABIERTA-01/fail.txt", "e2e": "tasks/evidence/DEBT-PUSHES-ACUMULADOS-BLOQUEADOS-POR-DEUDA-ABIERTA-01/e2e.txt"}
severity: P2
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-10-12
close_check: {"cmd": "grep -q repositorio_publicado tasks/evidence/DEBT-PUSHES-ACUMULADOS-BLOQUEADOS-POR-DEUDA-ABIERTA-01/publicacion.txt", "expect": "exit_zero", "porque": "El push de /clean no termino (lo mato el reinicio) y despues se pidio no repetirlo hasta tener el portero. Cierra cuando el repo este publicado (0 commits adelante de origin/master, medido con git rev-list --count origin/master..master) tras el despliegue del portero y la decision sobre el baseline de ship-freeze con dueno y fecha; frase obligatoria en publicacion.txt: repositorio_publicado."}
---

## Medido
bb: 38 commits adelante de origin/master al 2026-10-12; Atlas informa 39 locales sin empujar. `zero-debt-repo` bloquea con 100+ fichas abiertas. El pre-push corre la suite completa: solo bajo el portero (una a la vez, scope con tope).

## Voto de Luis 2026-10-12
Cerrar fichas con evidencia real y empujar cuando zero-debt pase. Descartado: mover las fichas de despliegue fuera del backlog para destrabar el push (oculta deuda real de la vista de zero-debt).

## Avance 2026-10-13: la premisa de bb esta obsoleta
`git rev-list --count origin/master..master` en bb da 0 (control negativo: `origin/master~3..master` da 3), asi que bb no tiene commits sin publicar; el ultimo push fue `75b3b1ee` y luego `b99560e8`. Sigue abierta por la parte de Atlas y por la decision de Luis sobre el baseline de ship-freeze con dueno y fecha.

## Root Cause
El pre-push corre la suite completa y la cobertura sobre un app.slice compartido; con tres sesiones empujando a la vez se llenaban los slots y los commits se acumulaban sin publicar.

## Regression Test
El close_check mismo (grep de `repositorio_publicado` en publicacion.txt) mas la medicion del portero (tasks/evidence/FEATURE-PORTERO-UNIVERSAL-DE-LA-MAQUINA-01/medicion.txt): las suites entran de una en una. Control negativo: `git rev-list --count origin/master~3..master` da 3, asi que el conteo distingue.

## Verification Evidence
- fail: `tasks/evidence/DEBT-PUSHES-ACUMULADOS-BLOQUEADOS-POR-DEUDA-ABIERTA-01/fail.txt`.
- pass: `tasks/evidence/DEBT-PUSHES-ACUMULADOS-BLOQUEADOS-POR-DEUDA-ABIERTA-01/pass.txt`.
- e2e: `tasks/evidence/DEBT-PUSHES-ACUMULADOS-BLOQUEADOS-POR-DEUDA-ABIERTA-01/e2e.txt`.
