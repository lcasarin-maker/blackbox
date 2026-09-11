---
id: HARVEST-348223-dgx-spark-gpu-crash
kind: task
title: "Evaluar adopción: mecanismo cosechado por Atlas (348223-dgx-spark-gpu-crash)"
status: open
severity: P3
origin: asserted
satd_family: HARVEST_SUGGESTION
close_check: {"cmd": "python -m tools.check_harvest_accepted tasks/backlog/HARVEST-348223-dgx-spark-gpu-crash.md", "expect": "exit_zero", "porque": "Sugerencia de adopcion, no un defecto -- verifica que accepted.by/date/trigger este lleno y no sea el placeholder, patron de own_chats/tools/check_harvest_accepted.py (DGX-505)."}
created: 2026-09-09
accepted: {"by": "the maintainer + Claude, revision de deuda 2026-09-09", "date": "2026-09-09", "trigger": "adoptado -- el trabajo real vive en tasks/backlog/FEATURE-GPU-XID-DETECTION.md, no en esta ficha de evaluacion"}
reason: "Sonda de disponibilidad de GPU (nvidia-smi con timeout) no duplica la telemetria de 5s: distingue 'no responde' de 'no corrio la muestra'. Se consolida en FEATURE-GPU-XID-DETECTION junto con la deteccion de codigos Xid."
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

- Interrogatorio Mecanismo 2 (Paso 2): Ataca la categoría de falla conocida de cuelgues no interactivos del driver de GPU / kernel panics silenciosos; a nuestra escala mapea a pipelines de ingesta automatizada de diagnósticos en Atlas; formaliza la recolección post-mortem de logs de sistema y estado de aceleradores — `knowledge/references/forum_nvidia_348223_dgx-spark-gpu-crash.md:"Atlas como la pipeline de diagnóstico/ingestión donde estos logs serían procesados para detección de patrones de fallo hardware"`
- Interrogatorio Mecanismo 3 (Paso 2): Ataca la categoría de falla conocida de falla de inicialización de hardware durante el arranque (hardware handshake failure); a nuestra escala pasa de monitoreo manual de red a sondas locales de disponibilidad de acelerador acopladas a healthchecks; formaliza la detección de nodos zombi accesibles por red pero sin cómputo acelerado — `knowledge/references/forum_nvidia_348223_dgx-spark-gpu-crash.md:"deja el sistema en un estado semi-operativo donde la red responde pero la GPU no."`

## Por qué se sugiere para blackbox en concreto

El hallazgo VERIFICADO del Mecanismo 3 describe 'sondas locales de disponibilidad de acelerador acopladas a healthchecks' para detectar 'nodos zombi' (red responde, GPU no) sin interrogar contra ningún satélite; ese healthcheck de hardware es exactamente el dominio declarado de blackbox (monitoreo de hardware/telemetría de la AI TOP ATOM GB10), nunca considerado por la lista rota de 5.

## Procedencia

- Fuente original: https://forums.developer.nvidia.com/t/dgx-spark-gpu-crash/348223
- Dictamen de cosecha, ruta absoluta: `~/projects/Atlas/docs/agent_findings/2026-09-05_cosecha_forum_nvidia_348223_dgx-spark-gpu-crash.md`
- Corregido el 2026-09-09 (DGX-503): el dictamen original interrogó estos mecanismos sólo contra
  Atlas/aequitas_os porque la lista de flota de Atlas estaba rota (DGX-502) y no consideraba
  a blackbox en absoluto.

## Lo que esta ficha NO decide

No dice que blackbox deba adoptar nada. No mide si el código fuente es
production-ready, tiene licencia compatible, o pasa los propios gates de este repo -- eso lo
evalúa quien trabaje aquí, si decide que vale la pena mirarlo.
