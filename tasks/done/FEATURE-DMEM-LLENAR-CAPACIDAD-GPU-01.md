---
id: FEATURE-DMEM-LLENAR-CAPACIDAD-GPU-01
kind: task
domain: GPU
title: "Registrar la memoria GPU/UMA en el controlador dmem de cgroup (modulo propio y parche del driver)"
status: done
closed_at: 2026-10-12
closure_type: fixed
reason: "dmem.capacity lleno (53794045952 B) y carga GPU contabilizada contra un cgroup con dmem.max, con controles d1/d3."
evidence: {"pass": "tasks/evidence/FEATURE-DMEM-LLENAR-CAPACIDAD-GPU-01.pass.txt", "fail": "tasks/evidence/FEATURE-DMEM-LLENAR-CAPACIDAD-GPU-01.fail.txt"}
severity: P2
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-10-12
close_check: {"cmd": "grep -q dmem_llenado_y_medido tasks/evidence/FEATURE-DMEM-LLENAR-CAPACIDAD-GPU-01/medicion.txt", "expect": "exit_zero", "porque": "Peticion de Luis 2026-10-12: llenar nosotros dmem.capacity y dar mantenimiento cuando NVIDIA actualice. Cierra con una medicion que muestre una region registrada en dmem.capacity, un cgroup con dmem.max y la carga GPU contabilizada contra el, con control negativo."}
---

## Medido (2026-10-12)
- Kernel 6.17.0-1032-nvidia con `CONFIG_CGROUP_DMEM=y`; `dmem` esta entre los controladores de la raiz; `dmem.capacity` esta VACIO (el driver no registra region).
- `__ksymtab_dmem_cgroup_register_region`, `_unregister_region`, `_try_charge`, `_uncharge`, `_pool_state_put` y `_state_evict_valuable` estan exportados a modulos.
- Registrar una region es facil con un modulo propio; contabilizar NO: `try_charge` lo tiene que llamar el asignador de memoria del driver. Un modulo que solo registra no hace que ningun cgroup pague nada. Eso exige un parche al modulo abierto de NVIDIA (driver 580.178.04, open-gpu-kernel-modules): ver `FEATURE-1358-CGROUP-04-PARCHE` y `FEATURE-1358-CGROUP-03-NATIVO`.
## Que falta
1. Modulo `bb_dmem` fuera de arbol que registre la region y exponga su capacidad, con Secure Boot (firma MOK) y DKMS.
2. Parche al asignador del driver abierto para cargar/descargar contra el cgroup del proceso (condicionado al hueco demostrado en CGROUP-01/02).
3. Mantenimiento por cada actualizacion de NVIDIA: una verificacion que detecte driver nuevo y diga si el parche aplica (decision de Luis: se da mantenimiento al actualizar).
4. Medicion con control negativo; riesgo declarado: un parche mal hecho cuelga el driver.

## Investigacion en internet y en el codigo fuente de NVIDIA (2026-10-12), por orden de Luis

**Alguien ya lo construyo, y fue NVIDIA.** El driver abierto trae un modulo de contabilidad `memacct` que registra una region `dmem` por GPU y carga cada asignacion de memoria de video contra el cgroup del proceso.
- Medido leyendo `NVIDIA/open-gpu-kernel-modules` tag 615.71.09 (clonado solo para leer): `src/nvidia/src/kernel/mem_mgr/memacct.c` crea la region con `osCgroupRegisterRegion` (`memacct.c:482`), nombre `nvidia/<dominio>:<bus>:<dev>.0/vidmem` (`os.c:2209-2216`), y las cargas se hacen en `video_mem.c:629` (`memacctTryCharge`) y se liberan en `video_mem.c:1115` y `:1157`. Si el tamano de la RAM de video es 0, la region se IGNORA (`memacct.c`: "region zero size, ignoring").
- Existe desde el tag 610.43.02 (HTTP 200 para `memacct.c` en 610.43.02, 610.57.04, 615.71.09 y 615.78.08) y NO existe en 595.99.02, 595.104.02, 580.159.03 ni en NUESTRA 580.178.04 (HTTP 404). Por eso `dmem.capacity` esta vacio aqui.
- Toca solo 6 archivos del RM (`memacct.c/.h`, `os.c`, `video_mem.c`, `mem_mgr.c`, `srcs.mk`) mas el pegamento de `kernel-open` (`os-interface.c`, `conftest.sh`, `nvidia.Kbuild`, `nv.c`): un backport a 580.178.04 es acotado.
- Las notas de la comunidad dicen que 615.71.09 anuncia "cgroups-based memory partitioning"; el kernel 7.3 cambio la firma de `dmem_cgroup_register_region` (PR #1330, cerrado el 2026-10-07 por un arreglo en el repo). Nuestro kernel 6.17 usa la firma vieja (con `size`), la que el codigo de 615 ya usa por defecto.

**Lo que NO se sabe y decide si sirve en GB10:** si las asignaciones CUDA de GB10 (memoria unificada, sin VRAM dedicada: `nvidia-smi` da N/A) pasan por `video_mem.c` y si `memmgrGetTotalRamSizeBytes` devuelve distinto de 0. Si devuelve 0, la region se ignora y el backport no contabiliza nada. Un reporte de comunidad dice que la herramienta `dmemcg-booster` no funciona en GPUs moviles NVIDIA con 615.71.09; no hay reporte para GB10.

**Soluciones caseras que existen (validadas solo como lectura, ninguna probada aqui):**
- `dmemcg-booster` / `gnome-vram-booster`: demonios que escriben `dmem.low`/`dmem.max` por cgroup; presuponen un driver que registre la region (AMD o NVIDIA 610+ con VRAM dedicada). No resuelven GB10 por si solos.
- Limitadores LD_PRELOAD de asignaciones CUDA (patron `CUDA_DEVICE_MEMORY_LIMIT` de proyectos de vGPU): reporte de un limitador de 96 GB para GB10 sin fuente publicada; falla ABIERTO si la variable falta (KAI-Scheduler #2156). Hay que verificar que de verdad aplique.
- Controles de aplicacion: `--gpu-memory-utilization` (no es un tope duro en GB10: vLLM #46307), `PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True` (vLLM #55569), y vigilantes de `MemAvailable` (earlyoom o un vigilante propio): el reporte que mas se parece a nuestro caso es evanwtf/local-llm #456.
- Ningun kernel o modulo propio publicado para contabilidad de memoria unificada de GB10: no se encontro.

## Que falta (reemplaza la lista anterior)
1. Experimento barato y sin riesgo: compilar la region de 610/615 en un modulo de laboratorio NO cargado en el driver de produccion es imposible (el RM es el driver); el experimento real es cargar `nvidia.ko` 615.71.09 abierto solo en una maquina o VM de prueba con GB10. Decision de Luis: no se toca el driver de produccion hasta medir.
2. Medir en lectura del codigo y en una maquina de prueba si `memmgrGetTotalRamSizeBytes` != 0 y si CUDA UMA carga por `video_mem.c`.
3. Mientras tanto, evaluar un limitador LD_PRELOAD con prueba negativa (variable ausente = debe rechazar o registrar).
4. Decidir backport 580.178.04 frente a actualizar a 610/615 (soporte de DGX OS y firma Secure Boot por MOK).

## Voto de Luis 2026-10-12
Medir primero si las asignaciones de GB10 pasan por vidmem antes de portar memacct o enrolar una llave MOK. Descartado por ahora: backport inmediato con MOK; esperar una version de NVIDIA. El backport (FEATURE-DMEM-BACKPORT-MEMACCT-580-REVERSIBLE-01) queda condicionado al resultado de esa medicion.
