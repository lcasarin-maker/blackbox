# Informe de puntos ciegos — eventos del 2026-10-24 al 2026-11-02

Fuentes: `journalctl --list-boots` (32 arranques desde 2026-10-24), `journalctl -k -b <id>` por arranque, `reboots.jsonl`, `atom_gpu_telemetry.jsonl`, `gpumem_historial.jsonl`, `muestreo-<boot>.jsonl` (1 s con fsync), `coredumpctl`, `opt_in_captura.sh estado`. Los scripts de medicion viven en el directorio temporal de la sesion; los numeros de abajo salen de sus corridas del 2026-11-02.

## 1. Lo que ocurrio, arranque por arranque

| Periodo | Arranques | Kernel | Lo que se ve |
|---|---|---|---|
| 10-24 a 10-30 15:28 | 3 largos (0,9 a 2,9 dias) | 6.17 | cierres ordenados; 3 caidas de `gnome-shell` (10-25 SIGSEGV, 10-26 SIGQUIT manual, 10-27 SIGSEGV) |
| 10-30 15:30 a 16:45 | 6 | 7.0.0-1024 | 1 h 50 min estable con modulo de fabrica; 4 cortes duros en 25 min con modulo parchado (8:01, >=2:33, >=2:09, >=1:58, tiempos corregidos por la cola perdida del journal); sin Xid, NVRM ni AER |
| 10-30 17:04 a 19:00 | 1 de 1 h 56 min | 7.0 | estable, sin motor; termina a las 19:00 (veredicto: ninguna fila) |
| 10-30 19:02 a 11-02 11:44 | 21 | 7.0 | 20 arranques de 3 a 242 s y uno de 2 h 44 min; **timeout del GSP y Xid 154 en 8 de 11 arranques que pasan de 25 s** |
| 11-02 13:02 a hoy | 1 (en marcha) | 6.17 | estable, 4 h+ con el motor cargado (el motor no se detuvo) |

## 2. Lo que SI se descarto con datos

Ultimas muestras de 1 s antes del fin de los 14 arranques cortos del bucle y de los dos cortes largos (`muestreo-*.jsonl`):

- CPU entre 0,5 y 44 %, carga 0,4 a 6,8, sin proceso fuera de lo habitual.
- Temperatura maxima 52,2 C (limite del equipo mucho mas alto).
- GPU entre 5 y 9,7 W y 0 % en el ultimo segundo.
- PSI de CPU y memoria en cero.

No fue saturacion de CPU, calentamiento, potencia de GPU ni presion de memoria en esos arranques. El muestreador demostro que su fsync sobrevive: en el arranque de 2 h 44 min la ultima muestra esta a ~0,4 s del ultimo registro del journal.

## 3. Lo que NO se habia visto y apareció

En kernel 7.0.0-1024, desde 2026-10-30 19:05, entre los 21 y 28 s de vida:
`rpcRecvPoll timedout` (GSP) -> volcado del falcon -> `Xid 154: GPU Reset Required` -> miles de aserciones `NV_ERR_GPU_IN_FULLCHIP_RESET` y `NV_ERR_RESET_REQUIRED`. Ausente en los cuatro cortes del 10-30 16:22 a 16:45, en el arranque de 17:04 a 19:00 y en el 6.17 actual. Detalle: DEBT-NVRM-GSP-TIMEOUT-XID154-KERNEL-7-0-SIN-ALARMA-01.

Esto contradice una lectura previa: el informe para NVIDIA y el tema del foro dicen "sin Xid ni NVRM" para los cuatro cortes (cierto) y no mencionan los arranques del bucle (omision mia, por mirar solo las colas de los journals).

## 4. Mapa de puntos ciegos

