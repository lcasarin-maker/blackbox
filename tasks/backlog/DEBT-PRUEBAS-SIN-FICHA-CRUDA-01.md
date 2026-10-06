---
id: DEBT-PRUEBAS-SIN-FICHA-CRUDA-01
kind: task
domain: VERDICT
title: "Cuatro pruebas de cierre sin ficha que las cite, con evidencia cruda ausente"
status: open
severity: P2
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-10-06
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

Abierta. Pendiente de identificar la ficha de origen de cada prueba o de registrarla.
