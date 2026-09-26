---
id: HARVEST-364636-with-two-sparks-vllm-0-18-1rc0-still-hammerin
kind: task
title: "Evaluar adopción: mecanismo cosechado por Atlas (364636-with-two-sparks-vllm-0-18-1rc0-still-hammering-two-cores-at-100)"
status: done
closure_type: void_wontfix
closed_at: 2026-09-26
severity: P3
origin: asserted
satd_family: HARVEST_SUGGESTION
close_check: {"cmd": "python -m tools.check_harvest_accepted tasks/done/HARVEST-364636-with-two-sparks-vllm-0-18-1rc0-still-hammerin.md", "expect": "exit_zero", "porque": "Sugerencia de adopcion, no un defecto: lo unico verificable por maquina es que la DECISION quedo registrada. Cerrada, la forma que el modulo comprueba es closure_type + reason (no accepted, que ledger_schema prohibe junto a status: done). El texto anterior describia la forma ABIERTA y quedo falso al cerrarse -- un porque falso no se puede refutar midiendo lo que dice."}
created: 2026-09-09
reason: "void_wontfix: la DECISION registrada ES el entregable de una ficha HARVEST -- no hay fix de codigo que probar. Decidida el 2026-09-09 por the maintainer + Claude, revision de deuda 2026-09-09, con este disparador de reapertura: hardware/escenario distinto -- reabrir si ATOM cambia de configuracion (cluster, rack, otro chip) || Motivo tecnico: Explicitamente multi-nodo (dos Sparks via Ray/QSFP56) -- fuera de alcance de una caja negra de una sola maquina. El submecanismo de nucleos al 100% ya queda cubierto por FEATURE-RED-CPU-SCAN via HARVEST-362964, sin aporte propio adicional."
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

## CERRADA el 2026-09-26 como `void_wontfix`

La decision estaba tomada el **2026-09-09** y su `close_check` la daba por
cumplida; lo que faltaba era archivarla. Se cierra con sus hermanas en la misma
pasada, por la misma causa.

- **quien**: the maintainer + Claude, revision de deuda 2026-09-09
- **disparador de reapertura**: hardware/escenario distinto -- reabrir si ATOM cambia de configuracion (cluster, rack, otro chip)

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

> hardware/escenario distinto -- reabrir si ATOM cambia de configuracion (cluster, rack, otro chip)

Lo unico verificable por maquina es que la decision quedo registrada en la forma
que el contrato exige:

```
python -m tools.check_harvest_accepted tasks/done/HARVEST-364636-with-two-sparks-vllm-0-18-1rc0-still-hammerin.md
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
