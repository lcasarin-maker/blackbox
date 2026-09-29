---
id: "DEBT-WATCHDOG-PSI-ILEGIBLE-REARMA"
kind: "debt"
title: "PSI ilegible alimenta el watchdog durante un colapso declarado"
status: done
closed_at: 2026-09-29
closure_type: fixed
evidence:
  pass: tasks/evidence/DEBT-WATCHDOG-PSI-ILEGIBLE-REARMA/pass.txt
  fail: tasks/evidence/DEBT-WATCHDOG-PSI-ILEGIBLE-REARMA/fail.txt
  e2e: tasks/evidence/DEBT-WATCHDOG-PSI-ILEGIBLE-REARMA/e2e.txt
severity: "P1"
origin: "detected"
detector: {"rule": "adversarial-audit/DEBT-WATCHDOG-PSI-ILEGIBLE-REARMA", "confidence": 1.0}
satd_family: "BLIND_INSTRUMENT"
created: "2026-09-29"
close_check: {"cmd": "python3 -m pytest tests/test_auditoria_bb_regresiones.py::test_watchdog_colapso_psi_ilegible -q", "expect": "exit_zero"}
---

## Hallazgo y evidencia

Auditoría del commit `72d190d`. Código: `bin/bb-usable:282`.

Diez lecturas 99.0 seguidas de None terminan enviando WATCHDOG=1, aunque la racha conserva el estado de colapso.

Reproducción `H3`: `tasks/evidence/AUDIT-BB-2026-09-29/reproduce.py`; salida literal en `observed.txt` del mismo directorio. Señales y watchdog simulados; ninguna acción sobre procesos reales.

## Plan de remediación

Mantener retirada del latido durante un colapso declarado hasta medir recuperación suficiente. Distinguir sensor ilegible antes de un colapso del mismo fallo después de declarar acción.

## Criterio de cierre

Colapso seguido de None no alimenta; dos lecturas bajas recuperan; ausencia inicial de PSI no inventa colapso.

El `close_check` es una obligación futura: el test todavía debe implementarse. Su ausencia debe fallar; el reproductor histórico imprime defectos y su rc=0 NO verifica remediación. Antes de cerrar, guardar pass/fail/e2e reproducibles, comprobar el control contra `72d190d`, actualizar SPEC/README y verificar el proceso desplegado cuando corresponda.

## Coordinación

Orden y dependencias: `docs/PLAN-REMEDIACION-BB-2026-09-29.md`. Esta ficha queda abierta; no declara deuda aceptada ni remediación realizada.

## Cierre

Cuando PSI no se puede leer antes del umbral, el watchdog conserva su caricia y la racha alta continúa. Una vez declarado el colapso, PSI ilegible ya no devuelve el latido: solo dos lecturas bajas consecutivas limpian la racha, según la política existente. La ausencia inicial sigue sin inventar colapso.

H3 mostró 11 latidos antes del cambio. El `close_check` pasó. La suite `test_bb_usable.py` junto con la regresión dio 26 passed y 2 fallidas por `PermissionError: [Errno 1] Operation not permitted` al enlazar sockets Unix en el sandbox; están anotadas como `could_not_run`, no como fallas del producto. Sin despliegue del servicio.
