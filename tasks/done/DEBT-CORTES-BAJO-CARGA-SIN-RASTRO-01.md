---
id: DEBT-CORTES-BAJO-CARGA-SIN-RASTRO-01
kind: task
domain: HARDWARE
title: "Clasificar los tres cortes bajo carga de GPU del 06, 07 y 08-oct (energia o hardware)"
status: done
closed_at: 2026-10-14
closure_type: fixed
reason: "Clasificacion escrita por corte (voto de Luis 2026-10-14: 'cerrar con clasificacion INDETERMINADA por corte y un close_check que verifique de verdad'): 06-oct (36ebc0d9), 07-oct (0de3e072) y 08-oct (e651544a) quedan INDETERMINADA (energia o hardware interno), igual que los cortes del 11, 12 y 13-oct, en tasks/evidence/DEBT-CORTES-BAJO-CARGA-SIN-RASTRO-01/clasificacion.txt. La palabra BERT 0x14 no discrimina. LIMITE con ficha: separar red de hardware interno exige FEATURE-MEDIDOR-DE-ENERGIA-EXTERNO-01 y FEATURE-OBSERVADOR-EXTERNO-DE-REINICIOS-01, abiertas."
evidence: {"pass": "tasks/evidence/DEBT-CORTES-BAJO-CARGA-SIN-RASTRO-01/pass.txt", "fail": "tasks/evidence/DEBT-CORTES-BAJO-CARGA-SIN-RASTRO-01/fail.txt", "e2e": "tasks/evidence/DEBT-CORTES-BAJO-CARGA-SIN-RASTRO-01/e2e.txt"}
severity: P1
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-10-10
close_check: {"cmd": "python3 -m pytest -q tests/test_clasificacion_cortes.py", "expect": "exit_zero", "porque": "Verifica la clasificacion escrita, no su existencia: para cada corte del titulo (06, 07 y 08-oct) exige una seccion con el boot correcto, 'Clasificacion: INDETERMINADA (energia o hardware interno)', una linea de evidencia y una de lo que falta que nombre las dos fichas de salida, y la marca clasificacion_indeterminada_declarada; sus controles negativos (vacio, basura, una linea, corte quitado, boot equivocado, clasificacion cambiada, salida ausente) corren en el mismo archivo. El close_check anterior era `grep -q . tasks/evidence/DEBT-CORTES-BAJO-CARGA-SIN-RASTRO-01/clasificacion.md`, que aceptaba cualquier archivo con un byte (medido: rc=0 con 'basura')."}
---

## Medido (2026-10-10, journal, telemetria de 5 s y registros BERT)

Tres boots terminaron de golpe, sin apagado, panic ni mensaje del kernel, con la GPU cargada:

| corte | utilizacion GPU | potencia GPU | temperatura | hueco hasta el boot siguiente | BERT en el boot siguiente |
|---|---|---|---|---|---|
| 06-oct 16:08 | 89 % | 82 W | 83 C | 42 min | si, palabra 0x14 = 0x100 |
| 07-oct 16:50 | 91 % | 74 W | 83 C | 6 min | si, palabra 0x14 = 0x20 |
| 08-oct 18:55 | 96 % | 67 W | 85 C | 38 min | no |

Luis informa que dos fueron cortes de energia. Falta saber cuales. Por la duracion del hueco, los de 42 y 38 min encajan con un corte de red electrica; el de 6 min, muerto con 91 % de carga a 83 C, queda sin explicar. Es una inferencia, no una medicion.

El journal dejo de escribir entre 4 y 26 s antes de la ultima muestra de telemetria (4 s el 07-oct, 8 s el 08-oct, 26 s el 06-oct), asi que el journal no marca la hora de muerte; la telemetria de 5 s si.

## Lo que falta como instrumento

- Los registros BERT (firmware, seccion MTKID) llevan una palabra distinta por corte y nadie la decodifica. `bb scan` ya los cuenta desde 2026-10-10.
- No hay telemetria de potencia de entrada ni del PMIC: un corte de energia y una caida de tension del equipo se ven igual.
- /sys/fs/pstore da Permission denied para este usuario: `kernel_capture` no puede leerlo sin privilegios.

## Cuarto corte medido (2026-10-11) y revision de los ultimos 10 reinicios

Corte del 11-oct 12:13:23 CST (ultima muestra de telemetria; el journal calla a las 12:13:18), hueco de 70 min hasta el boot siguiente. GPU 96 %, 78.3 W, 84 C; `thermal_zone0/5` en 95.7 C (umbral de alarma 94.8, trip 104.8; pico del boot 98.1 C; 119 muestras >= 94.8). Memoria sana: 57 GB disponibles, PSI full 0.0, sin throttle (`0x0`), sin panic, OOM ni Xid proximo (ultimo Xid 13/43 a las 10:41 CST, 92 min antes). BERT ausente en el boot siguiente.

