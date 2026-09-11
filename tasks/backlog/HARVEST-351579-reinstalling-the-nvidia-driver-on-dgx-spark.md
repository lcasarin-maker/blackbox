---
id: HARVEST-351579-reinstalling-the-nvidia-driver-on-dgx-spark
kind: task
title: "Evaluar adopción: mecanismo cosechado por Atlas (351579-reinstalling-the-nvidia-driver-on-dgx-spark)"
status: open
severity: P3
origin: asserted
satd_family: HARVEST_SUGGESTION
close_check: {"cmd": "python -m tools.check_harvest_accepted tasks/backlog/HARVEST-351579-reinstalling-the-nvidia-driver-on-dgx-spark.md", "expect": "exit_zero", "porque": "Sugerencia de adopcion, no un defecto -- verifica que accepted.by/date/trigger este lleno y no sea el placeholder, patron de own_chats/tools/check_harvest_accepted.py (DGX-505)."}
created: 2026-09-09
accepted: {"by": "the maintainer + Claude, revision de deuda 2026-09-09", "date": "2026-09-09", "trigger": "adoptado -- el trabajo real vive en tasks/backlog/FEATURE-NVIDIA-CONTAINER-RUNTIME-HOOK.md, no en esta ficha de evaluacion"}
reason: "El fallo del prestart hook OCI/nvidia-container-runtime (fallback silencioso a modo legacy) es una firma nueva, ausente del catalogo de bb scan. El gateway ya corre en Docker (mecanismo adoptado). Se consolida en FEATURE-NVIDIA-CONTAINER-RUNTIME-HOOK."
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

- Mecanismo 3 (Paso 1): Ejecución del hook de contenedor en runtime OCI (`prestart hook #0`) con fallback a modo legacy ante la falta de carga del driver NVML — `knowledge/references/forum_nvidia_351579_reinstalling-the-nvidia-driver-on-dgx-spark.md:"error running prestart hook #0: exit status 1, stdout: , stderr: Auto-detected mode as 'legacy'"`
- Mecanismo 4 (Paso 1): Generación y recolección de diagnósticos y registros del sistema mediante script automatizado para soporte — `knowledge/references/forum_nvidia_351579_reinstalling-the-nvidia-driver-on-dgx-spark.md:"sudo nvidia-bug-report.sh"`
- Interrogatorio (Paso 2): El mecanismo de hook de inicio de contenedor ataca la categoría de falla de fallo de inicialización de runtime de contenedor por driver de GPU no cargado o no firmado bajo arranque seguro — `knowledge/references/forum_nvidia_351579_reinstalling-the-nvidia-driver-on-dgx-spark.md:"El fallo de init de contenedor debido a incoherencia de driver. Aunque el hilo es DGX Spark, el síntoma (driver no cargado para contenedor) es un caso de uso típico para Liberation Watchdog"`

## Por qué se sugiere para blackbox en concreto

'el síntoma (driver no cargado para contenedor) es un caso de uso típico para Liberation Watchdog' -- detección de fallo de driver/hardware vía hooks OCI y logs de diagnóstico (nvidia-bug-report.sh) es monitoreo de hardware/systemd, dominio explícito de blackbox, miembro real nunca considerado por la lista rota.

## Procedencia

- Fuente original: https://forums.developer.nvidia.com/t/reinstalling-the-nvidia-driver-on-dgx-spark/351579
- Dictamen de cosecha, ruta absoluta: `~/projects/Atlas/docs/agent_findings/2026-09-05_cosecha_forum_nvidia_351579_reinstalling-the-nvidia-driver-on-dgx-spark.md`
- Corregido el 2026-09-09 (DGX-503): el dictamen original interrogó estos mecanismos sólo contra
  Atlas/aequitas_os porque la lista de flota de Atlas estaba rota (DGX-502) y no consideraba
  a blackbox en absoluto.

## Lo que esta ficha NO decide

No dice que blackbox deba adoptar nada. No mide si el código fuente es
production-ready, tiene licencia compatible, o pasa los propios gates de este repo -- eso lo
evalúa quien trabaje aquí, si decide que vale la pena mirarlo.
