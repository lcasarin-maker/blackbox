---
id: DEBT-CLOSE-CHECK-VERIFY-FORUM-FINDING-01
kind: task
domain: VERDICT
title: "Implementar criterios ejecutables de tools.verify_forum_finding"
status: done
closed_at: 2026-10-14
closure_type: duplicate
reason: "Duplicada de su(s) ficha(s) sujeto FORUM-00-CX7-HOTPLUG-FAN-PROTECTION, FEATURE-FORUM-PROVIDER-FALLBACK-REGRESSION-01, FEATURE-FORUM-SBSA-WATCHDOG-STATE-01, FORUM-REALTEK-DRIVER-BINDING-01, FEATURE-FORUM-GB10-RUNTIME-COMPAT-01, FEATURE-FORUM-DESKTOP-SESSION-POSTUPDATE-01, FORUM-00-KERNEL-INITRD-UPDATE-GATE, FORUM-00-DGX-OTA-DRM-COMPAT-PREFLIGHT, FEATURE-FORUM-RESCUE-RUNBOOK-01, FORUM-02-PSTORE-KERNEL-REGRESSION, FORUM-00-GB10-THERMAL-RESIDENCY-ADMISSION, FEATURE-FORUM-GPU-GSP-BOOT-HEALTH-01, FORUM-02-USB-UVC-EP0: pedia implementar los criterios ejecutables de tools.verify_forum_finding, que ya existe y es el close_check de esas fichas; su propio close_check era un xfail de relleno. Decision de Luis 2026-10-14: consolidar; la medicion la lleva la ficha sujeto."
evidence: {"pass": "tasks/evidence/DEBT-CLOSE-CHECK-VERIFY-FORUM-FINDING-01/pass.txt", "fail": "tasks/evidence/DEBT-CLOSE-CHECK-VERIFY-FORUM-FINDING-01/fail.txt", "e2e": "tasks/evidence/DEBT-CLOSE-CHECK-VERIFY-FORUM-FINDING-01/e2e.txt"}
severity: P2
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-10-02
close_check: {"cmd": "python -m tools.check_harvest_accepted tasks/done/DEBT-CLOSE-CHECK-VERIFY-FORUM-FINDING-01.md", "expect": "exit_zero", "porque": "Cerrada como duplicate (decision de Luis 2026-10-14: consolidar en la ficha sujeto): no hay fix propio que probar, lo verificable por maquina es que la decision quedo registrada (closure_type y reason). El close_check anterior era `python3 -m pytest -q tests/test_debt_registration_controls.py::test_debt_close_check_verify_forum_finding_01`, un xfail de relleno que se retira con el cierre; los criterios ejecutables los mide el close_check de la ficha sujeto."}
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

## Re-ejecución y corrección de predicado — 2026-10-07

- Selector re-ejecutado sin máscara (`--runxfail`) sobre los 33 IDs (`SUPPORTED` ∪ batch02 `IDS` ∪ batch03 `CARD_IDS`): 0 PASS, 0 FAIL, 33 UNKNOWN, 44 could_not_run. Mismos conteos que el recibo del 2026-10-03.
- Defecto de evaluador encontrado y corregido (`FEATURE-FORUM-RESCUE-RUNBOOK-01`): `_verify_restored_service` comparaba la caducidad del manifiesto de suspensión contra `datetime.now()` del verificador, así que la misma evidencia pasaba antes del 2026-10-04 y fallaba después. Ahora compara contra el último `captured_at` de las filas `restoration`. Prueba de regresión con control negativo: `tests/test_forum_hardware_subjects.py::test_rescue_boot_and_verified_service_restore_pass_from_native_outputs` (caducidad anterior a la restauración ⇒ `fail`). Contra el verificador previo esa prueba sale rc=1; con el arreglo, rc=0.
- RESCUE-RUNBOOK tampoco tiene captura real (sólo `host-observation.txt`); el arreglo corrige el predicado, no su evidencia.
- Los 32 IDs restantes no tienen defecto de evaluador: 24 no tienen captura cruda (15 directorios vacíos, 9 con sólo `host-observation.txt`/`progress.txt`/`owner-query.json`) en `tasks/evidence/<id>/`; APT-ARM64 tiene un sondeo de 6 comandos, no el bundle schema 1; DGX-OTA y KERNEL-INITRD tienen las observaciones en `null` (sysfs denegado, lock de dpkg); GB10-RUNTIME, GPU-GSP y PROVIDER-FALLBACK declaran `closure: open` con bloqueadores en su propia evidencia; OTA-DRIVER-KERNEL y THERMAL-TELEMETRY sólo tienen resúmenes/prototipos.
- La ficha sigue abierta: el cierre exige capturas físicas por ID (arranque de rescate, hotplug CX7, actualización de firmware, reinicio de energía, soaks térmicos), y el código no las produce.

