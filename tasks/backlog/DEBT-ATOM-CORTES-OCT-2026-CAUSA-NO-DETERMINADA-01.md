---
id: DEBT-ATOM-CORTES-OCT-2026-CAUSA-NO-DETERMINADA-01
kind: task
domain: HARDWARE
title: "Cortes de la ATOM de octubre 2026 sin causa determinada (trasladada de Atlas DGX-640)"
status: open
severity: P1
origin: asserted
satd_family: UNCLASSIFIED_DEBT
created: 2026-10-17
close_check: {"cmd": "grep -q \"CAUSA DETERMINADA\" /home/lcasarin/projects/Atlas/docs/agent_findings/2026-10-12_atom_causa_de_los_cortes_oct_2026.md", "expect": "exit_zero", "porque": "Mismo patron que DGX-640 (grep sobre el dictamen que queda en Atlas, porque el gate de esquema no admite scripts ni cd), con exit_zero: el original esperaba empty_stdout y el verificador imprime 'OK 1 archivo(s)...' cuando pasa, asi que ese criterio no podia ponerse verde. Hoy rc=1 ('patron requerido CAUSA DETERMINADA ausente'). Control positivo corrido 2026-10-17: un dictamen con '**CAUSA DETERMINADA.**' da rc=0."}
---

## Origen

Trasladada el 2026-10-17 por pedido de Luis desde Atlas `tasks/backlog/DGX-640` (`tasks/done/DGX-640.md`, `closure_type: relocated`). La evidencia, los dictamenes `crash_atom_*` y el dictamen de correlacion siguen en Atlas (`docs/agent_findings/`, indexados); esta ficha los cita, no los copia.

## Estado heredado (la decision de Luis del 2026-10-12 sigue vigente)

- Veredicto vigente: **CAUSA NO DETERMINADA**. Se descarta cerrar con la correlacion de la cola o con la tendencia de tres boots (refutadas por los cortes sin jobs y por la serie no monotona).
- El cierre exige evidencia NUEVA: para el proximo proceso grande o caida, blackbox guarda RSS y PSI por minuto, `pid`/`ppid`/cgroup/ancestros del proceso de mayor RSS y un recibo externo. La captura prospectiva esta desplegada desde 2026-10-13 (`bb-guardia-proceso`, `blackbox-sample.timer`, `atom-gpu-telemetry.service`); se dispara por crecimiento de VmSize >= 2 GiB, no reconstruye PIDs de boots perdidos.
- Dictamen: `/home/lcasarin/projects/Atlas/docs/agent_findings/2026-10-12_atom_causa_de_los_cortes_oct_2026.md`. Lista de cortes y actualizaciones (1)-(8): `/home/lcasarin/projects/Atlas/tasks/done/DGX-640.md`.
- 2026-10-17: otra caida (reinicio por lentitud, Luis) sin dictamen todavia.

## Relacionadas

`DEBT-ATOM-DEGRADACION-ACELERADA-DE-BOOTS-01`, `DEBT-MOTOR-LLM-CAIDAS-CUDA-SIN-CAUSA-01`, `DEBT-COLAPSOS-11-OCT-SUITES-PYTEST-SIN-TECHO-01`.
