---
id: HARVEST-DanTup-dgx-dashboard
kind: task
title: "Evaluar adopción: mecanismo cosechado por Atlas (DanTup-dgx-dashboard)"
status: open
severity: P3
origin: asserted
satd_family: HARVEST_SUGGESTION
close_check: {"cmd": "python -m tools.check_harvest_accepted tasks/backlog/HARVEST-DanTup-dgx-dashboard.md", "expect": "exit_zero", "porque": "Sugerencia de adopcion, no un defecto -- verifica que accepted.by/date/trigger este lleno y no sea el placeholder, patron de own_chats/tools/check_harvest_accepted.py (DGX-505)."}
created: 2026-09-09
accepted: {"by": "the maintainer + Claude, revision de deuda 2026-09-09", "date": "2026-09-09", "trigger": "revisado a fondo (codigo + fuente citada) y sin valor incremental hoy -- reabrir si aparece un caso real medido en esta maquina que lo contradiga"}
reason: "Docker ya figura 'Adoptado' en la tabla de cherry-pick del README. El resto (socket passthrough, dashboard con UI) es un dashboard con interfaz, que blackbox no tiene."
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
