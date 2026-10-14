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

## Avance 2026-10-14: sin unidad de sistema, via bb-root-run
`/var/lib/blackbox/pstore` ya existe (lo creo `pstore-preparar`) y `/sys/fs/pstore` esta vacio (ningun panic desde el ultimo arranque). Construido: `adopted/root-scripts/arranque-forense.sh` (copia pstore y la tabla BERT, guarda `dmidecode -t bios` y `-t 45`, anade una fila a `pstore/arranque.jsonl` por ejecucion, con guardas contra symlinks y dueno ajeno; `tests/test_bb_root_manifest.py`, 10 tests nuevos con controles negativos) y la unidad de usuario pendiente `adopted/pendiente-de-despliegue/bb-arranque-forense.service` (`tests/test_unidad_arranque_forense.py`). Falta: Luis reinstala el manifiesto (el script nuevo tiene hash propio), se instala la unidad de usuario y se verifica `arranque.jsonl` tras el proximo arranque. No lleva unidad de root ni toca `enable-privileged.sh`.

## Avance 2026-10-14 (2): manifiesto reinstalado por Luis y primera corrida real
`sudo -n bb-root-run arranque-forense` rc=0: `/var/lib/blackbox/pstore/arranque.jsonl` tiene filas (`pstore_archivos` 0, `bert` copiada, `firmware` bios+t45), el directorio quedo de root, y `dmidecode-bios.txt` / `dmidecode-t45.txt` existen. El close_check de esta ficha (`grep -q . .../arranque.jsonl`) pasa. `bb incident` ya rellena `version de UEFI/EC/PD y BIOS` desde esos archivos (`tools/incident_report.py::firmware_recogido`, 2 tests, control negativo). No se cierra todavia: falta instalar la unidad de usuario que lo corre en cada arranque y ver una fila nueva tras el siguiente reinicio.
