---
id: HARVEST-371753-heat-and-power-numbers-for-asus-gx-10-4-days-
kind: task
title: "Evaluar adopción: mecanismo cosechado por Atlas (371753-heat-and-power-numbers-for-asus-gx-10-4-days-on-90-utilization)"
status: open
severity: P3
origin: asserted
satd_family: HARVEST_SUGGESTION
close_check: {"cmd": "python -m tools.check_harvest_accepted tasks/backlog/HARVEST-371753-heat-and-power-numbers-for-asus-gx-10-4-days-.md", "expect": "exit_zero", "porque": "Sugerencia de adopcion, no un defecto -- verifica que accepted.by/date/trigger este lleno y no sea el placeholder, patron de own_chats/tools/check_harvest_accepted.py (DGX-505)."}
created: 2026-09-09
accepted: {"by": "the maintainer + Claude, revision de deuda 2026-09-09", "date": "2026-09-09", "trigger": "hardware/escenario distinto -- reabrir si ATOM cambia de configuracion (cluster, rack, otro chip)"}
reason: "Configuracion fisica de rack de 4 unidades con conveccion forzada que ATOM (una sola maquina de escritorio) no tiene; la cadencia de telemetria propuesta (3 min) es ademas peor que la ya existente."
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

- PASO 1 (Mecanismos), Mecanismo 1: Muestreo periódico de telemetría térmica y consumo cada tres minutos con persistencia — `knowledge/references/forum_nvidia_371753_heat-and-power-numbers-for-asus-gx-10-4-days-on-90-utilization.md:"Muestreo térmico cada 3 minutos con persistencia en disco"`
- PASO 1 (Mecanismos), Mecanismo 2: Arquitectura de disipación térmica por convección forzada en rack 5U bajo escritorio mediante disposición escalonada y ventilación push/pull — `knowledge/references/forum_nvidia_371753_heat-and-power-numbers-for-asus-gx-10-4-days-on-90-utilization.md:"Arquitectura de flujo de convección forzada en rack 5U"`
- La arquitectura mecánica ubica estante ventilado superior, ventilador de extracción frontal 1U Cloudplate T-6 y ventiladores push/pull 140mm atados a los rieles laterales — `knowledge/references/forum_nvidia_371753_heat-and-power-numbers-for-asus-gx-10-4-days-on-90-utilization.md:"top row is open vented shelf", "second layer is 1U Cloudplate T-6 front exhaust fan", "140mm Be Quiet Silent Pure 3 push/pull usando cable ties a side rails"`
- Los nodos se distribuyen escalonados de izquierda a derecha y de frente a fondo para dirigir la columna de convección hacia el extractor — `knowledge/references/forum_nvidia_371753_heat-and-power-numbers-for-asus-gx-10-4-days-on-90-utilization.md:"Staggering the GX10s left/right and front/back to push the convection column straight up into the T-6 exhaust"`
- PASO 1 (Mecanismos), Mecanismo 3: Estabilidad de frecuencia y mitigación de estrangulamiento térmico y caídas de energía por firmware ante eventos de agotamiento de memoria bajo utilización del 90%+ — `knowledge/references/forum_nvidia_371753_heat-and-power-numbers-for-asus-gx-10-4-days-on-90-utilization.md:"Estabilidad de frecuencia bajo carga sostenida (90% util)"`
- PASO 2 (Interrogatorio), Mecanismo 1: Ataca la categoría de falla conocida de degradación térmica acumulativa y estrangulamiento térmico de nodos en el sistema de telemetría de Atlas — `knowledge/references/forum_nvidia_371753_heat-and-power-numbers-for-asus-gx-10-4-days-on-90-utilization.md:"Este mecanismo es crítico para la detección temprana de degradación de componentes y la gestión de la residencia de trabajos en el clúster, evitando que los nodos entren en umbrales de calor crítico durante ejecuciones prolongadas."`
- PASO 2 (Interrogatorio), Mecanismo 2: Aplica a la optimización de flujo de aire para racks compactos transposables a Cuencia, atacando la acumulación de calor por convección confinada en espacios físicos reducidos — `knowledge/references/forum_nvidia_371753_heat-and-power-numbers-for-asus-gx-10-4-days-on-90-utilization.md:"el patrón de diseño de flujo de aire es transposable a las soluciones de rack de Cuencia para validar diseños de convección natural forzada en entornos de FinTech con restricciones de espacio físico."`
- PASO 2 (Interrogatorio), Mecanismo 3: Se mapea a DGX Spark atacando la degradación de rendimiento / estrangulamiento térmico en ejecuciones continuas y validando perfiles energéticos en nodos satélite aislados — `knowledge/references/forum_nvidia_371753_heat-and-power-numbers-for-asus-gx-10-4-days-on-90-utilization.md:"Valida que la arquitectura de potencia de estos "satélites" puede sostener cargas de inferencia/training intensivas sin throttling térmico, un dato clave para la ingeniería de firmware y configuraciones de VRAM en nodos isolados."`

## Por qué se sugiere para blackbox en concreto

El Mecanismo 1 -- muestreo periodico de telemetria termica/consumo cada 3 min con persistencia en disco -- se mapea a 'el sistema de telemetria de Atlas', pero ese es exactamente el dominio declarado de blackbox ('Caja negra / telemetria de la AI TOP ATOM: monitoreo de hardware, logs, systemd units'), un ajuste de dominio mucho mas directo que el RAG de Atlas.

## Procedencia

- Fuente original: https://forums.developer.nvidia.com/t/heat-and-power-numbers-for-asus-gx-10-4-days-on-90-utilization/371753
- Dictamen de cosecha, ruta absoluta: `~/projects/Atlas/docs/agent_findings/2026-09-05_cosecha_forum_nvidia_371753_heat-and-power-numbers-for-asus-gx-10-4-days-on-90-utilization.md`
- Corregido el 2026-09-09 (DGX-503): el dictamen original interrogó estos mecanismos sólo contra
  Atlas/aequitas_os porque la lista de flota de Atlas estaba rota (DGX-502) y no consideraba
  a blackbox en absoluto.

## Lo que esta ficha NO decide

No dice que blackbox deba adoptar nada. No mide si el código fuente es
production-ready, tiene licencia compatible, o pasa los propios gates de este repo -- eso lo
evalúa quien trabaje aquí, si decide que vale la pena mirarlo.
