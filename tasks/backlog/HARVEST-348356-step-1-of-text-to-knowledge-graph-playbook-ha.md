---
id: HARVEST-348356-step-1-of-text-to-knowledge-graph-playbook-ha
kind: task
title: "Evaluar adopción: mecanismo cosechado por Atlas (348356-step-1-of-text-to-knowledge-graph-playbook-has-an-error)"
status: open
severity: P3
origin: asserted
satd_family: HARVEST_SUGGESTION
close_check: {"cmd": "python -m tools.check_harvest_accepted tasks/backlog/HARVEST-348356-step-1-of-text-to-knowledge-graph-playbook-ha.md", "expect": "exit_zero", "porque": "Sugerencia de adopcion, no un defecto -- verifica que accepted.by/date/trigger este lleno y no sea el placeholder, patron de own_chats/tools/check_harvest_accepted.py (DGX-505)."}
created: 2026-09-09
accepted: {"by": "the maintainer + Claude, revision de deuda 2026-09-09", "date": "2026-09-09", "trigger": "adoptado -- el trabajo real vive en tasks/backlog/FEATURE-GPU-UTIL-CERO-FALLBACK-CPU.md, no en esta ficha de evaluacion"}
reason: "Cruzar utilizacion de GPU (ya muestreada) contra carga activa para detectar 0% = fallback silencioso a CPU es una correlacion nueva, mismo patron que el tok/s ya adoptado. Se consolida en FEATURE-GPU-UTIL-CERO-FALLBACK-CPU."
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

- El mecanismo de informe de telemetría de GPU mediante NVIDIA-SMI y dashboard reporta 0% de utilización durante la extracción de tripletes KG cuando el runtime no hace offloading a GPU — `knowledge/references/forum_nvidia_348356_step-1-of-text-to-knowledge-graph-playbook-has-an-error.md:"El mecanismo aquí es la informe de telemetría del driver NVIDIA-SMI frente a la carga de trabajo inferencia/extracción."`
- Para el mecanismo de ruta errónea en la documentación inicial, la categoría de falla que ataca es fallo de inicialización por discrepancia en la estructura de rutas relativas del repositorio — `knowledge/references/forum_nvidia_348356_step-1-of-text-to-knowledge-graph-playbook-has-an-error.md:"Este es un error de pathing relativo que rompe la ejecución inicial del flujo de trabajo."`
- La reevaluación se detona al corregir y endurecer la configuración del playbook para asegurar la utilización real del hardware — `knowledge/references/forum_nvidia_348356_step-1-of-text-to-knowledge-graph-playbook-has-an-error.md:"esto detona la creación de un ítem de *backlog* en el proyecto **DGX Spark** para corregir el *playbook* y endurecer la configuración por defecto."`

## Por qué se sugiere para blackbox en concreto

El hallazgo VERIFICADO 'telemetría de GPU mediante NVIDIA-SMI... reporta 0% de utilización... cuando el runtime no hace offloading a GPU' se atribuye como backlog al inexistente 'proyecto DGX Spark' (verificado en la cita del disparador); ese mecanismo de verificación de utilización GPU para detectar fallback silencioso a CPU es el dominio declarado de blackbox (telemetría/monitoreo de hardware de la AI TOP ATOM GB10), nunca considerado por la lista rota de 5.

## Procedencia

- Fuente original: https://forums.developer.nvidia.com/t/step-1-of-text-to-knowledge-graph-playbook-has-an-error/348356
- Dictamen de cosecha, ruta absoluta: `~/projects/Atlas/docs/agent_findings/2026-09-05_cosecha_forum_nvidia_348356_step-1-of-text-to-knowledge-graph-playbook-has-an-error.md`
- Corregido el 2026-09-09 (DGX-503): el dictamen original interrogó estos mecanismos sólo contra
  Atlas/aequitas_os porque la lista de flota de Atlas estaba rota (DGX-502) y no consideraba
  a blackbox en absoluto.

## Lo que esta ficha NO decide

No dice que blackbox deba adoptar nada. No mide si el código fuente es
production-ready, tiene licencia compatible, o pasa los propios gates de este repo -- eso lo
evalúa quien trabaje aquí, si decide que vale la pena mirarlo.
