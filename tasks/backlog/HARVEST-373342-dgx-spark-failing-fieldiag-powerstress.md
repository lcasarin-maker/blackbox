---
id: HARVEST-373342-dgx-spark-failing-fieldiag-powerstress
kind: task
title: "Evaluar adopción: mecanismo cosechado por Atlas (373342-dgx-spark-failing-fieldiag-powerstress)"
status: open
severity: P3
origin: asserted
satd_family: HARVEST_SUGGESTION
close_check: {"cmd": "python -m tools.check_harvest_accepted tasks/backlog/HARVEST-373342-dgx-spark-failing-fieldiag-powerstress.md", "expect": "exit_zero", "porque": "Sugerencia de adopcion, no un defecto -- verifica que accepted.by/date/trigger este lleno y no sea el placeholder, patron de own_chats/tools/check_harvest_accepted.py (DGX-505)."}
created: 2026-09-09
accepted: {"by": "the maintainer + Claude, revision de deuda 2026-09-09", "date": "2026-09-09", "trigger": "revisado a fondo (codigo + fuente citada) y sin valor incremental hoy -- reabrir si aparece un caso real medido en esta maquina que lo contradiga"}
reason: "fieldiag/powerstress ejecuta cargas de estres activas -- benchmarking sintetico, explicitamente excluido del alcance de blackbox aunque sea una herramienta oficial de NVIDIA para este hardware."
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

- PASO 2 (Interrogatorio - Atlas): La rutina `fieldiag` ataca la categoría de falla conocida de diagnóstico remoto y validación de salud de hardware en campo para unidades DGX Spark — `knowledge/references/forum_nvidia_373342_dgx-spark-failing-fieldiag-powerstress.md:"Validación de salud del hardware en campo; enrutamiento de diagnósticos remotos para unidades DGX Spark."`
- PASO 2 (Interrogatorio - DGX Spark): El evento de umbral térmico/potencia ataca la categoría de falla de nivel de unidad física (*unit-level thermal/power fault*), distinguiendo entre sensor defectuoso o superación del límite de diseño térmico — `knowledge/references/forum_nvidia_373342_dgx-spark-failing-fieldiag-powerstress.md:"Fallo de nivel de unidad (unit-level thermal/power fault); distinción entre sensor roto vs. límite de diseño."`
- PASO 2 (Interrogatorio - Cuenza): La paternidad de sostenimiento de carga ataca la categoría de fallo por apagado imprevisto en campo durante inferencia sostenida o finetuning — `knowledge/references/forum_nvidia_373342_dgx-spark-failing-fieldiag-powerstress.md:"Validación de cargas de trabajo financieras/finetuning; asegurar que la inferencia sostenida no desencadene apagados en campo."`
- PASO 3 (Veredicto y Disparador): El veredicto técnico es COS, justificando la creación de un ítem de backlog para bajar código, analizar la implementación del sensor o margen térmico en BIOS/DRV y hacer fork-and-own/harden para distinguir entre límite de diseño y sensor defectuoso — `knowledge/references/forum_nvidia_373342_dgx-spark-failing-fieldiag-powerstress.md:"es necesario bajar código, analizar la implementación del sensor/thermal margin en la BIOS/DRV y adoptar/harden o fork-and-own la unidad defectuosa"`

## Por qué se sugiere para blackbox en concreto

La rutina 'fieldiag/partnerdiag' de diagnóstico remoto de salud de hardware en campo se atribuyó a 'Interrogatorio - Atlas', pero ese mecanismo es literalmente la misión de blackbox ('monitoreo de hardware, logs, systemd units' del mismo GB10), nunca interrogado.

## Procedencia

- Fuente original: https://forums.developer.nvidia.com/t/dgx-spark-failing-fieldiag-powerstress/373342
- Dictamen de cosecha, ruta absoluta: `~/projects/Atlas/docs/agent_findings/2026-09-05_cosecha_forum_nvidia_373342_dgx-spark-failing-fieldiag-powerstress.md`
- Corregido el 2026-09-09 (DGX-503): el dictamen original interrogó estos mecanismos sólo contra
  Atlas/aequitas_os porque la lista de flota de Atlas estaba rota (DGX-502) y no consideraba
  a blackbox en absoluto.

## Lo que esta ficha NO decide

No dice que blackbox deba adoptar nada. No mide si el código fuente es
production-ready, tiene licencia compatible, o pasa los propios gates de este repo -- eso lo
evalúa quien trabaje aquí, si decide que vale la pena mirarlo.
