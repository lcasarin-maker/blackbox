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

## Medido 2026-10-17: la atestacion de cobertura por commit tambien es una estampida
Con el kit 10.2.4 el hook post-commit lanza `coverage_attestation --background`, una suite completa con cobertura, por CADA commit. `.simplecode/evidence/coverage_attestation_attempts.jsonl` (103 intentos en 2 dias, 88 el 2026-10-16 y 15 el 2026-10-17): 39 `started`, 28 `could-not-run`, 17 `superseded`, 10 `attested`, 9 `failed`; 103 min de suite sumados. Con la memoria libre en 15 % `earlyoom` mato workers de pytest de esas corridas y de los push (2 pushes caidos por `worker crashed`, sin test fallido). El escalonamiento que pide esta ficha debe cubrir tambien las atestaciones en segundo plano: una a la vez por maquina, y la nueva reemplaza a la anterior ANTES de arrancar, no despues.
