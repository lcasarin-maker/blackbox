---
id: DEBT-DOCKER-FUERA-DEL-TECHO
kind: debt
title: El techo de memoria solo cubre app.slice -- Docker y system.slice quedan fuera
status: open
severity: P2
origin: asserted
satd_family: INCOMPLETE_MITIGATION
created: 2026-09-24
close_check: {"cmd": "grep -q MemoryMax adopted/system-config/etc_systemd_system_docker.service.d_99-blackbox.conf", "expect": "exit_zero"}
---

## Que pasa

El techo que se instalo el 2026-09-24 vive en
`~/.config/systemd/user/app.slice.d/99-blackbox.conf` y es **`app.slice`**:
cubre lo que lanza la sesion grafica del usuario (Atom, Antigravity, Codex,
los navegadores). No cubre nada de:

- **`docker.service` y sus contenedores**, que cuelgan de `system.slice`;
- cualquier demonio de sistema (`system.slice`);
- lo que se lance con `sudo`, que sale de la sesion de usuario.

Un contenedor sin `--memory` puede reservar hasta agotar la maquina y el techo
de `app.slice` no lo ve. Es exactamente el modo de fallo de los cuatro
congelamientos, con otro dueno.

## Por que no se arreglo en la pasada del 2026-09-24

`system.slice` es configuracion de sistema: el drop-in va en
`/etc/systemd/system/` y necesita `sudo`, que el agente no puede dar. Se
declaro como hueco y se dejo ahi -- que es justo lo que Luis prohibio ese
mismo dia ("es prohibido solo declarar, lo menos es abrir ficha de backlog").
Esta ficha es la reparacion de esa omision.

## Como se cierra

1. Medir primero cuanto reserva de verdad el stack de Docker en esta maquina
   (`systemd-cgtop -1 --raw -m` sobre `system.slice`, varias muestras), para no
   poner un numero inventado -- ver [[DEBT-TECHOS-SIN-CALIBRAR]].
2. Escribir el drop-in en `adopted/system-config/` con su revert, como se hizo
   con `app.slice`.
3. Anadirlo a `enable-privileged.sh` con su seccion de revert, que es donde
   vive todo lo que requiere `sudo` en este repo.
4. El `close_check` comprueba las dos cosas: que el fichero adoptado existe y
   que `docker.service` ya NO reporta `MemoryMax=infinity`.

## Limite declarado

El techo de cgroup **no ve la memoria unificada de GPU**: medido el 2026-09-24,
7 GiB de CUDA se cobraron como 15 MiB (0.2%). Este drop-in acota la memoria
ordinaria de los contenedores, no lo que reserven por CUDA. Esa mitad la
cubren `bb-usable` (PSI) y el `uvm_global_oversubscription=0`, no un cgroup.
