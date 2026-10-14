---
id: FEATURE-BB-FALSO-CUELGUE-POR-AISLAMIENTO-WIFI-01
kind: task
domain: INCIDENT_CAPTURE
title: "Distinguir un cuelgue real de un aislamiento de red cuando el logger local sigue vivo"
status: done
closed_at: 2026-10-13
closure_type: fixed
reason: "clasifica_hueco_de_red existe con 4 tests y control negativo (silencio local => CUELGUE). El cableado en reporte() lo posee FEATURE-OBSERVADOR-EXTERNO-DE-REINICIOS-01, que aporta la fuente red_alcanzable."
evidence: {"pass": "tasks/evidence/FEATURE-BB-FALSO-CUELGUE-POR-AISLAMIENTO-WIFI-01/pass.txt", "fail": "tasks/evidence/FEATURE-BB-FALSO-CUELGUE-POR-AISLAMIENTO-WIFI-01/fail.txt", "e2e": "tasks/evidence/FEATURE-BB-FALSO-CUELGUE-POR-AISLAMIENTO-WIFI-01/e2e.txt"}
severity: P3
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-10-11
close_check: {"cmd": "python3 -m pytest -q tests/test_incident_report.py -k aislamiento_wifi", "expect": "exit_zero", "porque": "El test no existe. Debe cubrir un hueco de red con telemetria local continua (aislamiento, no cuelgue) y uno con telemetria local cortada (cuelgue), como control negativo."}
---

Conocimiento en Atlas: `knowledge/investigations/gb10_cortes_2026-10-11/hilos/hilo_358951_*` (L20: un caso de "idle hard-lockup" resulto ser aislamiento WiFi del MT7925, demostrado porque el logger local siguio con 1473 muestras sanas). Un monitor externo que solo mira ping o SSH da falso positivo.

Instrumento: cuando exista el observador externo (`FEATURE-OBSERVADOR-EXTERNO-DE-REINICIOS-01`), `reboot_verdict` cruza el hueco de ping con la ultima muestra local: telemetria local viva durante el hueco = `AISLAMIENTO_DE_RED`, no corte. Hoy no aplica porque la unica fuente es local.

## Avance 2026-10-13

- close_check antes: rc=5 (0 tests seleccionados, 42 deselected). Ahora: `python3 -m pytest -q tests/test_incident_report.py -k aislamiento_wifi` rc=0 (4 tests, con control negativo de silencio local y de borde).
- Construido: `tools/incident_report.py::clasifica_hueco_de_red(muestras, desde, hasta, red_alcanzable)` -> AISLAMIENTO_DE_RED / CUELGUE / RED_ALCANZABLE / NO_DETERMINADO (sin observacion externa no se infiere).
- Falta: la funcion no esta cableada en `reporte()` porque no existe fuente de `red_alcanzable` hasta FEATURE-OBSERVADOR-EXTERNO-DE-REINICIOS-01.

## Root Cause
Un monitor externo que solo mira ping daba falso positivo de cuelgue cuando el logger local seguia vivo (aislamiento WiFi, no corte); no existia clasificador del hueco.

## Regression Test
tests/test_incident_report.py -k aislamiento_wifi (4 tests): red caida con muestras locales vivas => AISLAMIENTO_DE_RED; control negativo: sin muestras locales => CUELGUE; sin observacion externa => NO_DETERMINADO.

## Verification Evidence
- fail: `tasks/evidence/FEATURE-BB-FALSO-CUELGUE-POR-AISLAMIENTO-WIFI-01/fail.txt`.
- pass: `tasks/evidence/FEATURE-BB-FALSO-CUELGUE-POR-AISLAMIENTO-WIFI-01/pass.txt`.
- e2e: `tasks/evidence/FEATURE-BB-FALSO-CUELGUE-POR-AISLAMIENTO-WIFI-01/e2e.txt`.
