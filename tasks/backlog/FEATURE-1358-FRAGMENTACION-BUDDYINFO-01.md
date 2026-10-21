---
id: FEATURE-1358-FRAGMENTACION-BUDDYINFO-01
kind: task
domain: GPU
title: "Muestrear fragmentación de memoria (buddyinfo, pagetypeinfo) para contrastar la hipótesis de MiaAI-Lab#23 con los cuelgues de 1358"
status: open
severity: P3
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-10-20
close_check: {"cmd": "grep -q buddyinfo_muestreado tasks/evidence/FEATURE-1358-FRAGMENTACION-BUDDYINFO-01/medicion.txt", "expect": "exit_zero", "porque": "Cierra cuando Blackbox registre órdenes 8+ y 10+ de /proc/buddyinfo y la mezcla de pageblocks de /proc/pagetypeinfo antes y después de una carga de modelo, con control negativo (una lectura que dé conteos distintos tras un cambio inducido). Hasta entonces la hipótesis no tiene dato propio."}
---

## Contexto

Hallazgo del 2026-10-20 al revisar [NVIDIA #1358](https://github.com/NVIDIA/open-gpu-kernel-modules/issues/1358) y los foros. [MiaAI-Lab/DeepSeek-v4.1-Flash-DGX-Sparks#23](https://github.com/MiaAI-Lab/DeepSeek-v4.1-Flash-DGX-Sparks/issues/23) propone que la carga de un modelo fragmenta la memoria del host (≈86 % de pageblocks UNMOVABLE; órdenes 8+ de 3909 a 10), que el driver pide memoria contigua y recibe `NV_ERR_NO_MEMORY` con ~8,7 GiB libres, y que `echo 1 > /proc/sys/vm/compact_memory` permite completar prefills que antes colgaban (dos usuarios, 2× y 4× DGX Spark). El dueño del repo no lo ha reproducido; es una inferencia, no una observación confirmada.

Brecha propia: una búsqueda en el repo de `buddyinfo`, `compact_memory` y `After Power Loss` no encontró referencias (fuera de `tasks/evidence`). Blackbox registra PSI y MemAvailable, que no distinguen "poca memoria" de "memoria sin bloques contiguos".

## Alcance

Reutilizar el muestreador existente de Blackbox. Añadir lectura de solo lectura de `/proc/buddyinfo` (suma de órdenes 8+ y 10+ de la zona Normal) y de `/proc/pagetypeinfo` (pageblocks por tipo de movilidad) a cada muestra. Medir antes y después de cargar un modelo en esta máquina. No ejecutar `compact_memory` ni cambiar `vm.min_free_kbytes` ni `vm.watermark_scale_factor`: el hilo advierte que subir los dos últimos colgó equipos con carga.

Campos del convenio de incidente de #1358: cuando falte la lectura, `NOT_COLLECTED`; cero solo si se observó cero. Añadir al mismo convenio los campos propuestos por RFDH (UEFI "After Power Loss", `kernel.panic_on_rcu_stall`) como `NOT_COLLECTED` por defecto.

## Criterio de cierre

Dos lecturas literales (antes/después de una carga) con comando y salida, un control negativo que muestre que la lectura cambia cuando cambia la fragmentación, y el resultado informado aunque no confirme la hipótesis. Un resultado sin fragmentación también cierra si delimita la pila donde no ocurre.
