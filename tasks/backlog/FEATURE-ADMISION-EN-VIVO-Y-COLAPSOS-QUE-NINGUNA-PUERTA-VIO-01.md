---
id: FEATURE-ADMISION-EN-VIVO-Y-COLAPSOS-QUE-NINGUNA-PUERTA-VIO-01
kind: task
domain: MEMORY
title: "La puerta de admision de todo o nada nunca se ha visto actuar en vivo, y los colapsos del 22, 24 y 29-oct pasaron sin que ninguna puerta de app.slice los viera"
status: open
severity: P2
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-10-30
close_check: {"cmd": "grep -qx admision_en_vivo_evaluada tasks/evidence/FEATURE-ADMISION-EN-VIVO-Y-COLAPSOS-QUE-NINGUNA-PUERTA-VIO-01/medicion.txt", "expect": "exit_zero", "porque": "Especificacion pendiente: el archivo no existe hoy (grep sale 2). Pasa cuando medicion.txt traiga, con comando y salida literales, el resumen de al menos 7 dias del registro `habria_negado` de `portero_admision` en observar (aciertos, falsos positivos, NOT_COLLECTED) y el analisis de que senal habria visto los colapsos del 22, 24 y 29-oct, y termine con la linea completa admision_en_vivo_evaluada."}
---

## Origen

Resto de `FEATURE-ADMISION-TODO-O-NADA-CON-HOLGURA-REAL-01` (cerrada 2026-10-30 por voto de Luis con la ventana del 2026-10-21). Su medicion (`tasks/evidence/FEATURE-ADMISION-TODO-O-NADA-CON-HOLGURA-REAL-01/medicion.txt`) deja tres huecos que esa ficha no cierra:

1. **Nunca se vio actuar en vivo.** `portero_admision` esta en `off` (ausente en `interruptores.json`). Ponerlo en `observar` es decision de Luis (solo registra `habria_negado`). La regla `tope - anon < 20 GiB` negaria el 0.93 % del tiempo (168 de 18 066 muestras sanas, 157 sin colapso despues) y sobre 1168 admisiones reales de suite habria negado 10, una sola seguida de colapso.
2. **Colapsos que ninguna puerta vio.** Los de 2026-10-22 19:37, 10-24 12:22, 10-29 21:45 y 22:53 llegaron con anon previo de 9.1 a 18.6 GiB: la puerta de anon+shmem no los ve. Falta saber que senal si (hipotesis a medir: presion de IO/CPU, cache, swap; `atasco_confinado` registra esos campos en `observar`).
3. **Condicion previa al arranque del motor vLLM** (punto 3 de la ficha cerrada, `ExecCondition=` de systemd 255, a verificar): no se toco. Aplicarla es decision de Luis porque la configuracion del motor es de la pila de IA.

## Para cerrar

1. Luis pone `portero_admision` en `observar`; pasados 7 dias se resume `portero.jsonl` (`habria_negado`: aciertos, falsos positivos, `NOT_COLLECTED`).
2. Cruzar los 4 colapsos sin vision con `$BLACKBOX_DATA/interruptores/atasco_confinado.jsonl` y `reclaim` para nombrar una senal que si los separe, o declarar que no existe con las cifras.
3. Evaluar el punto 3 y proponerlo a Luis con su costo.
