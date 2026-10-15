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

## Avance 2026-10-13: encendido en vivo; la persistencia queda lista para desplegar
`nvidia-smi --query-gpu=accounting.mode` da `Enabled` (lo encendio el instalador que corrio Luis) y `bash tools/verifica_gpu_accounting.sh` sale 0. No sobrevive un reinicio del driver: el instalador lo dice ("hasta el proximo reinicio del driver"). Construido: `adopted/pendiente-de-despliegue/etc_systemd_system_bb-gpu-accounting.service` (oneshot `nvidia-smi -am 1` tras nvidia-persistenced) y `tests/test_unidad_gpu_accounting.py` (2 tests; el segundo distingue la unidad de la de clock). Falta: desplegar la unidad (pasos en `adopted/pendiente-de-despliegue/LEEME.txt`; `systemctl enable` recarga systemd, mismo riesgo P1 que el daemon-reload) y verificar `Enabled` tras el proximo reinicio. Cierra entonces, no antes.

## Avance 2026-10-15: unidad desplegada; falta verificar tras el proximo reinicio
Ventana del motor con sudo de Luis (`tasks/evidence/VENTANA-VLLM-20261015/ventana.sh`): `bb-gpu-accounting.service` instalada (`cmp` contra el repo sin diferencias, ahora en `adopted/system-config/`), `enable --now` rc 0; `is-enabled: enabled`, `is-active: active`, `nvidia-smi --query-gpu=accounting.mode` = `Enabled`, `bash tools/verifica_gpu_accounting.sh` rc 0. Sigue abierta por su propia regla ("cierra entonces, no antes"): hay que ver `Enabled` DESPUES del proximo reinicio del driver o de la maquina, que es lo que la unidad existe para garantizar.
