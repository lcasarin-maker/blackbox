---
id: HARVEST-363224-i-cannot-login-to-dgx-spark-i-cannot-ssh-into
kind: task
title: "Evaluar adopción: mecanismo cosechado por Atlas (363224-i-cannot-login-to-dgx-spark-i-cannot-ssh-into-it-from-my-macboo)"
status: done
closure_type: void_wontfix
closed_at: 2026-09-26
severity: P3
origin: asserted
satd_family: HARVEST_SUGGESTION
close_check: {"cmd": "python -m tools.check_harvest_accepted tasks/done/HARVEST-363224-i-cannot-login-to-dgx-spark-i-cannot-ssh-into.md", "expect": "exit_zero", "porque": "Sugerencia de adopcion, no un defecto: lo unico verificable por maquina es que la DECISION quedo registrada. Cerrada, la forma que el modulo comprueba es closure_type + reason (no accepted, que ledger_schema prohibe junto a status: done). El texto anterior describia la forma ABIERTA y quedo falso al cerrarse -- un porque falso no se puede refutar midiendo lo que dice."}
created: 2026-09-09
reason: "void_wontfix: la DECISION registrada ES el entregable de una ficha HARVEST -- no hay fix de codigo que probar. Decidida el 2026-09-09 por the maintainer + Claude, revision de deuda 2026-09-09, con este disparador de reapertura: revisado a fondo (codigo + fuente citada) y sin valor incremental hoy -- reabrir si aparece un caso real medido en esta maquina que lo contradiga || Motivo tecnico: El mecanismo 3 (pantalla de login colgada, 'se requiere acceso visual para monitoreo') es la MISMA senal que FEATURE-GDM-BOOT-COLGADO (originada en HARVEST-347951) sin ninguna tecnica adicional propia -- queda subsumida ahi, no aporta nada nuevo por su cuenta. El mecanismo 1 (OOM en entrenamiento) ya esta cubierto por el grep de OOM del kernel existente."
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

- Interrogatorio del Mecanismo 1 (Falla que ataca): ataca el dolor de Out of Memory (OOM) / agotamiento de memoria durante cargas de trabajo de entrenamiento/modelos en hardware DGX Spark — `knowledge/references/forum_nvidia_363224_i-cannot-login-to-dgx-spark-i-cannot-ssh-into-it-from-my-macbook-either.md:"Ataca el dolor de **OOM (Out of Memory)** durante cargas de trabajo de entrenamiento/modelos, que es el caso de uso principal del hardware DGX Spark."`
- Interrogatorio del Mecanismo 3 (Falla que ataca): mapea al caso de uso de Liberation Watchdog (o infraestructura de escritorio ligada) ante el congelamiento completo o bloqueo del subsistema visual — `knowledge/references/forum_nvidia_363224_i-cannot-login-to-dgx-spark-i-cannot-ssh-into-it-from-my-macbook-either.md:"El mecanismo de la pantalla de login colgada mapea al caso de uso de **Liberation Watchdog** (o infraestructura de escritorio ligada) donde se requiere acceso visual para monitoreo o depuración"`

## Por qué se sugiere para blackbox en concreto

El mecanismo 3 (pantalla de login colgada) se mapeó a 'Liberation Watchdog' diciendo textualmente que 'se requiere acceso visual para monitoreo o depuración' -- eso es literalmente el mandato de blackbox ('monitoreo de hardware, logs, systemd units' de la AI TOP ATOM/GB10), nunca considerado por ser fantasma.

## Procedencia

- Fuente original: https://forums.developer.nvidia.com/t/i-cannot-login-to-dgx-spark-i-cannot-ssh-into-it-from-my-macbook-either/363224
- Dictamen de cosecha, ruta absoluta: `~/projects/Atlas/docs/agent_findings/2026-09-05_cosecha_forum_nvidia_363224_i-cannot-login-to-dgx-spark-i-cannot-ssh-into-it-from-my-macbook-either.md`
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
python -m tools.check_harvest_accepted tasks/done/HARVEST-363224-i-cannot-login-to-dgx-spark-i-cannot-ssh-into.md
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
