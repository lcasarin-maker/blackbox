---
id: HARVEST-377375-what-are-normal-temps-under-load-is-94-6c-too
kind: task
title: "Evaluar adopción: mecanismo cosechado por Atlas (377375-what-are-normal-temps-under-load-is-94-6c-too-hot)"
status: open
severity: P3
origin: asserted
satd_family: HARVEST_SUGGESTION
close_check: {"cmd": "python -m tools.check_harvest_accepted tasks/backlog/HARVEST-377375-what-are-normal-temps-under-load-is-94-6c-too.md", "expect": "exit_zero", "porque": "Sugerencia de adopcion, no un defecto -- verifica que accepted.by/date/trigger este lleno y no sea el placeholder, patron de own_chats/tools/check_harvest_accepted.py (DGX-505)."}
created: 2026-09-09
accepted: {"by": "the maintainer + Claude, revision de deuda 2026-09-09", "date": "2026-09-09", "trigger": "revisado a fondo (codigo + fuente citada) y sin valor incremental hoy -- reabrir si aparece un caso real medido en esta maquina que lo contradiga"}
reason: "Pregunta de soporte sin mecanismo ('es normal 94.6C?'). Las zonas termicas y el clock-cap ya estan cubiertos; tegrastats seria redundante con atom_gpu_telemetry.py."
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

- Mecanismo 1 (Paso 1): Lectura cruda de temperaturas desde `sysfs` en `/sys/class/thermal/thermal_zoneN/temp` expresadas en milikelvin para mapear zonas térmicas — `knowledge/references/forum_nvidia_377375_what-are-normal-temps-under-load-is-94-6c-too-hot.md:12`
- Mecanismo 2 (Paso 1): Acoplamiento y limitación de frecuencia de reloj GPU (`300-2200` MHz) para reducir la disipación de calor operativa y evitar apagados térmicos — `knowledge/references/forum_nvidia_377375_what-are-normal-temps-under-load-is-94-6c-too-hot.md:14`
- Mecanismo 3 (Paso 1): Utilidad binaria `tegrastats` para consolidar telemetría de hardware (RAM, CPU%, zonas acpitz) en entornos donde no hay desglose por zona térmica — `knowledge/references/forum_nvidia_377375_what-are-normal-temps-under-load-is-94-6c-too-hot.md:16`
- Paso 2 (Interrogatorio Mecanismo 1): Ataca en Atlas la categoría de falla de caída de nodos por umbral de shutdown térmico no documentado; a escala pasa de telemetría distribuida en clúster a lectura directa por nodo en sysfs; nombra formalmente la inspección de registros térmicos acpitz del kernel — `knowledge/references/forum_nvidia_377375_what-are-normal-temps-under-load-is-94-6c-too-hot.md:22`
- Paso 2 (Interrogatorio Mecanismo 2): Ataca en DGX Spark / GB10 la categoría de falla de inestabilidad o crash por sobrecalentamiento bajo carga intensiva de inferencia; a escala pasa de políticas dinámicas del orquestador a fijación manual de frecuencia local; formaliza la degradación controlada de throughput — `knowledge/references/forum_nvidia_377375_what-are-normal-temps-under-load-is-94-6c-too-hot.md:23`
- Paso 2 (Interrogatorio Mecanismo 3): Ataca en Aequitas / Cuenza la categoría de falla de ceguera de observabilidad en firmware cerrado; a escala pasa de pipelines centralizados de métricas a binario local de diagnóstico; formaliza el sondeo periódico de contadores de hardware embebido — `knowledge/references/forum_nvidia_377375_what-are-normal-temps-under-load-is-94-6c-too-hot.md:24`
- Paso 3 (Veredicto y disparador): Declarado explícitamente como COS con disparador en la correlación entre temperaturas superiores a 90°C y fallos de estabilidad en cargas de lenguaje natural — `knowledge/references/forum_nvidia_377375_what-are-normal-temps-under-load-is-94-6c-too-hot.md:28`

## Por qué se sugiere para blackbox en concreto

El Mecanismo 3 (sondeo periódico de contadores de hardware embebido vía tegrastats/sysfs para 'ceguera de observabilidad en firmware cerrado') se mapea a 'Aequitas / Cuenza' (apps legal/fiscal), cuando ese mecanismo de telemetría de hardware es exactamente el dominio de blackbox.

## Procedencia

- Fuente original: https://forums.developer.nvidia.com/t/what-are-normal-temps-under-load-is-94-6c-too-hot/377375
- Dictamen de cosecha, ruta absoluta: `~/projects/Atlas/docs/agent_findings/2026-09-05_cosecha_forum_nvidia_377375_what-are-normal-temps-under-load-is-94-6c-too-hot.md`
- Corregido el 2026-09-09 (DGX-503): el dictamen original interrogó estos mecanismos sólo contra
  Atlas/aequitas_os porque la lista de flota de Atlas estaba rota (DGX-502) y no consideraba
  a blackbox en absoluto.

## Lo que esta ficha NO decide

No dice que blackbox deba adoptar nada. No mide si el código fuente es
production-ready, tiene licencia compatible, o pasa los propios gates de este repo -- eso lo
evalúa quien trabaje aquí, si decide que vale la pena mirarlo.
