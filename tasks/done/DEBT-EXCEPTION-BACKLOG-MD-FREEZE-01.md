---
id: DEBT-EXCEPTION-BACKLOG-MD-FREEZE-01
kind: task
domain: VERDICT
title: "Revalidar no aplicabilidad de backlog_md_freeze"
status: done
severity: P2
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-10-02
close_check: {"cmd": "python3 -m pytest -q tests/test_debt_registration_controls.py::test_debt_exception_backlog_md_freeze_01", "expect": "exit_zero", "porque": "Comprobar el supuesto de no aplicabilidad contra el repo actual y ejecutar el órgano en su contexto. Si el sujeto existe, reactivar el control; si permanece ausente, conservar NO APLICA explícito y justificar canaria o su imposibilidad sin fabricar un sujeto falso. Renovar caducidad y vigía concretos solo con evidencia; una excepción vencida debe bloquear, no desaparecer."}
closed_at: 2026-10-03
closure_type: void_wontfix
reason: "La revisión confirma que BACKLOG.md y la declaración .simplecode/backlog_md_frozen.json siguen ausentes. Se conserva la excepción explícita y el vigía `the maintainer`, con caducidad existente 2026-10-13. El órgano se probó en un repo temporal declarado frozen: una línea staged nueva bloquea."
evidence: {"pass":"tasks/evidence/DEBT-EXCEPTION-BACKLOG-MD-FREEZE-01/pass.txt","fail":"tasks/evidence/DEBT-EXCEPTION-BACKLOG-MD-FREEZE-01/fail.txt","e2e":"tasks/evidence/DEBT-EXCEPTION-BACKLOG-MD-FREEZE-01/e2e.txt"}
---

## Registro y responsable

Registro solicitado por Luis el 2026-10-02. Responsable: coordinación de Blackbox. Trabajo o revisión pendiente; la presencia del marcador no demuestra por sí sola un defecto.

## Evidencia y alcance

Declaración vigente: owner=the maintainer; expires=2026-10-13.

{
  "reason": "Este repo NO TIENE BACKLOG.md y su ausencia es una decision, no un olvido: el declutter del 2026-09-13 lo retiro a proposito bajo 'un solo canon de estado', y el propio scan.py de /debt lo documenta ('Sin indice, el ranking lee DIRECTO de tasks/backlog/*.md -- declutter retiro BACKLOG.md a proposito'). Medido 2026-09-24: `ls BACKLOG.md` -> no existe el fichero, y `git log -- BACKLOG.md` no devuelve un solo commit, o sea que nunca existio en este repo. El organo vigila que no se anada contenido nuevo a un indice ya declarado; sin indice no hay nada que congelar. RE-CONFIRMADO 2026-09-28: sigue sin existir BACKLOG.md, y el organo da `.simplecode/backlog_md_frozen.json not declared -- nothing frozen`.",
  "canary": "NO se planta, y por la misma razon ya aceptada para lockfile_parity en este mismo fichero: exigiria CREAR un BACKLOG.md solo para que el organo tuviera algo que vigilar, que es fabricar el sujeto para el instrumento en vez de al reves. Peor aqui, porque ese fichero fue retirado por decision explicita y plantarlo deshace la decision que el repo tomo. Lo que SI se midio es la ausencia del sujeto, arriba, con dos comandos y sus salidas.",
  "difiere": "Captura en los repos que si mantienen BACKLOG.md como indice: no es una propiedad de blackbox sino de su canon de estado. Queda refutada, y hay que borrar esta entrada, en cuanto blackbox vuelva a tener BACKLOG.md por cualquier via."
}

Fuentes: .simplecode/organ_inapplicable.json.

## Criterio de cierre y control negativo

Comprobar el supuesto de no aplicabilidad contra el repo actual y ejecutar el órgano en su contexto. Si el sujeto existe, reactivar el control; si permanece ausente, conservar NO APLICA explícito y justificar canaria o su imposibilidad sin fabricar un sujeto falso. Renovar caducidad y vigía concretos solo con evidencia; una excepción vencida debe bloquear, no desaparecer.

## Root Cause

La ficha registraba una exclusión/sunset pendiente de revalidación. Se inspeccionó el sitio exacto y se contrastó la razón de la excepción con el control que la sostiene.

## Regression Test

`python3 -m pytest -q tests/test_debt_registration_controls.py::test_debt_exception_backlog_md_freeze_01`

Control negativo incluido en el selector: La revisión confirma que BACKLOG.md y la declaración .simplecode/backlog_md_frozen.json siguen ausentes. Se conserva la excepción explícita y el vigía `the maintainer`, con caducidad existente 2026-10-13. El órgano se probó en un repo temporal declarado frozen: una línea staged nueva bloquea.

## Verification Evidence

Pass: selector `DEBT-EXCEPTION-BACKLOG-MD-FREEZE-01` pasa junto con los 13 selectores de esta ola; resultado `14 passed`, `could_not_run=0`. Fail previo: selector ausente, pytest exit 4; registrado solo como estado anterior de la instrumentación. El detalle y el alcance del control negativo constan en `tasks/evidence/DEBT-EXCEPTION-BACKLOG-MD-FREEZE-01/e2e.txt`.
