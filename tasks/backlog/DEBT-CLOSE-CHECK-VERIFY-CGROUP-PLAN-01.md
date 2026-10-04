---
id: DEBT-CLOSE-CHECK-VERIFY-CGROUP-PLAN-01
kind: task
domain: VERDICT
title: "Implementar criterios ejecutables de tools.verify_cgroup_plan"
status: open
severity: P2
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-10-02
close_check: {"cmd": "python3 -m pytest -q tests/test_debt_registration_controls.py::test_debt_close_check_verify_cgroup_plan_01", "expect": "exit_zero", "porque": "Cada fase/id soportado evalúa su sujeto específico con capturas reales y controles negativos. Rechazar evidencia ausente, incorrecta, incompleta o controles neutralizados. Separar fail de could_not_run e imprimir ceros. No cerrar investigaciones por existencia de un informe ni por fixtures sanos. Compartir solo lógica realmente común; conservar comandos literales y demostrar discriminación entre fichas."}
---

## Registro y responsable

Registro solicitado por Luis el 2026-10-02. Responsable: coordinación de Blackbox. Trabajo o revisión pendiente; la presencia del marcador no demuestra por sí sola un defecto.

## Evidencia y alcance

Módulo ausente citado por 4 fichas. Esta ficha agrupa la implementación compartida; las investigaciones originales conservan sus ensayos y no se duplican.

- tasks/backlog/FEATURE-1358-CGROUP-04-PARCHE.md
- tasks/backlog/FEATURE-1358-CGROUP-03-NATIVO.md
- tasks/backlog/FEATURE-1358-CGROUP-05-CUELGUES.md
- tasks/backlog/FEATURE-1358-CGROUP-02-TRAZA.md

Fuentes: tasks/backlog/FEATURE-1358-CGROUP-04-PARCHE.md, tasks/backlog/FEATURE-1358-CGROUP-03-NATIVO.md, tasks/backlog/FEATURE-1358-CGROUP-05-CUELGUES.md, tasks/backlog/FEATURE-1358-CGROUP-02-TRAZA.md.

## Criterio de cierre y control negativo

Cada fase/id soportado evalúa su sujeto específico con capturas reales y controles negativos. Rechazar evidencia ausente, incorrecta, incompleta o controles neutralizados. Separar fail de could_not_run e imprimir ceros. No cerrar investigaciones por existencia de un informe ni por fixtures sanos. Compartir solo lógica realmente común; conservar comandos literales y demostrar discriminación entre fichas.

## Estado del verificador

La ficha permanece abierta. El test selector del close_check es una especificación pendiente, no una prueba existente ni un resultado ejecutado. Implementarlo exige comprobar el sujeto y su control negativo; la existencia de archivos o esta ficha no basta para cerrar.

Conservar comandos, salida literal y could_not_run incluso cero; una ejecución skipped o inaccesible deja el cierre pendiente. Reutilizar instrumentos nativos y pruebas existentes antes de crear código.

## Clasificación del impedimento — 2026-10-04

- Categoría principal: `workload_or_lab`.
- Impedimento: El selector y tools.verify_cgroup_plan ya existen. Su close_check agrega fase 01 y las fases 02–05; 02 carece de capture.json, 03 requiere ejecución del driver 615/GPU runtime con dos cgroups y binding 02, 04 no tiene diff/gap demostrado, y 05 requiere evidencia real de cuelgues. El recibo root 2026-10-04 confirma controller dmem disponible pero root dmem.capacity/current vacíos (CNR=0), no sujeto GPU registrado.
- Evidencia faltante para cierre: Raw phase capture.json bound to exact id/phase/boot/kernel/driver for 02–05; phase 03 paired 580/615 stack runs and bound trace; 04 evidence of residual defect or proof native path covers it; safe real hang reproduction/control for 05. Root summary native-cgroup-capability-root-summary-20261004.json is host capability only.
- Siguiente acción: Coordinación BB: primero revisar tools/verify_cgroup_plan.py y tests/test_closure_kernel_selectors.py::closure_selector_cgroup_plan_01; preparar dossier 02–05 con los esquemas exactos. Operador Luis: sólo en canario GPU/lab, capturar fases 02/03 y 05 con salida raw; no inventar el dmem vacío como ausencia de controller. Revaluar si 04 necesita parche cuando 03 confirme el stack. Ref: tasks/evidence/CLOSURE-CONTROLS-2026-10-03/native-cgroup-capability-root-summary-20261004.json; tasks/evidence/CLOSURE-CONTROLS-2026-10-03/FEATURE-1358-CGROUP-02-TRAZA-direct-close-current.log; tasks/evidence/FEATURE-1358-CGROUP-03-NATIVO/comparison.txt; tasks/evidence/FEATURE-1358-CGROUP-04-PARCHE/readiness.txt; tasks/evidence/FEATURE-1358-CGROUP-05-CUELGUES/host-controls.txt.
- Responsable del siguiente paso: Coordinación BB; para recuperación de históricos, custodio del artifact store si corresponde..
- Cierre completo accionable hoy: no. Preparación coordinable: sí.
- Evidencias de clasificación: `tasks/backlog/DEBT-CLOSE-CHECK-VERIFY-CGROUP-PLAN-01.md`, `tests/test_debt_registration_controls.py`, `tools/verify_cgroup_plan.py`, `tests/test_closure_kernel_selectors.py`, `tasks/evidence/CLOSURE-CONTROLS-2026-10-03/native-cgroup-capability-root-summary-20261004.json`, `tasks/evidence/CLOSURE-CONTROLS-2026-10-03/FEATURE-1358-CGROUP-02-TRAZA-direct-close-current.log`, `tasks/evidence/FEATURE-1358-CGROUP-03-NATIVO/comparison.txt`, `tasks/evidence/FEATURE-1358-CGROUP-04-PARCHE/readiness.txt`, `tasks/evidence/FEATURE-1358-CGROUP-05-CUELGUES/host-controls.txt`, `tasks/evidence/OPEN-96-CLASSIFICATION-2026-10-04/batches/batch_00.json`.
- Impedimentos de inspección: 0. El criterio original permanece intacto; esta clasificación conserva la ficha abierta.
