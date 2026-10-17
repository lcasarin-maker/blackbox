---
id: DEBT-DOCKER-SLICE-TOPE-VS-TOPES-DE-CONTENEDORES-01
kind: task
domain: MEMORY
title: "docker.slice (14 GiB) no cabe con los topes de sus contenedores; dimensionar y persistir los topes"
status: open
severity: P2
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-10-12
close_check: {"cmd": "grep -q docker_slice_dimensionado tasks/evidence/DEBT-DOCKER-SLICE-TOPE-VS-TOPES-DE-CONTENEDORES-01/medicion.txt", "expect": "exit_zero", "porque": "Medido 2026-10-12: docker.slice tiene MemoryMax 14 GiB y el pico de vLLM (12.5 GiB) mas el resto lo llena casi entero (`MemoryCurrent` 14.75 GB de 15.03 GB). Los topes individuales (nemotron 75 GiB, pgvector 2, librechat 3, mongo 2, proyecto-A-pg 2) suman 84 GiB: el tope real es el del slice. Cierra con una decision votada de dimensionamiento y los topes persistidos en quien crea cada contenedor (hoy `docker update` en vivo, que se pierde al recrear)."}
---

## Medido
- `bb portero contenedores` (lectura en seco) no acota ninguno: el reparto sale negativo (-758 180 kB para librechat).
- Los contenedores se crean con `docker run` (sin etiquetas de compose): hallar quien los crea.
- Topes aplicados por `docker update` el 2026-10-12: librechat 3g, mongo-librechat 2g, proyecto-A-pg 2g (4x pico medido, sin swap, pids 2048) y atlas-pgvector swap 0.
## Que falta
Decidir el tope de docker.slice frente al presupuesto de slices votado el 2026-09-27 (42/14/12) o bajar el de vLLM; persistir; revisar tras el despliegue del runtime OCI (`FEATURE-CONTENEDORES-TOPE-PROPIO-Y-RUNTIME-OCI-01`).

## Avance 2026-10-13
Voto de Luis: `docker.slice` a 16 GiB (registrado en `DECISIONS.md`). Medido en `tasks/evidence/DEBT-DOCKER-SLICE-TOPE-VS-TOPES-DE-CONTENEDORES-01/medicion.txt`: uso 12,06 GiB de 14 (1,94 libres); con 16 quedan 3,94. El repo ya lo trae: drop-in adoptado, `enable-privileged.sh` (valor esperado 17179869184) y `DECISIONS.md`. Sigue abierta porque faltan dos cosas: aplicarlo (`sudo systemctl daemon-reload && sudo systemctl restart docker`, tira vLLM) y persistir los topes de contenedor en quien los crea (`docker update` en vivo no sobrevive a recrearlos); el `close_check` exige el marcador que se escribe tras comprobar el techo en la maquina.

## Avance 2026-10-14 (lote 'cierra las pendientes conforme a la opcion recomendada'): espera un disparador, no una decision
Medido hoy: `systemctl show docker.slice -p MemoryMax` = 15032385536 (14 GiB): el voto de 16 GiB sigue sin aplicar. Disparador: la ventana del motor de 60 min que anuncia Luis (reiniciar docker tira vLLM) con sudo de Luis. Pasos exactos: `sudo install -D -m 0644 adopted/pendiente-de-despliegue/etc_systemd_system_docker.slice.d_99-blackbox.conf /etc/systemd/system/docker.slice.d/99-blackbox.conf && sudo systemctl daemon-reload && sudo systemctl restart docker`; comprobar `systemctl show docker.slice -p MemoryMax` = 17179869184; `git mv` del fichero a `adopted/system-config/`; escribir `docker_slice_dimensionado` con esa salida en `medicion.txt`. La segunda mitad (persistir los topes en quien crea cada contenedor) no pide root y sigue pendiente aparte.

## Avance 2026-10-15: techo de 16 GiB aplicado en la maquina; falta la segunda mitad
Ventana del motor con sudo de Luis (`tasks/evidence/VENTANA-VLLM-20261015/ventana.sh`, log literal ahi): copia del drop-in de 14 G en `/var/lib/blackbox/99-blackbox.conf.14G` (sha256 b963e13b...), instalado el drop-in votado, `daemon-reload` + `restart docker`. Medido: `MemoryMax=15032385536` antes y `MemoryMax=17179869184` despues (= 16 GiB); `cmp` del repo contra `/etc/systemd/system/docker.slice.d/99-blackbox.conf` sin diferencias; el drop-in ya vive en `adopted/system-config/`. Con el motor arriba `docker.slice` marca `MemoryCurrent` 11.47 GB. NO se escribe `docker_slice_dimensionado`: la ficha exige tambien persistir los topes por contenedor en quien los crea (sin root, pendiente aparte).

## Avance 2026-10-16: BLOQUEADA, ningun creador vive en este repo
Medido con `docker inspect` (tabla completa en `medicion.txt`). Librechat y mongo-librechat ya no existen. Los contenedores vivos y quien los crea:
- `nemotron-server` (75 GiB, swap 75 GiB, sin pids): `/srv/ai/gateway/main.py`, `build_vllm_args`, fuera de todo repo (blackbox solo adopta `admission_check_wrapper.sh`). Ya persiste memory y memory-swap; falta `--pids-limit`.
- `atlas-pgvector` (2 GiB, swap 2 GiB, sin pids): repo Atlas, `deploy/atlas-pgvector.sh`, comando `docker run` de `levantar()`. Ya persiste memory y memory-swap; añadir `--pids-limit=2048`.
- `proyecto-A-pg` (2 GiB, swap 2 GiB, pids 2048): creador NO ENCONTRADO en ningun repo hermano. El tope se aplico con `docker update` y se pierde al recrearlo. Flags: `--memory=2g --memory-swap=2g --pids-limit=2048`.
- `nemotron-bolt-test` (48 GiB, swap 96 GiB, sin pids): creador NO ENCONTRADO; la receta `Atlas/playbooks/nemotron-bolt/README.md` crea `nemotron-bolt` con `--memory 48g` y sin `--memory-swap`. Si ese contenedor debe vivir: `--memory-swap=48g --pids-limit=2048`.
- Parados y de un solo uso (`proyecto-A-etapa1-20260912`, `proyecto-A-audit-20260927`, dos de documenso): sin accion, retirar con `docker rm` cuando Luis lo decida.
Quedan por hacer: Atlas (una linea en su script), la sesion del gateway en `/srv/ai/gateway/main.py`, y localizar o crear el creador de `proyecto-A-pg`. Cuando los tres esten persistidos, escribir `docker_slice_dimensionado` con la salida de `docker inspect` recreado.
