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

## Paso 1 hecho: lectura del codigo 615 (2026-10-12)
Corrige lo que dije antes ("probablemente sysmem, nunca se cobra"):
- `mem_desc.c:1192-1197`: en configuraciones zero-FB, una asignacion `ADDR_FBMEM` se convierte a `ADDR_SYSMEM` ("FB alloc on ZERO_FB config moved to sysmem"). La conversion ocurre en `memdescAlloc`, DESPUES del cobro: `video_mem.c:629` llama `memacctTryCharge` con el atributo `LOCATION_VIDMEM` que pide el cliente, antes de tocar el memdesc. Un `cudaMalloc` que llegue como VIDMEM seria cobrado aunque acabe en sysmem.
- `memacct.c:208-214`: sin region para el gpuId, `memacctTryCharge` devuelve OK sin cobrar (es lo que pasa hoy).
- `memacct.c:456-479`: la region se crea con `size = memmgrGetTotalRamSizeBytes` y `precharge = size - freeSize`, con `freeSize = memmgrGetHeapFreeBytes`; ambas devuelven 0 en zero-FB (`mem_mgr.c:4190` y `:4228`). Parchear SOLO el tamano daria `precharge = size`: toda la region precargada y nada disponible. Hay que parchear las dos funciones con el mismo valor (precharge 0).
Parche minimo hipotetico: dos funciones de `mem_mgr.c` devuelven un valor propio (p. ej. el tope de GPU votado, 50.1 GiB o la RAM total) cuando `bGpuArchIsZeroFb`, sin tocar `memacct.c` ni `video_mem.c`.
Sin confirmar: que `cudaMalloc` en GB10 llegue por `vidmemConstruct` con atributo VIDMEM (el aviso "moved to sysmem" existe porque llegan asignaciones asi, pero no prueba que sean las de CUDA), y que `dmem` cobre con el cgroup del proceso. Solo se confirma con el modulo cargado y trazas `LEVEL_INFO`.
Costo que sigue en pie: portar memacct a 580 (es nuevo desde 610), llave MOK, reinicio, y rehacer el parche en cada actualizacion de driver.
