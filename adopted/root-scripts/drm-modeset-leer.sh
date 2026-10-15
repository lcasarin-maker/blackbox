#!/usr/bin/env bash
# bb-root-run drm-modeset-leer -- SOLO LECTURA.
# Lee: el valor EFECTIVO de nvidia_drm.modeset y nvidia_drm.fbdev en
#      /sys/module/nvidia_drm/parameters/ (modo 0400 root: el usuario recibe permiso
#      denegado) y el boot_id con el que se leyo.
# Por que: este equipo tiene a la vez un modprobe.d con modeset=0 (paquete
#      nvidia-drm-options-modeset0) y otro con modeset=1; sin el valor efectivo el
#      preflight de OTA queda en unknown.
# Desbloquea: FORUM-00-DGX-OTA-DRM-COMPAT-PREFLIGHT.
# Escribe: nada fuera de stdout. Sin red, sin argumentos.
set -euo pipefail

params=/sys/module/nvidia_drm/parameters

echo "== boot_id"
cat /proc/sys/kernel/random/boot_id
echo "== $params"
for p in modeset fbdev; do
  if [[ -r "$params/$p" ]]; then
    printf 'nvidia_drm.%s=%s\n' "$p" "$(cat -- "$params/$p")"
  else
    echo "nvidia_drm.$p: ilegible o ausente (modulo nvidia_drm sin cargar?)"
  fi
done
