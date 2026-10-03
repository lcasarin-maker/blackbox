---
id: DEBT-RUFF-TEST-PRESUPUESTO-MEMORIA-01
kind: task
domain: VERDICT
title: "Resolver infracciones Ruff en test_presupuesto_memoria.py"
status: done
severity: P2
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-10-02
closed_at: 2026-10-02
closure_type: fixed
close_check: {"cmd": "python3 -m ruff check tests/test_presupuesto_memoria.py", "expect": "exit_zero", "porque": "Ruff del archivo retorna cero con las reglas actuales y las pruebas del sujeto pasan. Reducir complejidad sin debilitar validación, seguridad ni controles negativos. No silenciar reglas ni añadir noqa para conseguir verde. Control negativo: variante temporal que exceda la regla vuelve a fallar."}
evidence: {"pass": "tasks/evidence/DEBT-RUFF-TEST-PRESUPUESTO-MEMORIA-01/pass.txt", "fail": "tasks/evidence/DEBT-RUFF-TEST-PRESUPUESTO-MEMORIA-01/fail.txt", "e2e": "tasks/evidence/DEBT-RUFF-TEST-PRESUPUESTO-MEMORIA-01/e2e.txt"}
reason: "La validación parametrizada agrupa el caso de entrada en un único parámetro para quedar dentro del límite de argumentos Ruff conservando sus dos casos y asserts. Ruff y ambos casos de pytest pasan. El control negativo temporal de seis parámetros produce PLR0913."
---

## Registro y responsable

Registro solicitado por Luis el 2026-10-02. Responsable: coordinación de Blackbox. Defecto confirmado.

## Evidencia y alcance

Comando medido: `python3 -m ruff check tools tests --output-format=json`. 1 infracciones en este archivo:

- Línea 563: PLR0913 — Too many arguments in function definition (6 > 5)

Fuentes: tests/test_presupuesto_memoria.py.

## Criterio de cierre y control negativo

Ruff del archivo retorna cero con las reglas actuales y las pruebas del sujeto pasan. Reducir complejidad sin debilitar validación, seguridad ni controles negativos. No silenciar reglas ni añadir noqa para conseguir verde. Control negativo: variante temporal que exceda la regla vuelve a fallar.

## Estado del verificador

La ficha permanece abierta. El comando ya existe; se conserva el fallo actual y falta resolver el sujeto.

Conservar comandos, salida literal y could_not_run incluso cero; una ejecución skipped o inaccesible deja el cierre pendiente. Reutilizar instrumentos nativos y pruebas existentes antes de crear código.

## Root Cause

La función indicada en evidencia excedía la regla de complejidad o parámetros seleccionada por Ruff. La extracción/agrupación mantiene los controles originales.

## Regression Test

El close_check original pasa con las reglas actuales; las pruebas del sujeto conservan sus controles sanos y negativos. La variante temporal de Ruff registra el fallo de la regla sin cambiar configuración.

## Verification Evidence

Salidas literales antes/después y del subconjunto en las tres rutas evidence del frontmatter. Re-chequeo del coordinador y triage por ID registrados en tasks/evidence/ZERO-2026-10-02. La revisión Bash del hook carecía de archivos candidatos y se reporta como could_not_run.
