---
id: FEATURE-RELOJ-CAPTURA-PD-FIRMWARE-Y-TRANSICION-01
kind: task
domain: GPU
title: "bb reloj: adjuntar firmware PD con historial por arranque y conservar el episodio sano -> atascado"
status: done
closed_at: 2026-10-27
closure_type: fixed
closure_reason: "arranque-forense agrega pd0/pd1/ec/bios de esa corrida a su fila (lista blanca, NOT_COLLECTED con motivo, nunca vacio, sin heredar la copia de otro arranque); bb reloj adjunta firmware a todo ATASCADO desde la ultima fila (NOT_COLLECTED: <motivo> si falta), SANO/INDETERMINADO sin el campo; inicio() devuelve ultimo_episodio_cerrado y copia cada episodio a episodios_reloj.jsonl sin duplicar. El codigo esta completo; la primera fila con valores solo existe tras la reinstalacion de Luis (seccion Para desplegar)."
evidence:
  fail: tasks/evidence/FEATURE-RELOJ-CAPTURA-PD-FIRMWARE-Y-TRANSICION-01/fail.txt
  pass: tasks/evidence/FEATURE-RELOJ-CAPTURA-PD-FIRMWARE-Y-TRANSICION-01/pass.txt
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

## Cierre (2026-10-27)

Hecho, por punto del alcance:

1. `adopted/root-scripts/arranque-forense.sh`: la fila de `arranque.jsonl` gana `pd0`, `pd1`, `ec` (de `dmidecode -t 45`) y
   `bios` (`Version:` de `dmidecode -t bios`). Solo se leen las copias escritas EN ESA corrida: si dmidecode falla, la copia
   del arranque anterior sigue en disco pero no se atribuye a este (`NOT_COLLECTED: dmidecode -t 45 fallo`). El script no
   tenia mecanismo de escape (lo que interpolaba eran constantes, `date` y `boot_id`); el texto de dmidecode entra solo si
   casa `^[A-Za-z0-9 ._:,+-]{1,80}$` con `LC_ALL=C`; si no, `NOT_COLLECTED: valor fuera de la lista blanca`. Sin eval, sin
   argumentos, `set -euo pipefail` como antes; los cinco campos de antes no cambian (bin/bb sigue casando la fila por
   `boot_id`, `bb incident` sigue leyendo la copia `dmidecode-t45.txt`). Las filas viejas siguen siendo JSON valido y se leen
   como `NOT_COLLECTED`.
2. Sellado regenerado con `python3 -m tools.bb_root_manifest --propose`: `adopted/pendiente-de-despliegue/bb-root-run.manifest.json`
   (arranque-forense `ad91459ff951...` -> `ee6d14a41a55abf25f011bb21ef891cbd795fda25c0dbf6f9008329fefcd70df`) y la
   descripcion en `manifest.src.json`. Nada instalado.
3. `tools/reloj_atascado.py`: `firmware(ruta=None)` lee la ULTIMA fila de `BB_ARRANQUE_JSONL` (por defecto
   `/var/lib/blackbox/pstore/arranque.jsonl`, la misma variable que `bin/bb`); `main` lo adjunta a todo ATASCADO (y
   `evento_arranque` lo registra en `reloj_arranque.jsonl` cuando el veredicto lo trae). Sin archivo, ilegible, vacio, roto o
   fila vieja: `NOT_COLLECTED: <motivo>`; campo suelto ausente en una fila nueva: ese campo `NOT_COLLECTED`.
4. `inicio(ruta, episodios=None)`: sigue en streaming; al ver una muestra sana con carga tras un episodio abierto lo CIERRA
   (`ultima_sana`, `primera_atascada`, `primera_recuperada`) en vez de descartarlo, y devuelve `ultimo_episodio_cerrado`
   (las claves de antes, si hay uno abierto, no cambian). Cada episodio, abierto o cerrado, con los ts tal como estan en la
   telemetria, se anade a `episodios_reloj.jsonl` junto a la telemetria (`BLACKBOX_DATA`), sin duplicar la misma tupla.
   `bb reloj --arranque` (una vez por boot) recorre la telemetria aunque salga SANO, para que el episodio cerrado se copie
   antes de que rote: ~1 s sobre los 235 MB (medido: `inicio()` sobre el archivo real, `segundos 1.0`, devolvio `None`).
