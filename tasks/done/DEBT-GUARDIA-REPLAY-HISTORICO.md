---
id: "DEBT-GUARDIA-REPLAY-HISTORICO"
kind: "debt"
title: "El guardian escala sobre muestras historicas sin validar identidad"
status: done
closed_at: 2026-09-29
closure_type: fixed
evidence:
  pass: tasks/evidence/DEBT-GUARDIA-REPLAY-HISTORICO/pass.txt
  fail: tasks/evidence/DEBT-GUARDIA-REPLAY-HISTORICO/fail.txt
  e2e: tasks/evidence/DEBT-GUARDIA-REPLAY-HISTORICO/e2e.txt
severity: "P1"
origin: "detected"
detector: {"rule": "adversarial-audit/DEBT-GUARDIA-REPLAY-HISTORICO", "confidence": 1.0}
satd_family: "BLIND_INSTRUMENT"
created: "2026-09-29"
close_check: {"cmd": "python3 -m pytest tests/test_auditoria_bb_regresiones.py::test_guardia_replay_no_actua -q", "expect": "exit_zero"}
---

## Hallazgo y evidencia

Auditoría del commit `72d190d`. Código: `bin/bb-guardia-proceso:305`.

Cuatro registros del año 2000 se procesan en un solo ciclo y producen aviso, SIGTERM y SIGKILL simulados. El riesgo de PID reutilizado se deduce del uso de os.kill(pid) sin starttime; no se provocó reutilización real.

Reproducción `H1`: `tasks/evidence/AUDIT-BB-2026-09-29/reproduce.py`; salida literal en `observed.txt` del mismo directorio. Señales y watchdog simulados; ninguna acción sobre procesos reales.

## Plan de remediación

Persistir cursor e identidad del archivo; rechazar muestras antiguas, duplicadas y de otro boot. Asociar PID con starttime y revalidar identidad y condición actual antes de cada señal. Garantizar tiempo real entre etapas aunque llegue un lote de muestras.

## Criterio de cierre

Reiniciar con historia acumulada no envía señales; PID reutilizado queda intacto; muestras nuevas sí escalan con intervalos verificables.

El `close_check` es una obligación futura: el test todavía debe implementarse. Su ausencia debe fallar; el reproductor histórico imprime defectos y su rc=0 NO verifica remediación. Antes de cerrar, guardar pass/fail/e2e reproducibles, comprobar el control contra `72d190d`, actualizar SPEC/README y verificar el proceso desplegado cuando corresponda.

## Coordinación

Orden y dependencias: `docs/PLAN-REMEDIACION-BB-2026-09-29.md`. Esta ficha queda abierta; no declara deuda aceptada ni remediación realizada.

## Cierre

Al conectar el guardian a un archivo, salta todo lo que ya estaba escrito. Reinicia la racha de escalada, solo procesa la muestra nueva más reciente por sondeo, y descarta muestras viejas, de otro boot, duplicadas o fuera de secuencia. Las muestras de `bb sample` incluyen boot id y `starttime_ticks`; se coteja identidad con `/proc` al evaluar y otra vez antes de cada señal.

H1 reprodujo el avance histórico hasta SIGTERM/SIGKILL antes del cambio. El `close_check` pasó; el conjunto de regresión del guardián dio 21 passed. `bash -n bin/bb` e `inventario --check` pasaron. El test intercepta señales. No se desplegó ni reinició el servicio; la unidad activa verificada en 2026-09-28 todavía requiere actualización en producción.
