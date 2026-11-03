---
id: DEBT-LECTURA-DE-GPU-CONGELADA-TRAS-GSP-SIN-MARCA-01
kind: task
domain: GPU
title: "Tras el fallo del GSP la lectura de nvidia-smi queda congelada en una linea identica (hasta 9 614 s) y ningun muestreador la marca como vieja"
status: open
severity: P1
origin: measured
satd_family: BLIND_INSTRUMENT
created: 2026-11-02
close_check: {"cmd": "grep -qE 'gpu_congelada|gpu_edad' tools/muestreo_1s.py", "expect": "exit_zero", "porque": "Falla hoy (medido 2026-11-02): tools/muestreo_1s.py escribe la ultima linea de nvidia-smi sin edad ni bandera; una lectura congelada es indistinguible de una viva."}
---

## Medido el 2026-11-02 (`muestreo-<boot>.jsonl`, campo `gpu`, racha final de lineas exactamente iguales)

| Arranque | Fallo del GSP | Duracion | Racha final identica | Empieza a los |
|---|---|---|---|---|
| 813b8381 | si | 36 s | 12 s | 25 s |
| eb3c701b | si | 237 s | 210 s | 23 s |
| 6fed1707 | si | 79 s | 54 s | 24 s |
| 7cd0848b | si | 9 864 s | 9 614 s | 24 s |
| c092e563 | si | (reloj negativo) | 47 s | 25 s |
| 81ff05b2, 7b53a8f5, 447f4342, a50c88c0, 39e2f667, fc60e471 | no | 22 s a 38 721 s | 1 a 3 s | (viva) |

Control negativo, medido: en el arranque sano actual (6.17), con GPU al 0 %, 562 filas dieron 393 lecturas distintas y una racha maxima de 4 s. Una GPU ociosa sana NO repite la misma linea durante minutos; los cinco arranques con GSP caido repiten la misma linea desde los 23 a 25 s, que es cuando aparece `rpcRecvPoll timedout`. La telemetria propia de 5 s (`atom_gpu_telemetry.jsonl`) trae 3 potencias distintas en 1 641 muestras de 7cd0848b: mismo sintoma.

## Que invalida

La afirmacion «la potencia de GPU (5 a 9,7 W) descarta la GPU como causa» de la entrega del 2026-11-02 vale solo para arranques con lectura viva. En los cinco arranques con el fallo, esa potencia es el ultimo valor valido antes del fallo repetido, no una medicion de los ultimos segundos. CPU, zonas termicas de `/sys`, carga y PSI vienen de `/proc` y `/sys` y no se afectan.

## Alcance

1. `tools/muestreo_1s.py`: anotar por muestra la edad de la lectura de GPU (segundos desde que cambio la linea) y `gpu_congelada: true` pasados N s identicos (N a medir: la racha sana maxima fue 4 s).
2. Lo mismo en `atom_gpu_telemetry` (evento `gpu_lectura_congelada`) y aviso por el canal de `aviso_gpu_reset`.
3. Revisar `adopted/gpu_governance/gpu_sampler.sh` (suspendido desde 2026-09-07): su `timeout 10 nvidia-smi` marcaria `TIMEOUT` si el binario colgara, pero estos arranques indican que nvidia-smi RESPONDE con valores viejos; el sampler grabaria filas `OK` iguales. No cierra este hueco por si solo.
4. Corregir el tema publicado en el foro de NVIDIA (post 2 dice «muestras tranquilas») con esta salvedad: decision de Luis.

## Limite

No se probo si `nvidia-smi` devuelve cache o si el stream `-lms` se bloquea; solo se midio que la salida es identica. Distinguirlo requiere correr `nvidia-smi` aparte durante un fallo real.
