---
id: DEBT-SKIP-TEST-CONTROL-RACHA-118
kind: task
domain: VERDICT
title: "Revisar skip en test_control_racha.py:118"
severity: P2
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-10-02
close_check: {"cmd": "python3 -m pytest -q tests/test_debt_registration_controls.py::test_debt_skip_test_control_racha_118", "expect": "exit_zero", "porque": "Ejecutar la rama del sujeto que hoy puede quedar skipped con fixture reproducible o entorno requerido identificado. Un informe con skip no se declara limpio. Control negativo: quitar la capacidad/fixture produce could_not_run visible; romper el comportamiento real hace fallar la prueba. Conservar el skip si corresponde, con razón, responsable y disparador revisables; no quitarlo para forzar éxito."}
status: open
closed_at: 2026-10-03
closure_type: fixed
reason: "El corpus real de 22653 muestras está disponible y el control positivo devuelve LIMPIO; la ausencia queda como COULD_NOT_RUN con owner y trigger visibles."
evidence: {"pass":"tasks/evidence/DEBT-SKIP-TEST-CONTROL-RACHA-118.pass.txt","fail":"tasks/evidence/DEBT-SKIP-TEST-CONTROL-RACHA-118.fail.txt","e2e":"tasks/evidence/DEBT-SKIP-TEST-CONTROL-RACHA-118.e2e.txt"}
---

## Registro y responsable

Registro solicitado por Luis el 2026-10-02. Responsable: coordinación de Blackbox. El defecto del instrumento quedó corregido y el close_check pasó con la precondición correspondiente.

## Evidencia y alcance

Sitio: `tests/test_control_racha.py:118`; función/contexto: test_el_gate_sale_0_sobre_el_corpus_real.

```text
pytest.skip("sin corpus de muestras en esta maquina")
```

Clasificación: revisión de una exclusión/captura, no bug demostrado. No retirar automáticamente una protección o cleanup.

Fuentes: tests/test_control_racha.py:118.

## Criterio de cierre y control negativo

Ejecutar la rama del sujeto que hoy puede quedar skipped con fixture reproducible o entorno requerido identificado. Un informe con skip no se declara limpio. Control negativo: quitar la capacidad/fixture produce could_not_run visible; romper el comportamiento real hace fallar la prueba. Conservar el skip si corresponde, con razón, responsable y disparador revisables; no quitarlo para forzar éxito.

## Estado del verificador

El selector close_check pasó en su entorno requerido y no reportó skip ni COULD_NOT_RUN. Las salidas originales y posteriores están en las tres rutas evidence.

## Root Cause

El corpus real de 22653 muestras está disponible y el control positivo devuelve LIMPIO; la ausencia queda como COULD_NOT_RUN con owner y trigger visibles.

## Regression Test

El selector registrado ejecuta la rama afectada del test real y exige salida sin skip ni COULD_NOT_RUN. Los casos de permisos inyectan PermissionError/os.access(False) de manera acotada; PII prueba runtime ausente y contador ausente; los controles de racha usan el corpus real positivo y negativo; demonio ejecuta con acceso al servicio del host.

## Verification Evidence

Las rutas fail/pass/e2e contienen el close_check original literal (EXIT=4 por selector ausente), el resultado posterior literal y el control específico. `could_not_run` observado: 0 en la ejecución cerrada.
