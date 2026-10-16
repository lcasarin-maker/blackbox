---
id: DEBT-ESTAMPIDA-DE-SYNC-DE-FLOTA-SIN-ESCALONAR-01
kind: task
domain: MEMORY
title: "Un sync de flota hace empujar a todos los proyectos a la vez: escalonarlo"
status: done
closed_at: 2026-10-16
closure_type: relocated_prior_verification
reason: "regla sync_de_flota_escalonado fijada por voto de Luis en DECISIONS.md, con el portero local (una suite por turno, en actuar) como mecanismo; el escalonamiento del comando de sync vive en simplecode y tiene su ficha"
evidence: {"pass": "tasks/evidence/DEBT-ESTAMPIDA-DE-SYNC-DE-FLOTA-SIN-ESCALONAR-01.pass.txt", "fail": "tasks/evidence/DEBT-ESTAMPIDA-DE-SYNC-DE-FLOTA-SIN-ESCALONAR-01.fail.txt", "e2e": "tasks/evidence/DEBT-ESTAMPIDA-DE-SYNC-DE-FLOTA-SIN-ESCALONAR-01.e2e.txt"}
severity: P1
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-10-12
close_check: {"cmd": "grep -q sync_de_flota_escalonado DECISIONS.md", "expect": "exit_zero", "porque": "La orden de sync del kit 9.9.0 provoco al menos seis pushes con pre-push (suite completa) simultaneos en el colapso 1 del 11-oct. Cierra con una regla durable en DECISIONS.md (frase sync_de_flota_escalonado) y el mecanismo que la haga cumplir (el portero admite una suite a la vez)."}
---

## Medido
Atribucion por las transcripciones de las sesiones, en `DEBT-COLAPSOS-11-OCT-SUITES-PYTEST-SIN-TECHO-01.md`. Los workers `simple`, `proyecto-D atom` y `ae` aceptaron por escrito la regla provisional (una suite a la vez, bajo scope con tope y PSI full < 5); falta que `twiner`, `020` y `atlas` confirmen y que el sync de flota lo escalone `simple` (kit simplecode).

## Root Cause
El sync de flota no tenia regla ni orden: seis `pre-push` a la vez.

## Regression Test
`tests/test_portero.py::test_turno_ocupado_congela_al_nuevo_y_al_liberarse_descongela_al_mas_antiguo`.

## Verification Evidence
Triada en tasks/evidence/. Cierra la parte de este repo; el resto: DEBT-KIT-SYNC-DE-FLOTA-NO-ESCALONA-LOS-PROYECTOS-01.
