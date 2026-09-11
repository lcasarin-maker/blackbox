---
id: HARVEST-372642-my-spark-is-overheating-when-clustered-and-ru
kind: task
title: "Evaluar adopción: mecanismo cosechado por Atlas (372642-my-spark-is-overheating-when-clustered-and-running-a-model-acro)"
status: open
severity: P3
origin: asserted
satd_family: HARVEST_SUGGESTION
close_check: {"cmd": "python -m tools.check_harvest_accepted tasks/backlog/HARVEST-372642-my-spark-is-overheating-when-clustered-and-ru.md", "expect": "exit_zero", "porque": "Sugerencia de adopcion, no un defecto -- verifica que accepted.by/date/trigger este lleno y no sea el placeholder, patron de own_chats/tools/check_harvest_accepted.py (DGX-505)."}
created: 2026-09-09
accepted: {"by": "the maintainer + Claude, revision de deuda 2026-09-09", "date": "2026-09-09", "trigger": "hardware/escenario distinto -- reabrir si ATOM cambia de configuracion (cluster, rack, otro chip)"}
reason: "Escenario explicitamente de clustering multi-nodo. El throttling termico que menciona ya lo cubre atom_gpu_telemetry.py (campos throttle/temp); 'fieldiag' es diagnostico activo tipo stress-test, tambien excluido."
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

- El segundo mecanismo es el thermal throttling y monitoreo de temperatura: qué hace (restringe la frecuencia/desempeño o apaga la unidad al alcanzar temperaturas críticas), cómo (respuesta automática del hardware/firmware ante inferencia continua por más de 4 horas en clúster) y por qué (proteger la integridad física de los chips frente a sobrecalentamiento sostenido). En el interrogatorio, ataca la categoría de falla conocida de degradación de rendimiento por estrés térmico prolongado; a nuestra escala corresponde a políticas locales de limitación de frecuencia de reloj (clock speed) a nivel de proceso o nodo individual; y nombra formalmente lo que hacemos sin nombre como limitación preventiva de potencia/reloj ante cargas de inferencia pesada. — `knowledge/references/forum_nvidia_372642_my-spark-is-overheating-when-clustered-and-running-a-model-across-both-fieldiag-.md:"- **Throttling térmico y monitoreo de temperatura**: El usuario reporta que el Spark se sobrecalienta durante inference por >4h en cluster. El mecanismo de throttling es la respuesta automática del sistema a temperaturas críticas, observable en la caída de rendimiento o apagados."`
- El veredicto técnico es COS, con justificación en el punto de fallo de microcódigo/firmware y disparador de reevaluación basado en la correlación entre la ejecución de diagnósticos y fallos del componente de energía. — `knowledge/references/forum_nvidia_372642_my-spark-is-overheating-when-clustered-and-running-a-model-across-both-fieldiag-.md:"Justificación técnica y disparador de reevaluación: El hilo reporta una falla concreta en la ejecución de fieldiags (microcódigo/firmware de gestión de energía) que resulta en error FAIL sobre el componente de energía, provocando overheating en cluster DGX Spark por >4h. El mecanismo de extracción y ejecución de estos fieldiags es un punto de fallo identificable. Esto detona la creación de un ítem de backlog en el proyecto DGX Spark para: (1) analizar la lógica de los fieldiags fallidos, (2) implementar un fallback o validación de potencia segura y (3) endurecer los perfiles térmicos para inferencia prolongada. El disparador es la correlación entre la ejecución de fieldiags y el fallo de componente de energía, requisito indispensable para la estabilidad del clúster."`

## Por qué se sugiere para blackbox en concreto

El disparador de reevaluacion detona 'un item de backlog en el proyecto DGX Spark' (nombre falso) para analizar fieldiags fallidos y endurecer perfiles termicos de hardware bajo carga en cluster, mecanismo que es exactamente el dominio de blackbox (telemetria/monitoreo de hardware de la AI TOP ATOM).

## Procedencia

- Fuente original: https://forums.developer.nvidia.com/t/my-spark-is-overheating-when-clustered-and-running-a-model-across-both-fieldiag-fail/372642
- Dictamen de cosecha, ruta absoluta: `~/projects/Atlas/docs/agent_findings/2026-09-05_cosecha_forum_nvidia_372642_my-spark-is-overheating-when-clustered-and-running-a-model-across-both-fieldiag-.md`
- Corregido el 2026-09-09 (DGX-503): el dictamen original interrogó estos mecanismos sólo contra
  Atlas/aequitas_os porque la lista de flota de Atlas estaba rota (DGX-502) y no consideraba
  a blackbox en absoluto.

## Lo que esta ficha NO decide

No dice que blackbox deba adoptar nada. No mide si el código fuente es
production-ready, tiene licencia compatible, o pasa los propios gates de este repo -- eso lo
evalúa quien trabaje aquí, si decide que vale la pena mirarlo.
