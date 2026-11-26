---
id: DEBT-RUFF-BB-USABLE-01
kind: task
domain: VERDICT
title: "Resolver hallazgos del ejecutable completo fuera del alcance previo"
status: done
closed_at: 2026-10-16
closure_type: fixed
reason: "main() partida en reacciones explicitas (ilegible, alta, colapso, baja) con los contadores pasados y devueltos; una caracterizacion grabada contra el main() sin modificar fija byte a byte notify, log, origen y contadores. Ruff del ejecutable pasa."
evidence: {"pass": "tasks/evidence/DEBT-RUFF-BB-USABLE-01.pass.txt", "fail": "tasks/evidence/DEBT-RUFF-BB-USABLE-01.fail.txt", "e2e": "tasks/evidence/DEBT-RUFF-BB-USABLE-01.e2e.txt"}
severity: P2
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-10-02
close_check: {"cmd": "python3 -m ruff check bin/bb-usable", "expect": "exit_zero", "porque": "Reglas actuales pasan sobre el sujeto completo. Preservar semántica, controles sanos y negativos; sin supresión de reglas ni cambios de configuración para ocultar hallazgos."}
---

## Registro automático /0

Hallazgos derivados de la salida JSON literal, no transcritos a mano. Fuente: tasks/evidence/DEBT-RUFF-BB-USABLE-01.fail.txt. 1 hallazgos.

```json
[
  {
    "cell": null,
    "code": "C901",
    "end_location": {
      "column": 9,
      "row": 247
    },
    "filename": "/tmp/bb-zero-provider/bin/bb-usable",
    "fix": null,
    "location": {
      "column": 5,
      "row": 247
    },
    "message": "`main` is too complex (12 > 10)",
    "name": "complex-structure",
    "noqa_row": 247,
    "severity": "error",
    "url": "https://docs.astral.sh/ruff/rules/complex-structure"
  }
]
```

## Criterio

Refactor mínimo y pruebas sobre el ejecutable real. Mantener quoting y estados could_not_run; variantes negativas deben fallar.

## Reapertura 2026-10-16

El backlog_verifier la devolvio: `python3 -m ruff check bin/bb-usable` salia 1 con C901 (`main` 12 > 10) y
PLR0915 (55 > 50 sentencias) en bin/bb-usable:863. f8006e7c anadio a main() la rama del atasco confinado
(`paso_confinado`, acaricia / habria_acariciado) despues del cierre del 2026-10-02, y nada volvio a correr el
close_check en ese commit.

## Root Cause

Primer cierre (2026-10-02): el ejecutable sin extension quedaba fuera del barrido tools/tests y main excedia C901;
se extrajo `log_recovery`. Reapertura: cada criterio nuevo del latido se anadia como otra rama dentro del `while`
de main(), que crecia sin limite porque las decisiones (ilegible, alta, colapso, baja) vivian en linea con los
contadores como variables locales. Arreglo: cuatro funciones de modulo -- `reaccion_psi_ilegible`,
`reaccion_psi_alta`, `reaccion_colapso`, `reaccion_psi_baja` -- que reciben y devuelven `sostenido`, `bajas` y
`confinadas` de forma explicita y devuelven si la vuelta acaricia; main() solo llama `notify("WATCHDOG=1")` cuando
la reaccion lo pide. Mismas lineas de log, mismo orden de efectos. De paso, pyright sobre el archivo tocado daba 4
errores previos (spec opcional en `_cargar_origen`, `s.fraccion() >= ...` sin estrechar); corregidos sin cambiar la
conducta.

## Regression Test

`tests/test_bb_usable_caracterizacion.py` (17 pruebas): corre el main() real sobre 11 secuencias de PSI y compara la
lista ORDENADA de efectos (notify, log, origen con `sostenido`, paso confinado con `confinadas`) con
`tests/fixtures/bb_usable_caracterizacion.json`, grabado contra el main() SIN modificar de b71ef875. Seis pruebas
semanticas fijan en claro las caricias de cada escenario, para que regrabar la fixture con otra conducta no pase
inadvertido. Siguen corriendo las suites previas del watchdog (test_bb_usable, test_atasco_confinado,
test_escalon_app_slice y el resto de las que nombran bb-usable).

## Verification Evidence

- fail: ruff sale 1 con C901 + PLR0915 sobre b71ef875.
- pass: ruff sale 0 (`All checks passed!`); pyright 0 errores sobre los dos archivos tocados.
- e2e: caracterizacion 17 passed contra el refactor; control negativo 1 (el COLAPSO acaricia) 9 failed / 8 passed;
  control negativo 2 (off-by-one en la baja) 3 failed / 14 passed; ambas mutaciones revertidas y verificado el sha.
  Suites relacionadas mas test_sin_datos_privados: 639 passed, 8 xfailed, could_not_run 0.
