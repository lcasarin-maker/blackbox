---
id: DEBT-BLACKBOX-TEST-NET-HERMETICITY
kind: debt
domain: VERDICT
title: "Tests unitarios de bb se cuelgan por timeouts de 20s contra demonios vLLM en localhost:8000"
status: done
closed_at: 2026-10-24
closure_type: fixed
closure_reason: "Inyectado BLACKBOX_GATEWAY_URL=http://127.0.0.1:1 por defecto en correr() de test_bb_bash.py para forzar Connection Refused inmediato (0.001s)."
evidence:
  pass: tasks/evidence/DEBT-BLACKBOX-TEST-NET-HERMETICITY/pass.txt
severity: P1
origin: asserted
satd_family: TEST_DEBT
created: 2026-10-24
close_check: {"cmd": "pytest tests/test_bb_bash.py", "expect": "exit_zero"}
---

## Problema
Al ejecutar `bin/bb status`, el binario consulta `http://127.0.0.1:8000/v1/models` y `http://127.0.0.1:8000/v1/chat/completions`. Cuando un demonio local de vLLM está activo en el puerto 8000 (ej. modelo Nemotron), el subproceso intenta negociar una solicitud con un timeout de 20s. En las más de 30 invocaciones de `tests/test_bb_bash.py`, esto provocaba congelamientos de hasta 8 minutos en el hook de push.

## Solución
Se configuró `BLACKBOX_GATEWAY_URL="http://127.0.0.1:1"` por defecto en el arnés de ejecución de `tests/test_bb_bash.py`, garantizando rechazo inmediato a nivel TCP (0.001s) e inmunidad contra demonios de IA locales.
Commit: `1df1441f`.
