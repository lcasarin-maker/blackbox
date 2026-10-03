---
id: DEBT-SUNSET-TEST-BB-BASH-802
kind: task
domain: VERDICT
title: "Revisar sunset en test_bb_bash.py:802"
status: done
severity: P2
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-10-02
close_check: {"cmd": "python3 -m pytest -q tests/test_debt_registration_controls.py::test_debt_sunset_test_bb_bash_802", "expect": "exit_zero", "porque": "Revalidar la justificación y el alcance exacto de la excepción sunset antes de su vencimiento, con comando literal y control negativo. Si es pausa de arnés/sampler, medir timeout/bounded scope/cancelación; si es test, conservar sensibilidad al delta observado. Retirar la excepción innecesaria o registrar revisión válida con responsable y expiración concreta, sin suspensión permanente."}
closed_at: 2026-10-03
closure_type: fixed
reason: "Se retiró la espera fija de 4 s: el negativo de proceso dormido pasó sin ella y el positivo emparejado también pasó sin su espera en la medición actual; ambos conservan dos muestras reales y sus aserciones de atribución."
evidence: {"pass":"tasks/evidence/DEBT-SUNSET-TEST-BB-BASH-802/pass.txt","fail":"tasks/evidence/DEBT-SUNSET-TEST-BB-BASH-802/fail.txt","e2e":"tasks/evidence/DEBT-SUNSET-TEST-BB-BASH-802/e2e.txt"}
---

## Registro y responsable

Registro solicitado por Luis el 2026-10-02. Responsable: coordinación de Blackbox. Trabajo o revisión pendiente; la presencia del marcador no demuestra por sí sola un defecto.

## Evidencia y alcance

Sitio: `tests/test_bb_bash.py:802`; función/contexto: test_bb_bash.

```text
time.sleep(4)  # blocking-sleep: mismo intervalo que el caso positivo, para que la comparacion valga -- DEBT-ACCEPTED-SLEEP-TESTS-BB  # sunset-reviewed: 2.1 -- relectura 2026-10-02: objetivo y expresion sin cambios frente a git show 7049dce^:tests/test_bb_bash.py; Las razones de delta entero y sondeo con deadline que siguen conservan su sujeto. Comparacion por linea en tasks/evidence/RELEASE-2.1.0/sunset-review.json. Revision anterior 2.0: sin cambios desde la revision de 1.9 horas antes, mismo dia, mismas evidencias -- SE QUEDA, y su base MEJORO: es CONTROL NEGATIVO y su prueba es que su positivo emparejado (linea 679) falle sin la suya. En 1.8 ese positivo NO fallaba y esta exencion heredaba su debilidad; en 1.9 SI falla. Evidencia: tasks/evidence/DEBT-ACCEPTED-SLEEP-TESTS-BB/sunset-1.9-sleeps.txt
```

Clasificación: revisión de una exclusión/captura, no bug demostrado. No retirar automáticamente una protección o cleanup.

Fuentes: tests/test_bb_bash.py:802.

## Criterio de cierre y control negativo

Revalidar la justificación y el alcance exacto de la excepción sunset antes de su vencimiento, con comando literal y control negativo. Si es pausa de arnés/sampler, medir timeout/bounded scope/cancelación; si es test, conservar sensibilidad al delta observado. Retirar la excepción innecesaria o registrar revisión válida con responsable y expiración concreta, sin suspensión permanente.

## Root Cause

La ficha registraba una exclusión/sunset pendiente de revalidación. Se inspeccionó el sitio exacto y se contrastó la razón de la excepción con el control que la sostiene.

## Regression Test

`python3 -m pytest -q tests/test_debt_registration_controls.py::test_debt_sunset_test_bb_bash_802`

Control negativo incluido en el selector: Se retiró la espera fija de 4 s: el negativo de proceso dormido pasó sin ella y el positivo emparejado también pasó sin su espera en la medición actual; ambos conservan dos muestras reales y sus aserciones de atribución.

## Verification Evidence

Pass: selector `DEBT-SUNSET-TEST-BB-BASH-802` pasa junto con los 13 selectores de esta ola; resultado `14 passed`, `could_not_run=0`. Fail previo: selector ausente, pytest exit 4; registrado solo como estado anterior de la instrumentación. El detalle y el alcance del control negativo constan en `tasks/evidence/DEBT-SUNSET-TEST-BB-BASH-802/e2e.txt`.
