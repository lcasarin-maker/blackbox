---
id: DEBT-SCHEMA-EVIDENCE-INDEX-SCOPE-01
kind: task
domain: VERDICT
title: "Índice Markdown de evidencias queda fuera del esquema gobernado"
status: done
closed_at: 2026-10-03
closure_type: relocated_prior_verification
reason: "El fix (prosa archivada byte identica bajo docs; ledger conserva todos los sujetos y detecta ficha real fuera de alcance) ya estaba commiteado desde el 2026-10-03 en 383a1d0. Esta ficha solo corrige una nota interna desactualizada y mueve el archivo el 2026-10-07."
evidence:
  fail: tasks/evidence/DEBT-SCHEMA-EVIDENCE-INDEX-SCOPE-01/fail.txt
  pass: tasks/evidence/DEBT-SCHEMA-EVIDENCE-INDEX-SCOPE-01/pass.txt
  e2e: tasks/evidence/DEBT-SCHEMA-EVIDENCE-INDEX-SCOPE-01/e2e.txt
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

Nota corregida 2026-10-07: esta sección decía "el test selector es una especificación pendiente, no una prueba existente" -- quedó desactualizada por el propio trabajo que describen las secciones Root Cause/Regression Test/Verification Evidence de abajo. `test_debt_schema_evidence_index_scope_01` existe en `tests/test_debt_registration_controls.py` (línea 379) y pasa hoy: `python3 -m pytest -q tests/test_debt_registration_controls.py::test_debt_schema_evidence_index_scope_01` -> 1 passed. `tasks/evidence/DEBT-SCHEMA-EVIDENCE-INDEX-SCOPE-01/{fail,pass,e2e}.txt` están en disco y su contenido coincide con la medición (`could_not_run` 4 antes, 0 después).

Conservar comandos, salida literal y could_not_run incluso cero; una ejecución skipped o inaccesible deja el cierre pendiente. Reutilizar instrumentos nativos y pruebas existentes antes de crear código.

## Root Cause

El esquema interpreta todo Markdown bajo tasks como ficha salvo los nombres de documentación nativa. Cuatro documentos de investigación carecían de contrato porque eran prosa de evidencia, no fichas. Se preservan bytes y modos en docs/evidence con migration.json; ninguna ficha real sale del alcance ni se modifica el instrumento.

## Regression Test

El selector verifica hashes, ausencia del documento en tasks y ejecución del esquema nativo sobre todos los sujetos actuales. El negativo copia una ficha real fuera de carpetas gobernadas: el mismo gate devuelve could_not_run=1 y fallo. El índice original sigue siendo snapshot histórico; su navegación portable se reconcilia por separado.

## Verification Evidence

La captura previa registra 4 could_not_run. Tras convención nativa, checked=268 passed=268 failed=0 could_not_run=0; 80 avisos consultivos permanecen visibles. El test con control negativo da 1 passed. No se cambia whitelist, cutoff, baseline ni supresión.
