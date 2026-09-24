---
id: HARVEST-362964-vllm-100-cpu-usage-when-idle-again
kind: task
title: "Evaluar adopción: mecanismo cosechado por Atlas (362964-vllm-100-cpu-usage-when-idle-again)"
status: done
closure_type: adopted_prior_implementation
closed_at: 2026-09-23
evidence: {"verificado_el_destino": "$ # el close_check de la ficha que lleva el trabajo, corrido el 2026-09-23\n$ grep -q 'red y CPU por nucleo (muestras de blackbox)' bin/bb\nrc=0  (0 = pasa)", "evidencia_del_destino": "Los 3 ficheros de tasks/done/FEATURE-RED-CPU-SCAN.md, comprobados presentes el 2026-09-23: tasks/evidence/FEATURE-RED-CPU-SCAN/e2e.txt, tasks/evidence/FEATURE-RED-CPU-SCAN/fail.txt, tasks/evidence/FEATURE-RED-CPU-SCAN/pass.txt", "limite_declarado": "El close_check de FEATURE-RED-CPU-SCAN.md es un grep sobre su propio texto: comprueba que la ficha diga lo que dice, no que la funcion sirva. Lo que sostiene el cierre son sus ficheros de evidencia, que traen comando, salida y control negativo.", "e2e": "tasks/evidence/FEATURE-RED-CPU-SCAN/e2e.txt", "fail": "tasks/evidence/FEATURE-RED-CPU-SCAN/fail.txt", "pass": "tasks/evidence/FEATURE-RED-CPU-SCAN/pass.txt"}
severity: P3
origin: asserted
satd_family: HARVEST_SUGGESTION
close_check: {"cmd": "python -m tools.check_harvest_accepted tasks/done/HARVEST-362964-vllm-100-cpu-usage-when-idle-again.md", "expect": "exit_zero", "porque": "Sugerencia de adopcion, no un defecto -- verifica que accepted.by/date/trigger este lleno y no sea el placeholder, patron de own_chats/tools/check_harvest_accepted.py (DGX-505)."}
created: 2026-09-09
reason: "CERRADA 2026-09-23 como adopted_prior_implementation. La adopcion de esta sugerencia se implemento con codigo real en un commit ANTERIOR y ese trabajo vive en tasks/done/FEATURE-RED-CPU-SCAN.md, cerrada con su propia evidencia (3 ficheros, los 3 presentes). Esta ficha era la EVALUACION, no el trabajo: su trigger era un puntero a trabajo ya terminado, no una vigilancia, asi que cerrarla no apaga nada. Verificado antes de cerrar: el close_check de FEATURE-RED-CPU-SCAN.md corre y pasa."
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

- Se analiza el mecanismo de busywait en los hilos del servidor que consumen núcleos enteros al estar inactivo — `knowledge/references/forum_nvidia_362964_vllm-100-cpu-usage-when-idle-again.md:"- **Rastreo de hilos (Busywait en hilos de CPU principal)**: El proceso de servidor de vLLM mantiene dos hilos de CPU principales al 100% de ocupación mientras está inactivo, actuando como un bucle de espera activo (busywait) que impide que el CPU entre en estados de idle profundos."`
- Para DGX Spark, el mecanismo ataca la categoría de falla de consumo excesivo de energía y sobrecalentamiento térmico en reposo — `knowledge/references/forum_nvidia_362964_vllm-100-cpu-usage-when-idle-again.md:"- **DGX Spark**: La observación de "2 full CPU cores" se alinea con el perfil de consumo de energía y térmico del DGX Spark; activar el modo de sueño cuando está idling es crítico para mantener la eficiencia energética en hardware de borde/orilla."`
- Para Liberation Watchdog, se aborda la categoría de falla de activación descontrolada de alarmas térmicas y ventiladores — `knowledge/references/forum_nvidia_362964_vllm-100-cpu-usage-when-idle-again.md:"- **Liberation Watchdog**: El informe de "sparks' fans at full blast" indica un fallo de gestión de energía que el Watchdog monitorea; el mecanismo de sueño aborda el disparador de alarma térmica/fan-noise."`
- Para Cuenza, el busywait constante ataca la degradación de latencia de entrada — `knowledge/references/forum_nvidia_362964_vllm-100-cpu-usage-when-idle-again.md:"- **Cuenza**: Para cargas de trabajo de FinTech (validación estructurada JSON/tablas), el busywait constante introduce latencia injusta en los hilos de procesamiento de entrada, haciendo que la variable de entorno sea un requisito previo antes de desplegar pipelines de Cuenta por Pagar."`
- Como mecanismo alternativo de sincronización entre procesos, el PR #28053 sustituye el bucle activo usando ZeroMQ y un socket interno — `knowledge/references/forum_nvidia_362964_vllm-100-cpu-usage-when-idle-again.md:"This PR uses ZMQ to send write notifications which readers can wait for, however it also uses an in-process socket to wake up the reader on shut down so that there's no need to constantly wake up to check for a cancellation flag."`
- El disparador de reevaluación del veredicto está condicionado a versiones upstream o nuevos modelos — `knowledge/references/forum_nvidia_362964_vllm-100-cpu-usage-when-idle-again.md:"**Disparador de reevaluación**: Reevaluar si se introduce un nuevo modelo de lenguaje o se actualiza vLLM a una versión posterior a la 0.7.4.dev183 donde el parche upstream pueda haberse resuelto definitivamente, eliminando la necesidad de la bandera manual."`

