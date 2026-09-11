---
id: HARVEST-354764-dgx-spark-ethernet-connection-unstable-after-
kind: task
title: "Evaluar adopción: mecanismo cosechado por Atlas (354764-dgx-spark-ethernet-connection-unstable-after-november-2025-upda)"
status: open
severity: P3
origin: asserted
satd_family: HARVEST_SUGGESTION
close_check: {"cmd": "python -m tools.check_harvest_accepted tasks/backlog/HARVEST-354764-dgx-spark-ethernet-connection-unstable-after-.md", "expect": "exit_zero", "porque": "Sugerencia de adopcion, no un defecto -- verifica que accepted.by/date/trigger este lleno y no sea el placeholder, patron de own_chats/tools/check_harvest_accepted.py (DGX-505)."}
created: 2026-09-09
accepted: {"by": "the maintainer + Claude, revision de deuda 2026-09-09", "date": "2026-09-09", "trigger": "adoptado -- el trabajo real vive en tasks/done/FEATURE-RED-CPU-SCAN.md, no en esta ficha de evaluacion"}
reason: "Contadores EEE/LPI via ethtool son una fuente de telemetria de red especifica y nueva. Se adopta solo la parte diagnostica (capturar estado EEE); el servicio systemd 'disable-eee' que la misma ficha propone es mitigacion y queda fuera. Consolidada en FEATURE-RED-CPU-SCAN como trabajo de red pendiente (ethtool no incluido en la primera pasada, ver notas del ticket)."
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

- El documento describe el mecanismo de autonegresis EEE y transición de estados LPI (Low Power Idle) tras la OTA 7.3.1, donde EEE entra en estados de bajo poder agresivamente provocando `Tx LPI: 19 (us)` y `Tx LPI: 12 (us)`, lo cual rompe la continuidad física del enlace Ethernet causando congelamiento silencioso del tráfico y caída de paquetes. — `knowledge/references/forum_nvidia_354764_dgx-spark-ethernet-connection-unstable-after-november-2025-update-eee-energy-eff.md:"1. **Autonegresis EEE y transición de estados LPI (Low Power Idle):** El documento describe cómo después de la OTA 7.3.1, la EEE entra en estados de bajo poder demasiado agresivamente, provocando "Tx LPI: 19 (us)" y "Tx LPI: 12 (us)". Esto genera una transición de estado PHY que rompe la continuidad del enlace Ethernet, causando la observación de que "traffic silently stalls" y los "packets drop" después de unos minutos de conectividad."`
- Para el Paso 2, respecto a las fallas de la flota: el problema de inestabilidad ataca una categoría de falla de "inestabilidad de enlace por transición agresiva de ahorro de energía / regresión de gestión de energía a nivel PHY" que afecta directamente a DGX Spark en enlaces directos PC↔Spark tras actualizaciones OTA. — `knowledge/references/forum_nvidia_354764_dgx-spark-ethernet-connection-unstable-after-november-2025-update-eee-energy-eff.md:"El proyecto DGX Spark es el receptor directo de la falla de estabilidad de Ethernet y la solución propuesta ataca directamente la regresión de power-management introducida en la OTA 7.3.1. El "pain point" es la interferencia de EEE en la estabilidad del enlace PHY en modo direct PC↔Spark."`
- Para el Paso 2, el mecanismo de servicio systemd para ajustes persistentes de hardware mapea al paradigma de Atlas de configuración persistente de singularidades de hardware a nivel de nodo ("persistent node configuration quirks"). — `knowledge/references/forum_nvidia_354764_dgx-spark-ethernet-connection-unstable-after-november-2025-update-eee-energy-eff.md:"Aunque el documento no menciona Atlas explícitamente, el mecanismo de servicio systemd para "disable-eee" mapea al paradigma de Atlas de "persistent node configuration quirks" (por ejemplo, ajustes de firmware o estado de hardware al arranque)."`
- El veredicto técnico es COS (cosechado), detonando un ítem de backlog en DGX Spark para adoptar/endurecer la corrección en la imagen base; el disparador de reevaluación documentado es verificar si la próxima actualización OTA subsana el problema o si es necesario desactivar/bloquear EEE por defecto en el build de DGX Spark. — `knowledge/references/forum_nvidia_354764_dgx-spark-ethernet-connection-unstable-after-november-2025-update-eee-energy-eff.md:"El disparador de reevaluación es verificar si la próxima OTA subsana el problema o si es necesario blacklistear/desactivar EEE por defecto en la build de DGX Spark."`

## Por qué se sugiere para blackbox en concreto

El patron de deteccion de regresion de red post-OTA por polling se atribuye a 'Liberation Watchdog' ('monitoreo continuo de salud del sistema/regresiones de red'), y el servicio systemd persistente se atribuye a un 'paradigma de Atlas' generico -- ambos mecanismos (systemd + polling de metricas de hardware) son el dominio real de blackbox.

## Procedencia

- Fuente original: https://forums.developer.nvidia.com/t/dgx-spark-ethernet-connection-unstable-after-november-2025-update-eee-energy-efficient-ethernet-workaround/354764
- Dictamen de cosecha, ruta absoluta: `~/projects/Atlas/docs/agent_findings/2026-09-05_cosecha_forum_nvidia_354764_dgx-spark-ethernet-connection-unstable-after-november-2025-update-eee-energy-eff.md`
- Corregido el 2026-09-09 (DGX-503): el dictamen original interrogó estos mecanismos sólo contra
  Atlas/aequitas_os porque la lista de flota de Atlas estaba rota (DGX-502) y no consideraba
  a blackbox en absoluto.

## Lo que esta ficha NO decide

No dice que blackbox deba adoptar nada. No mide si el código fuente es
production-ready, tiene licencia compatible, o pasa los propios gates de este repo -- eso lo
evalúa quien trabaje aquí, si decide que vale la pena mirarlo.
