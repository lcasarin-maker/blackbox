---
id: FEATURE-OWNEAR-EN-BB-LO-QUE-ACTUA-SOBRE-LA-MAQUINA-01
kind: task
domain: MEMORY
title: "Adoptar en bb todo lo que mide o actua sobre la maquina y hoy vive fuera (resto de /srv/ai)"
status: open
severity: P2
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-10-12
close_check: {"cmd": "grep -q ownership_revisado tasks/evidence/FEATURE-OWNEAR-EN-BB-LO-QUE-ACTUA-SOBRE-LA-MAQUINA-01/inventario.txt", "expect": "exit_zero", "porque": "Peticion de Luis 2026-10-12: revisar todo y adueñarse en bb de lo que debe vivir en bb. Cierra con un inventario clasificado de /srv/ai, systemd (usuario y sistema), sysctl, earlyoom, docker y drop-ins, cada pieza con su destino, y lo que corresponde adoptado y vigilado por bb drift."}
---

## Correccion medida (2026-10-12)
`adopted/gpu_governance/` YA existe en bb (admission_check.sh, gpu_lock.sh, monitor_memory.sh, gpu_sampler.sh) y `bb drift` los vigila (47 sujetos, 0 divergentes). Diferencias con /srv/ai: solo `gpu.lock` (estado en ejecucion) y el nombre del muestreador suspendido.
## Lo que sigue fuera de bb en /srv/ai
`gateway/` (active_engine.json, admission_check_wrapper.sh, main.py), `librechat/`, `engines/`, `bakeoff/`, `suspensiones/`, `vendor/`, `logs/`, `models/`, `storage/`. `bin/bb` ya lee `/srv/ai/gateway/active_engine.json` y `/srv/ai/models/_coredumps`.
## Que falta
1. Clasificar cada pieza: mide/actua sobre la maquina (bb) o es la pila de IA (no bb); ubicacion segun el estudio bb/Atlas.
2. Adoptar lo que corresponde, con `bb drift`, sin secretos (`.env` NO).
3. Documentar la relacion de informacion con la pila de IA.
