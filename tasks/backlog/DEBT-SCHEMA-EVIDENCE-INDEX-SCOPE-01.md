---
id: DEBT-SCHEMA-EVIDENCE-INDEX-SCOPE-01
kind: task
domain: VERDICT
title: "Índice Markdown de evidencias queda fuera del esquema gobernado"
status: open
severity: P2
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-10-02
close_check: {"cmd": "python3 -m pytest -q tests/test_debt_registration_controls.py::test_debt_schema_evidence_index_scope_01", "expect": "exit_zero", "porque": "El gate conserva los 145 sujetos y deja de omitir el índice de documentación con could_not_run. Usar convención nativa para documentación/evidencia o una carpeta gobernada según el contenido, sin borrar ni ocultar fichas reales. Control negativo: una ficha real fuera de alcance sigue siendo detectada. Preservar el índice y sus enlaces."}
---

## Registro y responsable

Registro solicitado por Luis el 2026-10-02. Responsable: coordinación de Blackbox. Defecto confirmado.

## Evidencia y alcance

`ledger_schema --root .`: checked=145 passed=145 failed=0 avisos=74 could_not_run=1; BACKLOG-INDEX.md de la investigación está fuera de carpetas gobernadas. El índice no constituye una ficha y no debe introducir una fila omitida silenciosamente. Durante el registro se añadió una segunda omisión: attachments-root/360142-post39-RESULTS.md. Verificación actual:263 checked263 passed0 failed74 avisos2 could_not_run. Resolver la política de documentos/evidencias fuera de alcance, preservando ambos archivos y detectando fichas reales mal ubicadas.

Fuentes: tasks/evidence/SWARM-LUNA-FORUM-2026-10-02/BACKLOG-INDEX.md.

## Criterio de cierre y control negativo

El gate conserva los 145 sujetos y deja de omitir el índice de documentación con could_not_run. Usar convención nativa para documentación/evidencia o una carpeta gobernada según el contenido, sin borrar ni ocultar fichas reales. Control negativo: una ficha real fuera de alcance sigue siendo detectada. Preservar el índice y sus enlaces.

## Estado del verificador

La ficha permanece abierta. El test selector del close_check es una especificación pendiente, no una prueba existente ni un resultado ejecutado. Implementarlo exige comprobar el sujeto y su control negativo; la existencia de archivos o esta ficha no basta para cerrar.

Conservar comandos, salida literal y could_not_run incluso cero; una ejecución skipped o inaccesible deja el cierre pendiente. Reutilizar instrumentos nativos y pruebas existentes antes de crear código.
