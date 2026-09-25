---
id: DEBT-ACCEPTED-SLEEP-TESTS-BB
title: "Los 4 time.sleep() de tests/test_bb_bash.py esperan a un subproceso real"
status: done
closure_type: void_wontfix
closed_at: 2026-09-24
severity: P3
category: debt
satd_family: ACCEPTED_TEST_SLEEP
lifespan: accepted
tag: DECISION
kind: debt
origin: asserted
close_check: {"cmd": "python3 -m pytest tests/test_bb_bash.py -q", "expect": "exit_zero"}
evidence:
  pass: tasks/evidence/DEBT-ACCEPTED-SLEEP-TESTS-BB/pass.txt
  fail: tasks/evidence/DEBT-ACCEPTED-SLEEP-TESTS-BB/fail.txt
  e2e: tasks/evidence/DEBT-ACCEPTED-SLEEP-TESTS-BB/e2e.txt
reason: "CERRADO como void_wontfix: los 4 time.sleep() de tests/test_bb_bash.py esperan a un SUBPROCESO real, no sondean un estado propio. No hay evento que compartir con un proceso hijo que esta reservando memoria, y sustituirlos por un bucle de sondeo cambiaria un sleep por otro."
created: 2026-09-24
---

## Root Cause

`zero-debt` bloqueo el commit de `tests/test_bb_bash.py` con 4 hallazgos de
`blocking_sleep`. El detector existe porque un `time.sleep()` en produccion
suele ser un sondeo que deberia ser un evento.

Aqui los cuatro esperan a un **subproceso real**: que exista antes de la
primera muestra, que reserve memoria entre las dos, o que dos muestras caigan
en segundos distintos. Entre procesos separados no hay condition variable que
compartir, y cambiar el `sleep` por un bucle que sondea `/proc/<pid>/status`
seria cambiar un sleep por otro, con mas codigo.

Es la misma clase que `DEBT-SLOT-WAIT-SLEEP` en simplecode, resuelta igual.

## Regression Test

```
python3 -m pytest tests/test_bb_bash.py -q
```

Y el detector que lo cazo, sobre el fichero final: `blocking_sleep` sin
justificar -> 0.

## Verification Evidence

- `pass`: los 18 tests en verde.
- `fail`: los 7 mutantes de `bin/bb`, los 7 en rojo, con el original en verde.
- `e2e`: el detector satisfecho y tres corridas seguidas sin flaky.

LIMITE DECLARADO: los sleeps suman ~10 s a la suite. Es el precio de probar un
ejecutable de verdad en vez de simularlo, y se acepta por eso; si la suite
creciera hasta molestar, la salida es paralelizar los tests, no quitar las
esperas.
