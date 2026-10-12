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

## Paso 2 hecho: port y compilacion SIN cargar (2026-10-12, autorizado por Luis)
Agente Opus; verificado por mi: `nvidia.ko` 580.178.04 con `vermagic` 6.17.0-1032-nvidia, sin firma, sha256 `bf817b6b573aed6c...`; importa `dmem_cgroup_register_region/try_charge/uncharge/unregister_region/state_evict_valuable` (el modulo instalado de Canonical importa 0); la constante zero-FB (51302 MiB) aparece en `mem_mgr.o` (3 coincidencias); parche de 16 archivos en `memacct-580.patch`. Tres intentos de compilacion, los dos primeros fallaron y quedaron documentados.
Diferencias con 615: en 580 la condicion es `PDB_PROP_GPU_ZERO_FB` (activa para GB10B, GB20B, GB20C; **580 no lista GB10C**); funciones propias `bbMemmgrGet*`; firma de `dmem_cgroup_register_region` del kernel 6.17 adaptada; avisos de limite suave omitidos; ioctl del modo misc no portadas.
**NO verificado**: que el modulo cargue, registre la region o cobre; que `cudaMalloc` llegue por `vidmemConstruct` con VIDMEM; que este chip active `PDB_PROP_GPU_ZERO_FB`; la constante 51302 MiB es fija. Cargarlo exige firma con la llave MOK (existe, sin enrolar) y reinicio: decision de Luis.
Evidencia: `compilacion.txt`, `modulo-ko.txt`, `control-negativo-zerofb.txt`, `firma-dmem.txt`, `medicion.txt`, `memacct-580.patch`.

## Paso 3 hecho: modulo cargado y medido (2026-10-12, Luis enrolo la MOK y reinicio)
Resuelto POSITIVO: el modulo parcheado carga (firmado, Secure Boot activo), la GPU responde, vLLM y la pantalla siguen. `PDB_PROP_GPU_ZERO_FB` si se activa en este chip y la constante da region: `dmem.capacity = nvidia/0000000F:01:00.0/vidmem 53794045952` (50.1 GiB; antes vacio).
Resuelto NEGATIVO: `cudaMalloc` NO se cobra. `dmem_prueba.sh` rc 4: el control sin tope asigno 256 MiB (`torch.empty(device=cuda)` OK) y `dmem.current` quedo en 0. El unico punto de cobro del parche es `video_mem.c` (RM); la ruta real de `cudaMalloc` en GB10 no pasa por ahi (probable: UVM/sysmem, que no usa `vidmemConstruct`). Evidencia: `medicion-modulo-cargado-20261012.txt`.
Lo que sigue: localizar por que ruta entra la asignacion (trazas o lectura de `nvidia-uvm`, `os_alloc_pages`/`memdescAlloc` ADDR_SYSMEM) y cobrar ahi, o descartar `dmem` como mecanismo de tope y dejar el limitador LD_PRELOAD (ya integrado) como unico. Decision de Luis.
Hallazgos de herramienta (arreglados): `dmem_modulo.sh` comprobaba la llave con `mokutil | grep -q` bajo `pipefail` y `mokutil --test-key` sale 1 si esta enrolada (rechazaba una llave enrolada; `tests/test_dmem_modulo_llave.py`); `dmem_prueba.sh` se callaba cuando root no veia `torch` (site de usuario).
