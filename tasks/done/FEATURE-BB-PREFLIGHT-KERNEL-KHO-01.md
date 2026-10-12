---
id: FEATURE-BB-PREFLIGHT-KERNEL-KHO-01
kind: task
domain: HARDWARE
title: "bb status avisa si el kernel es 7.0.0-1019 sin kho=off o con CMA en 0"
status: done
closed_at: 2026-10-11
closure_type: fixed
reason: "bb status declara KERNEL_CONOCIDO_MALO, ARMADO o NOT_COLLECTED leyendo /proc/version, /proc/cmdline y CmaTotal."
evidence: {"pass": "tasks/evidence/FEATURE-BB-PREFLIGHT-KERNEL-KHO-01.pass.txt", "fail": "tasks/evidence/FEATURE-BB-PREFLIGHT-KERNEL-KHO-01.fail.txt", "e2e": "tasks/evidence/FEATURE-BB-PREFLIGHT-KERNEL-KHO-01.e2e.txt"}
severity: P2
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-10-11
close_check: {"cmd": "python3 -m pytest -q tests/test_status_kernel_kho.py", "expect": "exit_zero", "porque": "El test no existe. Debe cubrir el kernel malo con y sin kho=off, y 6.17.0-1032 sano como control negativo."}
---

Conocimiento en Atlas: `knowledge/investigations/gb10_cortes_2026-10-11/hilos/hilo_383023_*` (L20: causa raiz medida de la regresion del kernel 7.0.0-1019: KHO deja ~9.3 GiB marcados como MIGRATE_CMA fuera de la contabilidad y CONFIG_CMA_SIZE_MBYTES pasa de 128 a 0; hotfix oficial `kho=off`; el mismo hilo, post #44, reporta un caso que persiste con `kho=off`).

Instrumento: `bb status` lee `uname -r`, `/proc/cmdline` y `CmaTotal` de `/proc/meminfo` y declara `KERNEL_CONOCIDO_MALO`, `ARMADO` o `NOT_COLLECTED`. Esta maquina corre 6.17.0-1032 (sana en esa regresion): el valor es detectar una actualizacion automatica que la cambie.

## Root Cause

`bb status` no leia el kernel en uso ni su cmdline: una actualizacion automatica a 7.0.0-1019 (KHO deja CmaTotal en 0) pasaba sin aviso.

## Regression Test

`tests/test_status_kernel_kho.py` redirige /proc con BB_PROC_DIR: kernel malo sin kho=off, malo con kho=off y CMA sano (ARMADO), malo con kho=off y CMA en 0 (post #44), 6.17.0-1032 sano, kho=offline como subcadena y tres lecturas ilegibles (NOT_COLLECTED, could_not_run>0). Limite declarado: solo se evalua el kernel nombrado.

## Verification Evidence

Antes: rc=4, el test no existia (.fail). Despues: 8 passed (.pass). Control negativo corrido: con la llamada anulada, 8 failed. shellcheck y bash -n limpios; bb status real muestra la fila ARMADO (.e2e).
