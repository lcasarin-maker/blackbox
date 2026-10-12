---
id: FEATURE-BB-PREFLIGHT-KERNEL-KHO-01
kind: task
domain: HARDWARE
title: "bb status avisa si el kernel es 7.0.0-1019 sin kho=off o con CMA en 0"
status: open
severity: P2
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-10-11
close_check: {"cmd": "python3 -m pytest -q tests/test_status_kernel_kho.py", "expect": "exit_zero", "porque": "El test no existe. Debe cubrir el kernel malo con y sin kho=off, y 6.17.0-1032 sano como control negativo."}
---

Conocimiento en Atlas: `knowledge/investigations/gb10_cortes_2026-10-11/hilos/hilo_383023_*` (L20: causa raiz medida de la regresion del kernel 7.0.0-1019: KHO deja ~9.3 GiB marcados como MIGRATE_CMA fuera de la contabilidad y CONFIG_CMA_SIZE_MBYTES pasa de 128 a 0; hotfix oficial `kho=off`; el mismo hilo, post #44, reporta un caso que persiste con `kho=off`).

Instrumento: `bb status` lee `uname -r`, `/proc/cmdline` y `CmaTotal` de `/proc/meminfo` y declara `KERNEL_CONOCIDO_MALO`, `ARMADO` o `NOT_COLLECTED`. Esta maquina corre 6.17.0-1032 (sana en esa regresion): el valor es detectar una actualizacion automatica que la cambie.
