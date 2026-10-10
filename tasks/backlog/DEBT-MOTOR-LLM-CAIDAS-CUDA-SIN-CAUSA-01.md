---
id: DEBT-MOTOR-LLM-CAIDAS-CUDA-SIN-CAUSA-01
kind: task
domain: INFERENCE
title: "Nombrar el kernel CUDA que tumba el motor vLLM local (caidas fatales del 2026-10-08/10)"
status: open
severity: P1
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-10-10
close_check: {"expect": "exit_zero", "porque": "Solo se cierra con la salida literal de cuda-gdb sobre un volcado REAL vllm_* del motor: kernel, excepcion y linea. Hipotesis sin volcado no cierran nada.", "cmd": "grep -qE \"Warp|Exception|kernel\" tasks/evidence/DEBT-MOTOR-LLM-CAIDAS-CUDA-SIN-CAUSA-01/cuda-gdb-kernel.txt"}
---

## Que paso (medido con `bb scan "2026-10-08 19:39"`, journal de ai-nemotron.service)

15 caidas fatales del EngineCore entre el 08-oct 20:54 y el 10-oct 05:51, y 4 cuelgues en
que /v1/models daba 200 y el chat no contestaba (reiniciados por el vigilante). Clases de
error CUDA: 12 illegal memory access, 2 illegal instruction, 1 misaligned address.

Dos patrones de Xid, no uno: ocho caidas con rafaga Xid 13 (108 o 144 lineas) mas Xid 43,
y siete con un solo Xid 31 (fallo de MMU) o con Xid 13 y 31. Los dos conviven en la misma
carga. Quien investigue no debe tratarlas como un solo fallo.

Racha sana de 13 h 49 min (09-oct 13:55 a 10-oct 03:44) con la misma carga: la carga
agregada no distingue caidas de calma. Medicion de la sesion Declutter, no reproducida aqui.

## Instrumento

- Volcado CUDA armado el 2026-10-10 05:56 (`CUDA_ENABLE_COREDUMP_ON_EXCEPTION=1` en
  /srv/ai/gateway/active_engine.json, destino /srv/ai/models/_coredumps). Control positivo
  hecho por Declutter: un kernel Triton fuera de rango produjo un volcado de 3.4 MB que
  cuda-gdb leyo. Hasta la hora de esta ficha: 0 volcados `vllm_*` reales.
- `bb status` lo exige (fila "volcado CUDA ante excepcion del motor") y `bb scan` lo lista
  y le corre `cuda-gdb ... info cuda kernels` a los ultimos tres (tools/motor_caidas.py).

## Hipotesis SIN probar (no cerrar por ellas)

cache de prefijos de Mamba en modo align (vLLM la marca experimental), kernels compilados
para SM12.0 corriendo en SM12.1, driver o kernel (hay 7.0.0-1019 pendiente de reinicio).

## Criterio de cierre

Guardar en `tasks/evidence/DEBT-MOTOR-LLM-CAIDAS-CUDA-SIN-CAUSA-01/cuda-gdb-kernel.txt` la
salida literal de cuda-gdb sobre el primer volcado real, y nombrar aqui el kernel. Cambiar
el motor o el driver antes de eso destruye la comparacion: avisar a la sesion Declutter,
cuya corrida de fichas (~45 h) depende del servidor.
