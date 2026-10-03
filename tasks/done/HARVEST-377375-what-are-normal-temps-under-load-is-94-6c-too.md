---
id: HARVEST-377375-what-are-normal-temps-under-load-is-94-6c-too
kind: task
title: "Atlas: evaluar adopción — is 94.6°C normal under load?"
status: done
closure_type: void_wontfix
closed_at: 2026-09-26
severity: P3
origin: asserted
satd_family: HARVEST_SUGGESTION
close_check: {"cmd": "python -m tools.check_harvest_accepted tasks/done/HARVEST-377375-what-are-normal-temps-under-load-is-94-6c-too.md", "expect": "exit_zero", "porque": "Sugerencia de adopcion, no un defecto: lo unico verificable por maquina es que la DECISION quedo registrada. Cerrada, la forma que el modulo comprueba es closure_type + reason (no accepted, que ledger_schema prohibe junto a status: done). El texto anterior describia la forma ABIERTA y quedo falso al cerrarse -- un porque falso no se puede refutar midiendo lo que dice."}
created: 2026-09-09
evidence:
  pass: shared:harvest-decision-registrada
  fail: shared:harvest-decision-registrada
  e2e: shared:harvest-decision-registrada
reason: "void_wontfix: la DECISION registrada ES el entregable de una ficha HARVEST -- no hay fix de codigo que probar. Decidida el 2026-09-09 por the maintainer + Claude, revision de deuda 2026-09-09, con este disparador de reapertura: revisado a fondo (codigo + fuente citada) y sin valor incremental hoy -- reabrir si aparece un caso real medido en esta maquina que lo contradiga || Motivo tecnico: Pregunta de soporte sin mecanismo ('es normal 94.6C?'). Las zonas termicas y el clock-cap ya estan cubiertos; tegrastats seria redundante con atom_gpu_telemetry.py."
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
python -m tools.check_harvest_accepted tasks/done/HARVEST-377375-what-are-normal-temps-under-load-is-94-6c-too.md
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
