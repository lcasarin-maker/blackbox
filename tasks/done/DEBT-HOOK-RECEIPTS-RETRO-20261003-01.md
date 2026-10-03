---
id: DEBT-HOOK-RECEIPTS-RETRO-20261003-01
kind: debt
title: "17 commits de la ola del 3 de octubre carecían de recibo pre-commit verificable"
status: done
closure_type: relocated_prior_verification
closed_at: 2026-10-03
severity: P2
origin: detected
detector: {"rule": "native hook_receipts audit: missing retroactive verification for commits generated 2026-10-03", "confidence": 1.0}
satd_family: BLIND_INSTRUMENT
created: 2026-10-03
close_check: {"cmd": "python3 .simplecode/run.py simplecode.verification.hook_receipts --root . --audit --gate", "expect": "exit_zero", "porque": "El verificador nativo vuelve a construir su ventana reciente y reporta 0 recibos ausentes o bloqueantes; los recibos retroactivos no se presentan como escritos a tiempo."}
evidence:
  fail: tasks/evidence/DEBT-HOOK-RECEIPTS-RETRO-20261003-01.fail.txt
  pass: tasks/evidence/DEBT-HOOK-RECEIPTS-RETRO-20261003-01.pass.txt
  e2e: tasks/evidence/DEBT-HOOK-RECEIPTS-RETRO-20261003-01.e2e.txt
reason: "Cerrado con 17 verificaciones retroactivas ejecutadas por el hook pre-commit propio y registradas en .simplecode/evidence/hook_receipts.jsonl. Cada salida identifica GIT_VERIFIED_RETROACTIVE; no se alteró el cutoff ni el baseline."
---

## Root Cause

Los commits de la ola se crearon bajo secuenciación que dejó recibos faltantes; la auditoría nativa detectó esos IDs antes de que se reejecutara el pre-commit propio.

## Regression Test

El close_check ejecuta `hook_receipts --audit --gate`: verifica en la ventana activa que los recibos requeridos existen y que no hay commit bloqueante sin recibo. Los SHA antiguos fuera de ventana se midieron por separado con `--verify-historical`; esa verificación no se confunde con un recibo contemporáneo.

## Verification Evidence

Las salidas literales pre/post y la lista de 17 SHA se conservan en las tres rutas evidence. Los 6 commits históricos de septiembre también se retroverificaron; el audit final los dejó en cero fuera de ventana sin modificar el baseline.
