---
id: HARVEST-355865-problem-with-simple-framebuffer
kind: task
title: "Evaluar adopción: mecanismo cosechado por Atlas (355865-problem-with-simple-framebuffer)"
status: open
severity: P3
origin: asserted
satd_family: HARVEST_SUGGESTION
close_check: {"cmd": "python -m tools.check_harvest_accepted tasks/backlog/HARVEST-355865-problem-with-simple-framebuffer.md", "expect": "exit_zero", "porque": "Sugerencia de adopcion, no un defecto -- verifica que accepted.by/date/trigger este lleno y no sea el placeholder, patron de own_chats/tools/check_harvest_accepted.py (DGX-505)."}
created: 2026-09-09
accepted: {"by": "the maintainer + Claude, revision de deuda 2026-09-09", "date": "2026-09-09", "trigger": "adoptado -- el trabajo real vive en tasks/backlog/FEATURE-SHUTDOWN-CAUSA-CLASIFICADOR.md, no en esta ficha de evaluacion"}
reason: "El mecanismo 3 (clasificar causa de reinicio no limpio -- PSU, GPU hang, thermal trip -- via logs de kernel) es real y hoy ausente: bb scan cruza OOM y termico por separado, sin armar un veredicto de causa. Se consolida en FEATURE-SHUTDOWN-CAUSA-CLASIFICADOR."
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

- Paso 2 para Mecanismo 1: ataca en Atlas la categoría de falla de ruido en telemetría de kernel y falsos positivos de kernel panic en hardware de borde — `knowledge/references/forum_nvidia_355865_problem-with-simple-framebuffer.md:"Aporta a **Atlas**. El enrutamiento de logs y abstracción de hardware es fundamental para que Atlas gestione la diversidad de kernels y hardware de borde. Ayuda a distinguir ruido de señal en la telemetría de borde."`
- Paso 2 para Mecanismo 2: ataca en DGX Spark la categoría de falla de cuelgues o congelamientos silenciosos (silent freeze) por problemas de driver o GPU durante flujos de entrenamiento — `knowledge/references/forum_nvidia_355865_problem-with-simple-framebuffer.md:"Aporta a **DGX Spark**. La capacidad de filtrar y correlacionar logs de kernel en tiempo real o post-mortem es crítica para la estabilidad de los flujos de trabajo de IA (PyTorch/Training) en hardware DGX"`
- Paso 2 para Mecanismo 3: ataca en Liberation Watchdog la categoría de falla de reinicios no limpios no clasificados (por corte de energía, cuelgue de GPU o thermal trip) — `knowledge/references/forum_nvidia_355865_problem-with-simple-framebuffer.md:"Aporta a **Liberation Watchdog**. La capacidad de detectar reinicios no limpios y clasificar su causa (PSU, GPU hang, Thermal trip) es la base para cualquier sistema de watchdog"`
- Disparador de reevaluación de la cosecha: validación y adopción en entornos de borde y DGX para endurecer telemetría y diagnóstico de estabilidad en entrenamientos PyTorch — `knowledge/references/forum_nvidia_355865_problem-with-simple-framebuffer.md:"La acción es bajar este patrón de diagnóstico, validarlo en entornos de borde y DGX, y adoptarlo para endurecer los pipelines de estabilidad."`

## Por qué se sugiere para blackbox en concreto

El mecanismo de deteccion y clasificacion de causa de reinicios no limpios (PSU, GPU hang, thermal trip) se atribuye a 'Liberation Watchdog' como 'la base para cualquier sistema de watchdog', pero ese diagnostico de causa-de-reinicio via logs de kernel es exactamente el dominio real de blackbox (monitoreo de hardware, logs, systemd de la AI TOP ATOM).

## Procedencia

- Fuente original: https://forums.developer.nvidia.com/t/problem-with-simple-framebuffer/355865
- Dictamen de cosecha, ruta absoluta: `~/projects/Atlas/docs/agent_findings/2026-09-05_cosecha_forum_nvidia_355865_problem-with-simple-framebuffer.md`
- Corregido el 2026-09-09 (DGX-503): el dictamen original interrogó estos mecanismos sólo contra
  Atlas/aequitas_os porque la lista de flota de Atlas estaba rota (DGX-502) y no consideraba
  a blackbox en absoluto.

## Lo que esta ficha NO decide

No dice que blackbox deba adoptar nada. No mide si el código fuente es
production-ready, tiene licencia compatible, o pasa los propios gates de este repo -- eso lo
evalúa quien trabaje aquí, si decide que vale la pena mirarlo.
