---
id: FEATURE-1358-CGROUP-02-TRAZA
kind: task
domain: GPU
title: "Identificar el camino de asignación y el propietario del cargo"
status: open
severity: P2
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-10-02
close_check: {"cmd": "python3 -m tools.verify_cgroup_plan --phase 02-traza --evidence tasks/evidence/FEATURE-1358-CGROUP-02-TRAZA", "expect": "exit_zero", "porque": "Verificador específico pendiente: debe evaluar resultados reales y controles negativos descritos en esta ficha, no su mera existencia."}
---
## Alcance de esta ficha en la rama de auditoría

Este registro contiene los complementos del dive NVIDIA. El desarrollo previo de cgroups y trazadores se conserva en la rama de trabajo del otro agente. Verificadores y ejecución del cierre permanecen pendientes en esta rama.


**FEATURE-FORUM-UVM-TRACE-CAPABILITY-01 (delta del foro 357848).** En GB10/SM121 con driver 580.95.05, CUDA 13.1 y Nsight Systems 2026.1.1, un operador no pudo capturar page faults/migraciones UVM y NVIDIA respondió que el perfilado UVM no está soportado en Spark en esa combinación ([357848](https://forums.developer.nvidia.com/t/357848)). Reusar el mapa de traza de esta ficha para anotar capacidad/no-capacidad por versión; no inferir migraciones UVM a partir de memoria host, faults CPU agregados o `nvidia-smi`, ni abrir un probe separado que Blackbox no usa. Una alternativa solo se admite tras soporte del proveedor y una prueba conocida de UVM contra control host.

## Estado de publicación de esta investigación

Propuesta abierta. Los comandos de cierre describen el verificador y evidencia requeridos; esta rama publica investigación y fichas, sin implementación ni resultados de ejecución de los mecanismos propuestos.
