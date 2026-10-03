---
id: DEBT-NOQA-BB-USABLE-249
kind: task
domain: VERDICT
title: "Revisar noqa en bb-usable:249"
status: done
closed_at: 2026-10-02
closure_type: fixed
reason: "Función local explícita preserva logging y elimina supresión E731."
evidence: {"pass": "tasks/evidence/DEBT-NOQA-BB-USABLE-249.pass.txt", "fail": "tasks/evidence/DEBT-NOQA-BB-USABLE-249.fail.txt", "e2e": "tasks/evidence/DEBT-NOQA-BB-USABLE-249.e2e.txt"}
severity: P2
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-10-02
close_check: {"cmd": "python3 -m pytest -q tests/test_debt_registration_controls.py::test_debt_noqa_bb_usable_249", "expect": "exit_zero", "porque": "Comprobar alcance y necesidad de la excepción del linter contra el sujeto real, incluyendo control negativo sin excepción. Simplificar usando código nativo si mantiene comportamiento; si sigue siendo necesaria registrar razón, responsable y fecha/version de revisión. No retirar validación para conseguir cero warnings."}
---

## Registro y responsable

Registro solicitado por Luis el 2026-10-02. Responsable: coordinación de Blackbox. Trabajo o revisión pendiente; la presencia del marcador no demuestra por sí sola un defecto.

## Evidencia y alcance

Sitio: `bin/bb-usable:249`; función/contexto: bb-usable.

```text
log = lambda m: (print(m, file=sys.stderr, flush=True))  # noqa: E731
```

Clasificación: revisión de una exclusión/captura, no bug demostrado. No retirar automáticamente una protección o cleanup.

Fuentes: bin/bb-usable:249.

## Criterio de cierre y control negativo

Comprobar alcance y necesidad de la excepción del linter contra el sujeto real, incluyendo control negativo sin excepción. Simplificar usando código nativo si mantiene comportamiento; si sigue siendo necesaria registrar razón, responsable y fecha/version de revisión. No retirar validación para conseguir cero warnings.

## Estado del verificador

La ficha permanece abierta. El test selector del close_check es una especificación pendiente, no una prueba existente ni un resultado ejecutado. Implementarlo exige comprobar el sujeto y su control negativo; la existencia de archivos o esta ficha no basta para cerrar.

Conservar comandos, salida literal y could_not_run incluso cero; una ejecución skipped o inaccesible deja el cierre pendiente. Reutilizar instrumentos nativos y pruebas existentes antes de crear código.

## Verificación realizada

El close_check ejecuta Ruff E731 contra el ejecutable real con --ignore-noqa y el primer log de main con interrupción antes de medir. Fallaba con la lambda; pasa con def. Suite de bb-usable conserva decisiones de watchdog y controles negativos.

## Root Cause

Una lambda asignada requería la supresión E731. La función explícita conserva print a stderr con flush=True.

## Regression Test

El close_check original pasa con las reglas actuales; las pruebas del sujeto conservan sus controles sanos y negativos. La variante temporal de Ruff registra el fallo de la regla sin cambiar configuración.

## Verification Evidence

Salidas literales antes/después y del subconjunto en las tres rutas evidence del frontmatter. Re-chequeo del coordinador y triage por ID registrados en tasks/evidence/ZERO-2026-10-02. La revisión Bash del hook carecía de archivos candidatos y se reporta como could_not_run.
