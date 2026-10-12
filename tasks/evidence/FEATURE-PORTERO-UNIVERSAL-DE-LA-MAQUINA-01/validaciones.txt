# Validaciones medidas en esta maquina (2026-10-12), no tomadas de hilos

Cada una con su control negativo. Los hilos del foro son indicios; esto es el sujeto.

## 1. Docker ya esta contenido y se puede acotar EN VIVO
- `/etc/docker/daemon.json` tiene `"cgroup-parent": "docker.slice"`: todo contenedor nace bajo `docker.slice`
  (MemoryMax 15032385536 = 14 GiB, MemorySwapMax 4 GiB). Medido con `docker inspect` + `/sys/fs/cgroup/docker.slice/docker-<id>.scope`.
- Topes por contenedor hoy: nemotron-server 75 GiB, atlas-pgvector 2 GiB; librechat, mongo-librechat y aequitas-pg SIN tope (`memory.max=max`).
- `docker update --memory 256m --memory-swap 256m --pids-limit 40` sobre un contenedor de prueba en marcha (imagen pgvector, `sleep 120`):
  ANTES `memory.max=max swap.max=max pids.max=152777`; DESPUES `memory.max=268435456 swap.max=0 pids.max=40`. Contenedor borrado, 0 restos.
- Correccion: la afirmacion "el portero no puede cercar los contenedores Docker" era una suposicion tomada de un hilo (353752, n=1). Falsa en esta maquina.
- Una primera prueba con `hello-world` no valia (la imagen no trae `sleep`, el contenedor no arranco): se descarto y se repitio.

## 2. Un drop-in por PREFIJO fija el tope de un scope transitorio en el momento de crearse
- `~/.config/systemd/user/app-bbprobe-.scope.d/50-prueba.conf` con `MemoryMax=300M MemorySwapMax=0 TasksMax=50`.
- POSITIVO `systemd-run --user --scope --unit=app-bbprobe-1 sleep 60`: `memory.max=314572800 swap.max=0 pids.max=50`; `DropInPaths` lo lista.
- NEGATIVO `--unit=app-otro-1`: `memory.max=max pids.max=152777`.
- Limpieza hecha (drop-in borrado, `daemon-reload`).
- Correccion: el comentario de `app.slice.d/99-blackbox.conf` ("el scope es transitorio y lleva el pid en el nombre, asi que no admite un drop-in estable")
  era una suposicion refutada. `app-com.anthropic.Claude-.scope.d/` fijaria el tope de CADA scope de la app al crearse.

## 3. Tope en caliente, mover pids entre scopes y congelar (scopes desechables)
- `systemctl --user set-property --runtime <scope> MemoryMax=300M MemorySwapMax=0` -> `memory.max=314572800 swap.max=0`.
- Escribir un pid en `cgroup.procs` de otro scope delegado lo mueve; fuera de lo delegado (`system.slice`, `user-1000.slice`) da `Permiso denegado` (control negativo).
- `systemctl --user freeze/thaw`: `cgroup.freeze` 1 y 0.

## 4. La memoria GPU NO la contabiliza el cgroup (medido, no del hilo)
- vLLM: `nvidia-smi --query-compute-apps` 33393 MiB (pid 655929) frente a `memory.current` del cgroup del contenedor 12198 MiB (anon 9359 + file 2656).
- Limite real en esta maquina: un tope de cgroup NO acota la memoria GPU/UMA. Lo que si se puede decidir en la CREACION del contenedor es su reclamo GPU declarado
  (p.ej. vLLM `--gpu-memory-utilization`) y sumarlo contra el suelo de GPU (50.1 GiB p95 segun `99-blackbox.conf`). No validado.

## 5. systemd-oomd: sin probar todavia
- Disponible `255.4-1ubuntu8.17`, NO instalado; `sudo` pide contrasena: lo instala Luis (`sudo apt install systemd-oomd`).
- Hipotesis a probar tras instalar (no afirmada): oomd mata el CGROUP entero, asi que aplicado al scope de la app mataria todas las sesiones;
  aplicado a los cgroups hijos por trabajo del portero mataria solo ese trabajo.
