---
id: HARVEST-367765-dear-nvidia-nvidia-smi-is-broken-on-the-dgx-s
kind: task
title: "Evaluar adopción: mecanismo cosechado por Atlas (367765-dear-nvidia-nvidia-smi-is-broken-on-the-dgx-spark)"
status: open
severity: P3
origin: asserted
satd_family: HARVEST_SUGGESTION
close_check: {"cmd": "python -m tools.check_harvest_accepted tasks/backlog/HARVEST-367765-dear-nvidia-nvidia-smi-is-broken-on-the-dgx-s.md", "expect": "exit_zero", "porque": "Sugerencia de adopcion, no un defecto -- verifica que accepted.by/date/trigger este lleno y no sea el placeholder, patron de own_chats/tools/check_harvest_accepted.py (DGX-505)."}
created: 2026-09-09
accepted: {"by": "the maintainer + Claude, revision de deuda 2026-09-09", "date": "2026-09-09", "trigger": "revisado a fondo (codigo + fuente citada) y sin valor incremental hoy -- reabrir si aparece un caso real medido en esta maquina que lo contradiga"}
reason: "Verificado en codigo: el hueco real (--query-gpu da [N/A] para memoria en GB10) ya esta resuelto en bin/bb via --query-compute-apps, documentado ademas en el README ('Dos cosas que esta maquina ya sabia'). La parte de mitigar/watchdog activo no es trabajo de blackbox."
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

- Veredicto y disparador de reevaluación: veredicto formal `COS` justificado por la creación de ítem de backlog en DGX Spark para desarrollar/integrar un puente de monitoreo unificado, activado por la brecha de API de monitoreo en GB10 — `knowledge/references/forum_nvidia_367765_dear-nvidia-nvidia-smi-is-broken-on-the-dgx-spark.md:"El disparador es la brecha de API identificada para la monitorización de GB10."`

## Por qué se sugiere para blackbox en concreto

El hallazgo verificado dice 'Vigilancia de anomalías en Liberation Watchdog: la falta de soporte CLI para memoria constituye una anomalía de hardware a reportar o mitigar por el watchdog' -- Liberation Watchdog es nombre falso; el mecanismo (monitoreo/telemetría de hardware GB10/AI TOP, systemd) es exactamente el dominio de blackbox ('Caja negra / telemetría de la AI TOP ATOM: monitoreo de hardware, logs, systemd units'). Además 'backlog en DGX Spark' debería leerse como backlog de Atlas.

## Procedencia

- Fuente original: https://forums.developer.nvidia.com/t/dear-nvidia-nvidia-smi-is-broken-on-the-dgx-spark/367765
- Dictamen de cosecha, ruta absoluta: `~/projects/Atlas/docs/agent_findings/2026-09-05_cosecha_forum_nvidia_367765_dear-nvidia-nvidia-smi-is-broken-on-the-dgx-spark.md`
- Corregido el 2026-09-09 (DGX-503): el dictamen original interrogó estos mecanismos sólo contra
  Atlas/aequitas_os porque la lista de flota de Atlas estaba rota (DGX-502) y no consideraba
  a blackbox en absoluto.

## Lo que esta ficha NO decide

No dice que blackbox deba adoptar nada. No mide si el código fuente es
production-ready, tiene licencia compatible, o pasa los propios gates de este repo -- eso lo
evalúa quien trabaje aquí, si decide que vale la pena mirarlo.
