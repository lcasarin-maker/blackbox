---
id: DEBT-JUDGE-THREAT-SWEEP-TOOLS-01
kind: debt
domain: VERDICT
title: El barrido de amenazas omite los módulos de tools
status: done
closure_type: relocated_prior_verification
reason: "El test de BB ya se commiteó en 4b3595f; la corrección del productor en 9a19c8be. Este commit mueve la ficha tras sync oficial 9.3.2 y close_check exit 0; no añade pruebas sintéticas para satisfacer el gate."
closed_at: 2026-10-03
severity: P2
origin: detected
detector: {"rule": "adversarial_judge.AGENT_THREAT_TREES excludes tools", "confidence": 1.0}
satd_family: BLIND_INSTRUMENT
created: 2026-10-03
evidence:
  pass: tasks/evidence/CLOSURE-CONTROLS-2026-10-03/scope-repair/official-pass.txt
  fail: tasks/evidence/CLOSURE-CONTROLS-2026-10-03/scope-repair/official-negative.txt
  e2e: tasks/evidence/CLOSURE-CONTROLS-2026-10-03/scope-repair/official-gate.txt
close_check: {"cmd": "python3 -m pytest -q tests/test_adversarial_product_scope.py::test_threat_sweep_reads_tools_and_rejects_injected_case", "expect": "exit_zero", "porque": "El control futuro debe demostrar lectura real de tools/, PASS del sujeto limpio y rechazo de un homoglyph/invisible inyectado en un módulo de esa ruta; la salida PASS con cero archivos no satisface el criterio."}
---

## Hallazgo medido

El hook pre-push invoca `simplecode.verification.adversarial_judge --root . --gate`. Su threat sweep declara `read 0 file(s) across <no tree>` y PASS. El checkout tiene 25 archivos Python trackeados bajo `tools/`; el barrido no los examina. La auditoría separada de mock-theater sí examinó las pruebas y detectó el defecto de importación reparado en esta sesión.

## Root Cause

`AGENT_THREAT_TREES` en el runtime fijado incluye `src`, `scripts`, `daemon`, `central`, `installer` y omite `tools`. La CLI ofrece solo root/gate; la revisión no encontró una configuración para ampliar el alcance. [Inspección literal](../evidence/CLEAN-2026-10-03/judge-scope-review.json). Un cero sostenido de este barrido acredita un defecto del instrumento, no limpieza de sus sujetos.

## Plan

Reparar la selección de directorios en la fuente del kit upstream y reconstruir su runtime fijado; incluir los directorios de producto declarados y distinguir ausencia de sujeto de un resultado juzgado. Añadir el selector de cierre en BB con fixture positiva y mutación negativa bajo `tools/`. El selector aún no existe y la ficha permanece abierta; cambiar la configuración generada o el ZIP local por fuera del productor no cumple el contrato del kit.

## Límites

Esta ficha no atribuye una vulnerabilidad a BB. Registra que ese barrido no inspeccionó su producto. Ruff, Pyright, cobertura, gitleaks y los controles de cierres conservan su alcance medido independiente.

## Regression Test

`tests/test_adversarial_product_scope.py` ahora ejecuta el juez fijado en un subproceso aislado, verifica el hash del artefacto contra kit.lock, compara la colección contra todos los archivos Python reales de tools y exige sujeto sano más detección de homoglyph e invisible inyectados. Contra el bundle oficial 9.3.1, el close_check devuelve exit 1 (`1 failed in 0.17s`): tools contiene 35 archivos y el scope del kit los omite; el negativo no devuelve hallazgos. Ruff y Pyright focales pasan (0 errores/advertencias/información). La reparación source y la sincronización oficial siguen pendientes, por lo que esta ficha conserva open. Evidencia literal: tasks/evidence/CLOSURE-CONTROLS-2026-10-03/scope-repair/official-negative.txt.

## Verification Evidence

La fuente del productor se reparó y aterrizó en su primario limpio mediante fast-forward del commit `9a19c8be` (versión local 9.3.2). El sincronizador canónico, ejecutado desde esa fuente, instaló runtime/lock en BB; no se editó el ZIP a mano. El close_check original pasó sobre BB (`official-pass.txt`), y el gate oficial declara `threat sweep read 35 file(s) across tools`, HALLAZGOS 0. El selector valida lectura completa del sujeto real y condena los dos negativos inyectados (homoglyph/invisible); esta evidencia acredita ese scope y esas dos clases, sin afirmar ausencia de toda vulnerabilidad.

Artefacto SHA256: 77fa3b77aa5c8a9bb2de4f23bdbfaf7e4246319526452370d0b6aa9995a2d9d3; content SHA256: de6eb26d3321e99bc85c1cc38e946d740881aa959815bd608afa901afea63fc3. Plan, aplicación, lock y gate literales en tasks/evidence/CLOSURE-CONTROLS-2026-10-03/scope-repair/. El productor pasó 4408 pruebas y cobertura 22406/22406 según las salidas de ejecución del agente; esos stdout completos quedaron en el historial de herramientas y no en archivos persistidos.