5. 19 tests en `tests/test_reloj_atascado.py` (13 con `pd_firmware`, 6 con `episodio`), cada uno con su control negativo;
   corridos contra el codigo de antes: 19 de 19 en rojo (`assert None is not None` en el de la recuperacion; literal en
   `pass.txt`).

## Para desplegar (Luis)

Orden importa. El runner lee los scripts del checkout PRINCIPAL (`~/projects/blackbox/adopted/root-scripts`, por SUDO_UID) y
compara su sha256 con `/etc/bb-root-run/manifest.json`. Consecuencia medida en el codigo (`tools/bb_root_run.py`, rechazo
rc 3 por hash distinto): **desde que este commit este en el checkout principal y hasta que se reinstale el manifiesto,
`bb-arranque-forense.service` sale 3 en cada arranque y NO copia pstore, BERT ni dmidecode**. `bb status` lo marca (chk
"arranque forense"). Hacer los pasos 1-3 en la misma sesion en que se mergea.

0. En el checkout principal, con esta rama ya en master: `cd ~/projects/blackbox && git log -1 --oneline` y
   `sha256sum adopted/root-scripts/arranque-forense.sh adopted/pendiente-de-despliegue/bb-root-run.manifest.json tools/bb_root_run.py`.
   Esperado (si nada mas cambio en master desde este commit):
   - `ee6d14a41a55abf25f011bb21ef891cbd795fda25c0dbf6f9008329fefcd70df  adopted/root-scripts/arranque-forense.sh`
   - `bb8d9f3a05efe2420626181141c51257a1756a68bad4e1534f1d91461e5a6e65  adopted/pendiente-de-despliegue/bb-root-run.manifest.json`
   - `0c9f47a49e925e930661d5f544d1a8647cc0e8b3b38c989ee364bcec446c2e2f  tools/bb_root_run.py`
   Si difieren, otro commit cambio un script o el runner: leer que cambio antes de seguir.
1. Leer lo que se aprueba: `python3 -m tools.bb_root_manifest --propose` (desde el checkout principal, no desde un worktree:
   las rutas del comando salen de donde se corra). Imprime el manifiesto, el texto de los 11 scripts con su sha256 y, en la
   ultima linea, el `sudo sh -c '...'`. Revisar `arranque-forense.sh` (lineas nuevas: el bloque de `pd0..bios`, la lista
   blanca y los dos `while read` sobre las copias de esta corrida).
2. Correr esa ultima linea. Con los hashes de arriba es exactamente:
   `sudo sh -c 'set -e; install -d -m 0755 -o root -g root /etc/bb-root-run; install -m 0755 -o root -g root /home/lcasarin/projects/blackbox/tools/bb_root_run.py /usr/local/sbin/bb-root-run.nuevo; echo "0c9f47a49e925e930661d5f544d1a8647cc0e8b3b38c989ee364bcec446c2e2f  /usr/local/sbin/bb-root-run.nuevo" | sha256sum -c -; install -m 0644 -o root -g root /home/lcasarin/projects/blackbox/adopted/pendiente-de-despliegue/bb-root-run.manifest.json /etc/bb-root-run/manifest.json.nuevo; echo "bb8d9f3a05efe2420626181141c51257a1756a68bad4e1534f1d91461e5a6e65  /etc/bb-root-run/manifest.json.nuevo" | sha256sum -c -; install -m 0440 -o root -g root /home/lcasarin/projects/blackbox/adopted/pendiente-de-despliegue/etc_sudoers.d_bb-root-run /etc/sudoers.d/bb-root-run.nuevo; echo "46ec14fbc0e741f54ce025426808210bb0437dccea3eae234c4ff44fa7fc1e93  /etc/sudoers.d/bb-root-run.nuevo" | sha256sum -c -; visudo -c -f /etc/sudoers.d/bb-root-run.nuevo; mv -f /usr/local/sbin/bb-root-run.nuevo /usr/local/sbin/bb-root-run; mv -f /etc/bb-root-run/manifest.json.nuevo /etc/bb-root-run/manifest.json; mv -f /etc/sudoers.d/bb-root-run.nuevo /etc/sudoers.d/bb-root-run'`
   (runner y sudoers no cambiaron: se reinstalan iguales; solo cambia el manifiesto.)
