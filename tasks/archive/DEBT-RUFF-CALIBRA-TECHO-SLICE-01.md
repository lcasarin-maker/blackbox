---
id: DEBT-RUFF-CALIBRA-TECHO-SLICE-01
kind: task
domain: VERDICT
title: "Resolver infracciones Ruff en calibra_techo_slice.py"
status: done
closure_type: fixed
closed_at: 2026-10-02
severity: P2
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-10-02
close_check: {"cmd": "python3 -m ruff check tools/calibra_techo_slice.py", "expect": "exit_zero", "porque": "Ruff del archivo retorna cero con las reglas actuales y las pruebas del sujeto pasan. Reducir complejidad sin debilitar validación, seguridad ni controles negativos. No silenciar reglas ni añadir noqa para conseguir verde. Control negativo: variante temporal que exceda la regla vuelve a fallar."}
evidence:
  fail: tasks/evidence/DEBT-RUFF-CALIBRA-TECHO-SLICE-01.fail.txt
  pass: tasks/evidence/DEBT-RUFF-CALIBRA-TECHO-SLICE-01.pass.txt
  e2e: tasks/evidence/DEBT-RUFF-CALIBRA-TECHO-SLICE-01.e2e.txt
reason: "CERRADO: la lectura de cada línea JSONL se extrajo a un helper, conservando filtros, conversiones, memoria.peak y registro de I/O ilegible. Ruff y cobertura branch pasan."
---

## Registro y responsable

Registro solicitado por Luis el 2026-10-02. Responsable: coordinación de Blackbox. Defecto confirmado.

## Evidencia y alcance

Comando medido: `python3 -m ruff check tools tests --output-format=json`. 1 infracciones en este archivo:

- Línea 82: C901 — `serie` is too complex (11 > 10)

Fuentes: tools/calibra_techo_slice.py.

## Criterio de cierre y control negativo

Ruff del archivo retorna cero con las reglas actuales y las pruebas del sujeto pasan. Reducir complejidad sin debilitar validación, seguridad ni controles negativos. No silenciar reglas ni añadir noqa para conseguir verde. Control negativo: variante temporal que exceda la regla vuelve a fallar.

## Estado del verificador

Ficha cerrada; el close_check existente pasa en el archivo sujeto.

## Root Cause

serie leía ficheros, filtraba registros y parseaba cada slice dentro del mismo bucle, excediendo C901.

## Regression Test

test_calibra_techo_slice.py conserva los controles del mínimo de muestras, máximo creciente, slice ausente, muestras ilegibles, memory.peak y derivación del techo.

## Verification Evidence

Ruff pasa. Las suites de ambos calibradores dieron 47 passed; latencia_x y techo_slice alcanzaron cobertura branch 100%, cero statements omitidos y cero ramas parciales. Ver e2e.
