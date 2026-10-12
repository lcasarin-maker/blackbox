# Nivel 2: instrucciones para Luis (una sola vez, con sudo)

Desde la raiz del repo bb, con el envoltorio ya en la rama que se va a probar:

```
sudo bash tools/portero_docker_lab.sh up && sudo bash tools/portero_docker_lab.sh prueba; sudo bash tools/portero_docker_lab.sh down
```

`down` va despues de `;` a proposito: se ejecuta aunque `up` o `prueba` fallen.

## Que hace cada paso

- `up`: crea `bblab.slice` con `MemoryMax=1G MemorySwapMax=0 TasksMax=512` (propiedad
  `--runtime`, vive en `/run`); arranca un containerd propio (`/run/bb-lab/containerd.sock`,
  root `/var/lib/bb-docker-lab/containerd`, CRI y NRI desactivados) y un dockerd propio
  (`--host unix:///run/bb-lab/docker.sock --data-root /var/lib/bb-docker-lab
  --exec-root /run/bb-docker-lab --pidfile /run/bb-lab/dockerd.pid --bridge=none
  --iptables=false --ip6tables=false --ip-forward=false`, namespace de containerd `bblab`)
  con `daemon.json` propio: runtime por defecto `bb` -> `tools/bb_oci_runtime.py`
  (runtime real `nvidia-container-runtime`), `cgroup-parent: bblab.slice`. Carga
  `postgres:16-alpine` con `docker save` del daemon de produccion (lectura) y
  `docker load` en el de laboratorio.
- `prueba`: cinco contenedores `sleep 300`, con su resultado literal en
  `prueba-nivel2-<fecha>.txt` de este directorio:
  1. control negativo: `--runtime runc` (sin envoltorio) -> debe quedar `memory.max=max`;
  2. sin tope -> corregido a `3221225472 / swap 0 / pids 2048`;
  3. `--memory 64m --memory-swap 64m --pids-limit 16` -> intacto (`67108864 / 0 / 16`);
  4. `-e NVIDIA_VISIBLE_DEVICES=all` sin anotacion -> rechazado, con `RECHAZAR` en el registro;
  5. lo mismo con `--annotation bb.gpu_budget_gib=60` -> rechazado por la suma.
  Solo si los cinco pasan y no hay `COULD_NOT_RUN`, anota la frase del close_check en
  `medicion.md`. Si algo falla, `medicion.md` no se toca.
- `down`: borra los contenedores del laboratorio, para dockerd y containerd (solo si su
  cmdline nombra los ficheros de configuracion del laboratorio), desmonta lo que quede
  bajo las rutas del laboratorio, `systemctl stop` + `revert` de `bblab.slice`, y borra
  `/var/lib/bb-docker-lab`, `/run/bb-docker-lab` y `/run/bb-lab`. Termina con `restos=0`
  o lista lo que quedo.

## Lo que no toca

`/etc/docker/daemon.json`, `/etc/systemd`, el dockerd de produccion, su containerd
(`/run/containerd/containerd.sock`) y sus contenedores. Cada subcomando comprueba antes
de actuar que el socket del laboratorio no resuelve a `/var/run/docker.sock` (enlaces
incluidos) y, antes de crear o borrar contenedores, que el daemon al otro lado tiene
`DockerRootDir=/var/lib/bb-docker-lab`.

## Riesgos que quedan, dichos antes

- Primera ejecucion: `up` no se ha corrido nunca. Los puntos que pueden fallar y que el
  nivel 1 no cubre: que containerd 2.2.5 acepte la config `version = 3` con esos
  `disabled_plugins`; que dockerd 29.6.2 acepte el runtime `bb` como `default-runtime`;
  que `nvidia-container-runtime` delegue en runc dentro de un shim del containerd de
  laboratorio; que el mensaje de rechazo del envoltorio llegue a la salida de `docker run`.
  Si `up` falla, `down` limpia y el resultado es un dato, no una averia de produccion.
- Memoria: cinco `sleep` dentro de un slice de 1 GiB, mas containerd y dockerd de
  laboratorio (decenas de MiB) y un `docker save | load` de 288 MB por tuberia.
- El shim del containerd de laboratorio crea su socket en `/run/containerd/s/` (ruta fija
  de containerd, nombre derivado del hash de la direccion del containerd de laboratorio):
  no colisiona con los de produccion y desaparece al terminar el shim.
