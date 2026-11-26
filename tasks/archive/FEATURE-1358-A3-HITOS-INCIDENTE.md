---
id: FEATURE-1358-A3-HITOS-INCIDENTE
kind: task
domain: GPU
title: "Hitos temporales separados del incidente"
status: done
reason: "Alcance local implementado y verificado; despliegue y validación de nuevos incidentes se declaran aparte."
closure_type: fixed
severity: P2
origin: asserted
created: 2026-10-02
closed_at: 2026-10-02
evidence: {"pass": "tasks/evidence/FEATURE-1358-A3-HITOS-INCIDENTE/pass.txt", "fail": "tasks/evidence/FEATURE-1358-A3-HITOS-INCIDENTE/fail.txt", "e2e": "tasks/evidence/FEATURE-1358-A3-HITOS-INCIDENTE/e2e.txt"}
satd_family: BLIND_INSTRUMENT
close_check: {"cmd": "python3 -m pytest -q tests/test_1358_hitos_nvrm.py -k \"not firma_allocator and not watcher and not error_nvrm\"", "expect": "exit_zero", "porque": "Comportamiento y controles negativos del alcance implementado, sin afirmar despliegue."}
---

## Contexto

Derivada de NVIDIA/open-gpu-kernel-modules#1358 y la comparación del 2026-10-02.

## Alcance

Crear análisis mínimo stdlib de registros aportados: NVRM, señal de colapso PSI, pérdida/recuperación de servicio, acción watchdog y próximo boot. Preservar zona/boot, incertidumbre y campos ausentes; no inferir inicio físico desde detección. CLI documentada y fixtures control negativos.

## Verificación y límite

`python3 -m pytest -q tests/test_1358_hitos_nvrm.py`: 28 passed. `pyright tools/hitos_incidente.py tests/test_1358_hitos_nvrm.py`: 0 errors. `python3 -m coverage run --data-file=/tmp/coverage-hitos --source=tools.hitos_incidente -m pytest -q tests/test_1358_hitos_nvrm.py`; coverage report: 181 statements, 0 missing, 100%. `ruff check` and `bash -n adopted/system-config/usr_local_bin_nvrm-watch.sh` passed. Evidence: per-task pass/fail/E2E output files below.

Los hitos son observaciones con timestamp explícito en UTC para journal y zona original para muestras, e identidad de boot cuando existe. Señales de PSI, fallo de respuesta SSH, timeout de servicio watchdog, fallo de unit y primera observación del siguiente boot aparecen separadas. `could_not_run` registra datos de entrada ausentes o inválidos. No se estima inicio físico ni causalidad. Sin despliegue ni validación ante incidentes nuevos.

## Root Cause

Los registros separaban fuentes y ventanas sin una salida que distinguiera el error del allocator, la señal de PSI, la sonda de servicio, el timeout del watchdog y la primera observación del siguiente boot. Este déficit de cronología no determina la causa del fallo de GPU.

## Regression Test

`tests/test_1358_hitos_nvrm.py` cubre tiempos con offset, cambio de boot, campos ausentes, JSON inválido, estados de servicio y un journal persistido real.

## Verification Evidence

Salidas reales de pytest: `tasks/evidence/FEATURE-1358-A3-HITOS-INCIDENTE/{pass,fail,e2e}.txt`; resumen de cobertura: `tasks/evidence/SWARM-LUNA-1358-2026-10-02/a3-b3-checks.txt`.
