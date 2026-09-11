---
id: HARVEST-354194-my-dgx-system-is-getting-shut-itself-down-whi
kind: task
title: "Evaluar adopción: mecanismo cosechado por Atlas (354194-my-dgx-system-is-getting-shut-itself-down-while-running-my-llm-)"
status: open
severity: P3
origin: asserted
satd_family: HARVEST_SUGGESTION
close_check: {"cmd": "python -m tools.check_harvest_accepted tasks/backlog/HARVEST-354194-my-dgx-system-is-getting-shut-itself-down-whi.md", "expect": "exit_zero", "porque": "Sugerencia de adopcion, no un defecto -- verifica que accepted.by/date/trigger este lleno y no sea el placeholder, patron de own_chats/tools/check_harvest_accepted.py (DGX-505)."}
created: 2026-09-09
accepted: {"by": "the maintainer + Claude, revision de deuda 2026-09-09", "date": "2026-09-09", "trigger": "adoptado -- el trabajo real vive en tasks/backlog/FEATURE-SHUTDOWN-CAUSA-CLASIFICADOR.md, no en esta ficha de evaluacion"}
reason: "Aunque Atlas no cito 'Mecanismos encontrados', la seccion 'por que se sugiere' SI trae una tecnica concreta y citable: firma de apagado por insuficiencia de energia PCIe (lspci SlotPowerLimit, mlx5_pcie_event). Se consolida en FEATURE-SHUTDOWN-CAUSA-CLASIFICADOR."
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

El mecanismo de deteccion de firma de apagado por insuficiencia de potencia PCIe (lspci SlotPowerLimit, mlx5_pcie_event) se atribuye a 'Liberation Watchdog' como si fuera un satelite de monitoreo de fallos de energia, pero ese mecanismo de telemetria de hardware/logs pertenece a blackbox, no a una herramienta interna de cola de Atlas.

## Procedencia

- Fuente original: https://forums.developer.nvidia.com/t/my-dgx-system-is-getting-shut-itself-down-while-running-my-llm-fine-tuning-project-ram-reaches-to-100-percent-along-with-gpu-reaches-100-percent/354194
- Dictamen de cosecha, ruta absoluta: `~/projects/Atlas/docs/agent_findings/2026-09-05_cosecha_forum_nvidia_354194_my-dgx-system-is-getting-shut-itself-down-while-running-my-llm-fine-tuning-proje.md`
- Corregido el 2026-09-09 (DGX-503): el dictamen original interrogó estos mecanismos sólo contra
  Atlas/aequitas_os porque la lista de flota de Atlas estaba rota (DGX-502) y no consideraba
  a blackbox en absoluto.

## Lo que esta ficha NO decide

No dice que blackbox deba adoptar nada. No mide si el código fuente es
production-ready, tiene licencia compatible, o pasa los propios gates de este repo -- eso lo
evalúa quien trabaje aquí, si decide que vale la pena mirarlo.
