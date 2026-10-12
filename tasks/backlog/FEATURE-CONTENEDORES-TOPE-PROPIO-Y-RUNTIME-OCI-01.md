---
id: FEATURE-CONTENEDORES-TOPE-PROPIO-Y-RUNTIME-OCI-01
kind: task
domain: MEMORY
title: "Todo contenedor con tope propio desde su creacion, incluido vLLM, via runtime OCI de bb"
status: open
severity: P1
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-10-12
close_check: {"cmd": "grep -q runtime_oci_probado tasks/evidence/FEATURE-CONTENEDORES-TOPE-PROPIO-Y-RUNTIME-OCI-01/medicion.txt", "expect": "exit_zero", "porque": "Decision de Luis 2026-10-12: todo contenedor debe tener tope propio, incluido vLLM, y eso se impone en el punto donde se crea el cgroup: el runtime OCI que invoca el daemon de Docker (daemon.json ya declara el runtime nvidia). Cierra cuando un envoltorio de runtime de bb, probado en un daemon de laboratorio separado (nunca en el de produccion), rechace o corrija la creacion de un contenedor sin tope de memoria, swap y procesos, exija el reclamo GPU declarado a los contenedores que piden GPU, y lo demuestre con su control negativo. Frase obligatoria en medicion.md: runtime_oci_probado."}
---

## Regla (voto de Luis, 2026-10-12)

Todo contenedor lleva tope propio de memoria, swap y procesos desde su creacion, incluido vLLM; ningun contenedor depende de que alguien recuerde ponerlo ni de un `docker update` posterior. La GPU no la contabiliza el cgroup (medido: vLLM 33.4 GiB de GPU, 12.2 GiB de cgroup; `dmem.capacity` vacio), asi que el tope GPU es el reclamo declarado y sumado, no un limite del kernel.

## Estado medido hoy (2026-10-12)

| Contenedor | memory.max | swap | pids | Nota |
|---|---|---|---|---|
| nemotron-server (vLLM) | 75 GiB | max | max | `gpu_memory_utilization=0.3` declarado en `/srv/ai/gateway/active_engine.json`; pico 12.7 GiB de cgroup |
| atlas-pgvector | 2 GiB | **max** | max | `docker update --memory-swap` bloqueado por el clasificador de permisos: decision pendiente de Luis |
| librechat | 3 GiB | 0 | 2048 | `docker update` en vivo 2026-10-12 (pico medido 753 MiB, 4x redondeado) |
| mongo-librechat | 2 GiB | 0 | 2048 | idem (pico 407 MiB) |
| aequitas-pg | 2 GiB | 0 | 2048 | idem (pico 418 MiB) |

Los tres `docker update` se pierden si el contenedor se recrea: ninguno lleva etiquetas de compose, se crean con `docker run`. Hallar quien los crea y persistir el tope ahi es parte de esta ficha; el runtime OCI lo resuelve de forma general.

## Antecedentes en esta maquina (no empezar de cero)

- `/srv/ai/gpu_governance/` (fuera de cualquier repo): `admission_check.sh` (comprobacion de arranque por memoria disponible menos 18 GB de reserva de escritorio; es una foto, no una reserva), `gpu_lock.sh` (flock), `monitor_memory.sh`. `ai-nemotron.service` la invoca por `ExecStartPre` via `/srv/ai/gateway/admission_check_wrapper.sh` con `admission_check_gb=68`.
- Su cabecera registra H6/H34: el tope de Docker no gobierna la memoria unificada y el controlador `dmem` existe pero el driver no lo llena. Verificado hoy: `dmem` esta en los controladores raiz y `dmem.capacity` esta vacio.
- Decision pendiente: absorber `gpu_governance` en bb (versionado, con tests) o dejarlo en `/srv/ai`. Por la regla de ubicacion (lo que actua sobre la maquina vive en bb) corresponde a bb.
- `FEATURE-1358-CGROUP-03-NATIVO` evalua la contabilidad nativa/dmem; no se duplica aqui.

## Diseno del runtime OCI (por validar)

`daemon.json` declara `"runtimes": {"nvidia": {"path": "nvidia-container-runtime"}}` y `"cgroup-parent": "docker.slice"`. Un envoltorio `bb-oci-runtime` en lugar del `path` vera cada `create` con su `config.json` OCI y podra: (1) inyectar `linux.resources.memory.limit/swap` y `pids.limit` por defecto de la clase si faltan; (2) rechazar (exit != 0 con motivo) un contenedor que pida GPU sin etiqueta `bb.gpu_budget_gib` o cuya suma de reclamos supere el suelo de GPU (50.1 GiB p95, `99-blackbox.conf`); (3) registrar cada decision en `$BLACKBOX_DATA`; (4) delegar en el runtime real sin cambiar nada mas. Falla cerrado hacia el comportamiento actual si no puede leer el spec.

### Implementado (etapa 1, 2026-10-12)

