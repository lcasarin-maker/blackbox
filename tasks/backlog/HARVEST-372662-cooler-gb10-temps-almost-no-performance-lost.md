---
id: HARVEST-372662-cooler-gb10-temps-almost-no-performance-lost
kind: task
title: "Evaluar adopción: mecanismo cosechado por Atlas (372662-cooler-gb10-temps-almost-no-performance-lost)"
status: open
severity: P3
origin: asserted
satd_family: HARVEST_SUGGESTION
close_check: {"cmd": "python -m tools.check_harvest_accepted tasks/backlog/HARVEST-372662-cooler-gb10-temps-almost-no-performance-lost.md", "expect": "exit_zero", "porque": "Sugerencia de adopcion, no un defecto -- verifica que accepted.by/date/trigger este lleno y no sea el placeholder, patron de own_chats/tools/check_harvest_accepted.py (DGX-505)."}
created: 2026-09-09
accepted: {"by": "the maintainer + Claude, revision de deuda 2026-09-09", "date": "2026-09-09", "trigger": "revisado a fondo (codigo + fuente citada) y sin valor incremental hoy -- reabrir si aparece un caso real medido en esta maquina que lo contradiga"}
reason: "Verificado: Atlas YA lee multiples zonas termicas ACPI, no solo el die de GPU de nvidia-smi -- el README cita explicitamente thermal_zone4 y el maximo historico en 'zonas 0 y 4'. El gobernador dinamico de clock que propone la misma ficha es mitigacion activa, dominio de Atlas."
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

- PASO 1 (Mecanismos): El primer mecanismo es el ajuste y limitación de frecuencia de GPU mediante `nvidia-smi -lgc 0,2000`, modulando a nivel de driver el límite superior de reloj a 2000 MHz frente al rango de fábrica de 2400-2470 MHz para reducir drásticamente potencia y temperatura con mínimo impacto en inferencia limitada por ancho de banda — `knowledge/references/forum_nvidia_372662_cooler-gb10-temps-almost-no-performance-lost.md:"sudo nvidia-smi -lgc 0,2000"`
- PASO 1 (Mecanismos): El segundo mecanismo es un gobernador térmico dinámico de lazo cerrado implementado en Python (`gb10-clock-governor.py`) que ajusta la frecuencia bajando o subiendo peldaños en una escala (`LADDER = [2400, 2200, 2000, 1800, 1700, 1500, 1300, 1200]`) según la temperatura leída del sensor más caliente — `knowledge/references/forum_nvidia_372662_cooler-gb10-temps-almost-no-performance-lost.md:"LADDER = [2400, 2200, 2000, 1800, 1700, 1500, 1300, 1200]"`
- PASO 1 (Mecanismos): El tercer mecanismo es la telemetría de temperatura multi-zona tomando el valor máximo entre las zonas ACPI (`/sys/class/thermal/thermal_zone*/temp`) y la lectura del die GPU de `nvidia-smi`, debido a que el die GPU no es el punto más caliente del SoC unificado y subestima la temperatura real entre 7 y 17 °C — `knowledge/references/forum_nvidia_372662_cooler-gb10-temps-almost-no-performance-lost.md:"# max over ALL ACPI zones + nvidia-smi GPU die"`
- PASO 2 (Interrogatorio - Falla de flota que ataca): Para DGX Spark, el mecanismo ataca directamente la categoría de falla conocida de sobrecalentamiento y apagado térmico automático ("DGX Spark temperature too high, automatic shutdown") bajo cargas continuas o falta de refrigeración ambiental — `knowledge/references/forum_nvidia_372662_cooler-gb10-temps-almost-no-performance-lost.md:"DGX Spark temperature too high, automatic shutdown"`
- PASO 2 (Interrogatorio - Escala): La versión a escala de un solo nodo de inferencia/batch local consiste en invocar el script gobernador como servicio de systemd (`gb10-clock-governor.service`) o encapsulado en un wrapper bash de ejecución de tareas (`govern-run.sh`) restaurando relojes al finalizar mediante `nvidia-smi -rgc` — `knowledge/references/forum_nvidia_372662_cooler-gb10-temps-almost-no-performance-lost.md:"python3 /opt/gb10-clock-governor.py --target 80 & gov=$!"`
- PASO 2 (Interrogatorio - Nombra algo sin nombre): Formaliza el principio de que en cargas limitadas por ancho de banda de memoria (memory-bandwidth-bound), el exceso de frecuencia de cómputo sobre el punto óptimo de retorno decreciente actúa como gasto térmico performativo sin ganancia real de throughput — `knowledge/references/forum_nvidia_372662_cooler-gb10-temps-almost-no-performance-lost.md:"overclocking at 3000 Mhz is purely performative and worthless"`
- PASO 3 (Veredicto y Disparador de reevaluación): Veredicto `COS` con disparador de reevaluación centrado en la necesidad de estandarizar la política de limitación o gobierno dinámico en la imagen base de DGX Spark para prevenir paradas térmicas y reducir consumo energético sin degradar el throughput de inferencia — `knowledge/references/forum_nvidia_372662_cooler-gb10-temps-almost-no-performance-lost.md:"El disparador de reevaluación es la necesidad de estandarizar este ajuste en la imagen base de DGX Spark para evitar apagados automáticos por sobrecalentamiento en escenarios de carga larga, reduciendo costos de energía sin impacto material en el throughput."`

## Por qué se sugiere para blackbox en concreto

El gobernador termico dinamico (gb10-clock-governor.py como servicio systemd, telemetria multi-zona de temperatura) se atribuye a 'la imagen base de DGX Spark' (nombre falso), pero ese mecanismo -- monitoreo de hardware y logs via systemd units -- es exactamente el dominio declarado de blackbox.

## Procedencia

- Fuente original: https://forums.developer.nvidia.com/t/cooler-gb10-temps-almost-no-performance-lost/372662
- Dictamen de cosecha, ruta absoluta: `~/projects/Atlas/docs/agent_findings/2026-09-05_cosecha_forum_nvidia_372662_cooler-gb10-temps-almost-no-performance-lost.md`
- Corregido el 2026-09-09 (DGX-503): el dictamen original interrogó estos mecanismos sólo contra
  Atlas/aequitas_os porque la lista de flota de Atlas estaba rota (DGX-502) y no consideraba
  a blackbox en absoluto.

## Lo que esta ficha NO decide

No dice que blackbox deba adoptar nada. No mide si el código fuente es
production-ready, tiene licencia compatible, o pasa los propios gates de este repo -- eso lo
evalúa quien trabaje aquí, si decide que vale la pena mirarlo.
