---
id: DEBT-COBERTURA-PISO-REBAJADO-01
kind: task
domain: VERDICT
title: "Restituir el piso de cobertura a 100 % cuando se cierren las fichas de pruebas xfail"
status: open
severity: P2
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-10-06
close_check: {"cmd": "python3 -m pytest -q tests/test_cobertura_piso.py", "expect": "exit_zero", "porque": "El piso vuelve a 100 % solo cuando las fichas de las pruebas xfail se cierren con evidencia y su cobertura se mide completa."}
---

## Registro y responsable

Registro creado el 2026-10-06 con la decisión de Luis (DECISIONS.md, misma fecha). Responsable: Luis Casarin. El piso de `.coverage_watermark` queda en 97.15 % con caducidad 2026-11-06.

## Evidencia y alcance

- tests/known_failures.json (116 entradas xfail, cada una con su ficha)
- .coverage_watermark (97.15)

## Criterio de cierre

El piso vuelve a 100 % cuando las fichas de las pruebas xfail se cierran y la cobertura medida es completa.

## Estado

Abierta. La caducidad de la excepción no la aplica ningún gate todavía: hay que revisarla a mano antes de 2026-11-06.
