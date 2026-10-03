---
id: DEBT-H1-RELEASE-CLAIMS-01
kind: debt
domain: VERDICT
title: Auditar las afirmaciones pendientes de SPEC antes del release
status: open
severity: P1
origin: detected
satd_family: BLIND_INSTRUMENT
detector: {"rule": "audit gate: 12 unaudited SPEC claims", "confidence": 1.0}
created: 2026-10-03
close_check: {"cmd": "python3 .simplecode/run.py simplecode.cli audit --root . --gate", "expect": "exit_zero", "porque": "El ledger exige evidencia específica y sellos actuales para cada afirmación; corregir código o alcance factual antes de registrar los veredictos."}
owner: coordinación Blackbox
---

## Root Cause

El gate H1 identifica 12 afirmaciones sin auditoría vigente. La lista proviene de la salida nativa conservada en tasks/evidence/DEBT-H1-RELEASE-CLAIMS-01/source.json.

## Regression Test

Contrastar cada afirmación con código y controles negativos; los fallos por permisos deben declararse COULD_NOT_RUN y repetirse en el host autorizado. El gate nativo falla antes del registro válido.

## Verification Evidence

Auditoría en curso. Se conservarán resultados por afirmación y salida del gate antes de cerrar. Un cero histórico sin artefacto tiene alcance limitado y una ejecución actual divergente exige fecha y salida literal.
