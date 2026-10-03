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

Módulo ausente citado por 15 fichas. Esta ficha agrupa la implementación compartida; las investigaciones originales conservan sus ensayos y no se duplican.

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

La ficha permanece abierta. El test selector del close_check es una especificación pendiente, no una prueba existente ni un resultado ejecutado. Implementarlo exige comprobar el sujeto y su control negativo; la existencia de archivos o esta ficha no basta para cerrar.

Conservar comandos, salida literal y could_not_run incluso cero; una ejecución skipped o inaccesible deja el cierre pendiente. Reutilizar instrumentos nativos y pruebas existentes antes de crear código.
