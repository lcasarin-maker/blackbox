---
id: DEBT-COVERAGE-TARGETS-BIN-USABLE-01
kind: task
domain: VERDICT
title: "Revisar alcance de cobertura tools y exclusión de bin/bb-usable"
severity: P2
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-10-02
close_check: {"cmd": "python3 -m pytest -q tests/test_debt_registration_controls.py::test_debt_coverage_targets_bin_usable_01", "expect": "exit_zero", "porque": "Medir la cobertura efectiva del ejecutable Python bin/bb-usable con sus controles existentes o declarar su instrumento específico con comandos y denominador. Actualizar alcance/documentación contra archivos reales; no afirmar cobertura del repo desde tools. Control negativo: mutación del sujeto fuera del alcance debe ser detectada por su instrumento. Conservar exclusiones válidas con razón y revisión, sin inventar dependencias."}
status: done
closed_at: 2026-10-03
closure_type: fixed
reason: "La suite independiente carga el ejecutable extensionless con SourceFileLoader y Coverage.py lo mide como bin/bb-usable; el target tools queda sin cambio de política y sus 23 módulos quedan contados correctamente."
evidence: {"pass":"tasks/evidence/DEBT-COVERAGE-TARGETS-BIN-USABLE-01.pass.txt","fail":"tasks/evidence/DEBT-COVERAGE-TARGETS-BIN-USABLE-01.fail.txt","e2e":"tasks/evidence/DEBT-COVERAGE-TARGETS-BIN-USABLE-01.e2e.txt"}
---

## Registro y responsable

Registro solicitado por Luis el 2026-10-02. Responsable: coordinación de Blackbox. La revisión del instrumento y su control negativo quedó verificada en esta ficha.

## Evidencia y alcance

`.simplecode/corpus_exempt.yaml` fija coverage_targets a tools y declara bin/bb-usable fuera del detector Python por carecer de extensión .py. Los comentarios históricos dicen tres archivos Python, mientras el inventario actual contiene 23 módulos tools. Las pruebas de bb-usable existen pero el porcentaje tools no mide ese ejecutable.

Fuentes: .simplecode/corpus_exempt.yaml, bin/bb-usable, tests/test_bb_usable.py.

## Criterio de cierre y control negativo

Medir la cobertura efectiva del ejecutable Python bin/bb-usable con sus controles existentes o declarar su instrumento específico con comandos y denominador. Actualizar alcance/documentación contra archivos reales; no afirmar cobertura del repo desde tools. Control negativo: mutación del sujeto fuera del alcance debe ser detectada por su instrumento. Conservar exclusiones válidas con razón y revisión, sin inventar dependencias.

## Estado del verificador

El selector close_check pasó y la evidencia separa la ejecución previa, posterior y el control mutante.

## Root Cause

El comentario decía que el inventario Python eran tres archivos y confundía la autodetección general de tools con la cobertura efectiva del ejecutable extensionless; tests/test_bb_usable.py ya carga bin/bb-usable con SourceFileLoader, y Coverage.py 7.15.4 lo incluye al medir --source=bin.

## Regression Test

El selector ejecuta coverage run --branch --source=bin -m pytest tests/test_bb_usable.py, exige que el reporte enumere bin/bb-usable y demuestra que una copia mutante que devuelve -1.0 falla el control PSI positivo existente.

## Verification Evidence

Las rutas fail/pass/e2e contienen salidas literales. El reporte de cobertura identifica 103 sentencias, 4 misses, 36 ramas, 4 parciales y 94%; el intento sandbox sin sockets tuvo 2 fallos de permiso y la repetición con acceso al host pasó 27/27. No se modificó el ejecutable bin/bb-usable.
