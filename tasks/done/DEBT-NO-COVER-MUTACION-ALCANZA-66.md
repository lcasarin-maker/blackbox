---
id: DEBT-NO-COVER-MUTACION-ALCANZA-66
kind: task
domain: VERDICT
title: "Revisar no-cover en mutacion_alcanza.py:66"
status: done
closed_at: 2026-10-02
closure_type: fixed
reason: "Quité la exclusión de cobertura y el close check ejecuta el launcher __main__ real con caso válido, error CLI y control negativo mutado."
evidence: {"pass": "tasks/evidence/DEBT-NO-COVER-MUTACION-ALCANZA-66/pass.txt", "fail": "tasks/evidence/DEBT-NO-COVER-MUTACION-ALCANZA-66/fail.txt", "e2e": "tasks/evidence/DEBT-NO-COVER-MUTACION-ALCANZA-66/e2e.txt"}
severity: P2
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-10-02
close_check: {"cmd": "python3 -m pytest -q tests/test_debt_registration_controls.py::test_debt_no_cover_mutacion_alcanza_66", "expect": "exit_zero", "porque": "Medir el camino excluido sin depender de la marca no cover. Si es entrypoint, ejecutar el script real con caso válido e inválido y comprobar stdout/rc; si es un fake, justificar qué camino es inalcanzable y comprobar esa afirmación. Control negativo: mutar el comportamiento del sujeto y demostrar rechazo. Quitar la marca o conservar una exclusión justificada sin afirmar cobertura de lo excluido."}
---

## Registro y responsable

Registro solicitado por Luis el 2026-10-02. Responsable: coordinación de Blackbox. Trabajo o revisión pendiente; la presencia del marcador no demuestra por sí sola un defecto.

## Evidencia y alcance

Sitio: `tools/mutacion_alcanza.py:66`; función/contexto: mutacion_alcanza.

```text
if __name__ == "__main__":  # pragma: no cover -- entry point, ejercitado via main()
```

Clasificación: revisión de una exclusión/captura, no bug demostrado. No retirar automáticamente una protección o cleanup.

Fuentes: tools/mutacion_alcanza.py:66.

## Criterio de cierre y control negativo

Medir el camino excluido sin depender de la marca no cover. Si es entrypoint, ejecutar el script real con caso válido e inválido y comprobar stdout/rc; si es un fake, justificar qué camino es inalcanzable y comprobar esa afirmación. Control negativo: mutar el comportamiento del sujeto y demostrar rechazo. Quitar la marca o conservar una exclusión justificada sin afirmar cobertura de lo excluido.

## Estado del verificador

La ficha permanece abierta. El test selector del close_check es una especificación pendiente, no una prueba existente ni un resultado ejecutado. Implementarlo exige comprobar el sujeto y su control negativo; la existencia de archivos o esta ficha no basta para cerrar.

Conservar comandos, salida literal y could_not_run incluso cero; una ejecución skipped o inaccesible deja el cierre pendiente. Reutilizar instrumentos nativos y pruebas existentes antes de crear código.


## Root Cause

The `DEBT-NO-COVER-MUTACION-ALCANZA-66` suppression excluded the script's `__main__` launcher from coverage, while imported-function tests did not prove the CLI process, its output, or its exit status. The entrypoint is reachable and safe to invoke with bounded CLI inputs.

## Regression Test

`python3 -m pytest -q tests/test_debt_registration_controls.py::test_debt_no_cover_mutacion_alcanza_66` starts the real script in a subprocess. It checks a successful CLI path, the invalid-argument/usage path with exit code 2, and a temporary mutant that forces launcher success and must violate that expected error code. The accepted-fiche script uses a valid temporary Markdown fixture. No GPU workload or host mutation is performed.

## Verification Evidence

- `tasks/evidence/DEBT-NO-COVER-MUTACION-ALCANZA-66/fail.txt` records the pre-fix missing-selector result and the report with the suppression active.
- `tasks/evidence/DEBT-NO-COVER-MUTACION-ALCANZA-66/pass.txt` records this ID's close check after implementation.
- `tasks/evidence/DEBT-NO-COVER-MUTACION-ALCANZA-66/e2e.txt` records the real process invocation and mutation control.
