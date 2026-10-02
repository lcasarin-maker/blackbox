---
id: FEATURE-1358-CGROUP-05-CUELGUES
kind: task
domain: GPU
title: "Medir por separado contención y efecto sobre los cuelgues de 1358"
status: open
severity: P2
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-10-02
close_check: {"cmd": "python3 -m tools.verify_cgroup_plan --phase 05-cuelgues --evidence tasks/evidence/FEATURE-1358-CGROUP-05-CUELGUES", "expect": "exit_zero", "porque": "Verificador específico pendiente: debe evaluar resultados reales y controles negativos descritos en esta ficha, no su mera existencia."}
---

## Contexto y dependencias

Plan derivado de [la corrección del README](../../README.md#a-measured-cgroup-accounting-gap-on-this-gb10-stack) y [el informe histórico corregido](../evidence/nvidia-1358-comment.md). Fuente de colaboración: [NVIDIA #1358](https://github.com/NVIDIA/open-gpu-kernel-modules/issues/1358).

Dependencias: FEATURE-1358-CGROUP-03-NATIVO.

## Alcance

Usar la solución nativa evaluada en 03 o, cuando exista, el parche de 04. Preparar comparación de carga acotada con versiones, configuración, clocks, watchdogs y ventanas de observación fijados. Reutilizar muestras, PSI, NVRM, sonda de servicio y exportación externa de Blackbox.

Separar rechazo controlado de asignaciones de pérdida de servicio o cuelgue del host. Conservar timestamps del primer error, última respuesta útil, watchdog y reinicio. Incluir controles sanos y reportar todos los ensayos y fallos de colección. Preparar un paquete reproducible para colaboración en #1358.

## Criterio de cierre

Resultados con exposición y número de ensayos literales, capturas y controles sanos; hipótesis causal limitada a lo observado. Una ventana sin cuelgues se informa como ventana observada. Contención demostrada puede coexistir con cuelgues pendientes de explicación. El análisis y el post para copiar deben conservar esa distinción; publicar el post es una acción separada.

El comando close_check queda especificado para su implementación con el trabajo. Hoy el verificador y sus evidencias están pendientes; esta ficha registra el plan, no resultados ejecutados. Debe rechazar evidencias ausentes y datos fabricados, y tener un control negativo que pruebe que detecta el defecto de su sujeto.

## Avance del swarm — 2026-10-02

Coordinador: Codex. Protocolo A/B y borrador de colaboración preparados en
`tasks/evidence/FEATURE-1358-CGROUP-05-CUELGUES/`. La captura literal
`host-controls.txt` registra driver 580.178.04, PSI actual, bb-usable activo
con WatchdogUSec=6min y RuntimeWatchdogUSec=1min. El control negativo del
analizador devolvió rc=2 con dos fuentes faltantes. Suite existente de hitos:
`python3 -m pytest -q tests/test_1358_hitos_nvrm.py`: 28 passed.

Ensayos A/B ejecutados: 0. Solución candidata evaluada en el host: pendiente.
Exposición comparativa: 0 segundos. Pendientes de ejecución: pila candidata,
rechazo por límite, compartición, liberación y respuesta útil durante el ensayo.
La ficha conserva status open hasta observar estos sujetos reales.

## Caso adicional del dive NVIDIA

[352339](https://forums.developer.nvidia.com/t/352339) reúne autores que reportan freeze total al agotar RAM unificada/swap; un anuncio de580.159.03 como fix tuvo dos respuestas con reproducción persistente. EarlyOOM -m2 es workaround reportado, sin validación BB. Usar este caso para prueba ya prevista de presión RAM y CUDA combinadas, cargada al cgroup frente a memoria GPU, SSH/desktop y recuperación. No adoptar umbral universal ni confundir proceso OOM con host congelado; conservar versión/OEM y resultados positivos/negativos.

[366287](https://forums.developer.nvidia.com/t/366287) adds a long-duration host-pressure case: after roughly 60 hours of Qwen/HF plus Ollama use, the author corrected an initial attribution to `snapd` after observing UMA swap thrash. The summary came from Copilot and the binary logs were not read, so process attribution is unverified. NVIDIA states `snapd` is supported/required in the thread. Treat this as a memory pressure/lifecycle reproduction candidate; capture PSI, swap, cgroup and process state over the long soak, and do not purge/disable snapd as a remedy.

[376882](https://forums.developer.nvidia.com/t/total-host-freeze-not-process-hang-during-multi-node-tp-2-vllm-prefill-on-2x-dgx-spark-gb10-zero-forensic-trace-across-kdump-watchdogs-netconsole/376882) reports five total host freezes in two days on a 2×GB10 TP2 prefill workload after an initial memory-floor fix; no ping/SSH/display, OOM, Xid, panic, kdump vmcore or netconsole packet arrived. After replacing both units, passing FieldDiag, and separately capping vLLM at 90GB, the owner reports two days without a repeat; those changes are confounded. A reply alleges a FlashInfer sparse-MLA livelock and a memdesc leak in driver 580.159.03 and earlier; it cites an external RFC/evidence repo and proposes GPU utilization/power and `0x00000051` as discriminators. Archive attachments remain unread, and none of these causes is confirmed for the reporting nodes. Add an exact-stack repro matrix with GPU power/utilization, memory traffic, per-rank NCCL progress, memory descriptor count, FieldDiag and off-host freshness; a quiet receiver or passing generic diagnostic must remain unknown for an unobserved failure. Do not adopt the external kernel patch or memory cap without an A/B and rollback.

[364886](https://forums.developer.nvidia.com/t/memory-creep-on-dgx-spark-where-your-128-gb-actually-goes-and-how-to-stop-it/364886) supplies an LLM-assisted, single-owner memory profile for driver 580.142/vLLM 0.18.1rc1: author claims `/proc/meminfo` showed 117GB default usage and 32GB after lowering KV-cache budget/eager mode and using prebuilt SM121 wheels. The thread also recommends global `drop_caches`, changing the boot target and sysctls. Treat profile measurements as unverified until repeated with the exact container/model; evaluate only workload-local admission knobs here, never apply global cache/desktop/sysctl recipes from a forum post.

[377334](https://forums.developer.nvidia.com/t/flashinfer-sparse-mla-mbarrier-livelock-on-gb10-root-cause-evidence-and-validated-workaround/377334) is a cross-reference for distinguishing host-wide GPU-kernel wedge from memory-pressure/process failure: the owner reports cold-prefill rank GPU spinning in a kernel while every host thread waits in `cuLaunchKernel`; published reports show high GPU utilization but zero memory traffic. This is unverified by BB and the evidence pack’s raw logs were not inspected. Reuse the existing long-run capture to distinguish process/cgroup pressure, GPU progress and host/SSH health before restarting; cgroup limits alone are not a proven recovery for a wedged GPU kernel.
