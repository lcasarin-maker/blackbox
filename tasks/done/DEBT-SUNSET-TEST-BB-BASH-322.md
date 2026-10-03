---
id: DEBT-SUNSET-TEST-BB-BASH-322
kind: task
domain: VERDICT
title: "Revisar sunset en test_bb_bash.py:322"
status: done
severity: P2
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-10-02
close_check: {"cmd": "python3 -m pytest -q tests/test_debt_registration_controls.py::test_debt_sunset_test_bb_bash_322", "expect": "exit_zero", "porque": "Revalidar la justificación y el alcance exacto de la excepción sunset antes de su vencimiento, con comando literal y control negativo. Si es pausa de arnés/sampler, medir timeout/bounded scope/cancelación; si es test, conservar sensibilidad al delta observado. Retirar la excepción innecesaria o registrar revisión válida con responsable y expiración concreta, sin suspensión permanente."}
closed_at: 2026-10-03
closure_type: void_wontfix
reason: "La espera de 4 s sostiene la sensibilidad del test positivo de ritmo: su variante con espera neutralizada falla en la aserción de delta; el test con tráfico separado conserva signo y orden de magnitud."
evidence: {"pass":"tasks/evidence/DEBT-SUNSET-TEST-BB-BASH-322/pass.txt","fail":"tasks/evidence/DEBT-SUNSET-TEST-BB-BASH-322/fail.txt","e2e":"tasks/evidence/DEBT-SUNSET-TEST-BB-BASH-322/e2e.txt"}
---

## Registro y responsable

Registro solicitado por Luis el 2026-10-02. Responsable: coordinación de Blackbox. Trabajo o revisión pendiente; la presencia del marcador no demuestra por sí sola un defecto.

## Evidencia y alcance

Sitio: `tests/test_bb_bash.py:322`; función/contexto: test_bb_bash.

```text
time.sleep(4)  # blocking-sleep: el ritmo es un delta y necesita dos instantes separados -- DEBT-ACCEPTED-SLEEP-TESTS-BB  # sunset-reviewed: 2.1 -- relectura 2026-10-02: objetivo y expresion sin cambios frente a git show 7049dce^:tests/test_bb_bash.py; Las razones de delta entero y sondeo con deadline que siguen conservan su sujeto. Comparacion por linea en tasks/evidence/RELEASE-2.1.0/sunset-review.json. Revision anterior 2.0: sin cambios desde la revision de 1.9 horas antes, mismo dia, mismas evidencias -- SE QUEDA, y AHORA CON PRUEBA PROPIA: sin la espera su test FALLA (1 failed in 1.64s), asi que no necesita el argumento de pareja. Evidencia: tasks/evidence/DEBT-ACCEPTED-SLEEP-TESTS-BB/sunset-1.9-sleeps.txt
```

Clasificación: revisión de una exclusión/captura, no bug demostrado. No retirar automáticamente una protección o cleanup.

Fuentes: tests/test_bb_bash.py:322.

## Criterio de cierre y control negativo

Revalidar la justificación y el alcance exacto de la excepción sunset antes de su vencimiento, con comando literal y control negativo. Si es pausa de arnés/sampler, medir timeout/bounded scope/cancelación; si es test, conservar sensibilidad al delta observado. Retirar la excepción innecesaria o registrar revisión válida con responsable y expiración concreta, sin suspensión permanente.

## Root Cause

La ficha registraba una exclusión/sunset pendiente de revalidación. Se inspeccionó el sitio exacto y se contrastó la razón de la excepción con el control que la sostiene.

## Regression Test

`python3 -m pytest -q tests/test_debt_registration_controls.py::test_debt_sunset_test_bb_bash_322`

Control negativo incluido en el selector: La espera de 4 s sostiene la sensibilidad del test positivo de ritmo: su variante con espera neutralizada falla en la aserción de delta; el test con tráfico separado conserva signo y orden de magnitud.

## Verification Evidence

Pass: selector `DEBT-SUNSET-TEST-BB-BASH-322` pasa junto con los 13 selectores de esta ola; resultado `14 passed`, `could_not_run=0`. Fail previo: selector ausente, pytest exit 4; registrado solo como estado anterior de la instrumentación. El detalle y el alcance del control negativo constan en `tasks/evidence/DEBT-SUNSET-TEST-BB-BASH-322/e2e.txt`.
