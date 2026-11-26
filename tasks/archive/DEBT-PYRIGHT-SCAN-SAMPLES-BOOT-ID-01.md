---
id: DEBT-PYRIGHT-SCAN-SAMPLES-BOOT-ID-01
kind: task
domain: VERDICT
title: "Validar boot_id antes de agrupar contadores de muestras"
status: done
severity: P2
origin: detected
detector: {"rule": "pyright: reportArgumentType for boot_id dictionary key", "confidence": 1.0}
satd_family: BLIND_INSTRUMENT
created: 2026-10-03
closed_at: 2026-10-03
closure_type: fixed
close_check: {"cmd": "python3 -m pytest -q tests/test_scan_samples.py::test_scan_samples_malformed_boot_ids_preserve_valid_counters", "expect": "exit_zero", "porque": "La prueba debe alimentar boot_id faltante y valores JSON no string mezclados con dos muestras válidas del mismo boot; debe completar sin excepción, excluir contadores de filas malformadas y conservar los contadores válidos. El control negativo debe probar que una mutación que usa boot_id sin validar falla."}
evidence: {"pass": "tasks/evidence/DEBT-PYRIGHT-SCAN-SAMPLES-BOOT-ID-01/pass.txt", "fail": "tasks/evidence/DEBT-PYRIGHT-SCAN-SAMPLES-BOOT-ID-01/fail.txt", "e2e": "tasks/evidence/DEBT-PYRIGHT-SCAN-SAMPLES-BOOT-ID-01/e2e.txt"}
reason: "Pyright señaló Unknown | None como clave dict en setdefault al agrupar contadores por boot. Ahora solo se seleccionan boot_id string no vacíos y se agrupa usando boot_actual ya validado; las filas malformadas pierden contadores y las tasas válidas permanecen intactas. Pyright, Ruff y las 12 pruebas pasan; la cobertura del módulo registra 100% de sentencias y ramas."
---

## Registro y responsable

Deuda detectora Pyright observada en tools/scan_samples.py:203. Responsable: coordinación de Blackbox.

## Criterio de cierre

Resolver el error de tipos con validación real del valor de boot_id, sin casts, ignores ni supresiones. La regresión debe probar entradas JSON malformadas y conservar el cálculo válido de contadores.

## Root Cause

El código asumía que comparar el valor no tipado de boot_id contra el boot actual lo convertía en str. Pyright reportaba correctamente que dict.setdefault podía recibir None o un valor desconocido.

## Regression Test

El close_check ejecuta test_scan_samples_malformed_boot_ids_preserve_valid_counters con boot_id faltante y valores JSON no string junto con dos filas válidas. Comprueba que no se produce excepción, se quitan contadores de filas con boot_id inválido y los contadores válidos siguen disponibles. El control negativo restauró el código original y el test falló con TypeError: unhashable type: 'list'.

## Verification Evidence

Las salidas literales están en tasks/evidence/DEBT-PYRIGHT-SCAN-SAMPLES-BOOT-ID-01/{fail,pass,e2e}.txt. El close_check pasó (1 test); Pyright reporta 0 errores, Ruff pasa, las 12 pruebas pasan y coverage reporta 208/208 sentencias y 92/92 ramas. El control negativo del código original falla con TypeError, como requiere el gate.
