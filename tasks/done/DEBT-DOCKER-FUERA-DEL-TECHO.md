---
id: DEBT-DOCKER-FUERA-DEL-TECHO
kind: debt
title: Los 5 contenedores cuelgan de system.slice sin techo agregado, y tres sin techo alguno
status: done
closure_type: relocated_prior_verification
severity: P1
origin: asserted
satd_family: INCOMPLETE_MITIGATION
created: 2026-09-24
closed_at: 2026-09-24
close_check: {"cmd": "grep -qx 34359738368 /sys/fs/cgroup/docker.slice/memory.max", "expect": "exit_zero", "porque": "mide el SUJETO -- el techo puesto en la maquina -- no el fichero que lo propone. Control negativo: el mismo comando contra system.slice devuelve 1."}
evidence: {"pass": "tasks/evidence/DEBT-DOCKER-FUERA-DEL-TECHO/despues.txt", "fail": "tasks/evidence/DEBT-DOCKER-FUERA-DEL-TECHO/antes.txt", "e2e": "tasks/evidence/DEBT-DOCKER-FUERA-DEL-TECHO/mezcla-daemon-json.txt"}
reason: "relocated_prior_verification: el arreglo -- el drop-in de docker.slice, la seccion 9 de enable-privileged.sh y su revert -- aterrizo en a16b551, un commit anterior. Este commit solo mueve la ficha y anade la evidencia de que el techo quedo puesto: Luis corrio sudo ./enable-privileged.sh y reinicio el demonio el 2026-09-24, y verificado sobre la maquina docker.slice/memory.max = 34359738368, los 5 contenedores cuelgan de /docker.slice/, cero quedan en system.slice, y el runtime de nvidia sobrevivio a la mezcla de daemon.json."
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

## Root Cause

El techo instalado ese mismo dia era `app.slice`, y se dio por hecho que Docker
colgaba de `docker.service`. Medirlo mostro que no: los contenedores son cgroups
HERMANOS del demonio, bajo `system.slice/docker-<id>.scope`. Un drop-in sobre
`docker.service` no habria acotado nada, y el informe habria dicho que si.

## Regression Test

```
grep -qx 34359738368 /sys/fs/cgroup/docker.slice/memory.max
```

Lee la maquina, no el fichero que propone el techo. Control negativo corrido:
el mismo comando contra `system.slice/memory.max` devuelve 1, asi que sabe
decir que no.

## Verification Evidence

- `fail` -- `antes.txt`: el estado que motivo la ficha. `nemotron-server` en
  `system.slice/docker-....scope`, `system.slice memory.max = max`, tres
  contenedores con `Memory=0`, y los techos declarados sumando 125G sobre
  121.1 GiB de maquina.
- `e2e` -- `mezcla-daemon-json.txt`: la mezcla de `daemon.json` conserva
  `runtimes.nvidia.path` y es idempotente.
- `pass` -- `despues.txt`: `docker.slice/memory.max = 34359738368`, los 5
  contenedores bajo `/docker.slice/`, **0** en `system.slice`, y el runtime de
  nvidia intacto en el fichero real. `system.slice` bajo de 19.5 a 9.99 GiB
  porque los contenedores salieron de ahi.

## Lo que este cierre NO arregla

El reparto sigue sin calibrar: [[DEBT-TECHOS-SIN-CALIBRAR]]. 48G + 32G = 80G
sobre 121.1 GiB deja 41 GiB para el kernel, el resto de `system.slice` y la
memoria unificada de GPU -- y ese ultimo numero nadie lo ha medido.

## Limite declarado

El techo de cgroup **no ve la memoria unificada de GPU**: medido el 2026-09-24,
7 GiB de CUDA se cobraron como 15 MiB (0.2%). `nemotron-server` es vLLM: sus
pesos viven en memoria unificada y **no** estan en los 9.9 GiB que el cgroup le
cobra. Este techo acota su memoria ordinaria, no la de GPU. Esa mitad la cubren
`bb-usable` (PSI) y `uvm_global_oversubscription=0`, no un cgroup.
