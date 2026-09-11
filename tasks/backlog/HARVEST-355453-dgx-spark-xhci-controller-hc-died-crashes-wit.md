---
id: HARVEST-355453-dgx-spark-xhci-controller-hc-died-crashes-wit
kind: task
title: "Evaluar adopción: mecanismo cosechado por Atlas (355453-dgx-spark-xhci-controller-hc-died-crashes-with-realsense-d435i-)"
status: open
severity: P3
origin: asserted
satd_family: HARVEST_SUGGESTION
close_check: {"cmd": "python -m tools.check_harvest_accepted tasks/backlog/HARVEST-355453-dgx-spark-xhci-controller-hc-died-crashes-wit.md", "expect": "exit_zero", "porque": "Sugerencia de adopcion, no un defecto -- verifica que accepted.by/date/trigger este lleno y no sea el placeholder, patron de own_chats/tools/check_harvest_accepted.py (DGX-505)."}
created: 2026-09-09
accepted: {"by": "the maintainer + Claude, revision de deuda 2026-09-09", "date": "2026-09-09", "trigger": "adoptado -- el trabajo real vive en tasks/backlog/FEATURE-USB-XHCI-FORENSICS.md, no en esta ficha de evaluacion"}
reason: "'HC died' del controlador xHCI es una firma de fallo de kernel nueva, ausente del catalogo de bb scan. Se consolida en FEATURE-USB-XHCI-FORENSICS."
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

- Mecanismo 1 (Hardware de Control Host XHCI MT8901): El controlador xHCI en NVIDIA DGX Spark (chip MT8901) falla al procesar transferencias ep0 tras iniciar un flujo de video, evidenciado por el registro donde el host no responde al comando de parada de endpoint — `knowledge/references/forum_nvidia_355453_dgx-spark-xhci-controller-hc-died-crashes-with-realsense-d435i-streaming-30fps-d.md:"El controlador xHCI en la plataforma NVIDIA DGX Spark (chip MT8901) falla al procesar transferencias ep0 (endpoint 0) después de iniciar un flujo de video."`

## Por qué se sugiere para blackbox en concreto

El diagnostico del estado 'HC died' del controlador xHCI se atribuye a 'Liberation Watchdog' como si su mision fuera 'monitorear y reportar fallos de infraestructura', pero ese es el dominio real de blackbox (telemetria/monitoreo de hardware GB10); Liberation Watchdog nunca tuvo esa mision.

## Procedencia

- Fuente original: https://forums.developer.nvidia.com/t/dgx-spark-xhci-controller-hc-died-crashes-with-realsense-d435i-streaming-30fps-depth-rgb/355453
- Dictamen de cosecha, ruta absoluta: `~/projects/Atlas/docs/agent_findings/2026-09-05_cosecha_forum_nvidia_355453_dgx-spark-xhci-controller-hc-died-crashes-with-realsense-d435i-streaming-30fps-d.md`
- Corregido el 2026-09-09 (DGX-503): el dictamen original interrogó estos mecanismos sólo contra
  Atlas/aequitas_os porque la lista de flota de Atlas estaba rota (DGX-502) y no consideraba
  a blackbox en absoluto.

## Lo que esta ficha NO decide

No dice que blackbox deba adoptar nada. No mide si el código fuente es
production-ready, tiene licencia compatible, o pasa los propios gates de este repo -- eso lo
evalúa quien trabaje aquí, si decide que vale la pena mirarlo.
