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

## Medido 2026-10-17, 09:10 (la ATOM "super sluggish"): un sync de flota ya causo una hora de suite
- 08:20:26-27: cuatro scopes `run-r*` con `.simplecode/run.py simplecode.verification.*` de simplecode arrancaron dentro del mismo segundo (journal del usuario), mas un servicio batch de otro proyecto desde las 08:16.
- 08:23: otra sesion commiteo `chore(kit): sync satellite kit to simplecode 10.2.6` (2d8df6e1) en ESTE repo; el anterior fue `10.2.4` a las 23:48 del dia 16 (dos syncs en 9 h). El hook post-commit lanzo la atestacion de cobertura.
- `coverage_attestation_attempts.jsonl`: 08:23:39 `started` pid 155078; 09:24:43 `failed` tras 61.1 min (la suite sin carga tarda 4-6 min), y un segundo intento del mismo SHA `failed` tras 24.9 min. El log: `3 failed, 3726 passed ... in 3659.62s`, un worker de xdist caido (`worker 'gw1' crashed`) y dos fallas que pasan solas (`test_el_que_mas_crece_lleva_su_origen_en_la_muestra`: 1 passed en 2 s).
- Las muestras de `bb` 08:24-09:24 nombran un solo worker de pytest-xdist al 100 % de un nucleo durante 60 minutos; carga 11-16; a las 09:15-09:19 `MemAvailable` bajo a 21 GiB con `mem_full` 5.6 %.
Conclusion: el escalonamiento que pide esta ficha debe cubrir tambien lo que un commit de sync dispara en cada proyecto (la atestacion completa), no solo el reparto del comando de sync.
