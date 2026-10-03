---
id: DEBT-SUNSET-CGROUP-REPRO-107
kind: task
domain: VERDICT
title: "Revisar sunset en cgroup_repro.py:107"
status: done
severity: P2
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-10-02
close_check: {"cmd": "python3 -m pytest -q tests/test_debt_registration_controls.py::test_debt_sunset_cgroup_repro_107", "expect": "exit_zero", "porque": "Revalidar la justificación y el alcance exacto de la excepción sunset antes de su vencimiento, con comando literal y control negativo. Si es pausa de arnés/sampler, medir timeout/bounded scope/cancelación; si es test, conservar sensibilidad al delta observado. Retirar la excepción innecesaria o registrar revisión válida con responsable y expiración concreta, sin suspensión permanente."}
closed_at: 2026-10-03
closure_type: void_wontfix
reason: "Se conserva la ventana de observación de la asignación CUDA. Prueba unitaria con interfaz CUDA mock: el evento held y after_release quedan separados por 2 s de reloj controlado; con sleep neutralizado la ventana es cero. No se ejecutó CUDA."
evidence: {"pass":"tasks/evidence/DEBT-SUNSET-CGROUP-REPRO-107/pass.txt","fail":"tasks/evidence/DEBT-SUNSET-CGROUP-REPRO-107/fail.txt","e2e":"tasks/evidence/DEBT-SUNSET-CGROUP-REPRO-107/e2e.txt"}
---

## Registro y responsable

Registro solicitado por Luis el 2026-10-02. Responsable: coordinación de Blackbox. Trabajo o revisión pendiente; la presencia del marcador no demuestra por sí sola un defecto.

## Evidencia y alcance

Sitio: `tools/cgroup_repro.py:107`; función/contexto: cgroup_repro.

```text
time.sleep(2)  # blocking-sleep: retain allocation for cgroup observation -- DEBT-ESCRITORIO-Y-ARNESES-COMPARTEN-CGROUP  # sunset-reviewed: 2.2 -- isolated bounded worker retains allocation for observation; review sampling window
```

Clasificación: revisión de una exclusión/captura, no bug demostrado. No retirar automáticamente una protección o cleanup.

Fuentes: tools/cgroup_repro.py:107.

## Criterio de cierre y control negativo

Revalidar la justificación y el alcance exacto de la excepción sunset antes de su vencimiento, con comando literal y control negativo. Si es pausa de arnés/sampler, medir timeout/bounded scope/cancelación; si es test, conservar sensibilidad al delta observado. Retirar la excepción innecesaria o registrar revisión válida con responsable y expiración concreta, sin suspensión permanente.

## Root Cause

La ficha registraba una exclusión/sunset pendiente de revalidación. Se inspeccionó el sitio exacto y se contrastó la razón de la excepción con el control que la sostiene.

## Regression Test

`python3 -m pytest -q tests/test_debt_registration_controls.py::test_debt_sunset_cgroup_repro_107`

Control negativo incluido en el selector: Se conserva la ventana de observación de la asignación CUDA. Prueba unitaria con interfaz CUDA mock: el evento held y after_release quedan separados por 2 s de reloj controlado; con sleep neutralizado la ventana es cero. No se ejecutó CUDA.

## Verification Evidence

Pass: selector `DEBT-SUNSET-CGROUP-REPRO-107` pasa junto con los 13 selectores de esta ola; resultado `14 passed`, `could_not_run=0`. Fail previo: selector ausente, pytest exit 4; registrado solo como estado anterior de la instrumentación. El detalle y el alcance del control negativo constan en `tasks/evidence/DEBT-SUNSET-CGROUP-REPRO-107/e2e.txt`.
