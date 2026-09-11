---
id: HARVEST-377044-dgx-spark-gb10-thermal-throttling-after-ec-ue
kind: task
title: "Evaluar adopción: mecanismo cosechado por Atlas (377044-dgx-spark-gb10-thermal-throttling-after-ec-uefi-updates-acpi-zo)"
status: open
severity: P3
origin: asserted
satd_family: HARVEST_SUGGESTION
close_check: {"cmd": "python -m tools.check_harvest_accepted tasks/backlog/HARVEST-377044-dgx-spark-gb10-thermal-throttling-after-ec-ue.md", "expect": "exit_zero", "porque": "Sugerencia de adopcion, no un defecto -- verifica que accepted.by/date/trigger este lleno y no sea el placeholder, patron de own_chats/tools/check_harvest_accepted.py (DGX-505)."}
created: 2026-09-09
accepted: {"by": "the maintainer + Claude, revision de deuda 2026-09-09", "date": "2026-09-09", "trigger": "revisado a fondo (codigo + fuente citada) y sin valor incremental hoy -- reabrir si aparece un caso real medido en esta maquina que lo contradiga"}
reason: "dgx-spark-fieldiag ejecuta cargas de estres activas -- aunque sea un paquete oficial de NVIDIA para este hardware exacto, no es observacion pasiva; queda fuera por el mismo criterio que otras fichas de benchmarking. La fan curve del EC no tiene interfaz expuesta al SO, no instrumentable."
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

- Mecanismo 1 (Paso 1): Monitoreo térmico de bajo nivel mediante extracción de zonas ACPI y comparación numérica en milidegrados — `knowledge/references/forum_nvidia_377044_dgx-spark-gb10-thermal-throttling-after-ec-uefi-updates-acpi-zones-96-97c-fans-n.md:7`
- Mecanismo 2 (Paso 1): Control de curva de ventilación encapsulado en Embedded Controller (EC) sin interfaz de control expuesta al SO invitado — `knowledge/references/forum_nvidia_377044_dgx-spark-gb10-thermal-throttling-after-ec-uefi-updates-acpi-zones-96-97c-fans-n.md:9`
- Mecanismo 3 (Paso 1): Diagnóstico oficial de campo mediante paquete `dgx-spark-fieldiag` acoplado al repositorio CUDA APT — `knowledge/references/forum_nvidia_377044_dgx-spark-gb10-thermal-throttling-after-ec-uefi-updates-acpi-zones-96-97c-fans-n.md:11`
- Interrogatorio Mecanismo 1 (Paso 2): El documento mapea este mecanismo a la validación estructurada de límites de temperatura y umbrales ACPI en pipelines de Cuenza — `knowledge/references/forum_nvidia_377044_dgx-spark-gb10-thermal-throttling-after-ec-uefi-updates-acpi-zones-96-97c-fans-n.md:15`
- Interrogatorio Mecanismo 2 (Paso 2): La falla técnica que ataca es la degradación térmica por falta de respuesta activa en ventilación, relacionada a la categoría de sobrecalentamiento no mitigado por firmware en DGX Spark — `knowledge/references/forum_nvidia_377044_dgx-spark-gb10-thermal-throttling-after-ec-uefi-updates-acpi-zones-96-97c-fans-n.md:17`
- Interrogatorio Mecanismo 3 (Paso 2): Falla relacionada con la categoría de fallo por dependencias rotas en repositorios de empaquetado del sistema — `knowledge/references/forum_nvidia_377044_dgx-spark-gb10-thermal-throttling-after-ec-uefi-updates-acpi-zones-96-97c-fans-n.md:11`
- Veredicto y cosecha (Paso 3): Veredicto clasificado como `INF` con downscaling requerido de políticas diseñadas para hardware masivo a un solo nodo local — `knowledge/references/forum_nvidia_377044_dgx-spark-gb10-thermal-throttling-after-ec-uefi-updates-acpi-zones-96-97c-fans-n.md:23-25`
- Disparador de reevaluación (Paso 3): Validar versión de firmware EC actual contra el mínimo reportado e intentar downgrade vía LVFS/UEFI o ajustar parámetros térmicos en `nvidia-smi` — `knowledge/references/forum_nvidia_377044_dgx-spark-gb10-thermal-throttling-after-ec-uefi-updates-acpi-zones-96-97c-fans-n.md:27`

## Por qué se sugiere para blackbox en concreto

El interrogatorio mapea la validación de umbrales térmicos ACPI y el diagnóstico oficial `dgx-spark-fieldiag` a 'pipelines de Cuenza' (app financiera), cuando ese mecanismo de monitoreo térmico/EC/ACPI de la GB10 encaja directamente en blackbox ('Caja negra / telemetría de la AI TOP ATOM: monitoreo de hardware, logs, systemd units').

## Procedencia

- Fuente original: https://forums.developer.nvidia.com/t/dgx-spark-gb10-thermal-throttling-after-ec-uefi-updates-acpi-zones-96-97c-fans-not-ramping/377044
- Dictamen de cosecha, ruta absoluta: `~/projects/Atlas/docs/agent_findings/2026-09-05_cosecha_forum_nvidia_377044_dgx-spark-gb10-thermal-throttling-after-ec-uefi-updates-acpi-zones-96-97c-fans-n.md`
- Corregido el 2026-09-09 (DGX-503): el dictamen original interrogó estos mecanismos sólo contra
  Atlas/aequitas_os porque la lista de flota de Atlas estaba rota (DGX-502) y no consideraba
  a blackbox en absoluto.

## Lo que esta ficha NO decide

No dice que blackbox deba adoptar nada. No mide si el código fuente es
production-ready, tiene licencia compatible, o pasa los propios gates de este repo -- eso lo
evalúa quien trabaje aquí, si decide que vale la pena mirarlo.
