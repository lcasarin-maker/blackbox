---
id: DEBT-DOCKER-CGROUP-SYSTEMD-RECARGA-QUITA-GPU-01
kind: debt
domain: GPU
title: "Docker en cgroup systemd: un daemon-reload puede quitarle la GPU al contenedor de vLLM"
status: done
closed_at: 2026-10-15
closure_type: relocated_prior_verification
reason: "La prueba se midio en la ventana del motor del 2026-10-15 (ventana.sh con sudo de Luis) y su evidencia se commiteo en cc9a234e; este commit solo mueve la ficha. Control negativo: sin prueba.txt en HEAD el close_check sale 1 (fail.txt), con ella sale 0 (pass.txt)."
evidence: {"pass": "tasks/evidence/DEBT-DOCKER-CGROUP-SYSTEMD-RECARGA-QUITA-GPU-01/pass.txt", "fail": "tasks/evidence/DEBT-DOCKER-CGROUP-SYSTEMD-RECARGA-QUITA-GPU-01/fail.txt", "e2e": "tasks/evidence/DEBT-DOCKER-CGROUP-SYSTEMD-RECARGA-QUITA-GPU-01/e2e.txt"}
severity: P1
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-10-12
close_check: {"cmd": "grep -q recarga_probada tasks/evidence/DEBT-DOCKER-CGROUP-SYSTEMD-RECARGA-QUITA-GPU-01/prueba.txt", "porque": "Hasta medir con un contenedor desechable y un daemon-reload en una ventana sin vLLM, el riesgo es una afirmacion de un hilo ajeno; hoy no existe prueba.txt.", "expect": "exit_zero"}
---

## Riesgo
Hilo 352743 del foro: en GB10 con Docker en cgroup `systemd`, `systemctl daemon-reload` en el host hace que el contenedor pierda `/dev/nvidia-caps` y `/dev/nvidia-modeset` y `nvidia-smi` falle dentro con "Failed to initialize NVML: Unknown Error" hasta reiniciarlo. Este host: `docker info` = `cgroup_driver=systemd`, runtime `nvidia`, y vLLM de produccion corre asi. Cada `apt`, `systemctl enable` o `daemon-reload` es un disparador posible.
## Lo ya corregido (2026-10-12)
`tools/dmem_modulo.sh` ejecutaba `systemctl daemon-reload` en `instala` y `systemctl disable` en `retrocede`: ahora usan `--no-reload`, con prueba en `tests/test_dmem_modulo_llave.py`.
## Falta
1. Prueba con contenedor desechable (no el de produccion) y un `daemon-reload` en una ventana sin vLLM: ¿pierde `/dev/nvidia-caps`? Con control: el mismo contenedor sin recarga.
2. Decision de Luis (toca el demonio de Docker, regla del repo: no se toca produccion): `"exec-opts": ["native.cgroupdriver=cgroupfs"]` (remedio que reporta el autor del hilo) o CDI (`--device nvidia.com/gpu=all`, recomendado por NVIDIA; existe `/var/run/cdi/nvidia.yaml`). Cada una exige reiniciar el contenedor de vLLM.
3. Registrar cada `daemon-reload` del host junto a un `nvidia-smi -L` dentro del contenedor, para saber si ya paso.
## Decision de Luis (2026-10-12)
Probar primero con un contenedor desechable (paso 1 de "Falta"), con `daemon-reload` en una ventana sin vLLM y con control sin recarga. Descartado por ahora: pasar Docker a cgroupfs o a CDI sin ese dato (ambas tocan el demonio y reinician vLLM). La decision entre cgroupfs y CDI se vota con la medicion delante.

## Avance 2026-10-13 18:18: observacion en produccion, no cierra la ficha
Luis corrio `sudo ./enable-privileged.sh` con vLLM sirviendo. El instalador ejecuto `systemctl daemon-reload` tres veces, `daemon-reexec` y reinicio `earlyoom`. Medido despues, sobre el contenedor `nemotron-server` (Docker 28 con driver de cgroup `systemd`, driver NVIDIA 580.178.04): `docker exec nemotron-server nvidia-smi -L` lista la GPU; en el contenedor existen `/dev/nvidia-caps`, `/dev/nvidia-modeset`, `/dev/nvidia-uvm`, `/dev/nvidia0` y `/dev/nvidiactl` (los dos primeros son los que desaparecian en el hilo 352743); `nvidia-smi --query-gpu` responde; `/health` da 200 y `/v1/models` sirve `nemotron-local`. Es una observacion de UNA recarga sobre el contenedor de produccion; el criterio de esta ficha exige un contenedor desechable en una ventana sin vLLM, asi que sigue abierta. Evidencia a favor de que el riesgo no se materializa en esta configuracion, no prueba de que no exista.

## Avance 2026-10-14 (lote 'cierra las pendientes conforme a la opcion recomendada'): espera un disparador, no una decision
Disparador: la ventana del motor de 60 min que anuncia Luis, con sudo de Luis (`daemon-reload` es una escritura de root sobre systemd; no cabe en un script sellado de solo lectura). Pasos exactos: `docker run -d --rm --name bb-recarga-prueba --runtime nvidia --gpus all --entrypoint sleep vllm/vllm-openai:v0.27.1 900`; `docker exec bb-recarga-prueba nvidia-smi -L` y `docker exec bb-recarga-prueba ls /dev/nvidia-caps /dev/nvidia-modeset` (antes); control sin recarga: repetir a los 60 s; `sudo systemctl daemon-reload`; repetir las dos ordenes; `docker stop bb-recarga-prueba`. Guardar las salidas con `recarga_probada` en `tasks/evidence/DEBT-DOCKER-CGROUP-SYSTEMD-RECARGA-QUITA-GPU-01/prueba.txt`.

## Root Cause
Un hilo ajeno afirmaba que `systemctl daemon-reload` hace que systemd reaplique las reglas de cgroup de los contenedores y les quita `/dev/nvidia-caps` y `/dev/nvidia-modeset` (driver de cgroup `systemd`). Aqui no existia medicion propia y cualquier reload (instaladores, despliegues) se trataba como riesgo P1 sin prueba.

## Regression Test
`close_check`: `grep -q recarga_probada tasks/evidence/DEBT-DOCKER-CGROUP-SYSTEMD-RECARGA-QUITA-GPU-01/prueba.txt`. El veredicto lo escribe `tasks/evidence/VENTANA-VLLM-20261015/ventana.sh` solo si la instantanea ANTES, la de CONTROL (60 s despues, sin recarga) y la de DESPUES son identicas y listan la GPU; su control negativo comprueba que quitar `nvidia-caps` del texto SI cambia la comparacion.

## Verification Evidence
Medido el 2026-10-15 con el motor parado, contenedor desechable `vllm/vllm-openai:v0.27.1`, Docker 29.6.2, driver 580.178.04: antes, control y despues listan `GPU 0: NVIDIA GB10` y `/dev/nvidia-caps` (cap1, cap2), `nvidia-modeset`, `nvidia-uvm`, `nvidia0`, `nvidiactl`; `daemon-reload rc=0`. Veredicto `recarga_probada`. Log literal: `tasks/evidence/VENTANA-VLLM-20261015/ventana-20261015T063058.txt`. Limite declarado: un solo `daemon-reload` sobre un contenedor desechable; no cubre `daemon-reexec` ni un reload con el motor sirviendo (el 2026-10-13 un instalador hizo ambos con vLLM sirviendo y la GPU siguio visible, ver el Avance de esa fecha).
