---
id: HARVEST-353683-dgx-spark-gpu-usage-0-after-24-hours-open-web
kind: task
title: "Evaluar adopción: mecanismo cosechado por Atlas (353683-dgx-spark-gpu-usage-0-after-24-hours-open-webui)"
status: open
severity: P3
origin: asserted
satd_family: HARVEST_SUGGESTION
close_check: {"cmd": "python -m tools.check_harvest_accepted tasks/backlog/HARVEST-353683-dgx-spark-gpu-usage-0-after-24-hours-open-web.md", "expect": "exit_zero", "porque": "Sugerencia de adopcion, no un defecto -- verifica que accepted.by/date/trigger este lleno y no sea el placeholder, patron de own_chats/tools/check_harvest_accepted.py (DGX-505)."}
created: 2026-09-09
accepted: {"by": "the maintainer + Claude, revision de deuda 2026-09-09", "date": "2026-09-09", "trigger": "adoptado -- el trabajo real vive en tasks/backlog/FEATURE-GPU-UTIL-CERO-FALLBACK-CPU.md, no en esta ficha de evaluacion"}
reason: "Mismo mecanismo que HARVEST-348356 (0% de utilizacion con carga activa = fallback silencioso a CPU). Se consolida en FEATURE-GPU-UTIL-CERO-FALLBACK-CPU."
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

- Interrogatorio Paso 2 (Mecanismo 3 en Liberation Watchdog): Ataca la categoría de falla de degradación silenciosa de acelerador a CPU por saturación/inaccesibilidad de memoria y recursos — `knowledge/references/forum_nvidia_353683_dgx-spark-gpu-usage-0-after-24-hours-open-webui.md:"El consumo de memoria del proceso python (~19.8GB) y la falta de uso de GPU provocan que los flujos de trabajo de IA se degraden a ejecución CPU. Esto es un síntoma de fondo que Liberation Watchdog monitorearía para detectar desperdicio de recursos."`

## Por qué se sugiere para blackbox en concreto

El único hallazgo verificado atribuye la detección de 'degradación silenciosa de acelerador a CPU' / 'desperdicio de recursos' a 'Liberation Watchdog' (nombre falso); ese mecanismo de monitoreo de hardware/systemd es el dominio declarado de blackbox.

## Procedencia

- Fuente original: https://forums.developer.nvidia.com/t/dgx-spark-gpu-usage-0-after-24-hours-open-webui/353683
- Dictamen de cosecha, ruta absoluta: `~/projects/Atlas/docs/agent_findings/2026-09-05_cosecha_forum_nvidia_353683_dgx-spark-gpu-usage-0-after-24-hours-open-webui.md`
- Corregido el 2026-09-09 (DGX-503): el dictamen original interrogó estos mecanismos sólo contra
  Atlas/aequitas_os porque la lista de flota de Atlas estaba rota (DGX-502) y no consideraba
  a blackbox en absoluto.

## Lo que esta ficha NO decide

No dice que blackbox deba adoptar nada. No mide si el código fuente es
production-ready, tiene licencia compatible, o pasa los propios gates de este repo -- eso lo
evalúa quien trabaje aquí, si decide que vale la pena mirarlo.
