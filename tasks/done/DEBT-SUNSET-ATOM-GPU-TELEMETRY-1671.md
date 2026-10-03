---
id: DEBT-SUNSET-ATOM-GPU-TELEMETRY-1671
kind: task
domain: VERDICT
title: "Revisar sunset en atom_gpu_telemetry.py:1671"
status: done
severity: P2
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-10-02
close_check: {"cmd": "python3 -m pytest -q tests/test_debt_registration_controls.py::test_debt_sunset_atom_gpu_telemetry_1671", "expect": "exit_zero", "porque": "Revalidar la justificación y el alcance exacto de la excepción sunset antes de su vencimiento, con comando literal y control negativo. Si es pausa de arnés/sampler, medir timeout/bounded scope/cancelación; si es test, conservar sensibilidad al delta observado. Retirar la excepción innecesaria o registrar revisión válida con responsable y expiración concreta, sin suspensión permanente."}
closed_at: 2026-10-03
closure_type: void_wontfix
reason: "Se conserva el intervalo del sampler de vida larga: el loop toma muestras repetidas con el intervalo configurado y `--once` termina sin esperar. Revisión sunset 2.1; no se usó hardware."
evidence: {"pass":"tasks/evidence/DEBT-SUNSET-ATOM-GPU-TELEMETRY-1671/pass.txt","fail":"tasks/evidence/DEBT-SUNSET-ATOM-GPU-TELEMETRY-1671/fail.txt","e2e":"tasks/evidence/DEBT-SUNSET-ATOM-GPU-TELEMETRY-1671/e2e.txt"}
---

## Registro y responsable

Registro solicitado por Luis el 2026-10-02. Responsable: coordinación de Blackbox. Trabajo o revisión pendiente; la presencia del marcador no demuestra por sí sola un defecto.

## Evidencia y alcance

Sitio: `tools/atom_gpu_telemetry.py:1671`; función/contexto: atom_gpu_telemetry.

```text
time.sleep(args.interval_seconds)  # blocking-sleep: intervalo del sampler de vida larga, no I/O a esperar -- DGX-334  # sunset-reviewed: 2.1 -- relectura 2026-10-02: objetivo y expresion sin cambios frente a git show 7049dce^:tools/atom_gpu_telemetry.py; El bucle de vida larga necesita su intervalo entre muestras. Comparacion por linea en tasks/evidence/RELEASE-2.1.0/sunset-review.json. Revision anterior 2.0: sin cambios desde la revision de 1.9 horas antes, mismo dia, mismas evidencias -- SE QUEDA con la misma razon de 1.8, re-verificada: es el intervalo del bucle de un sampler de vida larga y NO esta en el camino de los tests. Comprobado 2026-09-28 sobre los 466 tests recolectados: ninguno referencia `interval_seconds`, asi que ninguno entra en ese bucle. Evidencia: tasks/evidence/DEBT-ACCEPTED-SLEEP-TESTS-BB/sunset-1.9-sleeps.txt
```

Clasificación: revisión de una exclusión/captura, no bug demostrado. No retirar automáticamente una protección o cleanup.

Fuentes: tools/atom_gpu_telemetry.py:1671.

## Criterio de cierre y control negativo

Revalidar la justificación y el alcance exacto de la excepción sunset antes de su vencimiento, con comando literal y control negativo. Si es pausa de arnés/sampler, medir timeout/bounded scope/cancelación; si es test, conservar sensibilidad al delta observado. Retirar la excepción innecesaria o registrar revisión válida con responsable y expiración concreta, sin suspensión permanente.

## Root Cause

La ficha registraba una exclusión/sunset pendiente de revalidación. Se inspeccionó el sitio exacto y se contrastó la razón de la excepción con el control que la sostiene.

## Regression Test

`python3 -m pytest -q tests/test_debt_registration_controls.py::test_debt_sunset_atom_gpu_telemetry_1671`

Control negativo incluido en el selector: Se conserva el intervalo del sampler de vida larga: el loop toma muestras repetidas con el intervalo configurado y `--once` termina sin esperar. Revisión sunset 2.1; no se usó hardware.

## Verification Evidence

Pass: selector `DEBT-SUNSET-ATOM-GPU-TELEMETRY-1671` pasa junto con los 13 selectores de esta ola; resultado `14 passed`, `could_not_run=0`. Fail previo: selector ausente, pytest exit 4; registrado solo como estado anterior de la instrumentación. El detalle y el alcance del control negativo constan en `tasks/evidence/DEBT-SUNSET-ATOM-GPU-TELEMETRY-1671/e2e.txt`.
