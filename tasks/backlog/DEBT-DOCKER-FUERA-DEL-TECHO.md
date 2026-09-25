---
id: DEBT-DOCKER-FUERA-DEL-TECHO
kind: debt
title: Los 5 contenedores cuelgan de system.slice sin techo agregado, y tres sin techo alguno
status: open
severity: P1
origin: asserted
satd_family: INCOMPLETE_MITIGATION
created: 2026-09-24
close_check: {"cmd": "grep -qx 34359738368 /sys/fs/cgroup/docker.slice/memory.max", "expect": "exit_zero", "porque": "mide el SUJETO -- el techo puesto en la maquina -- no el fichero que lo propone. Un close_check sobre adopted/ pasaria con el techo sin aplicar."}
---

## Que pasa

El techo instalado el 2026-09-24 es `app.slice` (48G/4G): cubre la sesion
grafica. Docker **no** esta ahi. Medido hoy en ATOM:

```
$ cat /proc/<pid de nemotron-server>/cgroup
0::/system.slice/docker-eaee36ede8a8....scope
```

Los contenedores cuelgan **directamente de `system.slice`**, cada uno en su
propio scope. Dos consecuencias, las dos medidas:

1. **Un drop-in sobre `docker.service` no los toca.** El demonio y los
   contenedores son cgroups hermanos, no padre e hijo. La propuesta original de
   esta ficha (drop-in en `docker.service`) estaba equivocada.
2. **No hay techo agregado.** `system.slice` esta en `memory.max = max`, con
   19.5 GiB en uso y 20.5 GiB de pico.

Y tres de los cinco contenedores no tienen techo propio:

| contenedor | ahora | pico | techo |
|---|---|---|---|
| nemotron-server (vLLM) | 9.9G | 10.0G | 75G |
| atlas-pgvector | 0.1G | 0.1G | 2G |
| librechat | 0.5G | 0.7G | **SIN TECHO** |
| mongo-librechat | 0.3G | 0.4G | **SIN TECHO** |
| aequitas-pg | 0.1G | 0.1G | **SIN TECHO** |

Cualquiera de los tres sin techo puede reservar hasta agotar la maquina, y el
techo de `app.slice` no lo ve. Es el modo de fallo exacto de los cuatro
congelamientos, con otro dueno. Sube a **P1** por eso: no es un hueco teorico,
son tres procesos vivos ahora mismo sin nada que los acote.

## Como se cierra

Docker admite `"cgroup-parent": "docker.slice"` en `/etc/docker/daemon.json`.
Con eso todos los contenedores -- tambien los futuros -- cuelgan de una slice
propia, y **un solo** drop-in en `/etc/systemd/system/docker.slice.d/` los acota
a todos. El fichero adoptado y su revert van en `adopted/system-config/`, y la
aplicacion en `enable-privileged.sh`, que es donde vive todo lo que pide `sudo`.

El numero sale de [[DEBT-TECHOS-SIN-CALIBRAR]], que es donde vive el reparto
del presupuesto de los 121.1 GiB.

## Estado 2026-09-24: el artefacto esta escrito, el techo NO esta puesto

Hecho y versionado:

- `adopted/system-config/etc_systemd_system_docker.slice.d_99-blackbox.conf`
  -- `MemoryMax=32G`, `MemorySwapMax=4G`, con el origen de los 32G por escrito.
- `enable-privileged.sh` seccion 9: mezcla `cgroup-parent` en
  `/etc/docker/daemon.json` **sin sobrescribirlo** (el runtime de nvidia
  sobrevive -- control negativo corrido, `tasks/evidence/.../mezcla-daemon-json.txt`),
  copia el drop-in, y **no reinicia el demonio**: tirar los contenedores es
  decision del dueno.
- Su revert en la seccion de `--revert`, con copia previa de `daemon.json`.

Falta lo unico que un agente no puede hacer: `sudo`.

```
sudo ./enable-privileged.sh
sudo systemctl daemon-reload && sudo systemctl restart docker   # tira los 5 contenedores
```

La ficha sigue ABIERTA a proposito. Su `close_check` lee
`/sys/fs/cgroup/docker.slice/memory.max`, que es la maquina, no el fichero que
lo propone: mientras el techo no este puesto de verdad, esto es deuda abierta
por mucho que el artefacto este completo.

## Limite declarado

El techo de cgroup **no ve la memoria unificada de GPU**: medido el 2026-09-24,
7 GiB de CUDA se cobraron como 15 MiB (0.2%). `nemotron-server` es vLLM: sus
pesos viven en memoria unificada y **no** estan en los 9.9 GiB que el cgroup le
cobra. Este techo acota su memoria ordinaria, no la de GPU. Esa mitad la cubren
`bb-usable` (PSI) y `uvm_global_oversubscription=0`, no un cgroup.
