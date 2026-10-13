---
id: DEBT-APT-ARM64-EVIDENCE-PASS-INALCANZABLE-01
kind: debt
domain: GPU
title: "apt_arm64_evidence: verify_capture nunca devuelve pass (veredicto final inalcanzable)"
status: done
closed_at: 2026-10-13
closure_type: fixed
reason: "verify_capture puede devolver pass: una fila de control bad_source (apt-get con fuente mala, exit distinto de 0, stderr 404/Failed to fetch/Unable to locate) escribe bad_source_negative=pass; sin la fila sigue unknown y con un control que acepta la fuente mala da fail. Los tests nuevos fallan contra el codigo anterior (3 de 4) y pasan contra el nuevo."
evidence: {"pass": "tasks/evidence/DEBT-APT-ARM64-EVIDENCE-PASS-INALCANZABLE-01/pass.txt", "fail": "tasks/evidence/DEBT-APT-ARM64-EVIDENCE-PASS-INALCANZABLE-01/fail.txt", "e2e": "tasks/evidence/DEBT-APT-ARM64-EVIDENCE-PASS-INALCANZABLE-01/e2e.txt"}
severity: P2
origin: detected
detector: {"rule": "coverage: tests/test_apt_arm64_evidence.py, linea 111 inalcanzable", "confidence": 1.0}
satd_family: BLIND_INSTRUMENT
created: 2026-10-12
close_check: {"cmd": "python -m pytest tests/test_apt_arm64_evidence.py -q -k pass_alcanzable", "porque": "Hasta que exista una captura que verify_capture califique pass, el instrumento solo puede decir unknown o fail: un gate sin salida positiva.", "expect": "exit_zero"}
---

## Hallazgo
Al escribir `tests/test_apt_arm64_evidence.py` (2026-10-12): `_outcome("pass", ...)` al final de `verify_capture` (linea 111) es inalcanzable. `bad_source_negative` nunca se escribe en `checks` y `_validate_simulation` siempre termina en `unknown` o `fail`; con la captura buena el modulo da `unknown` con `bad_signature_negative=pass` y `bad_source_negative=unknown`.
## Falta
Decidir si `bad_source_negative` debe medirse (entonces escribirlo en `checks` y probar una captura que de `pass`, con test `*pass_alcanzable*` y su control negativo) o si el veredicto `pass` se retira del contrato del modulo.

## Root Cause
bad_source_negative nunca se escribia en checks y _validate_simulation terminaba siempre en unknown o fail: el veredicto final pass era inalcanzable, asi que el instrumento no podia certificar una captura buena.

## Regression Test
`tests/test_apt_arm64_evidence.py` con cuatro tests `*pass_alcanzable*` (pass con la fila, fail si el control acepta la fuente mala, fail con stderr irrelevante, unknown sin la fila).

## Verification Evidence
fail.txt: los tests nuevos contra el modulo anterior dan 3 failed; pass.txt: contra el nuevo, 4 passed; e2e.txt: los dos archivos de tests del modulo (38 passed, 7 xfailed preexistentes) y 99 % de cobertura. Pendiente fuera de esta ficha: grabar el control bad_source en una captura real (la de test_closure_hardware sigue en unknown).
