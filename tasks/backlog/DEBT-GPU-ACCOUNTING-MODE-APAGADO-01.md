---
id: DEBT-GPU-ACCOUNTING-MODE-APAGADO-01
kind: task
domain: GPU
title: "Encender el accounting mode de la GPU para saber que proceso la tenia al caer"
status: open
severity: P2
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-10-10
close_check: {"cmd": "bash tools/verifica_gpu_accounting.sh", "expect": "exit_zero", "porque": "Con accounting apagado, bb scan no puede nombrar los procesos de GPU ya salidos: tras una caida CUDA no se sabe quien tenia la GPU."}
---

## Hueco

`bb scan` imprime `accounting mode: COULD_NOT_RUN (apagado)`. Medido hoy: `nvidia-smi --query-gpu=accounting.mode` da Disabled.
Activarlo exige root (`sudo nvidia-smi -am 1`) y no persiste al reiniciar: hace falta una unit que lo aplique al arrancar, con el mismo patron que `atom-clock-lock.service`.
Quince caidas CUDA del motor (2026-10-08/10) ocurrieron sin que ningun instrumento pudiera nombrar el proceso que usaba la GPU.
