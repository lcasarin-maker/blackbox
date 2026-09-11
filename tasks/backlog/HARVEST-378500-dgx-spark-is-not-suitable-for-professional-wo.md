---
id: HARVEST-378500-dgx-spark-is-not-suitable-for-professional-wo
kind: task
title: "Evaluar adopción: mecanismo cosechado por Atlas (378500-dgx-spark-is-not-suitable-for-professional-workloads-due-to-the)"
status: open
severity: P3
origin: asserted
satd_family: HARVEST_SUGGESTION
close_check: {"cmd": "python -m tools.check_harvest_accepted tasks/backlog/HARVEST-378500-dgx-spark-is-not-suitable-for-professional-wo.md", "expect": "exit_zero", "porque": "Sugerencia de adopcion, no un defecto -- verifica que accepted.by/date/trigger este lleno y no sea el placeholder, patron de own_chats/tools/check_harvest_accepted.py (DGX-505)."}
created: 2026-09-09
accepted: {"by": "the maintainer + Claude, revision de deuda 2026-09-09", "date": "2026-09-09", "trigger": "revisado a fondo (codigo + fuente citada) y sin valor incremental hoy -- reabrir si aparece un caso real medido en esta maquina que lo contradiga"}
reason: "Verificado en codigo: el cuello de botella de ancho de banda de memoria ya esta atacado por el mecanismo de tok/s de trafico real (bin/bb, seccion motor de inferencia). Recuperacion tras corte de energia y checkpointing son arquitectura de aplicacion, fuera de alcance de un instrumento de monitoreo."
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

- Mecanismo 3 (Cuello de botella de ancho de banda en inferencia): la tasa de generación de tokens está limitada por el bus de memoria (LPDDR5X) y no por el cálculo puro de GPU — `knowledge/references/forum_nvidia_378500_dgx-spark-is-not-suitable-for-professional-workloads-due-to-thermal-instability-.md:"aunque el hardware GPU es capaz, el rendimiento real de inferencia se ve limitado por el ancho de banda de memoria. Esto no es un fallo de hardware catastrófico, sino un cuello de botella de arquitectura que impide que el hardware alcance sus especificaciones de throughput"`
- Paso 2 aplicado a Mecanismo 1: en la flota de operación desatendida 24/7 (Nomad Offline / Liberation Watchdog), ataca la categoría de falla de interrupción de disponibilidad por apagado irrecuperable sin reinicio remoto — `knowledge/references/forum_nvidia_378500_dgx-spark-is-not-suitable-for-professional-workloads-due-to-thermal-instability-.md:"la incapacidad para recuperar automáticamente el estado después de un corte de energía térmico impide su uso como servidor de inferencia o nodo de entrenamiento descentralizado (Liberation Watchdog/Nomad Offline) donde se espera operación 24/7 sin supervisión humana."`
- Paso 2 aplicado a Mecanismo 2: ataca la categoría de falla de corrupción de estado por corte abrupto de energía, requiriendo mecanismos de degradación suave y puntos de control a nivel de software — `knowledge/references/forum_nvidia_378500_dgx-spark-is-not-suitable-for-professional-workloads-due-to-thermal-instability-.md:"Para el ecosistema, esto se traduce en la necesidad de implementar estrategias de *graceful degradation* o *workload checkpointing* a nivel de software para mitigar el fallo de hardware, ya que el dispositivo no transiciona a modo de protección suave antes del corte."`
- Paso 2 aplicado a Mecanismo 3: ataca la categoría de falla de degradación de latencia y throughput bajo presión de contexto en pipelines RAG (Atlas) — `knowledge/references/forum_nvidia_378500_dgx-spark-is-not-suitable-for-professional-workloads-due-to-thermal-instability-.md:"En proyectos que utilizan Atlas para pipelines RAG o inferencia densa, este limite obliga a reconfigurar los modelos o ajustar los parámetros de batch size para compensar la falta de throughput esperado del hardware GB10/Grace."`

## Por qué se sugiere para blackbox en concreto

El Mecanismo 1 (detección de apagado irrecuperable/falta de reinicio remoto tras corte térmico en operación 24/7) se mapea explícitamente a 'Nomad Offline / Liberation Watchdog', nombres falsos; ese mecanismo de detección/alerta de fallos de hardware es dominio de blackbox, que monitorea exactamente esa máquina (GB10/AI TOP ATOM).

## Procedencia

- Fuente original: https://forums.developer.nvidia.com/t/dgx-spark-is-not-suitable-for-professional-workloads-due-to-thermal-instability-and-missing-enterprise-features/378500
- Dictamen de cosecha, ruta absoluta: `~/projects/Atlas/docs/agent_findings/2026-09-05_cosecha_forum_nvidia_378500_dgx-spark-is-not-suitable-for-professional-workloads-due-to-thermal-instability-.md`
- Corregido el 2026-09-09 (DGX-503): el dictamen original interrogó estos mecanismos sólo contra
  Atlas/aequitas_os porque la lista de flota de Atlas estaba rota (DGX-502) y no consideraba
  a blackbox en absoluto.

## Lo que esta ficha NO decide

No dice que blackbox deba adoptar nada. No mide si el código fuente es
production-ready, tiene licencia compatible, o pasa los propios gates de este repo -- eso lo
evalúa quien trabaje aquí, si decide que vale la pena mirarlo.
