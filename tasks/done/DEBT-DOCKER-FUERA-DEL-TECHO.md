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
close_check: {"cmd": "grep -qx 17179869184 /sys/fs/cgroup/docker.slice/memory.max", "expect": "exit_zero", "porque": "mide el SUJETO -- el techo puesto en la maquina -- no el fichero que lo propone. Control negativo: el mismo comando contra system.slice (memory.max = max) devuelve 1. El numero se fija a proposito en vez de comprobar solo que NO es `max`: un techo que se afloja en silencio tiene que romper este criterio, y por eso rompio cuando 7061336 lo bajo de 32G a 16G. Ver la seccion `Por que el numero de este criterio cambio`."}
evidence: {"pass": "tasks/evidence/DEBT-DOCKER-FUERA-DEL-TECHO/despues.txt", "fail": "tasks/evidence/DEBT-DOCKER-FUERA-DEL-TECHO/antes.txt", "e2e": "tasks/evidence/DEBT-DOCKER-FUERA-DEL-TECHO/mezcla-daemon-json.txt", "pass_recalibrado": "tasks/evidence/DEBT-DOCKER-FUERA-DEL-TECHO/despues-16g.txt"}
reason: "relocated_prior_verification: el arreglo -- el drop-in de docker.slice, la seccion 9 de enable-privileged.sh y su revert -- aterrizo en a16b551, un commit anterior. Este commit solo mueve la ficha y anade la evidencia de que el techo quedo puesto: Luis corrio sudo ./enable-privileged.sh y reinicio el demonio el 2026-09-24, y verificado sobre la maquina docker.slice/memory.max = 34359738368, los 5 contenedores cuelgan de /docker.slice/, cero quedan en system.slice, y el runtime de nvidia sobrevivio a la mezcla de daemon.json. (Ese 34359738368 es lo que se midio el 2026-09-24 y se deja como esta: es el registro. Hoy el techo son 16G por 7061336, y el criterio de cierre se recalibro a 17179869184 -- ver la seccion `Por que el numero de este criterio cambio`.)"
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
grep -qx 17179869184 /sys/fs/cgroup/docker.slice/memory.max
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
- `pass` -- `despues.txt`: `docker.slice/memory.max = 34359738368` **tal como estaba
  el 2026-09-24**, los 5
  contenedores bajo `/docker.slice/`, **0** en `system.slice`, y el runtime de
  nvidia intacto en el fichero real. `system.slice` bajo de 19.5 a 9.99 GiB
  porque los contenedores salieron de ahi.
- `pass_recalibrado` -- `despues-16g.txt`: el mismo sujeto el 2026-09-25, con el
  techo ya en 17179869184, y los dos controles negativos corridos -- el criterio
  nuevo contra `system.slice` da 1, y el criterio VIEJO contra el sujeto de hoy da
  1, que es justo lo que hizo bloquear el push.

## Lo que este cierre NO arregla

El reparto sigue sin calibrar: [[DEBT-TECHOS-SIN-CALIBRAR]]. Cuando se escribio
esto eran 48G + 32G = 80G sobre 121.1 GiB, dejando 41 GiB para el kernel, el
resto de `system.slice` y la memoria unificada de GPU -- y ese ultimo numero
nadie lo habia medido. **Ya se midio**: 86.0 GiB de pico sobre 18 733 muestras,
y con eso el reparto de hoy (48G + 16G = 64G) sigue sin componer. Eso es lo que
`python3 -m tools.presupuesto_memoria --check` reporta, y por lo que
[[DEBT-TECHOS-SIN-CALIBRAR]] sigue abierta.

## Por que el numero de este criterio cambio

El 2026-09-25, `backlog-verifier` bloqueo un push con
`FRAUD DETECTED: Found 1 closed tasks whose findings still reproduce` sobre
esta ficha. Tenia razon en lo que mide y conviene ser exacto sobre lo que NO
significa:

- **El arreglo no se deshizo.** Los contenedores siguen colgando de
  `docker.slice` (6 scopes) y quedan **0** en `system.slice`, que era el
  hallazgo. Eso esta medido en `despues-16g.txt`.
- **Lo que se rompio fue el criterio**, porque el techo se APRETO a proposito:
  `7061336` lo bajo de 32G a 16G. El commit trae la medida que lo justifica --
  con 32G el presupuesto de GPU queda en 37.1 GiB y la serie lo supera el
  75.4 % del tiempo; con 16G queda en 53.1 GiB y lo supera el 0.9 %. Sin ese
  recorte la alarma del abanico avisa siempre, que es no avisar.

O sea: el gate cazo un cambio real del sujeto que nadie habia reflejado en la
ficha. Eso es el instrumento funcionando, no un falso positivo -- y es la
razon de fijar el numero en vez de comprobar solo que no es `max`.

Lo que **no** se hizo: aflojar el criterio a `test $(cat ...) != max`. Eso lo
habria dejado verde para siempre y habria dejado pasar el caso que importa, que
es un techo aflojado en silencio.

`antes.txt` y `despues.txt` NO se tocan: son el registro de lo que se midio el
2026-09-24 y reescribirlos seria inventar que el techo siempre fue 16G.

## Limite declarado

El techo de cgroup **no ve la memoria unificada de GPU**: medido el 2026-09-24,
7 GiB de CUDA se cobraron como 15 MiB (0.2%). `nemotron-server` es vLLM: sus
pesos viven en memoria unificada y **no** estan en los 9.9 GiB que el cgroup le
cobra. Este techo acota su memoria ordinaria, no la de GPU. Esa mitad la cubren
`bb-usable` (PSI) y `uvm_global_oversubscription=0`, no un cgroup.
