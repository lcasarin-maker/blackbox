---
id: FEATURE-LECTOR-PSTORE-BERT-ROOT-01
kind: task
domain: HARDWARE
title: "Copiar pstore y registros BERT a un directorio legible por el usuario en cada arranque"
status: open
severity: P2
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-10-11
close_check: {"cmd": "grep -q . /var/lib/blackbox/pstore/arranque.jsonl", "expect": "exit_zero", "porque": "/sys/fs/pstore da permiso denegado al usuario y reboot_verdict no puede mirar si un panic o un registro de firmware dejo volcado. Un oneshot de root debe copiarlo y dejar un indice legible."}
---

## Por que

Medido 2026-10-11: `/sys/fs/pstore` no se puede leer sin privilegios (la ficha DEBT-CORTES-BAJO-CARGA-SIN-RASTRO-01 ya lo registraba) y `/var/crash` esta vacio. `reboot_verdict` solo distingue PANIC_KERNEL cuando el journal lo trae; un panic que no alcanzo el disco solo dejaria rastro en pstore.

## Alcance

Unidad de sistema (root, `Before=` el resto) que en cada arranque copia `/sys/fs/pstore/*` a `/var/lib/blackbox/pstore/` con grupo `adm` y escribe una fila en `arranque.jsonl` (hasta cuando no hay nada: la ausencia se declara). Se agrega a `enable-privileged.sh` con su `--revert` y su `--dry-run`. Requiere `sudo`, que el agente no tiene: lo corre Luis.

## Ampliacion (2026-10-11): versiones de firmware en cada arranque

Lo primero que pide el personal de NVIDIA en los foros es `sudo dmidecode -t 45 | grep -A2 -E "UEFI|EC|PD|FLASH"` y `sudo dmidecode -t bios` (Atlas: `knowledge/investigations/gb10_cortes_2026-10-11/hilos/hilo_369572_*`, L27 y L202). El oneshot de root de esta ficha debe escribir tambien esas dos salidas en `/var/lib/blackbox/`, para que `bb incident` rellene `version de UEFI/EC/PD y BIOS` (hoy `NOT_COLLECTED`) sin pedir sudo en el momento del incidente.
