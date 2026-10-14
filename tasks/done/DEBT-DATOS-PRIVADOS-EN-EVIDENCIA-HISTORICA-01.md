---
id: DEBT-DATOS-PRIVADOS-EN-EVIDENCIA-HISTORICA-01
kind: task
domain: SECURITY
title: "El repo publico conserva MACs, IPs, hostname y proyectos privados en evidencias historicas"
status: done
closed_at: 2026-10-13
closure_type: fixed
reason: "Las 1963 ocurrencias de los 53 archivos de tasks/evidence se redactaron dentro de su linea con el PATRON del propio test (<mac>/<host>/<ip>/otro proyecto; 0 lineas perdidas), los 24 manifiestos que guardaban sus sha256 se re-registraron en cascada, SPEC-L135 se re-audito con /h1 (PASS) en vez de editar el ledger, y las 53 rutas salieron de la base. El detector no se toco. La historia de git conserva los valores: reescribirla sigue siendo decision del dueno."
evidence: {"pass": "tasks/evidence/DEBT-DATOS-PRIVADOS-EN-EVIDENCIA-HISTORICA-01/pass.txt", "fail": "tasks/evidence/DEBT-DATOS-PRIVADOS-EN-EVIDENCIA-HISTORICA-01/fail.txt", "e2e": "tasks/evidence/DEBT-DATOS-PRIVADOS-EN-EVIDENCIA-HISTORICA-01/e2e.txt"}
severity: P2
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-10-11
close_check: {"cmd": "grep -F tasks/evidence/ tests/fixtures/datos_privados_baseline.json", "expect": "empty_stdout", "porque": "Medido el 2026-10-11: 139 archivos versionados y 2194 ocurrencias en tests/fixtures/datos_privados_baseline.json, la mayoria en tasks/evidence con hashes de procedencia. Desde hoy tests/test_sin_datos_privados.py impide que crezca; falta vaciar la lista. Cierra cuando ninguna ruta de tasks/evidence quede en la base."}
---

## Estado

La guarda impide archivos nuevos con estos datos. Las evidencias historicas llevan sha256 de procedencia: redactarlas exige regenerar los hashes y sus manifiestos, y la historia de git las conserva de todos modos. Reescribir la historia (force-push) es decision del dueno y no se tomo. Antes de decidir, medir el alcance con gitleaks y el historial: el analisis cubrio 6 patrones y solo el arbol actual.

## Cierre (2026-10-13)

- close_check antes: 53 rutas de tasks/evidence en la base (fail.txt). Despues: stdout vacio (pass.txt).
- Redaccion: 1963 ocurrencias en 53 archivos, reemplazadas dentro de la linea; 77 archivos cambiaron con 1236 lineas + / 1236 - (el resto son manifiestos con el sha256 nuevo).
- Ledger H1: no se edito a mano; SPEC-L135 quedo stale por run.json y se re-audito (1 auditor Opus, PASS), grabado con `audit --record --merge`; `audit --gate` en verde.
- Control negativo (e2e.txt): reinsertar una MAC original en un archivo redactado hace fallar la guarda; restaurado, pasa.
- Limite declarado: la historia de git conserva los valores originales; reescribirla (force-push) es decision del dueno y no se tomo. Las 86 entradas fuera de tasks/evidence siguen en la base (fuera del alcance de esta ficha).
