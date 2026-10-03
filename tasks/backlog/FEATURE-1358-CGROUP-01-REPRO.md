---
id: FEATURE-1358-CGROUP-01-REPRO
kind: task
domain: GPU
title: "Reproducir y delimitar el hueco de contabilidad CUDA"
status: open
severity: P2
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-10-02
close_check: {"cmd": "python3 -m tools.verify_cgroup_plan --phase 01-repro --evidence tasks/evidence/FEATURE-1358-CGROUP-01-REPRO", "expect": "exit_zero", "porque": "Verificador específico pendiente: debe evaluar resultados reales y controles negativos descritos en esta ficha, no su mera existencia."}
---
## Alcance de esta ficha en la rama de auditoría

Este registro contiene los complementos del dive NVIDIA. El desarrollo previo de cgroups y trazadores se conserva en la rama de trabajo del otro agente. Verificadores y ejecución del cierre permanecen pendientes en esta rama.

## Índice de propuestas registradas del swarm NVIDIA categoría 721

- **`BB-DASHBOARD-MEMORY-UNIT-CALIBRATION`** — DGX Spark users report that dashboard memory usage disagrees with `free`/`/proc/meminfo`, potentially mixing GiB and GB; one reply says an update fixed it while a later user says the mismatch persists. In a separate report, a vLLM model… Fuente: [350359](https://forums.developer.nvidia.com/t/350359/1).
- **`BB-RAY-UMA-OBJECT-STORE-MONITOR-GATE`** — On a reported TP=3 MiniMax-M3 workload, Ray reserves roughly 30% (~36GB) of per-node RAM for an object store the author says TP does not use; head also loads ~84GB shard plus KV, triggering driver OOM during weight load. After warmup,… Fuente: [373387](https://forums.developer.nvidia.com/t/373387/1).

## Estado de publicación de esta investigación

Propuesta abierta. Los comandos de cierre describen el verificador y evidencia requeridos; esta rama publica investigación y fichas, sin implementación ni resultados de ejecución de los mecanismos propuestos.
