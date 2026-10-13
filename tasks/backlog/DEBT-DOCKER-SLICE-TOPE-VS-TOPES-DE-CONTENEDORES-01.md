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
