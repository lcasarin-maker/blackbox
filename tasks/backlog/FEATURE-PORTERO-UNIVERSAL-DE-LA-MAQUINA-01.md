---
id: FEATURE-PORTERO-UNIVERSAL-DE-LA-MAQUINA-01
kind: task
domain: MEMORY
title: "Portero universal y automatico de la maquina: cola FIFO y topes por trabajo dentro de cada slice"
status: open
severity: P1
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-10-12
close_check: {"cmd": "grep -q portero_universal_probado tasks/evidence/FEATURE-PORTERO-UNIVERSAL-DE-LA-MAQUINA-01/medicion.md", "expect": "exit_zero", "porque": "Los dos colapsos del 11-oct fueron una estampida de git push con pre-push (suite completa) lanzados a la vez por seis sesiones; cada uno corria sin tope propio dentro de un app.slice de 42 GiB compartido, y cerca del techo el kernel se estanca en vez de matar. Cierra cuando haya una medicion con el portero activo: tres suites lanzadas a la vez entran de una en una, cada una bajo su tope, sin que ningun llamador cambie, y el estancamiento no se reproduce. Frase obligatoria en medicion.md: portero_universal_probado."}
---

## Decision de ubicacion (voto de Luis 2026-10-12, a partir del estudio bb/Atlas)

La pieza vive en bb: mide y actua sobre la maquina y no necesita a Atlas (regla del analisis `analisis_frontera_bb_atlas.md`: lo que actua sobre la maquina sin Atlas va a bb). bb es publico y debe funcionar solo. Atlas conserva su cola y consulta el mismo portero por archivo/CLI; el kit de simplecode puede usarlo, pero el portero NO depende de que ningun llamador lo invoque: debe ser universal y automatico.

## Que se midio (2026-10-12, scopes desechables, con control negativo)

- Delegacion: `user@1000.service` delega `cpu memory pids`; se puede poner tope a un scope EN MARCHA: `systemctl --user set-property --runtime <scope> MemoryMax=300M MemorySwapMax=0` -> `memory.max=314572800`, `swap.max=0`.
- Reasignar: escribir un pid en `cgroup.procs` de otro scope dentro de lo delegado lo mueve (pid 844379 paso de `bbprobeA.scope` a `bbprobeB.scope`). Control negativo: mover a `system.slice` o `user-1000.slice` da `Permiso denegado`.
- Congelar/descongelar un scope en marcha: `cgroup.freeze` 1 y 0.
- No medido: que la memoria ya cargada NO se mueve con el proceso en cgroup v2 (comportamiento conocido del kernel, no probado aqui): reasignar sirve al arrancar el trabajo, no al final.

## Diseno

1. **Demonio de usuario `bb-portero`** (lee /proc cada 1-2 s, barato) que detecta ARBOLES de trabajo pesado sin depender del llamador. Criterio por crecimiento y forma, no por nombre: un arbol cuya suma de RSS o numero de procesos cruza un umbral medido, o cuyo ancestro es un hook `pre-push`/`pre-commit`, `pytest`, `java`, `dotnet`. El origen de cada arbol (quien lo lanzo) se identifica con el registro de origen portado de `witr` (ver `bb origen`).
2. **Topes dentro de cada slice**: cada arbol admitido se mueve a su propio cgroup hijo bajo `app.slice` con `MemoryMax` y `MemoryHigh` por clase (suite: 20G, swap 0; `MemoryHigh` al 90 % para que el reclaim empiece antes del muro) y `TasksMax`. Presupuesto jerarquico: slice -> clase -> trabajo.
3. **Cola FIFO**: con dos o mas arboles pesados, el mas antiguo corre y los demas se congelan (`cgroup.freeze`) en orden de llegada hasta que haya turno y holgura (PSI full < 5, freno termico `--gate-termico`, holgura de `app.slice`). Nunca congela un arbol cuyo ancestro sea `pre-commit` (sostiene `index.lock`) ni nada de `docker.slice`/`system.slice`.
4. **Reasignar a un slice libre**: un arbol que no cabe en `app.slice` se mueve a un hermano con holgura (`bb-jobs.slice`, tope = presupuesto total menos GPU y resto) si la suma de topes sigue cabiendo en el total.
5. **CLI explicita** `bb portero run --clase suite -- <cmd>` para quien quiera pedir turno (usa la misma cola), y `bb portero estado`.
6. Todo evento (admite, congela, descongela, mueve, no actua y por que) se registra en `$BLACKBOX_DATA` con el origen; fallo cerrado hacia el comportamiento actual si /proc o cgroup no se pueden leer.

## Riesgos declarados

- Latencia de deteccion de 1-2 s: un trabajo asigna memoria antes de ser movido (por eso el escalon de `bb-usable` sigue de respaldo).
- Congelar un `git push` hace correr su `timeout` mientras espera.
- Falsos positivos: congelar un arbol que el dueno necesitaba ya; por eso la lista de excepciones y el registro de cada decision.
