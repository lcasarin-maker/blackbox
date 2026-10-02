---
id: FEATURE-1358-B3-FIRMA-ALLOCATOR
kind: feature
title: "Firma de allocator independiente de número de línea"
status: done
reason: "Alcance local implementado y verificado; despliegue y calibración contra incidentes se declaran aparte. Evidencia integrada en verification.txt."
closure_type: fixed
severity: P2
origin: asserted
created: 2026-10-02
closed_at: 2026-10-02
evidence: {"pass": "tasks/evidence/SWARM-LUNA-1358-2026-10-02/verification.txt"}
close_check: {"cmd": "python3 -m pytest -q tests/test_1358_hitos_nvrm.py -k \"firma_allocator or watcher or error_nvrm\"", "expect": "exit_zero", "porque": "Comportamiento y controles negativos del alcance implementado, sin afirmar despliegue."}
---

## Contexto

Derivada de NVIDIA/open-gpu-kernel-modules#1358 y la comparación del 2026-10-02.

## Alcance

Verificar detección NV_ERR_NO_MEMORY con mem_desc.c:1359 y1361, error sin cuelgue y cuelgue sin error; corregir watcher que etiqueta predictor suficiente. No actuar por NVRM solo. Reusar patrones existentes y controles.

## Verificación y límite

`python3 -m pytest -q tests/test_1358_hitos_nvrm.py`: 11 passed, incluidos `mem_desc.c:1359` y `mem_desc.c:1361`, error sin señal PSI, PSI sin NVRM y controles comportamentales del watcher. `python3 -m ruff check tools/hitos_incidente.py tests/test_1358_hitos_nvrm.py`: All checks passed. `bash -n adopted/system-config/usr_local_bin_nvrm-watch.sh`: exit 0. `git diff --check`: exit 0. Evidencia: `tasks/evidence/SWARM-LUNA-1358-2026-10-02/a3-b3-checks.txt`.

El watcher registra errores NVRM como evidencia y no inicia una recuperación por ese evento. Detección y watcher se validaron con fixtures; no se desplegó ni se probó una asignación real fallida en este turno.
