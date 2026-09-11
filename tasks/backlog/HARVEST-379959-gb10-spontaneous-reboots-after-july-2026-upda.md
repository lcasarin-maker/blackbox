---
id: HARVEST-379959-gb10-spontaneous-reboots-after-july-2026-upda
kind: task
title: "Evaluar adopción: mecanismo cosechado por Atlas (379959-gb10-spontaneous-reboots-after-july-2026-update-gsp-health-chec)"
status: open
severity: P3
origin: asserted
satd_family: HARVEST_SUGGESTION
close_check: {"cmd": "python -m tools.check_harvest_accepted tasks/backlog/HARVEST-379959-gb10-spontaneous-reboots-after-july-2026-upda.md", "expect": "exit_zero", "porque": "Sugerencia de adopcion, no un defecto -- verifica que accepted.by/date/trigger este lleno y no sea el placeholder, patron de own_chats/tools/check_harvest_accepted.py (DGX-505)."}
created: 2026-09-09
accepted: {"by": "the maintainer + Claude, revision de deuda 2026-09-09", "date": "2026-09-09", "trigger": "adoptado -- el trabajo real vive en tasks/backlog/FEATURE-GPU-XID-DETECTION.md, no en esta ficha de evaluacion"}
reason: "Deteccion de eventos Xid (ej. 119/120 por timeout de RPC del GSP) via dmesg/journalctl es una señal real ausente de bb scan hoy. El watchdog sbsa_gwdt que fuerza panic es mitigacion/procedimiento, no parte de esta adopcion. Se consolida en FEATURE-GPU-XID-DETECTION."
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
