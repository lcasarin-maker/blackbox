---
id: HARVEST-376039-dgx-spark-gb10-gpu-clock-pinned-at-721-mhz-un
kind: task
title: "Evaluar adopción: mecanismo cosechado por Atlas (376039-dgx-spark-gb10-gpu-clock-pinned-at-721-mhz-under-full-load-no-t)"
status: open
severity: P3
origin: asserted
satd_family: HARVEST_SUGGESTION
close_check: {"cmd": "python -m tools.check_harvest_accepted tasks/backlog/HARVEST-376039-dgx-spark-gb10-gpu-clock-pinned-at-721-mhz-un.md", "expect": "exit_zero", "porque": "Sugerencia de adopcion, no un defecto -- verifica que accepted.by/date/trigger este lleno y no sea el placeholder, patron de own_chats/tools/check_harvest_accepted.py (DGX-505)."}
created: 2026-09-09
accepted: {"by": "the maintainer + Claude, revision de deuda 2026-09-09", "date": "2026-09-09", "trigger": "adoptado -- el trabajo real vive en tasks/backlog/FEATURE-CLOCK-THROTTLE-CRUZADO.md, no en esta ficha de evaluacion"}
reason: "Mismo mecanismo exacto que HARVEST-364166/374274: desajuste entre bandera de throttle y reloj real, verificado como hueco real en bb scan. Se consolida en FEATURE-CLOCK-THROTTLE-CRUZADO."
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

- Mecanismo 1 (Gestión de reloj no configurable): El comando `nvidia-smi -lgc 3003` falla de forma silenciosa manteniendo la frecuencia fija en 721 MHz, implementando una restricción hard-capped en firmware/BSP sin interfaz en espacio de usuario. — `knowledge/references/forum_nvidia_376039_dgx-spark-gb10-gpu-clock-pinned-at-721-mhz-under-full-load-no-throttling-not-lif.md:7`
- Mecanismo 2 (Ausencia de nodos devfreq y modelo de energía): El entorno opera sin herramientas de ajuste de frecuencia dinámica ni interfaces de escala de energía en DGX OS 7.5.0. — `knowledge/references/forum_nvidia_376039_dgx-spark-gb10-gpu-clock-pinned-at-721-mhz-under-full-load-no-throttling-not-lif.md:9`
- Mecanismo 3 (Telemetría de Clock Event Reasons): Los eventos de reloj informan estado inactivo sin banderas de throttling activas a pesar de operar a una fracción del reloj nominal bajo carga. — `knowledge/references/forum_nvidia_376039_dgx-spark-gb10-gpu-clock-pinned-at-721-mhz-under-full-load-no-throttling-not-lif.md:11`
- Paso 2 sobre Mecanismo 1 y 2 (Falla conocida de flota): Mapeado directamente a DGX Spark (GB10) para abordar la incapacidad de escalar frecuencia SM más allá del reloj base bajo cargas plenas (categoría: bloqueo de frecuencia de reloj / degradación por negociación de energía de firmware tras agotamiento de memoria). — `knowledge/references/forum_nvidia_376039_dgx-spark-gb10-gpu-clock-pinned-at-721-mhz-under-full-load-no-throttling-not-lif.md:15`
- Paso 2 sobre Mecanismo 3 (Falla conocida de flota): Mapeado a Atlas para comprobar si la recuperación de políticas de reloj o documentación de firmware mitiga la falta de información sobre frecuencias soportadas (categoría: falla de observabilidad o telemetría incompleta de estado de hardware). — `knowledge/references/forum_nvidia_376039_dgx-spark-gb10-gpu-clock-pinned-at-721-mhz-under-full-load-no-throttling-not-lif.md:17`
- Paso 2 sobre Mecanismo 2 (Falla conocida de flota): Mapeado a Liberation Watchdog para detectar configuraciones de BSP ausentes o restrictivas que impiden la optimización de hardware (categoría: falla de supervisión de entorno/BSP). — `knowledge/references/forum_nvidia_376039_dgx-spark-gb10-gpu-clock-pinned-at-721-mhz-under-full-load-no-throttling-not-lif.md:19`
- Paso 3 (Veredicto y disparador): El documento dictamina veredicto COS con detonación de análisis de implementación de firmware BSP en DGX Spark para exponer políticas de reloj o validar reloj base intencional vs defecto de inicialización. — `knowledge/references/forum_nvidia_376039_dgx-spark-gb10-gpu-clock-pinned-at-721-mhz-under-full-load-no-throttling-not-lif.md:23-25`

## Por qué se sugiere para blackbox en concreto

El mecanismo verificado de 'detectar configuraciones de BSP ausentes o restrictivas que impiden la optimización de hardware' se mapeó a Liberation Watchdog (nombre falso) cuando esa supervisión de entorno/BSP de hardware es el dominio de blackbox (monitoreo de hardware, logs, systemd units de la AI TOP ATOM).

## Procedencia

- Fuente original: https://forums.developer.nvidia.com/t/dgx-spark-gb10-gpu-clock-pinned-at-721-mhz-under-full-load-no-throttling-not-liftable-via-nvidia-smi/376039
- Dictamen de cosecha, ruta absoluta: `~/projects/Atlas/docs/agent_findings/2026-09-05_cosecha_forum_nvidia_376039_dgx-spark-gb10-gpu-clock-pinned-at-721-mhz-under-full-load-no-throttling-not-lif.md`
- Corregido el 2026-09-09 (DGX-503): el dictamen original interrogó estos mecanismos sólo contra
  Atlas/aequitas_os porque la lista de flota de Atlas estaba rota (DGX-502) y no consideraba
  a blackbox en absoluto.

## Lo que esta ficha NO decide

No dice que blackbox deba adoptar nada. No mide si el código fuente es
production-ready, tiene licencia compatible, o pasa los propios gates de este repo -- eso lo
evalúa quien trabaje aquí, si decide que vale la pena mirarlo.
