---
id: DEBT-VERIFICAR-DGX-30-OOM-LLAMADORES-CONCURRENTES-01
kind: task
domain: MEMORY
title: "Verificar DGX-30 de Atlas (OOM por llamadores LLM concurrentes) antes de citarlo"
status: open
severity: P3
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-10-12
close_check: {"cmd": "grep -q dgx30_verificado tasks/evidence/DEBT-VERIFICAR-DGX-30-OOM-LLAMADORES-CONCURRENTES-01/verificacion.txt", "expect": "exit_zero", "porque": "La sesion de Atlas lo citó sin releerlo (referenciado en ingest_batch.py e ingest.py). Cierra cuando se lea el incidente en Atlas y se registre que paso, su causa y si el portero lo cubre."}
---

## Que falta
Leer el dictamen o commit de DGX-30 en Atlas (solo lectura), medir su relacion con la estampida del 11-oct y anotar en la ficha del portero.
