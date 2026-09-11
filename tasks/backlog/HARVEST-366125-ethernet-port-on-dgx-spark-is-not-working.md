---
id: HARVEST-366125-ethernet-port-on-dgx-spark-is-not-working
kind: task
title: "Evaluar adopción: mecanismo cosechado por Atlas (366125-ethernet-port-on-dgx-spark-is-not-working)"
status: open
severity: P3
origin: asserted
satd_family: HARVEST_SUGGESTION
close_check: {"cmd": "python -m tools.check_harvest_accepted tasks/backlog/HARVEST-366125-ethernet-port-on-dgx-spark-is-not-working.md", "expect": "exit_zero", "porque": "Sugerencia de adopcion, no un defecto -- verifica que accepted.by/date/trigger este lleno y no sea el placeholder, patron de own_chats/tools/check_harvest_accepted.py (DGX-505)."}
created: 2026-09-09
accepted: {"by": "the maintainer + Claude, revision de deuda 2026-09-09", "date": "2026-09-09", "trigger": "adoptado -- el trabajo real vive en tasks/done/FEATURE-RED-CPU-SCAN.md, no en esta ficha de evaluacion"}
reason: "ethtool para estado de enlace, conteo de vectores MSI-X en /proc/interrupts, y validacion de VPD/EEPROM son tecnicas concretas y baratas ausentes hoy. Consolidada como trabajo de red pendiente en FEATURE-RED-CPU-SCAN (la primera pasada de ese ticket solo activo el analisis de contadores ya capturados; ethtool/MSI-X/VPD quedan como extension declarada en el mismo ticket)."
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

- El primer mecanismo es la extracción de reportes forenses y análisis del estado del enlace mediante herramientas del sistema (`nvidia-bug-report` y `ethtool enP7s7`), lo que permite obtener parámetros de negociación, velocidad y presencia de señal física — `knowledge/references/forum_nvidia_366125_ethernet-port-on-dgx-spark-is-not-working.md:7`
- El segundo mecanismo es el diagnóstico de interrupciones de hardware mediante el conteo de vectores MSI-X, verificando si el dispositivo genera actividad tras la inicialización del driver — `knowledge/references/forum_nvidia_366125_ethernet-port-on-dgx-spark-is-not-working.md:9`
- El tercer mecanismo es la validación de registros VPD y EEPROM en el driver de red para comprobar la integridad de datos de firmware/hardware requeridos — `knowledge/references/forum_nvidia_366125_ethernet-port-on-dgx-spark-is-not-working.md:11`
- Para el mecanismo de inspección por `ethtool` y logs de diagnóstico: ataca la categoría de falla de desconexión física no detectada o fallo de negociación de enlace (enlace en NO-CARRIER pese a driver activo); a nuestra escala se traduce de un diagnóstico manual a scripts o sondas locales de inspección periódica de estado de interfaces; y formaliza diagnósticos de conectividad que se ejecutan ad-hoc — `knowledge/references/forum_nvidia_366125_ethernet-port-on-dgx-spark-is-not-working.md:7-17`
- Para el mecanismo de conteo de vectores MSI-X: ataca la categoría de falla de fallo silencioso de inicialización de hardware (el driver carga pero el dispositivo queda inerte sin despachar interrupciones); a nuestra escala se mapea de inspección manual de `/proc/interrupts` a heurísticas del watchdog local que alertan si un periférico inicializado mantiene sus contadores en cero; y nombra la verificación de vida útil de interrupciones que antes no se cuantificaba — `knowledge/references/forum_nvidia_366125_ethernet-port-on-dgx-spark-is-not-working.md:9-19`
- Para el mecanismo de validación de VPD y EEPROM: ataca la categoría de falla de corrupción o discrepancia de firmware/configuración de hardware base; a nuestra escala pasa de análisis forense post-mortem en logs a validaciones de arranque (sanity checks al inicializar el nodo); y nombra la inspección de flags de integridad de hardware que se asumían implícitamente correctos — `knowledge/references/forum_nvidia_366125_ethernet-port-on-dgx-spark-is-not-working.md:11-15`
- El documento clasifica formalmente la fuente con un veredicto de producto cosechable por documentar el patrón forense de diagnóstico ante fallos de hardware localizados en unidades específicas — `knowledge/references/forum_nvidia_366125_ethernet-port-on-dgx-spark-is-not-working.md:23`
- El disparador de reevaluación declarado para este veredicto es la revisión de firmware/BIOS o el reemplazo de EEPROM para la unidad afectada — `knowledge/references/forum_nvidia_366125_ethernet-port-on-dgx-spark-is-not-working.md:26`

## Por qué se sugiere para blackbox en concreto

Los tres mecanismos (ethtool/nvidia-bug-report, conteo de vectores MSI-X, validación VPD/EEPROM) son diagnóstico forense y heurísticas de watchdog de hardware -- dominio exacto de blackbox ('monitoreo de hardware, logs'); el dictamen sólo consideró la lista rota (DGX Spark/Atlas/Liberation Watchdog) en 'lo que no se pudo determinar' y nunca a blackbox.

## Procedencia

- Fuente original: https://forums.developer.nvidia.com/t/ethernet-port-on-dgx-spark-is-not-working/366125
- Dictamen de cosecha, ruta absoluta: `~/projects/Atlas/docs/agent_findings/2026-09-05_cosecha_forum_nvidia_366125_ethernet-port-on-dgx-spark-is-not-working.md`
- Corregido el 2026-09-09 (DGX-503): el dictamen original interrogó estos mecanismos sólo contra
  Atlas/aequitas_os porque la lista de flota de Atlas estaba rota (DGX-502) y no consideraba
  a blackbox en absoluto.

## Lo que esta ficha NO decide

No dice que blackbox deba adoptar nada. No mide si el código fuente es
production-ready, tiene licencia compatible, o pasa los propios gates de este repo -- eso lo
evalúa quien trabaje aquí, si decide que vale la pena mirarlo.
