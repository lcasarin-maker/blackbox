---
id: DEBT-RESEARCH-COLLECTOR-BB-FORUM-FETCH-01
kind: task
domain: VERDICT
title: "Decidir alcance del recolector histórico bb_forum_fetch"
status: done
closed_at: 2026-10-03
evidence: {"pass": "tasks/evidence/DEBT-RESEARCH-COLLECTOR-BB-FORUM-FETCH-01/pass.txt", "fail": "tasks/evidence/DEBT-RESEARCH-COLLECTOR-BB-FORUM-FETCH-01/fail.txt", "e2e": "tasks/evidence/DEBT-RESEARCH-COLLECTOR-BB-FORUM-FETCH-01/e2e.txt"}
severity: P2
origin: detected
detector: {"rule": "zero_debt: hardcoded_path, unencoded_file_io, blocking_sleep", "confidence": 1.0}
satd_family: BLIND_INSTRUMENT
created: 2026-10-03
close_check: {"cmd": "python3 -m pytest -q tests/test_debt_registration_controls.py::test_debt_research_collector_bb_forum_fetch_01", "expect": "exit_zero", "porque": "Resolver alcance por decisión explícita: archivo histórico preservado con hashes y sujeto retirado de código publicado, o recolector mantenido con controles positivos/negativos de rutas, IO y pacing. No ocultar hallazgos sin decisión ni alterar gates."}
---

## Hallazgos derivados de fuente

Sujeto `tasks/evidence/SWARM-LUNA-FORUM-2026-10-02/bb_forum_fetch.py`. 9 hallazgos literales del gate. Fuente: `tasks/evidence/ZERO-2026-10-02/research-collectors-before.txt`. Es una herramienta usada en investigación de una sesión, aún sin contrato de mantenimiento. La decisión cambia el alcance y el costo; boleta presentada al usuario 2026-10-03.

```json
[
  {
    "detector_id": "hardcoded_path",
    "file_path": "tasks/evidence/SWARM-LUNA-FORUM-2026-10-02/bb_forum_fetch.py",
    "line": 3,
    "message": "tasks/evidence/SWARM-LUNA-FORUM-2026-10-02/bb_forum_fetch.py:3: hardcoded_path: hardcoded absolute path '/home/lcasarin/projects/blackbox/tasks/evidence/SWARM-LUNA-FORUM-2026-10-02'",
    "severity": "FAIL",
    "would_block": true
  },
  {
    "detector_id": "unencoded_file_io",
    "file_path": "tasks/evidence/SWARM-LUNA-FORUM-2026-10-02/bb_forum_fetch.py",
    "line": 46,
    "message": "tasks/evidence/SWARM-LUNA-FORUM-2026-10-02/bb_forum_fetch.py:46: unencoded_file_io: .write_text(...) with no explicit encoding=",
    "severity": "FAIL",
    "would_block": true
  },
  {
    "detector_id": "unencoded_file_io",
    "file_path": "tasks/evidence/SWARM-LUNA-FORUM-2026-10-02/bb_forum_fetch.py",
    "line": 49,
    "message": "tasks/evidence/SWARM-LUNA-FORUM-2026-10-02/bb_forum_fetch.py:49: unencoded_file_io: .read_text(...) with no explicit encoding=",
    "severity": "FAIL",
    "would_block": true
  },
  {
    "detector_id": "unencoded_file_io",
    "file_path": "tasks/evidence/SWARM-LUNA-FORUM-2026-10-02/bb_forum_fetch.py",
    "line": 36,
    "message": "tasks/evidence/SWARM-LUNA-FORUM-2026-10-02/bb_forum_fetch.py:36: unencoded_file_io: .write_text(...) with no explicit encoding=",
    "severity": "FAIL",
    "would_block": true
  },
  {
    "detector_id": "unencoded_file_io",
    "file_path": "tasks/evidence/SWARM-LUNA-FORUM-2026-10-02/bb_forum_fetch.py",
    "line": 42,
    "message": "tasks/evidence/SWARM-LUNA-FORUM-2026-10-02/bb_forum_fetch.py:42: unencoded_file_io: .write_text(...) with no explicit encoding=",
    "severity": "FAIL",
    "would_block": true
  },
  {
    "detector_id": "unencoded_file_io",
    "file_path": "tasks/evidence/SWARM-LUNA-FORUM-2026-10-02/bb_forum_fetch.py",
    "line": 21,
    "message": "tasks/evidence/SWARM-LUNA-FORUM-2026-10-02/bb_forum_fetch.py:21: unencoded_file_io: .read_text(...) with no explicit encoding=",
    "severity": "FAIL",
    "would_block": true
  },
  {
    "detector_id": "blocking_sleep",
    "file_path": "tasks/evidence/SWARM-LUNA-FORUM-2026-10-02/bb_forum_fetch.py",
    "line": 48,
    "message": "tasks/evidence/SWARM-LUNA-FORUM-2026-10-02/bb_forum_fetch.py:48: blocking_sleep: blocking time.sleep() with no # blocking-sleep: <reason> -- <TICKET> justification",
    "severity": "FAIL",
    "would_block": true
  },
  {
    "detector_id": "blocking_sleep",
    "file_path": "tasks/evidence/SWARM-LUNA-FORUM-2026-10-02/bb_forum_fetch.py",
    "line": 32,
    "message": "tasks/evidence/SWARM-LUNA-FORUM-2026-10-02/bb_forum_fetch.py:32: blocking_sleep: blocking time.sleep() with no # blocking-sleep: <reason> -- <TICKET> justification",
    "severity": "FAIL",
    "would_block": true
  },
  {
    "detector_id": "blocking_sleep",
    "file_path": "tasks/evidence/SWARM-LUNA-FORUM-2026-10-02/bb_forum_fetch.py",
    "line": 16,
    "message": "tasks/evidence/SWARM-LUNA-FORUM-2026-10-02/bb_forum_fetch.py:16: blocking_sleep: blocking time.sleep() with no # blocking-sleep: <reason> -- <TICKET> justification",
    "severity": "FAIL",
    "would_block": true
  }
]
```

