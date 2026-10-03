---
id: HARVEST-372662-cooler-gb10-temps-almost-no-performance-lost
kind: task
title: "Atlas: evaluar adopción — GB10 runs cooler with almost no performance loss"
status: done
closure_type: void_wontfix
closed_at: 2026-09-26
severity: P3
origin: asserted
satd_family: HARVEST_SUGGESTION
close_check: {"cmd": "python -m tools.check_harvest_accepted tasks/done/HARVEST-372662-cooler-gb10-temps-almost-no-performance-lost.md", "expect": "exit_zero", "porque": "Sugerencia de adopcion, no un defecto: lo unico verificable por maquina es que la DECISION quedo registrada. Cerrada, la forma que el modulo comprueba es closure_type + reason (no accepted, que ledger_schema prohibe junto a status: done). El texto anterior describia la forma ABIERTA y quedo falso al cerrarse -- un porque falso no se puede refutar midiendo lo que dice."}
created: 2026-09-09
evidence:
  pass: shared:harvest-decision-registrada
  fail: shared:harvest-decision-registrada
  e2e: shared:harvest-decision-registrada
reason: "void_wontfix: la DECISION registrada ES el entregable de una ficha HARVEST -- no hay fix de codigo que probar. Decidida el 2026-09-09 por the maintainer + Claude, revision de deuda 2026-09-09, con este disparador de reapertura: revisado a fondo (codigo + fuente citada) y sin valor incremental hoy -- reabrir si aparece un caso real medido en esta maquina que lo contradiga || Motivo tecnico: Verificado: Atlas YA lee multiples zonas termicas ACPI, no solo el die de GPU de nvidia-smi -- el README cita explicitamente thermal_zone4 y el maximo historico en 'zonas 0 y 4'. El gobernador dinamico de clock que propone la misma ficha es mitigacion activa, dominio de Atlas."
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

## CERRADA el 2026-09-26 como `void_wontfix`

La decision estaba tomada el **2026-09-09** y su `close_check` la daba por
cumplida; lo que faltaba era archivarla. Se cierra con sus hermanas en la misma
pasada, por la misma causa.

- **quien**: the maintainer + Claude, revision de deuda 2026-09-09
- **disparador de reapertura**: revisado a fondo (codigo + fuente citada) y sin valor incremental hoy -- reabrir si aparece un caso real medido en esta maquina que lo contradiga

El bloque `accepted` se retira del frontmatter porque `ledger_schema` prohibe que
conviva con `status: done` -- "una ficha cerrada no tiene nada que aceptar". Su
contenido no se pierde: esta arriba y en el `reason`.

## Root Cause

Atlas coseho un mecanismo de una fuente externa y lo sugirio para blackbox por
dominio. **Nadie de blackbox pidio esta evaluacion** -- es cosecha pasiva, y la
ficha existe para dejar constancia de la DECISION, no para hacer el trabajo.

La decision fue **DESCARTAR**, y por eso el `closure_type` es `void_wontfix` y no
`adopted_prior_implementation` como en las 26 HARVEST que este repo cerro antes:
aquellas apuntan a la ficha que lleva el codigo, y aqui no hay codigo al que
apuntar. El motivo tecnico concreto esta en el `reason` del frontmatter.

## Regression Test

**Un descarte no tiene codigo que pueda regresar**, y decir lo contrario seria
inventar un sujeto. Lo que puede cambiar es la PREMISA, y para eso esta el
disparador de reapertura, que es el verdadero criterio de vigilancia:

> revisado a fondo (codigo + fuente citada) y sin valor incremental hoy -- reabrir si aparece un caso real medido en esta maquina que lo contradiga

Lo unico verificable por maquina es que la decision quedo registrada en la forma
que el contrato exige:

```
python -m tools.check_harvest_accepted tasks/done/HARVEST-372662-cooler-gb10-temps-almost-no-performance-lost.md
```

Corrido el 2026-09-26 antes de cerrar: **pasa**. Y la compuerta de flota
`simplecode.verification.harvest_decision` sobre esta misma ficha: **pasa**.

## Verification Evidence

La decision registrada ES el entregable, asi que la evidencia es el propio
registro: `closure_type`, `reason` con quien decidio y cuando, y el disparador de
reapertura de arriba.

LIMITE DECLARADO, y es el mismo que las 26 anteriores ya declaraban: este
`close_check` comprueba que la ficha **diga** lo que dice, no que una funcion
sirva -- porque aqui no hay funcion. En un descarte eso es todo lo que hay que
comprobar, y se escribe en vez de presentar el chequeo del registro como si fuera
una prueba funcional.

Medido sobre el conjunto entero el 2026-09-26: 34 de 34 pasan su propio
`close_check` y 34 de 34 pasan `harvest_decision`.
