---
id: HARVEST-364636-with-two-sparks-vllm-0-18-1rc0-still-hammerin
kind: task
title: "Evaluar adopción: mecanismo cosechado por Atlas (364636-with-two-sparks-vllm-0-18-1rc0-still-hammering-two-cores-at-100)"
status: open
severity: P3
origin: asserted
satd_family: HARVEST_SUGGESTION
close_check: {"cmd": "python -m tools.check_harvest_accepted tasks/backlog/HARVEST-364636-with-two-sparks-vllm-0-18-1rc0-still-hammerin.md", "expect": "exit_zero", "porque": "Sugerencia de adopcion, no un defecto -- verifica que accepted.by/date/trigger este lleno y no sea el placeholder, patron de own_chats/tools/check_harvest_accepted.py (DGX-505)."}
created: 2026-09-09
accepted: {"by": "the maintainer + Claude, revision de deuda 2026-09-09", "date": "2026-09-09", "trigger": "hardware/escenario distinto -- reabrir si ATOM cambia de configuracion (cluster, rack, otro chip)"}
reason: "Explicitamente multi-nodo (dos Sparks via Ray/QSFP56) -- fuera de alcance de una caja negra de una sola maquina. El submecanismo de nucleos al 100% ya queda cubierto por FEATURE-RED-CPU-SCAN via HARVEST-362964, sin aporte propio adicional."
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

- PASO 1 (Mecanismo 3): Desactivación explícita de Ray mediante `--no-ray` para evitar que los procesos de sincronización y el agente de Ray residan en núcleos CPU en reposo — `knowledge/references/forum_nvidia_364636_with-two-sparks-vllm-0-18-1rc0-still-hammering-two-cores-at-100-when-idle.md:"Esto impide que el agente de Ray y sus procesos de sincronización se queden residiendo en los núcleos CPU durante el estado de inactividad, liberando los recursos CPU para otros procesos o reposo del sistema."`
- PASO 2 (Mecanismo 1): Ataca la categoría de falla de sobrecarga por sondeo activo en reposo / saturación de CPU por orquestadores externos en Atlas — `knowledge/references/forum_nvidia_364636_with-two-sparks-vllm-0-18-1rc0-still-hammering-two-cores-at-100-when-idle.md:"El cambio de backend de Ray a MP es un ajuste de enrutamiento a nivel de ejecutor, optimizando cómo Atlas programa los tokens a través de la infraestructura de múltiples nodos sin la sobrecarga del agente Ray."`
- PASO 2 (Mecanismo 2): Permite reducir la sobrecarga de orquestación en DGX Spark/GB10 sustituyendo el orquestador automático distribuido por inicialización estática punto a punto — `knowledge/references/forum_nvidia_364636_with-two-sparks-vllm-0-18-1rc0-still-hammering-two-cores-at-100-when-idle.md:"El mecanismo de lanzamiento manual con IDs de nodo y direcciones maestras es la forma estándar de coordinar ejecuciones distribuidas en hardware de alto rendimiento y bajo consumo donde la orquestación automática de Ray es excesiva o inestable."`
- PASO 2 (Mecanismo 3): Relacionado con Liberation Watchdog frente a la categoría de saturación de CPU inactiva / uso excesivo de recursos por demonios o procesos huérfanos — `knowledge/references/forum_nvidia_364636_with-two-sparks-vllm-0-18-1rc0-still-hammering-two-cores-at-100-when-idle.md:"La eliminación de Ray aborda directamente el "dolor" de los núcleos atascados al 100% durante el ocioso, un problema de libertad del sistema que el watchdog está diseñado para identificar y mitigar en despliegues de inference autónomos."`

## Por qué se sugiere para blackbox en concreto

El Mecanismo 3 se atribuye a "Liberation Watchdog" (nombre falso) para "saturación de CPU inactiva / uso excesivo de recursos por demonios o procesos huérfanos", que es exactamente el dominio de blackbox (telemetría/monitoreo de hardware, systemd units); el veredicto de producto COS no cambia porque ya se sostiene vía Atlas en los mecanismos 1 y 2.

## Procedencia

- Fuente original: https://forums.developer.nvidia.com/t/with-two-sparks-vllm-0-18-1rc0-still-hammering-two-cores-at-100-when-idle/364636
- Dictamen de cosecha, ruta absoluta: `~/projects/Atlas/docs/agent_findings/2026-09-05_cosecha_forum_nvidia_364636_with-two-sparks-vllm-0-18-1rc0-still-hammering-two-cores-at-100-when-idle.md`
- Corregido el 2026-09-09 (DGX-503): el dictamen original interrogó estos mecanismos sólo contra
  Atlas/aequitas_os porque la lista de flota de Atlas estaba rota (DGX-502) y no consideraba
  a blackbox en absoluto.

## Lo que esta ficha NO decide

No dice que blackbox deba adoptar nada. No mide si el código fuente es
production-ready, tiene licencia compatible, o pasa los propios gates de este repo -- eso lo
evalúa quien trabaje aquí, si decide que vale la pena mirarlo.
