---
id: DEBT-SKIP-TEST-PII-SCAN-SYSTEMD-86
kind: task
domain: VERDICT
title: "Revisar skip en test_pii_scan_systemd.py:86"
severity: P2
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-10-02
close_check: {"cmd": "python3 -m pytest -q tests/test_debt_registration_controls.py::test_debt_skip_test_pii_scan_systemd_86", "expect": "exit_zero", "porque": "Ejecutar la rama del sujeto que hoy puede quedar skipped con fixture reproducible o entorno requerido identificado. Un informe con skip no se declara limpio. Control negativo: quitar la capacidad/fixture produce could_not_run visible; romper el comportamiento real hace fallar la prueba. Conservar el skip si corresponde, con razón, responsable y disparador revisables; no quitarlo para forzar éxito."}
status: done
closed_at: 2026-10-03
closure_type: fixed
reason: "La ausencia del runtime ya falla con COULD_NOT_RUN y tiene control negativo reproducible; el kit real está verificado en el worktree."
evidence: {"pass":"tasks/evidence/DEBT-SKIP-TEST-PII-SCAN-SYSTEMD-86.pass.txt","fail":"tasks/evidence/DEBT-SKIP-TEST-PII-SCAN-SYSTEMD-86.fail.txt","e2e":"tasks/evidence/DEBT-SKIP-TEST-PII-SCAN-SYSTEMD-86.e2e.txt"}
---

## Registro y responsable

Registro solicitado por Luis el 2026-10-02. Responsable: coordinación de Blackbox. El defecto del instrumento quedó corregido y el close_check pasó con la precondición correspondiente.

## Evidencia y alcance

Sitio: `tests/test_pii_scan_systemd.py:86`; función/contexto: _pii_scan.

```text
pytest.skip(f"sin runtime del kit en {RUNTIME}")
```

Clasificación: revisión de una exclusión/captura, no bug demostrado. No retirar automáticamente una protección o cleanup.

Fuentes: tests/test_pii_scan_systemd.py:86.

## Criterio de cierre y control negativo

Ejecutar la rama del sujeto que hoy puede quedar skipped con fixture reproducible o entorno requerido identificado. Un informe con skip no se declara limpio. Control negativo: quitar la capacidad/fixture produce could_not_run visible; romper el comportamiento real hace fallar la prueba. Conservar el skip si corresponde, con razón, responsable y disparador revisables; no quitarlo para forzar éxito.

## Estado del verificador

El selector close_check pasó en su entorno requerido y no reportó skip ni COULD_NOT_RUN. Las salidas originales y posteriores están en las tres rutas evidence.

## Root Cause

La ausencia del runtime ya falla con COULD_NOT_RUN y tiene control negativo reproducible; el kit real está verificado en el worktree.

## Regression Test

El selector registrado ejecuta la rama afectada del test real y exige salida sin skip ni COULD_NOT_RUN. Los casos de permisos inyectan PermissionError/os.access(False) de manera acotada; PII prueba runtime ausente y contador ausente; los controles de racha usan el corpus real positivo y negativo; demonio ejecuta con acceso al servicio del host.

## Verification Evidence

Las rutas fail/pass/e2e contienen el close_check original literal (EXIT=4 por selector ausente), el resultado posterior literal y el control específico. `could_not_run` observado: 0 en la ejecución cerrada.
