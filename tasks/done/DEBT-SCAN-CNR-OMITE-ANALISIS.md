---
id: DEBT-SCAN-CNR-OMITE-ANALISIS
kind: debt
title: "El resumen omite analisis sin datos utilizables o fallidos"
status: done
closed_at: 2026-09-29
closure_type: fixed
evidence:
  pass: tasks/evidence/DEBT-SCAN-CNR-OMITE-ANALISIS/pass.txt
  fail: tasks/evidence/DEBT-SCAN-CNR-OMITE-ANALISIS/fail.txt
  e2e: tasks/evidence/DEBT-SCAN-CNR-OMITE-ANALISIS/e2e.txt
severity: P2
origin: detected
detector: {"rule": "adversarial-audit/DEBT-SCAN-CNR-OMITE-ANALISIS", "confidence": 1.0}
satd_family: BLIND_INSTRUMENT
created: 2026-09-29
close_check: {"cmd": "python3 -m pytest tests/test_auditoria_bb_regresiones.py::test_scan_cnr_analisis_fallido -q", "expect": "exit_zero"}
---

## Hallazgo y evidencia

Auditoría del commit `72d190d`. Código: `bin/bb:1307`.

Dos objetos JSON válidos pero sin campos producen mensajes sin ventana con dato y rc=0. El rótulo H6 malformed JSON del artefacto original es impreciso: los objetos son válidos. Los manejadores de error Python tampoco incrementan CNR.

Reproducción `H6`: `tasks/evidence/AUDIT-BB-2026-09-29/reproduce.py`; salida literal en `observed.txt` del mismo directorio. Señales y watchdog simulados; ninguna acción sobre procesos reales.

## Plan de remediación

Propagar resultado explícito de cada análisis al contador: ejecutado sin hallazgo, hallazgo o imposible de evaluar. Validar campos y cobertura temporal; conservar diagnóstico de error. Evitar que un echo convierta fracaso en éxito.

## Criterio de cierre

Scan completo cuenta entradas inválidas, datos insuficientes y error del analizador; controles sanos conservan CNR=0. El estado final coincide con las secciones.

El `close_check` es una obligación futura: el test todavía debe implementarse. Su ausencia debe fallar; el reproductor histórico imprime defectos y su rc=0 NO verifica remediación. Antes de cerrar, guardar pass/fail/e2e reproducibles, comprobar el control contra `72d190d`, actualizar SPEC/README y verificar el proceso desplegado cuando corresponda.

## Coordinación

Orden y dependencias: `docs/PLAN-REMEDIACION-BB-2026-09-29.md`. Esta ficha queda abierta; no declara deuda aceptada ni remediación realizada.

## Cierre

El lector común valida JSONL, timestamps y campos de entrada antes del análisis. Registra datos corruptos, ventanas sin datos y series insuficientes por análisis. Los pipelines Python que fallan incrementan el mismo contador CNR, y el veredicto final afirma que el reporte no está limpio cuando CNR es distinto de cero. Los controles sanos mantienen disponible el camino de análisis.

H6 mostró JSON válido sin campos y CNR silencioso antes del cambio. `close_check` pasó con una prueba que ejecuta el `bb scan` completo: el comando informó muestras en ventana, registró la línea JSONL inválida y mostró `NO esta limpio`. `bash -n bin/bb`, `py_compile tools/scan_samples.py` e `inventario --check` pasaron. El smoke simula `journalctl`; las otras fuentes del scan son de solo lectura.


## Root Cause

El scan imprimía texto de insuficiencia o absorbía errores de analizadores sin sumar esas secciones a `could_not_run`.

## Regression Test

`python3 -m pytest tests/test_auditoria_bb_regresiones.py::test_scan_cnr_analisis_fallido -q`: La prueba ejecuta el CLI `bb scan` con JSONL inválido y analiza que CNR aumente y el informe declare que no está limpio.

## Verification Evidence

Resultados reproducibles: tasks/evidence/DEBT-SCAN-CNR-OMITE-ANALISIS/e2e.txt. La salida del `close_check` está en el archivo `pass.txt` de la misma ficha de evidencia; el control previo está en `fail.txt`.
