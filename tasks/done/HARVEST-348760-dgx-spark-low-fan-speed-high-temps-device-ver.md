---
id: HARVEST-348760-dgx-spark-low-fan-speed-high-temps-device-ver
kind: task
title: "Evaluar adopción: mecanismo cosechado por Atlas (348760-dgx-spark-low-fan-speed-high-temps-device-very-hot)"
status: done
closure_type: void_wontfix
closed_at: 2026-09-26
severity: P3
origin: asserted
satd_family: HARVEST_SUGGESTION
close_check: {"cmd": "python -m tools.check_harvest_accepted tasks/done/HARVEST-348760-dgx-spark-low-fan-speed-high-temps-device-ver.md", "expect": "exit_zero", "porque": "Sugerencia de adopcion, no un defecto: lo unico verificable por maquina es que la DECISION quedo registrada. Cerrada, la forma que el modulo comprueba es closure_type + reason (no accepted, que ledger_schema prohibe junto a status: done). El texto anterior describia la forma ABIERTA y quedo falso al cerrarse -- un porque falso no se puede refutar midiendo lo que dice."}
created: 2026-09-09
reason: "void_wontfix: la DECISION registrada ES el entregable de una ficha HARVEST -- no hay fix de codigo que probar. Decidida el 2026-09-09 por the maintainer + Claude, revision de deuda 2026-09-09, con este disparador de reapertura: revisado a fondo (codigo + fuente citada) y sin valor incremental hoy -- reabrir si aparece un caso real medido en esta maquina que lo contradiga || Motivo tecnico: Mitigacion activa (SIGKILL por umbral termico de 92C, descarga de modelos inactivos) -- dominio de Atlas (liberation_watchdog/memory_cgroup), no de un instrumento forense post-hoc. Sin parte diagnostica separable."
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

- PASO 1 (Mecanismos): El primer mecanismo documentado es el control de ventiladores por firmware exclusivo sin PWM ni BMC (`Fans are controlled entirely by firmware. No PWM no BMC control posible.`), lo que hace que la velocidad dependa enteramente de la lógica embebida en la placa base y no del sistema operativo o herramientas estándar. — `knowledge/references/forum_nvidia_348760_dgx-spark-low-fan-speed-high-temps-device-very-hot.md:136`
- PASO 1 (Mecanismos): El segundo mecanismo es un perro guardián térmico en espacio de usuario (`thermal_watchdog.py`) que sondea periódicamente `/sys/class/thermal/thermal_zone*/temp` y `nvidia-smi`, aplicando un `SIGKILL` a los procesos cuyo patrón coincida cuando se supera un umbral de corte (por defecto 92 °C). — `knowledge/references/forum_nvidia_348760_dgx-spark-low-fan-speed-high-temps-device-very-hot.md:961-975`
- PASO 1 (Mecanismos): El tercer mecanismo es la mitigación de presión térmica mediante la descarga de modelos inactivos en memoria unificada LPDDR, liberando espacio para reducir el consumo continuo de energía por refresco y ganando margen térmico sin alterar la curva de ventiladores. — `knowledge/references/forum_nvidia_348760_dgx-spark-low-fan-speed-high-temps-device-very-hot.md:934-942`
- PASO 2 (Interrogatorio - Falla que ataca): Para el perro guardián térmico y el colapso por saturación de swap, ataca la categoría de falla conocida de "agotamiento de memoria unificada" y "bloqueo por degradación térmica / lockup", evitando que el sistema quede inoperable y requiera apagado manual. — `knowledge/references/forum_nvidia_348760_dgx-spark-low-fan-speed-high-temps-device-very-hot.md:180-184`
- PASO 2 (Interrogatorio - Escala): El mecanismo de watchdog pasa de requerir telemetría externa o servicios distribuidos complejos a un script monolítico de Python estándar sin dependencias externas que lee zonas de `/sys`. — `knowledge/references/forum_nvidia_348760_dgx-spark-low-fan-speed-high-temps-device-very-hot.md:976-978`
- PASO 2 (Interrogatorio - Algo que ya hacemos sin nombre): Da nombre de "higiene de VRAM" (VRAM hygiene) y acoplamiento térmico CPU-GPU bajo un mismo disipador a lo que empíricamente se gestionaba cerrando contenedores huérfanos. — `knowledge/references/forum_nvidia_348760_dgx-spark-low-fan-speed-high-temps-device-very-hot.md:930-932`
- PASO 3 (Veredicto y disparador): Se declara veredicto COS debido a que la cosecha de mitigaciones térmicas y scripts watchdog es viable para operar el hardware mientras persisten defectos de firmware, con disparador de reevaluación fijado en un parche de firmware o actualización de BIOS que exponga el control manual/PWM de los ventiladores. — `knowledge/references/forum_nvidia_348760_dgx-spark-low-fan-speed-high-temps-device-very-hot.md:20`

## Por qué se sugiere para blackbox en concreto

Ningún satélite real se nombra en el interrogatorio; el mecanismo es literalmente un daemon en espacio de usuario que sondea `/sys/class/thermal` y `nvidia-smi` y aplica SIGKILL por umbral -- coincide casi textual con la misión de blackbox ('telemetria de la AI TOP ATOM (NVIDIA GB10): monitoreo de hardware, logs, systemd units'), nunca considerado por no estar en la lista rota de 5.

## Procedencia

- Fuente original: https://forums.developer.nvidia.com/t/dgx-spark-low-fan-speed-high-temps-device-very-hot/348760
- Dictamen de cosecha, ruta absoluta: `~/projects/Atlas/docs/agent_findings/2026-09-05_cosecha_forum_nvidia_348760_dgx-spark-low-fan-speed-high-temps-device-very-hot.md`
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
python -m tools.check_harvest_accepted tasks/done/HARVEST-348760-dgx-spark-low-fan-speed-high-temps-device-ver.md
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
