---
id: DEBT-KIT-SYNC-DE-FLOTA-NO-ESCALONA-LOS-PROYECTOS-01
kind: task
domain: MEMORY
title: "El comando de sync de flota del kit reparte a todos los proyectos a la vez; debe escalonarlos"
status: open
severity: P2
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-10-16
close_check: {"cmd": "grep -rqi escalon .simplecode/kit.lock", "expect": "exit_zero", "porque": "Falta que simplecode (otro repo) escalone el sync; cuando el kit lo declare en su lock/versionado este grep lo vera. Hasta entonces la regla sync_de_flota_escalonado solo la cumple el portero local."}
---

## Medido
Voto de Luis 2026-10-16 (`DECISIONS.md`, `sync_de_flota_escalonado`): el portero local ordena las suites de esta maquina, pero el reparto del sync lo lanza el kit de simplecode. Bloqueada por upstream: debe cambiarse en simplecode. `twiner`, `020` y `atlas` tambien debian confirmar la regla provisional.