## Estado (2026-10-11, /0 + /vote)

Bloqueada por criterio sin implementar: el `close_check` de esta ficha termina en `xfailed` y por eso sale con codigo 0 sin que el criterio real exista. Un `xfail` no es una verificacion y cerrar con el no es cierre. Cerrarla exige implementar la prueba real contra el sujeto (vLLM, NCCL, CX7 u otro hardware) con su control negativo. Decision del dueno el 2026-10-11: dejarla abierta y declarada, no cerrarla como `void_wontfix`.

## Root Cause
Meta-ficha sin sujeto propio: pedia implementar los criterios ejecutables de `tools.verify_forum_finding`. El verificador existe (`tools/verify_forum_finding.py`) y es el close_check de `FORUM-00-CX7-HOTPLUG-FAN-PROTECTION`, `FEATURE-FORUM-PROVIDER-FALLBACK-REGRESSION-01`, `FEATURE-FORUM-SBSA-WATCHDOG-STATE-01`, `FORUM-REALTEK-DRIVER-BINDING-01`, `FEATURE-FORUM-GB10-RUNTIME-COMPAT-01`, `FEATURE-FORUM-DESKTOP-SESSION-POSTUPDATE-01`, `FORUM-00-KERNEL-INITRD-UPDATE-GATE`, `FORUM-00-DGX-OTA-DRM-COMPAT-PREFLIGHT`, `FEATURE-FORUM-RESCUE-RUNBOOK-01`, `FORUM-02-PSTORE-KERNEL-REGRESSION`, `FORUM-00-GB10-THERMAL-RESIDENCY-ADMISSION`, `FEATURE-FORUM-GPU-GSP-BOOT-HEALTH-01`, `FORUM-02-USB-UVC-EP0`; hoy sale con rc=2 (could_not_run) porque falta la captura real del sujeto, que es el trabajo de esas fichas, no de esta. Su propio close_check era un selector xfail que no podia cerrar nada. El test retirado agregaba ademas los ids de `tools.hardware_batch02_controls.IDS` y `tools.hardware_batch03_controls.CARD_IDS`, que tienen su propio close_check y su propio test.

## Regression Test
Ninguno propio: la ficha se cierra como duplicada. Se retira `tests/test_debt_registration_controls.py::test_debt_close_check_verify_forum_finding_01` y `tests/test_closure_hardware.py::test_debt_close_check_verify_forum_finding_01`, xfail de relleno, junto con sus entradas de `tests/known_failures.json`; las pruebas unitarias de `tools.verify_forum_finding` siguen corriendo.

## Verification Evidence
Tres rutas del frontmatter: `fail` (control negativo: el close_check de cada ficha sujeto sale hoy con rc distinto de 0, el verificador sabe decir que no), `pass` (el verificador existe, cada ficha sujeto lo nombra y sus pruebas unitarias pasan: control positivo) y `e2e` (la decision registrada). Cada ficha sujeto lleva una nota que dice que los criterios de `tools.verify_forum_finding` se miden alli. Para reabrirla: `git mv tasks/done/DEBT-CLOSE-CHECK-VERIFY-FORUM-FINDING-01.md tasks/backlog/` y `status: open`.
