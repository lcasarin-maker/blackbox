---
id: HARVEST-365609-nvidia-dgx-spark-continuously-freezing-hangin
kind: task
title: "Evaluar adopción: mecanismo cosechado por Atlas (365609-nvidia-dgx-spark-continuously-freezing-hanging-and-or-rebooting)"
status: open
severity: P3
origin: asserted
satd_family: HARVEST_SUGGESTION
close_check: {"cmd": "python -m tools.check_harvest_accepted tasks/backlog/HARVEST-365609-nvidia-dgx-spark-continuously-freezing-hangin.md", "expect": "exit_zero", "porque": "Sugerencia de adopcion, no un defecto -- verifica que accepted.by/date/trigger este lleno y no sea el placeholder, patron de own_chats/tools/check_harvest_accepted.py (DGX-505)."}
created: 2026-09-09
accepted: {"by": "the maintainer + Claude, revision de deuda 2026-09-09", "date": "2026-09-09", "trigger": "adoptado -- el trabajo real vive en tasks/backlog/FEATURE-USB-XHCI-FORENSICS.md, no en esta ficha de evaluacion"}
reason: "Erosion de runtime-PM del controlador xHCI y conflictos de enumeracion USB en topologias encadenadas son tecnicas concretas y nuevas, mismo subsistema que HARVEST-355453/362015. El 'kernel panic por sobrecalentamiento en zona USB-C' se pliega en el mismo ticket como señal termica localizada a evaluar. Se consolida en FEATURE-USB-XHCI-FORENSICS."
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

- Mecanismo 1 (Erosión del controlador xHCI/USB runtime-PM): en los logs verbatim se detecta falla en la gestión de energía runtime del controlador USB, impidiendo transitar entre estados activos e inactivos y causando reinicios forzosos al detectar periféricos. — `knowledge/references/forum_nvidia_365609_nvidia-dgx-spark-continuously-freezing-hanging-and-or-rebooting.md:"Erosión del controlador xHCI/USB runtime-PM"`
- Mecanismo 2 (Conflicto de enumeración de dispositivos USB en cadena): la topología de periféricos en cascada degrada la compatibilidad de handshake USB y genera conflictos de IDs y asignación de IRQ en xHCI. — `knowledge/references/forum_nvidia_365609_nvidia-dgx-spark-continuously-freezing-hanging-and-or-rebooting.md:"Conflicto de enumeración de dispositivos USB en cadena (hub + dongle + periférico)"`
- Mecanismo 3 (Kernel panic inducido por sobrecarga térmica en la zona USB-C): calentamiento localizado (>45°C en ~15 min) que dispara protecciones térmicas de firmware/BIOS forzando reinicios para proteger el controlador. — `knowledge/references/forum_nvidia_365609_nvidia-dgx-spark-continuously-freezing-hanging-and-or-rebooting.md:"Kernel panic inducido por sobrecarga térmica en la zona USB-C"`
- Paso 2 (Fallas que ataca): el problema ataca la categoría de inestabilidad térmica y de bus I/O en DGX Spark, fallas de estabilidad en boot/recovery en Atlas, y escenarios de bucle de reinicio fatal en Liberation Watchdog. — `knowledge/references/forum_nvidia_365609_nvidia-dgx-spark-continuously-freezing-hanging-and-or-rebooting.md:"Mapeo a Proyectos de la Flota"`

## Por qué se sugiere para blackbox en concreto

El mapeo a la flota atribuye "escenarios de bucle de reinicio fatal" a "Liberation Watchdog" (nombre falso); ese monitoreo de reinicios/estabilidad térmica es el dominio exacto de blackbox (telemetría de hardware, logs, systemd units); el veredicto COS no cambia, se sostiene vía los mecanismos de USB/térmico mapeados a DGX Spark/Atlas.

## Procedencia

- Fuente original: https://forums.developer.nvidia.com/t/nvidia-dgx-spark-continuously-freezing-hanging-and-or-rebooting/365609
- Dictamen de cosecha, ruta absoluta: `~/projects/Atlas/docs/agent_findings/2026-09-05_cosecha_forum_nvidia_365609_nvidia-dgx-spark-continuously-freezing-hanging-and-or-rebooting.md`
- Corregido el 2026-09-09 (DGX-503): el dictamen original interrogó estos mecanismos sólo contra
  Atlas/aequitas_os porque la lista de flota de Atlas estaba rota (DGX-502) y no consideraba
  a blackbox en absoluto.

## Lo que esta ficha NO decide

No dice que blackbox deba adoptar nada. No mide si el código fuente es
production-ready, tiene licencia compatible, o pasa los propios gates de este repo -- eso lo
evalúa quien trabaje aquí, si decide que vale la pena mirarlo.
