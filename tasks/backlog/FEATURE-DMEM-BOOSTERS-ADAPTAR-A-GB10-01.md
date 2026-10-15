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

## Avance 2026-10-13: la region dmem ya existe
Lectura de solo lectura: `/sys/fs/cgroup/dmem.capacity` = `nvidia/0000000F:01:00.0/vidmem 53794045952` (50,1 GiB) y `bb gpumem` cobra por region (38,34 GiB de 50,1: contenedor nemotron-server 33,40, user.slice 4,72). La premisa de la ficha ("depende de que la prueba 5 de region") ya se cumple porque el modulo parcheado esta cargado desde el 12-oct 21:57. Sigue abierta porque escribir `dmem.low`/`dmem.max` por cgroup exige root o delegacion del controlador (el cgroup del usuario trae solo memory y pids) y una medicion con el motor en produccion.

## Avance 2026-10-14 (lote 'cierra las pendientes conforme a la opcion recomendada'): espera un disparador, no una decision
Disparador: la ventana del motor de 60 min que anuncia Luis con root de Luis: escribir `dmem.low`/`dmem.max` es escritura en cgroupfs (no cabe en un script de solo lectura), y `user.slice` no delega `dmem` (medido hoy: solo `cpu memory pids`). Paso exacto: con el motor sirviendo, `echo "nvidia/0000000F:01:00.0/vidmem <bytes>" | sudo tee <cgroup del contenedor>/dmem.low`, medir con `bb gpumem` y un control sin la escritura, y escribir `booster_dmem_adaptado` en `medicion.txt`.