| # | Punto ciego | Evidencia medida | Estado | Cierre |
|---|---|---|---|---|
| 1 | Energia de la maquina entera | Linux no expone potencia de entrada ni PD; 0 `power_supply`/`typec` | abierto, enchufe en camino | FEATURE-MEDIDOR-DE-ENERGIA-EXTERNO-01 |
| 2 | Primeros segundos de arranque fuera de la maquina | 20 arranques de 3 a 242 s; netconsole de ejecucion arranca a ~30 s; `netconsole-arranque` sin aplicar | abierto (necesita root) | DEBT-OBSERVADORES-CONSTRUIDOS-SIN-INSTALAR-01 |
| 3 | pstore/ramoops | 0 archivos, sin region reservada, capas `pstore-tras-panico` y `panic-temprano` sin aplicar | abierto (necesita root) | idem |
| 4 | Observadores construidos y no instalados | `bb-ultimo-aliento` no instalada; `bb_testigo` no corre; ping NAS votado el 10-14 sin instalar | abierto | idem |
| 5 | Veredicto por arranque | 8 de 32 arranques con fila; el temporizador exige 3 min de uptime y juzga solo el anterior | en correccion | DEBT-REBOOT-VERDICT-CIEGO-A-ARRANQUES-CORTOS-Y-RELOJ-01 |
| 6 | Veredicto engañado por el reloj | fila `CORTE_ABRUPTO` para el arranque en marcha (vivo 4 h) | en correccion | idem |
| 7 | Reloj de pared adelantado en arranque | 2 arranques con 3 h 25 min y ~18 h de desfase; uno con duracion negativa | abierto | DEBT-RELOJ-DE-PARED-ADELANTADO-HORAS-EN-ARRANQUE-01 |
| 8 | Xid 154 y fallo del GSP sin alarma | 8 arranques, 0 filas lo registran | en correccion | DEBT-NVRM-GSP-TIMEOUT-XID154-KERNEL-7-0-SIN-ALARMA-01 |
| 9 | 22 unidades de monitoreo suspendidas 3 dias | `gpumem_historial` 0 muestras desde 10-30 16:32; detector de reloj, canario del motor, monitores dmem apagados | reponiendo una a una (2 de 16 repuestas) | manifiesto 2026-10-30, vence 2026-11-06 |
| 10 | El instrumento mas util vive fuera del repo | `muestreo_1s.py` solo en el directorio de datos, sin pruebas | abierto | DEBT-MUESTREO-1S-FUERA-DEL-REPO-01 |
| 11 | Cola del journal | antes del 10-30 17:00 se perdian 19 a 26 s; con `SyncIntervalSec=1s` la diferencia medida entre la telemetria y el ultimo log fue de -9 a 29 s segun el arranque | mitigado, sin medir contra un corte limpio | seguimiento en el proximo corte |
| 12 | Receptor externo en un PC que se puede reiniciar | tarea `bb_receptor_netconsole` creada, sin probar a traves de un reinicio de Windows | armado, sin probar | DEBT-OBSERVADORES-CONSTRUIDOS-SIN-INSTALAR-01 |
| 13 | Caidas de la sesion grafica | 3 SIGSEGV de `gnome-shell` en 8 dias; pila con simbolos: `device=0x0` en `meta_input_device_x11_reset_scroll_info` | causa localizada, decision pendiente | DEBT-GNOME-SHELL-SEGV-EN-LIBMUTTER-FREE-X11-01 |
| 14 | Consola serie a 921 600 baudios inundada por NVRM | hilo `pr/ttyS0` al 101 % de un nucleo en 39e2f667 | pista sin probar | DEBT-NVRM-GSP-TIMEOUT-XID154-KERNEL-7-0-SIN-ALARMA-01 §3 |

## 5. Lo que sigue sin saberse

La causa de los cortes. Las muestras planas del ultimo segundo, la ausencia de panic y el estado de GSP en reset-requerido son compatibles con un reset de hardware (SoC, EC o PD) y con perdida de energia; ningun instrumento instalado distingue entre los dos. Eso solo lo distingue el medidor de energia externo, mas el netconsole en la linea de arranque.

## 6. Orden propuesto para cerrar

1. Corregir `reboot_verdict` (en curso; evita seguir midiendo con un instrumento que mira 1 de cada 4 arranques).
2. Reponer `bb-reloj-arranque` y los monitores de memoria antes que los de dmem.
3. Aplicar `netconsole-arranque` y `pstore-tras-panico` (root).
4. Instalar `bb-ultimo-aliento` y el ping del NAS.
5. Con el enchufe: cerrar la pregunta energia contra reset interno.
