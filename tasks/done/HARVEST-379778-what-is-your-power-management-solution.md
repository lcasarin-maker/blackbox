---
id: HARVEST-379778-what-is-your-power-management-solution
kind: task
title: "Evaluar adopción: mecanismo cosechado por Atlas (379778-what-is-your-power-management-solution)"
status: done
closure_type: void_wontfix
closed_at: 2026-09-26
severity: P3
origin: asserted
satd_family: HARVEST_SUGGESTION
close_check: {"cmd": "python -m tools.check_harvest_accepted tasks/done/HARVEST-379778-what-is-your-power-management-solution.md", "expect": "exit_zero", "porque": "Sugerencia de adopcion, no un defecto: lo unico verificable por maquina es que la DECISION quedo registrada. Cerrada, la forma que el modulo comprueba es closure_type + reason (no accepted, que ledger_schema prohibe junto a status: done). El texto anterior describia la forma ABIERTA y quedo falso al cerrarse -- un porque falso no se puede refutar midiendo lo que dice."}
created: 2026-09-09
evidence:
  pass: shared:harvest-decision-registrada
  fail: shared:harvest-decision-registrada
  e2e: shared:harvest-decision-registrada
reason: "void_wontfix: la DECISION registrada ES el entregable de una ficha HARVEST -- no hay fix de codigo que probar. Decidida el 2026-09-09 por the maintainer + Claude, revision de deuda 2026-09-09, con este disparador de reapertura: revisado a fondo (codigo + fuente citada) y sin valor incremental hoy -- reabrir si aparece un caso real medido en esta maquina que lo contradiga || Motivo tecnico: La orquestacion por PDU/smart-plug para cortar y restaurar AC es mitigacion activa externa (power-cycling remoto), fuera de alcance. La falta de S3 suspend es un hecho de hardware, no una señal a capturar."
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

- El primer mecanismo es el apagado completo forzado ante la ineficacia de S2Idle y la falta de soporte de S3 suspend-to-RAM en hardware GB10/DGX Spark — `knowledge/references/forum_nvidia_379778_what-is-your-power-management-solution.md:"Múltiples usuarios informan que la arquitectura GB10/DGX Spark no soporta S3 suspend-to-RAM confiable, cayendo en S2Idle (o peor), donde el sistema se despierta inmediatamente debido a interrupciones de hardware. Esto obliga a una estrategia de *full shutdown* en lugar de *suspend*."`
- El tercer mecanismo es la orquestación externa mediante PDU o Smart Plug ante la ausencia de Wake-on-LAN para cortar la alimentación AC y reactivar los nodos al restaurar la corriente — `knowledge/references/forum_nvidia_379778_what-is-your-power-management-solution.md:"La única vía viable para gestionar el poder es cortar la corriente AC mediante un smart plug o PDU gestionada, combinada con la práctica de apagar los nodos completamente. Dependiendo de que una señal externa (home lab / Raspberry Pi) reactive el sistema al restablecer la alimentación."`
- En el interrogatorio del paso 2, el mecanismo de shutdown completo ataca la categoría de falla de consumo energético desmedido en reposo / falta de suspensión por hardware — `knowledge/references/forum_nvidia_379778_what-is-your-power-management-solution.md:"Falta de soporte de suspend-to-RAM (S3) en hardware actual. Los nodos DGX Spark/Garuda no pueden mantener un estado de bajo consumo persistente sin riesgo de despertar, haciendo que el *idle* siga siendo caro en costo energético."`
- En el interrogatorio del paso 2, la intervención externa con PDU/Smart Plug ataca la categoría de falla de orquestación de energía fuera de banda / ausencia de encendido remoto por red — `knowledge/references/forum_nvidia_379778_what-is-your-power-management-solution.md:"Orquestación de energía fuera del control del SO: uso de hardware gestionado para *power cycling* y wake-on-power-restore, necesario por la ausencia de Wake-on-LAN y suspend confiable."`

## Por qué se sugiere para blackbox en concreto

Los mecanismos (shutdown forzado por falta de S3 suspend confiable en GB10/DGX Spark, orquestación externa por PDU/smart plug ante ausencia de Wake-on-LAN) son gestión de energía y ciclo de vida físico del hardware de la máquina -- misión central de blackbox -- pero solo se interrogó contra Atlas y el nombre falso Liberation Watchdog.

## Procedencia

- Fuente original: https://forums.developer.nvidia.com/t/what-is-your-power-management-solution/379778
- Dictamen de cosecha, ruta absoluta: `~/projects/Atlas/docs/agent_findings/2026-09-05_cosecha_forum_nvidia_379778_what-is-your-power-management-solution.md`
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
python -m tools.check_harvest_accepted tasks/done/HARVEST-379778-what-is-your-power-management-solution.md
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
