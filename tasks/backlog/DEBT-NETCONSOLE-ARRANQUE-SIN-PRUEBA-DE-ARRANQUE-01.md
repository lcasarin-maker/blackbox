---
id: DEBT-NETCONSOLE-ARRANQUE-SIN-PRUEBA-DE-ARRANQUE-01
kind: task
domain: SYSTEM
title: "netconsole-arranque esta aplicada pero no probada en un arranque real: hasta el proximo reinicio la ATOM corre SIN netconsole"
status: open
severity: P1
origin: split
split_from: DEBT-OBSERVADORES-CONSTRUIDOS-SIN-INSTALAR-01
created: 2026-11-16
close_check: {"cmd": "journalctl -k -b -o short-monotonic --no-pager | grep -iE 'netconsole: network logging started' | grep -qE '^\\[ *([0-9]|1[0-9])\\.[0-9]+\\]'", "expect": "exit_zero", "porque": "Pasa solo cuando el arranque en curso inicio netconsole en los primeros 19 s (desde el initramfs). Control negativo medido 2026-11-16: con el runtime, el mensaje salia a 27.9 s y este mismo comando da rc=1."}
---

## Que falta

Luis aplico `netconsole-arranque` el 2026-11-16 retirando antes el runtime. Efecto: hasta el proximo reinicio no hay netconsole
(la Dell no recibe el kernel). Riesgos declarados en `adopted/opt-in/LEEME.md` sin verificar: `r8127` y netpoll desde el initramfs
(un netpoll roto puede colgar un printk); el initramfs puede cargar netconsole antes de que udev renombre `enP7s7` y el destino
no nacer (`netconsole: <if> doesn't exist`).

## Prueba

Tras el primer reinicio en 6.17.0-1032: (1) el close_check de arriba; (2) la Dell recibe lineas del arranque (`netconsole-atom.log`);
(3) `journalctl -k -b | grep -i netconsole` sin `doesn't exist`. Si falla: `sudo bash tools/opt_in_captura.sh retrocede netconsole-arranque`
y reaplicar `netconsole-runtime`. Salida de emergencia: `adopted/opt-in/LEEME.md` (las entradas recovery de GRUB no llevan la capa).
