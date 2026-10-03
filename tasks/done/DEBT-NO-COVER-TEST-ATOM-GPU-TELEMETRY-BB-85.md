---
id: DEBT-NO-COVER-TEST-ATOM-GPU-TELEMETRY-BB-85
kind: task
domain: VERDICT
title: "Revisar no-cover en test_atom_gpu_telemetry_bb.py:85"
severity: P2
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-10-02
close_check: {"cmd": "python3 -m pytest -q tests/test_debt_registration_controls.py::test_debt_no_cover_test_atom_gpu_telemetry_bb_85", "expect": "exit_zero", "porque": "Medir el camino excluido sin depender de la marca no cover. Si es entrypoint, ejecutar el script real con caso válido e inválido y comprobar stdout/rc; si es un fake, justificar qué camino es inalcanzable y comprobar esa afirmación. Control negativo: mutar el comportamiento del sujeto y demostrar rechazo. Quitar la marca o conservar una exclusión justificada sin afirmar cobertura de lo excluido."}
status: done
closed_at: 2026-10-03
closure_type: fixed
reason: "El fake HTTP 503 no necesita read(): la rama retorna por status antes de consumir el cuerpo; un mutante que intenta leerlo falla visiblemente."
evidence: {"pass":"tasks/evidence/DEBT-NO-COVER-TEST-ATOM-GPU-TELEMETRY-BB-85.pass.txt","fail":"tasks/evidence/DEBT-NO-COVER-TEST-ATOM-GPU-TELEMETRY-BB-85.fail.txt","e2e":"tasks/evidence/DEBT-NO-COVER-TEST-ATOM-GPU-TELEMETRY-BB-85.e2e.txt"}
---

## Registro y responsable

Registro solicitado por Luis el 2026-10-02. Responsable: coordinación de Blackbox. La revisión del instrumento y su control negativo quedó verificada en esta ficha.

## Evidencia y alcance

Sitio: `tests/test_atom_gpu_telemetry_bb.py:85`; función/contexto: test_atom_gpu_telemetry_bb.

```text
def read(self): return b""            # pragma: no cover - no se llega
```

Clasificación: revisión de una exclusión/captura, no bug demostrado. No retirar automáticamente una protección o cleanup.

Fuentes: tests/test_atom_gpu_telemetry_bb.py:85.

## Criterio de cierre y control negativo

Medir el camino excluido sin depender de la marca no cover. Si es entrypoint, ejecutar el script real con caso válido e inválido y comprobar stdout/rc; si es un fake, justificar qué camino es inalcanzable y comprobar esa afirmación. Control negativo: mutar el comportamiento del sujeto y demostrar rechazo. Quitar la marca o conservar una exclusión justificada sin afirmar cobertura de lo excluido.

## Estado del verificador

El selector close_check pasó y la evidencia separa la ejecución previa, posterior y el control mutante.

## Root Cause

Con status 503 el sujeto retorna el diagnóstico antes de llamar read(); el método del fake no era alcanzable y falseaba el contrato del objeto de respuesta.

## Regression Test

El fake conserva status y el protocolo de contexto, pero elimina read(). La prueba exige el diagnóstico exacto HTTP 503. El selector repite la prueba con un mutante que lee el cuerpo no-200 y espera AttributeError.

## Verification Evidence

Las rutas fail/pass/e2e registran el close_check ausente inicial y su resultado posterior. La prueba Atom completa pasó 53/53; el fake sin read conserva HTTP 503 y el mutante que lee el cuerpo lanza el AttributeError esperado. could_not_run: 0 en estas verificaciones. No se añadió suppressión.
