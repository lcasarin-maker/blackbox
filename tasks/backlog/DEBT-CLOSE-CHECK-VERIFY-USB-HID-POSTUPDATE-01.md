---
id: DEBT-CLOSE-CHECK-VERIFY-USB-HID-POSTUPDATE-01
kind: task
domain: VERDICT
title: "Implementar criterios ejecutables de tools.verify_usb_hid_postupdate"
status: open
severity: P2
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-10-02
close_check: {"cmd": "python3 -m pytest -q tests/test_debt_registration_controls.py::test_debt_close_check_verify_usb_hid_postupdate_01", "expect": "exit_zero", "porque": "Cada fase/id soportado evalúa su sujeto específico con capturas reales y controles negativos. Rechazar evidencia ausente, incorrecta, incompleta o controles neutralizados. Separar fail de could_not_run e imprimir ceros. No cerrar investigaciones por existencia de un informe ni por fixtures sanos. Compartir solo lógica realmente común; conservar comandos literales y demostrar discriminación entre fichas."}
---

## Registro y responsable

Registro solicitado por Luis el 2026-10-02. Responsable: coordinación de Blackbox. Trabajo o revisión pendiente; la presencia del marcador no demuestra por sí sola un defecto.

## Evidencia y alcance

Módulo ausente citado por 1 fichas. Esta ficha agrupa la implementación compartida; las investigaciones originales conservan sus ensayos y no se duplican.

- tasks/backlog/FEATURE-USB-HID-POSTUPDATE-CHECK.md

Fuentes: tasks/backlog/FEATURE-USB-HID-POSTUPDATE-CHECK.md.

## Criterio de cierre y control negativo

Cada fase/id soportado evalúa su sujeto específico con capturas reales y controles negativos. Rechazar evidencia ausente, incorrecta, incompleta o controles neutralizados. Separar fail de could_not_run e imprimir ceros. No cerrar investigaciones por existencia de un informe ni por fixtures sanos. Compartir solo lógica realmente común; conservar comandos literales y demostrar discriminación entre fichas.

## Estado del verificador

La ficha permanece abierta. El test selector del close_check es una especificación pendiente, no una prueba existente ni un resultado ejecutado. Implementarlo exige comprobar el sujeto y su control negativo; la existencia de archivos o esta ficha no basta para cerrar.

Conservar comandos, salida literal y could_not_run incluso cero; una ejecución skipped o inaccesible deja el cierre pendiente. Reutilizar instrumentos nativos y pruebas existentes antes de crear código.


## Avance de instrumentación 2026-10-03

`tools.host_diagnostics` ahora relaciona entradas HID con el USB ancestro más cercano y conserva estados `could_not_run`; la captura disponible no observó entradas HID. El avance y la limitación están documentados en [BB-INSTRUMENTS-devices](../../docs/evidence/BB-INSTRUMENTS-devices.md). La ficha sigue abierta y el close_check original permanece pendiente.
