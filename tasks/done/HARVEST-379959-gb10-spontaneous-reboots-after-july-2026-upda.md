---
id: HARVEST-379959-gb10-spontaneous-reboots-after-july-2026-upda
kind: task
title: "Evaluar adopción: mecanismo cosechado por Atlas (379959-gb10-spontaneous-reboots-after-july-2026-update-gsp-health-chec)"
status: done
closure_type: adopted_prior_implementation
closed_at: 2026-09-23
evidence: {"verificado_el_destino": "$ # el close_check de la ficha que lleva el trabajo, corrido el 2026-09-23\n$ grep -q 'Xid' tasks/done/FEATURE-GPU-XID-DETECTION.md\nrc=0  (0 = pasa)", "evidencia_del_destino": "Los 3 ficheros de tasks/done/FEATURE-GPU-XID-DETECTION.md, comprobados presentes el 2026-09-23: tasks/evidence/FEATURE-GPU-XID-DETECTION/e2e.txt, tasks/evidence/FEATURE-GPU-XID-DETECTION/fail.txt, tasks/evidence/FEATURE-GPU-XID-DETECTION/pass.txt", "limite_declarado": "El close_check de FEATURE-GPU-XID-DETECTION.md es un grep sobre su propio texto: comprueba que la ficha diga lo que dice, no que la funcion sirva. Lo que sostiene el cierre son sus ficheros de evidencia, que traen comando, salida y control negativo.", "e2e": "tasks/evidence/FEATURE-GPU-XID-DETECTION/e2e.txt", "fail": "tasks/evidence/FEATURE-GPU-XID-DETECTION/fail.txt", "pass": "tasks/evidence/FEATURE-GPU-XID-DETECTION/pass.txt"}
severity: P3
origin: asserted
satd_family: HARVEST_SUGGESTION
close_check: {"cmd": "python -m tools.check_harvest_accepted tasks/done/HARVEST-379959-gb10-spontaneous-reboots-after-july-2026-upda.md", "expect": "exit_zero", "porque": "Sugerencia de adopcion, no un defecto -- verifica que accepted.by/date/trigger este lleno y no sea el placeholder, patron de own_chats/tools/check_harvest_accepted.py (DGX-505)."}
created: 2026-09-09
reason: "CERRADA 2026-09-23 como adopted_prior_implementation. La adopcion de esta sugerencia se implemento con codigo real en un commit ANTERIOR y ese trabajo vive en tasks/done/FEATURE-GPU-XID-DETECTION.md, cerrada con su propia evidencia (3 ficheros, los 3 presentes). Esta ficha era la EVALUACION, no el trabajo: su trigger era un puntero a trabajo ya terminado, no una vigilancia, asi que cerrarla no apaga nada. Verificado antes de cerrar: el close_check de FEATURE-GPU-XID-DETECTION.md corre y pasa."
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

- Mecanismo 2 (Polling de RPC y watchdog de salud GSP): algoritmo de consulta periódica de salud entre el kernel y el coprocesador GSP (`kgspHealthCheck_TU102`), donde `rpcRecvPoll` aborta tras un timeout preconfigurado (por ejemplo 4000 ms) retornando el estado de error `0x00000062` y arrojando excepciones Xid 119/120 para aislar fallas del microcódigo — `knowledge/references/forum_nvidia_379959_gb10-spontaneous-reboots-after-july-2026-update-gsp-health-check-fail-nvrm-asser.md:"rpcRecvPoll failed with status 0x00000062 for fn 76 sequence 5742!"`
- Mecanismo 3 (Reinicio por pánico forzado vía hardware watchdog): el módulo `sbsa_gwdt` opera configurado con el parámetro `options sbsa_gwdt action=1`, provocando intencionalmente un pánico en el kernel Linux tras recibir la interrupción `WS0` para forzar la recuperación automática de un nodo desatendido ante bloqueos del controlador gráfico — `knowledge/references/forum_nvidia_379959_gb10-spontaneous-reboots-after-july-2026-update-gsp-health-check-fail-nvrm-asser.md:"options sbsa_gwdt action=1"`
- Mecanismo 4 (Pipeline de actualización y ciclo de energía AC en frío): la aplicación de cápsulas EC/UEFI mediante `fwupd` o paquetes adyacentes al firmware requiere un corte total de energía de corriente alterna (AC power disconnect) para purgar el estado residual de controladores embebidos que no resetean en arranques tibios (warm reboot) — `knowledge/references/forum_nvidia_379959_gb10-spontaneous-reboots-after-july-2026-update-gsp-health-check-fail-nvrm-asser.md:"EC/SBIOS capsule updates via fwupd require a full AC power disconnect to fully activate"`
- Paso 2 (Interrogatorio - Falla conocida atacada): ataca la categoría de falla conocida de "inconsistencia de estado de firmware tras reinicio tibio / colapso de comunicación interprocesador (GSP timeout) que activa pánico de watchdog de hardware", mapeada a nivel de flota a DGX Spark y Atlas — `knowledge/references/forum_nvidia_379959_gb10-spontaneous-reboots-after-july-2026-update-gsp-health-check-fail-nvrm-asser.md:"La actualización de capas EC/UEFI por fwupd modifica el firmware de bajo nivel del DGX Spark, introduciendo una ventana de inconsistencia que dispara los reboots espontáneos."`
- Paso 2 (Interrogatorio - Escala y prácticas existentes): traslada el requerimiento de orquestación de firmware de nivel nodo/datacenter a un procedimiento operativo estándar de reseteo eléctrico completo en hardware local, formalizando el comportamiento implícito de recuperación mediante reinicios periódicos inducidos por watchdog — `knowledge/references/forum_nvidia_379959_gb10-spontaneous-reboots-after-july-2026-update-gsp-health-check-fail-nvrm-asser.md:"on GB10, after ANY update batch that touches firmware or the GPU stack — fwupd EC/SBIOS capsules or apt updates like linux-firmware and nvidia components — do a full AC disconnect before trusting the box."`

