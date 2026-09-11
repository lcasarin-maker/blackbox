---
id: DEBT-PSI-UMBRALES-SIN-CALIBRAR
kind: debt
title: Los umbrales LOW/MODERATE/HIGH/CRITICAL de PSI vienen de otra maquina y no de una medicion propia
status: open
severity: P2
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-09-08
close_check: {"cmd": "grep -q 'calibrado 2026' bin/bb", "expect": "exit_zero"}
---

## Que pasa

`bb scan` clasifica la presion de memoria en LOW (<5%), MODERATE (<20%), HIGH
(<50%) y CRITICAL. Esa escala sale de `sparkview` (foro NVIDIA 366877, ingerido
en la KB de Atlas), **no** de una medicion en esta maquina. Esta declarada como
provisional en el codigo y en el README, pero sigue siendo un instrumento cuyo
punto de corte nadie ha comprobado aqui.

## Por que importa

Un umbral demasiado alto no dispara cuando debe; uno demasiado bajo entrena a
ignorarlo. Las dos formas de fallar son silenciosas.

## Que la cierra

Un incidente real de esta maquina con PSI registrado a su alrededor, y los
cortes movidos a lo que ese incidente muestre. Hay dos medidas propias ya:
`mem_full` 4.21% durante la carga del gateway (trabajo util cero) y 0.00% con
MemAvailable en 6.1 GB (memoria usada, no sufrida). Con dos puntos no se calibra
una escala de cuatro.

## Ceiling y trigger

ponytail: techo = la escala se queda como esta mientras solo haya 2 medidas
propias; trigger = al tercer incidente con PSI registrado, o si un umbral deja
pasar un colapso.
