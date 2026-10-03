---
id: DEBT-JUDGE-THREAT-SWEEP-TOOLS-01
kind: debt
domain: VERDICT
title: El barrido de amenazas omite los módulos de tools
status: open
severity: P2
origin: detected
detector: {"rule": "adversarial_judge.AGENT_THREAT_TREES excludes tools", "confidence": 1.0}
satd_family: BLIND_INSTRUMENT
created: 2026-10-03
close_check: {"cmd": "python3 -m pytest -q tests/test_adversarial_product_scope.py::test_threat_sweep_reads_tools_and_rejects_injected_case", "expect": "exit_zero", "porque": "El control futuro debe demostrar lectura real de tools/, PASS del sujeto limpio y rechazo de un homoglyph/invisible inyectado en un módulo de esa ruta; la salida PASS con cero archivos no satisface el criterio."}
---

## Hallazgo medido

El hook pre-push invoca `simplecode.verification.adversarial_judge --root . --gate`. Su threat sweep declara `read 0 file(s) across <no tree>` y PASS. El checkout tiene 25 archivos Python trackeados bajo `tools/`; el barrido no los examina. La auditoría separada de mock-theater sí examinó las pruebas y detectó el defecto de importación reparado en esta sesión.

## Causa y alcance

`AGENT_THREAT_TREES` en el runtime fijado incluye `src`, `scripts`, `daemon`, `central`, `installer` y omite `tools`. La CLI ofrece solo root/gate; la revisión no encontró una configuración para ampliar el alcance. [Inspección literal](../evidence/CLEAN-2026-10-03/judge-scope-review.json). Un cero sostenido de este barrido acredita un defecto del instrumento, no limpieza de sus sujetos.

## Plan

Reparar la selección de directorios en la fuente del kit upstream y reconstruir su runtime fijado; incluir los directorios de producto declarados y distinguir ausencia de sujeto de un resultado juzgado. Añadir el selector de cierre en BB con fixture positiva y mutación negativa bajo `tools/`. El selector aún no existe y la ficha permanece abierta; cambiar la configuración generada o el ZIP local por fuera del productor no cumple el contrato del kit.

## Límites

Esta ficha no atribuye una vulnerabilidad a BB. Registra que ese barrido no inspeccionó su producto. Ruff, Pyright, cobertura, gitleaks y los controles de cierres conservan su alcance medido independiente.