Los cuatro cortes abruptos con GPU cargada comparten firma y la comparten SOLO entre ellos:

| boot | fin CST | util / W / C / zmax | RAM disp. | PSI full | hueco | BERT despues |
|---|---|---|---|---|---|---|
| 36ebc0d9 | 06-oct 16:07 | 89 % / 82 W / 83 / 93.0 | 60 GB | 0.0 | 42 min | si |
| 0de3e072 | 07-oct 16:49 | 91 % / 74 W / 83 / 93.6 | 49 GB | 0.0 | 6 min | si |
| e651544a | 08-oct 18:55 | 96 % / 67 W / 85 / 93.4 | 52 GB | 0.0 | 38 min | no |
| 54b71618 | 11-oct 12:13 | 96 % / 78 W / 84 / 95.7 | 57 GB | 0.0 | 70 min | no |

Control negativo: el mismo instrumento SI detecta el colapso de memoria (28-sep 03:39 y 04:27: PSI full 50-54 % sostenido 600 s; 05-oct 00:29: PSI full 72 %), asi que el PSI 0.0 de estos cuatro es evidencia real de que no fue memoria.

BERT no discrimina: aparece tras un `poweroff` ordenado (10-oct 13:44) y falta tras dos cortes abruptos (08 y 11-oct).

Sin medir: potencia de entrada y PMIC (ver arriba). Hasta tener ese dato, "corte de red" y "reset por hardware/termico" no se pueden separar; el hueco de 6 min del 07-oct no cuadra con red electrica.

### Dato de Luis (2026-10-11): hubo que pulsar el boton de encendido, la pantalla estaba sin imagen

Config medida: `kernel.panic=10`, `hung_task_panic`/`softlockup_panic`/`hardlockup_panic`/`panic_on_oops`=1, `RuntimeWatchdogUSec=1min` sobre `/dev/watchdog0` (SBSA). Un cuelgue de software o de CPU deberia haberse reiniciado solo en menos de ~1 min; el equipo estuvo 70 min abajo hasta el boton. Eso apunta a perdida de alimentacion o apagado de proteccion, no a cuelgue. Declarado por configuracion, NO demostrado: nunca se probo que el watchdog reinicie esta unidad (control negativo pendiente: `echo c > /proc/sysrq-trigger` en ventana controlada, o `systemctl kill`-style de prueba con vLLM parado).
Falta el dato fisico del momento del corte: LED de encendido, ventiladores, y si bastaba pulsar o hubo que mantener.

### Instrumentos abiertos a partir de esta ficha (2026-10-11)

`tools/reboot_verdict.py` clasifica cada reinicio (unidad `bb-reboot-verdict.timer`, filas en `~/.local/share/blackbox/reboots.jsonl`). Pendientes con ficha propia: FEATURE-OBSERVADOR-EXTERNO-DE-REINICIOS-01 (ping, netconsole, enchufe medidor), FEATURE-LECTOR-PSTORE-BERT-ROOT-01 (pstore/BERT con root) y DEBT-WATCHDOG-SIN-CONTROL-NEGATIVO-01 (probar el watchdog).

### Registros BERT por corte (2026-10-11), comparados con el catalogo

Todos los registros de esta maquina llevan el GUID `3c1e3f4b-1e1a-43df-af28-59820e958e3c`, longitud `0x3e`, creador `MTKID` y severidad `corrected`: la misma clase que el personal de NVIDIA cita como patron multi-OEM de falla en el riel de potencia o `PERST#` (hilos 384436 y 377478; segun NVIDIA, Linux no la decodifica). Palabra en `0x14`, leida por `bb incident`:

| reinicio previo | gap | palabra@0x14 |
|---|---|---|
| colapso de memoria 28-sep 03:39 (bb-usable, reinicio por software) | 2 min | `0x10` |
| colapso de memoria 28-sep 04:27 (idem) | 2 min | `0x10` |
| colapso de memoria 05-oct (idem) | 2 min | `0x10` |
| corte 06-oct bajo carga | 42 min | `0x100` |
| corte 07-oct bajo carga | 6 min | `0x20` |
| corte 08-oct bajo carga | 38 min | sin registro |
| poweroff ordenado 10-oct, encendido a mano | 3 min | `0x100` |
| corte 11-oct bajo carga | 70 min | sin registro |

**Hipotesis, n = 8 (3 colapsos con 0x10, 3 con otra palabra, 2 sin registro), sin probar:** la palabra podria codificar el tipo de reset (0x10 tras reinicios que inicia el software; 0x100 y 0x20 tras otros tipos; ausente tras otros). La comunidad publica 0x10 (georgeperjan, 19 resets) y 0x20 (HP ZGX). Solo un medidor externo y el control del reinicio provocado (`DEBT-WATCHDOG-SIN-CONTROL-NEGATIVO-01`) permiten cruzar la palabra con la causa.

