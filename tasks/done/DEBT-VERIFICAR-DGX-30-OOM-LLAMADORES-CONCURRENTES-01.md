---
id: DEBT-VERIFICAR-DGX-30-OOM-LLAMADORES-CONCURRENTES-01
kind: task
domain: MEMORY
title: "Verificar DGX-30 de Atlas (OOM por llamadores LLM concurrentes) antes de citarlo"
status: done
closed_at: 2026-10-13
closure_type: relocated_prior_verification
reason: "DGX-30 leido en Atlas (solo lectura): es el cuelgue del 2026-07-31 por NV_ERR_NO_MEMORY del driver (Nemotron 0.70 + BGE-M3 en CUDA), no un OOM por llamadores LLM concurrentes; Atlas lo cerro con gpu_intruder(); el portero de bb no cubre procesos ajenos con CUDA y esa clase queda en el watchdog de Atlas."
evidence: {"pass": "tasks/evidence/DEBT-VERIFICAR-DGX-30-OOM-LLAMADORES-CONCURRENTES-01/pass.txt", "fail": "tasks/evidence/DEBT-VERIFICAR-DGX-30-OOM-LLAMADORES-CONCURRENTES-01/fail.txt", "e2e": "tasks/evidence/DEBT-VERIFICAR-DGX-30-OOM-LLAMADORES-CONCURRENTES-01/e2e.txt"}
severity: P3
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-10-12
close_check: {"cmd": "grep -q dgx30_verificado tasks/evidence/DEBT-VERIFICAR-DGX-30-OOM-LLAMADORES-CONCURRENTES-01/verificacion.txt", "expect": "exit_zero", "porque": "La sesion de Atlas lo citó sin releerlo (referenciado en ingest_batch.py e ingest.py). Cierra cuando se lea el incidente en Atlas y se registre que paso, su causa y si el portero lo cubre."}
---

## Que falta
Leer el dictamen o commit de DGX-30 en Atlas (solo lectura), medir su relacion con la estampida del 11-oct y anotar en la ficha del portero.

## Root Cause
La ficha citaba DGX-30 sin releerlo y con un titulo equivocado ("OOM por llamadores LLM concurrentes"); se leyo el incidente en Atlas.

## Regression Test
No aplica codigo nuevo: es una verificacion de lectura. El `close_check` exige el marcador `dgx30_verificado` en `verificacion.txt`, que contiene las lecturas literales.

## Verification Evidence
fail.txt: el close_check sobre un archivo ausente sale 2; pass.txt: sobre verificacion.txt sale 0; e2e.txt: las lecturas con comando literal (4) estan en verificacion.txt.
