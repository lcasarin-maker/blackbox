---
id: DEBT-BB-SAMPLE-SMI-QUERIES-WITHOUT-TIMEOUT-01
kind: task
domain: VERDICT
title: "Acotar todas las consultas NVIDIA de bb sample"
status: done
closed_at: 2026-10-04
closure_type: verified_code_fix
severity: P2
origin: detected
detector: {"rule": "bb-query-audit: blocking NVIDIA process queries and false-zero fallback", "confidence": 1.0}
satd_family: BLIND_INSTRUMENT
created: 2026-10-04
evidence:
  pass: tasks/evidence/CLOSURE-CONTROLS-2026-10-03/bb-smi-original-close-final-20261004.log
  fail: tasks/evidence/CLOSURE-CONTROLS-2026-10-03/bb-smi-original-negative-control.log
  e2e: tasks/evidence/CLOSURE-CONTROLS-2026-10-03/DEBT-BB-SAMPLE-SMI-QUERIES-WITHOUT-TIMEOUT-01-e2e-current.log
close_check: {"cmd": "python3 -m pytest -q tests/test_bb_bash.py::test_sample_all_smi_queries_are_bounded", "expect": "exit_zero", "porque": "Control sano conserva memoria/procesos reales; shim que bloquea query-compute-apps termina dentro del presupuesto explícito y comunica dato ausente, nunca cero falso. Mantener timeout de salud y no iniciar cargas GPU."}
---

## Evidencia

Durante la suite general del 2026-10-04, el proceso de `test_control_negativo_smi_dice_TIMEOUT_cuando_el_driver_se_cuelga` llevaba 59 segundos y un hijo del shim NVIDIA seguía en `sleep 30` tras 28 segundos. El test fija `BB_SMI_TIMEOUT_S=1`; `smi_salud` respeta ese límite, pero `gpu_mem_mib` y `gpu_procs` ejecutan `query-compute-apps` sin timeout. Un driver colgado prolonga también el muestreo. Esta es una deuda descubierta adicional; los 98 IDs originales conservan su alcance y close_check.

## Cambio requerido

Reutilizar el presupuesto de consulta existente en ambas rutas. Propagar fallo/timeout como ausencia y preservar cero real cuando una consulta exitosa no devuelve procesos. Revisar el resto de queries directas antes de cerrar. Evitar un segundo sistema de temporizadores.

## Validación de cierre

El close_check original pasó con control sano, fallo de consulta y shim bloqueado; conserva cero real y representa fallo como ausencia. Resultado y hash: `tasks/evidence/CLOSURE-CONTROLS-2026-10-03/bb-smi-original-close-final-20261004.log`.

La auditoría completa encontró 11 consultas ejecutables, todas con timeout; retiró `gpu_stat`, que carecía de callers, y acotó snapshot/accounting. Accounting comunica consulta fallida como COULD_NOT_RUN. Ver `smi-whole-file-query-audit.json`.

E2E del selector exacto (captura actual): `tasks/evidence/CLOSURE-CONTROLS-2026-10-03/DEBT-BB-SAMPLE-SMI-QUERIES-WITHOUT-TIMEOUT-01-e2e-current.log`. El test ejercita `bin/bb sample` con datos aislados y un shim `nvidia-smi`: query vacía exitosa, error rc9 y query bloqueada con `BB_SMI_TIMEOUT_S=1`. La prueba no usa hardware ni driver físicos; esa verificación queda COULD_NOT_RUN (CNR). El control negativo previo y el resultado previo de cobertura se conservan en sus rutas existentes.

`tools/piso_cobertura.sh` exit 0: `[bb-cobertura] bin/bb al 40.2% (piso 32.8%)`. No se cambiaron el piso ni las exclusiones. Esta ficha adicional está fuera del alcance original de 98; el cierre no acredita ninguna investigación hardware.

## Root Cause

Las consultas de procesos GPU carecían del timeout existente de salud NVIDIA. Un fallo de consulta se convertía además en cero por el fallback del muestreo. La revisión encontró otras consultas directas en snapshot/accounting y una función sin uso.

## Regression Test

`tests/test_bb_bash.py::test_sample_all_smi_queries_are_bounded` compara un resultado vacío exitoso, error rc9 y consulta bloqueada. El caso sano conserva cero; error y timeout quedan como ausencia dentro del presupuesto. El control sobre el código anterior falla y el selector final pasa.

## Verification Evidence

Las rutas evidence de la cabecera conservan el control negativo, el cierre literal (`1 passed in 4.52s`) y el piso de cobertura (`40.2%`, piso `32.8%`). `smi-whole-file-query-audit.json` registra 11 consultas ejecutables acotadas y la retirada de `gpu_stat`, sin callers. Ninguna modificación del piso ni exclusión adicional se aplicó.
