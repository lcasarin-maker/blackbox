---
id: FORUM-00-DGX-OTA-DRM-COMPAT-PREFLIGHT
kind: task
domain: DISPLAY
title: "Detect unsupported nvidia-drm modeset override before DGX OS OTA"
status: open
severity: P2
origin: asserted
satd_family: PREVENTION
created: 2026-10-02
close_check: {"cmd": "python3 -m tools.verify_forum_finding --id FORUM-00-DGX-OTA-DRM-COMPAT-PREFLIGHT --evidence tasks/evidence/FORUM-00-DGX-OTA-DRM-COMPAT-PREFLIGHT", "expect": "exit_zero", "porque": "Show that OTA compatibility checks detect a conflicting DRM modeset override before update, with safe recovery and a clean-system negative control."}
---

## Fallo y receta reportados

En [NVIDIA forum 382452, post 1](https://forums.developer.nvidia.com/t/dgx-spark-ota-update-to-dgx-os-7-5-0-kills-all-display-output-when-nvidias-own-nvidia-drm-options-modeset0-package-is-installed/382452/1), un DGX Spark GB10 con BIOS 5.36_0ACUM018, DGX OS 7.2.3 pasando a OTA 7.5.0 / meta 26.03.1, kernel 6.17.0-1032, driver 580.173.02 y el paquete NVIDIA `nvidia-drm-options-modeset0` perdió HDMI y USB-C/DP después del OTA. El archivo `/etc/modprobe.d/zz-nvidia-drm-override.conf` fijaba `nvidia-drm modeset=0`; el autor reporta que no quedaban conectores DRM registrados y GNOME no obtenía modos. El SSH seguía disponible.

El autor verificó recuperación tras quitar el override/paquete, reiniciar y cortar AC durante aproximadamente un minuto para reinitializar el display engine; su Thunderbolt hub también necesitó ciclo de alimentación. En su caso OTA meta 26.04.1 resolvió la interacción después de retirar el override. Propone que la OTA advierta/pare si hay incompatibilidad con KMS. Este es un caso reproducido por un propietario y no demuestra que toda instalación de ese paquete falle, ni que el paquete resulte incompatible en cada OEM.

## Exposición local y cobertura

El host inspeccionado por el coordinador usa kernel `6.17.0-1032-nvidia`, paquete `nvidia-drm-options-modeset0 25.07-1` instalado, y dos archivos de modprobe con ajustes `modeset=0` y `modeset=1`. Leer el parámetro efectivo de `/sys/module/nvidia_drm/parameters/modeset` falló por permisos; por tanto el valor activo no está verificado y no se afirma que el host tenga el fallo. El repo mantiene telemetría en modo headless, pero no valida compatibilidad entre una OTA/driver y un override DRM antes de reiniciar.

## Prevención, riesgo y cierre

Preferir un control de compatibilidad declarado por NVIDIA/paquetes de OTA, no reglas específicas inferidas únicamente del post. Antes de instalar una OTA o reiniciar, registrar versiones DGX OS, kernel, driver y paquete de override, inspeccionar opciones modprobe efectivas y comprobar si la versión objetivo requiere KMS para USB-C DP/Wayland. Si la combinación está declarada incompatible, preservar acceso SSH y recomendar actualización/retirada soportada del override con recuperación documentada; no eliminar la configuración automáticamente sin fuente oficial y plan de rollback.

Probar en un equipo de laboratorio con la misma OEM/BIOS/OTA: KMS habilitado, override modeset=0, combinación afectada, paquete ausente, HDMI, USB-C/DP directo y hub. Capturar conectores DRM, `nvidia-smi`, journal y acceso SSH antes/después, y confirmar rollback. Ciclar AC solo si la guía del fabricante lo permite. Una prueba local de valor sysfs requiere privilegios de solo lectura autorizados; sin esa evidencia mantenerlo como `could_not_run`. Cerrar con matriz oficial de compatibilidad o confirmación del vendor y un gate OTA que rechace/avise solo combinaciones incompatibles, incluyendo control negativo para un sistema sano.


## Estado de publicación de esta investigación

Propuesta abierta. Los comandos de cierre describen el verificador y evidencia requeridos; esta rama publica investigación y fichas, sin implementación ni resultados de ejecución de los mecanismos propuestos.