## Criterio y responsable

Responsable coordinación BB/Luis. Al registrar esta ficha, la decisión aún estaba pendiente; cierre y evidencia final constan en la sección siguiente. Si se archiva, conservar bytes/modos/SHA-256 y captura de hallazgos en registro; comprobar control negativo que reintroduce el sujeto. El archivo histórico no acredita código corregido. Si se mantiene, portar sin nueva supresión, ejecutar contra fixtures y preservar límites/reintentos medidos.

## Cierre (decisión derivada 2026-10-03)

Se mantiene y repara el recolector. La instrucción vigente de reparar los 80 avisos y los 4 de pyright determina mantener estos recolectores de investigación. Esta instrucción resuelve el alcance de los recolectores; la boleta anterior seguía pendiente.

## Root Cause

 la herramienta de investigación usaba una ruta absoluta del host, IO con encoding implícito y reintentos con pausas no cubiertas por fixtures; el resultado de cinco fallos agotados quedaba implícito en el control de flujo.

## Regression Test

 `python3 -m pytest -q tests/test_debt_registration_controls.py::test_debt_research_collector_bb_forum_fetch_01` cubre respuesta válida, datos incompletos, errores, 429/Retry-After, timeout agotado, pacing y salida a ruta temporal ajena al checkout.

## Verification Evidence

 `tasks/evidence/DEBT-RESEARCH-COLLECTOR-BB-FORUM-FETCH-01/fail.txt`, `pass.txt` y `e2e.txt`. Incluyen controles negativos, resultado positivo, fixtures de payload válido/malformado/incompleto, reintentos, Retry-After, timeout, pacing y serialización. El close check conjunto reportó `5 passed in 0.04s`; Ruff reportó `All checks passed!`; Pyright sobre ambos recolectores reportó `0 errors, 0 warnings, 0 informations`. Fixtures offline; ninguna petición de red real.
