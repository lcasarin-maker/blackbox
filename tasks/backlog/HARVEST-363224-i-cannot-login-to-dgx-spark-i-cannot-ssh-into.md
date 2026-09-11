---
id: HARVEST-363224-i-cannot-login-to-dgx-spark-i-cannot-ssh-into
kind: task
title: "Evaluar adopción: mecanismo cosechado por Atlas (363224-i-cannot-login-to-dgx-spark-i-cannot-ssh-into-it-from-my-macboo)"
status: open
severity: P3
origin: asserted
satd_family: HARVEST_SUGGESTION
close_check: {"cmd": "python -m tools.check_harvest_accepted tasks/backlog/HARVEST-363224-i-cannot-login-to-dgx-spark-i-cannot-ssh-into.md", "expect": "exit_zero", "porque": "Sugerencia de adopcion, no un defecto -- verifica que accepted.by/date/trigger este lleno y no sea el placeholder, patron de own_chats/tools/check_harvest_accepted.py (DGX-505)."}
created: 2026-09-09
accepted: {"by": "the maintainer + Claude, revision de deuda 2026-09-09", "date": "2026-09-09", "trigger": "revisado a fondo (codigo + fuente citada) y sin valor incremental hoy -- reabrir si aparece un caso real medido en esta maquina que lo contradiga"}
reason: "El mecanismo 3 (pantalla de login colgada, 'se requiere acceso visual para monitoreo') es la MISMA senal que FEATURE-GDM-BOOT-COLGADO (originada en HARVEST-347951) sin ninguna tecnica adicional propia -- queda subsumida ahi, no aporta nada nuevo por su cuenta. El mecanismo 1 (OOM en entrenamiento) ya esta cubierto por el grep de OOM del kernel existente."
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
