---
id: DEBT-SCAN-GPU-PROCESOS-FANTASMA
kind: debt
title: "La alarma GPU conserva procesos ausentes y confunde idle con fallback"
status: done
closed_at: 2026-09-29
closure_type: fixed
evidence:
  pass: tasks/evidence/DEBT-SCAN-GPU-PROCESOS-FANTASMA/pass.txt
  fail: tasks/evidence/DEBT-SCAN-GPU-PROCESOS-FANTASMA/fail.txt
  e2e: tasks/evidence/DEBT-SCAN-GPU-PROCESOS-FANTASMA/e2e.txt
severity: P2
origin: detected
detector: {"rule": "adversarial-audit/DEBT-SCAN-GPU-PROCESOS-FANTASMA", "confidence": 1.0}
satd_family: BLIND_INSTRUMENT
created: 2026-09-29
close_check: {"cmd": "python3 -m pytest tests/test_auditoria_bb_regresiones.py::test_scan_gpu_vacia_invalida -q", "expect": "exit_zero"}
---

## Hallazgo y evidencia

Auditoría del commit `72d190d`. Código: `bin/bb:1423`.

Una lista `gpu_procs` vacía no invalidaba la caché; tres muestras podían atribuir memoria a `already-exited`. La prueba tampoco demostraba fallback real.

Reproducción histórica H5: `tasks/evidence/AUDIT-BB-2026-09-29/reproduce.py`; resultado guardado en `observed.txt`. Control y salida conservados en `tasks/evidence/DEBT-SCAN-GPU-PROCESOS-FANTASMA/fail.txt`.

## Remediación y cierre

La caché distingue campo ausente de lista vacía, invalida listas vacías o inválidas y limita la antigüedad. `bb scan` atribuye fallback solo con solicitudes activas y evidencia de trabajo CPU del mismo PID y boot. Una correlación insuficiente incrementa `could_not_run`; GPU ociosa no se etiqueta como fallback.

El `close_check` corre el `bb scan` completo con datos temporales: `1 passed`. Regresiones: `10 passed`; suites de telemetría térmica: `121 passed`. Sintaxis, compilación Python e inventario pasaron. Ver salidas en `tasks/evidence/DEBT-SCAN-GPU-PROCESOS-FANTASMA/`.

El código está cerrado en el repositorio; `bb scan` y el productor térmico aún requieren despliegue y comprobación en vivo.


## Root Cause

Una lista GPU vacía no invalidaba la caché de procesos y la utilización cero se interpretaba sin demostrar solicitudes activas ni trabajo CPU del PID.

## Regression Test

`python3 -m pytest tests/test_auditoria_bb_regresiones.py::test_scan_gpu_vacia_invalida -q`: La prueba ejecuta el CLI `bb scan` ante caché vaciada, campo ausente, idle, incertidumbre CPU y correlación positiva del mismo PID/boot.

## Verification Evidence

Resultados reproducibles: tasks/evidence/DEBT-SCAN-GPU-PROCESOS-FANTASMA/e2e.txt. La salida del `close_check` está en el archivo `pass.txt` de la misma ficha de evidencia; el control previo está en `fail.txt`.
