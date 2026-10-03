---
id: DEBT-RUFF-TEST-AUDITORIA-BB-REGRESIONES-01
kind: task
domain: VERDICT
title: "Resolver infracciones Ruff en test_auditoria_bb_regresiones.py"
status: done
closure_type: fixed
closed_at: 2026-10-02
severity: P2
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-10-02
close_check: {"cmd": "python3 -m ruff check tests/test_auditoria_bb_regresiones.py", "expect": "exit_zero", "porque": "Ruff del archivo retorna cero con las reglas actuales y las pruebas del sujeto pasan. Reducir complejidad sin debilitar validación, seguridad ni controles negativos. No silenciar reglas ni añadir noqa para conseguir verde. Control negativo: variante temporal que exceda la regla vuelve a fallar."}
evidence:
  fail: tasks/evidence/DEBT-RUFF-TEST-AUDITORIA-BB-REGRESIONES-01.fail.txt
  pass: tasks/evidence/DEBT-RUFF-TEST-AUDITORIA-BB-REGRESIONES-01.pass.txt
  e2e: tasks/evidence/DEBT-RUFF-TEST-AUDITORIA-BB-REGRESIONES-01.e2e.txt
reason: "CERRADO: Ruff ahora pasa después de simplificar el helper de gate / extraer la simulación de archivo tardío; las pruebas conservan los casos de bloqueo, control negativo, telemetría y rotación. El control negativo temporal vuelve a detectar PLR0913 y PLR0915."
---

## Registro y responsable

Registro solicitado por Luis el 2026-10-02. Responsable: coordinación de Blackbox. Defecto confirmado.

## Evidencia y alcance

Comando medido: `python3 -m ruff check tools tests --output-format=json`. 1 infracciones en este archivo:

- Línea 157: PLR0915 — Too many statements (51 > 50)

Fuentes: tests/test_auditoria_bb_regresiones.py.

## Criterio de cierre y control negativo

Ruff del archivo retorna cero con las reglas actuales y las pruebas del sujeto pasan. Reducir complejidad sin debilitar validación, seguridad ni controles negativos. No silenciar reglas ni añadir noqa para conseguir verde. Control negativo: variante temporal que exceda la regla vuelve a fallar.

## Estado del verificador

La ficha permanece abierta. El comando ya existe; se conserva el fallo actual y falta resolver el sujeto.

Conservar comandos, salida literal y could_not_run incluso cero; una ejecución skipped o inaccesible deja el cierre pendiente. Reutilizar instrumentos nativos y pruebas existentes antes de crear código.
