---
id: HARVEST-grafana-grafana
kind: task
title: "Evaluar adopción: mecanismo cosechado por Atlas (grafana-grafana)"
status: open
severity: P3
origin: asserted
satd_family: HARVEST_SUGGESTION
close_check: {"cmd": "python -m tools.check_harvest_accepted tasks/backlog/HARVEST-grafana-grafana.md", "expect": "exit_zero", "porque": "Sugerencia de adopcion, no un defecto -- verifica que accepted.by/date/trigger este lleno y no sea el placeholder, patron de own_chats/tools/check_harvest_accepted.py (DGX-505)."}
created: 2026-09-09
accepted: {"by": "the maintainer + Claude, revision de deuda 2026-09-09", "date": "2026-09-09", "trigger": "revisado a fondo (codigo + fuente citada) y sin valor incremental hoy -- reabrir si aparece un caso real medido en esta maquina que lo contradiga"}
reason: "Los tres mecanismos (mezcla de datasources, variables de plantilla, alerting visual) son features de una UI de dashboard -- categoria explicitamente descartada en el README ('UI: curses, SSE, gauges -- Descartado')."
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
