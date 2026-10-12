---
id: FEATURE-INCIDENTE-CARGA-DE-ATLAS-01
kind: task
domain: INCIDENT_CAPTURE
title: "Que bb incident diga que trabajos de Atlas corrian cuando se corto la ATOM"
status: done
closed_at: 2026-10-11
evidence: {"fail": "tasks/evidence/FEATURE-INCIDENTE-CARGA-DE-ATLAS-01.fail.txt", "pass": "tasks/evidence/FEATURE-INCIDENTE-CARGA-DE-ATLAS-01.pass.txt", "e2e": "tasks/evidence/FEATURE-INCIDENTE-CARGA-DE-ATLAS-01.e2e.txt"}
closure_type: fixed
severity: P2
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-10-11
close_check: {"cmd": "python3 -m pytest -q tests/test_incident_report.py -k carga_de_atlas", "expect": "exit_zero", "porque": "Hoy el reporte por incidente conoce los procesos de GPU (nombre y MiB) pero no que trabajo de la cola de Atlas los lanzo. Los tests no existen: el cierre exige implementarlos con control negativo."}
---

Dependencia de informacion de Atlas hacia blackbox (enmienda del 2026-10-11): blackbox lee, solo lectura, el diario de la cola de Atlas (`logs/generate_queue_jobs.jsonl`, bitacora del `liberation-watchdog`) para la ventana del corte y lo imprime en `bb incident` como `carga_de_atlas`. Si el archivo no esta, `NOT_COLLECTED`. Sin `import` de codigo de Atlas.

Por que importa: el 11-oct la otra sesion midio 24 procesos `wineboot` huerfanos con `load` 47; `bb sample` los ve solo de 13:44 a 16:30, despues del corte de las 12:13. Saber que corria Atlas en cada corte separa carga propia de carga ajena sin adivinar.

## Root Cause

`bb incident` conocia los procesos de GPU (nombre y MiB) pero no la cola de trabajos de Atlas, asi que no separaba carga propia de ajena. La ficha nombra `logs/generate_queue_jobs.jsonl` como bitacora del watchdog; medido: ese archivo es el log del GENERADOR de fichas (eventos `job_generated`, `skipped_duplicate`, ...) y no tiene `job_start`. La bitacora que dice que corria es `logs/liberation_watchdog.jsonl` (`job_start` con `boot_id`, `job_done`, `job_orphaned`), y es la que lee `carga_de_atlas`. Ruta sobreescribible con `ATLAS_BITACORA_COLA`.

## Regression Test

`tests/test_incident_report.py -k carga_de_atlas` (6 tests): job abierto del boot sale, job cerrado y job de otro boot no; reintento cuenta por su ultimo `job_start`; sin jobs del boot el cero lleva su alcance; archivo ausente es `NOT_COLLECTED`; ilegible es `COLLECTION_FAILED`; el modulo no importa codigo de Atlas. Las mutaciones del e2e (job_done que no cierra, otro boot que cuenta, ilegible leido como ausente) hacen fallar su test.

## Verification Evidence

`tasks/evidence/FEATURE-INCIDENTE-CARGA-DE-ATLAS-01.fail.txt` (antes, rc=5), `.pass.txt` (rc=0, 6 passed) y `.e2e.txt` (informe real: 10 `job_start`, 9 `job_done`, 1 abierto, `69_01_gen_sparse_side_regen_20261011.json`, que Atlas marco `job_orphaned` con `murio_con_la_maquina: true`; y el control con la bitacora ausente).

## Limites

Lee la bitacora de Atlas por ruta; si Atlas la mueve o cambia el esquema de `job_start`, el campo pasa a `0 job_start ...` o `NOT_COLLECTED`, no a un dato inventado. Las horas de la bitacora son locales sin zona (`inicio_hora_local_de_atlas`). Solo cubre trabajos de la cola `liberation_queue`: lo que Atlas lance fuera de ella (como los 24 `wineboot` que midio la otra sesion) sigue sin verse aqui; eso lo ve `bb sample` por proceso.
