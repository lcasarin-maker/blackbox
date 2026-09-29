---
id: DEBT-SCAN-VENTANA-INCONSISTENTE
kind: debt
title: "El scan mezcla la ventana solicitada con todo el historial"
status: done
closed_at: 2026-09-29
closure_type: fixed
evidence:
  pass: tasks/evidence/DEBT-SCAN-VENTANA-INCONSISTENTE/pass.txt
  fail: tasks/evidence/DEBT-SCAN-VENTANA-INCONSISTENTE/fail.txt
  e2e: tasks/evidence/DEBT-SCAN-VENTANA-INCONSISTENTE/e2e.txt
severity: P2
origin: detected
detector: {"rule": "adversarial-audit/DEBT-SCAN-VENTANA-INCONSISTENTE", "confidence": 1.0}
satd_family: BLIND_INSTRUMENT
created: 2026-09-29
close_check: {"cmd": "python3 -m pytest tests/test_auditoria_bb_regresiones.py::test_scan_respeta_ventana -q", "expect": "exit_zero"}
---

## Hallazgo y evidencia

Auditoría del commit `72d190d`. Código: `bin/bb:1184`.

El bloque real de red/CPU informa CPU 100% con muestras exclusivamente del año 2000. Prueba del bloque extraído: no ejecuta el scan completo. Su llamador no pasa since. Memoria, zombis y apps también leen toda la retención.

Reproducción `H4`: `tasks/evidence/AUDIT-BB-2026-09-29/reproduce.py`; salida literal en `observed.txt` del mismo directorio. Señales y watchdog simulados; ninguna acción sobre procesos reales.

## Plan de remediación

Reutilizar un lector temporal común para JSONL y pasar inicio y fin explícitos. Normalizar zonas horarias, ordenar registros y separar boot e identidad de contadores. Aplicarlo a todas las secciones que prometen ventana.

## Criterio de cierre

Scan completo excluye incidentes anteriores y futuros; incluye límites definidos; cruces de boot y resets nunca producen tasas falsas.

El `close_check` es una obligación futura: el test todavía debe implementarse. Su ausencia debe fallar; el reproductor histórico imprime defectos y su rc=0 NO verifica remediación. Antes de cerrar, guardar pass/fail/e2e reproducibles, comprobar el control contra `72d190d`, actualizar SPEC/README y verificar el proceso desplegado cuando corresponda.

## Coordinación

Orden y dependencias: `docs/PLAN-REMEDIACION-BB-2026-09-29.md`. Esta ficha queda abierta; no declara deuda aceptada ni remediación realizada.

## Cierre

`bb scan` prepara una vista JSONL temporal entre el epoch solicitado y el inicio del informe. Ordena por timestamp con zona horaria, descarta registros anteriores y futuros, y conserva para tasas CPU/red solo campos del boot más reciente. Señala como `could_not_run` los contadores sin boot, resets y timestamps duplicados. Todas las secciones de muestras blackbox y telemetría térmica consumen esa vista.

H4 calculó 100% de CPU usando datos del año 2000 antes del cambio. `close_check` y prueba de integración del CLI pasaron; la prueba comprueba que el resultado contiene exactamente las dos muestras actuales y excluye una antigua y una futura. `bash -n bin/bb`, `py_compile tools/scan_samples.py` e `inventario --check` pasaron.


## Root Cause

Varias secciones consumían todo el JSONL retenido, aunque el encabezado del informe prometía una ventana temporal acotada.

## Regression Test

`python3 -m pytest tests/test_auditoria_bb_regresiones.py::test_scan_respeta_ventana -q`: La prueba ejecuta el CLI `bb scan` y afirma que solo aparecen filas dentro del intervalo, excluyendo timestamps anteriores y futuros.

## Verification Evidence

Resultados reproducibles: tasks/evidence/DEBT-SCAN-VENTANA-INCONSISTENTE/e2e.txt. La salida del `close_check` está en el archivo `pass.txt` de la misma ficha de evidencia; el control previo está en `fail.txt`.
