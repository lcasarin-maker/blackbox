---
id: DEBT-CLOSE-CHECK-VERIFY-APT-CRITICAL-REMOVALS-01
kind: task
domain: VERDICT
title: "Implementar criterios ejecutables de tools.verify_apt_critical_removals"
status: done
severity: P2
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-10-02
close_check: {"cmd": "python3 -m pytest -q tests/test_debt_registration_controls.py::test_debt_close_check_verify_apt_critical_removals_01", "expect": "exit_zero", "porque": "Cada fase/id soportado evalúa su sujeto específico con capturas reales y controles negativos. Rechazar evidencia ausente, incorrecta, incompleta o controles neutralizados. Separar fail de could_not_run e imprimir ceros. No cerrar investigaciones por existencia de un informe ni por fixtures sanos. Compartir solo lógica realmente común; conservar comandos literales y demostrar discriminación entre fichas."}
closed_at: 2026-10-03
evidence: {"pass":"tasks/evidence/DEBT-CLOSE-CHECK-VERIFY-APT-CRITICAL-REMOVALS-01.pass.txt","fail":"tasks/evidence/DEBT-CLOSE-CHECK-VERIFY-APT-CRITICAL-REMOVALS-01.fail.txt","e2e":"tasks/evidence/DEBT-CLOSE-CHECK-VERIFY-APT-CRITICAL-REMOVALS-01.e2e.txt"}
---

## Registro y responsable

Registro solicitado por Luis el 2026-10-02. Responsable: coordinación de Blackbox. Trabajo o revisión pendiente; la presencia del marcador no demuestra por sí sola un defecto.

## Evidencia y alcance

Módulo ausente citado por 1 fichas. Esta ficha agrupa la implementación compartida; las investigaciones originales conservan sus ensayos y no se duplican.

- tasks/backlog/FEATURE-APT-CRITICAL-METAPACKAGE-GUARD.md

Fuentes: tasks/backlog/FEATURE-APT-CRITICAL-METAPACKAGE-GUARD.md.

## Criterio de cierre y control negativo

Cada fase/id soportado evalúa su sujeto específico con capturas reales y controles negativos. Rechazar evidencia ausente, incorrecta, incompleta o controles neutralizados. Separar fail de could_not_run e imprimir ceros. No cerrar investigaciones por existencia de un informe ni por fixtures sanos. Compartir solo lógica realmente común; conservar comandos literales y demostrar discriminación entre fichas.

## Estado del verificador

Cerrado el instrumento el 2026-10-03: contrasta dos simulaciones reales readonly del host contra el clasificador APT existente. La ficha padre FEATURE-APT-CRITICAL-METAPACKAGE-GUARD sigue abierta; aquí no se acredita protección OEM ni instalación de un guard.

Conservar comandos, salida literal y could_not_run incluso cero; una ejecución skipped o inaccesible deja el cierre pendiente. Reutilizar instrumentos nativos y pruebas existentes antes de crear código.


## Root Cause

Faltaba el módulo verify_apt_critical_removals y el selector de close_check. El preflight ya clasificaba planes APT, pero carecía de una comprobación ejecutable ligada a capturas reales. El primer cierre omitió estas secciones del contrato; la suite completa lo rechazó con 1 failed, 885 passed.

## Regression Test

El close_check ejecuta test_debt_close_check_verify_apt_critical_removals_01: la captura real de upgrade pasa y la remoción real simulada de nvidia-system-station se bloquea. Neutralizar check_apt convierte el resultado en fail=1/could_not_run=0. Datos ausentes o incompletos producen unknown/could_not_run=1; el test CLI comprueba rc=0/1/2 y alteraciones del expediente.

## Verification Evidence

La tríada fail/pass/e2e conserva comandos y salidas. Root comprobó que apt-captures.json es byte por byte la captura readonly original y repitió 17 pruebas en la principal: 17 passed in 0.77s. SHA-256: 018d8932bb86dbb0bb60920ff184cb699fd9bb7c64c11e812610497412daadc2. El instrumento válido reporta fail=0/could_not_run=0; la cobertura OEM y el guard instalado siguen sin verificar en la investigación padre.
