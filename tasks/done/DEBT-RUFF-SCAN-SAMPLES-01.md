---
id: DEBT-RUFF-SCAN-SAMPLES-01
kind: task
domain: VERDICT
title: "Resolver infracciones Ruff en scan_samples.py"
status: done
severity: P2
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-10-02
closed_at: 2026-10-02
closure_type: fixed
close_check: {"cmd": "python3 -m ruff check tools/scan_samples.py", "expect": "exit_zero", "porque": "Ruff del archivo retorna cero con las reglas actuales y las pruebas del sujeto pasan. Reducir complejidad sin debilitar validación, seguridad ni controles negativos. No silenciar reglas ni añadir noqa para conseguir verde. Control negativo: variante temporal que exceda la regla vuelve a fallar."}
evidence: {"pass": "tasks/evidence/DEBT-RUFF-SCAN-SAMPLES-01/pass.txt", "fail": "tasks/evidence/DEBT-RUFF-SCAN-SAMPLES-01/fail.txt", "e2e": "tasks/evidence/DEBT-RUFF-SCAN-SAMPLES-01/e2e.txt"}
reason: "La salida y evaluación del gate se extrajeron a helpers cohesivos; los límites de validación, errores COULD_NOT_RUN y métricas permanecen cubiertos al 100%, sin alterar los casos de prueba. Ruff y los controles negativos dieron los resultados registrados."
---

## Registro y responsable

Registro solicitado por Luis el 2026-10-02. Responsable: coordinación de Blackbox. Defecto confirmado.

## Evidencia y alcance

Comando medido: `python3 -m ruff check tools tests --output-format=json`. 6 infracciones en este archivo:

- Línea 39: C901 — `asociar_cpu_gpu` is too complex (17 > 10)
- Línea 39: PLR0912 — Too many branches (18 > 12)
- Línea 39: PLR0915 — Too many statements (57 > 50)
- Línea 112: C901 — `preparar` is too complex (29 > 10)
- Línea 112: PLR0912 — Too many branches (30 > 12)
- Línea 112: PLR0915 — Too many statements (68 > 50)

Fuentes: tools/scan_samples.py.

## Criterio de cierre y control negativo

Ruff del archivo retorna cero con las reglas actuales y las pruebas del sujeto pasan. Reducir complejidad sin debilitar validación, seguridad ni controles negativos. No silenciar reglas ni añadir noqa para conseguir verde. Control negativo: variante temporal que exceda la regla vuelve a fallar.

## Estado del verificador

La ficha se cerró como fixed el 2026-10-02 después de que el close_check pasara y las pruebas de sujeto alcanzaran 100% de cobertura de sentencias y ramas.

Conservar comandos, salida literal y could_not_run incluso cero; una ejecución skipped o inaccesible deja el cierre pendiente. Reutilizar instrumentos nativos y pruebas existentes antes de crear código.

## Root Cause

`preparar` concentraba lectura JSONL, selección temporal, diagnóstico de filas, normalización de boot y validación de contadores/térmica. `asociar_cpu_gpu` juntaba lectura de históricos con caché de procesos y atribución temporal por PID. Extraje esas unidades a helpers; los orquestadores conservan la misma selección, métricas, mutación de filas y razones. Los fallos de lectura siguen incrementando el diagnóstico de COULD_NOT_RUN en vez de producir una ventana sana vacía.

## Regression Test

`python3 -m pytest --cov=tools.scan_samples --cov-report=term-missing tests/test_scan_samples.py` pasa 11 casos y reporta 100% de cobertura de sentencias, 0 faltantes. Cinco regresiones de auditoría pasan, incluidas ventana, contadores entre boots, CPU/GPU vacía e inválida, e incremento de COULD_NOT_RUN por análisis fallido. La variante Ruff temporal de 13 ramas falla con C901 y PLR0912.

## Verification Evidence

Las salidas literales están en `tasks/evidence/DEBT-RUFF-SCAN-SAMPLES-01/{fail,pass,e2e}.txt`. Antes, el close_check reportó tres reglas en `asociar_cpu_gpu` y tres en `preparar` (exit 1). Después, `python3 -m ruff check tools/scan_samples.py` pasa; los 11 tests cubren el módulo al 100%, y los cinco tests de regresión también pasan. El control Ruff negativo devuelve exit 1 por C901 y PLR0912, como se espera.
