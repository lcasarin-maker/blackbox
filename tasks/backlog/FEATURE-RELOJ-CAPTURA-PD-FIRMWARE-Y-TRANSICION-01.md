---
id: FEATURE-RELOJ-CAPTURA-PD-FIRMWARE-Y-TRANSICION-01
kind: task
domain: GPU
title: "bb reloj: adjuntar firmware PD con historial por arranque y conservar el episodio sano -> atascado"
status: open
severity: P3
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-10-26
close_check: {"cmd": "python3 -m pytest -q tests/test_reloj_atascado.py -k \"pd_firmware\"", "expect": "exit_zero", "porque": "Especificacion pendiente, no prueba existente: exige que el veredicto ATASCADO adjunte la version de firmware PD leida de lo que escribio arranque-forense, o NOT_COLLECTED con motivo; y que el historial por arranque conserve los valores, no solo el nombre de la fuente."}
---

## Origen

Hilo [386060](https://forums.developer.nvidia.com/t/386060/3), respuesta de zneill (rol de moderador segun Anantus; no
verificado aqui). Pide: versiones exactas de firmware PD y logs de negociacion, correlacion con driver o DGX OS, telemetria
termica y de potencia durante la transicion sano -> atascado, y si afecta tambien a unidades NVIDIA. Anantus responde (post 4)
que no tiene logs PD de la transicion y pregunta como capturarlos.

## Correccion de esta ficha (2026-10-26)

La primera version de esta ficha afirmaba que ningun codigo de bb captura el firmware PD. Era falso: `bb-root-run
arranque-forense` (helper root instalado en `/usr/local/sbin/bb-root-run`, unidad `bb-arranque-forense.service` habilitada)
copia `dmidecode -t 45` a `/var/lib/blackbox/dmidecode-t45.txt` (root, 0644, legible sin sudo) en cada arranque, y
`bb incident` rellena UEFI/EC/PD/FLASH desde esa copia (commit `ee8a99d8`). Lo medido hoy en esa copia, mtime
2026-10-24 23:55 (-0600): `PD0 FW1: 5.22, FW2: 5.0`, `PD1 FW1: 5.22, FW2: 5.0`, EC 3.5.11, BIOS 5.36_0ACUM08. La busqueda
original fallo porque buscaba el texto "pd firmware" en `tools/` y `bin/` y no el nombre del archivo `dmidecode-t45`.

## Lo que SI falta (medido)

1. **Una sola copia, sin historial.** `dmidecode-t45.txt` se sobrescribe en cada arranque. Las filas de
   `/var/lib/blackbox/pstore/arranque.jsonl` (8, desde 2026-10-14) dicen `"firmware":"bios+t45"`, el nombre de la fuente, no
   los valores. No se puede saber que firmware PD tenia la unidad en un arranque anterior ni detectar un cambio.
2. **El episodio atascado del 2026-10-12 es anterior** a la primera fila de `arranque.jsonl` (2026-10-14): no hay version PD
   de ese momento en ningun archivo de bb.
3. **`bb reloj` no adjunta nada.** Un veredicto ATASCADO no lleva firmware PD, EC ni BIOS.
4. **`inicio()` pierde el episodio al recuperarse.** Con una muestra sana posterior con carga pone `bajo = None` y devuelve
   `None`; hoy devuelve `None` en esta unidad. Ademas `atom_gpu_telemetry.jsonl` empieza el 2026-10-16T17:16Z y no tiene
   ninguna muestra con carga >= 80 % y reloj < 1000 MHz (0 de 174539): la telemetria de la transicion ya no existe.
5. **Negociacion PD: sin fuente.** `dmesg` con root no tiene lineas de UCSI, Type-C ni PD en esta unidad (descubrimiento
   literal en `tasks/evidence/FEATURE-RELOJ-CAPTURA-PD-FIRMWARE-Y-TRANSICION-01/descubrimiento.txt`). Pendiente de la respuesta
   de NVIDIA sobre que herramienta usar.

## Alcance

- `arranque-forense` agrega a su fila los valores de PD0/PD1, EC y BIOS (no solo el nombre de la fuente). Es el helper root
  ya instalado: el cambio exige que Luis lo reinstale (`/usr/local/sbin/bb-root-run` es de root).
- `bb reloj` adjunta a cada ATASCADO las versiones de la ultima fila; sin fila o sin valores: `NOT_COLLECTED: <motivo>`.
- `inicio()` devuelve tambien el ultimo episodio cerrado, y el episodio se copia a un archivo aparte antes de que rote la
  telemetria.
- Negociacion PD: no se implementa hasta tener fuente. Solo lectura; sin ciclo de corriente.

## Control negativo exigido

Veredicto con fila que trae valores => campos con valor; fila antigua sin valores => `NOT_COLLECTED`; veredicto SANO => sin
los campos; `inicio()` sobre una serie con recuperacion => devuelve el episodio cerrado.

## Limite

La transicion real solo se captura si ocurre otra vez con el instrumento armado. Esta ficha no la provoca.
