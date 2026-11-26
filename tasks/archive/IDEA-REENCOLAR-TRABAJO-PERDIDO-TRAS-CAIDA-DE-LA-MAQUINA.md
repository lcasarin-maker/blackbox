---
id: IDEA-REENCOLAR-TRABAJO-PERDIDO-TRAS-CAIDA-DE-LA-MAQUINA
kind: task
title: "Reencolar automáticamente los trabajos que una caída o un OOM dejó sin terminar, con el diagnóstico de la falla en el mismo registro"
status: discarded
severity: P3
origin: asserted
satd_family: MISSING_CAPABILITY
close_check: {"cmd": "python3 -m tools.inventario --check", "expect": "exit_zero", "porque": "Descartada en blackbox por frontera de dominio: el reencolado de trabajos pertenece al despachador del consumidor externo, no al monitor de máquina."}
created: 2026-11-10
---

## Contexto

Descartada en `blackbox` por frontera de responsabilidades: `blackbox` sólo vigila y registra las caídas de la máquina; la cola de trabajos y su reencolado idempotente pertenecen al despachador del consumidor externo, donde la ficha fue abierta.
