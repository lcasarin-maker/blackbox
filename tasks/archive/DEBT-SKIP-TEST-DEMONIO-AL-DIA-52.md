---
id: DEBT-SKIP-TEST-DEMONIO-AL-DIA-52
kind: task
domain: VERDICT
title: "Revisar skip en test_demonio_al_dia.py:52"
severity: P2
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-10-02
close_check: {"cmd": "python3 -m pytest -q tests/test_debt_registration_controls.py::test_debt_skip_test_demonio_al_dia_52", "expect": "exit_zero", "porque": "Ejecutar la rama del sujeto que hoy puede quedar skipped con fixture reproducible o entorno requerido identificado. Un informe con skip no se declara limpio. Control negativo: quitar la capacidad/fixture produce could_not_run visible; romper el comportamiento real hace fallar la prueba. Conservar el skip si corresponde, con razón, responsable y disparador revisables; no quitarlo para forzar éxito."}
status: done
closed_at: 2026-10-03
closure_type: fixed
reason: "La prueba de integración corre con acceso al systemd del host; el skip informa COULD_NOT_RUN, owner y trigger cuando falta ese acceso."
evidence: {"pass":"tasks/evidence/DEBT-SKIP-TEST-DEMONIO-AL-DIA-52.pass.txt","fail":"tasks/evidence/DEBT-SKIP-TEST-DEMONIO-AL-DIA-52.fail.txt","e2e":"tasks/evidence/DEBT-SKIP-TEST-DEMONIO-AL-DIA-52.e2e.txt"}
---

## Registro y responsable

Registro solicitado por Luis el 2026-10-02. Responsable: coordinación de Blackbox. El defecto del instrumento quedó corregido y el close_check pasó con la precondición correspondiente.

## Evidencia y alcance

Sitio: `tests/test_demonio_al_dia.py:52`; función/contexto: module.

```text
pytest.mark.skipif(
    not _hay_unit(), reason=f"{UNIT} no esta corriendo en esta maquina")
```

Clasificación: revisión de una exclusión/captura, no bug demostrado. No retirar automáticamente una protección o cleanup.

Fuentes: tests/test_demonio_al_dia.py:52.

## Criterio de cierre y control negativo

Ejecutar la rama del sujeto que hoy puede quedar skipped con fixture reproducible o entorno requerido identificado. Un informe con skip no se declara limpio. Control negativo: quitar la capacidad/fixture produce could_not_run visible; romper el comportamiento real hace fallar la prueba. Conservar el skip si corresponde, con razón, responsable y disparador revisables; no quitarlo para forzar éxito.

## Estado del verificador

El selector close_check pasó en su entorno requerido y no reportó skip ni COULD_NOT_RUN. Las salidas originales y posteriores están en las tres rutas evidence.

## Root Cause

La prueba de integración corre con acceso al systemd del host; el skip informa COULD_NOT_RUN, owner y trigger cuando falta ese acceso.

## Regression Test

El selector registrado ejecuta la rama afectada del test real y exige salida sin skip ni COULD_NOT_RUN. Los casos de permisos inyectan PermissionError/os.access(False) de manera acotada; PII prueba runtime ausente y contador ausente; los controles de racha usan el corpus real positivo y negativo; demonio ejecuta con acceso al servicio del host.

## Verification Evidence

Las rutas fail/pass/e2e contienen el close_check original literal (EXIT=4 por selector ausente), el resultado posterior literal y el control específico. `could_not_run` observado: 0 en la ejecución cerrada.
