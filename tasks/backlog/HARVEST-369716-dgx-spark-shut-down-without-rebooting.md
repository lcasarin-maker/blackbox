---
id: HARVEST-369716-dgx-spark-shut-down-without-rebooting
kind: task
title: "Evaluar adopción: mecanismo cosechado por Atlas (369716-dgx-spark-shut-down-without-rebooting)"
status: open
severity: P3
origin: asserted
satd_family: HARVEST_SUGGESTION
close_check: {"cmd": "python -m tools.check_harvest_accepted tasks/backlog/HARVEST-369716-dgx-spark-shut-down-without-rebooting.md", "expect": "exit_zero", "porque": "Sugerencia de adopcion, no un defecto -- verifica que accepted.by/date/trigger este lleno y no sea el placeholder, patron de own_chats/tools/check_harvest_accepted.py (DGX-505)."}
created: 2026-09-09
accepted: {"by": "the maintainer + Claude, revision de deuda 2026-09-09", "date": "2026-09-09", "trigger": "adoptado -- el trabajo real vive en tasks/backlog/FEATURE-SHUTDOWN-CAUSA-CLASIFICADOR.md, no en esta ficha de evaluacion"}
reason: "PCIe RxErr/AER/hotplug removal es una categoria de fallo completamente ausente de bb scan hoy. El 'heartbeat que drena cargas' que la misma ficha propone es mitigacion activa y queda fuera. Se consolida en FEATURE-SHUTDOWN-CAUSA-CLASIFICADOR."
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

- Paso 2 aplicado a Atlas y Liberation Watchdog: La gestión de hotplug y eventos de remoción de cable aplica a Atlas para detección de presencia y reemplazo en caliente; en Liberation Watchdog, la secuencia RxErr → AER → hotplug removal podría activar un heartbeat para drenar cargas ante fallos de hardware — `knowledge/references/forum_nvidia_369716_dgx-spark-shut-down-without-rebooting.md:12-13`

## Por qué se sugiere para blackbox en concreto

El dictamen atribuye la detección de fallas AER/PCIe hotplug y la señal de drenaje ante falla de hardware a 'Liberation Watchdog' (herramienta interna de Atlas, no satélite real); el mecanismo -- monitoreo de eventos de kernel/hardware y logging de fallas físicas del GB10 -- es exactamente el dominio declarado de blackbox ('telemetria de la AI TOP ATOM: monitoreo de hardware, logs, systemd units'), nunca considerado por estar fuera de la lista rota de 5.

## Procedencia

- Fuente original: https://forums.developer.nvidia.com/t/dgx-spark-shut-down-without-rebooting/369716
- Dictamen de cosecha, ruta absoluta: `~/projects/Atlas/docs/agent_findings/2026-09-05_cosecha_forum_nvidia_369716_dgx-spark-shut-down-without-rebooting.md`
- Corregido el 2026-09-09 (DGX-503): el dictamen original interrogó estos mecanismos sólo contra
  Atlas/aequitas_os porque la lista de flota de Atlas estaba rota (DGX-502) y no consideraba
  a blackbox en absoluto.

## Lo que esta ficha NO decide

No dice que blackbox deba adoptar nada. No mide si el código fuente es
production-ready, tiene licencia compatible, o pasa los propios gates de este repo -- eso lo
evalúa quien trabaje aquí, si decide que vale la pena mirarlo.
