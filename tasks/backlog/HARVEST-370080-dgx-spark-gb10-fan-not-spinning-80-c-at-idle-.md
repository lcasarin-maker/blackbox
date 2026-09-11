---
id: HARVEST-370080-dgx-spark-gb10-fan-not-spinning-80-c-at-idle-
kind: task
title: "Evaluar adopción: mecanismo cosechado por Atlas (370080-dgx-spark-gb10-fan-not-spinning-80-c-at-idle-with-0-gpu-utiliza)"
status: open
severity: P3
origin: asserted
satd_family: HARVEST_SUGGESTION
close_check: {"cmd": "python -m tools.check_harvest_accepted tasks/backlog/HARVEST-370080-dgx-spark-gb10-fan-not-spinning-80-c-at-idle-.md", "expect": "exit_zero", "porque": "Sugerencia de adopcion, no un defecto -- verifica que accepted.by/date/trigger este lleno y no sea el placeholder, patron de own_chats/tools/check_harvest_accepted.py (DGX-505)."}
created: 2026-09-09
accepted: {"by": "the maintainer + Claude, revision de deuda 2026-09-09", "date": "2026-09-09", "trigger": "adoptado -- el trabajo real vive en tasks/backlog/FEATURE-FAN-RPM.md, no en esta ficha de evaluacion"}
reason: "El CSV cada 5s que pide la ficha es peor cadencia que la ya existente (atom_gpu_telemetry.py), pero el RPM de ventilador tiene 0% de cobertura en TODO el inventario actual -- ausencia real, no redundancia. Se consolida en FEATURE-FAN-RPM."
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

- PASO 2 - Interrogatorio del Mecanismo 2: Ataca la categoría de falla de degradación de observabilidad en herramientas estándar de gestión; su escala se traduce en lidiar con APIs ciegas forzando diagnósticos externos de campo; y nombra la limitación de diagnósticos oficiales que fallan o crashean ante sobrecalentamiento extremo. — `knowledge/references/forum_nvidia_370080_dgx-spark-gb10-fan-not-spinning-80-c-at-idle-with-0-gpu-utilization.md:"El sistema RAG falla al extraer señales útiles de los datos de usuario cuando la herramienta de diagnóstico oficial crashea, requiriendo parsing manual de CSVs no estructurados."`
- PASO 3 - Veredicto y Disparador: Calificado como INF debido a que la gestión de ventilación encapsulada requiere adaptar las lógicas de monitoreo térmico y energía al entorno de 1 nodo/local; el disparador de reevaluación es la necesidad de reescalar los umbrales térmicos y las curvas de ventilación para operar bajo las limitaciones físicas del hardware GB10 local. — `knowledge/references/forum_nvidia_370080_dgx-spark-gb10-fan-not-spinning-80-c-at-idle-with-0-gpu-utilization.md:"El disparador es la necesidad de reescalar los umbrales térmicos y las curvas de ventilación para operar dentro de las limitaciones del hardwareDGX Spark/Spark GB10 en lugar de esperar comportamientos de centro de datos distribuidos."`

## Por qué se sugiere para blackbox en concreto

El dictamen interroga genéricamente contra 'nuestro sistema RAG' sin considerar ningún satélite; el Mecanismo 3 describe logging de telemetría CSV a intervalos de 5s (memoria, temp acpitz, temp GPU, potencia, utilización) para detectar anomalías térmicas en reposo -- exactamente el dominio declarado de blackbox ('monitoreo de hardware, logs'), a su escala nativa de un solo nodo (no requiere downscaling de distribuido, por lo que el veredicto sube de INF a COS).

## Procedencia

- Fuente original: https://forums.developer.nvidia.com/t/dgx-spark-gb10-fan-not-spinning-80-c-at-idle-with-0-gpu-utilization/370080
- Dictamen de cosecha, ruta absoluta: `~/projects/Atlas/docs/agent_findings/2026-09-05_cosecha_forum_nvidia_370080_dgx-spark-gb10-fan-not-spinning-80-c-at-idle-with-0-gpu-utilization.md`
- Corregido el 2026-09-09 (DGX-503): el dictamen original interrogó estos mecanismos sólo contra
  Atlas/aequitas_os porque la lista de flota de Atlas estaba rota (DGX-502) y no consideraba
  a blackbox en absoluto.

## Lo que esta ficha NO decide

No dice que blackbox deba adoptar nada. No mide si el código fuente es
production-ready, tiene licencia compatible, o pasa los propios gates de este repo -- eso lo
evalúa quien trabaje aquí, si decide que vale la pena mirarlo.
