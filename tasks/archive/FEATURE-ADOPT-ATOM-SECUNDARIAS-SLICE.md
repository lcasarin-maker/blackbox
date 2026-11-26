---
id: FEATURE-ADOPT-ATOM-SECUNDARIAS-SLICE
kind: task
domain: SYSTEMD
title: "Adopción e instrumentación de atom-secundarias.slice (Aislamiento de cgroups v2 en GB10)"
status: done
closed_at: 2026-10-10
closure_type: fixed
reason: "La unidad adoptada pasa systemd-analyze verify sin advertencias, el control negativo de una unidad rota si las produce y MemoryHigh < MemoryMax; el despliegue en la maquina queda en DEBT-ATOM-SECUNDARIAS-SLICE-SIN-DESPLEGAR-01 porque exige root."
evidence: {"pass":"tasks/evidence/FEATURE-ADOPT-ATOM-SECUNDARIAS-SLICE/pass.txt","fail":"tasks/evidence/FEATURE-ADOPT-ATOM-SECUNDARIAS-SLICE/fail.txt","e2e":"tasks/evidence/FEATURE-ADOPT-ATOM-SECUNDARIAS-SLICE/e2e.txt"}
owner: Luis
severity: P2
origin: asserted
satd_family: INFRASTRUCTURE_GOVERNANCE
created: 2026-10-08
close_check: {"cmd": "pytest -q tests/test_atom_slice.py", "expect": "exit_zero", "porque": "Valida que atom-secundarias.slice no produzca advertencias sintácticas en systemd-analyze, que el control negativo falle deliberadamente y que MemoryHigh < MemoryMax."}
---

## Contexto y Procedencia

Procedencia: rescatado de `migracion_atom/systemd/atom-secundarias.slice` y `migracion_atom/tests/test_systemd_slice.py` (TASK-ATOM-01) durante el colapso y consolidación de la flota.

En estaciones NVIDIA GB10 con arquitectura de memoria unificada (Grace/Blackwell con 128 GB LPDDR5X coherentes), los procesos secundarios no regulados (scripts de indexado, crawlers, OCR, tareas auxiliares) compiten directamente por la memoria física compartida que vLLM necesita para inferencia. Sin límites de cgroups v2, una sobrecarga en tareas secundarias detona caídas fatales de vLLM o reinicios por watchdog.

## Artefactos Incorporados

1. Unidad de servicio systemd: `adopted/system-config/etc_systemd_system_atom-secundarias.slice`
   - `MemoryHigh=32G` (umbral blando de throttling de reclaim).
   - `MemoryMax=48G` (límite duro con OOM-killer confinado dentro del slice secundario).
2. Suite de verificación determinista: `tests/test_atom_slice.py`
   - Comprobación sintáctica con `systemd-analyze verify`.
   - Control negativo contra una unidad sintéticamente rota.
   - Validación aritmética de `MemoryHigh < MemoryMax`.

## Criterio de Cierre

Ejecución exitosa de `pytest -q tests/test_atom_slice.py` con 3/3 tests aprobados.

## Cierre por /clean (2026-10-10)

Este trabajo lo dejo una sesion anterior sin commitear (archivos del 2026-10-08). `/clean` lo cosecho y lo completo con lo que faltaba para que el repo lo aceptara. Lo inferido, separado de la letra del autor:

- La unidad se renombro a `etc_systemd_system_atom-secundarias.slice`: con el nombre original `bb drift` la buscaba en `/atom-secundarias.slice`, una ruta que no existe. Su contenido es identico byte a byte a `migracion_atom/systemd/atom-secundarias.slice`.
- Se agrego el paso al instalador `enable-privileged.sh` y su fila en el inventario de SPEC.md.
- La unica linea cambiada en `tests/test_atom_slice.py` es la ruta de la unidad.
- El despliegue real queda fuera: exige root. Ficha `DEBT-ATOM-SECUNDARIAS-SLICE-SIN-DESPLEGAR-01`.

## Root Cause

Sin limites de cgroups v2, los procesos secundarios (indexado, migracion, OCR) competian por la memoria unificada que vLLM necesita en la GB10, y una sobrecarga detonaba caidas del motor. La unidad existia solo en `migracion_atom` y no estaba en este repo.

## Regression Test

`python3 -m pytest -q tests/test_atom_slice.py`: la unidad real no produce advertencias de `systemd-analyze verify`, una unidad deliberadamente rota SI las produce (control negativo) y `MemoryHigh` es menor que `MemoryMax`.

## Verification Evidence

- `tasks/evidence/FEATURE-ADOPT-ATOM-SECUNDARIAS-SLICE/fail.txt`: la unidad rota produce las dos advertencias (`Invalid memory limit` y `Unknown key name`) con exit 0, por eso el criterio mira la salida y no el codigo.
- `tasks/evidence/FEATURE-ADOPT-ATOM-SECUNDARIAS-SLICE/pass.txt`: 3 pruebas pasan.
- `tasks/evidence/FEATURE-ADOPT-ATOM-SECUNDARIAS-SLICE/e2e.txt`: verificacion limpia, identica al origen y `bb drift` marcando AUSENTE hasta el despliegue (ficha `DEBT-ATOM-SECUNDARIAS-SLICE-SIN-DESPLEGAR-01`).
