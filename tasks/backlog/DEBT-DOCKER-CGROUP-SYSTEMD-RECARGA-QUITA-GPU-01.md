---
id: DEBT-DOCKER-CGROUP-SYSTEMD-RECARGA-QUITA-GPU-01
kind: debt
domain: GPU
title: "Docker en cgroup systemd: un daemon-reload puede quitarle la GPU al contenedor de vLLM"
status: open
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
