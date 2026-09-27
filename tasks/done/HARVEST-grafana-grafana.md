---
id: HARVEST-grafana-grafana
kind: task
title: "Evaluar adopción: mecanismo cosechado por Atlas (grafana-grafana)"
status: done
closure_type: void_wontfix
closed_at: 2026-09-26
severity: P3
origin: asserted
satd_family: HARVEST_SUGGESTION
close_check: {"cmd": "python -m tools.check_harvest_accepted tasks/done/HARVEST-grafana-grafana.md", "expect": "exit_zero", "porque": "Sugerencia de adopcion, no un defecto: lo unico verificable por maquina es que la DECISION quedo registrada. Cerrada, la forma que el modulo comprueba es closure_type + reason (no accepted, que ledger_schema prohibe junto a status: done). El texto anterior describia la forma ABIERTA y quedo falso al cerrarse -- un porque falso no se puede refutar midiendo lo que dice."}
created: 2026-09-09
evidence:
  pass: shared:harvest-decision-registrada
  fail: shared:harvest-decision-registrada
  e2e: shared:harvest-decision-registrada
reason: "void_wontfix: la DECISION registrada ES el entregable de una ficha HARVEST -- no hay fix de codigo que probar. Decidida el 2026-09-09 por the maintainer + Claude, revision de deuda 2026-09-09, con este disparador de reapertura: revisado a fondo (codigo + fuente citada) y sin valor incremental hoy -- reabrir si aparece un caso real medido en esta maquina que lo contradiga || Motivo tecnico: Los tres mecanismos (mezcla de datasources, variables de plantilla, alerting visual) son features de una UI de dashboard -- categoria explicitamente descartada en el README ('UI: curses, SSE, gauges -- Descartado')."
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

- Mecanismo 1 (Configuración de datasources y provisioning automatizado): permite registrar y mezclar diferentes fuentes en un mismo gráfico especificándolas por consulta — `knowledge/references/github_com_grafana_grafana.md:"Mix different data sources in the same graph! You can specify a data source on a per-query basis. This works for even custom datasources."`
- Mecanismo 2 (Motor de plantillas dinámicas / template variables): implementa sustitución de variables desplegadas como selectores en la interfaz para parametrizar consultas dinámicamente — `knowledge/references/github_com_grafana_grafana.md:"Create dynamic & reusable dashboards with template variables that appear as dropdowns at the top of the dashboard."`
- Mecanismo 3 (Motor de alerting continuo y notificación): evalúa continuamente reglas de alerta visuales y despacha notificaciones a través de canales externos estructurados — `knowledge/references/github_com_grafana_grafana.md:"Visually define alert rules for your most important metrics. Grafana will continuously evaluate and send notifications to systems like Slack, PagerDuty, VictorOps, OpsGenie."`
- Interrogatorio Mecanismo 1: ataca la categoría de falla de inconsistencia por dispersión de fuentes de datos aisladas y se mapea al dolor de validación cruzada en Cuenca / proyectos de la flota — `knowledge/references/github_com_grafana_grafana.md:"La capacidad de mezclar diferentes datasources en un mismo gráfico es crítica para validar y cruzar datos financieros estructurados (JSON/tablas) con métricas de operación"`
- Interrogatorio Mecanismo 2: ataca la categoría de falla de dispersión/duplicación de consultas manuales ad-hoc y falta de reproducibilidad en la visualización, asociándose a Atlas — `knowledge/references/github_com_grafana_grafana.md:"El mecanismo de *template variables* permite a Atlas crear dashboards ejecutables y compartidos donde el usuario final puede cambiar el enfoque de la monitorización sin editar la query"`
- Interrogatorio Mecanismo 3: ataca la categoría de falla de degradación silenciosa no detectada a tiempo, mapeándose al rol de observabilidad en Liberation Watchdog — `knowledge/references/github_com_grafana_grafana.md:"El sistema de alertas visuales y notificaciones automáticas a sistemas externos (Slack, PagerDuty) es el mecanismo base para que el *Watchdog* detecte desviaciones críticas en tiempo real"`

## Por qué se sugiere para blackbox en concreto

El Mecanismo 3 verificado (alerting continuo con notificaciones a Slack/PagerDuty ante degradación silenciosa de métricas) se atribuyó a 'Liberation Watchdog', que no es satélite real; ese dominio de observabilidad/alertas sobre hardware coincide exactamente con blackbox ('monitoreo de hardware, logs, systemd units' de la AI TOP ATOM/GB10), no considerado en la interrogación original.

## Procedencia

- Fuente original: https://github.com/grafana/grafana
- Dictamen de cosecha, ruta absoluta: `~/projects/Atlas/docs/agent_findings/2026-09-05_cosecha_github_com_grafana_grafana.md`
- Corregido el 2026-09-09 (DGX-503): el dictamen original interrogó estos mecanismos sólo contra
  Atlas/aequitas_os porque la lista de flota de Atlas estaba rota (DGX-502) y no consideraba
  a blackbox en absoluto.

## Lo que esta ficha NO decide

No dice que blackbox deba adoptar nada. No mide si el código fuente es
production-ready, tiene licencia compatible, o pasa los propios gates de este repo -- eso lo
evalúa quien trabaje aquí, si decide que vale la pena mirarlo.

## CERRADA el 2026-09-26 como `void_wontfix`

La decision estaba tomada el **2026-09-09** y su `close_check` la daba por
cumplida; lo que faltaba era archivarla. Se cierra con las 33 hermanas en la
misma pasada, por la misma causa.

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
python -m tools.check_harvest_accepted tasks/done/HARVEST-grafana-grafana.md
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
