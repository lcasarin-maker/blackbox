---
id: BUG-FORUM-STATUS-BUS-UNKNOWN-01
kind: task
domain: VERDICT
title: "Conservar error de consulta systemd en bb status en vez de declarar inactividad"
status: done
closed_at: 2026-10-02
closure_type: fixed
reason: "Consulta systemd/journal ilegible preservada como CIEGO y could_not_run."
evidence: {"pass": "tasks/evidence/BUG-FORUM-STATUS-BUS-UNKNOWN-01/pass.txt", "fail": "tasks/evidence/BUG-FORUM-STATUS-BUS-UNKNOWN-01/fail.txt", "e2e": "tasks/evidence/BUG-FORUM-STATUS-BUS-UNKNOWN-01/e2e.txt"}
severity: P1
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-10-02
close_check: {"cmd": "python3 -m pytest tests/test_status_bus_unknown.py -q", "expect": "exit_zero", "porque": "Control negativo: consulta systemd denegada => could_not_run/CIEGO; unidad inactiva consultable => FALTA; activa con/sin latido => estados distintos."}
---

## Reproducción propia

`bin/bb:2322-2324` descarta stderr de `systemctl is-active bb-usable.service` y cualquier fallo cae en detalle `inactiva`. Dentro del sandbox la consulta show retorna rc1 y `Failed to connect to bus: Operation not permitted`; fuera retorna rc0, ActiveState=active/SubState=running/Result=success/WatchdogUSec=6min. Comando literal y resultados conservados en tasks/evidence/SWARM-LUNA-FORUM-2026-10-02/local-platform-checks.txt. El primer bb status en sandbox declaró bb-usable inactiva; la comparación demuestra error de clasificación, sin afirmar cobertura eficaz del servicio por estar activo.

## Fix mínimo y prevención

Reutilizar la clasificación CIEGO/could_not_run del instrumento. Conservar rc y stderr de consultas; distinguir bus inaccesible, unit inexistente/inactiva, activa sin heartbeat y activa con señal fresca. Auditar llamadas hermanas de estado que silencian errores para evitar repetir el patrón. Mantener timestamps y comandos de diagnóstico en salida; ninguna consulta ilegible demuestra ausencia de protección ni salud.

## Cierre y riesgo

Fixtures de acceso denegado, bus ausente, unit not-found, inactiva consultable, activa sin latido y activa con latido. No requerir elevación automática ni alterar servicios para poder reportar su estado. Comprobar sumas de ARMADO/FALTA/CIEGO y could_not_run, con ceros impresos. La suite ejecuta estos controles sobre las funciones Bash corregidas.

## Implementado

status_usable consulta LoadState/ActiveState conservando rc/stderr. Diferencia ausencia/inactividad de consulta ilegible y exige latido fresco consultable. El resumen imprime could_not_run incluso cero. Pruebas negativas y verificación real arriba.

## Root Cause

La rama is-active descartaba stderr y colapsaba error de bus e inactividad en el mismo resultado. La consulta explícita de propiedades conserva el fallo; la consulta de latido también conserva permiso/rc.

## Regression Test

`tests/test_status_bus_unknown.py` ejecuta la función Bash del sujeto con fixtures de bus denegado/ausente, unidad ausente/inactiva, latido ausente/fresco, consulta vacía y journal ilegible. Verifica contadores ARMADO/FALTA/CIEGO/CNR exactamente, incluyendo cuatro controles negativos de consultas del bloqueo de reloj.

## Verification Evidence

pass/fail/e2e registran los controles y la consulta real de `bb status`. Salida completa en `tasks/evidence/SWARM-OPEN-2026-10-02/status-host.json`.
