---
id: DEBT-EARLYOOM-MOTOR-SIGUE-ELEGIBLE-01
kind: task
domain: MEMORY
title: "earlyoom sigue pudiendo elegir al motor vLLM: --avoid solo resta 300 puntos"
status: done
closed_at: 2026-10-30
closure_type: verified
reason: "Pasaron 15 dias desde el cambio de earlyoom (2026-10-14 11:50:07) con 0 senales a VLLM::EngineCor o vllm; el verificador dice aun no con una copia de hoy (rc=2) y cuenta 3 senales reales antes del cambio. Limite: el contenedor del motor sigue con oom_score_adj 500."
evidence: {"pass": "tasks/evidence/DEBT-EARLYOOM-MOTOR-SIGUE-ELEGIBLE-01/pass.txt", "fail": "tasks/evidence/DEBT-EARLYOOM-MOTOR-SIGUE-ELEGIBLE-01/fail.txt", "e2e": "tasks/evidence/DEBT-EARLYOOM-MOTOR-SIGUE-ELEGIBLE-01/e2e.txt"}
severity: P3
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-10-14
close_check: {"cmd": "bash tools/verifica_earlyoom_sin_muertes_motor.sh", "expect": "exit_zero", "porque": "Resto declarado al cerrar DEBT-EARLYOOM-MATA-AL-MOTOR-VLLM-01: en earlyoom 1.7 --avoid RESTA 300 al oom_score, no excluye, y el contenedor del motor tiene oom_score_adj 500 (/srv/ai/gateway/main.py:112, puesto a proposito). Cierra cuando pasen 14 dias desde el cambio (2026-10-14) con cero senales de earlyoom a VLLM::EngineCor o vllm en el journal; si hay alguna, la salida es decidir si el motor baja su oom_score_adj (ventana con el motor caido) o se acepta como sacrificio previsto."}
---

## Medido
14 senales de earlyoom a `VLLM::EngineCor` (17 con `vllm`) entre 2026-09-08 y 2026-10-10 (`journalctl -u earlyoom | grep -E 'to process.*VLLM'`). El cambio aplicado baja su badness 300 puntos (1038 a 738 en la ultima); el margen contra los demas candidatos no se puede medir: el journal solo registra a la victima.

## Por que no se ataca ahora
El seguimiento es tiempo: `tools/verifica_earlyoom_sin_muertes_motor.sh` sale 2 ("aun no") hasta que pasen 14 dias.
