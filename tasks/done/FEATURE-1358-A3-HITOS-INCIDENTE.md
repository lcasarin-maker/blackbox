---
id: FEATURE-1358-A3-HITOS-INCIDENTE
kind: feature
title: "Hitos temporales separados del incidente"
status: done
reason: "Alcance local implementado y verificado; despliegue y calibración contra incidentes se declaran aparte. Evidencia integrada en verification.txt."
closure_type: fixed
severity: P2
origin: asserted
created: 2026-10-02
closed_at: 2026-10-02
evidence: {"pass": "tasks/evidence/SWARM-LUNA-1358-2026-10-02/verification.txt"}
close_check: {"cmd": "python3 -m pytest -q tests/test_1358_hitos_nvrm.py -k \"not firma_allocator and not watcher and not error_nvrm\"", "expect": "exit_zero", "porque": "Comportamiento y controles negativos del alcance implementado, sin afirmar despliegue."}
---

## Contexto

Derivada de NVIDIA/open-gpu-kernel-modules#1358 y la comparación del 2026-10-02.

## Alcance

Crear análisis mínimo stdlib de registros aportados: NVRM, señal de colapso PSI, pérdida/recuperación de servicio, acción watchdog y próximo boot. Preservar zona/boot, incertidumbre y campos ausentes; no inferir inicio físico desde detección. CLI documentada y fixtures control negativos.

## Verificación y límite

`python3 -m pytest -q tests/test_1358_hitos_nvrm.py`: 11 passed. `python3 -m ruff check tools/hitos_incidente.py tests/test_1358_hitos_nvrm.py`: All checks passed. `bash -n adopted/system-config/usr_local_bin_nvrm-watch.sh`: exit 0. `git diff --check`: exit 0. Evidencia de CLI contra journal real: `tasks/evidence/SWARM-LUNA-1358-2026-10-02/a3-b3-checks.txt`.

Los hitos son observaciones con timestamp explícito en UTC para journal y zona original para muestras, e identidad de boot cuando existe. Señales de PSI, fallo de respuesta SSH, timeout de servicio watchdog, fallo de unit y primera observación del siguiente boot aparecen separadas. `could_not_run` registra datos de entrada ausentes o inválidos. No se estima inicio físico ni causalidad. Sin despliegue ni validación ante incidentes nuevos.
