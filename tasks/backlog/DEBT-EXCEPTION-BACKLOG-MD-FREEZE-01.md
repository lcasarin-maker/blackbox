---
id: DEBT-EXCEPTION-BACKLOG-MD-FREEZE-01
kind: task
domain: VERDICT
title: "Revalidar no aplicabilidad de backlog_md_freeze"
status: open
severity: P2
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-10-02
close_check: {"cmd": "python3 -m pytest -q tests/test_debt_registration_controls.py::test_debt_exception_backlog_md_freeze_01", "expect": "exit_zero", "porque": "Comprobar el supuesto de no aplicabilidad contra el repo actual y ejecutar el órgano en su contexto. Si el sujeto existe, reactivar el control; si permanece ausente, conservar NO APLICA explícito y justificar canaria o su imposibilidad sin fabricar un sujeto falso. Renovar caducidad y vigía concretos solo con evidencia; una excepción vencida debe bloquear, no desaparecer."}
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

## Estado del verificador

La ficha permanece abierta. El test selector del close_check es una especificación pendiente, no una prueba existente ni un resultado ejecutado. Implementarlo exige comprobar el sujeto y su control negativo; la existencia de archivos o esta ficha no basta para cerrar.

Conservar comandos, salida literal y could_not_run incluso cero; una ejecución skipped o inaccesible deja el cierre pendiente. Reutilizar instrumentos nativos y pruebas existentes antes de crear código.
