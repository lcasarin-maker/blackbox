---
id: DEBT-BROAD-EXCEPT-CGROUP-REPRO-113
kind: task
domain: VERDICT
title: "Revisar broad-except en cgroup_repro.py:113"
status: done
closure_type: fixed
closed_at: 2026-10-03
severity: P2
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-10-02
close_check: {"cmd": "python3 -m pytest -q tests/test_debt_registration_controls.py::test_debt_broad_except_cgroup_repro_113", "expect": "exit_zero", "porque": "Auditar el límite de captura y ejecutar errores primarios/cleanup/cancelación relevantes. Preservar causa y errores de colección; no perder recursos ni convertir fallo en éxito. Limitar los tipos si es correcto, o conservar captura amplia cuando proteja teardown con razón explícita. Control negativo: excepción real inyectada que el sujeto registra/propaga y variante que la silencia debe fallar. La amplitud por sí sola no prueba defecto."}
evidence:
  fail: tasks/evidence/DEBT-BROAD-EXCEPT-CGROUP-REPRO-113.fail.txt
  pass: tasks/evidence/DEBT-BROAD-EXCEPT-CGROUP-REPRO-113.pass.txt
  e2e: tasks/evidence/DEBT-BROAD-EXCEPT-CGROUP-REPRO-113.e2e.txt
reason: "CERRADO: la falla primaria CUDA sobrevive a errores de free/sync, se intenta sync tras un free fallido y el worker conserva el reporte estructurado; cancelación se propaga tras el cleanup."
---

## Root Cause

La ruta CUDA usaba finally con una liberación que podía lanzar antes de sincronizar; el cleanup podía ocultar el error de asignación y omitir sync tras un cudaFree fallido. La captura amplia del worker es necesaria para devolver estado de fallo estructurado. La ruta de liberación ahora agrega errores secundarios y sincroniza aunque free falle.

## Regression Test

`tests/test_debt_registration_controls.py::test_debt_broad_except_cgroup_repro_113` inyecta fallos en el sitio revisado y comprueba propagación/JSON de fallo, cleanup completo, ausencia de doble free y notas del cleanup. El control negativo temporal reemplazó el recolector por una versión silenciosa; la aserción de cleanup falló.

## Verification Evidence

Las salidas literales antes/después y la corrida e2e están enlazadas en `tasks/evidence/DEBT-BROAD-EXCEPT-CGROUP-REPRO-113.{fail,pass,e2e}.txt`. Los siete selectores pasan; la suite fake-only de CUDA/cgroup pasa (90 pruebas combinadas), sin hardware CUDA ni servicios.

## Registro y responsable

Registro solicitado por Luis el 2026-10-02. Responsable: coordinación de Blackbox. Revisión y pruebas completadas en el sujeto.

## Evidencia y alcance

Sitio: `tools/cgroup_repro.py:113`; función/contexto: cuda_worker.

```text
except Exception as exc:
        logging.error("Allocation worker failed: %s", exc)
        print(json.dumps({"phase": "error", "error": f"{type(exc).__name__}: {exc}"}), flush=True)
        return 33
```

Clasificación: bug confirmado de preservación del error primario durante teardown; la captura amplia del worker es una frontera válida para informar el fallo.

Fuentes: tools/cgroup_repro.py:113.

## Criterio de cierre y control negativo

Auditar el límite de captura y ejecutar errores primarios/cleanup/cancelación relevantes. Preservar causa y errores de colección; no perder recursos ni convertir fallo en éxito. Limitar los tipos si es correcto, o conservar captura amplia cuando proteja teardown con razón explícita. Control negativo: excepción real inyectada que el sujeto registra/propaga y variante que la silencia debe fallar. La amplitud por sí sola no prueba defecto.

## Estado del verificador

La ficha quedó cerrada tras ejecutar el selector declarado y verificar inyecciones de error y control negativo en el sujeto.

Conservar comandos, salida literal y could_not_run incluso cero; una ejecución skipped o inaccesible deja el cierre pendiente. Reutilizar instrumentos nativos y pruebas existentes antes de crear código.
