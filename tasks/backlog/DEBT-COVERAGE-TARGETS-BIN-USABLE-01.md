---
id: DEBT-COVERAGE-TARGETS-BIN-USABLE-01
kind: task
domain: VERDICT
title: "Revisar alcance de cobertura tools y exclusión de bin/bb-usable"
status: open
severity: P2
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-10-02
close_check: {"cmd": "python3 -m pytest -q tests/test_debt_registration_controls.py::test_debt_coverage_targets_bin_usable_01", "expect": "exit_zero", "porque": "Medir la cobertura efectiva del ejecutable Python bin/bb-usable con sus controles existentes o declarar su instrumento específico con comandos y denominador. Actualizar alcance/documentación contra archivos reales; no afirmar cobertura del repo desde tools. Control negativo: mutación del sujeto fuera del alcance debe ser detectada por su instrumento. Conservar exclusiones válidas con razón y revisión, sin inventar dependencias."}
---

## Registro y responsable

Registro solicitado por Luis el 2026-10-02. Responsable: coordinación de Blackbox. Trabajo o revisión pendiente; la presencia del marcador no demuestra por sí sola un defecto.

## Evidencia y alcance

`.simplecode/corpus_exempt.yaml` fija coverage_targets a tools y declara bin/bb-usable fuera del detector Python por carecer de extensión .py. Los comentarios históricos dicen tres archivos Python, mientras el inventario actual contiene 23 módulos tools. Las pruebas de bb-usable existen pero el porcentaje tools no mide ese ejecutable.

Fuentes: .simplecode/corpus_exempt.yaml, bin/bb-usable, tests/test_bb_usable.py.

## Criterio de cierre y control negativo

Medir la cobertura efectiva del ejecutable Python bin/bb-usable con sus controles existentes o declarar su instrumento específico con comandos y denominador. Actualizar alcance/documentación contra archivos reales; no afirmar cobertura del repo desde tools. Control negativo: mutación del sujeto fuera del alcance debe ser detectada por su instrumento. Conservar exclusiones válidas con razón y revisión, sin inventar dependencias.

## Estado del verificador

La ficha permanece abierta. El test selector del close_check es una especificación pendiente, no una prueba existente ni un resultado ejecutado. Implementarlo exige comprobar el sujeto y su control negativo; la existencia de archivos o esta ficha no basta para cerrar.

Conservar comandos, salida literal y could_not_run incluso cero; una ejecución skipped o inaccesible deja el cierre pendiente. Reutilizar instrumentos nativos y pruebas existentes antes de crear código.
