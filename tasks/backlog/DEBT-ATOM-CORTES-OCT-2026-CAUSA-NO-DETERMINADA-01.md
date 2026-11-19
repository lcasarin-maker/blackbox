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

## Estado 2026-11-18 (revision pedida por Luis; la ficha sigue ABIERTA)

- **Su `close_check` sale rc=2 hoy**: `tasks/evidence/DEBT-ATOM-CORTES-OCT-2026-CAUSA-NO-DETERMINADA-01/dictamen.md` no existe (la carpeta tampoco). El veredicto vigente sigue siendo CAUSA NO DETERMINADA.
- **Evidencia nueva desde el 2026-11-03, ninguna determina la causa de octubre**: el 2026-11-09 el primer reinicio en caliente de vuelta a 6.17.0-1032 dio Xid 119 (GSP Timeout), el segundo lo repitio y un apagado en frio lo limpio (`FEATURE-PRUEBA-KERNEL-7-0-1025-UNA-VEZ-01`). Es compatible con un estado del GSP que sobrevive al reinicio en caliente; es una hipotesis para ESE episodio, no una causa probada de los cortes de octubre.
- **Instrumentos nuevos que si pueden dar el dictamen en el proximo corte**: `bb-ultimo-aliento` desplegado (`--estado` fresco, rc=0, medido 2026-11-18); medidor de energia Shelly Plug US Gen4 verificado el 2026-11-18, registrado a 1 Hz en la Dell por `bb-testigo`, que separa `CORTE_DE_RED` de `APAGADO_INTERNO`.
- **Falta para cerrar**: (1) un corte nuevo capturado con esos dos instrumentos, o un dictamen del consumidor de conocimiento que declare la causa; (2) copiarlo aqui como `dictamen.md` con procedencia (repo, ruta, commit, fecha) conteniendo `CAUSA DETERMINADA`.
- **Aviso para el consumidor de conocimiento (su ficha `DGX-683`)**: su `close_check` busca `status: closed` en `tasks/backlog/` de ESTA ficha. Al cerrarla aqui la ficha pasa a `tasks/done/` con `status: done`, y esa ruta deja de existir: ese `close_check` no puede pasar como esta escrito. Hay que reescribirlo en ese repo (por ejemplo, buscar la ficha en `tasks/done/` con `status: done`).