3. `python3 -m tools.bb_root_manifest --check; echo rc=$?` -> `[bb-root-manifest] aprobados iguales: 11, cambios: 0,
   could_not_run: 0` y `rc=0`. Control negativo de este paso, medido hoy antes de reinstalar: `cambiado desde la aprobacion:
   arranque-forense (arranque-forense.sh: aprobado ad91459ff951, repo ee6d14a41a55)`, `aprobados iguales: 10, cambios: 1`,
   `rc=1`.
4. Escribir una fila sin esperar al proximo arranque: `systemctl --user start bb-arranque-forense.service` (o
   `sudo -n bb-root-run arranque-forense`; anade una fila mas para el mismo boot_id, como ya paso el 2026-10-14).
5. Comprobar que la nueva fila trae los valores: `tail -n 1 /var/lib/blackbox/pstore/arranque.jsonl` debe terminar en
   `"firmware":"bios+t45","pd0":"PD0 FW1: 5.22, FW2: 5.0","pd1":"PD1 FW1: 5.22, FW2: 5.0","ec":"3.5.11","bios":"5.36_0ACUM08"}`;
   y `python3 -c "from tools import reloj_atascado as r; print(r.firmware())"` debe imprimir un dict con esos cuatro valores.
   Control negativo de este paso, medido hoy: el mismo comando imprime `NOT_COLLECTED: la ultima fila de
   /var/lib/blackbox/pstore/arranque.jsonl (2026-10-25T05:55:32Z) no trae valores, solo la fuente firmware='bios+t45'; ...`.
   Si la fila trae `NOT_COLLECTED: ...` en algun campo, el motivo dice cual (dmidecode fallo, componente ausente o valor
   fuera de la lista blanca).

Revertir: reinstalar el manifiesto anterior no basta (el checkout principal tendria el script nuevo y el runner lo
rechazaria igual); hay que volver el script en master y repetir 1-2.

## Limites del cierre

- La primera fila con valores solo existe despues del paso 4 de arriba: hasta entonces `bb reloj` adjunta a un ATASCADO
  `NOT_COLLECTED: ... no trae valores` (medido hoy). El codigo esta completo; el dato depende del despliegue.
- El historial PD empieza con esa fila: no hay version PD de ningun arranque anterior (las 8 filas desde el 2026-10-14 solo
  dicen `bios+t45`), ni del episodio del 2026-10-12.
- `episodios_reloj.jsonl` solo se llena cuando corre `inicio()`: con un ATASCADO o con `bb reloj --arranque`. Un episodio
  que empiece y termine entre dos arranques y cuya telemetria rote antes del siguiente `--arranque` se pierde igual.
- `firmware()` lee la ULTIMA fila, que es la del arranque mas reciente: si el firmware PD cambio despues de ese arranque (un
  flasheo sin reiniciar), la version adjunta es la del arranque, no la viva.
- Negociacion PD: sin fuente, no implementada (punto 5 de "Lo que SI falta").
- SPEC.md (fila de `tools/reloj_atascado.py`, linea 283) dice que `inicio` "lo ubica en el historial": sigue siendo cierto y
  no menciona `firmware` ni `episodios_reloj.jsonl`. No se edito SPEC.md (invalidaria el ledger H1 por numero de linea).

## Despliegue verificado 2026-10-26 (19:42 -0600)

Luis corrio el bloque de instalacion; las tres sumas coincidieron y `visudo -c` dio "analisis OK".
- `python3 -m tools.bb_root_manifest --check` antes: `aprobados iguales: 10, cambios: 1`, rc=1 (control negativo); despues:
  `aprobados iguales: 11, cambios: 0, could_not_run: 0`, rc=0.
- `systemctl --user start bb-arranque-forense.service`: `Result=success ExecMainStatus=0`. Fila nueva de
  `/var/lib/blackbox/pstore/arranque.jsonl`: `"pd0":"PD0 FW1: 5.22, FW2: 5.0","pd1":"PD1 FW1: 5.22, FW2: 5.0","ec":"3.5.11","bios":"5.36_0ACUM08"`.
- `reloj_atascado.firmware()` devuelve esos cuatro valores con el `boot_id` de la fila. Las 8 filas anteriores (2026-10-14 a
  2026-10-25) no traen `pd0` (conteo 0): no hay version PD de ningun arranque previo, incluido el episodio del 2026-10-12.
