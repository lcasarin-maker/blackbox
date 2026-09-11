---
id: HARVEST-354395-can-not-reset-spark-gpu
kind: task
title: "Evaluar adopción: mecanismo cosechado por Atlas (354395-can-not-reset-spark-gpu)"
status: open
severity: P3
origin: asserted
satd_family: HARVEST_SUGGESTION
close_check: {"cmd": "python -m tools.check_harvest_accepted tasks/backlog/HARVEST-354395-can-not-reset-spark-gpu.md", "expect": "exit_zero", "porque": "Sugerencia de adopcion, no un defecto -- verifica que accepted.by/date/trigger este lleno y no sea el placeholder, patron de own_chats/tools/check_harvest_accepted.py (DGX-505)."}
created: 2026-09-09
accepted: {"by": "the maintainer + Claude, revision de deuda 2026-09-09", "date": "2026-09-09", "trigger": "revisado a fondo (codigo + fuente citada) y sin valor incremental hoy -- reabrir si aparece un caso real medido en esta maquina que lo contradiga"}
reason: "Revisada la fuente citada completa: no hay ninguna tecnica de diagnostico rescatable bajo la reatribucion a 'Liberation Watchdog' (satelite inexistente) -- solo el sintoma nombrado dos veces ('estados de hardware colgados', 'sintonizacion de firmware'), sin comando ni umbral."
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

(ninguno)

## Por qué se sugiere para blackbox en concreto

El interrogatorio mapea la deteccion de 'estados de hardware colgados o no reseteables' a 'Liberation Watchdog' (fake) y la sintonizacion de firmware/VRAM a 'DGX Spark' (fake); ambos mecanismos de monitoreo/estado de GPU pertenecen al dominio real de blackbox (monitoreo de hardware GB10, logs, systemd).

## Procedencia

- Fuente original: https://forums.developer.nvidia.com/t/can-not-reset-spark-gpu/354395
- Dictamen de cosecha, ruta absoluta: `~/projects/Atlas/docs/agent_findings/2026-09-05_cosecha_forum_nvidia_354395_can-not-reset-spark-gpu.md`
- Corregido el 2026-09-09 (DGX-503): el dictamen original interrogó estos mecanismos sólo contra
  Atlas/aequitas_os porque la lista de flota de Atlas estaba rota (DGX-502) y no consideraba
  a blackbox en absoluto.

## Lo que esta ficha NO decide

No dice que blackbox deba adoptar nada. No mide si el código fuente es
production-ready, tiene licencia compatible, o pasa los propios gates de este repo -- eso lo
evalúa quien trabaje aquí, si decide que vale la pena mirarlo.
