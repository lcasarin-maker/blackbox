---
id: HARVEST-365938-fabricmanager-will-not-run
kind: task
title: "Evaluar adopción: mecanismo cosechado por Atlas (365938-fabricmanager-will-not-run)"
status: done
closure_type: void_wontfix
closed_at: 2026-09-26
severity: P3
origin: asserted
satd_family: HARVEST_SUGGESTION
close_check: {"cmd": "python -m tools.check_harvest_accepted tasks/done/HARVEST-365938-fabricmanager-will-not-run.md", "expect": "exit_zero", "porque": "Sugerencia de adopcion, no un defecto: lo unico verificable por maquina es que la DECISION quedo registrada. Cerrada, la forma que el modulo comprueba es closure_type + reason (no accepted, que ledger_schema prohibe junto a status: done). El texto anterior describia la forma ABIERTA y quedo falso al cerrarse -- un porque falso no se puede refutar midiendo lo que dice."}
created: 2026-09-09
evidence:
  pass: shared:harvest-decision-registrada
  fail: shared:harvest-decision-registrada
  e2e: shared:harvest-decision-registrada
reason: "void_wontfix: la DECISION registrada ES el entregable de una ficha HARVEST -- no hay fix de codigo que probar. Decidida el 2026-09-09 por the maintainer + Claude, revision de deuda 2026-09-09, con este disparador de reapertura: revisado a fondo (codigo + fuente citada) y sin valor incremental hoy -- reabrir si aparece un caso real medido en esta maquina que lo contradiga || Motivo tecnico: Revisada la fuente completa: no hay tecnica concreta y verificable especifica para el dominio de blackbox bajo la reatribucion a 'Liberation Watchdog' (bloqueo por hostname sin comando ni patron de log citado). El fallback UMA a CPU se mapea explicitamente a otro proyecto (Cuenta/fintech) en la propia ficha, no a blackbox."
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

- El documento describe rutas alternativas de instalación basadas en `sparkrun.dev` y comandos CLI para evadir interfaces gráficas fallidas y habilitar un arranque headless — `knowledge/references/forum_nvidia_365938_fabricmanager-will-not-run.md:11`
- Se documenta el diagnóstico del modo de bloqueo de seguridad que deja la unidad en solo lectura activado por la configuración de hostname — `knowledge/references/forum_nvidia_365938_fabricmanager-will-not-run.md:12`
- Se analiza la gestión de memoria unificada (UMA) de DGX Spark (Strix Halo) y el fallo donde modelos cargan en CPU mientras GPU permanece ocioso — `knowledge/references/forum_nvidia_365938_fabricmanager-will-not-run.md:13`
- Para el mecanismo de CLI / instalación alternativa, ataca la categoría de falla de entorno gráfico inutilizable o bloqueo por reconfiguración; se mapea a DGX Spark y su versión a escala simplificada es un script o pipeline de instalación headless vía CLI — `knowledge/references/forum_nvidia_365938_fabricmanager-will-not-run.md:17`
- Para el diagnóstico de bloqueo de unidad, ataca la categoría de falsos positivos en mecanismos de seguridad ante cambios de configuración de sistema; Liberation Watchdog monitorea este patrón de degradación de resiliencia — `knowledge/references/forum_nvidia_365938_fabricmanager-will-not-run.md:18`
- Para la gestión de memoria UMA, ataca la categoría de fallback incorrecto a CPU o asignación subóptima de tensores en memoria unificada; mapea a Cuenta para validación de uso efectivo de GPU — `knowledge/references/forum_nvidia_365938_fabricmanager-will-not-run.md:19`
- El veredicto explícito registrado es COS con recomendación de creación de ítem de backlog en DGX Spark y Cuenta — `knowledge/references/forum_nvidia_365938_fabricmanager-will-not-run.md:23-24`

## Por qué se sugiere para blackbox en concreto

El diagnóstico de bloqueo de unidad se atribuye a "Liberation Watchdog" (nombre falso) para monitorear "degradación de resiliencia", que es el dominio exacto de blackbox (telemetría/monitoreo de hardware); el veredicto COS no cambia, se sostiene vía el mecanismo de instalación CLI/headless.

## Procedencia

- Fuente original: https://forums.developer.nvidia.com/t/fabricmanager-will-not-run/365938
- Dictamen de cosecha, ruta absoluta: `~/projects/Atlas/docs/agent_findings/2026-09-05_cosecha_forum_nvidia_365938_fabricmanager-will-not-run.md`
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
python -m tools.check_harvest_accepted tasks/done/HARVEST-365938-fabricmanager-will-not-run.md
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
