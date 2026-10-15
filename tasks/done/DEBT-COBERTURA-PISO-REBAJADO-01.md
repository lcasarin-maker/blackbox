---
id: DEBT-COBERTURA-PISO-REBAJADO-01
kind: task
domain: VERDICT
title: "Restituir el piso de cobertura a 100 % cuando se cierren las fichas de pruebas xfail"
status: done
closed_at: 2026-10-15
closure_type: relocated_prior_verification
reason: "El piso se subio a 100.00 con coverage_target --advance (3629 passed) en el commit 8085a698 tras cubrir los ultimos modulos en la campana del 2026-10-15; este commit solo mueve la ficha. Control negativo: con el watermark de HEAD~1 (99.97) el mismo test falla."
evidence: {"pass": "tasks/evidence/DEBT-COBERTURA-PISO-REBAJADO-01/pass.txt", "fail": "tasks/evidence/DEBT-COBERTURA-PISO-REBAJADO-01/fail.txt", "e2e": "tasks/evidence/DEBT-COBERTURA-PISO-REBAJADO-01/e2e.txt"}
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

## Codigo inalcanzable hallado (2026-10-15, grupo-1)

`tools/forum_hardware_subjects.py` conserva 6 lineas que ninguna entrada puede ejecutar; cubrirlas exige borrarlas (decision del dueno), no probarlas: `_parse_compute_app` el `return None` de memoria negativa o no finita (la regex solo admite `\d+`); `_identity_matches_source` el `return False` de `not identity_rows` (`missing` ya retorno antes); `_read_integrity` el `return "unknown"` de elapsed (el replay ya exige elapsed > 0); `_gather_cases` el `return` de `not data` (`output` siempre esta presente); `_check_eee_measurements` el `return "unknown"` de `link_resets <= 0` (`disabled < direct` con `disabled >= 0` fuerza `direct > 0`); `_evaluate_simple` el `return "fail"` de `unsupported subject predicate` (todo id de IDS tiene rama).

## Estado (2026-10-11, /0 + /vote)

Bloqueada por criterio sin implementar: el `close_check` de esta ficha termina en `xfailed` y por eso sale con codigo 0 sin que el criterio real exista. Un `xfail` no es una verificacion y cerrar con el no es cierre. Cerrarla exige implementar la prueba real contra el sujeto (vLLM, NCCL, CX7 u otro hardware) con su control negativo. Decision del dueno el 2026-10-11: dejarla abierta y declarada, no cerrarla como `void_wontfix`.

## Root Cause
El piso de cobertura se rebajo a 97.15 % mientras las fichas de pruebas xfail y los modulos nuevos (apt guard, bb_root_run, observador_ping, incident_report, forum_hardware_subjects y 28 mas) no tenian tests que ejecutaran sus lineas; el ratchet solo sube cuando alguien mide y avanza.

## Regression Test
`tests/test_cobertura_piso.py::test_piso_de_cobertura_vuelve_a_100` exige `.coverage_watermark == 100.00`. El ratchet del pre-push (`coverage_target`) impide que el piso baje de nuevo.

## Verification Evidence
`tasks/evidence/DEBT-COBERTURA-PISO-REBAJADO-01/`: `fail.txt` (watermark de HEAD~1 = 99.97, el test falla), `pass.txt` (con 100.00 el test pasa), `e2e.txt` (corrida completa de la compuerta: 3629 passed, 14 xfailed, carril serial 1 passed, `ADVANCED: Watermark raised from 99.97% to 100.00%`). Limite: la medicion cubre `tools/` y el piso de `bin/bb` aparte; `bin/bb-guardia-proceso` (89 %) y `bin/bb-usable` (92 %) no entran en este piso.
