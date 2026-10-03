---
id: DEBT-RUFF-ATOM-GPU-TELEMETRY-01
kind: task
domain: VERDICT
title: "Resolver infracciones Ruff en atom_gpu_telemetry.py"
status: done
closure_type: fixed
closed_at: 2026-10-02
severity: P2
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-10-02
close_check: {"cmd": "python3 -m ruff check tools/atom_gpu_telemetry.py", "expect": "exit_zero", "porque": "Ruff del archivo retorna cero con las reglas actuales y las pruebas del sujeto pasan. Reducir complejidad sin debilitar validación, seguridad ni controles negativos. No silenciar reglas ni añadir noqa para conseguir verde. Control negativo: variante temporal que exceda la regla vuelve a fallar."}
evidence:
  fail: tasks/evidence/DEBT-RUFF-ATOM-GPU-TELEMETRY-01.fail.txt
  pass: tasks/evidence/DEBT-RUFF-ATOM-GPU-TELEMETRY-01.pass.txt
  e2e: tasks/evidence/DEBT-RUFF-ATOM-GPU-TELEMETRY-01.e2e.txt
reason: "CERRADO: se extrajeron pausa, reanudación y CLI sin cambiar las compuertas, persistencia, identidades ni eventos. Las seis suites dieron 173 passed; las ramas nuevas quedaron cubiertas. El subconjunto conserva 99% de cobertura, igual al baseline, con los mismos seis arcos parciales preexistentes."
---

## Registro y responsable

Registro solicitado por Luis el 2026-10-02. Responsable: coordinación de Blackbox. Defecto confirmado.

## Evidencia y alcance

Comando medido: `python3 -m ruff check tools tests --output-format=json`. 5 infracciones en este archivo:

- Línea 1396: C901 — `mitigar` is too complex (17 > 10)
- Línea 1396: PLR0913 — Too many arguments in function definition (6 > 5)
- Línea 1396: PLR0912 — Too many branches (17 > 12)
- Línea 1396: PLR0915 — Too many statements (64 > 50)
- Línea 1582: C901 — `main` is too complex (12 > 10)

Fuentes: tools/atom_gpu_telemetry.py.

## Criterio de cierre y control negativo

Ruff del archivo retorna cero con las reglas actuales y las pruebas del sujeto pasan. Reducir complejidad sin debilitar validación, seguridad ni controles negativos. No silenciar reglas ni añadir noqa para conseguir verde. Control negativo: variante temporal que exceda la regla vuelve a fallar.

## Estado del verificador

Ficha cerrada; el close_check existente pasa en el archivo sujeto.

## Root Cause

La función mitigar mezclaba selección, pausa, persistencia, reconciliación de PID y eventos; main reunía dos modos CLI. Ruff detectó C901, PLR0913, PLR0912 y PLR0915.

## Regression Test

Las seis suites atom verifican carga real, ausencia de datos, señales, identidad y persistencia. Se añadió un control para conservar TypeError ante una opción desconocida.

## Verification Evidence

Ruff del archivo pasa. Las seis suites: 173 passed. Cobertura: 99%, cero statements omitidos, 6 arcos parciales; el baseline original también dio 99% y los mismos 6 arcos equivalentes. El gate --fail-under=100 sigue fallando como en baseline. Ver e2e.
