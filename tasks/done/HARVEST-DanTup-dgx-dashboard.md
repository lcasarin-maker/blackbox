---
id: HARVEST-DanTup-dgx-dashboard
kind: task
title: "Evaluar adopción: mecanismo cosechado por Atlas (DanTup-dgx-dashboard)"
status: done
closure_type: void_wontfix
closed_at: 2026-09-26
severity: P3
origin: asserted
satd_family: HARVEST_SUGGESTION
close_check: {"cmd": "python -m tools.check_harvest_accepted tasks/done/HARVEST-DanTup-dgx-dashboard.md", "expect": "exit_zero", "porque": "Sugerencia de adopcion, no un defecto: lo unico verificable por maquina es que la DECISION quedo registrada. Cerrada, la forma que el modulo comprueba es closure_type + reason (no accepted, que ledger_schema prohibe junto a status: done). El texto anterior describia la forma ABIERTA y quedo falso al cerrarse -- un porque falso no se puede refutar midiendo lo que dice."}
created: 2026-09-09
evidence:
  pass: shared:harvest-decision-registrada
  fail: shared:harvest-decision-registrada
  e2e: shared:harvest-decision-registrada
reason: "void_wontfix: la DECISION registrada ES el entregable de una ficha HARVEST -- no hay fix de codigo que probar. Decidida el 2026-09-09 por the maintainer + Claude, revision de deuda 2026-09-09, con este disparador de reapertura: revisado a fondo (codigo + fuente citada) y sin valor incremental hoy -- reabrir si aparece un caso real medido en esta maquina que lo contradiga || Motivo tecnico: Docker ya figura 'Adoptado' en la tabla de cherry-pick del README. El resto (socket passthrough, dashboard con UI) es un dashboard con interfaz, que blackbox no tiene."
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

- El dashboard implementa un segundo mecanismo de "socket pass-through" para visibilidad de runtime: monta `/var/run/docker.sock` permitiendo que el contenedor ejecute API de Docker para listar y monitorear contenedores vivos — `knowledge/references/github_com_DanTup_dgx_dashboard.md:"Includes a list of Docker containers with CPU/memory usage and Start/Stop buttons"` — atacando la categoría de falla de "visibilidad incompleta de dependencias de ejecución"; escala directa a un nodo con API Docker nativa.
- El dashboard implementa un tercer mecanismo de colección condicionada a observación activa: recolecta métricas solo mientras existe cliente conectado, mediante bucles temporizados (5s para métricas, 10s para contenedores) controlados por bandera de estado — `knowledge/references/github_com_DanTup_dgx_dashboard.md:"Metrics update every 5s and are only collected while there is a connected client"` — atacando la categoría de falla de "desperdicio de recursos en recolección pasiva"; ejecutable en un nodo mediante control de banderas simples sin cambio de arquitectura.
- Los tres mecanismos son patrones concretos y funcionales (no descripciones de producto) cuya adopción está justificada por el mandato explícito del documento: "se requiere análisis de implementación y adopción/hardening para integrar estos patrones de medición y control de estado" — `knowledge/references/github_com_DanTup_dgx_dashboard.md:"se requiere análisis de implementación y adopción/hardening para integrar estos patrones de medición y control de estado en la infraestructura existente de Atlas o los proyectos de la flota"` — disparador: crear fichas de backlog para cada mecanismo en el proyecto propietario (ATL para Atlas si es infraestructura compartida, o LIB si es para el watchdog que gestiona recursos).

## Por qué se sugiere para blackbox en concreto

Es un dashboard de telemetría/contenedores Docker para una máquina tipo DGX (métricas CPU/memoria, systemd/containers) -- exactamente el dominio de blackbox (caja negra/telemetría de la AI TOP ATOM), pero el interrogatorio solo considera 'Atlas' o el prefijo ficticio 'LIB' (Liberation Watchdog) sin nombrar al satélite real de telemetría.

## Procedencia

- Fuente original: https://github.com/DanTup/dgx_dashboard
- Dictamen de cosecha, ruta absoluta: `~/projects/Atlas/docs/agent_findings/2026-09-06_cosecha_github_com_DanTup_dgx_dashboard.md`
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
python -m tools.check_harvest_accepted tasks/done/HARVEST-DanTup-dgx-dashboard.md
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
