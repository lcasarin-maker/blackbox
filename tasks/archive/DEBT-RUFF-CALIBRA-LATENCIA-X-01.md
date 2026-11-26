---
id: DEBT-RUFF-CALIBRA-LATENCIA-X-01
kind: task
domain: VERDICT
title: "Resolver infracciones Ruff en calibra_latencia_x.py"
status: done
closure_type: fixed
closed_at: 2026-10-02
severity: P2
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-10-02
close_check: {"cmd": "python3 -m ruff check tools/calibra_latencia_x.py", "expect": "exit_zero", "porque": "Ruff del archivo retorna cero con las reglas actuales y las pruebas del sujeto pasan. Reducir complejidad sin debilitar validación, seguridad ni controles negativos. No silenciar reglas ni añadir noqa para conseguir verde. Control negativo: variante temporal que exceda la regla vuelve a fallar."}
evidence:
  fail: tasks/evidence/DEBT-RUFF-CALIBRA-LATENCIA-X-01.fail.txt
  pass: tasks/evidence/DEBT-RUFF-CALIBRA-LATENCIA-X-01.pass.txt
  e2e: tasks/evidence/DEBT-RUFF-CALIBRA-LATENCIA-X-01.e2e.txt
reason: "CERRADO: el reporte de episodios y la evaluación de cortes se extrajeron a un helper sin alterar muestras, etiquetas ni umbrales. Ruff y cobertura branch pasan."
---

## Registro y responsable

Registro solicitado por Luis el 2026-10-02. Responsable: coordinación de Blackbox. Defecto confirmado.

## Evidencia y alcance

Comando medido: `python3 -m ruff check tools tests --output-format=json`. 2 infracciones en este archivo:

- Línea 242: C901 — `main` is too complex (11 > 10)
- Línea 242: PLR0915 — Too many statements (51 > 50)

Fuentes: tools/calibra_latencia_x.py.

## Criterio de cierre y control negativo

Ruff del archivo retorna cero con las reglas actuales y las pruebas del sujeto pasan. Reducir complejidad sin debilitar validación, seguridad ni controles negativos. No silenciar reglas ni añadir noqa para conseguir verde. Control negativo: variante temporal que exceda la regla vuelve a fallar.

## Estado del verificador

Ficha cerrada; el close_check existente pasa en el archivo sujeto.

## Root Cause

main mezclaba carga del corpus, etiquetas, reporte y búsqueda de cortes, excediendo C901 y PLR0915.

## Regression Test

test_calibra_latencia_x.py conserva controles de muestreador desalojado frente a sano, duración consecutiva, ausencia de etiquetas y etiqueta sintética.

## Verification Evidence

Ruff pasa. Las suites de ambos calibradores dieron 47 passed; latencia_x y techo_slice alcanzaron cobertura branch 100%, cero statements omitidos y cero ramas parciales. Ver e2e.
