---
id: FEATURE-DMEM-BOOSTERS-ADAPTAR-A-GB10-01
kind: task
domain: GPU
title: "Adaptar la idea de dmemcg-booster (dmem.low/max por cgroup) al portero cuando exista la region dmem"
status: open
severity: P3
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-10-12
close_check: {"cmd": "grep -q booster_dmem_adaptado tasks/evidence/FEATURE-DMEM-BOOSTERS-ADAPTAR-A-GB10-01/medicion.txt", "expect": "exit_zero", "porque": "Voto de Luis 2026-10-12. Cierra cuando exista una region dmem en esta maquina (ver el backport) y el portero escriba dmem.low/dmem.max por cgroup con prueba y control negativo; hasta entonces es solo estudio."}
---

## Antecedentes (lectura)
`DistrictD64/dmemcg-booster` (demonio en C que escribe `dmem.capacity` en `dmem.low` por unidades de systemd) y `gnome-vram-booster` (prioridad para la ventana enfocada) presuponen un driver con region dmem (AMD o NVIDIA 610+ con VRAM dedicada). Un reporte indica que no funciona con GPUs moviles NVIDIA en 615.71.09.
## Plan
Depende de `FEATURE-DMEM-BACKPORT-MEMACCT-580-REVERSIBLE-01`. Cosechar su logica con atribucion y licencia; sin region no hay nada que escribir.
