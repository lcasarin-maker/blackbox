---
id: "DEBT-GUARDIA-ARCHIVO-TARDIO"
kind: "debt"
title: "El guardian no reintenta abrir el archivo del dia tras un fallo"
status: done
closed_at: 2026-09-29
closure_type: fixed
evidence:
  pass: tasks/evidence/DEBT-GUARDIA-ARCHIVO-TARDIO/pass.txt
  fail: tasks/evidence/DEBT-GUARDIA-ARCHIVO-TARDIO/fail.txt
  e2e: tasks/evidence/DEBT-GUARDIA-ARCHIVO-TARDIO/e2e.txt
severity: "P1"
origin: "detected"
detector: {"rule": "adversarial-audit/DEBT-GUARDIA-ARCHIVO-TARDIO", "confidence": 1.0}
satd_family: "BLIND_INSTRUMENT"
created: "2026-09-29"
close_check: {"cmd": "python3 -m pytest tests/test_auditoria_bb_regresiones.py::test_guardia_archivo_tardio -q", "expect": "exit_zero"}
---

## Hallazgo y evidencia

Auditoría del commit `72d190d`. Código: `bin/bb-guardia-proceso:305`.

El archivo se crea tras el primer intento; tres ciclos después no existen eventos. ruta_actual cambia incluso cuando open falla, impidiendo nuevos intentos ese día.

Reproducción `H2`: `tasks/evidence/AUDIT-BB-2026-09-29/reproduce.py`; salida literal en `observed.txt` del mismo directorio. Señales y watchdog simulados; ninguna acción sobre procesos reales.

## Plan de remediación

Reintentar apertura mientras falte descriptor; manejar cambio de fecha, truncado y reemplazo del archivo. Informar antigüedad y ausencia de muestras en estado observable y bb status.

## Criterio de cierre

Archivo ausente al arranque y al cambio de fecha se consume cuando aparece; reemplazo y truncado recuperan lectura sin replay peligroso.

El `close_check` es una obligación futura: el test todavía debe implementarse. Su ausencia debe fallar; el reproductor histórico imprime defectos y su rc=0 NO verifica remediación. Antes de cerrar, guardar pass/fail/e2e reproducibles, comprobar el control contra `72d190d`, actualizar SPEC/README y verificar el proceso desplegado cuando corresponda.

## Coordinación

Orden y dependencias: `docs/PLAN-REMEDIACION-BB-2026-09-29.md`. Esta ficha queda abierta; no declara deuda aceptada ni remediación realizada.

## Cierre

El guardián reintenta abrir el archivo hasta que aparece, vuelve a abrir al cambiar de fecha, y detecta truncado y reemplazo por identidad de inode. En cada nueva generación comienza al final para evitar replay. La lectura binaria conserva offsets por byte y espera líneas completas antes de parsear. Los logs registran espera, conexión y reemplazo. Frescura, boot id e identidad PID siguen filtrando cada muestra procesable.

H2 reproduce tres polls sin eventos antes del arreglo. El `close_check` pasó; conjunto de regresión guardián: 22 passed. `py_compile`, `bash -n` e `inventario --check` pasaron. Sin despliegue del servicio.
