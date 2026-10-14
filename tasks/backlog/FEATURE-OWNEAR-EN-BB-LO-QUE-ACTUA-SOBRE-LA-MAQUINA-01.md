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

## Avance 2026-10-12 (inventario y adopcion)
Inventario clasificado, pieza por pieza, en `tasks/evidence/FEATURE-OWNEAR-EN-BB-LO-QUE-ACTUA-SOBRE-LA-MAQUINA-01/inventario.txt` (10 categorias: /srv/ai, systemd de usuario y de sistema, docker, sysctl, /etc/default, slices, udev/modprobe, cron/timers, otros escritos por `enable-privileged.sh`).

Hechos 1 y 3. Del 2, adoptadas 12 piezas que eran de bb y estaban fuera de `bb drift`: `/srv/ai/gateway/admission_check_wrapper.sh` (directorio nuevo `adopted/gateway/`), `bb-guardia-proceso.service`, los cuatro ficheros de core que escriben las secciones 1 y 2 de `enable-privileged.sh` en linea (`coredump.conf.d`, `system.conf.d`, `user.conf.d`, `limits.d/99-blackbox-core.conf`), `/etc/default/earlyoom`, `/etc/docker/daemon.json`, `/etc/default/grub`, `/etc/default/grub.d/kdump-tools.cfg` y la pareja `journal-udp-forward` (la IP destino va redactada; `bb drift` aplica la misma redaccion antes de comparar). `bb drift`: 47 -> 59 sujetos, 0 divergentes. Guardia nueva `tests/test_adopted_sin_secretos.py`, con control negativo de secretos sembrados.

Pendiente (por eso el inventario NO lleva la marca del close_check):
- `/etc/audit/rules.d/10-blackbox-signals.rules` (seccion 7): de bb, sin adoptar. Leerla pide root, y `bb drift` corre como usuario, asi que la veria AUSENTE: hace falta un camino de comparacion, no solo una copia.
- crontabs de otros usuarios (`/var/spool/cron/crontabs`): ilegibles sin root, sin revisar.

## Avance 2026-10-14: los dos pendientes de root ya se leyeron (via bb-root-run)
Luis instalo `bb-root-run` y corrieron `audit-rules-leer` y `crontabs-leer` (rc=0, salida legible en `/var/lib/bb-root-run/`). Hechos: `/etc/audit/rules.d` tiene 4 ficheros: `10-blackbox-signals.rules` (de bb, instalada por `enable-privileged.sh`), `zz-blackbox-backlog.rules` (de bb, `-b 32768`), `audit.rules` (la base del paquete `auditd`) y `99-reboot.rules` (observa `systemctl`, `reboot`, `shutdown`, `loginctl` con la clave `reboot_cmd`; de origen externo a bb y SIN adoptar, aunque el instalador la cita y la compensa). Crontabs: 1 (el del usuario), 4 entradas: 3 de la flota simplecode y 1 de Twiner; ninguna es de bb, asi que no se adopta. Falta: copiar a `adopted/` las reglas de bb y la de `reboot_cmd` y darle a `bb drift` un camino para compararlas (corre sin root y vera `/etc/audit` AUSENTE): leer la salida de `audit-rules-leer` en `/var/lib/bb-root-run/`.
