---
id: HARVEST-niklasfrick-spark-dashboard
kind: task
title: "Evaluar adopción: mecanismo cosechado por Atlas (niklasfrick-spark-dashboard)"
status: open
severity: P3
origin: asserted
satd_family: HARVEST_SUGGESTION
close_check: {"cmd": "python -m tools.check_harvest_accepted tasks/backlog/HARVEST-niklasfrick-spark-dashboard.md", "expect": "exit_zero", "porque": "Sugerencia de adopcion, no un defecto -- verifica que accepted.by/date/trigger este lleno y no sea el placeholder, patron de own_chats/tools/check_harvest_accepted.py (DGX-505)."}
created: 2026-09-09
accepted: {"by": "the maintainer + Claude, revision de deuda 2026-09-09", "date": "2026-09-09", "trigger": "revisado a fondo (codigo + fuente citada) y sin valor incremental hoy -- reabrir si aparece un caso real medido en esta maquina que lo contradiga"}
reason: "El polling NVML/procfs ya esta cubierto por atom_gpu_telemetry.py + sar; el monitoreo de vLLM ya esta cubierto por '/metrics de vLLM' (adoptado); el resto es UI de dashboard, fuera de alcance."
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

- Mecanismo 1: Polling periódico (1 segundo) de NVML, sysinfo y procfs para extraer métricas de GPU (utilización, temperatura, power draw, clock frequencies, fan speed), CPU (agregado y per-core), memoria (CPU RAM vs GPU VRAM unificada en sistemas DGX), disco y red — convierte lecturas de bajo nivel en snapshots estructurados que viajan por broadcast channel — `knowledge/references/github_com_niklasfrick_spark_dashboard.md:"1s polling via NVML, sysinfo, procfs"` `knowledge/references/github_com_niklasfrick_spark_dashboard.md:"GPU utilization, temperature, power draw, clock frequencies, fan speed"` `knowledge/references/github_com_niklasfrick_spark_dashboard.md:"Memory breakdown — CPU RAM and GPU VRAM separately on discrete-GPU hosts, or a single unified pool on systems where CPU and GPU share memory (e.g. DGX Spark GB10, GH200)"`
- Mecanismo 1 interrogatorio: (a) El polling detecta "thermal throttling, hardware slowdown, power brake" (categoría: degradación térmica que impacta inference — no nombrada explícitamente en el texto acotado pero es preocupación del domain); (b) existe a escala de DGX — el README menciona explícitamente "Developed and tested on the NVIDIA DGX Spark"; (c) nombra "Memory breakdown — CPU RAM and GPU VRAM separately on discrete-GPU hosts, or a single unified pool on systems where CPU and GPU share memory (e.g. DGX Spark GB10, GH200)" — estructura que probablemente replicamos en facturación/costos — `knowledge/references/github_com_niklasfrick_spark_dashboard.md:"Developed and tested on the NVIDIA DGX Spark, but works on any Linux host with NVIDIA drivers"`
- Mecanismo 2 interrogatorio: (a) Falla atacada es "manual config + discovery latency cuando engines mueren/respawneán" (categoría: información desincronizada en estados dinámicos — no explícitamente mencionada en el texto acotado); (b) escala multi-engine confirmada en features: "Run and monitor any number of inference engines side by side"; (c) probablemente otros proyectos re-implementan este scan, pero el README no lo nombra — `knowledge/references/github_com_niklasfrick_spark_dashboard.md:"--engine <TYPE> Manual engine type (e.g. vllm) [env: SPARK_DASHBOARD_ENGINE]"` (muestra que existe fallback a config manual cuando auto-detect falla)

## Por qué se sugiere para blackbox en concreto

El mecanismo central es polling NVML/sysinfo/procfs de GPU/CPU/memoria-unificada/disco/red para telemetria de hardware NVIDIA GB10 -- exactamente el dominio declarado de blackbox ('Caja negra / telemetria de la AI TOP ATOM (NVIDIA GB10): monitoreo de hardware, logs, systemd units'), miembro real nunca considerado porque el interrogatorio solo nombro 'DGX Spark' (hardware, no satelite) y Atlas.

## Procedencia

- Fuente original: https://github.com/niklasfrick/spark-dashboard
- Dictamen de cosecha, ruta absoluta: `~/projects/Atlas/docs/agent_findings/2026-09-06_cosecha_github_com_niklasfrick_spark_dashboard.md`
- Corregido el 2026-09-09 (DGX-503): el dictamen original interrogó estos mecanismos sólo contra
  Atlas/aequitas_os porque la lista de flota de Atlas estaba rota (DGX-502) y no consideraba
  a blackbox en absoluto.

## Lo que esta ficha NO decide

No dice que blackbox deba adoptar nada. No mide si el código fuente es
production-ready, tiene licencia compatible, o pasa los propios gates de este repo -- eso lo
evalúa quien trabaje aquí, si decide que vale la pena mirarlo.
