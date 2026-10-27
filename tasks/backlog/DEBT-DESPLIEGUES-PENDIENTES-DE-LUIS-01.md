---
id: DEBT-DESPLIEGUES-PENDIENTES-DE-LUIS-01
kind: task
domain: MEMORY
title: "Despliegues que solo Luis puede ejecutar: portero, escalon, drop-in y laboratorio OCI"
status: open
severity: P1
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-10-12
close_check: {"cmd": "grep -q despliegues_hechos tasks/evidence/DEBT-DESPLIEGUES-PENDIENTES-DE-LUIS-01/despliegue.txt", "expect": "exit_zero", "porque": "Luis dijo el 2026-10-12 que no ejecutara los despliegues hasta terminar la revision. Cierra cuando cada despliegue este hecho, verificado con su comando, y con `bb drift` en 0 divergentes."}
---

## Pendientes (comandos exactos en `tasks/evidence/DEBT-COLAPSOS-11-OCT-SUITES-PYTEST-SIN-TECHO-01/despliegue.txt` y en el informe del portero)
1. Portero: copiar el drop-in `app-com.anthropic.Claude-.scope.d/50-bb-portero.conf` y `systemd/bb-portero.service` a `~/.config/systemd/user/`, `daemon-reload`, `enable --now bb-portero.service`.
2. Escalon: `sudo cp systemd/bb-usable.service /etc/systemd/system/` + `daemon-reload` + `restart bb-usable.service`; re-adoptar la unidad y `bb drift`.
3. Laboratorio OCI nivel 2: `sudo bash tools/portero_docker_lab.sh up` (cuando el agente lo entregue).
4. Decisiones de oomd (ficha propia).

## Avance 2026-10-14 (lote 'cierra las pendientes conforme a la opcion recomendada'): espera un disparador, no una decision
Medido hoy, punto por punto. (1) Portero: `systemctl --user is-active bb-portero.service` = active y `is-enabled` = enabled (hecho); el drop-in NO esta: `~/.config/systemd/user/app-com.anthropic.Claude-.scope.d/` no existe y el scope vivo `app-com.anthropic.Claude-56651.scope` da `MemoryMax=infinity`, `TasksMax=152777`. (2) Escalon: `cmp /etc/systemd/system/bb-usable.service systemd/bb-usable.service` rc=0 y igual a la copia adoptada (hecho). (3) Laboratorio OCI: `/run/bb-lab` no existe (no levantado). (4) oomd: ficha propia.
Disparador: que Luis despliegue lo que queda (son escrituras suyas, no de un agente). Pasos exactos: `mkdir -p ~/.config/systemd/user/app-com.anthropic.Claude-.scope.d && cp systemd/app-com.anthropic.Claude-.scope.d/50-bb-portero.conf ~/.config/systemd/user/app-com.anthropic.Claude-.scope.d/ && systemctl --user daemon-reload` (aplica a los scopes que la app cree despues: MemoryMax=35G, TasksMax=1230); en la ventana del motor de 60 min que anuncia Luis, `sudo bash tools/portero_docker_lab.sh up` y `... prueba`; luego `bb drift` y escribir `despliegues_hechos` con esas salidas en `tasks/evidence/DEBT-DESPLIEGUES-PENDIENTES-DE-LUIS-01/despliegue.txt`.

## Avance 2026-10-26 19:49 -0600: drop-in del portero desplegado por Luis; aplica tambien a scopes vivos

Luis copio `50-bb-portero.conf` a `~/.config/systemd/user/app-com.anthropic.Claude-.scope.d/` y corrio `daemon-reload`. Medido despues:
`cmp` contra `systemd/app-com.anthropic.Claude-.scope.d/50-bb-portero.conf` sin diferencias; `systemctl --user show` de los tres scopes
vivos (`454119`, `3053639`, `2469924`) da `MemoryMax=37580963840` (35 GiB), y el de `2469924` ademas `TasksMax=1230` y `DropInPaths`
con el archivo. Un scope inexistente da `DropInPaths=` vacio (control negativo). Esto contradice el comentario del propio archivo
("solo afecta a scopes NUEVOS"): el `daemon-reload` reaplica los topes a los scopes en marcha. Consumo en ese momento: 4.9, 0.1 y
18.9 GiB de 35, `oom_kill` 0 en los tres. Punto 1 de esta ficha: hecho. Quedan los puntos 3 (laboratorio OCI, ventana del motor) y 4.
