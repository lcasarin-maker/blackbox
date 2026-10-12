---
id: FEATURE-INCIDENTE-CARGA-DE-ATLAS-01
kind: task
domain: INCIDENT_CAPTURE
title: "Que bb incident diga que trabajos de Atlas corrian cuando se corto la ATOM"
status: open
severity: P2
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-10-11
close_check: {"cmd": "python3 -m pytest -q tests/test_incident_report.py -k carga_de_atlas", "expect": "exit_zero", "porque": "Hoy el reporte por incidente conoce los procesos de GPU (nombre y MiB) pero no que trabajo de la cola de Atlas los lanzo. Los tests no existen: el cierre exige implementarlos con control negativo."}
---

Dependencia de informacion de Atlas hacia blackbox (enmienda del 2026-10-11): blackbox lee, solo lectura, el diario de la cola de Atlas (`logs/generate_queue_jobs.jsonl`, bitacora del `liberation-watchdog`) para la ventana del corte y lo imprime en `bb incident` como `carga_de_atlas`. Si el archivo no esta, `NOT_COLLECTED`. Sin `import` de codigo de Atlas.

Por que importa: el 11-oct la otra sesion midio 24 procesos `wineboot` huerfanos con `load` 47; `bb sample` los ve solo de 13:44 a 16:30, despues del corte de las 12:13. Saber que corria Atlas en cada corte separa carga propia de carga ajena sin adivinar.
