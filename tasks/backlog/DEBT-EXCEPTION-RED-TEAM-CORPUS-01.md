---
id: DEBT-EXCEPTION-RED-TEAM-CORPUS-01
kind: task
domain: VERDICT
title: "Revalidar no aplicabilidad de red_team_corpus"
status: open
severity: P2
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-10-02
close_check: {"cmd": "python3 -m pytest -q tests/test_debt_registration_controls.py::test_debt_exception_red_team_corpus_01", "expect": "exit_zero", "porque": "Comprobar el supuesto de no aplicabilidad contra el repo actual y ejecutar el órgano en su contexto. Si el sujeto existe, reactivar el control; si permanece ausente, conservar NO APLICA explícito y justificar canaria o su imposibilidad sin fabricar un sujeto falso. Renovar caducidad y vigía concretos solo con evidencia; una excepción vencida debe bloquear, no desaparecer."}
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

## Estado del verificador

La ficha permanece abierta. El test selector del close_check es una especificación pendiente, no una prueba existente ni un resultado ejecutado. Implementarlo exige comprobar el sujeto y su control negativo; la existencia de archivos o esta ficha no basta para cerrar.

Conservar comandos, salida literal y could_not_run incluso cero; una ejecución skipped o inaccesible deja el cierre pendiente. Reutilizar instrumentos nativos y pruebas existentes antes de crear código.
