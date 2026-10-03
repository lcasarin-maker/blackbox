---
id: HARVEST-372469-dgx-spark-shutting-down-under-load-mods-02000
kind: task
title: "Atlas: evaluar adopción — DGX Spark shuts down under load"
status: done
closure_type: void_wontfix
closed_at: 2026-09-26
severity: P3
origin: asserted
satd_family: HARVEST_SUGGESTION
close_check: {"cmd": "python -m tools.check_harvest_accepted tasks/done/HARVEST-372469-dgx-spark-shutting-down-under-load-mods-02000.md", "expect": "exit_zero", "porque": "Sugerencia de adopcion, no un defecto: lo unico verificable por maquina es que la DECISION quedo registrada. Cerrada, la forma que el modulo comprueba es closure_type + reason (no accepted, que ledger_schema prohibe junto a status: done). El texto anterior describia la forma ABIERTA y quedo falso al cerrarse -- un porque falso no se puede refutar midiendo lo que dice."}
created: 2026-09-09
evidence:
  pass: shared:harvest-decision-registrada
  fail: shared:harvest-decision-registrada
  e2e: shared:harvest-decision-registrada
reason: "void_wontfix: la DECISION registrada ES el entregable de una ficha HARVEST -- no hay fix de codigo que probar. Decidida el 2026-09-09 por the maintainer + Claude, revision de deuda 2026-09-09, con este disparador de reapertura: revisado a fondo (codigo + fuente citada) y sin valor incremental hoy -- reabrir si aparece un caso real medido en esta maquina que lo contradiga || Motivo tecnico: El 'diagnostico de campo' (MODS) es una prueba de estres activa -- benchmarking sintetico, explicitamente excluido. El chasis 3D-impreso es modificacion fisica de hardware. El capping de frecuencia ya esta aplicado como limite registrado (-lgc)."
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

- Mecanismo 1 (Paso 1): Diagnóstico de campo mediante prueba de estrés de energía (`MODS-020000600139`), diseñado para validar a bajo nivel la integridad de hardware y firmware bajo demanda — `knowledge/references/forum_nvidia_372469_dgx-spark-shutting-down-under-load-mods-020000600139.md:"El sistema falla específicamente en la prueba de estrés de campo con el código de error MODS-020000600139"`
- Mecanismo 3 (Paso 1): Refrigeración externa mediante flujo forzado (disipadores y ventilador externo en chasis impreso en 3D) para mantener temperaturas estables en el rango de 70-80°C — `knowledge/references/forum_nvidia_372469_dgx-spark-shutting-down-under-load-mods-020000600139.md:"I 3d printed a enclosure for my dual sparks that mounts them upright and has a usb 120mm fan blowing down on them."`
- Interrogatorio (Paso 2): El fallo en la prueba de estrés y los apagones bajo carga atacan la categoría de inestabilidad de hardware y firmware bajo carga en DGX Spark — `knowledge/references/forum_nvidia_372469_dgx-spark-shutting-down-under-load-mods-020000600139.md:"Esto impacta directamente la validación de hardware y la fiabilidad del dispositivo en el proyecto DGX Spark."`
- Interrogatorio (Paso 2): Los mecanismos de límite de frecuencia y supervisión de estado de energía atacan la categoría de degradación de estabilidad por gestión de recursos en Atlas — `knowledge/references/forum_nvidia_372469_dgx-spark-shutting-down-under-load-mods-020000600139.md:"Los mecanismos de *capping* de frecuencia y monitoreo de estados de energía son paralelos al enrutamiento y gestión de recursos de Atlas."`

## Por qué se sugiere para blackbox en concreto

El Mecanismo 1 (diagnostico de campo MODS-020000600139, prueba de estres de energia) se atribuye a 'el proyecto DGX Spark' (nombre falso) para 'validacion de hardware y fiabilidad del dispositivo', pero ese es exactamente el dominio declarado de blackbox (telemetria/monitoreo de hardware de la AI TOP ATOM, mismo chip GB10).

## Procedencia

- Fuente original: https://forums.developer.nvidia.com/t/dgx-spark-shutting-down-under-load-mods-020000600139/372469
- Dictamen de cosecha, ruta absoluta: `~/projects/Atlas/docs/agent_findings/2026-09-05_cosecha_forum_nvidia_372469_dgx-spark-shutting-down-under-load-mods-020000600139.md`
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
python -m tools.check_harvest_accepted tasks/done/HARVEST-372469-dgx-spark-shutting-down-under-load-mods-02000.md
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
