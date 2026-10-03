---
id: DEBT-EXCEPTION-LOCKFILE-PARITY-01
kind: task
domain: VERDICT
title: "Revalidar no aplicabilidad de lockfile_parity"
status: open
severity: P2
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-10-02
close_check: {"cmd": "python3 -m pytest -q tests/test_debt_registration_controls.py::test_debt_exception_lockfile_parity_01", "expect": "exit_zero", "porque": "Comprobar el supuesto de no aplicabilidad contra el repo actual y ejecutar el órgano en su contexto. Si el sujeto existe, reactivar el control; si permanece ausente, conservar NO APLICA explícito y justificar canaria o su imposibilidad sin fabricar un sujeto falso. Renovar caducidad y vigía concretos solo con evidencia; una excepción vencida debe bloquear, no desaparecer."}
---

## Registro y responsable

Registro solicitado por Luis el 2026-10-02. Responsable: coordinación de Blackbox. Trabajo o revisión pendiente; la presencia del marcador no demuestra por sí sola un defecto.

## Evidencia y alcance

Declaración vigente: owner=the maintainer; expires=2026-10-13.

{
  "reason": "Medido el 2026-09-25 sobre la maquina: `[lockfile-parity] NO APLICA: no hay requirements-lock.txt`. Comprueba que las versiones FIJADAS sobrevivan a un clon, y aqui no hay fichero de pinneo del que derivarlas -- `bin/bb` es bash y no declara dependencias mas alla de lo que trae el sistema. CORRECCION de la razon anterior, que decia 'este repo no tiene pyproject.toml': lo tiene, y lo tenia ya cuando se escribio (203a19f lo trae). El organo nunca hablo de pyproject.toml sino del lockfile, asi que la declaracion era correcta en su conclusion y falsa en su motivo -- que es peor que estar equivocada, porque un motivo falso no se puede refutar midiendo lo que dice. RE-CONFIRMADO 2026-09-28: mismo mensaje exacto, `[lockfile-parity] NO APLICA: no hay requirements-lock.txt`, sin cambios.",
  "canary": "No se planta: exigiria crear un pyproject.toml con dependencias fijadas solo para que el organo tuviera algo que comparar, que es fabricar el sujeto. El propio organo distingue 'NO APLICA' de 'sin hallazgos', y esa distincion es la medicion.",
  "difiere": "Captura en los satelites Python que tienen requirements-lock.txt. Queda refutada en cuanto blackbox adopte un fichero de pinneo."
}

Fuentes: .simplecode/organ_inapplicable.json.

## Criterio de cierre y control negativo

Comprobar el supuesto de no aplicabilidad contra el repo actual y ejecutar el órgano en su contexto. Si el sujeto existe, reactivar el control; si permanece ausente, conservar NO APLICA explícito y justificar canaria o su imposibilidad sin fabricar un sujeto falso. Renovar caducidad y vigía concretos solo con evidencia; una excepción vencida debe bloquear, no desaparecer.

## Estado del verificador

La ficha permanece abierta. El test selector del close_check es una especificación pendiente, no una prueba existente ni un resultado ejecutado. Implementarlo exige comprobar el sujeto y su control negativo; la existencia de archivos o esta ficha no basta para cerrar.

Conservar comandos, salida literal y could_not_run incluso cero; una ejecución skipped o inaccesible deja el cierre pendiente. Reutilizar instrumentos nativos y pruebas existentes antes de crear código.
