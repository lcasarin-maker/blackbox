---
id: DEBT-SUNSET-TEST-BB-BASH-352
kind: task
domain: VERDICT
title: "Revisar sunset en test_bb_bash.py:352"
status: done
severity: P2
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-10-02
close_check: {"cmd": "python3 -m pytest -q tests/test_debt_registration_controls.py::test_debt_sunset_test_bb_bash_352", "expect": "exit_zero", "porque": "Revalidar la justificación y el alcance exacto de la excepción sunset antes de su vencimiento, con comando literal y control negativo. Si es pausa de arnés/sampler, medir timeout/bounded scope/cancelación; si es test, conservar sensibilidad al delta observado. Retirar la excepción innecesaria o registrar revisión válida con responsable y expiración concreta, sin suspensión permanente."}
closed_at: 2026-10-03
closure_type: fixed
reason: "El primer cierre reutilizaba por error 900000/900000 en ambas muestras, así que nunca observaba retroceso. Ahora usa 900000/900000 y luego 12/34 con dt determinista de 1 s; una copia real de `bin/bb` sin clamp produce tasa negativa y el test la rechaza. El wait se eliminó."
evidence: {"pass":"tasks/evidence/DEBT-SUNSET-TEST-BB-BASH-352/pass.txt","fail":"tasks/evidence/DEBT-SUNSET-TEST-BB-BASH-352/fail.txt","e2e":"tasks/evidence/DEBT-SUNSET-TEST-BB-BASH-352/e2e.txt"}
---

## Registro y responsable

Registro solicitado por Luis el 2026-10-02. Responsable de revisión: coordinación de Blackbox. La excepción fue revisada y cerrada el 2026-10-03.

## Evidencia y alcance

Sitio: `tests/test_bb_bash.py:352`; función/contexto: test_bb_bash.

```text
time.sleep(2)  # blocking-sleep: dt de bin/bb tiene resolucion de SEGUNDO ENTERO (`date +%s`) -- DEBT-ACCEPTED-SLEEP-TESTS-BB  # sunset-reviewed: 2.1 -- relectura 2026-10-02: objetivo y expresion sin cambios frente a git show 7049dce^:tests/test_bb_bash.py; Las razones de delta entero y sondeo con deadline que siguen conservan su sujeto. Comparacion por linea en tasks/evidence/RELEASE-2.1.0/sunset-review.json. Revision anterior 2.0: sin cambios desde la revision de 1.9 horas antes, mismo dia, mismas evidencias -- SE QUEDA, y con razon MAS FUERTE que antes: instrumentado bin/bb directamente el 2026-09-28 (`dt=$(( ahora_s - antes_s ))` en la seccion de swap/cputop), sleep(0) dio dt=0 en 3 de 6 corridas -- exactamente esos 3 saltan el bloque `[ "$dt" -gt 0 ]` entero y dejan swpin_s/swpout_s en su default 0 SIN pasar por el clamp `(v>0?v:0)` que el test dice verificar. O sea que sin la espera, la mitad de las corridas pasarian por el camino EQUIVOCADO -- vacuamente, no por el mecanismo. Ya no es "argumento estructural solo": es una puerta de tiempo medida y su fallo reproducido. Evidencia: tasks/evidence/DEBT-ACCEPTED-SLEEP-TESTS-BB/dt-resolucion-entera-2026-09-28.txt
```

Revisión de 2026-10-03: la ficha anterior usaba los mismos contadores en ambas muestras y no demostraba retroceso. Se corrigió la segunda muestra; con dt=1 la copia sin clamp produce -899988.0 y el test la rechaza.

Fuentes: tests/test_bb_bash.py:352.

## Criterio de cierre y control negativo

Revalidar la justificación y el alcance exacto de la excepción sunset antes de su vencimiento, con comando literal y control negativo. Si es pausa de arnés/sampler, medir timeout/bounded scope/cancelación; si es test, conservar sensibilidad al delta observado. Retirar la excepción innecesaria o registrar revisión válida con responsable y expiración concreta, sin suspensión permanente.

## Root Cause

La ficha registraba una exclusión/sunset pendiente de revalidación. Se inspeccionó el sitio exacto y se contrastó la razón de la excepción con el control que la sostiene.

## Regression Test

`python3 -m pytest -q tests/test_debt_registration_controls.py::test_debt_sunset_test_bb_bash_352`

Control negativo incluido en el selector: Dos muestras de `bin/bb` con reloj `date` temporal producen dt=1 y la segunda trae 12/34 frente a 900000/900000. El control mutante quita los dos clamps del ejecutable copiado y el mismo test falla por tasa negativa.

## Verification Evidence

La segunda muestra usa 12/34 tras 900000/900000 con dt=1. La copia de `bin/bb` sin clamps produce `-899988.0` y provoca el fallo esperado. Tres selectores corregidos pasan en 64.51 s. `could_not_run=0`. Evidencia por comando y control negativo: `tasks/evidence/DEBT-SUNSET-TEST-BB-BASH-352/e2e.txt`.
