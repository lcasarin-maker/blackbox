---
id: DEBT-SPEC-GATEWAY-DOS-NOTACIONES-01
kind: debt
domain: DOCUMENTATION
title: "Unificar la notacion documental en un cambio posterior revisado."
status: open
severity: P3
origin: measured
owner: blackbox
created: 2026-11-13
close_check: {"cmd": "python3 -m pytest -q -p no:cacheprovider tasks/checks/test_revision_privacidad.py::test_spec_usa_una_notacion_gateway", "expect": "exit_zero", "porque": "Tabla y narrativa deben usar la misma notacion del gateway, comprobando el contenido real de SPEC. Prueba de producto, no existencia de evidencia."}
---

## Fuente y evidencia

Generada desde `tasks/evidence/REVISION-PRIVACIDAD-2026-11-13/pendientes-revision.json`.
ID conservado; estado de origen: pendiente_no_bloqueante.
SHA256 del JSON fuente: `859b4d0178145f1c59c26bf14b9c0fd9f4ac793e0affe0740502938103fea64a`.

SPEC.md:380 usa @BB_GATEWAY@; SPEC.md:404 conserva nombre generico de sustitucion para active_engine.json.

## Responsable y aceptacion

Owner: blackbox; revision independiente antes de publicar el arreglo.
Tabla y narrativa deben usar la misma notacion del gateway, comprobando el contenido real de SPEC.

Accion pendiente: Unificar la notacion documental en un cambio posterior revisado.

El close_check ejecuta una regresion contra el producto actual y queda rojo
hasta corregirlo. Registrar esta ficha no lo resuelve ni autoriza su cierre.
