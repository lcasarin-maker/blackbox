---
id: DEBT-GUARDA-PUBLICA-ERROR-LECTOR-COMO-FAIL-01
kind: debt
domain: SECURITY
title: "Distinguir fallo del lector de hallazgo con salida de instrumento y controles para base rota y git ausente."
status: open
severity: P2
origin: measured
owner: blackbox
created: 2026-11-13
close_check: {"cmd": "python3 -m pytest -q -p no:cacheprovider tasks/checks/test_revision_privacidad.py::test_error_lector_es_could_not_run", "expect": "exit_zero", "porque": "Base ilegible y Git ausente deben ser CNR; hallazgo real debe seguir siendo fail, y HEAD limpio pass. Prueba de producto, no existencia de evidencia."}
---

## Fuente y evidencia

Generada desde `tasks/evidence/REVISION-PRIVACIDAD-2026-11-13/pendientes-revision.json`.
ID conservado; estado de origen: pendiente_no_bloqueante.
SHA256 del JSON fuente: `859b4d0178145f1c59c26bf14b9c0fd9f4ac793e0affe0740502938103fea64a`.

Revision final G4 y C7: base ilegible o ausencia de .git produce pytest rc=1, fila fail y could_not_run=0; instrumento caido se confunde con sujeto sucio.

## Responsable y aceptacion

Owner: blackbox; revision independiente antes de publicar el arreglo.
Base ilegible y Git ausente deben ser CNR; hallazgo real debe seguir siendo fail, y HEAD limpio pass.

Accion pendiente: Distinguir fallo del lector de hallazgo con salida de instrumento y controles para base rota y git ausente.

El close_check ejecuta una regresion contra el producto actual y queda rojo
hasta corregirlo. Registrar esta ficha no lo resuelve ni autoriza su cierre.
