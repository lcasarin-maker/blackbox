---
id: RELEASE-SUNSET-2-2-01
kind: task
domain: VERDICT
title: "Revisar 17 exenciones sunset antes de Blackbox 2.2.0"
status: done
closed_at: 2026-10-03
closure_type: relocated_prior_verification
reason: Revisión de 17 fuentes integrada en 0e42e5f7; versión nativa aplicada a 2.2.0 tras ledger H1 vigente; el close_check real pasa con 0 de 20 exenciones vencidas.
severity: P2
origin: detected
satd_family: BLIND_INSTRUMENT
detector: {"rule": "sunset-audit 2.2.0 stale exemption review", "confidence": 1.0}
created: 2026-10-03
close_check: {"cmd": "python3 .simplecode/run.py simplecode.verification.sunset_audit --root . --gate", "expect": "exit_zero", "porque": "Revalidar los 17 marcadores vencidos frente a la versión 2.2.0, manteniendo sus reglas y esperas solo si la revisión de fuente confirma que el comportamiento y control siguen vigentes."}
evidence: {"pass":"tasks/evidence/RELEASE-SUNSET-2-2-01/pass.txt","fail":"tasks/evidence/RELEASE-SUNSET-2-2-01/fail.txt","e2e":"tasks/evidence/RELEASE-SUNSET-2-2-01/e2e.txt"}
review_cost: "sunset-audit 0.4s; focused pytest 11.17s; 17 source rows read and hashed"
owner: "Luis (release owner); re-review at next version bump"
---

## Root Cause

Version 2.2.0's pre-push sunset audit found 17 markers still labeled 2.1 across 12 .gitignore rules, the long-lived Atom sampler interval, and four Bash tests. The rules and waits had persisted through the previous release, so the gate required a fresh source review before the next release.

## Regression Test

`python3 .simplecode/run.py simplecode.verification.sunset_audit --root . --gate`

Focused controls exercised the positive CPU-accounting test, its sleeping-process negative control, and Atom's missing-driver test without using a GPU. Earlier no-wait evidence recorded intermittent empty CPU samples and a failing positive control. The Atom interval remains the configurable cadence of its repeated sampler loop; `--once` exits without recurring sleep.

## Verification Evidence

The native audit passed with version 2.2.0 and zero stale exemptions: 20 reviewed, including 3 cgroup entries already current. Focused tests reported `3 passed in 11.17s`. A first pytest invocation used a misspelled selector and exited 4 with no tests collected; the corrected command passed. No review test remained unable to run. Literal pre-review gate output, source hashes, rule probes, and command results are in `tasks/evidence/RELEASE-SUNSET-2-2-01/`.
