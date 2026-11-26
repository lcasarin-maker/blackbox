---
id: DEBT-PANIC-INSTALACION-Y-PRUEBA-EN-ARRANQUE-REAL-01
kind: task
domain: SYSTEM
title: "sudo panic, el punto de restauracion y el autoarmado de GRUB estan construidos y probados con raiz falsa, pero ni instalados ni probados en un arranque real"
status: done
severity: P1
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-11-03
close_check: {"cmd": "test -x /usr/local/sbin/panic && grub-editenv list | grep -q '^bb_intentos=' && grep -q '\"autoarmado\": true.*\"fijado_a\": \"gnulinux-' /var/lib/blackbox/arranque-ok.jsonl", "expect": "exit_zero", "porque": "Falla hoy (medido 2026-11-03, rc=1): /usr/local/sbin/panic no existe (rc 1), `grub-editenv list` no tiene ninguna variable (0 lineas) y /var/lib/blackbox/arranque-ok.jsonl no existe. Pasa solo con panic instalado, el contador del autoarmado en el grubenv y UN arranque real en que GRUB eligio el punto, salio sano y bb-arranque-ok lo fijo con grub-set-default."}
closed_at: 2026-11-07
closure_type: verified_closed
closure_reason: "El close_check de la ficha sale 0 hoy (corrido por /debt el 2026-11-07); la ficha seguia abierta aunque su condicion ya se cumplia. Salida en la evidencia."
evidence:
  pass: tasks/evidence/DEBT-PANIC-INSTALACION-Y-PRUEBA-EN-ARRANQUE-REAL-01/pass.txt
---

## Que falta

Lo construido el 2026-11-03 (docs/PANIC.md): `tools/panic.py` + `bin/panic`, `tools/punto_restauracion.py`, las unidades
de sistema `bb-punto-restauracion.{service,timer}` y `bb-arranque-ok.{service,timer}`, y las capas
`grub-default-guardado` y `grub-autoarmado` de `tools/opt_in_captura.sh`. Todo probado solo con raiz falsa y shims
(`tests/test_panic.py`, `tests/test_grub_autoarmado.py`, `tests/test_opt_in_captura.py`). La logica de GRUB se valido
con `grub-script-check` (sintaxis) y con un interprete del subconjunto de GRUB (logica): NUNCA corrio en GRUB.

## Pasos (los corre Luis con sudo, uno por bloque; comandos exactos en docs/PANIC.md §Instalacion)

1. Instalar la copia root: `/usr/local/lib/blackbox/tools/` (lista `tools/panic.INSTALA`) y `/usr/local/sbin/panic`.
2. Retirar `/usr/local/sbin/rojo` si llego a instalarse (renombrar).
3. Instalar las cuatro unidades en `/etc/systemd/system/` y `daemon-reload`.
4. `aplica grub-default-guardado`; reiniciar una vez y comprobar `uname -r` = 6.17.0-1032-nvidia.
5. `enable --now` de `bb-arranque-ok.timer` y `bb-punto-restauracion.timer`; comprobar que existe un punto en
   `/var/lib/blackbox/restore/` y `bb_punto_entry` en `grub-editenv list`.
6. `aplica grub-autoarmado`.
7. Prueba en arranque real: `sudo grub-editenv /boot/grub/grubenv set bb_intentos=3`, `sudo reboot`, y comprobar
   `uname -r` = kernel del punto, `bb_autoarmado=1` antes de 180 s y, despues, la linea con `"autoarmado": true` y
   `"fijado_a": "<entrada del punto>"` en `/var/lib/blackbox/arranque-ok.jsonl`, y `saved_entry` = esa entrada
   (sin oscilacion: decision de Luis 2026-11-03). Un reinicio mas debe arrancar el punto.
8. Tras la instalacion: `git mv` de las cuatro gemelas de `adopted/pendiente-de-despliegue/` a
   `adopted/system-config/` y su fila en SPEC.md §Inventario de propiedad.

## Control negativo

El close_check falla hoy por las tres ramas, cada una medida por separado el 2026-11-03: `test -x /usr/local/sbin/panic`
rc 1; `grub-editenv list | grep -q '^bb_intentos='` rc 1 (el grubenv no tiene ninguna variable); el jsonl no existe.
