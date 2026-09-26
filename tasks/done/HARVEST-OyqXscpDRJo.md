---
id: HARVEST-OyqXscpDRJo
kind: task
title: "Evaluar adopción: mecanismo cosechado por Atlas (OyqXscpDRJo)"
status: done
closure_type: void_wontfix
closed_at: 2026-09-26
severity: P3
origin: asserted
satd_family: HARVEST_SUGGESTION
close_check: {"cmd": "python -m tools.check_harvest_accepted tasks/done/HARVEST-OyqXscpDRJo.md", "expect": "exit_zero", "porque": "Sugerencia de adopcion, no un defecto: lo unico verificable por maquina es que la DECISION quedo registrada. Cerrada, la forma que el modulo comprueba es closure_type + reason (no accepted, que ledger_schema prohibe junto a status: done). El texto anterior describia la forma ABIERTA y quedo falso al cerrarse -- un porque falso no se puede refutar midiendo lo que dice."}
created: 2026-09-09
reason: "void_wontfix: la DECISION registrada ES el entregable de una ficha HARVEST -- no hay fix de codigo que probar. Decidida el 2026-09-09 por the maintainer + Claude, revision de deuda 2026-09-09, con este disparador de reapertura: hardware/escenario distinto -- reabrir si ATOM cambia de configuracion (cluster, rack, otro chip) || Motivo tecnico: NVLink C2C es interconexion intra-chip/multi-GPU no aplicable a un solo GB10 mono-nodo. El power-management/throttling dinamico ya lo cubren los campos pstate/throttle/sm_clk_mhz de atom_gpu_telemetry.py."
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

- Mecanismo 1 (NVLink C2C Interconnect): Acopla directamente las GPU Blackwell a través de un bus propietario de alta velocidad para mover datos a velocidades cercanas a la memoria RAM y mitigar los cuellos de botella del bus PCIe en comunicaciones GPU a GPU, logrando una reducción de aproximadamente 20% en tiempos de entrenamiento — `knowledge/references/youtube_OyqXscpDRJo.md:"Blackwell GPUs are linked directly through NVIDIA's proprietary fabric, which means data can move between them at near memory speeds"`
- Mecanismo 2 (DGX OS preconfigurado): Sistema operativo Linux optimizado y preinstalado que suprime la fricción de configuración manual de módulos del kernel y discrepancias de versiones de CUDA — `knowledge/references/youtube_OyqXscpDRJo.md:"The BIOS boots straight into NVIDIA's DGX OS, a Linux-based distribution preconfigured for AI workloads. Because it's a purpose-built OS, most of the driver gymnastics you'd normally have to perform on a generic Linux install are already taken care of."`
- Mecanismo 3 (Power Management Mode): Modo de administración inteligente de energía que aplica estrangulamiento (throttling) dinámico reduciendo el consumo de las GPU cuando están inactivas para mitigar el consumo frente al pico de 850W — `knowledge/references/youtube_OyqXscpDRJo.md:"intelligent power management mode that throttles the GPUs when they're idle, but you still need to be aware of the baseline draw."`
- Paso 2 para NVLink C2C: Se mapea con Atlas atacando la categoría de falla de degradación de rendimiento por saturación o cuello de botella en bus de interconexión (PCIe bottleneck) durante el intercambio entre aceleradores — `knowledge/references/youtube_OyqXscpDRJo.md:"Atlas aproveja arquitecturas similares para su enrutamiento RAG y comunicación entre aceleradores, asegurando que los flujos de datos no se degraden por limitaciones de bus PCIe."`
- Paso 2 para Gestión de energía: Se mapea con DGX Spark atacando la categoría de falla de sobrecarga térmica y consumo energético excesivo en factores de forma compactos — `knowledge/references/youtube_OyqXscpDRJo.md:"la arquitectura DGX Spark/GB10 requiere mecanismos de gestión de VRAM y potencia eficiente para operar dentro de los límites térmicos y energéticos de un factor de forma compacto"`

## Por qué se sugiere para blackbox en concreto

El hallazgo verificado 'Paso 2 para Gestion de energia: Se mapea con DGX Spark atacando ... sobrecarga termica y consumo energetico' trata el throttling dinamico como si DGX Spark fuera proyecto; ese mecanismo de monitoreo/gestion de energia en tiempo real es el dominio de blackbox ('monitoreo de hardware' de la AI TOP ATOM/GB10), no de un satelite inexistente.

## Procedencia

- Fuente original: https://www.youtube.com/watch?v=OyqXscpDRJo
- Dictamen de cosecha, ruta absoluta: `~/projects/Atlas/docs/agent_findings/2026-09-05_cosecha_youtube_OyqXscpDRJo.md`
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
python -m tools.check_harvest_accepted tasks/done/HARVEST-OyqXscpDRJo.md
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
