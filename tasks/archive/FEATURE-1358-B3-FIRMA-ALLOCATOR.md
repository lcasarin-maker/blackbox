---
id: FEATURE-1358-B3-FIRMA-ALLOCATOR
kind: task
domain: GPU
title: "Firma de allocator independiente de número de línea"
status: done
reason: "La firma y el watcher se implementaron y probaron como registro de evidencia; no activan recuperación por sí solos."
closure_type: fixed
severity: P2
origin: asserted
created: 2026-10-02
closed_at: 2026-10-02
evidence: {"pass": "tasks/evidence/FEATURE-1358-B3-FIRMA-ALLOCATOR/pass.txt", "fail": "tasks/evidence/FEATURE-1358-B3-FIRMA-ALLOCATOR/fail.txt", "e2e": "tasks/evidence/FEATURE-1358-B3-FIRMA-ALLOCATOR/e2e.txt"}
satd_family: BLIND_INSTRUMENT
close_check: {"cmd": "python3 -m pytest -q tests/test_1358_hitos_nvrm.py -k \"firma_allocator or watcher or error_nvrm\"", "expect": "exit_zero", "porque": "Comportamiento y controles negativos del alcance implementado, sin afirmar despliegue."}
---

## Contexto

Derivada de NVIDIA/open-gpu-kernel-modules#1358 y la comparación del 2026-10-02.

## Alcance

Verificar detección NV_ERR_NO_MEMORY con mem_desc.c:1359 y1361, error sin cuelgue y cuelgue sin error; corregir watcher que etiqueta predictor suficiente. No actuar por NVRM solo. Reusar patrones existentes y controles.

## Verificación y límite

`python3 -m pytest -q tests/test_1358_hitos_nvrm.py`: 28 passed, incluidos `mem_desc.c:1359` y `mem_desc.c:1361`, error sin señal PSI, PSI sin NVRM y controles comportamentales del watcher. `pyright tools/hitos_incidente.py tests/test_1358_hitos_nvrm.py`: 0 errores. Evidencia: per-task pass/fail/E2E abajo.

El watcher registra errores NVRM como evidencia y no inicia una recuperación por ese evento. Detección y watcher se validaron con fixtures; no se desplegó ni se probó una asignación real fallida en este turno.

## Root Cause

La firma `NV_ERR_NO_MEMORY` puede identificar errores de allocator, pero por sí sola no establece un cuelgue. Se evita presentar el error como predictor o causa raíz universal.

## Regression Test

`tests/test_1358_hitos_nvrm.py` prueba `mem_desc.c:1359`/`1361`, error sin wedge, PSI sin NVRM, mensajes normales de watchdog y el watcher ante coincidencia y ausencia de NVRM.

## Verification Evidence

Salidas reales de pytest: `tasks/evidence/FEATURE-1358-B3-FIRMA-ALLOCATOR/{pass,fail,e2e}.txt`; validaciones adicionales: `tasks/evidence/SWARM-LUNA-1358-2026-10-02/a3-b3-checks.txt`.
