---
id: DEBT-RUFF-PRESUPUESTO-MEMORIA-01
kind: task
domain: VERDICT
title: "Resolver infracciones Ruff en presupuesto_memoria.py"
status: done
severity: P2
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-10-02
closed_at: 2026-10-02
closure_type: fixed
close_check: {"cmd": "python3 -m ruff check tools/presupuesto_memoria.py", "expect": "exit_zero", "porque": "Ruff del archivo retorna cero con las reglas actuales y las pruebas del sujeto pasan. Reducir complejidad sin debilitar validación, seguridad ni controles negativos. No silenciar reglas ni añadir noqa para conseguir verde. Control negativo: variante temporal que exceda la regla vuelve a fallar."}
evidence: {"pass": "tasks/evidence/DEBT-RUFF-PRESUPUESTO-MEMORIA-01/pass.txt", "fail": "tasks/evidence/DEBT-RUFF-PRESUPUESTO-MEMORIA-01/fail.txt", "e2e": "tasks/evidence/DEBT-RUFF-PRESUPUESTO-MEMORIA-01/e2e.txt"}
reason: "La salida y evaluación del gate se extrajeron a helpers cohesivos; los límites de validación, errores COULD_NOT_RUN y métricas permanecen cubiertos al 100%, sin alterar los casos de prueba. Ruff y los controles negativos dieron los resultados registrados."
---

## Registro y responsable

Registro solicitado por Luis el 2026-10-02. Responsable: coordinación de Blackbox. Defecto confirmado.

## Evidencia y alcance

Comando medido: `python3 -m ruff check tools tests --output-format=json`. 3 infracciones en este archivo:

- Línea 375: C901 — `main` is too complex (25 > 10)
- Línea 375: PLR0912 — Too many branches (30 > 12)
- Línea 375: PLR0915 — Too many statements (72 > 50)

Fuentes: tools/presupuesto_memoria.py.

## Criterio de cierre y control negativo

Ruff del archivo retorna cero con las reglas actuales y las pruebas del sujeto pasan. Reducir complejidad sin debilitar validación, seguridad ni controles negativos. No silenciar reglas ni añadir noqa para conseguir verde. Control negativo: variante temporal que exceda la regla vuelve a fallar.

## Estado del verificador

La ficha se cerró como fixed el 2026-10-02 después de que el close_check pasara y las pruebas de sujeto alcanzaran 100% de cobertura de sentencias y ramas.

Conservar comandos, salida literal y could_not_run incluso cero; una ejecución skipped o inaccesible deja el cierre pendiente. Reutilizar instrumentos nativos y pruebas existentes antes de crear código.

## Root Cause

`main` mezclaba el parseo del CLI, tres bloques de informe, la detección de lecturas incompletas y el veredicto del gate. Separé el formato por sección en `_mostrar_compromisos`, `_mostrar_excursion` y `_mostrar_abanico`; `_problemas_check` conserva las reglas y `None` sigue marcando MemTotal ilegible. El cálculo, los umbrales y el texto de COULD_NOT_RUN se mantienen.

## Regression Test

`python3 -m pytest --cov=tools.presupuesto_memoria --cov-report=term-missing tests/test_presupuesto_memoria.py` pasa 39 casos y reporta 100% de cobertura de sentencias, 0 faltantes. La suite incluye la serie ilegible y COULD_NOT_RUN sin muestras. La variante Ruff temporal de 13 ramas falla con C901 y PLR0912.

## Verification Evidence

Las salidas literales están en `tasks/evidence/DEBT-RUFF-PRESUPUESTO-MEMORIA-01/{fail,pass,e2e}.txt`. Antes, el close_check produjo C901, PLR0912 y PLR0915 (exit 1). Después, `python3 -m ruff check tools/presupuesto_memoria.py` pasa; los 39 tests pasan al 100%. El control Ruff negativo devuelve exit 1 por C901 y PLR0912, como se espera.
