---
id: "DEBT-TERMICA-PAUSAS-PERDIDAS"
kind: "debt"
title: "Reiniciar la telemetria pierde los procesos que dejo pausados"
status: done
closed_at: 2026-09-29
closure_type: fixed
evidence:
  pass: tasks/evidence/DEBT-TERMICA-PAUSAS-PERDIDAS/pass.txt
  fail: tasks/evidence/DEBT-TERMICA-PAUSAS-PERDIDAS/fail.txt
  e2e: tasks/evidence/DEBT-TERMICA-PAUSAS-PERDIDAS/e2e.txt
severity: "P1"
origin: "detected"
detector: {"rule": "adversarial-audit/DEBT-TERMICA-PAUSAS-PERDIDAS", "confidence": 1.0}
satd_family: "BLIND_INSTRUMENT"
created: "2026-09-29"
close_check: {"cmd": "python3 -m pytest tests/test_auditoria_bb_regresiones.py::test_termica_recupera_pausas -q", "expect": "exit_zero"}
---

## Hallazgo y evidencia

Auditoría del commit `72d190d`. Código: `tools/atom_gpu_telemetry.py:1246`.

Pausa seguida de estado nuevo emite SIGSTOP y ningún SIGCONT. Es simulación de pérdida de estado, no reinicio real de servicio.

Reproducción `H7`: `tasks/evidence/AUDIT-BB-2026-09-29/reproduce.py`; salida literal en `observed.txt` del mismo directorio. Señales y watchdog simulados; ninguna acción sobre procesos reales.

## Plan de remediación

Registrar durablemente procesos pausados por este instrumento con boot y starttime. Recuperar y conciliar al arrancar; gestionar salida normal y fallo sin reanudar procesos ajenos o PID reutilizados.

## Criterio de cierre

Reinicio recupera propiedad de pausas; enfriamiento reanuda únicamente los sujetos propios; cubrir caída entre señal y persistencia.

El `close_check` es una obligación futura: el test todavía debe implementarse. Su ausencia debe fallar; el reproductor histórico imprime defectos y su rc=0 NO verifica remediación. Antes de cerrar, guardar pass/fail/e2e reproducibles, comprobar el control contra `72d190d`, actualizar SPEC/README y verificar el proceso desplegado cuando corresponda.

## Coordinación

Orden y dependencias: `docs/PLAN-REMEDIACION-BB-2026-09-29.md`. Esta ficha queda abierta; no declara deuda aceptada ni remediación realizada.

## Cierre

La telemetría guarda atómicamente el boot id, PID, `starttime_ticks`, pausas propias e intención de señal antes de actuar. Tras reiniciar, recupera procesos solo si coinciden boot y starttime; al enfriarse los reanuda después de revalidar identidad. Si el proceso cae entre SIGSTOP y confirmación, la intención durable permite enviar SIGCONT únicamente cuando el mismo proceso sigue en estado detenido. PIDs reutilizados y boots anteriores se descartan sin señal.

H7 reprodujo la pausa sin reanudación antes del cambio. El `close_check` pasó; suites térmicas relacionadas: 122 passed. La prueba intercepta SIGSTOP/SIGCONT y simula estado de `/proc`; no envió señales reales. El servicio no se desplegó ni reinició.
