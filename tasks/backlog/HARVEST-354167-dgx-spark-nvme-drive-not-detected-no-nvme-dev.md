---
id: HARVEST-354167-dgx-spark-nvme-drive-not-detected-no-nvme-dev
kind: task
title: "Evaluar adopción: mecanismo cosechado por Atlas (354167-dgx-spark-nvme-drive-not-detected-no-nvme-device-found)"
status: open
severity: P3
origin: asserted
satd_family: HARVEST_SUGGESTION
close_check: {"cmd": "python -m tools.check_harvest_accepted tasks/backlog/HARVEST-354167-dgx-spark-nvme-drive-not-detected-no-nvme-dev.md", "expect": "exit_zero", "porque": "Sugerencia de adopcion, no un defecto -- verifica que accepted.by/date/trigger este lleno y no sea el placeholder, patron de own_chats/tools/check_harvest_accepted.py (DGX-505)."}
created: 2026-09-09
accepted: {"by": "the maintainer + Claude, revision de deuda 2026-09-09", "date": "2026-09-09", "trigger": "hardware/escenario distinto -- reabrir si ATOM cambia de configuracion (cluster, rack, otro chip)"}
reason: "La falla ocurre en firmware/BIOS antes de que el kernel monte nada -- no hay proceso corriendo, journal, ni /proc que leer. blackbox opera post-boot, sobre un sistema ya arrancado."
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

- Se documenta la falta de detección en entorno de recupero USB aislando la falla a nivel de hardware/BIOS previo al cargador de arranque — `knowledge/references/forum_nvidia_354167_dgx-spark-nvme-drive-not-detected-no-nvme-device-found.md:"*   **Falta de detección en Entorno de Recupero/Rescue USB:** La incapacidad del USB de recuperación para detectar el dispositivo sugiere que el problema reside en el nivel de hardware/BIOS y no en el sistema operativo o controladores del host. Esto aísla la falla antes del cargador de arranque."`
- En el mapeo de proyectos, se relaciona el fallo de hardware físico no detectable por software con el proyecto DGX Spark — `knowledge/references/forum_nvidia_354167_dgx-spark-nvme-drive-not-detected-no-nvme-device-found.md:"*   **DGX Spark: Fallo de enumeración NVMe/PCIe en firmware.** Este mecanismo ataca el dolor de **fallo de hardware físico/no detectable por software**, que es el síntoma principal reportado. Requiere validación de hardware a bajo nivel (UEFI/BIOS) antes de cualquier solución de software."`

## Por qué se sugiere para blackbox en concreto

El mecanismo se atribuye a 'Liberation Watchdog' como 'deteccion de hardware fantasma o inaccesible fuera del sistema operativo', pero ese es exactamente el dominio de blackbox (telemetria/monitoreo de hardware de la AI TOP ATOM, GB10) -- Liberation Watchdog nunca existio como satelite con ese objetivo.

## Procedencia

- Fuente original: https://forums.developer.nvidia.com/t/dgx-spark-nvme-drive-not-detected-no-nvme-device-found/354167
- Dictamen de cosecha, ruta absoluta: `~/projects/Atlas/docs/agent_findings/2026-09-05_cosecha_forum_nvidia_354167_dgx-spark-nvme-drive-not-detected-no-nvme-device-found.md`
- Corregido el 2026-09-09 (DGX-503): el dictamen original interrogó estos mecanismos sólo contra
  Atlas/aequitas_os porque la lista de flota de Atlas estaba rota (DGX-502) y no consideraba
  a blackbox en absoluto.

## Lo que esta ficha NO decide

No dice que blackbox deba adoptar nada. No mide si el código fuente es
production-ready, tiene licencia compatible, o pasa los propios gates de este repo -- eso lo
evalúa quien trabaje aquí, si decide que vale la pena mirarlo.
