---
id: HARVEST-378031-msi-edge-expert-nvme-devices-not-found
kind: task
title: "Evaluar adopción: mecanismo cosechado por Atlas (378031-msi-edge-expert-nvme-devices-not-found)"
status: done
closure_type: void_wontfix
closed_at: 2026-09-26
severity: P3
origin: asserted
satd_family: HARVEST_SUGGESTION
close_check: {"cmd": "python -m tools.check_harvest_accepted tasks/done/HARVEST-378031-msi-edge-expert-nvme-devices-not-found.md", "expect": "exit_zero", "porque": "Sugerencia de adopcion, no un defecto: lo unico verificable por maquina es que la DECISION quedo registrada. Cerrada, la forma que el modulo comprueba es closure_type + reason (no accepted, que ledger_schema prohibe junto a status: done). El texto anterior describia la forma ABIERTA y quedo falso al cerrarse -- un porque falso no se puede refutar midiendo lo que dice."}
created: 2026-09-09
evidence:
  pass: shared:harvest-decision-registrada
  fail: shared:harvest-decision-registrada
  e2e: shared:harvest-decision-registrada
reason: "void_wontfix: la DECISION registrada ES el entregable de una ficha HARVEST -- no hay fix de codigo que probar. Decidida el 2026-09-09 por the maintainer + Claude, revision de deuda 2026-09-09, con este disparador de reapertura: hardware/escenario distinto -- reabrir si ATOM cambia de configuracion (cluster, rack, otro chip) || Motivo tecnico: Hardware distinto (MSI Edge Expert, no GB10/DGX Spark). Los mecanismos (sonda NVMe en POST, fallback PXE) son ademas firmware pre-boot, no observables desde el SO ya arrancado."
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

- Enlazado NVMe UEFI/BIOS y detección de medio (NVMe Media Presence Check): el firmware realiza una sonda de presencia NVMe en POST y, si falla, pasa a fallback PXE IPv4. — `knowledge/references/forum_nvidia_378031_msi-edge-expert-nvme-devices-not-found.md:7`
- Ruta de diagnóstico NVMe CLI desde entorno Live USB: arranque desde Linux live USB e instalación de herramientas para ejecutar pruebas automáticas e inspección SMART. — `knowledge/references/forum_nvidia_378031_msi-edge-expert-nvme-devices-not-found.md:9`
- Ruteo PXE IPv4 como fallback de boot: cuando el firmware no detecta almacenamiento local arrancable, transfiere el control a la red por PXE IPv4. — `knowledge/references/forum_nvidia_378031_msi-edge-expert-nvme-devices-not-found.md:11`
- Mapeo a proyectos de la flota: el enlazado NVMe mitiga fallos de enumeración en DGX Spark / MSI Edge Expert; el diagnóstico CLI asiste en Liberation Watchdog; y el ruteo PXE actúa como componente de resiliencia en Atlas. — `knowledge/references/forum_nvidia_378031_msi-edge-expert-nvme-devices-not-found.md:15-19`
- Categoría de falla atacada: condición de fallo de enumeración de almacenamiento en firmware que induce desvío no deseado a arranque por red. — `knowledge/references/forum_nvidia_378031_msi-edge-expert-nvme-devices-not-found.md:17`
- Veredicto de producto COS: justificado por la validación de fallos a nivel de firmware/BIOS y con disparador de reevaluación consistente en bajar código de diagnóstico UEFI/NVMe y analizar la implementación en DGX Spark. — `knowledge/references/forum_nvidia_378031_msi-edge-expert-nvme-devices-not-found.md:23-25`

## Por qué se sugiere para blackbox en concreto

El mecanismo de diagnóstico CLI de NVMe (arranque Live USB, inspección SMART) se asigna a 'Liberation Watchdog', nombre falso; ese mecanismo de diagnóstico/telemetría de hardware es exactamente el dominio de blackbox ('monitoreo de hardware, logs, systemd units' de la AI TOP ATOM).

## Procedencia

- Fuente original: https://forums.developer.nvidia.com/t/msi-edge-expert-nvme-devices-not-found/378031
- Dictamen de cosecha, ruta absoluta: `~/projects/Atlas/docs/agent_findings/2026-09-05_cosecha_forum_nvidia_378031_msi-edge-expert-nvme-devices-not-found.md`
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
python -m tools.check_harvest_accepted tasks/done/HARVEST-378031-msi-edge-expert-nvme-devices-not-found.md
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