## Por qué se sugiere para blackbox en concreto

Los mecanismos (polling de salud GSP/RPC con Xid 119/120, watchdog de hardware sbsa_gwdt que fuerza pánico, pipeline de actualización de firmware EC/UEFI con corte de AC) son monitoreo y recuperación de hardware/firmware -- dominio central de blackbox -- pero el interrogatorio solo mapeó a 'DGX Spark y Atlas'.

## Procedencia

- Fuente original: https://forums.developer.nvidia.com/t/gb10-spontaneous-reboots-after-july-2026-update-gsp-health-check-fail-nvrm-assert-flood-gpu-user-shared-data-c-373/379959
- Dictamen de cosecha, ruta absoluta: `~/projects/Atlas/docs/agent_findings/2026-09-05_cosecha_forum_nvidia_379959_gb10-spontaneous-reboots-after-july-2026-update-gsp-health-check-fail-nvrm-asser.md`
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
`tasks/done/FEATURE-GPU-XID-DETECTION.md`, cerrada por su cuenta y con su propia evidencia. Esta
ficha no tenia codigo que escribir: su entregable era decidir, y decidio.

Por eso el `closure_type` es `adopted_prior_implementation` y no
`void_wontfix` (seria falso: SI se hizo trabajo) ni `duplicate` (no lo es: la
evaluacion y la implementacion son cosas distintas) ni
`relocated_prior_verification` (presupone que esta ficha ya estaba `done` en un
commit anterior, y seguia abierta).

## Regression Test

El de la ficha que lleva el trabajo, que es donde vive el sujeto:

```
grep -q 'Xid' tasks/done/FEATURE-GPU-XID-DETECTION.md
```

Corrido el 2026-09-23 antes de cerrar esta: **pasa**. Si esa verificacion
dejara de pasar, la que se reabre es `FEATURE-GPU-XID-DETECTION.md` -- ahi esta el codigo --, no esta
evaluacion, que no tiene nada que arreglar.

## Verification Evidence

La de `tasks/done/FEATURE-GPU-XID-DETECTION.md`, comprobada presente el 2026-09-23 (3 de 3 ficheros):

- `tasks/evidence/FEATURE-GPU-XID-DETECTION/e2e.txt`
- `tasks/evidence/FEATURE-GPU-XID-DETECTION/fail.txt`
- `tasks/evidence/FEATURE-GPU-XID-DETECTION/pass.txt`

LIMITE DECLARADO: el `close_check` de `FEATURE-GPU-XID-DETECTION.md` es un `grep` sobre su propio
texto en la mayoria de estas fichas, o sea que comprueba que la ficha diga lo
que dice, no que la funcion sirva. Lo que sostiene el cierre de verdad son sus
ficheros de evidencia, que traen comando, salida y control negativo. Se dice
en vez de presentar el `grep` como si fuera una prueba funcional.
