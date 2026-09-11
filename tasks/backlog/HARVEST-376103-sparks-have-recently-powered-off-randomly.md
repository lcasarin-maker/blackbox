---
id: HARVEST-376103-sparks-have-recently-powered-off-randomly
kind: task
title: "Evaluar adopción: mecanismo cosechado por Atlas (376103-sparks-have-recently-powered-off-randomly)"
status: open
severity: P3
origin: asserted
satd_family: HARVEST_SUGGESTION
close_check: {"cmd": "python -m tools.check_harvest_accepted tasks/backlog/HARVEST-376103-sparks-have-recently-powered-off-randomly.md", "expect": "exit_zero", "porque": "Sugerencia de adopcion, no un defecto -- verifica que accepted.by/date/trigger este lleno y no sea el placeholder, patron de own_chats/tools/check_harvest_accepted.py (DGX-505)."}
created: 2026-09-09
accepted: {"by": "the maintainer + Claude, revision de deuda 2026-09-09", "date": "2026-09-09", "trigger": "revisado a fondo (codigo + fuente citada) y sin valor incremental hoy -- reabrir si aparece un caso real medido en esta maquina que lo contradiga"}
reason: "El mecanismo termico central (lectura por-zona en vez de un sensor promedio) es el mismo que HARVEST-372662, ya cubierto -- Atlas lee multiples zonas ACPI. El rele GPIO/ping para reboot remoto y el failover de cluster son mitigacion activa + multi-nodo."
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

- Mecanismo 1 (telemetría térmica incompleta): el sensor térmico expuesto captura un promedio de los cores pero no detecta hot-spots aislados (como una esquina a 105°C), lo que induce apagados de protección sin dejar logs de overheat o OOM — `knowledge/references/forum_nvidia_376103_sparks-have-recently-powered-off-randomly.md:"Los usuarios reportan apagados aleatorios sin logs de overheat o OOM visibles, indicando que el sensor térmico expuesto en el OS captura un promedio de todos los cores mientras que *hot-spots* aislados (ej. un corner del CPU a 105°C mientras el resto está a 60°C) pueden inducir apagado de protección sin ser detectados por el sistema."`
- Mecanismo 2 (degradación de pasta térmica y contacto mecánico): tras meses de operación la pasta térmica se seca y genera pérdidas de contacto térmico, provocando throttling, GPU power limiting y apagados por temperaturas físicas no registradas por los sensores — `knowledge/references/forum_nvidia_376103_sparks-have-recently-powered-off-randomly.md:"El fallo intermitente tras meses de operación (pasta seca, burbujas de aire en la aplicación factory) provoca que el disipador original pierda contacto térmico efectivo."`
- Interrogatorio del mecanismo 3 frente a Atlas: ataca la resiliencia de clúster ante fallos no-graciosos de hardware donde un nodo queda offline y sin reboot remoto de hardware el fallo es irreversible sin intervención física — `knowledge/references/forum_nvidia_376103_sparks-have-recently-powered-off-randomly.md:"- **Atlas**: El mecanismo #3 (relay controlado por GPIO/ping) mapea al router/resiliencia de Atlas: si un nodo DGX Spark en un clúster Atlas falla, el sistema de enrutamiento RAG o orquestación debería poder marcar ese nodo como *offline* y redundar"`

## Por qué se sugiere para blackbox en concreto

El mecanismo verificado de detectar apagones de hardware y marcar un nodo offline para redundancia se forzó contra Atlas (enrutamiento RAG, que no gestiona resiliencia de clúster de hardware) cuando el dominio real es blackbox (telemetría/monitoreo de hardware de la AI TOP ATOM/GB10).

## Procedencia

- Fuente original: https://forums.developer.nvidia.com/t/sparks-have-recently-powered-off-randomly/376103
- Dictamen de cosecha, ruta absoluta: `~/projects/Atlas/docs/agent_findings/2026-09-05_cosecha_forum_nvidia_376103_sparks-have-recently-powered-off-randomly.md`
- Corregido el 2026-09-09 (DGX-503): el dictamen original interrogó estos mecanismos sólo contra
  Atlas/aequitas_os porque la lista de flota de Atlas estaba rota (DGX-502) y no consideraba
  a blackbox en absoluto.

## Lo que esta ficha NO decide

No dice que blackbox deba adoptar nada. No mide si el código fuente es
production-ready, tiene licencia compatible, o pasa los propios gates de este repo -- eso lo
evalúa quien trabaje aquí, si decide que vale la pena mirarlo.
