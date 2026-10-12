---
id: FEATURE-DMEM-LLENAR-CAPACIDAD-GPU-01
kind: task
domain: GPU
title: "Registrar la memoria GPU/UMA en el controlador dmem de cgroup (modulo propio y parche del driver)"
status: open
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
