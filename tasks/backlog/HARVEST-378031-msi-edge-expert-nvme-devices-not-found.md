---
id: HARVEST-378031-msi-edge-expert-nvme-devices-not-found
kind: task
title: "Evaluar adopción: mecanismo cosechado por Atlas (378031-msi-edge-expert-nvme-devices-not-found)"
status: open
severity: P3
origin: asserted
satd_family: HARVEST_SUGGESTION
close_check: {"cmd": "python -m tools.check_harvest_accepted tasks/backlog/HARVEST-378031-msi-edge-expert-nvme-devices-not-found.md", "expect": "exit_zero", "porque": "Sugerencia de adopcion, no un defecto -- verifica que accepted.by/date/trigger este lleno y no sea el placeholder, patron de own_chats/tools/check_harvest_accepted.py (DGX-505)."}
created: 2026-09-09
accepted: {"by": "the maintainer + Claude, revision de deuda 2026-09-09", "date": "2026-09-09", "trigger": "hardware/escenario distinto -- reabrir si ATOM cambia de configuracion (cluster, rack, otro chip)"}
reason: "Hardware distinto (MSI Edge Expert, no GB10/DGX Spark). Los mecanismos (sonda NVMe en POST, fallback PXE) son ademas firmware pre-boot, no observables desde el SO ya arrancado."
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

- Enlazado NVMe UEFI/BIOS y detección de medio (NVMe Media Presence Check): el firmware realiza una sonda de presencia NVMe en POST y, si falla, pasa a fallback PXE IPv4. — `knowledge/references/forum_nvidia_378031_msi-edge-expert-nvme-devices-not-found.md:7`
- Ruta de diagnóstico NVMe CLI desde entorno Live USB: arranque desde Linux live USB e instalación de herramientas para ejecutar pruebas automáticas e inspección SMART. — `knowledge/references/forum_nvidia_378031_msi-edge-expert-nvme-devices-not-found.md:9`
- Ruteo PXE IPv4 como fallback de boot: cuando el firmware no detecta almacenamiento local arrancable, transfiere el control a la red por PXE IPv4. — `knowledge/references/forum_nvidia_378031_msi-edge-expert-nvme-devices-not-found.md:11`
- Mapeo a proyectos de la flota: el enlazado NVMe mitiga fallos de enumeración en DGX Spark / MSI Edge Expert; el diagnóstico CLI asiste en Liberation Watchdog; y el ruteo PXE actúa como componente de resiliencia en Atlas. — `knowledge/references/forum_nvidia_378031_msi-edge-expert-nvme-devices-not-found.md:15-19`
- Categoría de falla atacada: condición de fallo de enumeración de almacenamiento en firmware que induce desvío no deseado a arranque por red. — `knowledge/references/forum_nvidia_378031_msi-edge-expert-nvme-devices-not-found.md:17`
- Veredicto de producto COS: justificado por la validación de fallos a nivel de firmware/BIOS y con disparador de reevaluación consistente en bajar código de diagnóstico UEFI/NVMe y analizar la implementación en DGX Spark. — `knowledge/references/forum_nvidia_378031_msi-edge-expert-nvme-devices-not-found.md:23-25`

## Por qué se sugiere para blackbox en concreto

El mecanismo de diagnóstico CLI de NVMe (arranque Live USB, inspección SMART) se asigna a 'Liberation Watchdog', nombre falso; ese mecanismo de diagnóstico/telemetría de hardware es exactamente el dominio de blackbox ('monitoreo de hardware, logs, systemd units' de la AI TOP ATOM).

## Procedencia

- Fuente original: https://forums.developer.nvidia.com/t/msi-edge-expert-nvme-devices-not-found/378031
- Dictamen de cosecha, ruta absoluta: `~/projects/Atlas/docs/agent_findings/2026-09-05_cosecha_forum_nvidia_378031_msi-edge-expert-nvme-devices-not-found.md`
- Corregido el 2026-09-09 (DGX-503): el dictamen original interrogó estos mecanismos sólo contra
  Atlas/aequitas_os porque la lista de flota de Atlas estaba rota (DGX-502) y no consideraba
  a blackbox en absoluto.

## Lo que esta ficha NO decide

No dice que blackbox deba adoptar nada. No mide si el código fuente es
production-ready, tiene licencia compatible, o pasa los propios gates de este repo -- eso lo
evalúa quien trabaje aquí, si decide que vale la pena mirarlo.
