---
id: DEBT-EXCEPTION-RED-TEAM-CORPUS-01
kind: task
domain: VERDICT
title: "Revalidar no aplicabilidad de red_team_corpus"
status: done
severity: P2
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-10-02
close_check: {"cmd": "python3 -m pytest -q tests/test_debt_registration_controls.py::test_debt_exception_red_team_corpus_01", "expect": "exit_zero", "porque": "Comprobar el supuesto de no aplicabilidad contra el repo actual y ejecutar el órgano en su contexto. Si el sujeto existe, reactivar el control; si permanece ausente, conservar NO APLICA explícito y justificar canaria o su imposibilidad sin fabricar un sujeto falso. Renovar caducidad y vigía concretos solo con evidencia; una excepción vencida debe bloquear, no desaparecer."}
closed_at: 2026-10-03
closure_type: void_wontfix
reason: "La revisión confirma 91 mutaciones generadas y cero casos persistidos; cero capturas no se interpretan como sujeto limpio. Se conserva la excepción explícita y el vigía `the maintainer`, con caducidad existente 2026-10-13. Un caso temporal registrado que no se genera produce FAIL."
evidence: {"pass":"tasks/evidence/DEBT-EXCEPTION-RED-TEAM-CORPUS-01/pass.txt","fail":"tasks/evidence/DEBT-EXCEPTION-RED-TEAM-CORPUS-01/fail.txt","e2e":"tasks/evidence/DEBT-EXCEPTION-RED-TEAM-CORPUS-01/e2e.txt"}
---

## Registro y responsable

Registro solicitado por Luis el 2026-10-02. Responsable: coordinación de Blackbox. Trabajo o revisión pendiente; la presencia del marcador no demuestra por sí sola un defecto.

## Evidencia y alcance

Declaración vigente: owner=the maintainer; expires=2026-10-13.

{
  "reason": "Vigila que un caso una vez probado no desaparezca en silencio. Medido 2026-09-08: rc=0 con '[red-team-corpus] casos registrados: 0 | generados hoy: 91 | registrados que hoy NO se generan: 0'. Con CERO casos registrados no hay nada que pueda desvanecerse: el conjunto que el organo compara esta vacio por un lado. RE-CONFIRMADO 2026-09-28: mismo mensaje, `casos registrados: 0`, sin cambios.",
  "canary": "No se planta registrando un caso falso: el registro es precisamente el sujeto que este organo protege, y ensuciarlo para que dispare seria corromper la evidencia que vigila. La linea 'registrados: 0' ES la medicion de por que no puede capturar.",
  "difiere": "Captura donde hay corpus registrado. Queda refutada en cuanto blackbox registre su primer caso de red team."
}

Fuentes: .simplecode/organ_inapplicable.json.

## Criterio de cierre y control negativo

Comprobar el supuesto de no aplicabilidad contra el repo actual y ejecutar el órgano en su contexto. Si el sujeto existe, reactivar el control; si permanece ausente, conservar NO APLICA explícito y justificar canaria o su imposibilidad sin fabricar un sujeto falso. Renovar caducidad y vigía concretos solo con evidencia; una excepción vencida debe bloquear, no desaparecer.

## Root Cause

La ficha registraba una exclusión/sunset pendiente de revalidación. Se inspeccionó el sitio exacto y se contrastó la razón de la excepción con el control que la sostiene.

## Regression Test

`python3 -m pytest -q tests/test_debt_registration_controls.py::test_debt_exception_red_team_corpus_01`

Control negativo incluido en el selector: La revisión confirma 91 mutaciones generadas y cero casos persistidos; cero capturas no se interpretan como sujeto limpio. Se conserva la excepción explícita y el vigía `the maintainer`, con caducidad existente 2026-10-13. Un caso temporal registrado que no se genera produce FAIL.

## Verification Evidence

Pass: selector `DEBT-EXCEPTION-RED-TEAM-CORPUS-01` pasa junto con los 13 selectores de esta ola; resultado `14 passed`, `could_not_run=0`. Fail previo: selector ausente, pytest exit 4; registrado solo como estado anterior de la instrumentación. El detalle y el alcance del control negativo constan en `tasks/evidence/DEBT-EXCEPTION-RED-TEAM-CORPUS-01/e2e.txt`.
