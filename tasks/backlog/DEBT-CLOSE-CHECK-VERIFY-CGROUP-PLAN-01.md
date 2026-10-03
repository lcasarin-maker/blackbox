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
