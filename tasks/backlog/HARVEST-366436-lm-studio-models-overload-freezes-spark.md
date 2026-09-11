---
id: HARVEST-366436-lm-studio-models-overload-freezes-spark
kind: task
title: "Evaluar adopción: mecanismo cosechado por Atlas (366436-lm-studio-models-overload-freezes-spark)"
status: open
severity: P3
origin: asserted
satd_family: HARVEST_SUGGESTION
close_check: {"cmd": "python -m tools.check_harvest_accepted tasks/backlog/HARVEST-366436-lm-studio-models-overload-freezes-spark.md", "expect": "exit_zero", "porque": "Sugerencia de adopcion, no un defecto -- verifica que accepted.by/date/trigger este lleno y no sea el placeholder, patron de own_chats/tools/check_harvest_accepted.py (DGX-505)."}
created: 2026-09-09
accepted: {"by": "the maintainer + Claude, revision de deuda 2026-09-09", "date": "2026-09-09", "trigger": "revisado a fondo (codigo + fuente citada) y sin valor incremental hoy -- reabrir si aparece un caso real medido en esta maquina que lo contradiga"}
reason: "Verificado en codigo: el mecanismo de sparkview (usar MemAvailable cuando NVML miente en memoria unificada) YA esta implementado literalmente como PSI (bin/bb, psi_campo()), misma fuente citada en el README. La vigilancia preventiva que pide el mecanismo 3 es mitigacion activa, dominio de Atlas."
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

- Limitación y carga JIT de un solo modelo: forzar la carga de únicamente un modelo a la vez y usar carga Just-In-Time vía API para maximizar la memoria disponible y prevenir la sobrecarga de VRAM — `knowledge/references/forum_nvidia_366436_lm-studio-models-overload-freezes-spark.md:"Yeah, I'm using JIT model loading right now and use them via API, also force that only one model can be loaded at time…"`
- Monitoreo adaptativo con detección de memoria usable (`sparkview` conmutable a `MemAvailable`): detecta en tiempo de ejecución la discrepancia de NVML en memoria unificada GB10 (donde `nvmlDeviceGetMemoryInfo` reporta ~121 GB pero no considera reservas de kernel ni page cache) y conmuta a `MemAvailable` para reflejar la capacidad asignable real — `knowledge/references/forum_nvidia_366436_lm-studio-models-overload-freezes-spark.md:"sparkview detects this condition at runtime and switches to MemAvailable for memory display."`
- Relación del mecanismo de thrashing de swap con fallas de flota: ataca la categoría de agotamiento de memoria unificada y congelamiento de kernel por contención de almacenamiento en hardware DGX Spark — `knowledge/references/forum_nvidia_366436_lm-studio-models-overload-freezes-spark.md:"El mecanismo de *exhaustión de swap y thrashing del kernel* ataca directamente el problema central reportado en el hilo."`
- Relación de la sobrecarga de memoria con fallas de flota: ataca la categoría de falta de supervisión proactiva de límites de memoria en tiempo real vinculada a Liberation Watchdog — `knowledge/references/forum_nvidia_366436_lm-studio-models-overload-freezes-spark.md:"El mecanismo de *excedente de asignación de VRAM* se relaciona con la necesidad de Watchdogs que monitoreen límites de memoria en tiempo real para prevenir congelamientos del sistema en lugar de solo detectarlos después."`

## Por qué se sugiere para blackbox en concreto

El mecanismo de supervisión proactiva de límites de memoria en tiempo real (thrashing de swap, discrepancia NVML/MemAvailable) se mapeó explícitamente a 'Liberation Watchdog' (nombre falso); el dominio real es monitoreo de hardware/memoria -- blackbox.

## Procedencia

- Fuente original: https://forums.developer.nvidia.com/t/lm-studio-models-overload-freezes-spark/366436
- Dictamen de cosecha, ruta absoluta: `~/projects/Atlas/docs/agent_findings/2026-09-05_cosecha_forum_nvidia_366436_lm-studio-models-overload-freezes-spark.md`
- Corregido el 2026-09-09 (DGX-503): el dictamen original interrogó estos mecanismos sólo contra
  Atlas/aequitas_os porque la lista de flota de Atlas estaba rota (DGX-502) y no consideraba
  a blackbox en absoluto.

## Lo que esta ficha NO decide

No dice que blackbox deba adoptar nada. No mide si el código fuente es
production-ready, tiene licencia compatible, o pasa los propios gates de este repo -- eso lo
evalúa quien trabaje aquí, si decide que vale la pena mirarlo.
