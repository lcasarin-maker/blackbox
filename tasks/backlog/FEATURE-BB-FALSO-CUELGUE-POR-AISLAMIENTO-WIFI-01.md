---
id: FEATURE-BB-FALSO-CUELGUE-POR-AISLAMIENTO-WIFI-01
kind: task
domain: INCIDENT_CAPTURE
title: "Distinguir un cuelgue real de un aislamiento de red cuando el logger local sigue vivo"
status: open
severity: P3
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-10-11
close_check: {"cmd": "python3 -m pytest -q tests/test_incident_report.py -k aislamiento_wifi", "expect": "exit_zero", "porque": "El test no existe. Debe cubrir un hueco de red con telemetria local continua (aislamiento, no cuelgue) y uno con telemetria local cortada (cuelgue), como control negativo."}
---

Conocimiento en Atlas: `knowledge/investigations/gb10_cortes_2026-10-11/hilos/hilo_358951_*` (L20: un caso de "idle hard-lockup" resulto ser aislamiento WiFi del MT7925, demostrado porque el logger local siguio con 1473 muestras sanas). Un monitor externo que solo mira ping o SSH da falso positivo.

Instrumento: cuando exista el observador externo (`FEATURE-OBSERVADOR-EXTERNO-DE-REINICIOS-01`), `reboot_verdict` cruza el hueco de ping con la ultima muestra local: telemetria local viva durante el hueco = `AISLAMIENTO_DE_RED`, no corte. Hoy no aplica porque la unica fuente es local.
