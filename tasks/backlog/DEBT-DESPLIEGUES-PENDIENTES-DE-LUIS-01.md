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
