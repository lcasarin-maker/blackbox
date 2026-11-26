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
closure_type: fixed
reason: "Ritmo positivo y controles de swap ahora usan un reloj `date` temporal con delta determinista de 4 s. `bin/bb sample` sigue siendo el sujeto; 4000/4=1000 y 400/4=100 páginas/s. Se eliminó el wait fijo."
evidence: {"pass":"tasks/evidence/DEBT-SUNSET-TEST-BB-BASH-322/pass.txt","fail":"tasks/evidence/DEBT-SUNSET-TEST-BB-BASH-322/fail.txt","e2e":"tasks/evidence/DEBT-SUNSET-TEST-BB-BASH-322/e2e.txt"}
---

## Registro y responsable

Registro solicitado por Luis el 2026-10-02. Responsable de revisión: coordinación de Blackbox. La excepción fue revisada y cerrada el 2026-10-03.

## Evidencia y alcance

Sitio: `tests/test_bb_bash.py:322`; función/contexto: test_bb_bash.

```text
time.sleep(4)  # blocking-sleep: el ritmo es un delta y necesita dos instantes separados -- DEBT-ACCEPTED-SLEEP-TESTS-BB  # sunset-reviewed: 2.1 -- relectura 2026-10-02: objetivo y expresion sin cambios frente a git show 7049dce^:tests/test_bb_bash.py; Las razones de delta entero y sondeo con deadline que siguen conservan su sujeto. Comparacion por linea en tasks/evidence/RELEASE-2.1.0/sunset-review.json. Revision anterior 2.0: sin cambios desde la revision de 1.9 horas antes, mismo dia, mismas evidencias -- SE QUEDA, y AHORA CON PRUEBA PROPIA: sin la espera su test FALLA (1 failed in 1.64s), asi que no necesita el argumento de pareja. Evidencia: tasks/evidence/DEBT-ACCEPTED-SLEEP-TESTS-BB/sunset-1.9-sleeps.txt
```

Revisión de 2026-10-03: el delta fijo se conserva, pero el tiempo real no es necesario; se reemplazó por un `date` temporal de 4 s. Un `bin/bb` temporal sin dividir el delta falla el control positivo.

Fuentes: tests/test_bb_bash.py:322.

## Criterio de cierre y control negativo

Revalidar la justificación y el alcance exacto de la excepción sunset antes de su vencimiento, con comando literal y control negativo. Si es pausa de arnés/sampler, medir timeout/bounded scope/cancelación; si es test, conservar sensibilidad al delta observado. Retirar la excepción innecesaria o registrar revisión válida con responsable y expiración concreta, sin suspensión permanente.

## Root Cause

La ficha registraba una exclusión/sunset pendiente de revalidación. Se inspeccionó el sitio exacto y se contrastó la razón de la excepción con el control que la sostiene.

## Regression Test

`python3 -m pytest -q tests/test_debt_registration_controls.py::test_debt_sunset_test_bb_bash_322`

Control negativo incluido en el selector: La muestra positiva y el control con contadores iguales pasan por `date` temporal (delta 4 s); verifican tasas esperadas y cero sin dormir.

## Verification Evidence

3 selectores corregidos (322, 339, 352) pasan en 64.51 s. Su variante mutante real omite `/d` y produce 4000/400 páginas/s, fuera del rango del positivo (1000/100); el control detecta el delta. `could_not_run=0`. Evidencia por comando y control negativo: `tasks/evidence/DEBT-SUNSET-TEST-BB-BASH-322/e2e.txt`.
