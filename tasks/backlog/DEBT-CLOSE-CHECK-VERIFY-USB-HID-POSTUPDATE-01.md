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

Registro inicial: módulo ausente citado por 1 fichas. El módulo y el selector original ya están disponibles. Esta ficha agrupa la implementación compartida; las investigaciones originales conservan sus ensayos y no se duplican.

- tasks/backlog/FEATURE-USB-HID-POSTUPDATE-CHECK.md

Fuentes: tasks/backlog/FEATURE-USB-HID-POSTUPDATE-CHECK.md.

## Criterio de cierre y control negativo

Cada fase/id soportado evalúa su sujeto específico con capturas reales y controles negativos. Rechazar evidencia ausente, incorrecta, incompleta o controles neutralizados. Separar fail de could_not_run e imprimir ceros. No cerrar investigaciones por existencia de un informe ni por fixtures sanos. Compartir solo lógica realmente común; conservar comandos literales y demostrar discriminación entre fichas.

## Estado del verificador

La ficha permanece abierta. El selector original ya ejecuta el evaluador sobre la captura de su sujeto: status=unknown, fail=0, could_not_run=1. Motivo: paired raw post-update USB command capture is missing. Recibo: tasks/evidence/CLOSURE-CONTROLS-2026-10-03/three-hardware-original-selectors-primary-run.json. La cobertura del paquete permanece parcial; la investigación requiere evidencia real.

Conservar comandos, salida literal y could_not_run incluso cero; una ejecución skipped o inaccesible deja el cierre pendiente. Reutilizar instrumentos nativos y pruebas existentes antes de crear código.


## Avance de instrumentación 2026-10-03

`tools.host_diagnostics` ahora relaciona entradas HID con el USB ancestro más cercano y conserva estados `could_not_run`; la captura disponible no observó entradas HID. El avance y la limitación están documentados en [BB-INSTRUMENTS-devices](../../docs/evidence/BB-INSTRUMENTS-devices.md). La ficha sigue abierta y el close_check original permanece pendiente.

## Clasificación del impedimento — 2026-10-04

- Categoría principal: `hardware_or_peer`.
- Impedimento: Selector original reportó unknown/fail=0/CNR=1 porque falta captura raw pareada de comandos USB post-update; herramienta hostdiag no observó entradas HID.
- Evidencia faltante para cierre: Selector original reportó unknown/fail=0/CNR=1 porque falta captura raw pareada de comandos USB post-update; herramienta hostdiag no observó entradas HID.
- Siguiente acción: Coordinación BB: completar contrato de parser/selector con fixtures; operador Luis: proporcionar captura pareada de HID/USB antes y después de actualizar firmware en dispositivo real. Ref explícita: tasks/backlog/DEBT-CLOSE-CHECK-VERIFY-USB-HID-POSTUPDATE-01.md y tests/test_debt_registration_controls.py. Ref explícita: tasks/backlog/DEBT-CLOSE-CHECK-VERIFY-USB-HID-POSTUPDATE-01.md y tasks/evidence/CLOSURE-CONTROLS-2026-10-03/DEBT-CLOSE-CHECK-VERIFY-USB-HID-POSTUPDATE-01-current-selector.log.
- Responsable del siguiente paso: Coordinación BB prepara/implementa; cuando la acción requiere root/lab/hardware, operador Luis aporta y ejecuta el sujeto indicado..
- Cierre completo accionable hoy: no. Preparación coordinable: sí.
- Evidencias de clasificación: `tasks/backlog/DEBT-CLOSE-CHECK-VERIFY-USB-HID-POSTUPDATE-01.md`, `tasks/evidence/CLOSURE-CONTROLS-2026-10-03/three-hardware-original-selectors-primary-run.json`, `docs/evidence/BB-INSTRUMENTS-devices.md`, `tests/test_debt_registration_controls.py`, `tasks/evidence/OPEN-96-CLASSIFICATION-2026-10-04/batches/batch_06.json`, `tasks/evidence/CLOSURE-CONTROLS-2026-10-03/DEBT-CLOSE-CHECK-VERIFY-USB-HID-POSTUPDATE-01-current-selector.log`.
- Impedimentos de inspección: 0. El criterio original permanece intacto; esta clasificación conserva la ficha abierta.
