---
id: HARVEST-373655-ubuntu-26-04-drivers-610-cuda-toolkit-13-3-zf
kind: task
title: "Evaluar adopción: mecanismo cosechado por Atlas (373655-ubuntu-26-04-drivers-610-cuda-toolkit-13-3-zfs-on-gx10)"
status: open
severity: P3
origin: asserted
satd_family: HARVEST_SUGGESTION
close_check: {"cmd": "python -m tools.check_harvest_accepted tasks/backlog/HARVEST-373655-ubuntu-26-04-drivers-610-cuda-toolkit-13-3-zf.md", "expect": "exit_zero", "porque": "Sugerencia de adopcion, no un defecto -- verifica que accepted.by/date/trigger este lleno y no sea el placeholder, patron de own_chats/tools/check_harvest_accepted.py (DGX-505)."}
created: 2026-09-09
accepted: {"by": "the maintainer + Claude, revision de deuda 2026-09-09", "date": "2026-09-09", "trigger": "hardware/escenario distinto -- reabrir si ATOM cambia de configuracion (cluster, rack, otro chip)"}
reason: "La gestion de energia de NIC Mellanox es para clustering multi-nodo, fuera de alcance. No hay evidencia de que ATOM use ZFS. El pipeline de llama.cpp ya quedo correctamente asignado a Atlas en el propio dictamen de la ficha."
---

## Qué es esto

Sugerencia de cosecha, no un defecto. Atlas (la KB compartida de la flota) leyó una fuente
externa y encontró mecanismos que podrían servirle a **este proyecto** específicamente, por
dominio. Nadie de blackbox pidió esta evaluación -- es cosecha pasiva. **La decisión
de adoptar, adaptar o descartar es 100% de este proyecto.**

Cruzada antes de escribirse contra `.simplecode/fork_own.json` de este repo (si existe) para
evitar sugerir algo que ya está vendorizado -- ver DGX-505 en Atlas, donde `own_chats` cazó 3
falsos positivos de este tipo en el primer lote.

## Mecanismos encontrados, con su cita (tal como Atlas los verificó)

- PASO 1 (Mecanismo 1): Configuración de límites de Adaptive Replacement Cache (ARC) de ZFS mediante escrituras a modprobe (`options zfs zfs_arc_max=2147483648` y `options zfs zfs_arc_min=1073741824` en `/etc/modprobe.d/zfs.conf`), limitando la memoria de ARC entre 1GB y 2GB para controlar la memoria del sistema en entornos con ZFS — `knowledge/references/forum_nvidia_373655_ubuntu-26-04-drivers-610-cuda-toolkit-13-3-zfs-on-gx10.md:7`
- PASO 1 (Mecanismo 2): Instalación del paquete `.deb` `dgx-spark-mlnx-hotplug` e integración en la inicialización temprana vía `update-initramfs -u` para gestionar el hot-plug de dispositivos Mellanox en DGX Spark y mitigar el consumo de energía en reposo de los puertos ConnectX-7 — `knowledge/references/forum_nvidia_373655_ubuntu-26-04-drivers-610-cuda-toolkit-13-3-zfs-on-gx10.md:9`
- PASO 1 (Mecanismo 3): Pipeline de extracción y compilación de `llama.cpp` mediante `git clone`, `cmake`, `make`, vinculando `libnccl2`/`libnccl-dev` y usando `ccache` para acelerar compilaciones iterativas y validar rendimiento bruto de inferencia — `knowledge/references/forum_nvidia_373655_ubuntu-26-04-drivers-610-cuda-toolkit-13-3-zfs-on-gx10.md:11`
- PASO 1 (Mecanismo adicional documentado): Ciclo de descarga y recarga de módulos del driver NVIDIA en caliente (`for m in nvidia_uvm nvidia_drm nvidia_modeset nvidia; do modprobe -r "$m" 2>/dev/null || true; done; modprobe nvidia; modprobe nvidia_uvm`) para liberar buffers y memoria de caché retenidos por vLLM — `knowledge/references/forum_nvidia_373655_ubuntu-26-04-drivers-610-cuda-toolkit-13-3-zfs-on-gx10.md:181`
- PASO 2 (Mecanismo 1 - Configuración ZFS): Mapea al proyecto Liberation Watchdog atacando la categoría de falla conocida de agotamiento de memoria unificada y degradación de integridad de datos por competencia de caché; no se define en el texto si existe versión a escala o nombre previo en la flota — `knowledge/references/forum_nvidia_373655_ubuntu-26-04-drivers-610-cuda-toolkit-13-3-zfs-on-gx10.md:15`
- PASO 2 (Mecanismo 2 - `dgx-spark-mlnx-hotplug`): Mapea al proyecto DGX Spark atacando la categoría de falla conocida de falla de inicialización temprana de hardware / consumo excesivo de energía en reposo; no se define en el texto si existe versión a escala o nombre previo en la flota — `knowledge/references/forum_nvidia_373655_ubuntu-26-04-drivers-610-cuda-toolkit-13-3-zfs-on-gx10.md:16`
- PASO 2 (Mecanismo 3 - Pipeline `llama.cpp`): Mapea al proyecto Atlas atacando la categoría de falla conocida de incompatibilidad de toolchain / degradación de latencia en compilación de inferencia local; no se define en el texto si existe versión a escala o nombre previo en la flota — `knowledge/references/forum_nvidia_373655_ubuntu-26-04-drivers-610-cuda-toolkit-13-3-zfs-on-gx10.md:17`
- PASO 3 (Veredicto del producto y cosecha): Veredicto `COS` (cosechado), justificado porque presenta un setup exitoso y probado en hardware real GB10 con Ubuntu 26.04 y ZFS, detonando backlog para documentar, endurecer y fork-and-own del patrón de migración fuera de DGX OS — `knowledge/references/forum_nvidia_373655_ubuntu-26-04-drivers-610-cuda-toolkit-13-3-zfs-on-gx10.md:21-23`

## Por qué se sugiere para blackbox en concreto

El Mecanismo 2 ('dgx-spark-mlnx-hotplug', inicialización temprana de hardware Mellanox y consumo de energía en reposo de ConnectX-7) se mapeó a 'proyecto DGX Spark' (falso); ese mecanismo de inicialización/energía de hardware físico es dominio de blackbox, no considerado (el Mecanismo 3, llama.cpp, sí queda correctamente en Atlas).

## Procedencia

- Fuente original: https://forums.developer.nvidia.com/t/ubuntu-26-04-drivers-610-cuda-toolkit-13-3-zfs-on-gx10/373655
- Dictamen de cosecha, ruta absoluta: `~/projects/Atlas/docs/agent_findings/2026-09-05_cosecha_forum_nvidia_373655_ubuntu-26-04-drivers-610-cuda-toolkit-13-3-zfs-on-gx10.md`
- Corregido el 2026-09-09 (DGX-503): el dictamen original interrogó estos mecanismos sólo contra
  Atlas/aequitas_os porque la lista de flota de Atlas estaba rota (DGX-502) y no consideraba
  a blackbox en absoluto.

## Lo que esta ficha NO decide

No dice que blackbox deba adoptar nada. No mide si el código fuente es
production-ready, tiene licencia compatible, o pasa los propios gates de este repo -- eso lo
evalúa quien trabaje aquí, si decide que vale la pena mirarlo.
