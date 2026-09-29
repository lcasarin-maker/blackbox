---
id: "DEBT-TERMICA-DRY-RUN-ACTUA"
kind: "debt"
title: "La simulacion termica puede pausar procesos y salir"
status: done
closed_at: 2026-09-29
closure_type: fixed
evidence:
  pass: tasks/evidence/DEBT-TERMICA-DRY-RUN-ACTUA/pass.txt
  fail: tasks/evidence/DEBT-TERMICA-DRY-RUN-ACTUA/fail.txt
  e2e: tasks/evidence/DEBT-TERMICA-DRY-RUN-ACTUA/e2e.txt
severity: "P1"
origin: "detected"
detector: {"rule": "adversarial-audit/DEBT-TERMICA-DRY-RUN-ACTUA", "confidence": 1.0}
satd_family: "BLIND_INSTRUMENT"
created: "2026-09-29"
close_check: {"cmd": "python3 -m pytest tests/test_auditoria_bb_regresiones.py::test_termica_dry_run_sin_senales -q", "expect": "exit_zero"}
---

## Hallazgo y evidencia

Auditoría del commit `72d190d`. Código: `tools/atom_gpu_telemetry.py:1322`.

main con --dry-run --once y alarma simulada llama os.kill con SIGSTOP. El help actual solo promete no escribir JSONL; la simulación sigue teniendo efectos sobre procesos.

Reproducción `H8`: `tasks/evidence/AUDIT-BB-2026-09-29/reproduce.py`; salida literal en `observed.txt` del mismo directorio. Señales y watchdog simulados; ninguna acción sobre procesos reales.

## Plan de remediación

Separar permiso de actuar del permiso de escribir. dry-run nunca envía señales; definir once como observación o asegurar ciclo de recuperación si se permite actuar. Probar main real con interceptores de señales.

## Criterio de cierre

dry-run, combinado o no con once, produce cero señales; el servicio normal conserva pausa y reanudación verificables.

El `close_check` es una obligación futura: el test todavía debe implementarse. Su ausencia debe fallar; el reproductor histórico imprime defectos y su rc=0 NO verifica remediación. Antes de cerrar, guardar pass/fail/e2e reproducibles, comprobar el control contra `72d190d`, actualizar SPEC/README y verificar el proceso desplegado cuando corresponda.

## Coordinación

Orden y dependencias: `docs/PLAN-REMEDIACION-BB-2026-09-29.md`. Esta ficha queda abierta; no declara deuda aceptada ni remediación realizada.

## Cierre

`muestrear` separa ahora el permiso de actuar del de escribir. En `--dry-run`, la mitigación emite `mitigacion_simulada` con la acción y los PIDs previstos, sin enviar señales ni modificar el conjunto de procesos pausados. El modo normal mantiene la pausa y reanudación reales.

Prueba roja: ambas variantes reprodujeron `SIGSTOP` antes del arreglo. `close_check` verde: 2 pruebas aprobadas. Suite térmica relacionada: 121 pruebas aprobadas. El test sustituye `os.kill`; ninguna señal se envió a procesos reales. No se desplegó la unidad del servicio en este cierre.
