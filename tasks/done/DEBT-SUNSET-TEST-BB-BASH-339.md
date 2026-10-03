---
id: DEBT-SUNSET-TEST-BB-BASH-339
kind: task
domain: VERDICT
title: "Revisar sunset en test_bb_bash.py:339"
status: done
severity: P2
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-10-02
close_check: {"cmd": "python3 -m pytest -q tests/test_debt_registration_controls.py::test_debt_sunset_test_bb_bash_339", "expect": "exit_zero", "porque": "Revalidar la justificación y el alcance exacto de la excepción sunset antes de su vencimiento, con comando literal y control negativo. Si es pausa de arnés/sampler, medir timeout/bounded scope/cancelación; si es test, conservar sensibilidad al delta observado. Retirar la excepción innecesaria o registrar revisión válida con responsable y expiración concreta, sin suspensión permanente."}
closed_at: 2026-10-03
closure_type: fixed
reason: "El negativo comparte la misma ventana determinista de 4 s que el positivo, por lo que cero proviene de contadores iguales con dt positivo y no de la rama que omite el cálculo. Se eliminó el wait fijo."
evidence: {"pass":"tasks/evidence/DEBT-SUNSET-TEST-BB-BASH-339/pass.txt","fail":"tasks/evidence/DEBT-SUNSET-TEST-BB-BASH-339/fail.txt","e2e":"tasks/evidence/DEBT-SUNSET-TEST-BB-BASH-339/e2e.txt"}
---

## Registro y responsable

Registro solicitado por Luis el 2026-10-02. Responsable de revisión: coordinación de Blackbox. La excepción fue revisada y cerrada el 2026-10-03.

## Evidencia y alcance

Sitio: `tests/test_bb_bash.py:339`; función/contexto: test_bb_bash.

```text
time.sleep(2)  # blocking-sleep: dos muestras separadas, mismos contadores -- DEBT-ACCEPTED-SLEEP-TESTS-BB  # sunset-reviewed: 2.1 -- relectura 2026-10-02: objetivo y expresion sin cambios frente a git show 7049dce^:tests/test_bb_bash.py; Las razones de delta entero y sondeo con deadline que siguen conservan su sujeto. Comparacion por linea en tasks/evidence/RELEASE-2.1.0/sunset-review.json. Revision anterior 2.0: sin cambios desde la revision de 1.9 horas antes, mismo dia, mismas evidencias -- SE QUEDA: CONTROL NEGATIVO cuya prueba es que su POSITIVO emparejado falle sin la suya -- y la linea 312 FALLA. Sostenida por pareja, medido 2026-09-28. Evidencia: tasks/evidence/DEBT-ACCEPTED-SLEEP-TESTS-BB/sunset-1.9-sleeps.txt
```

Revisión de 2026-10-03: el control negativo usa la misma ventana determinista de 4 s que su positivo. Los contadores iguales pasan por el cálculo con dt positivo; se retiró el wait fijo.

Fuentes: tests/test_bb_bash.py:339.

## Criterio de cierre y control negativo

Revalidar la justificación y el alcance exacto de la excepción sunset antes de su vencimiento, con comando literal y control negativo. Si es pausa de arnés/sampler, medir timeout/bounded scope/cancelación; si es test, conservar sensibilidad al delta observado. Retirar la excepción innecesaria o registrar revisión válida con responsable y expiración concreta, sin suspensión permanente.

## Root Cause

La ficha registraba una exclusión/sunset pendiente de revalidación. Se inspeccionó el sitio exacto y se contrastó la razón de la excepción con el control que la sostiene.

## Regression Test

`python3 -m pytest -q tests/test_debt_registration_controls.py::test_debt_sunset_test_bb_bash_339`

Control negativo incluido en el selector: El control negativo y su positivo usan el reloj temporal de 4 s; los contadores iguales producen tasa cero y el positivo conserva la tasa esperada.

## Verification Evidence

El control con mismos contadores pasa con delta positivo de 4 s y emite 0.0; su test positivo emparejado rechaza la mutación que quita la división por dt. Tres selectores corregidos pasan en 64.51 s. `could_not_run=0`. Evidencia por comando y control negativo: `tasks/evidence/DEBT-SUNSET-TEST-BB-BASH-339/e2e.txt`.
