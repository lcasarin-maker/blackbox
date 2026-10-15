#!/usr/bin/env bash
# Ventana del motor 2026-10-15 -- pasos de ROOT (el motor ya esta parado cuando esto corre; lo para y lo arranca la sesion, sin sudo).
# Lo que hace, en orden, y nada mas:
#   1. prueba de recarga: contenedor desechable con GPU, `nvidia-smi -L` y /dev/nvidia* ANTES, a los 60 s SIN recarga (control),
#      `systemctl daemon-reload`, y DESPUES. Escribe prueba.txt de DEBT-DOCKER-CGROUP-SYSTEMD-RECARGA-QUITA-GPU-01.
#   2. docker.slice 14 -> 16 GiB: copia el drop-in vigente a /var/lib/blackbox/, instala el votado, daemon-reload, restart docker.
#   3. unidad bb-gpu-accounting.service: instala, daemon-reload, enable --now.
# Escribe: /etc/systemd/system/docker.slice.d/99-blackbox.conf, /etc/systemd/system/bb-gpu-accounting.service, /var/lib/blackbox/ (copia),
#   y los .txt de evidencia bajo tasks/evidence/ (devueltos a tu usuario). No toca nada mas.
# Revertir 2: sudo install -m 0644 /var/lib/blackbox/99-blackbox.conf.14G /etc/systemd/system/docker.slice.d/99-blackbox.conf && sudo systemctl daemon-reload && sudo systemctl restart docker
# Revertir 3: sudo systemctl disable --now bb-gpu-accounting.service && sudo rm /etc/systemd/system/bb-gpu-accounting.service && sudo systemctl daemon-reload
set -u
[ "$(id -u)" = 0 ] || { echo "corre con sudo" >&2; exit 2; }
R=/home/lcasarin/projects/blackbox
U=${SUDO_USER:-lcasarin}
V=$R/tasks/evidence/VENTANA-VLLM-20261015
EV=$R/tasks/evidence/DEBT-DOCKER-CGROUP-SYSTEMD-RECARGA-QUITA-GPU-01
IMG=vllm/vllm-openai:v0.27.1
LOG=$V/ventana-$(date +%Y%m%dT%H%M%S).txt
exec > >(tee "$LOG") 2>&1
echo "== inicio $(date -Is); motor: $(docker ps --filter name=nemotron-server -q | wc -l) contenedor(es) nemotron-server corriendo (debe ser 0)"
[ -z "$(docker ps --filter name=nemotron-server -q)" ] || { echo "el motor sigue corriendo; no se hace nada"; exit 3; }

echo; echo "== 1. prueba de recarga"
snap() { docker exec bb-recarga-prueba sh -c 'nvidia-smi -L; ls /dev/nvidia-caps /dev/nvidia-modeset /dev/nvidia0 /dev/nvidiactl /dev/nvidia-uvm 2>&1'; }
docker rm -f bb-recarga-prueba > /dev/null 2>&1
docker run -d --rm --name bb-recarga-prueba --runtime nvidia --gpus all --entrypoint sleep "$IMG" 900 > /dev/null || echo "docker run fallo"
sleep 3
antes="$(snap)"; echo "--- ANTES:"; echo "$antes"
sleep 60
control="$(snap)"; echo "--- CONTROL (60 s despues, SIN recarga):"; echo "$control"
systemctl daemon-reload; echo "daemon-reload rc=$?"
sleep 3
despues="$(snap)"; echo "--- DESPUES de daemon-reload:"; echo "$despues"
docker rm -f bb-recarga-prueba > /dev/null 2>&1
if [ -n "$antes" ] && [ "$antes" = "$control" ] && [ "$antes" = "$despues" ] && echo "$antes" | grep -q "GPU 0"; then
  veredicto=recarga_probada
else
  veredicto=recarga_NO_PROBADA
fi
# control negativo del instrumento: quitar una linea de /dev/nvidia* debe hacer distinto el texto
if [ "$antes" != "$(echo "$antes" | grep -v nvidia-caps)" ]; then neg="control negativo: quitar nvidia-caps SI cambia la comparacion"; else neg="control negativo FALLO: la comparacion no distingue"; fi
{ echo "$veredicto"; echo "$neg"; echo "contenedor $IMG, Docker $(docker --version), driver $(nvidia-smi --query-gpu=driver_version --format=csv,noheader), $(date -Is)"; echo "--- ANTES"; echo "$antes"; echo "--- CONTROL"; echo "$control"; echo "--- DESPUES"; echo "$despues"; } > "$EV/prueba.txt"
echo "veredicto: $veredicto ($neg)"

echo; echo "== 2. docker.slice 14 -> 16 GiB"
cp -p /etc/systemd/system/docker.slice.d/99-blackbox.conf /var/lib/blackbox/99-blackbox.conf.14G && sha256sum /var/lib/blackbox/99-blackbox.conf.14G
echo "antes: $(systemctl show docker.slice -p MemoryMax)"
install -D -m 0644 -o root -g root "$R/adopted/pendiente-de-despliegue/etc_systemd_system_docker.slice.d_99-blackbox.conf" /etc/systemd/system/docker.slice.d/99-blackbox.conf
systemctl daemon-reload && systemctl restart docker; echo "restart docker rc=$?"
sleep 8
echo "despues: $(systemctl show docker.slice -p MemoryMax) (esperado MemoryMax=17179869184)"
docker ps --format '{{.Names}} {{.Status}}'

echo; echo "== 3. bb-gpu-accounting.service"
install -m 0644 -o root -g root "$R/adopted/pendiente-de-despliegue/etc_systemd_system_bb-gpu-accounting.service" /etc/systemd/system/bb-gpu-accounting.service
systemctl daemon-reload && systemctl enable --now bb-gpu-accounting.service; echo "enable rc=$?"
echo "is-enabled: $(systemctl is-enabled bb-gpu-accounting.service) is-active: $(systemctl is-active bb-gpu-accounting.service) accounting.mode: $(nvidia-smi --query-gpu=accounting.mode --format=csv,noheader)"

chown -R "$U": "$V" "$EV" 2>/dev/null
echo; echo "== fin $(date -Is). Dile a Claude que termino."
