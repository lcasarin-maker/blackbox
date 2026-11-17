---
id: DEBT-GUARDA-PUBLICA-ARCHIVOS-EXENTOS-01
kind: debt
domain: SECURITY
title: "Definir y probar cobertura de las dos exenciones manteniendo los tokens firmados y los fixtures necesarios."
status: done
closed_at: 2026-11-16
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

## Decision (voto de Luis, 2026-11-16)

Opcion elegida: **exentar solo lineas firmadas**. La guarda escanea todo su
archivo; solo se exentan las lineas de tokens firmados, identificadas por el
sha256 de cada linea. Descartadas: fijar el archivo por sha256, ofuscar tokens
sin exencion, dejarlo abierto. Costo aceptado: codigo nuevo en una guarda de
seguridad, que exige control negativo (editar una linea firmada debe disparar).

## Cierre (2026-11-16)

Commit 6d045169: `medir()` ya no salta el archivo de la guarda ni su linea base;
`cuenta_blob` descuenta solo las lineas de `LINEAS_FIRMADAS` (sha256 de la linea,
ruta exacta). Dos lineas firmadas: el MAC sintetico de un control de la guarda y
la ruta de evidencia de la linea base que cita un proyecto ajeno.
`test_cada_linea_firmada_existe_y_lleva_dato` obliga a quitar firmas huerfanas.
Controles en `tests/test_guarda_lineas_firmadas.py`; salidas y mutantes en
`tasks/evidence/DEBT-GUARDA-PUBLICA-ARCHIVOS-EXENTOS-01.{fail,pass}.txt`.
