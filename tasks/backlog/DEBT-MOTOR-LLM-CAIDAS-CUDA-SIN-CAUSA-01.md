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
close_check: {"expect": "exit_zero", "porque": "Solo se cierra con la salida literal de cuda-gdb sobre un volcado REAL vllm_* del motor: kernel, excepcion y linea. Hipotesis sin volcado no cierran nada.", "cmd": "grep -qE \"^CUDA Exception: Warp\" tasks/evidence/DEBT-MOTOR-LLM-CAIDAS-CUDA-SIN-CAUSA-01/cuda-gdb-kernel.txt"}
---

## Que paso (medido con `bb scan "2026-10-08 19:39"`, journal de ai-nemotron.service)

15 caidas fatales del EngineCore entre el 08-oct 20:54 y el 10-oct 05:51, y 4 cuelgues en
que /v1/models daba 200 y el chat no contestaba (reiniciados por el vigilante). Clases de
error CUDA: 12 illegal memory access, 2 illegal instruction, 1 misaligned address.

Dos patrones de Xid, no uno: ocho caidas con rafaga Xid 13 (108 o 144 lineas) mas Xid 43,
y siete con un solo Xid 31 (fallo de MMU) o con Xid 13 y 31. Los dos conviven en la misma
carga. Quien investigue no debe tratarlas como un solo fallo.

Racha sana de 13 h 49 min (09-oct 13:55 a 10-oct 03:44) con la misma carga: la carga
agregada no distingue caidas de calma. Medicion de la sesion otro proyecto, no reproducida aqui.

## Instrumento

- Volcado CUDA armado el 2026-10-10 05:56 (`CUDA_ENABLE_COREDUMP_ON_EXCEPTION=1` en
  /srv/ai/gateway/active_engine.json, destino /srv/ai/models/_coredumps). Control positivo
  hecho por otro proyecto: un kernel Triton fuera de rango produjo un volcado de 3.4 MB que
  cuda-gdb leyo. Al crear esta ficha: 0 volcados `vllm_*` reales.
- `bb status` lo exige (fila "volcado CUDA ante excepcion del motor") y `bb scan` lo lista
  y le corre `cuda-gdb ... info cuda kernels` a los ultimos tres (tools/motor_caidas.py).

## Hipotesis SIN probar (no cerrar por ellas)

cache de prefijos de Mamba en modo align (vLLM la marca experimental), kernels compilados
para SM12.0 corriendo en SM12.1, driver o kernel (hay 7.0.0-1019 pendiente de reinicio).

## Criterio de cierre

Guardar en `tasks/evidence/DEBT-MOTOR-LLM-CAIDAS-CUDA-SIN-CAUSA-01/cuda-gdb-kernel.txt` la
salida literal de cuda-gdb sobre el primer volcado real, y nombrar aqui el kernel. Cambiar
el motor o el driver antes de eso destruye la comparacion: avisar a la sesion otro proyecto,
cuya corrida de fichas (~45 h) depende del servidor.

## Seguimiento, 2026-10-10

Ahora hay seis volcados `vllm_*` reales y `file` confirma los seis como ELF core de arquitectura
NVIDIA CUDA. El intento literal de abrir el primero abortó dentro de `cuda-gdb` con
`Assertion 'm_instance.m_num_devices > 0' failed`; `nvidia-smi -L` también falla con código 9
porque esta sesión no puede comunicarse con el driver. La salida y los comandos están en
`tasks/evidence/DEBT-MOTOR-LLM-CAIDAS-CUDA-SIN-CAUSA-01/audit-2026-10-10.md`.

La captura ya ocurrió; falta correr el análisis en una sesión con GPU/driver visible. La P1 sigue
abierta y no se atribuye la causa ni se cambia el motor o el driver.

`tools/motor_caidas.py` conserva la línea `internal-error` de `cuda-gdb` cuando no produce salida,
y omite los volcados restantes de ese scan cuando detecta esta aserción de dispositivo ausente.
Así deja visible el motivo y evita repetir el mismo aborto por cada archivo; todavía requiere el
host con GPU/driver visible para cumplir el criterio de cierre.

## Analisis de los 28 volcados (2026-10-13, solo lectura; evidencia en `tasks/evidence/DEBT-MOTOR-LLM-CAIDAS-CUDA-SIN-CAUSA-01/`, resumen en `resumen.txt`)
- **Los 28 volcados `vllm_*` estan truncados** (67904 bytes cada uno; su encabezado ELF promete 420-459 MB). `cuda-gdb` no puede abrirlos (rc=134, `m_num_devices > 0`); el control positivo (un volcado de prueba) abre con rc=0 y el negativo (un archivo de texto) falla con rc=1.
- **Kernel nombrado por el log del propio generador de volcados** (`journalctl --user -u ai-nemotron`, 28 eventos, 1:1 con los archivos): en los 28, frame #0 es un kernel cuDNN fusionado `matMul_pointwise_pointwise` (22 `sm120 knob_11_128x128x64`, 4 `sm80 knob_0_256x128x128_3_0`, 1 `sm120 knob_12`, 1 `sm120 knob_6`). Excepciones: 17 `WARP_OUT_OF_RANGE_ADDRESS`, 8 `WARP_MISALIGNED_ADDRESS`, 3 `WARP_ILLEGAL_INSTRUCTION`. Sin linea de fuente.
- **Por que estan truncados:** en los 28 la escritura se detiene al 90 % o 95 % de "Writing out global memory" y el EngineCore queda colgado hasta que vLLM lo mata, 4 a 622 s despues. Es decir, el volcado de CUDA activado para diagnosticar retrasa el reinicio del motor y no produce un volcado utilizable.
- **Las caidas del 2026-10-08/10 de esta ficha no tienen volcado** (son anteriores al armado, 10-oct 05:56); solo hay la clase de error en el journal (56 illegal memory access, 9 illegal instruction, 4 misaligned address). Decir que son el mismo kernel cuDNN es inferencia, no medicion.
- **Hipotesis sin probar:** kernels compilados para sm120/sm80 corriendo en una GPU sm_121 encajan con una incompatibilidad SM12.0 sobre SM12.1; no la prueban.
- **Defecto del `close_check` corregido:** `grep -qE "Warp|Exception|kernel"` daba exit 0 sobre una salida fallida de `cuda-gdb` y sobre el control negativo, porque la linea de comando impresa contiene "kernels". Ahora exige una linea que empiece por `CUDA Exception: Warp`.
- **Decision pendiente de Luis:** para obtener un volcado completo hay que dejar que el generador termine (mas tiempo antes del reinicio o otras banderas de generacion). Eso cambia el motor de produccion y la ficha pide avisar antes a la otra sesion que usa el motor.
