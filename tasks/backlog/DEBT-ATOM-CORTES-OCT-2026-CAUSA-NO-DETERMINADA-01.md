---
id: DEBT-ATOM-CORTES-OCT-2026-CAUSA-NO-DETERMINADA-01
kind: task
domain: HARDWARE
title: "Cortes de la ATOM de octubre 2026 sin causa determinada (trasladada de una referencia externa)"
status: open
severity: P1
origin: asserted
satd_family: UNCLASSIFIED_DEBT
created: 2026-10-17
close_check: {"cmd": "grep -q \"CAUSA DETERMINADA\" tasks/evidence/DEBT-ATOM-CORTES-OCT-2026-CAUSA-NO-DETERMINADA-01/dictamen.md", "expect": "exit_zero", "porque": "Especificacion pendiente: el archivo no existe hoy y el criterio falla. El cierre lo mide una evidencia LOCAL, sin leer el checkout de otro repo (boleta #18 A del 2026-11-01): cuando el dictamen del consumidor de conocimiento sobre los cortes de octubre declare la causa, se copia aqui como `dictamen.md` con su procedencia (repo, ruta, commit y fecha). Cierra solo si contiene `CAUSA DETERMINADA`; con exit_zero, porque el criterio original esperaba empty_stdout y el verificador imprime 'OK 1 archivo(s)...' cuando pasa. Control positivo corrido 2026-10-17 sobre el dictamen de origen: con '**CAUSA DETERMINADA.**' da rc=0."}
---

## Origen

Trasladada el 2026-10-17 por pedido de Luis desde una referencia externa (una referencia externa, `closure_type: relocated`). La evidencia, los dictamenes `crash_atom_*` y el dictamen de correlacion siguen en el consumidor de conocimiento (`docs/agent_findings/`, indexados); esta ficha los cita, no los copia.

## Estado heredado (la decision de Luis del 2026-10-12 sigue vigente)

- Veredicto vigente: **CAUSA NO DETERMINADA**. Se descarta cerrar con la correlacion de la cola o con la tendencia de tres boots (refutadas por los cortes sin jobs y por la serie no monotona).
- El cierre exige evidencia NUEVA: para el proximo proceso grande o caida, blackbox guarda RSS y PSI por minuto, `pid`/`ppid`/cgroup/ancestros del proceso de mayor RSS y un recibo externo. La captura prospectiva esta desplegada desde 2026-10-13 (`bb-guardia-proceso`, `blackbox-sample.timer`, `atom-gpu-telemetry.service`); se dispara por crecimiento de VmSize >= 2 GiB, no reconstruye PIDs de boots perdidos.
- Dictamen: una referencia externa. Lista de cortes y actualizaciones (1)-(8): una referencia externa.
- 2026-10-17: otra caida (reinicio por lentitud, Luis) sin dictamen todavia.

## Relacionadas

`DEBT-ATOM-DEGRADACION-ACELERADA-DE-BOOTS-01`, `DEBT-MOTOR-LLM-CAIDAS-CUDA-SIN-CAUSA-01`, `DEBT-COLAPSOS-11-OCT-SUITES-PYTEST-SIN-TECHO-01`.
