---
id: DEBT-RUFF-TEST-ATOM-GPU-TELEMETRY-BB-01
kind: task
domain: VERDICT
title: "Resolver infracciones Ruff en test_atom_gpu_telemetry_bb.py"
status: done
closure_type: fixed
closed_at: 2026-10-02
severity: P2
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-10-02
close_check: {"cmd": "python3 -m ruff check tests/test_atom_gpu_telemetry_bb.py", "expect": "exit_zero", "porque": "Ruff del archivo retorna cero con las reglas actuales y las pruebas del sujeto pasan. Reducir complejidad sin debilitar validación, seguridad ni controles negativos. No silenciar reglas ni añadir noqa para conseguir verde. Control negativo: variante temporal que exceda la regla vuelve a fallar."}
evidence:
  fail: tasks/evidence/DEBT-RUFF-TEST-ATOM-GPU-TELEMETRY-BB-01.fail.txt
  pass: tasks/evidence/DEBT-RUFF-TEST-ATOM-GPU-TELEMETRY-BB-01.pass.txt
  e2e: tasks/evidence/DEBT-RUFF-TEST-ATOM-GPU-TELEMETRY-BB-01.e2e.txt
reason: "CERRADO: Ruff ahora pasa después de simplificar el helper de gate / extraer la simulación de archivo tardío; las pruebas conservan los casos de bloqueo, control negativo, telemetría y rotación. El control negativo temporal vuelve a detectar PLR0913 y PLR0915."
---

## Registro y responsable

Registro solicitado por Luis el 2026-10-02. Responsable: coordinación de Blackbox. Defecto confirmado.

## Evidencia y alcance

Comando medido: `python3 -m ruff check tools tests --output-format=json`. 1 infracciones en este archivo:

- Línea 419: PLR0913 — Too many arguments in function definition (6 > 5)

Fuentes: tests/test_atom_gpu_telemetry_bb.py.

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
