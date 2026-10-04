---
id: DEBT-CLOSE-CHECK-VERIFY-FORUM-FINDING-01
kind: task
domain: VERDICT
title: "Implementar criterios ejecutables de tools.verify_forum_finding"
status: open
severity: P2
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-10-02
close_check: {"cmd": "python3 -m pytest -q tests/test_debt_registration_controls.py::test_debt_close_check_verify_forum_finding_01", "expect": "exit_zero", "porque": "Cada fase/id soportado evalúa su sujeto específico con capturas reales y controles negativos. Rechazar evidencia ausente, incorrecta, incompleta o controles neutralizados. Separar fail de could_not_run e imprimir ceros. No cerrar investigaciones por existencia de un informe ni por fixtures sanos. Compartir solo lógica realmente común; conservar comandos literales y demostrar discriminación entre fichas."}
---

## Registro y responsable

Registro solicitado por Luis el 2026-10-02. Responsable: coordinación de Blackbox. Trabajo o revisión pendiente; la presencia del marcador no demuestra por sí sola un defecto.

## Evidencia y alcance

Registro inicial: módulo ausente citado por 15 fichas. El módulo y el selector original ya están disponibles. Esta ficha agrupa la implementación compartida; las investigaciones originales conservan sus ensayos y no se duplican.

- tasks/backlog/FORUM-00-CX7-HOTPLUG-FAN-PROTECTION.md
- tasks/backlog/FEATURE-FORUM-PROVIDER-FALLBACK-REGRESSION-01.md
- tasks/backlog/FORUM-02-GX10-READ-INTEGRITY.md
- tasks/backlog/FEATURE-FORUM-SBSA-WATCHDOG-STATE-01.md
- tasks/backlog/FORUM-REALTEK-DRIVER-BINDING-01.md
- tasks/backlog/FEATURE-FORUM-GB10-RUNTIME-COMPAT-01.md
- tasks/backlog/FEATURE-FORUM-DESKTOP-SESSION-POSTUPDATE-01.md
- tasks/backlog/FORUM-00-KERNEL-INITRD-UPDATE-GATE.md
- tasks/backlog/FORUM-00-REALTEK-EEE-DIRECT-LINK.md
- tasks/backlog/FORUM-00-DGX-OTA-DRM-COMPAT-PREFLIGHT.md
- tasks/backlog/FEATURE-FORUM-RESCUE-RUNBOOK-01.md
- tasks/backlog/FORUM-02-PSTORE-KERNEL-REGRESSION.md
- tasks/backlog/FORUM-00-GB10-THERMAL-RESIDENCY-ADMISSION.md
- tasks/backlog/FEATURE-FORUM-GPU-GSP-BOOT-HEALTH-01.md
- tasks/backlog/FORUM-02-USB-UVC-EP0.md

Fuentes: tasks/backlog/FORUM-00-CX7-HOTPLUG-FAN-PROTECTION.md, tasks/backlog/FEATURE-FORUM-PROVIDER-FALLBACK-REGRESSION-01.md, tasks/backlog/FORUM-02-GX10-READ-INTEGRITY.md, tasks/backlog/FEATURE-FORUM-SBSA-WATCHDOG-STATE-01.md, tasks/backlog/FORUM-REALTEK-DRIVER-BINDING-01.md, tasks/backlog/FEATURE-FORUM-GB10-RUNTIME-COMPAT-01.md, tasks/backlog/FEATURE-FORUM-DESKTOP-SESSION-POSTUPDATE-01.md, tasks/backlog/FORUM-00-KERNEL-INITRD-UPDATE-GATE.md, tasks/backlog/FORUM-00-REALTEK-EEE-DIRECT-LINK.md, tasks/backlog/FORUM-00-DGX-OTA-DRM-COMPAT-PREFLIGHT.md, tasks/backlog/FEATURE-FORUM-RESCUE-RUNBOOK-01.md, tasks/backlog/FORUM-02-PSTORE-KERNEL-REGRESSION.md, tasks/backlog/FORUM-00-GB10-THERMAL-RESIDENCY-ADMISSION.md, tasks/backlog/FEATURE-FORUM-GPU-GSP-BOOT-HEALTH-01.md, tasks/backlog/FORUM-02-USB-UVC-EP0.md.

## Criterio de cierre y control negativo

Cada fase/id soportado evalúa su sujeto específico con capturas reales y controles negativos. Rechazar evidencia ausente, incorrecta, incompleta o controles neutralizados. Separar fail de could_not_run e imprimir ceros. No cerrar investigaciones por existencia de un informe ni por fixtures sanos. Compartir solo lógica realmente común; conservar comandos literales y demostrar discriminación entre fichas.

## Estado del verificador

La ficha permanece abierta. El selector original ejecutó 33 IDs soportados: 0 PASS, 0 FAIL, 33 UNKNOWN y 44 could_not_run. Recibo: tasks/evidence/CLOSURE-CONTROLS-2026-10-03/forum-original-selector-primary-run.json. El enrutador integrado conserva las capturas pendientes y la cobertura parcial de los evaluadores.

Conservar comandos, salida literal y could_not_run incluso cero; una ejecución skipped o inaccesible deja el cierre pendiente. Reutilizar instrumentos nativos y pruebas existentes antes de crear código.

## Clasificación del impedimento — 2026-10-04

- Categoría principal: `missing_history`.
- Impedimento: Los selectores y el router existen. La ficha cita recibo con UNKNOWN/CNR y cobertura parcial, sin un defecto concreto del router reproducido.
- Evidencia faltante para cierre: Evidencia cruda y controles negativos aceptados por cada ID soportado; resultados literales y conteos PASS/FAIL/UNKNOWN/CNR.
- Siguiente acción: Leer el recibo por ID y convertir cada UNKNOWN/CNR en una solicitud de captura cruda específica; corregir solo una predicado si un caso raw identifica un fallo actual del evaluador. No recrear selector/router.
- Responsable del siguiente paso: BB.
- Cierre completo accionable hoy: no. Preparación coordinable: sí.
- Evidencias de clasificación: `tasks/backlog/DEBT-CLOSE-CHECK-VERIFY-FORUM-FINDING-01.md`, `tasks/evidence/CLOSURE-CONTROLS-2026-10-03/forum-original-selector-primary-run.json`, `tools/forum_finding.py`, `tools/hardware_evidence.py`, `tests/test_debt_registration_controls.py`, `tools/verify_forum_finding.py`.
- Impedimentos de inspección: 0. El criterio original permanece intacto; esta clasificación conserva la ficha abierta.
