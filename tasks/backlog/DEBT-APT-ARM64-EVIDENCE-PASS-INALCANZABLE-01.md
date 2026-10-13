---
id: DEBT-APT-ARM64-EVIDENCE-PASS-INALCANZABLE-01
kind: debt
domain: GPU
title: "apt_arm64_evidence: verify_capture nunca devuelve pass (veredicto final inalcanzable)"
status: open
severity: P2
origin: detected
satd_family: BLIND_INSTRUMENT
created: 2026-10-12
close_check: {"cmd": "python -m pytest tests/test_apt_arm64_evidence.py -q -k pass_alcanzable", "porque": "Hasta que exista una captura que verify_capture califique pass, el instrumento solo puede decir unknown o fail: un gate sin salida positiva.", "expect": "exit_zero"}
---

## Hallazgo
Al escribir `tests/test_apt_arm64_evidence.py` (2026-10-12): `_outcome("pass", ...)` al final de `verify_capture` (linea 111) es inalcanzable. `bad_source_negative` nunca se escribe en `checks` y `_validate_simulation` siempre termina en `unknown` o `fail`; con la captura buena el modulo da `unknown` con `bad_signature_negative=pass` y `bad_source_negative=unknown`.
## Falta
Decidir si `bad_source_negative` debe medirse (entonces escribirlo en `checks` y probar una captura que de `pass`, con test `*pass_alcanzable*` y su control negativo) o si el veredicto `pass` se retira del contrato del modulo.
