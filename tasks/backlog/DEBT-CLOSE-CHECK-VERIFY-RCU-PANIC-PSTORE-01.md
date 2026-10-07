---
id: DEBT-CLOSE-CHECK-VERIFY-RCU-PANIC-PSTORE-01
kind: task
domain: VERDICT
title: "Implementar criterios ejecutables de tools.verify_rcu_panic_pstore"
status: open
severity: P2
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-10-02
close_check: {"cmd": "python3 -m pytest -q tests/test_debt_registration_controls.py::test_debt_close_check_verify_rcu_panic_pstore_01", "expect": "exit_zero", "porque": "Cada fase/id soportado evalúa su sujeto específico con capturas reales y controles negativos. Rechazar evidencia ausente, incorrecta, incompleta o controles neutralizados. Separar fail de could_not_run e imprimir ceros. No cerrar investigaciones por existencia de un informe ni por fixtures sanos. Compartir solo lógica realmente común; conservar comandos literales y demostrar discriminación entre fichas."}
---

## Registro y responsable

Registro solicitado por Luis el 2026-10-02. Responsable: coordinación de Blackbox. Trabajo o revisión pendiente; la presencia del marcador no demuestra por sí sola un defecto.

## Evidencia y alcance

Módulo ausente citado por 1 fichas. Esta ficha agrupa la implementación compartida; las investigaciones originales conservan sus ensayos y no se duplican.

- tasks/backlog/FEATURE-FORUM-RCU-PANIC-PSTORE-01.md

Fuentes: tasks/backlog/FEATURE-FORUM-RCU-PANIC-PSTORE-01.md.

## Criterio de cierre y control negativo

Cada fase/id soportado evalúa su sujeto específico con capturas reales y controles negativos. Rechazar evidencia ausente, incorrecta, incompleta o controles neutralizados. Separar fail de could_not_run e imprimir ceros. No cerrar investigaciones por existencia de un informe ni por fixtures sanos. Compartir solo lógica realmente común; conservar comandos literales y demostrar discriminación entre fichas.

## Estado del verificador

La ficha permanece abierta. El test selector del close_check es una especificación pendiente, no una prueba existente ni un resultado ejecutado. Implementarlo exige comprobar el sujeto y su control negativo; la existencia de archivos o esta ficha no basta para cerrar.

Conservar comandos, salida literal y could_not_run incluso cero; una ejecución skipped o inaccesible deja el cierre pendiente. Reutilizar instrumentos nativos y pruebas existentes antes de crear código.

## Avance de ejecución 2026-10-03

Se reutilizó `tools.recovery_profile.pstore` para huellas y señales textuales y se añadieron observaciones kernel en `tools.kernel_capture`. No se lanzó panic, reboot ni ensayo RCU; el lector informa `could_not_run` de `/sys/fs/pstore` en la captura local. Configuración/sysctl y pstore vacío no demuestran captura persistente ni recuperación; el selector específico de cierre permanece pendiente.

Evidencia: `docs/evidence/BB-INSTRUMENTS-kernel.md` y `tasks/evidence/BB-INSTRUMENTS-2026-10-03/kernel-capture.json`. La ficha permanece abierta.

## Clasificación del impedimento — 2026-10-04

- Categoría principal: `privileged_access`.
- Impedimento: El verificador y el selector ya existen. El close_check original exige evidencia real de una intervención de panic/reboot con backend pstore registrado, ajuste activo y rollback exacto; no hay recovery.json y el operador no tiene acceso root concedido.
- Evidencia faltante para cierre: recovery.json con boot IDs, sysctl/cmdline/backend pstore crudos, marca de panic y captura post-reboot; sysctl original/restaurado iguales; salida systemctl show de kdump active/loaded
- Siguiente acción: Conservar UNKNOWN y el criterio abierto. Cuando exista un canary con acceso root y recuperación aprobada, el operador debe recolectar la evidencia y verificar el ciclo pstore/rollback antes de ejecutar el selector original; no inducir panic en el host actual.
- Responsable del siguiente paso: coordinación BB prepara el canary; operador Luis gestiona acceso root/lab y ejecuta el ciclo.
- Cierre completo accionable hoy: no. Preparación coordinable: sin acción adicional demostrada en esta revisión.
- Evidencias de clasificación: `tasks/backlog/DEBT-CLOSE-CHECK-VERIFY-RCU-PANIC-PSTORE-01.md`, `tools/verify_rcu_panic_pstore.py`, `tests/test_debt_registration_controls.py::test_debt_close_check_verify_rcu_panic_pstore_01`, `tasks/evidence/CLOSURE-CONTROLS-2026-10-03/FEATURE-FORUM-RCU-PANIC-PSTORE-01-direct-close-current.log`, `tasks/evidence/CLOSURE-CONTROLS-2026-10-03/pstore-root-negative.json`, `tasks/evidence/FEATURE-FORUM-RCU-PANIC-PSTORE-01/progress.txt`.
- Impedimentos de inspección: 0. El criterio original permanece intacto; esta clasificación conserva la ficha abierta.

## Avance 2026-10-07 — discriminación fail/could_not_run en rollback y kdump

- Defecto corregido en `tools/verify_rcu_panic_pstore.py::_validate_rollback`: un rollback sin `original_sysctl_text`/`restored_sysctl_text` capturados devolvía `fail` ("rollback does not restore..."), y un `systemctl show` sin `LoadState`/`ActiveState` devolvía `fail` ("kdump control failed"). Ninguno de los dos observó el sujeto; ahora ambos son `unknown` con `could_not_run=1`. Capturado y distinto sigue siendo `fail`.
- Regresión: `tests/test_closure_kernel.py::test_rcu_absent_rollback_or_kdump_state_is_could_not_run_not_fail`. Control negativo corrido: antes del fix falla (`assert ('fail' == 'unknown')` para rollback `{}`); después, `12 passed, 76 deselected` en `-k rcu`. `test_rcu_fixture_backend_and_kdump_description_do_not_pass` pasa de exigir `fail` a exigir `unknown` + `could_not_run == 1` (sigue sin pasar, ahora con la clase correcta).
- Close_check sin cambio: `1 xfailed`; con `--runxfail` el veredicto real es `status: unknown, could_not_run: 1` porque `tasks/evidence/FEATURE-FORUM-RCU-PANIC-PSTORE-01/recovery.json` no existe. El impedimento `privileged_access` de 2026-10-04 sigue vigente. La ficha permanece abierta.
