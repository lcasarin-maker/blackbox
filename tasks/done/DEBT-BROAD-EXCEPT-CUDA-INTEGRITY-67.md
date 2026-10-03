---
id: DEBT-BROAD-EXCEPT-CUDA-INTEGRITY-67
kind: task
domain: VERDICT
title: "Revisar broad-except en cuda_integrity.py:67"
status: done
closure_type: fixed
closed_at: 2026-10-03
severity: P2
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-10-02
close_check: {"cmd": "python3 -m pytest -q tests/test_debt_registration_controls.py::test_debt_broad_except_cuda_integrity_67", "expect": "exit_zero", "porque": "Auditar el límite de captura y ejecutar errores primarios/cleanup/cancelación relevantes. Preservar causa y errores de colección; no perder recursos ni convertir fallo en éxito. Limitar los tipos si es correcto, o conservar captura amplia cuando proteja teardown con razón explícita. Control negativo: excepción real inyectada que el sujeto registra/propaga y variante que la silencia debe fallar. La amplitud por sí sola no prueba defecto."}
evidence:
  fail: tasks/evidence/DEBT-BROAD-EXCEPT-CUDA-INTEGRITY-67.fail.txt
  pass: tasks/evidence/DEBT-BROAD-EXCEPT-CUDA-INTEGRITY-67.pass.txt
  e2e: tasks/evidence/DEBT-BROAD-EXCEPT-CUDA-INTEGRITY-67.e2e.txt
reason: "CERRADO: se validó que la captura continúa con los otros slots, vacía el registro y devuelve los errores de liberación."
---

## Root Cause

Cada slot independiente debe intentarse liberar aunque falle otro. El catch agrega el error y el finally elimina el slot incierto para prevenir doble free; después se recogen los errores de sync.

## Regression Test

`tests/test_debt_registration_controls.py::test_debt_broad_except_cuda_integrity_67` inyecta fallos en el sitio revisado y comprueba propagación/JSON de fallo, cleanup completo, ausencia de doble free y notas del cleanup. El control negativo temporal reemplazó el recolector por una versión silenciosa; la aserción de cleanup falló.

## Verification Evidence

Las salidas literales antes/después y la corrida e2e están enlazadas en `tasks/evidence/DEBT-BROAD-EXCEPT-CUDA-INTEGRITY-67.{fail,pass,e2e}.txt`. Los siete selectores pasan; la suite fake-only de CUDA/cgroup pasa (90 pruebas combinadas), sin hardware CUDA ni servicios.

## Registro y responsable

Registro solicitado por Luis el 2026-10-02. Responsable: coordinación de Blackbox. Revisión y pruebas completadas en el sujeto.

## Evidencia y alcance

Sitio: `tools/cuda_integrity.py:67`; función/contexto: cleanup_slots.

```text
except Exception as exc:
            errors.append(f"pointer {ptr_key}: {exc}")
```

Clasificación: captura amplia justificada por cleanup, estado incierto o frontera estructurada. Se conserva y queda cubierta por inyección fake.

Fuentes: tools/cuda_integrity.py:67.

## Criterio de cierre y control negativo

Auditar el límite de captura y ejecutar errores primarios/cleanup/cancelación relevantes. Preservar causa y errores de colección; no perder recursos ni convertir fallo en éxito. Limitar los tipos si es correcto, o conservar captura amplia cuando proteja teardown con razón explícita. Control negativo: excepción real inyectada que el sujeto registra/propaga y variante que la silencia debe fallar. La amplitud por sí sola no prueba defecto.

## Estado del verificador

La ficha quedó cerrada tras ejecutar el selector declarado y verificar inyecciones de error y control negativo en el sujeto.

Conservar comandos, salida literal y could_not_run incluso cero; una ejecución skipped o inaccesible deja el cierre pendiente. Reutilizar instrumentos nativos y pruebas existentes antes de crear código.
