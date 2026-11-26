---
id: BUG-COVERAGE-CLI-SUBPROCESS-01
kind: bug
domain: VERDICT
title: "Medición de CLI hijo ausente tras retirar exclusiones de entrypoints"
status: done
closed_at: 2026-10-03
closure_type: fixed
closure_reason: "El entrypoint hijo se mide con soporte nativo y su control sin patch detecta la omisión; cleanup 283 sentencias/88 ramas, 100%."
evidence:
  fail: tasks/evidence/BUG-COVERAGE-CLI-SUBPROCESS-01/fail.txt
  pass: tasks/evidence/BUG-COVERAGE-CLI-SUBPROCESS-01/pass.txt
  e2e: tasks/evidence/BUG-COVERAGE-CLI-SUBPROCESS-01/e2e.txt
severity: P2
origin: detected
detector: {"rule": "coverage: missing child entrypoints and cleanup statements", "confidence": 1.0}
satd_family: BLIND_INSTRUMENT
created: 2026-10-03
close_check: {"cmd": "python3 -m pytest -q tests/test_debt_registration_controls.py::test_bug_coverage_cli_subprocess_01", "expect": "exit_zero", "porque": "Medir entrypoint real de inventario en proceso hijo; el mismo comando sin patch subprocess pierde esa línea. Mantener umbral y sujetos."}
---

## Root Cause

Los controles CLI ejecutaban el programa real, pero coverage sólo medía el intérprete padre. La suite global pasó 846 pruebas y la medición con ramas dio 99.12%, con diez entrypoints sin medir. También faltaban diez sentencias nuevas del cleanup: se añaden pruebas reales de sincronización, fallo y cancelación, sin cambiar la fuente ni excluir caminos.

## Regression Test

Selector ejecuta el control existente del CLI inventario bajo coverage y comprueba la línea del entrypoint. Ejecuta una segunda medición con la configuración defectuosa sin patch; la línea queda sin medir. CUDA/PyTorch se prueban con interfaces simuladas: cancelación en liberación conserva excepción y sincroniza una vez, fallo ordinario devuelve error y nunca after_release. No hay carga GPU real.

## Verification Evidence

La falla global previa está conservada en fail.txt. Se reutiliza `[run] patch = subprocess` de coverage 7.15.4; el archivo de estado vive en la carpeta local ya existente. No se baja el watermark ni se añaden omisiones. Registrar positivo y cobertura conjunta antes del cierre.

57 passed, 13 deselected (selección dirigida), cgroup_repro 283 sentencias/88 ramas con 0 misses/0 partials y 100.00%. El selector positivo y negativo pasa. La medición global consolidada se registra al aterrizar las olas restantes.
