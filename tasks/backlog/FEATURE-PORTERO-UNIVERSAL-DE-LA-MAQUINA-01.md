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
close_check: {"cmd": "grep -q portero_universal_probado tasks/evidence/FEATURE-PORTERO-UNIVERSAL-DE-LA-MAQUINA-01/medicion.txt", "expect": "exit_zero", "porque": "Los dos colapsos del 11-oct fueron una estampida de git push con pre-push (suite completa) lanzados a la vez por seis sesiones; cada uno corria sin tope propio dentro de un app.slice de 42 GiB compartido, y cerca del techo el kernel se estanca en vez de matar. Cierra cuando haya una medicion con el portero activo: tres suites lanzadas a la vez entran de una en una, cada una bajo su tope, sin que ningun llamador cambie, y el estancamiento no se reproduce. Frase obligatoria en medicion.md: portero_universal_probado."}
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

## Implementado en la etapa 1 (2026-10-12), sin desplegar

- `tools/portero.py`: `decide()` PURA (sin I/O) y una parte con efecto separada (`observar`, `aplica`). Clase unica `suite` (pytest, hooks pre-push/pre-commit, por forma del comando): MemoryMax 20G, MemoryHigh 18G, swap 0, TasksMax 1230 (`pids.peak` de app.slice), 1 turno. Pesado = RSS del arbol >= 4 873 628 kB (p95 del RSS de un python en scope Claude, 6 895 muestras). Puerta para dar turno: PSI full avg10 < 5, estado termico `normal` sin freno vivo, holgura de app.slice >= 4 GiB (codo medido en 38 GiB: PSI >= 5 en 0.22 % por debajo, 1.26 % entre 38 y 40) y presupuesto (consumo de scopes con tope propio + turnos admitidos x MemoryMax <= tope del slice). Sin turno o con la puerta cerrada: `congelar` (adopcion en `bb-portero-suite-<pid>.scope` + `cgroup.freeze`); con turno: `admitir` o `descongelar` al mas antiguo; con slice alterno con holgura: `mover`.
- Nunca: congelar un arbol que sostiene `index.lock` (git commit/merge/rebase/cherry-pick/revert/am o su hook pre-commit: se le pone tope sin congelar), actuar fuera de app.slice, tocar un arbol cuyo cgroup tiene memory.max finito <= el de su clase, ni `liberation_job*.scope`, `bb-cap-*.scope`, docker, o descendientes de `liberation_watchdog` (regla del coordinador por el choque con los jobs de Atlas). Un arbol ya admitido no se re-congela. Sin /proc, PSI, cgroup de app.slice, consumo con tope propio o estado termico fresco: no actua y escribe NOT_COLLECTED.
- Efecto solo con lo delegado: `StartTransientUnit` del gestor de usuario con `PIDs` (adopta procesos vivos con sus topes, job asincrono: se espera la adopcion hasta 2 s), `cgroup.procs` para hijos nacidos entretanto, `cgroup.freeze`. Eventos en `$BLACKBOX_DATA/portero.jsonl` con `medicion` y `origen` (costura `Efectos.origen`; hoy `NOT_COLLECTED` hasta integrar `bb origen`).
- `bb portero estado` (solo lectura), `bb portero run --clase suite -- <cmd>` (peticion en `$BLACKBOX_DATA/portero_cola/<pid>.json`, la misma cola FIFO que ve el demonio; con turno lanza `systemd-run --user --scope -p MemoryMax=.. -p MemoryHigh=.. -p MemorySwapMax=0 -p TasksMax=..`), `bb portero demonio` (unidad `systemd/bb-portero.service`, en `background.slice` con MemoryMax=256M; un ciclo mide 28 MB de RSS y 80 ms de CPU con arranque de python).
- Contenedores: `bb portero contenedores [--aplicar]` decide `docker update --memory X --memory-swap X` para contenedores sin tope; X = tope de docker.slice - topes propios mas estrictos - picos medidos de los demas. Medido hoy: el pico de nemotron-server (12.5 GB, tope 75 GiB > slice) ya llena el slice de 14 GiB, asi que el reparto sale negativo y no acota ninguno (acotarlo lo mataria). El demonio solo lo corre con `--contenedores`.
- Drop-in de creacion `systemd/app-com.anthropic.Claude-.scope.d/50-bb-portero.conf`: MemoryMax=35G (calibracion de DEBT-COLAPSOS-11-OCT: 0/439 muestras con PSI >= 10 por debajo de 35 GB, 2/2 entre 35 y 40), TasksMax=1230. Probado con un scope desechable `app-bbprobe<tag>-1` y su control negativo.
- GPU: el cgroup no ve la memoria GPU (validaciones.txt §4). Propuesta NO VALIDADA: admitir contenedores por su reclamo GPU declarado al crearlos (`--gpu-memory-utilization`) contra el suelo de GPU de 50.1 GiB; no implementada.
- Falta: integrar `bb origen` en la costura; la medicion con tres suites reales tras el despliegue (Luis); que el demonio cubra java/dotnet (sin medicion, no hay clase).

## Avance 2026-10-14: desplegado en observar y medido con 3 suites
Voto de Luis (observar, medir, luego actuar). `bb-portero.service` corre como servicio de usuario con el interruptor en `observar`. Medicion en `tasks/evidence/FEATURE-PORTERO-UNIVERSAL-DE-LA-MAQUINA-01/medicion.txt`: tres suites con `bb portero run` entraron de una en una, cada una bajo su scope (20G, sin swap). Falta para la frase de cierre: la prueba por el camino transparente (hooks sin cambiar el llamador, demonio en `actuar`) y el estancamiento bajo carga alta real.
