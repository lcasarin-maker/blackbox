---
id: HARVEST-364166-latest-update-20mar-2026-on-nvidia-spark-fe-c
kind: task
title: "Evaluar adopción: mecanismo cosechado por Atlas (364166-latest-update-20mar-2026-on-nvidia-spark-fe-caps-gpu-performanc)"
status: open
severity: P3
origin: asserted
satd_family: HARVEST_SUGGESTION
close_check: {"cmd": "python -m tools.check_harvest_accepted tasks/backlog/HARVEST-364166-latest-update-20mar-2026-on-nvidia-spark-fe-c.md", "expect": "exit_zero", "porque": "Sugerencia de adopcion, no un defecto -- verifica que accepted.by/date/trigger este lleno y no sea el placeholder, patron de own_chats/tools/check_harvest_accepted.py (DGX-505)."}
created: 2026-09-09
accepted: {"by": "the maintainer + Claude, revision de deuda 2026-09-09", "date": "2026-09-09", "trigger": "adoptado -- el trabajo real vive en tasks/backlog/FEATURE-CLOCK-THROTTLE-CRUZADO.md, no en esta ficha de evaluacion"}
reason: "El mecanismo 2 (clock atascado en 750MHz) es un hueco real: sm_clk_mhz/pstate/throttle se capturan cada 5s pero bb scan nunca los cruza -- solo lee temp_critica del mismo JSONL. El replug fisico (mecanismo 1) es mitigacion y queda fuera. Se consolida en FEATURE-CLOCK-THROTTLE-CRUZADO."
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

- Mecanismo 1 (Rutina de reseteo físico de USB Power Delivery): Consiste en desconectar y reconectar físicamente el conector USB-C y/o el cargador de la toma de corriente para forzar un reinicio del controlador del cargador y renegociar perfiles de alimentación eléctrica tras actualizaciones de firmware — `knowledge/references/forum_nvidia_364166_latest-update-20mar-2026-on-nvidia-spark-fe-caps-gpu-performance.md:"El mecanismo diagnóstico y de mitigación consiste en la desconexión física y reconexión del cable USB-C y/o el cable de alimentación de pared para resetear el controlador del cargador."`
- Mecanismo 3 (Actualización coordinada de sistema operativo, kernel y controlador): Despliegue de actualización a Linux kernel 6.17.0-1014 y driver NVIDIA 580.142 mediante panel de control/dashboard del sistema, que altera la gestión de potencia del GPU GB10 — `knowledge/references/forum_nvidia_364166_latest-update-20mar-2026-on-nvidia-spark-fe-caps-gpu-performance.md:"El trigger del problema es la actualización del sistema a Linux kernel 6.17.0-1014 y driver NVIDIA 580.142, que introdujo un cambio de comportamiento en la gestión de energía (USB PD) que afecta el estado de rendimiento del GPU GB10 en la configuración Founders Edition."`
- Interrogatorio Mecanismo 1 (Paso 2): Ataca la categoría de falla de "degradación silenciosa de potencia / subalimentación de hardware"; a nuestra escala pasa de reseteo manual asistido por operador a una rutina de ciclo de potencia controlado/automático; describe la práctica empírica de "power cycling" o reinicio en frío de subsistemas de alimentación — `knowledge/references/forum_nvidia_364166_latest-update-20mar-2026-on-nvidia-spark-fe-caps-gpu-performance.md:"El mecanismo #1 (reseteo PD) y #2 (monitoreo throttling) son aplicaciones directas del proyecto DGX Spark."`
- Interrogatorio Mecanismo 2 (Paso 2): Ataca la categoría de falla de "estrangulamiento térmico o energético no alertado (silent throttling)"; a escala de nodo o flota opera integrando el script de chequeo liviano como sonda heurística periódica; formaliza la supervisión continua del estado operativo de reloj y telemetría de cómputo bajo un componente de vigilancia — `knowledge/references/forum_nvidia_364166_latest-update-20mar-2026-on-nvidia-spark-fe-caps-gpu-performance.md:"El mecanismo #2 (detección de throttling) se mapea al concepto de "Watchdog" para monitorear la salud y rendimiento del hardware, asegurando que los nodos no se queden operando en estados de baja frecuencia (750MHz) sin alerta."`
- Interrogatorio Mecanismo 3 (Paso 2): Ataca la categoría de falla de "regresión de rendimiento post-actualización de firmware/kernel"; a escala reducida equivale al control de versiones inmutable y canario de drivers en un único nodo; identifica la práctica de gestión de dependencias de bajo nivel del sistema operativo — `knowledge/references/forum_nvidia_364166_latest-update-20mar-2026-on-nvidia-spark-fe-caps-gpu-performance.md:"El mecanismo #3 (ruta de actualización de firmware/kernel) es relevante para Atlas, ya que cualquier pipeline de actualización de modelo o despliegue en hardware Atlas debe considerar esta vía de actualización de sistema operativo y driver como un posible factor de degradación de rendimiento GPU"`
- Veredicto y disparador de reevaluación (Paso 3): Veredicto COS (Cosechado). Su disparador es la necesidad de bajar código/analizar la implementación del reseteo PD y adoptar/harden el script de monitoreo throttle-check en la flota para mitigar el problema sin intervención manual — `knowledge/references/forum_nvidia_364166_latest-update-20mar-2026-on-nvidia-spark-fe-caps-gpu-performance.md:"El disparador es la necesidad de **bajar código/analizar la implementación del reseteo PD y adoptar/harden el script de monitoreo throttle-check** en la flota DGX Spark para automatizar la detección y mitigación de este estado, evitando la necesidad de reinicios manuales por parte del usuario."`

## Por qué se sugiere para blackbox en concreto

El mecanismo 2 (detección de throttling) se interroga textualmente como 'se mapea al concepto de Watchdog para monitorear la salud' y los otros dos al fantasma 'proyecto DGX Spark' -- monitoreo de salud/throttling de hardware GB10 es exactamente el mandato de blackbox, nunca considerado.

## Procedencia

- Fuente original: https://forums.developer.nvidia.com/t/latest-update-20mar-2026-on-nvidia-spark-fe-caps-gpu-performance/364166
- Dictamen de cosecha, ruta absoluta: `~/projects/Atlas/docs/agent_findings/2026-09-05_cosecha_forum_nvidia_364166_latest-update-20mar-2026-on-nvidia-spark-fe-caps-gpu-performance.md`
- Corregido el 2026-09-09 (DGX-503): el dictamen original interrogó estos mecanismos sólo contra
  Atlas/aequitas_os porque la lista de flota de Atlas estaba rota (DGX-502) y no consideraba
  a blackbox en absoluto.

## Lo que esta ficha NO decide

No dice que blackbox deba adoptar nada. No mide si el código fuente es
production-ready, tiene licencia compatible, o pasa los propios gates de este repo -- eso lo
evalúa quien trabaje aquí, si decide que vale la pena mirarlo.
