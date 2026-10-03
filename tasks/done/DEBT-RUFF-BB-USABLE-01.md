---
id: DEBT-RUFF-BB-USABLE-01
kind: task
domain: VERDICT
title: "Resolver hallazgos del ejecutable completo fuera del alcance previo"
status: done
closed_at: 2026-10-02
closure_type: fixed
reason: "Logging extraído sin cambiar criterios del watchdog; Ruff del ejecutable pasa."
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

## Root Cause

El ejecutable sin extensión quedaba fuera del barrido tools/tests y main excedía C901. La función local de logging añade complejidad; el logging de recuperación se separa de los contadores y decisiones.

## Regression Test

Ruff del ejecutable completo, 27 pruebas del watchdog más cuatro controles registrados. Mantener picos sanos, colapso, bajada suelta, recuperación, PSI ilegible, plazo y envío real de notify.

## Verification Evidence

Las rutas evidence guardan la salida JSON original, Ruff verde y31pruebas con acceso de sockets Unix. Sin acceso, dos pruebas de socket fallan por PermissionError: resultado capturado sin suprimirlas.
