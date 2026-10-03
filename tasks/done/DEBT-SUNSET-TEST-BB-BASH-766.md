---
id: DEBT-SUNSET-TEST-BB-BASH-766
kind: task
domain: VERDICT
title: "Revisar sunset en test_bb_bash.py:766"
status: done
severity: P2
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-10-02
close_check: {"cmd": "python3 -m pytest -q tests/test_debt_registration_controls.py::test_debt_sunset_test_bb_bash_766", "expect": "exit_zero", "porque": "Revalidar la justificación y el alcance exacto de la excepción sunset antes de su vencimiento, con comando literal y control negativo. Si es pausa de arnés/sampler, medir timeout/bounded scope/cancelación; si es test, conservar sensibilidad al delta observado. Retirar la excepción innecesaria o registrar revisión válida con responsable y expiración concreta, sin suspensión permanente."}
closed_at: 2026-10-03
closure_type: fixed
reason: "Se retiró la espera fija de 4 s: la variante sin espera pasó la aserción funcional con las dos muestras reales y el proceso hijo medido. Las dos invocaciones de sample ya proporcionan observaciones separadas suficientes en el entorno actual."
evidence: {"pass":"tasks/evidence/DEBT-SUNSET-TEST-BB-BASH-766/pass.txt","fail":"tasks/evidence/DEBT-SUNSET-TEST-BB-BASH-766/fail.txt","e2e":"tasks/evidence/DEBT-SUNSET-TEST-BB-BASH-766/e2e.txt"}
---

## Registro y responsable

Registro solicitado por Luis el 2026-10-02. Responsable: coordinación de Blackbox. Trabajo o revisión pendiente; la presencia del marcador no demuestra por sí sola un defecto.

## Evidencia y alcance

Sitio: `tests/test_bb_bash.py:766`; función/contexto: test_bb_bash.

```text
time.sleep(4)  # blocking-sleep: `ps -o times=` da segundos ENTEROS; hacen falta varios para que el delta sea legible -- DEBT-ACCEPTED-SLEEP-TESTS-BB  # sunset-reviewed: 2.1 -- relectura 2026-10-02: objetivo y expresion sin cambios frente a git show 7049dce^:tests/test_bb_bash.py; Las razones de delta entero y sondeo con deadline que siguen conservan su sujeto. Comparacion por linea en tasks/evidence/RELEASE-2.1.0/sunset-review.json. Revision anterior 2.0: sin cambios desde la revision de 1.9 horas antes, mismo dia, mismas evidencias -- SE QUEDA, y su justificacion MEJORO desde 1.8. Entonces se anoto que el test PASABA sin este sleep y que por eso la afirmacion de 1.7 era falsa; en 1.9 FALLA (1 failed in 1.59s). El disparador que 1.8 dejo escrito -- que `bb sample` bajara de 0.5 s -- se midio y NO se cumple: mediana 1.21 s en 6 corridas frente a 0.75 en 1.8, o sea que se ALEJO. Evidencia: tasks/evidence/DEBT-ACCEPTED-SLEEP-TESTS-BB/sunset-1.9-sleeps.txt
```

Clasificación: revisión de una exclusión/captura, no bug demostrado. No retirar automáticamente una protección o cleanup.

Fuentes: tests/test_bb_bash.py:766.

## Criterio de cierre y control negativo

Revalidar la justificación y el alcance exacto de la excepción sunset antes de su vencimiento, con comando literal y control negativo. Si es pausa de arnés/sampler, medir timeout/bounded scope/cancelación; si es test, conservar sensibilidad al delta observado. Retirar la excepción innecesaria o registrar revisión válida con responsable y expiración concreta, sin suspensión permanente.

## Root Cause

La ficha registraba una exclusión/sunset pendiente de revalidación. Se inspeccionó el sitio exacto y se contrastó la razón de la excepción con el control que la sostiene.

## Regression Test

`python3 -m pytest -q tests/test_debt_registration_controls.py::test_debt_sunset_test_bb_bash_766`

Control negativo incluido en el selector: Se retiró la espera fija de 4 s: la variante sin espera pasó la aserción funcional con las dos muestras reales y el proceso hijo medido. Las dos invocaciones de sample ya proporcionan observaciones separadas suficientes en el entorno actual.

## Verification Evidence

Pass: selector `DEBT-SUNSET-TEST-BB-BASH-766` pasa junto con los 13 selectores de esta ola; resultado `14 passed`, `could_not_run=0`. Fail previo: selector ausente, pytest exit 4; registrado solo como estado anterior de la instrumentación. El detalle y el alcance del control negativo constan en `tasks/evidence/DEBT-SUNSET-TEST-BB-BASH-766/e2e.txt`.
