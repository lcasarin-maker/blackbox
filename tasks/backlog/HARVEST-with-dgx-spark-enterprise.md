---
id: HARVEST-with-dgx-spark-enterprise
kind: task
title: "Evaluar adopción: mecanismo cosechado por Atlas (with-dgx-spark-enterprise)"
status: open
severity: P3
origin: asserted
satd_family: HARVEST_SUGGESTION
close_check: {"cmd": "python -m tools.check_harvest_accepted tasks/backlog/HARVEST-with-dgx-spark-enterprise.md", "expect": "exit_zero", "porque": "Sugerencia de adopcion, no un defecto -- verifica que accepted.by/date/trigger este lleno y no sea el placeholder, patron de own_chats/tools/check_harvest_accepted.py (DGX-505)."}
created: 2026-09-09
accepted: {"by": "the maintainer + Claude, revision de deuda 2026-09-09", "date": "2026-09-09", "trigger": "hardware/escenario distinto -- reabrir si ATOM cambia de configuracion (cluster, rack, otro chip)"}
reason: "spark_updatectl.py (anillos de dispositivos) es gestion de flota multi-nodo, fuera de alcance. reset_reason_reporter.py depende de registros BMC que un DGX Spark no tiene (a diferencia de los sistemas DGX Enterprise de rack). El patron L1/L2 ya esta implementado como bb status/bb snapshot."
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

- Mecanismo 1: `spark_diagctl.py` implementa diagnóstico y observabilidad desacoplados en dos niveles (`L1` para postura de salud rápida sin artefactos grandes, y `L2` para generación de bundle profundo de evidencia con puntero por stdout) mediante ejecución remota agentless por SSH con sobre JSON estandarizado, para evitar residentes permanentes y no sobrecargar el sistema en monitoreo frecuente — `knowledge/references/developer_nvidia_com_blog_delivering_lifecycle_control_for_ai_infrastructure_at_scale_with_nvidia_dgx_spark_enterprise_m.md:66-70`
- Mecanismo 2: `reset_reason_reporter.py` correlaciona múltiples fuentes heterogéneas de evidencia (system event logs, registros BMC, kernel oops, eventos de firmware) y emite un veredicto estructurado con clasificaciones conservadoras que señalan ambigüedad en lugar de especular, diseñado así para asegurar fiabilidad en triaje y análisis de tendencias de estabilidad — `knowledge/references/developer_nvidia_com_blog_delivering_lifecycle_control_for_ai_infrastructure_at_scale_with_nvidia_dgx_spark_enterprise_m.md:71-72`
- Mecanismo 3: Separación estricta entre recolectores (`collectors`) y controladores (`controllers`), donde los recolectores operan en modo solo lectura sin privilegios y los controladores exigen sudo restringido por operación y aprobación de control de cambios, para mapear directamente al principio de mínimo privilegio y gobernanza empresarial — `knowledge/references/developer_nvidia_com_blog_delivering_lifecycle_control_for_ai_infrastructure_at_scale_with_nvidia_dgx_spark_enterprise_m.md:44-44`
- Mecanismo 4: `spark_updatectl.py` expone la postura de actualización en un reporte JSON (paquetes, firmware aplicable, reinicio pendiente) y coordina despliegues por etapas a través de anillos de dispositivos con captura de evidencia precheck/postcheck y reversibilidad de firmware — `knowledge/references/developer_nvidia_com_blog_delivering_lifecycle_control_for_ai_infrastructure_at_scale_with_nvidia_dgx_spark_enterprise_m.md:79-80`
- Falla con nombre que ataca: ataca la categoría de falla de reinicios silenciosos o fallas de hardware/firmware no reproducibles sin rastro ("reinicio no explicado y pérdida de telemetría de causa raíz"), así como la "falta de evidencia forense post-crash" — `knowledge/references/developer_nvidia_com_blog_delivering_lifecycle_control_for_ai_infrastructure_at_scale_with_nvidia_dgx_spark_enterprise_m.md:62-64`
- Versión a nuestra escala: el modelo reemplaza daemons de telemetría continuos y agentes pesados por scripts CLI invocados on-demand por SSH (`agentless SSH execution with bounded standard JSON output`) que producen archivos o sobres JSON estructurados consumibles directamente — `knowledge/references/developer_nvidia_com_blog_delivering_lifecycle_control_for_ai_infrastructure_at_scale_with_nvidia_dgx_spark_enterprise_m.md:20-21`
- Nombra algo que ya hacemos sin nombre: clasificar la telemetría en sondeos ligeros periódicos frente a paquetes de diagnóstico forense profundo generados solo bajo demanda ante incidentes (`L1 health posture` vs `L2 deep evidence bundle`) — `knowledge/references/developer_nvidia_com_blog_delivering_lifecycle_control_for_ai_infrastructure_at_scale_with_nvidia_dgx_spark_enterprise_m.md:68-69`
- PASO 3 (Veredicto del producto): DOM (Dominio ajeno / específico de infraestructura hardware DGX Spark y GB10). Disparador de reevaluación: incorporación de nodos de cómputo físico NVIDIA DGX/GB10 a la flota que requieran aprovisionamiento bare-metal y ciclo de vida de firmware/BMC bajo gobernanza enterprise — `knowledge/references/developer_nvidia_com_blog_delivering_lifecycle_control_for_ai_infrastructure_at_scale_with_nvidia_dgx_spark_enterprise_m.md:14-14`

## Por qué se sugiere para blackbox en concreto

Los mecanismos (spark_diagctl.py con niveles L1/L2 de diagnóstico, reset_reason_reporter.py correlacionando logs BMC/kernel oops/firmware para explicar reinicios silenciosos en hardware GB10) son exactamente el dominio de blackbox ('Caja negra / telemetría de la AI TOP ATOM (NVIDIA GB10): monitoreo de hardware, logs, systemd units'); el interrogatorio genérico ('a nuestra escala') nunca consideró ningún satélite real y el veredicto DOM ('fuera de la flota, sin nodos DGX/GB10 físicos') es incorrecto porque blackbox ya opera exactamente sobre hardware GB10.

## Procedencia

- Fuente original: https://developer.nvidia.com/blog/delivering-lifecycle-control-for-ai-infrastructure-at-scale-with-nvidia-dgx-spark-enterprise-manageability/
- Dictamen de cosecha, ruta absoluta: `~/projects/Atlas/docs/agent_findings/2026-09-05_cosecha_developer_nvidia_com_blog_delivering_lifecycle_control_for_ai_infrastructure_at_scale_with_nvidia_dgx_spark_enterprise_m.md`
- Corregido el 2026-09-09 (DGX-503): el dictamen original interrogó estos mecanismos sólo contra
  Atlas/aequitas_os porque la lista de flota de Atlas estaba rota (DGX-502) y no consideraba
  a blackbox en absoluto.

## Lo que esta ficha NO decide

No dice que blackbox deba adoptar nada. No mide si el código fuente es
production-ready, tiene licencia compatible, o pasa los propios gates de este repo -- eso lo
evalúa quien trabaje aquí, si decide que vale la pena mirarlo.
