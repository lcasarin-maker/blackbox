---
id: DEBT-PREPUSH-TEST-OBSERVABILITY-BOOT-TYPES-01
kind: task
domain: VERDICT
title: "Cerrar hallazgos de observabilidad y tipos en pruebas"
status: done
severity: P2
origin: detected
satd_family: BLIND_INSTRUMENT
created: 2026-10-03
closed_at: 2026-10-03
closure_type: fixed
detector: {"rule": "PREPUSH adversarial_judge GS2-216 (4 pruebas) y Pyright reportArgumentType (tests/test_scan_samples.py._fila)", "confidence": 1.0}
close_check: {"cmd": "python3 .simplecode/run.py simplecode.verification.adversarial_judge --root . --gate", "expect": "exit_zero", "porque": "El juez adversarial nativo debe terminar con HALLAZGOS: 0, sin condenar los cuatro casos Mock Theater del reporte PREPUSH. Las pruebas conservan observaciones semánticas: resultado/causa primaria CUDA y fallos de cleanup, desaparición de proceso y sleeps, JSON/exit status del entrypoint, y ValueError con mensaje específico por parámetros inválidos."}
evidence: {"pass": "tasks/evidence/DEBT-PREPUSH-TEST-OBSERVABILITY-BOOT-TYPES-01/pass.txt", "fail": "tasks/evidence/DEBT-PREPUSH-TEST-OBSERVABILITY-BOOT-TYPES-01/fail.txt", "e2e": "tasks/evidence/DEBT-PREPUSH-TEST-OBSERVABILITY-BOOT-TYPES-01/e2e.txt"}
reason: "Se corrigieron las cuatro condenas GS2-216 haciendo visibles los valores reales de salida/llamada y los mensajes de rechazo; el helper de muestras ahora declara boot: object para los cuatro casos JSON heterogéneos. El juez nativo reporta cero hallazgos, Pyright reporta cero errores para el fixture y pasan 54 pruebas relacionadas."
---

## Registro y alcance

Fuente generada: /tmp/bb-final-prepush.txt, salida del PREPUSH para HEAD 3b66bff8e7b11ce164a60e90fe1a5a2f1eee4928. Grupo de cuatro condenas GS2-216 más cuatro errores de tipos del fixture de muestras.

## Criterio de cierre

El close_check es el CLI adversarial nativo y debe salir 0 con `HALLAZGOS: 0`. Ejecutar además Pyright sobre el módulo de prueba y pruebas funcionales relevantes. Mantener aserciones sobre valores medidos de los helpers, código y JSON emitido; conservar el límite/sleep del proceso y verificar cada clase de parámetro inválido. No añadir aserciones genéricas para satisfacer el juez.

## Root Cause

Las pruebas de CGroup delegaban observaciones al helper y el wrapper no afirmaba un resultado; la de Electron falso medía únicamente los intervalos de sleep; la del entrypoint aceptaba un `SystemExit` sin inspeccionar el código ni JSON; las pruebas de bounds no contrastaban el mensaje de rechazo. El helper `_fila` anotaba `boot` como `str`, aunque la regresión usa valores que JSON puede decodificar como `None`, número, objeto o lista.

## Regression Test

Las pruebas de los cuatro casos observan datos reales de retorno/captura: JSON con causa de asignación y errores de liberación, stdout vacío de pgrep junto a sus llamadas de teardown y los dos intervalos existentes, SystemExit con código 0 más JSON status pass, y `ValueError` con causa específica para cada entrada inválida. Pyright acepta `boot: object` sin cast ni supresión.

## Verification Evidence

Las salidas literales están en `tasks/evidence/DEBT-PREPUSH-TEST-OBSERVABILITY-BOOT-TYPES-01/{fail,pass,e2e}.txt`. El juez nativo falla con 4 hallazgos sobre HEAD original y pasa con 0; al restaurar los tests originales vuelve a fallar con los 4. Pyright pasa con 0 errores y el control negativo del fixture original reproduce los 4 reportArgumentType. Ruff pasa y 54 pruebas relacionadas pasan.
