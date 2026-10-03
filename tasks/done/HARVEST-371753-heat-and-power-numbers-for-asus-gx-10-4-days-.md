---
id: HARVEST-371753-heat-and-power-numbers-for-asus-gx-10-4-days-
kind: task
title: "Atlas: evaluar adopción — ASUS GX10 heat and power after four days at 90%"
status: done
closure_type: void_wontfix
closed_at: 2026-09-26
severity: P3
origin: asserted
satd_family: HARVEST_SUGGESTION
close_check: {"cmd": "python -m tools.check_harvest_accepted tasks/done/HARVEST-371753-heat-and-power-numbers-for-asus-gx-10-4-days-.md", "expect": "exit_zero", "porque": "Sugerencia de adopcion, no un defecto: lo unico verificable por maquina es que la DECISION quedo registrada. Cerrada, la forma que el modulo comprueba es closure_type + reason (no accepted, que ledger_schema prohibe junto a status: done). El texto anterior describia la forma ABIERTA y quedo falso al cerrarse -- un porque falso no se puede refutar midiendo lo que dice."}
created: 2026-09-09
evidence:
  pass: shared:harvest-decision-registrada
  fail: shared:harvest-decision-registrada
  e2e: shared:harvest-decision-registrada
reason: "void_wontfix: la DECISION registrada ES el entregable de una ficha HARVEST -- no hay fix de codigo que probar. Decidida el 2026-09-09 por the maintainer + Claude, revision de deuda 2026-09-09, con este disparador de reapertura: hardware/escenario distinto -- reabrir si ATOM cambia de configuracion (cluster, rack, otro chip) || Motivo tecnico: Configuracion fisica de rack de 4 unidades con conveccion forzada que ATOM (una sola maquina de escritorio) no tiene; la cadencia de telemetria propuesta (3 min) es ademas peor que la ya existente."
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

- PASO 1 (Mecanismos), Mecanismo 1: Muestreo periódico de telemetría térmica y consumo cada tres minutos con persistencia — `knowledge/references/forum_nvidia_371753_heat-and-power-numbers-for-asus-gx-10-4-days-on-90-utilization.md:"Muestreo térmico cada 3 minutos con persistencia en disco"`
- PASO 1 (Mecanismos), Mecanismo 2: Arquitectura de disipación térmica por convección forzada en rack 5U bajo escritorio mediante disposición escalonada y ventilación push/pull — `knowledge/references/forum_nvidia_371753_heat-and-power-numbers-for-asus-gx-10-4-days-on-90-utilization.md:"Arquitectura de flujo de convección forzada en rack 5U"`
- La arquitectura mecánica ubica estante ventilado superior, ventilador de extracción frontal 1U Cloudplate T-6 y ventiladores push/pull 140mm atados a los rieles laterales — `knowledge/references/forum_nvidia_371753_heat-and-power-numbers-for-asus-gx-10-4-days-on-90-utilization.md:"top row is open vented shelf", "second layer is 1U Cloudplate T-6 front exhaust fan", "140mm Be Quiet Silent Pure 3 push/pull usando cable ties a side rails"`
- Los nodos se distribuyen escalonados de izquierda a derecha y de frente a fondo para dirigir la columna de convección hacia el extractor — `knowledge/references/forum_nvidia_371753_heat-and-power-numbers-for-asus-gx-10-4-days-on-90-utilization.md:"Staggering the GX10s left/right and front/back to push the convection column straight up into the T-6 exhaust"`
- PASO 1 (Mecanismos), Mecanismo 3: Estabilidad de frecuencia y mitigación de estrangulamiento térmico y caídas de energía por firmware ante eventos de agotamiento de memoria bajo utilización del 90%+ — `knowledge/references/forum_nvidia_371753_heat-and-power-numbers-for-asus-gx-10-4-days-on-90-utilization.md:"Estabilidad de frecuencia bajo carga sostenida (90% util)"`
- PASO 2 (Interrogatorio), Mecanismo 1: Ataca la categoría de falla conocida de degradación térmica acumulativa y estrangulamiento térmico de nodos en el sistema de telemetría de Atlas — `knowledge/references/forum_nvidia_371753_heat-and-power-numbers-for-asus-gx-10-4-days-on-90-utilization.md:"Este mecanismo es crítico para la detección temprana de degradación de componentes y la gestión de la residencia de trabajos en el clúster, evitando que los nodos entren en umbrales de calor crítico durante ejecuciones prolongadas."`
- PASO 2 (Interrogatorio), Mecanismo 2: Aplica a la optimización de flujo de aire para racks compactos transposables a Cuencia, atacando la acumulación de calor por convección confinada en espacios físicos reducidos — `knowledge/references/forum_nvidia_371753_heat-and-power-numbers-for-asus-gx-10-4-days-on-90-utilization.md:"el patrón de diseño de flujo de aire es transposable a las soluciones de rack de Cuencia para validar diseños de convección natural forzada en entornos de FinTech con restricciones de espacio físico."`
- PASO 2 (Interrogatorio), Mecanismo 3: Se mapea a DGX Spark atacando la degradación de rendimiento / estrangulamiento térmico en ejecuciones continuas y validando perfiles energéticos en nodos satélite aislados — `knowledge/references/forum_nvidia_371753_heat-and-power-numbers-for-asus-gx-10-4-days-on-90-utilization.md:"Valida que la arquitectura de potencia de estos "satélites" puede sostener cargas de inferencia/training intensivas sin throttling térmico, un dato clave para la ingeniería de firmware y configuraciones de VRAM en nodos isolados."`

## Por qué se sugiere para blackbox en concreto

El Mecanismo 1 -- muestreo periodico de telemetria termica/consumo cada 3 min con persistencia en disco -- se mapea a 'el sistema de telemetria de Atlas', pero ese es exactamente el dominio declarado de blackbox ('Caja negra / telemetria de la AI TOP ATOM: monitoreo de hardware, logs, systemd units'), un ajuste de dominio mucho mas directo que el RAG de Atlas.

## Procedencia

- Fuente original: https://forums.developer.nvidia.com/t/heat-and-power-numbers-for-asus-gx-10-4-days-on-90-utilization/371753
- Dictamen de cosecha, ruta absoluta: `~/projects/Atlas/docs/agent_findings/2026-09-05_cosecha_forum_nvidia_371753_heat-and-power-numbers-for-asus-gx-10-4-days-on-90-utilization.md`
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
- **disparador de reapertura**: hardware/escenario distinto -- reabrir si ATOM cambia de configuracion (cluster, rack, otro chip)

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

> hardware/escenario distinto -- reabrir si ATOM cambia de configuracion (cluster, rack, otro chip)

Lo unico verificable por maquina es que la decision quedo registrada en la forma
que el contrato exige:

```
python -m tools.check_harvest_accepted tasks/done/HARVEST-371753-heat-and-power-numbers-for-asus-gx-10-4-days-.md
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
