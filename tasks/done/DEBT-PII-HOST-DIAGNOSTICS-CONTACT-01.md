---
id: "DEBT-PII-HOST-DIAGNOSTICS-CONTACT-01"
kind: "task"
domain: "VERDICT"
title: "Retirar correos de contacto del driver de diagnósticos compartibles"
status: "done"
severity: "P2"
origin: "detected"
detector: {"rule": "pii_scan: contact email in two host diagnostic snapshots", "confidence": 1.0}
satd_family: "BLIND_INSTRUMENT"
created: "2026-10-03"
closed_at: "2026-10-03"
closure_type: "fixed"
close_check: {"cmd": "python3 -c 'import subprocess; subprocess.run([\"python3\", \"-m\", \"pytest\", \"-q\", \"tests/test_host_diagnostics.py\"], check=True); subprocess.run([\"python3\", \".simplecode/run.py\", \"simplecode.verification.pii_scan\", \"--root\", \".\"], check=True)'", "expect": "exit_zero", "porque": "La regresión sustituye contactos entre ángulos en stdout/stderr, conserva unidades systemd y el estado real de error; neutralizar el matcher debe hacer fallar el control. El gate PII debe pasar sin exenciones ni cambios en el detector."}
evidence: {"pass": "tasks/evidence/DEBT-PII-HOST-DIAGNOSTICS-CONTACT-01/pass.txt", "fail": "tasks/evidence/DEBT-PII-HOST-DIAGNOSTICS-CONTACT-01/fail.txt", "e2e": "tasks/evidence/DEBT-PII-HOST-DIAGNOSTICS-CONTACT-01/e2e.txt"}
reason: "El capturador conservaba un correo de soporte publicado por Realtek en dos evidencias. Se sustituye ese dato de contacto en las salidas compartibles y se declara su conteo. Los originales locales se preservan con hash y modo; el gate y las señales diagnósticas se conservan."
---

## Root Cause

run_readonly publicaba stdout/stderr incluyendo direcciones de contacto entre ángulos. El gate detectó un correo de proveedor en dos capturas.

## Regression Test

test_contact_emails_redacted_without_altering_systemd_units conserva el nombre de unidad systemd y status/returncode al retirar contactos. Neutralizar el matcher reproduce el fallo de la misma prueba.

## Verification Evidence

Los comandos y salidas literales están en pass.txt y fail.txt; e2e.txt identifica el sujeto y las limitaciones. redaction-manifest.json registra los originales privados, SHA256 y modos. Responsable: coordinación Blackbox.
