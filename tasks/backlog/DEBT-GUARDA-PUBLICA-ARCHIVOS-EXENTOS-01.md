---
id: DEBT-GUARDA-PUBLICA-ARCHIVOS-EXENTOS-01
kind: debt
domain: SECURITY
title: "Definir y probar cobertura de las dos exenciones manteniendo los tokens firmados y los fixtures necesarios."
status: open
severity: P2
origin: measured
owner: blackbox
created: 2026-11-13
close_check: {"cmd": "python3 -m pytest -q -p no:cacheprovider tasks/checks/test_revision_privacidad.py::test_dato_nuevo_en_guarda_no_queda_exento", "expect": "exit_zero", "porque": "Dato nuevo en el archivo de la guarda debe bloquear; preservar los tokens firmados y fixtures imprescindibles mediante excepciones acotadas. Prueba de producto, no existencia de evidencia."}
---

## Fuente y evidencia

Generada desde `tasks/evidence/REVISION-PRIVACIDAD-2026-11-13/pendientes-revision.json`.
ID conservado; estado de origen: pendiente_no_bloqueante_preexistente.
SHA256 del JSON fuente: `859b4d0178145f1c59c26bf14b9c0fd9f4ac793e0affe0740502938103fea64a`.

Revision final C6: dato sintetico en HEAD dentro del archivo de la guarda produce 5 passed; archivo de guarda y base estan exentos.

## Responsable y aceptacion

Owner: blackbox; revision independiente antes de publicar el arreglo.
Dato nuevo en el archivo de la guarda debe bloquear; preservar los tokens firmados y fixtures imprescindibles mediante excepciones acotadas.

Accion pendiente: Definir y probar cobertura de las dos exenciones manteniendo los tokens firmados y los fixtures necesarios.

El close_check ejecuta una regresion contra el producto actual y queda rojo
hasta corregirlo. Registrar esta ficha no lo resuelve ni autoriza su cierre.
