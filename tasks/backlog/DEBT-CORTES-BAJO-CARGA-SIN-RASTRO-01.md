---
id: DEBT-CORTES-BAJO-CARGA-SIN-RASTRO-01
kind: task
domain: HARDWARE
title: "Clasificar los tres cortes bajo carga de GPU del 06, 07 y 08-oct (energia o hardware)"
status: open
severity: P1
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-10-10
close_check: {"cmd": "test -s tasks/evidence/DEBT-CORTES-BAJO-CARGA-SIN-RASTRO-01/clasificacion.md", "expect": "exit_zero", "porque": "Solo cierra con la clasificacion escrita de cada corte, con la confirmacion de Luis de cuales fueron cortes de energia."}
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
