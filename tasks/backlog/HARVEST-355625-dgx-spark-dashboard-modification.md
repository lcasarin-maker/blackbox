---
id: HARVEST-355625-dgx-spark-dashboard-modification
kind: task
title: "Evaluar adopción: mecanismo cosechado por Atlas (355625-dgx-spark-dashboard-modification)"
status: open
severity: P3
origin: asserted
satd_family: HARVEST_SUGGESTION
close_check: {"cmd": "python -m tools.check_harvest_accepted tasks/backlog/HARVEST-355625-dgx-spark-dashboard-modification.md", "expect": "exit_zero", "porque": "Sugerencia de adopcion, no un defecto -- verifica que accepted.by/date/trigger este lleno y no sea el placeholder, patron de own_chats/tools/check_harvest_accepted.py (DGX-505)."}
created: 2026-09-09
accepted: {"by": "the maintainer + Claude, revision de deuda 2026-09-09", "date": "2026-09-09", "trigger": "revisado a fondo (codigo + fuente citada) y sin valor incremental hoy -- reabrir si aparece un caso real medido en esta maquina que lo contradiga"}
reason: "El mecanismo central es un dashboard externo con UI -- exactamente lo que el README descarta explicitamente ('UI: curses, SSE, gauges -- Descartado, esto no tiene UI'). Lo demas (disco, Docker) ya esta adoptado."
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

- Mecanismo 1 (Inyección de métricas y capa externa de dashboard): Implementa un dashboard alternativo desacoplado para recolectar y mostrar uso de CPU, temperaturas y contenedores Docker sin alterar el binario oficial cerrado — `knowledge/references/forum_nvidia_355625_dgx-spark-dashboard-modification.md:"Este patrón aprovecha la arquitectura modular del sistema DGX Spark para interceptar llamadas de monitoreo del sistema y presentar datos agregados sin modificar el binario cerrado original."`
- Mecanismo 2 (Aislamiento y restricción de API Docker / WebSockets): Ejecuta el servicio en contenedor limitando conexiones WebSocket a mismo origen y acotando comandos de Docker exclusivamente a `start/stop/restart` (o prescindiendo del socket si sólo se requieren métricas) para mitigar vectores de compromiso en el demonio del host — `knowledge/references/forum_nvidia_355625_dgx-spark-dashboard-modification.md:"ensuring the backend only accepts WebSocket connections from the same origin and ensured the API only supports specific Docker commands"`
- Mecanismo 3 (Extracción y agregación de almacenamiento para cargas LLM y agentes): Mecanismo propuesto de lectura y parsing de metadatos/logs estructurados para calcular y visualizar el almacenamiento libre/utilizado por modelos LLM desplegados y datos de agentes — `knowledge/references/forum_nvidia_355625_dgx-spark-dashboard-modification.md:"We have an idea to show the free storage size as well to the dashboard, so the purpose of this is to look for our storage that calculates the usage of the applications we use (LLMs deployed, some agents data, etc)."`
- Paso 2 - Mecanismo 1: Ataca la categoría de falla de falta de observabilidad o telemetría en sistemas con componentes propietarios/cerrados; a nuestra escala pasa de un dashboard de nodo/host a un archivo de métricas o sondeo local; nombra la práctica de instrumentación externa o sidecar monitoring sin tocar el runtime central — `knowledge/references/forum_nvidia_355625_dgx-spark-dashboard-modification.md:"El dashboard original es cerrado-source y no modificable; el patrón de inyección externa resuelve la necesidad de monitoreo extensible sin violar la integridad del binario original."`
- Paso 2 - Mecanismo 2: Ataca la categoría de falla de escalada de privilegios o ejecución de comandos arbitrarios mediante exposición indebida del socket del motor de contenedores; a nuestra escala mapea a ejecución de procesos con privilegios mínimos y lista blanca de verbos; nombra el principio de mínimo privilegio en control de procesos — `knowledge/references/forum_nvidia_355625_dgx-spark-dashboard-modification.md:"limitando permisos a operaciones específicas y seguras."`
- Paso 2 - Mecanismo 3: Ataca la categoría de falla de agotamiento silencioso de disco o recursos de almacenamiento por acumulación de artefactos de inferencia; a nuestra escala mapea de un servicio centralizado de cuotas a inspección directa de rutas o archivos locales de log; nombra la contabilidad de uso de almacenamiento por proceso/agente — `knowledge/references/forum_nvidia_355625_dgx-spark-dashboard-modification.md:"parsing de metadata estructurada (probablemente JSON o archivos de log) para extraer valores numéricos de consumo de almacenamiento"`

## Por qué se sugiere para blackbox en concreto

El mecanismo es literalmente un dashboard externo desacoplado para CPU/temperatura/Docker que intercepta llamadas de monitoreo del sistema sin tocar el binario cerrado -- eso es exactamente la mision de blackbox (caja negra / telemetria de la AI TOP ATOM: monitoreo de hardware, logs, systemd), que el dictamen nunca considero por no estar en la lista rota.

## Procedencia

- Fuente original: https://forums.developer.nvidia.com/t/dgx-spark-dashboard-modification/355625
- Dictamen de cosecha, ruta absoluta: `~/projects/Atlas/docs/agent_findings/2026-09-05_cosecha_forum_nvidia_355625_dgx-spark-dashboard-modification.md`
- Corregido el 2026-09-09 (DGX-503): el dictamen original interrogó estos mecanismos sólo contra
  Atlas/aequitas_os porque la lista de flota de Atlas estaba rota (DGX-502) y no consideraba
  a blackbox en absoluto.

## Lo que esta ficha NO decide

No dice que blackbox deba adoptar nada. No mide si el código fuente es
production-ready, tiene licencia compatible, o pasa los propios gates de este repo -- eso lo
evalúa quien trabaje aquí, si decide que vale la pena mirarlo.
