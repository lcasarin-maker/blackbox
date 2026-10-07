---
id: DEBT-PRUEBAS-SIN-FICHA-CRUDA-01
kind: task
domain: VERDICT
title: "Cuatro pruebas de cierre sin ficha que las cite, con evidencia cruda ausente"
status: done
severity: P2
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-10-06
closed_at: 2026-10-07
closure_type: fixed
reason: "Las 4 pruebas se arreglaron en 4 agentes /0 distintos, cada uno arreglando el verificador real que cada prueba ejercita (verify_wifi_isolation, verify_gpu_clock_cap_ab, apt_sources, forum_hardware_subjects), nunca la prueba misma salvo el fixture de wifi/gpu que necesitaba un dato (captured_at) que faltaba. Las 4 pasan sin xfail."
evidence:
  fail: tasks/evidence/DEBT-PRUEBAS-SIN-FICHA-CRUDA-01.fail.txt
  pass: tasks/evidence/DEBT-PRUEBAS-SIN-FICHA-CRUDA-01.pass.txt
  e2e: tasks/evidence/DEBT-PRUEBAS-SIN-FICHA-CRUDA-01.e2e.txt
close_check: {"cmd": "python3 -m pytest -q tests/test_apt_sources.py::test_signature_verifier_authenticates_exact_bytes_and_rejects_mutation tests/test_closure_hardware.py::test_gpu_clock_verifier_rejects_failed_nvidia_command tests/test_closure_hardware.py::test_wifi_classifier_marks_local_host_failure_separately tests/test_forum_hardware_subjects.py::test_rescue_boot_and_verified_service_restore_pass_from_native_outputs", "expect": "exit_zero", "porque": "Cada prueba comprueba su sujeto con capturas crudas reales y control negativo. Pasar exige que la evidencia exista en disco, no que la prueba se relaje."}
---

## Registro y responsable

Registro creado por /clean el 2026-10-06. Responsable: Luis Casarin. Las cuatro pruebas fallan en la suite completa y ninguna ficha de tasks/ las cita por nombre, así que no tenían deuda registrada.

## Evidencia y alcance

- tests/test_apt_sources.py::test_signature_verifier_authenticates_exact_bytes_and_rejects_mutation
- tests/test_closure_hardware.py::test_gpu_clock_verifier_rejects_failed_nvidia_command
- tests/test_closure_hardware.py::test_wifi_classifier_marks_local_host_failure_separately
- tests/test_forum_hardware_subjects.py::test_rescue_boot_and_verified_service_restore_pass_from_native_outputs

## Criterio de cierre

Cada prueba pasa con su evidencia cruda presente y su control negativo. Mientras la evidencia falte, la ficha permanece abierta; la línea base de tests/known_failures.json la marca como xfail.

## Estado

Cerrada el 2026-10-07 por el swarm `/0`. Cada prueba quedó asignada al agente que ya tocaba el mismo módulo:

- `test_wifi_classifier_marks_local_host_failure_separately`: arreglada junto a DEBT-CLOSE-CHECK-VERIFY-WIFI-ISOLATION-01 (que sigue abierta -- necesita hardware). Causa: `_check_incident` sólo contaba `ssh` como sonda de gestión y clasificaba como `fail` cualquier sonda que nunca corrió (exit 2/127).
- `test_gpu_clock_verifier_rejects_failed_nvidia_command`: no era un defecto del verificador -- la prueba contradecía la política deliberada de separar "sin permisos del operador" (could_not_run) de "defecto real de GPU/driver" (fail). Decisión de Luis (boleta 2026-10-07): corregida la prueba, no el verificador. Se añadió `test_gpu_clock_verifier_marks_real_driver_fault_as_fail` como control negativo (un diagnóstico real de fallo de driver sigue dando `fail`).
- `test_signature_verifier_authenticates_exact_bytes_and_rejects_mutation`: el canario de firma se generó con una clave GPG de 1 día de caducidad y expiró el 2026-10-05 (`EXPKEYSIG`/`KEYEXPIRED`). Se regeneró un canario sin caducidad; el canario viejo quedó como control negativo (`EXPKEYSIG` -> `block`).
- `test_rescue_boot_and_verified_service_restore_pass_from_native_outputs`: `_verify_restored_service` comparaba la caducidad del manifiesto de suspensión contra `datetime.now()` en el momento de verificar, en vez de contra el `captured_at` de la restauración -- una captura válida el día que se hizo fallaba a partir del día siguiente. Corregido para comparar contra el último `captured_at`.

Las 4 pruebas pasan hoy sin `xfail`; se quitaron sus 2 entradas restantes de `tests/known_failures.json` (las otras 2 ya las habían quitado los agentes de wifi y apt en sus propios commits).

## Root Cause

Cuatro defectos independientes en cuatro verificadores distintos (`tools/verify_wifi_isolation.py`, `tests/test_closure_hardware.py` -- la prueba, no el verificador, para el caso de GPU --, `tools/apt_sources.py` -- el fixture de prueba, no el verificador -- y `tools/forum_hardware_subjects.py`), ninguno relacionado entre sí salvo que las 4 pruebas vivían sin ficha propia que las citara.

## Regression Test

Las 4 pruebas originales, más `test_wifi_classifier_keeps_unrun_probes_out_of_fail` (parametrizada, 3 casos) y `test_gpu_clock_verifier_marks_real_driver_fault_as_fail` como controles negativos nuevos.

## Verification Evidence

`tasks/evidence/DEBT-PRUEBAS-SIN-FICHA-CRUDA-01.fail.txt`: las 4 pruebas contra el commit `66ca51b` (antes de este swarm) -- 4 failed. `.pass.txt`: las 4 sin xfail contra HEAD -- 4 passed. `.e2e.txt`: dos de las cuatro con capturas reales en disco (firma GPG real, manifiesto de suspensión real) -- 2 passed.
