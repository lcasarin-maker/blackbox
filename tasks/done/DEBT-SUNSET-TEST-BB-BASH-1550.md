---
id: DEBT-SUNSET-TEST-BB-BASH-1550
kind: task
domain: VERDICT
title: "Revisar sunset en test_bb_bash.py:1550"
status: done
severity: P2
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-10-02
close_check: {"cmd": "python3 -m pytest -q tests/test_debt_registration_controls.py::test_debt_sunset_test_bb_bash_1550", "expect": "exit_zero", "porque": "Revalidar la justificación y el alcance exacto de la excepción sunset antes de su vencimiento, con comando literal y control negativo. Si es pausa de arnés/sampler, medir timeout/bounded scope/cancelación; si es test, conservar sensibilidad al delta observado. Retirar la excepción innecesaria o registrar revisión válida con responsable y expiración concreta, sin suspensión permanente."}
closed_at: 2026-10-03
closure_type: void_wontfix
reason: "Se conserva el sondeo de 50 ms dentro del deadline: el test controlado encuentra la ausencia dentro del plazo y demuestra que el poll cede al scheduler. El negativo real sigue ejecutándose por el selector funcional de Electron."
evidence: {"pass":"tasks/evidence/DEBT-SUNSET-TEST-BB-BASH-1550/pass.txt","fail":"tasks/evidence/DEBT-SUNSET-TEST-BB-BASH-1550/fail.txt","e2e":"tasks/evidence/DEBT-SUNSET-TEST-BB-BASH-1550/e2e.txt"}
---

## Registro y responsable

Registro solicitado por Luis el 2026-10-02. Responsable: coordinación de Blackbox. Trabajo o revisión pendiente; la presencia del marcador no demuestra por sí sola un defecto.

## Evidencia y alcance

Sitio: `tests/test_bb_bash.py:1550`; función/contexto: test_bb_bash.

```text
time.sleep(0.05)  # blocking-sleep: intervalo de sondeo DENTRO de un bucle con deadline explicito (arriba), no una espera fija -- sin el, el bucle quema un nucleo entero re-consultando pgrep sin ceder CPU -- DEBT-EL-GATE-DE-RENDERERS-EXIGE-CERO-NO-UI-MUERTA  # sunset-reviewed: 2.1 -- relectura 2026-10-02: objetivo y expresion sin cambios frente a git show 7049dce^:tests/test_bb_bash.py; Las razones de delta entero y sondeo con deadline que siguen conservan su sujeto. Comparacion por linea en tasks/evidence/RELEASE-2.1.0/sunset-review.json. Revision anterior 2.0: nuevo el 2026-09-28, mismo commit que lo introduce
```

Clasificación: revisión de una exclusión/captura, no bug demostrado. No retirar automáticamente una protección o cleanup.

Fuentes: tests/test_bb_bash.py:1550.

## Criterio de cierre y control negativo

Revalidar la justificación y el alcance exacto de la excepción sunset antes de su vencimiento, con comando literal y control negativo. Si es pausa de arnés/sampler, medir timeout/bounded scope/cancelación; si es test, conservar sensibilidad al delta observado. Retirar la excepción innecesaria o registrar revisión válida con responsable y expiración concreta, sin suspensión permanente.

## Root Cause

La ficha registraba una exclusión/sunset pendiente de revalidación. Se inspeccionó el sitio exacto y se contrastó la razón de la excepción con el control que la sostiene.

## Regression Test

`python3 -m pytest -q tests/test_debt_registration_controls.py::test_debt_sunset_test_bb_bash_1550`

Control negativo incluido en el selector: Se conserva el sondeo de 50 ms dentro del deadline: el test controlado encuentra la ausencia dentro del plazo y demuestra que el poll cede al scheduler. El negativo real sigue ejecutándose por el selector funcional de Electron.

## Verification Evidence

Pass: selector `DEBT-SUNSET-TEST-BB-BASH-1550` pasa junto con los 13 selectores de esta ola; resultado `14 passed`, `could_not_run=0`. Fail previo: selector ausente, pytest exit 4; registrado solo como estado anterior de la instrumentación. El detalle y el alcance del control negativo constan en `tasks/evidence/DEBT-SUNSET-TEST-BB-BASH-1550/e2e.txt`.
