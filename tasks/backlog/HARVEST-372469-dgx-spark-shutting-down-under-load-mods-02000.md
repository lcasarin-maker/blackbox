---
id: HARVEST-372469-dgx-spark-shutting-down-under-load-mods-02000
kind: task
title: "Evaluar adopción: mecanismo cosechado por Atlas (372469-dgx-spark-shutting-down-under-load-mods-020000600139)"
status: open
severity: P3
origin: asserted
satd_family: HARVEST_SUGGESTION
close_check: {"cmd": "python -m tools.check_harvest_accepted tasks/backlog/HARVEST-372469-dgx-spark-shutting-down-under-load-mods-02000.md", "expect": "exit_zero", "porque": "Sugerencia de adopcion, no un defecto -- verifica que accepted.by/date/trigger este lleno y no sea el placeholder, patron de own_chats/tools/check_harvest_accepted.py (DGX-505)."}
created: 2026-09-09
accepted: {"by": "the maintainer + Claude, revision de deuda 2026-09-09", "date": "2026-09-09", "trigger": "revisado a fondo (codigo + fuente citada) y sin valor incremental hoy -- reabrir si aparece un caso real medido en esta maquina que lo contradiga"}
reason: "El 'diagnostico de campo' (MODS) es una prueba de estres activa -- benchmarking sintetico, explicitamente excluido. El chasis 3D-impreso es modificacion fisica de hardware. El capping de frecuencia ya esta aplicado como limite registrado (-lgc)."
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

- Mecanismo 1 (Paso 1): Diagnóstico de campo mediante prueba de estrés de energía (`MODS-020000600139`), diseñado para validar a bajo nivel la integridad de hardware y firmware bajo demanda — `knowledge/references/forum_nvidia_372469_dgx-spark-shutting-down-under-load-mods-020000600139.md:"El sistema falla específicamente en la prueba de estrés de campo con el código de error MODS-020000600139"`
- Mecanismo 3 (Paso 1): Refrigeración externa mediante flujo forzado (disipadores y ventilador externo en chasis impreso en 3D) para mantener temperaturas estables en el rango de 70-80°C — `knowledge/references/forum_nvidia_372469_dgx-spark-shutting-down-under-load-mods-020000600139.md:"I 3d printed a enclosure for my dual sparks that mounts them upright and has a usb 120mm fan blowing down on them."`
- Interrogatorio (Paso 2): El fallo en la prueba de estrés y los apagones bajo carga atacan la categoría de inestabilidad de hardware y firmware bajo carga en DGX Spark — `knowledge/references/forum_nvidia_372469_dgx-spark-shutting-down-under-load-mods-020000600139.md:"Esto impacta directamente la validación de hardware y la fiabilidad del dispositivo en el proyecto DGX Spark."`
- Interrogatorio (Paso 2): Los mecanismos de límite de frecuencia y supervisión de estado de energía atacan la categoría de degradación de estabilidad por gestión de recursos en Atlas — `knowledge/references/forum_nvidia_372469_dgx-spark-shutting-down-under-load-mods-020000600139.md:"Los mecanismos de *capping* de frecuencia y monitoreo de estados de energía son paralelos al enrutamiento y gestión de recursos de Atlas."`

## Por qué se sugiere para blackbox en concreto

El Mecanismo 1 (diagnostico de campo MODS-020000600139, prueba de estres de energia) se atribuye a 'el proyecto DGX Spark' (nombre falso) para 'validacion de hardware y fiabilidad del dispositivo', pero ese es exactamente el dominio declarado de blackbox (telemetria/monitoreo de hardware de la AI TOP ATOM, mismo chip GB10).

## Procedencia

- Fuente original: https://forums.developer.nvidia.com/t/dgx-spark-shutting-down-under-load-mods-020000600139/372469
- Dictamen de cosecha, ruta absoluta: `~/projects/Atlas/docs/agent_findings/2026-09-05_cosecha_forum_nvidia_372469_dgx-spark-shutting-down-under-load-mods-020000600139.md`
- Corregido el 2026-09-09 (DGX-503): el dictamen original interrogó estos mecanismos sólo contra
  Atlas/aequitas_os porque la lista de flota de Atlas estaba rota (DGX-502) y no consideraba
  a blackbox en absoluto.

## Lo que esta ficha NO decide

No dice que blackbox deba adoptar nada. No mide si el código fuente es
production-ready, tiene licencia compatible, o pasa los propios gates de este repo -- eso lo
evalúa quien trabaje aquí, si decide que vale la pena mirarlo.
