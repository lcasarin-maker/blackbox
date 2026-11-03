---
id: DEBT-NVRM-GSP-TIMEOUT-XID154-KERNEL-7-0-SIN-ALARMA-01
kind: task
domain: GPU
title: "Desde 2026-10-30 19:05, 8 de 11 arranques en 7.0.0-1024 que pasan de ~25 s registran timeout del GSP y Xid 154 (GPU Reset Required) y ningun instrumento lo vio"
status: open
severity: P1
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-11-02
close_check: {"cmd": "grep -q '\"gsp_timeout\"' ~/.local/share/blackbox/reboots.jsonl", "expect": "exit_zero", "porque": "Falla hoy (medido 2026-11-02): las filas de reboots.jsonl no traen el campo gsp_timeout. Pasa cuando reboot_verdict lo escribe."}
---

## Medido el 2026-11-02 (`journalctl -k -b <id>`, tabla completa por arranque con `xid.py` del informe de puntos ciegos)

- Kernel 7.0.0-1024-nvidia, arranques desde 2026-10-30 19:05: en 8 de los 11 que llegan a 25 s o mas aparece, entre los 21 y 28 s de vida, la secuencia
  `NVRM: _issueRpcAndWait: rpcRecvPoll timedout` -> `kflcnCoreDumpDestructive_IMPL: ICD: unwind...` -> `NVRM: Xid (PCI:000f:01:00): 154, GPU recovery action changed from 0x0 (None) to 0x1 (GPU Reset Required)` -> miles de `Assertion failed: (status == NV_OK) || (status == NV_ERR_GPU_IN_FULLCHIP_RESET)` y `Check failed: Reset required [NV_ERR_RESET_REQUIRED]`.
- Sin la secuencia pese a pasar de 25 s: 447f4342 (35,9 s de vida), 2f73178e (28,0 s), d6577158 (28,2 s).
- Arranques con la secuencia (primer evento en segundos): 813b8381 (25,5), eb3c701b (21,7), c092e563 (24,9), a1cbc2ed (25,6), 6fed1707 (23,2), 7cd0848b (24,4), 08d82332 (27,9), 39e2f667 (27,9). Aserciones: 179, 879, 545, 0, 1144, 7057, 0, 83.
- Ausente en los cuatro cortes del 2026-10-30 16:22 a 16:45, en el arranque estable de 17:04 a 19:00 y en el arranque actual en 6.17.0-1032-nvidia (14 498 s, 0 aserciones).
- El arranque 7cd0848b vivio 9 871 s (2 h 44 min) con la GPU en ese estado y termino sin cierre ordenado; las ultimas 4 muestras de 1 s (`muestreo-7cd0848b.jsonl`) son planas: CPU 0,3 a 3,4 %, 41,8 a 43,3 C, GPU 9,3 W al 0 %.
- En el arranque 39e2f667 el hilo `pr/ttyS0` consume un nucleo al 101 % en la ultima muestra: la consola serie esta a `console=ttyS0,921600` y la inundacion de mensajes NVRM pasa por ella. Es una pista, no una causa: no hay prueba de que esa carga reinicie nada.

- **Modulo cargado en esos arranques: no consta.** `dmem_parche.jsonl` no tiene entradas despues de 2026-10-30 22:25 UTC (el monitor estaba suspendido), el journal de kernel de los arranques del bucle no trae lineas `dmem` ni `memacct`, y hoy `/lib/modules/7.0.0-1024-nvidia/updates/` no existe. No se puede afirmar si el bucle corrio con el modulo parchado o con el de fabrica; si fue el de fabrica, la hipotesis "el parche causa los cortes" pierde fuerza. Falta un registro por arranque de la ruta del `nvidia.ko` cargado (`/sys/module/nvidia/` + `modinfo -n`) y de su sha256.
  Escrito el 2026-11-02: `tools/modulo_nvidia_registro.py` + `reboot_verdict` (`modulo_nvidia_*`, `NOT_COLLECTED` sin registro). Rige desde el primer arranque con la unidad instalada (DEBT-BB-MODULO-NVIDIA-REGISTRO-UNIDAD-SIN-INSTALAR-01); los arranques del bucle ya pasados quedan `NOT_COLLECTED` para siempre.

## Lo que corrige

El informe preparado para NVIDIA y el tema publicado decian "sin Xid ni NVRM de error" y "pstore vacio" para los cortes del 2026-10-30 (cierto para esos cuatro) y no mencionaban esta secuencia en los arranques del bucle del 11-01 y 11-02. Esa omision es un error mio de lectura (solo mire las colas de los journals de los cortes), no una ausencia en los datos.

## Alcance

1. `reboot_verdict` escribe `gsp_timeout`, `xid154` y `gpu_fullchip_reset_asserts` por arranque (ver DEBT-REBOOT-VERDICT-CIEGO-A-ARRANQUES-CORTOS-Y-RELOJ-01).
2. Aviso al usuario cuando un arranque registra Xid 154 y la GPU queda en `Reset Required`: hoy el sistema sigue sirviendo el motor sobre una GPU que el controlador declara que necesita reinicio.
3. Probar si la secuencia aparece con el modulo de fabrica en 7.0 (una variable por vez) y con la consola serie en `loglevel` bajo.
4. Adjuntar esta secuencia al reporte de NVIDIA.

## Control negativo

El `close_check` falla hoy. La deteccion debe probarse contra el arranque actual (6.17, 0 aserciones: debe dar `false`) y contra 7cd0848b (debe dar `true`).

## Limite

El orden temporal (GSP falla a ~25 s; el corte llega despues, a veces horas) no prueba causalidad: el arranque de 2 h 44 min muestra que la GPU puede quedar en reset-requerido sin que la maquina corte pronto.
