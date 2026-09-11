---
id: HARVEST-366877-sparkview-gpu-monitor-tool-with-gb10-aware-un
kind: task
title: "Evaluar adopción: mecanismo cosechado por Atlas (366877-sparkview-gpu-monitor-tool-with-gb10-aware-unified-memory-handl)"
status: open
severity: P3
origin: asserted
satd_family: HARVEST_SUGGESTION
close_check: {"cmd": "python -m tools.check_harvest_accepted tasks/backlog/HARVEST-366877-sparkview-gpu-monitor-tool-with-gb10-aware-un.md", "expect": "exit_zero", "porque": "Sugerencia de adopcion, no un defecto -- verifica que accepted.by/date/trigger este lleno y no sea el placeholder, patron de own_chats/tools/check_harvest_accepted.py (DGX-505)."}
created: 2026-09-09
accepted: {"by": "the maintainer + Claude, revision de deuda 2026-09-09", "date": "2026-09-09", "trigger": "revisado a fondo (codigo + fuente citada) y sin valor incremental hoy -- reabrir si aparece un caso real medido en esta maquina que lo contradiga"}
reason: "Es la MISMA fuente que el README ya cita textualmente como origen de PSI (forum_nvidia_366877), ya en la tabla de cherry-pick como 'Adoptado -- la señal que faltaba'. Duplicado exacto, no una variante mejorable."
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

- Paso 3 (Veredicto y disparador de reevaluación): Veredicto `COS` con disparador de reevaluación fijado en la validación en hardware físico GB10/DGX Spark para confirmar la conmutación de memoria y la integridad de las señales PSI en el flujo de trabajo del usuario. — `knowledge/references/forum_nvidia_366877_sparkview-gpu-monitor-tool-with-gb10-aware-unified-memory-handling.md:"El disparador de reevaluación es la validación en hardware físico GB10/DGX Spark para confirmar la conmutación de memoria y la integridad de las señales PSI en el flujo de trabajo del usuario."`

## Por qué se sugiere para blackbox en concreto

El mecanismo 2 (señales PSI de presión de memoria del kernel para detectar HIGH/CRITICAL antes del colapso) se mapeó explícitamente a 'Liberation Watchdog' (falso) 'cumpliendo el rol de watchdog de bajo nivel'; el dominio real de esa función es blackbox.

## Procedencia

- Fuente original: https://forums.developer.nvidia.com/t/sparkview-gpu-monitor-tool-with-gb10-aware-unified-memory-handling/366877
- Dictamen de cosecha, ruta absoluta: `~/projects/Atlas/docs/agent_findings/2026-09-05_cosecha_forum_nvidia_366877_sparkview-gpu-monitor-tool-with-gb10-aware-unified-memory-handling.md`
- Corregido el 2026-09-09 (DGX-503): el dictamen original interrogó estos mecanismos sólo contra
  Atlas/aequitas_os porque la lista de flota de Atlas estaba rota (DGX-502) y no consideraba
  a blackbox en absoluto.

## Lo que esta ficha NO decide

No dice que blackbox deba adoptar nada. No mide si el código fuente es
production-ready, tiene licencia compatible, o pasa los propios gates de este repo -- eso lo
evalúa quien trabaje aquí, si decide que vale la pena mirarlo.