- `tools/bb_oci_runtime.py`: se invoca como runc. `create`: lee `<bundle>/config.json`, `decidir()` (pura, sin I/O) y, si corrige, reescribe el spec (tmp + rename) y hace `exec` del runtime real (`BB_OCI_REAL_RUNTIME`, por defecto `nvidia-container-runtime`). `delete`: registra la liberacion del reclamo y delega. El resto de subcomandos pasa tal cual y sin registro.
- Clases: `general` 3 GiB / pids 2048; `gpu` 14 GiB (= `docker.slice` memory.max) / pids 2048. Swap = limite (sin swap). Un campo cuenta como ausente si es nulo, 0 o -1; un valor positivo declarado no se toca nunca, sea mas estricto o mas laxo que la clase (vLLM con 75 GiB conserva sus 75 y solo recibe swap y pids).
- GPU = `NVIDIA_VISIBLE_DEVICES` distinto de vacio/void/none, o `/dev/nvidia*` en `linux.devices`, o un hook `nvidia-container`. El reclamo es la ANOTACION OCI `bb.gpu_budget_gib`, que en Docker se pone con `docker run --annotation` (las `--label` no llegan al spec OCI).
- Registro y suma: `$BLACKBOX_DATA/oci_runtime.jsonl`, con `flock` alrededor de leer-decidir-escribir. Los reclamos vigentes se repliegan del propio registro (creates admitidos menos deletes). Suelo con su origen en cada fila; `BB_OCI_GPU_FLOOR_GIB` lo cambia.
- `tools/portero_docker_lab.sh up|status|prueba|down` para el nivel 2; usa `bblab.slice` (no `docker-lab.slice`: el guion lo haria hijo de `docker.slice`) y un containerd propio (el dockerd de produccion usa el containerd del sistema).

### Probado de verdad

- Nivel 1 sin root: contenedores reales con runc 1.3.6 rootless a traves del envoltorio; sin tope -> `3221225472/0/2048`; control negativo sin envoltorio -> `max/max/152777`; tope estricto intacto; GPU sin anotacion y GPU con 60 GiB rechazadas (rc 3, sin cgroup); spec truncado pasa intacto y lo rechaza runc. `tasks/evidence/FEATURE-CONTENEDORES-TOPE-PROPIO-Y-RUNTIME-OCI-01/nivel1-salida.txt`.
- `tests/test_bb_oci_runtime.py` 38 casos sobre `runc spec`; 18 mutaciones, 0 vivas (`mutaciones-salida.txt`). La guarda del laboratorio se niega con el socket de produccion y con un enlace a el, y no se niega con el suyo.

### NO probado (y por que)

- Nada bajo Docker: el nivel 2 no se ha ejecutado (pide root). Tampoco con `nvidia-container-runtime` como runtime real ni con un contenedor que reciba GPU de verdad.
- No desplegado en produccion. Antes de hacerlo hay que decidir: (a) el creador de vLLM (`ai-nemotron.service`) tiene que pasar `--annotation bb.gpu_budget_gib=<N>`, o el siguiente arranque de vLLM sera RECHAZADO; (b) el registro arranca vacio, asi que los contenedores que ya corren no cuentan en la suma hasta que se recreen; (c) un contenedor que muera sin `delete` (caida del shim o del daemon) deja su reclamo en el registro y la suma rechaza de mas hasta que alguien lo limpie: falla hacia rechazar, y se ve en el jsonl.
- Si el mensaje de rechazo llega a la salida de `docker run` depende de como containerd recoge la stderr del runtime: se vera en el nivel 2.

## Entorno de prueba (lo mas importante, voto de Luis)

Nunca se prueba en el daemon de produccion (contiene nemotron-server, atlas-pgvector, librechat, mongo-librechat y aequitas-pg).
- Nivel 1, sin root: pruebas dorado sobre `config.json` (generado con `runc spec`) y, si `runc` rootless funciona aqui, un contenedor real con el envoltorio.
- Nivel 2, con root (lo ejecuta Luis una vez): `sudo bash tools/portero_docker_lab.sh up` levanta un SEGUNDO `dockerd` con otro socket, otro `data-root`, otro `exec-root`, otro puente (o ninguno) y su propio `daemon.json` que apunta al envoltorio; las imagenes se cargan con `docker save | docker -H unix:///run/bb-lab/docker.sock load`; `down` lo borra todo. Cada prueba lleva su control negativo (un contenedor con tope no se toca, uno sin tope se corrige o se rechaza).

## Que falta

1. Envoltorio `bb-oci-runtime`, script de laboratorio y sus pruebas: nivel 1 hecho (2026-10-12); falta el nivel 2, que ejecuta Luis con `sudo bash tools/portero_docker_lab.sh up && sudo bash tools/portero_docker_lab.sh prueba; sudo bash tools/portero_docker_lab.sh down` (detalle en `tasks/evidence/FEATURE-CONTENEDORES-TOPE-PROPIO-Y-RUNTIME-OCI-01/instrucciones-nivel2.txt`).
2. Persistir los topes de los contenedores existentes en sus creadores.
3. Decidir `atlas-pgvector` (swap) y la absorcion de `gpu_governance`.
