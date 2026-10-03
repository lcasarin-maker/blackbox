---
id: FEATURE-MEMORYSAVER-02-TRAZADOR
kind: task
domain: GPU
title: "Adaptar trazador de cargos kernel con atribución a cgroup"
status: open
severity: P2
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-10-02
close_check: {"cmd": "python3 -m tools.verify_memory_saver --phase 02-trazador --evidence tasks/evidence/FEATURE-MEMORYSAVER-02-TRAZADOR", "expect": "exit_zero", "porque": "Verificación específica pendiente: ejecutar el sujeto y sus controles, no comprobar solo que el informe exista."}
---
## Alcance de esta ficha en la rama de auditoría

Este registro contiene los complementos del dive NVIDIA. El desarrollo previo de cgroups y trazadores se conserva en la rama de trabajo del otro agente. Verificadores y ejecución del cierre permanecen pendientes en esta rama.

## Índice de propuestas registradas del swarm NVIDIA categoría 721

- **`BB-UMA-GPU-ALLOCATABLE-HEADROOM-SEMANTICS`** — On GB10 UMA, general system allocations reduce the pool available for GPU allocation. Forum users say nvtop displays GPU memory but excludes CPU allocations, while some released versions fail on Spark. This can hide reduced… Fuente: [351284](https://forums.developer.nvidia.com/t/nvtop-with-dgx-spark-unified-memory-support/351284/1).

## Estado de publicación de esta investigación

Propuesta abierta. Los comandos de cierre describen el verificador y evidencia requeridos; esta rama publica investigación y fichas, sin implementación ni resultados de ejecución de los mecanismos propuestos.
