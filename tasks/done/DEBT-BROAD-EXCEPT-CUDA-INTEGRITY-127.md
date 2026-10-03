---
id: DEBT-BROAD-EXCEPT-CUDA-INTEGRITY-127
kind: task
domain: VERDICT
title: "Revisar broad-except en cuda_integrity.py:127"
status: done
closure_type: fixed
closed_at: 2026-10-03
severity: P2
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-10-02
close_check: {"cmd": "python3 -m pytest -q tests/test_debt_registration_controls.py::test_debt_broad_except_cuda_integrity_127", "expect": "exit_zero", "porque": "Auditar el límite de captura y ejecutar errores primarios/cleanup/cancelación relevantes. Preservar causa y errores de colección; no perder recursos ni convertir fallo en éxito. Limitar los tipos si es correcto, o conservar captura amplia cuando proteja teardown con razón explícita. Control negativo: excepción real inyectada que el sujeto registra/propaga y variante que la silencia debe fallar. La amplitud por sí sola no prueba defecto."}
evidence:
  fail: tasks/evidence/DEBT-BROAD-EXCEPT-CUDA-INTEGRITY-127.fail.txt
  pass: tasks/evidence/DEBT-BROAD-EXCEPT-CUDA-INTEGRITY-127.pass.txt
  e2e: tasks/evidence/DEBT-BROAD-EXCEPT-CUDA-INTEGRITY-127.e2e.txt
reason: "CERRADO: se validó la conservación del primario y de la cancelación, junto con cleanup de cada puntero una sola vez y notas secundarias."
---

## Root Cause

La captura de BaseException conserva la excepción primaria mientras el finally intenta cleanup incluso ante cancelación. Los errores de liberación se adjuntan como notas y se relanza el primario con su traceback.

## Regression Test

`tests/test_debt_registration_controls.py::test_debt_broad_except_cuda_integrity_127` inyecta fallos en el sitio revisado y comprueba propagación/JSON de fallo, cleanup completo, ausencia de doble free y notas del cleanup. El control negativo temporal reemplazó el recolector por una versión silenciosa; la aserción de cleanup falló.

## Verification Evidence

Las salidas literales antes/después y la corrida e2e están enlazadas en `tasks/evidence/DEBT-BROAD-EXCEPT-CUDA-INTEGRITY-127.{fail,pass,e2e}.txt`. Los siete selectores pasan; la suite fake-only de CUDA/cgroup pasa (90 pruebas combinadas), sin hardware CUDA ni servicios.

## Registro y responsable

Registro solicitado por Luis el 2026-10-02. Responsable: coordinación de Blackbox. Revisión y pruebas completadas en el sujeto.

## Evidencia y alcance

Sitio: `tools/cuda_integrity.py:127`; función/contexto: run_worker.

```text
except BaseException as exc:
        primary_error = exc
        raise
```

Clasificación: captura amplia justificada por cleanup, estado incierto o frontera estructurada. Se conserva y queda cubierta por inyección fake.

Fuentes: tools/cuda_integrity.py:127.

## Criterio de cierre y control negativo

Auditar el límite de captura y ejecutar errores primarios/cleanup/cancelación relevantes. Preservar causa y errores de colección; no perder recursos ni convertir fallo en éxito. Limitar los tipos si es correcto, o conservar captura amplia cuando proteja teardown con razón explícita. Control negativo: excepción real inyectada que el sujeto registra/propaga y variante que la silencia debe fallar. La amplitud por sí sola no prueba defecto.

## Estado del verificador

La ficha quedó cerrada tras ejecutar el selector declarado y verificar inyecciones de error y control negativo en el sujeto.

Conservar comandos, salida literal y could_not_run incluso cero; una ejecución skipped o inaccesible deja el cierre pendiente. Reutilizar instrumentos nativos y pruebas existentes antes de crear código.