## Avance 2026-10-13: el corte de las 14:03 ocurrio con el modulo NVIDIA parcheado cargado
`CORTE_ABRUPTO` del boot `a66787af` (12-oct 21:57 a 13-oct 14:03:27 CST, 16 h 6 min): el journal se corta en pleno servicio de vLLM (200 OK hasta 14:03:27), sin panic ni OOM, PSI en 0, 57,6 GiB libres, zona 79 C, GPU 72 C, 16 peticiones en vuelo; BERT con la palabra 0x14 = 00000010 (la misma de otros cortes). Hecho nuevo: ese boot, y el actual, corren el modulo `nvidia` PARCHEADO de dmem, no el de Canonical: `/lib/modules/6.17.0-1032-nvidia/updates/nvidia.ko`, firmado con la llave MOK enrolada, `dmem.capacity` expone `nvidia/<bus>/vidmem 53794045952` y el kernel loguea `Loading NVIDIA UNIX Open Kernel Mode Setting Driver ... 580.178.04 (lcasarin@... 12 oct 2026 18:55:23)` en el arranque. Los cuatro cortes anteriores (06, 07, 08 y 11-oct) son anteriores al modulo parcheado, asi que este no los explica; del corte de hoy no se puede ni afirmar ni descartar su participacion con la evidencia actual (una sola muestra, sin observador externo). Lo que lo separaria: el medidor de energia y el observador de ping externos, y comparar la tasa de cortes por hora de funcionamiento con y sin el modulo.

## Avance 2026-10-13: tasa de cortes por hora de funcionamiento, antes y despues del modulo parcheado (medida)
Fuente: `./bin/bb reboots` (10 arranques que conserva el journal), cortes `CORTE_ABRUPTO`, excluyendo los dos `COLAPSO_MEMORIA` del 11-oct (otra causa: la estampida de pytest). Antes del modulo parcheado (arranques hasta `f6f10dc3`): 31,7 h de funcionamiento y 2 cortes abruptos = 6,3 por 100 h. Despues (desde `a66787af`, 13-oct 03:57Z): 16,1 h y 1 corte = 6,2 por 100 h. Con 3 eventos en total no hay inferencia posible en ningun sentido; sirve de base para repetir la medicion cuando haya mas arranques o el medidor externo. Nota: los 4 cortes del 06, 07 y 08-oct no entran en la cuenta porque el journal ya no conserva esos arranques.

## Root Cause
Los cortes del 06, 07 y 08-oct terminaron el boot sin apagado, panic ni colapso de memoria (PSI full 0.0, 48-60 GB disponibles, throttle 0x0) con la GPU al 89-96 %. Con los instrumentos de este equipo un corte de red y un apagado del propio equipo (riel de potencia, PMIC, proteccion) dejan la misma huella, y la palabra BERT 0x14 no separa causas (aparece tras un poweroff ordenado y falta tras dos cortes). La causa no se puede determinar aqui: se declara INDETERMINADA por corte y la salida real son el medidor de energia externo y el observador externo de reinicios.

## Regression Test
`tests/test_clasificacion_cortes.py` (nuevo, es el close_check): `test_la_clasificacion_real_cubre_los_tres_cortes` sobre el archivo real y seis controles negativos (`test_rechaza_archivos_que_el_grep_viejo_aceptaba[vacio|basura|solo-la-marca|una-linea-con-todo]`, `test_rechaza_la_clasificacion_real_sin_un_corte`, `test_rechaza_boot_equivocado_clasificacion_cambiada_o_salida_ausente`). No tenia test xfail propio que retirar.

## Verification Evidence
Tres rutas del frontmatter: `fail` (con `clasificacion.txt` sustituido por 'basura' y por una sola linea con la marca, el close_check viejo sale rc=0 y el nuevo rc=1; vacio, los dos salen rc=1; el archivo real se restaura con sha256 comprobado), `pass` (el nuevo acepta el archivo real, 7 pruebas pasan, y las filas de `bb reboots` de los 7 cortes abruptos de los ultimos 18 boots) y `e2e` (la decision registrada). La clasificacion en si: `tasks/evidence/DEBT-CORTES-BAJO-CARGA-SIN-RASTRO-01/clasificacion.txt`. El archivo es `clasificacion.txt` y no el `clasificacion.md` que nombraba el close_check viejo: ledger-schema trata un `.md` dentro de una carpeta de evidencia como una ficha sin gobernar (COULD_NOT_RUN, medido tras el primer commit de este cierre).
