---
id: DEBT-DATOS-PRIVADOS-EN-EVIDENCIA-HISTORICA-01
kind: task
domain: SECURITY
title: "El repo publico conserva MACs, IPs, hostname y proyectos privados en evidencias historicas"
status: open
severity: P2
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-10-11
close_check: {"cmd": "grep -F tasks/evidence/ tests/fixtures/datos_privados_baseline.json", "expect": "empty_stdout", "porque": "Medido el 2026-10-11: 139 archivos versionados y 2194 ocurrencias en tests/fixtures/datos_privados_baseline.json, la mayoria en tasks/evidence con hashes de procedencia. Desde hoy tests/test_sin_datos_privados.py impide que crezca; falta vaciar la lista. Cierra cuando ninguna ruta de tasks/evidence quede en la base."}
---

## Estado

La guarda impide archivos nuevos con estos datos. Las evidencias historicas llevan sha256 de procedencia: redactarlas exige regenerar los hashes y sus manifiestos, y la historia de git las conserva de todos modos. Reescribir la historia (force-push) es decision del dueno y no se tomo. Antes de decidir, medir el alcance con gitleaks y el historial: el analisis cubrio 6 patrones y solo el arbol actual.
