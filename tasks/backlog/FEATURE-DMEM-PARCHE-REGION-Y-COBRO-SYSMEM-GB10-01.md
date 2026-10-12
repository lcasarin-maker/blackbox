---
id: FEATURE-DMEM-PARCHE-REGION-Y-COBRO-SYSMEM-GB10-01
kind: task
domain: GPU
title: "Parchear memacct para dar tamano a la region dmem de GB10 y cobrar asignaciones sysmem"
status: open
severity: P3
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-10-12
close_check: {"cmd": "grep -q parche_dmem_gb10_medido tasks/evidence/FEATURE-DMEM-PARCHE-REGION-Y-COBRO-SYSMEM-GB10-01/medicion.txt", "expect": "exit_zero", "porque": "Pregunta de Luis 2026-10-12: 'podemos cambiar el tamano?'. Cierra con una medicion de que ruta toman las asignaciones de GB10 (vidmem o sysmem) y, si procede, un parche probado con control negativo que haga que dmem.capacity no este vacio y que una asignacion sobre dmem.max falle; o con la prueba de que no es viable."}
---

## Por que existe
En el codigo 615, `memmgrGetTotalRamSizeBytes` devuelve 0 para chips zero-FB (GB10B/C) y `memacct` ignora la region de tamano 0. `memacctTryCharge` solo corre para `LOCATION_VIDMEM` (`video_mem.c:629`). Cambiar solo el tamano no cobra nada si las asignaciones de GB10 son sysmem.

## Plan por partes
1. Antes de cualquier parche: leer en 615 que ruta toma una asignacion CUDA en un chip zero-FB (sysmem/`memdesc` vs `video_mem.c`).
2. Si es sysmem: disenar el cobro en esa ruta y el tamano de la region (RAM del sistema o un valor propio).
3. Probar solo en modulos propios bajo FEATURE-DMEM-BACKPORT-MEMACCT-580-REVERSIBLE-01 (llave MOK; decision de Luis pendiente).
4. Costo declarado: parche mantenido a mano en cada actualizacion de driver; riesgo de fallos de asignacion en vLLM.
