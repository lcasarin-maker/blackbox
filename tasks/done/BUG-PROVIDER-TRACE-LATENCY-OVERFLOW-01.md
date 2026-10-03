---
id: BUG-PROVIDER-TRACE-LATENCY-OVERFLOW-01
kind: task
domain: VERDICT
title: "Latencia entera enorme debe producir unknown y no OverflowError"
status: done
closed_at: 2026-10-02
closure_type: fixed
reason: "Validación acotada previa a conversión flotante; JSON enorme produce unknown."
evidence: {"pass": "tasks/evidence/BUG-PROVIDER-TRACE-LATENCY-OVERFLOW-01.pass.txt", "fail": "tasks/evidence/BUG-PROVIDER-TRACE-LATENCY-OVERFLOW-01.fail.txt", "e2e": "tasks/evidence/BUG-PROVIDER-TRACE-LATENCY-OVERFLOW-01.e2e.txt"}
severity: P2
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-10-02
close_check: {"cmd": "python3 -m pytest -q tests/test_debt_registration_controls.py::test_bug_provider_trace_latency_overflow_01", "expect": "exit_zero", "porque": "La entrada enorme produce unknown, una latencia negativa o no finita también, una latencia válida conserva pass y GPU→CPU sigue block. CLI imprime JSON con contadores y ningún traceback. Control negativo: versión previa reproduce OverflowError. Cubrir límites de enteros y bool sin conversión flotante insegura."}
---

## Registro y responsable

Registro solicitado por Luis el 2026-10-02. Responsable: coordinación de Blackbox. Defecto confirmado.

## Evidencia y alcance

`analyze_lines` con eventos request/worker/provider válidos y milliseconds=10**400 termina con `OverflowError: int too large to convert to float` en `math.isfinite`. Reproducido el 2026-10-02; no requiere workload ni GPU. Relacionada con FEATURE-FORUM-PROVIDER-FALLBACK-REGRESSION-01; esta ficha sigue el defecto concreto del instrumento.

Fuentes: tools/provider_trace.py:135, tasks/backlog/FEATURE-FORUM-PROVIDER-FALLBACK-REGRESSION-01.md.

## Criterio de cierre y control negativo

La entrada enorme produce unknown, una latencia negativa o no finita también, una latencia válida conserva pass y GPU→CPU sigue block. CLI imprime JSON con contadores y ningún traceback. Control negativo: versión previa reproduce OverflowError. Cubrir límites de enteros y bool sin conversión flotante insegura.

## Estado del verificador

La ficha permanece abierta. El test selector del close_check es una especificación pendiente, no una prueba existente ni un resultado ejecutado. Implementarlo exige comprobar el sujeto y su control negativo; la existencia de archivos o esta ficha no basta para cerrar.

Conservar comandos, salida literal y could_not_run incluso cero; una ejecución skipped o inaccesible deja el cierre pendiente. Reutilizar instrumentos nativos y pruebas existentes antes de crear código.

## Root Cause

math.isfinite convierte los enteros a float antes de comprobar el rango y lanza OverflowError sobre 10**400.

## Regression Test

El selector declarado ejecuta CLI JSON sobre enteros enormes de ambos signos, bool, valores negativos, infinito y NaN; valida unknown y could_not_run=0. Valores válidos conservan pass y la fixture de respawn GPU→CPU conserva block.

## Verification Evidence

La prueba nueva falla con OverflowError sobre el código anterior y pasa después. El subconjunto del proveedor también pasa; salidas literales en evidence.
