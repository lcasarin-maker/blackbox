---
id: DEBT-SKIP-TEST-DEMONIO-AL-DIA-52
kind: task
domain: VERDICT
title: "Revisar skip en test_demonio_al_dia.py:52"
status: open
severity: P2
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-10-02
close_check: {"cmd": "python3 -m pytest -q tests/test_debt_registration_controls.py::test_debt_skip_test_demonio_al_dia_52", "expect": "exit_zero", "porque": "Ejecutar la rama del sujeto que hoy puede quedar skipped con fixture reproducible o entorno requerido identificado. Un informe con skip no se declara limpio. Control negativo: quitar la capacidad/fixture produce could_not_run visible; romper el comportamiento real hace fallar la prueba. Conservar el skip si corresponde, con razón, responsable y disparador revisables; no quitarlo para forzar éxito."}
---

## Registro y responsable

Registro solicitado por Luis el 2026-10-02. Responsable: coordinación de Blackbox. Trabajo o revisión pendiente; la presencia del marcador no demuestra por sí sola un defecto.

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

La ficha permanece abierta. El test selector del close_check es una especificación pendiente, no una prueba existente ni un resultado ejecutado. Implementarlo exige comprobar el sujeto y su control negativo; la existencia de archivos o esta ficha no basta para cerrar.

Conservar comandos, salida literal y could_not_run incluso cero; una ejecución skipped o inaccesible deja el cierre pendiente. Reutilizar instrumentos nativos y pruebas existentes antes de crear código.
