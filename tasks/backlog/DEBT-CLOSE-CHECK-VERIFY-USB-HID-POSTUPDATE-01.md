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

## Corrección del evaluador — 2026-10-07 (la ficha sigue abierta)

Defectos reales de `tools/verify_usb_hid_postupdate.py`, medidos sobre una captura real de este host (`tasks/evidence/DEBT-CLOSE-CHECK-VERIFY-USB-HID-POSTUPDATE-01/host-capture-2026-10-07.json`, sha256 `cd970aff8334d2739c4858bbd292c3cd34da2132de0f47ad784762db4fcf75fe`; un solo arranque sano, headless, HID modular, sin dispositivo HID; no es captura de cierre):

1. Caía con `ValueError: too many values to unpack` en toda captura incompleta (`boot, detail = _boot_observations(...)` desempaquetaba el dict de `_result`): el instrumento reventaba en vez de reportar `could_not_run`.
2. Exigía el símbolo inexistente `CONFIG_USB_HID_GENERIC` (`grep -c CONFIG_USB_HID_GENERIC /boot/config-6.17.0-1032-nvidia` → `0`, exit 1); el símbolo real es `CONFIG_HID_GENERIC`. Un kernel con HID integrado nunca se reconocía y la recuperación se declaraba `fail`.
3. Aceptaba cualquier `/boot/config-*` (este host tiene tres) sin atarlo al `uname -r` de la fase, y rechazaba la lectura real `grep -E ... /boot/config-<kernel>`. Ahora sólo cuenta la config del kernel en ejecución de esa fase y exige que nombre `CONFIG_HID`, `CONFIG_USB_HID` y `CONFIG_HID_GENERIC`; si no, `could_not_run`.
4. El atajo sin fases declaraba «HID sin enlazar» desde `lsmod`, ciego al `usbhid` integrado: una interfaz `Driver=usbhid` daba `fail`. Ahora lee el enlace en la propia interfaz de `lsusb -t` (`Driver=[none]`).
5. El arranque afectado con interfaz HID enlazada podía dar `pass`; ahora es `fail` (pérdida no reproducida), y sin interfaz `[none]` observada queda `could_not_run`.
6. Recuperación con módulos ausentes y config integrada ilegible daba `fail`; ahora `could_not_run` (integrado vs. telemetría inaccesible). Modular sin módulos sigue en `fail`.

Pruebas nuevas en `tests/test_closure_hardware.py` (`-k usb_hid`), construidas sobre la captura real con mutaciones rotuladas.
- Control negativo: con el código anterior (`git show HEAD:tools/verify_usb_hid_postupdate.py`), `python3 -m pytest -q tests/test_closure_hardware.py -k usb_hid` → `6 failed, 3 passed, 19 deselected, 1 xfailed` (rc=1).
- Con la corrección → `9 passed, 19 deselected, 1 xfailed`.

Por qué sigue abierta: `python3 -m pytest -q --runxfail tests/test_debt_registration_controls.py::test_debt_close_check_verify_usb_hid_postupdate_01` → `1 failed`, `status=unknown, fail=0, could_not_run=1`, «paired raw post-update USB command capture is missing». Sin `--runxfail` sale 0 sólo por la línea base xfail. El cierre exige una captura real de tres arranques en hardware (pre-update sano con evtest+SSH, arranque afectado con interfaz HID `Driver=[none]` y DPKG/journal correlacionados, y recuperación al kernel previo con evtest+SSH), que no puede producirse desde software. El escenario de tres arranques en las pruebas es una mezcla de filas reales re-rotuladas y sondas sintéticas: prueba la discriminación y no cuenta como evidencia de cierre.