## Por qué se sugiere para blackbox en concreto

En '## Hallazgos verificados' el mecanismo de alarmas térmicas/ventiladores descontrolados ('sparks' fans at full blast') se atribuye a 'Liberation Watchdog' (nombre falso) como si fuera quien monitorea esas alarmas; ese es exactamente el dominio declarado de blackbox (telemetría del AI TOP ATOM: monitoreo de hardware, logs, systemd units) sobre el mismo chip GB10.

## Procedencia

- Fuente original: https://forums.developer.nvidia.com/t/vllm-100-cpu-usage-when-idle-again/362964
- Dictamen de cosecha, ruta absoluta: `~/projects/Atlas/docs/agent_findings/2026-09-05_cosecha_forum_nvidia_362964_vllm-100-cpu-usage-when-idle-again.md`
- Corregido el 2026-09-09 (DGX-503): el dictamen original interrogó estos mecanismos sólo contra
  Atlas/aequitas_os porque la lista de flota de Atlas estaba rota (DGX-502) y no consideraba
  a blackbox en absoluto.

## Lo que esta ficha NO decide

No dice que blackbox deba adoptar nada. No mide si el código fuente es
production-ready, tiene licencia compatible, o pasa los propios gates de este repo -- eso lo
evalúa quien trabaje aquí, si decide que vale la pena mirarlo.

## Root Cause

Atlas cosecho un mecanismo de una fuente externa y lo sugirio para blackbox por
dominio. **Nadie de blackbox pidio esta evaluacion** -- es cosecha pasiva, y la
ficha existe para dejar constancia de la DECISION, no para hacer el trabajo.

La decision fue ADOPTAR. El trabajo real se escribio como codigo y vive en
`tasks/done/FEATURE-RED-CPU-SCAN.md`, cerrada por su cuenta y con su propia evidencia. Esta
ficha no tenia codigo que escribir: su entregable era decidir, y decidio.

Por eso el `closure_type` es `adopted_prior_implementation` y no
`void_wontfix` (seria falso: SI se hizo trabajo) ni `duplicate` (no lo es: la
evaluacion y la implementacion son cosas distintas) ni
`relocated_prior_verification` (presupone que esta ficha ya estaba `done` en un
commit anterior, y seguia abierta).

## Regression Test

El de la ficha que lleva el trabajo, que es donde vive el sujeto:

```
grep -q 'red y CPU por nucleo (muestras de blackbox)' bin/bb
```

Corrido el 2026-09-23 antes de cerrar esta: **pasa**. Si esa verificacion
dejara de pasar, la que se reabre es `FEATURE-RED-CPU-SCAN.md` -- ahi esta el codigo --, no esta
evaluacion, que no tiene nada que arreglar.

## Verification Evidence

La de `tasks/done/FEATURE-RED-CPU-SCAN.md`, comprobada presente el 2026-09-23 (3 de 3 ficheros):

- `tasks/evidence/FEATURE-RED-CPU-SCAN/e2e.txt`
- `tasks/evidence/FEATURE-RED-CPU-SCAN/fail.txt`
- `tasks/evidence/FEATURE-RED-CPU-SCAN/pass.txt`

LIMITE DECLARADO: el `close_check` de `FEATURE-RED-CPU-SCAN.md` es un `grep` sobre su propio
texto en la mayoria de estas fichas, o sea que comprueba que la ficha diga lo
que dice, no que la funcion sirva. Lo que sostiene el cierre de verdad son sus
ficheros de evidencia, que traen comando, salida y control negativo. Se dice
en vez de presentar el `grep` como si fuera una prueba funcional.
