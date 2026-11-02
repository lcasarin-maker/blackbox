# Capas opt-in de captura de arranque y de pánico

La ATOM dejó de encender después de un cambio de kernel. Este directorio tiene las plantillas de cinco capas que
ayudan a ver qué pasa en el arranque y en un pánico. **Todas tocan el arranque o la red del kernel, así que ninguna
se activa por defecto.** Cada capa es opcional. Las aplica Luis a mano, con sudo, **una a la vez y con la consola
delante**, mediante `tools/opt_in_captura.sh`.

```bash
bash tools/opt_in_captura.sh                                  # = plan: modo seco, no escribe nada
bash tools/opt_in_captura.sh estado                           # capas aplicadas, si siguen intactas, qué recibió el kernel
bash tools/opt_in_captura.sh --kernel <version> plan <capa>   # qué escribiría y qué correría, con sus precondiciones
sudo bash tools/opt_in_captura.sh [--kernel <version>] aplica <capa>
sudo bash tools/opt_in_captura.sh retrocede <capa>
```

Cualquier invocación ambigua o incompleta (`aplica` sin capa, una capa que no existe, un verbo desconocido) no
escribe nada, muestra el plan y sale con 2. Una negativa sale con 3 y tampoco cambia nada. La herramienta nunca
reinicia la máquina: cada capa de arranque surte efecto en el siguiente arranque, que provoca Luis.

## Garantías de la herramienta

- **Valida antes de escribir.** Cada capa comprueba sus precondiciones y se niega ante cualquier `FALTA`.
  `grub.cfg` no se regenera en su sitio: se genera aparte con `grub-mkconfig -o` (lo mismo que hace `update-grub`)
  y se valida con `grub-script-check`. Si no hay `grub-script-check`, la capa se niega. También se niega si alguna
  línea `linux` queda sin argumentos o sin `root=`, si se pierde un `root=` que tenía el `grub.cfg` vigente o si el
  parámetro nuevo no llega a ninguna entrada. Solo cuando todo eso pasa sustituye al `grub.cfg` vigente.
- **Respalda byte a byte.** Antes de cambiar un fichero lo copia (con modo, dueño y fechas) a
  `/var/lib/blackbox/opt-in/<capa>/respaldo/` y anota su sha256 en `manifiesto`. Cada línea se anota *antes* del
  cambio que describe, así que una `aplica` cortada a medias también se puede retroceder (`estado` la muestra como
  `INCOMPLETA`).
- **Deshace si falla a medias.** Ante una negativa, un error o una señal, la aplica deshace en orden inverso lo
  que ya había escrito.
- **`retrocede` verifica antes de tocar.** Compara cada fichero con el sha256 que dejó `aplica`, y cada respaldo
  con el sha256 del original. Si algo cambió fuera de la herramienta, se niega sin cambiar nada y dice qué fichero
  cambió. Si el responsable es otra capa aplicada después (todas las de GRUB regeneran `grub.cfg`), dice cuál hay
  que retroceder primero: las capas se quitan en orden inverso.
- Con `--root <dir>` todo opera sobre una raíz falsa. Ahí un comando de la máquina sin su costura `BB_OPTIN_<CMD>`
  cuenta como ausente, así que una prueba nunca toca la máquina real (`tests/test_opt_in_captura.py`).

## Las capas

| Capa | Qué hace | Qué escribe | Riesgo | Retroceso |
|---|---|---|---|---|
| `netconsole-runtime` | `bb-netconsole.service` corre después de `network-online.target`, carga `netconsole` y crea el destino `/sys/kernel/config/netconsole/bb` (`extended=1`, `dev_name`, `local_ip`, `remote_ip`, `remote_mac`, `local_port=6665`, `remote_port=6666`) con los datos de `/etc/blackbox/netconsole.conf`. **No toca el arranque.** | `/usr/local/sbin/bb-netconsole-configfs`, `/etc/systemd/system/bb-netconsole.service`, el enlace en `multi-user.target.wants/` (equivale a `systemctl enable`, sin recargar systemd) | La NIC puede no soportar netpoll (ver abajo). Solo ve lo que se imprime después de que la red sube. | `systemctl stop`, después `rmdir` del destino y `modprobe -r netconsole`, y por último borra la unidad y su enlace |
| `netconsole-arranque` | Mete el driver de la NIC y `netconsole`, en ese orden, en `/etc/initramfs-tools/modules`, y añade `netconsole.netconsole=+6665@<ip-local>/<if>,6666@<ip-testigo>/<mac>` a la línea de comandos. Captura el arranque entero. | `/etc/initramfs-tools/modules`, `/etc/default/grub.d/90-bb-netconsole.cfg`, el initrd de `--kernel` (`update-initramfs -u -k`, con respaldo del initrd y de su sha en `/var/lib/initramfs-tools/`), `grub.cfg` | El más alto: si el netpoll del driver falla, cada `printk` del arranque pasa por él. Excluye a `netconsole-runtime`, porque dos destinos duplicarían cada mensaje. | Devuelve los dos ficheros, el initrd, su sha y `grub.cfg` desde el respaldo |
| `pstore-tras-panico` | Añade `crash_kexec_post_notifiers`. Así, ante un pánico, los notificadores y el volcado de kmsg a pstore corren *antes* del salto a kdump, y pstore guarda el pánico aunque kdump esté cargado. | `/etc/default/grub.d/91-bb-pstore-tras-panico.cfg`, `grub.cfg` | **Costo documentado: kdump queda algo menos fiable.** Ese código corre en un kernel ya roto y puede colgarse antes del kexec. | Devuelve `grub.cfg` y borra el `.cfg` |
| `grub-marca` | Instala `/etc/grub.d/09_bb_etapa`. Corre después del `load_env` de `00_header` y antes de cualquier entrada, y copia `recordfail` (el que dejó el arranque anterior), `default` y `boot_once` a `bb_prev_*` con `save_env`, antes de que la entrada vuelva a escribir `recordfail`. Se leen con `grub-editenv list`. | `/etc/grub.d/09_bb_etapa`, `grub.cfg` | `save_env` solo es seguro con `/boot/grub` en un sistema de ficheros simple. La capa **exige `/boot` en ext4 sin LVM ni RAID** (lo comprueba con `findmnt` y `lsblk`) y se niega si no se cumple. La plantilla repite la comprobación con `GRUB_FS`. | Devuelve `grub.cfg`, borra el script y quita las `bb_prev_*` del grubenv |
| `panic-temprano` | Añade `panic=30`. Hoy `kernel.panic` vale 0 hasta que sysctl aplica `99-blackbox-panic.conf` (10). Si un pánico anterior a ese momento no lo recoge kdump, la máquina se queda parada. | `/etc/default/grub.d/92-bb-panic-temprano.cfg`, `grub.cfg` | Bajo. Cuando corre sysctl, el valor pasa a 10. Con kdump cargado, el pánico salta a kdump igual. | Devuelve `grub.cfg` y borra el `.cfg` |

Los parámetros van en `GRUB_CMDLINE_LINUX_DEFAULT`, no en `GRUB_CMDLINE_LINUX`. Por eso las entradas *recovery
mode* quedan sin ellos y sirven de salida de emergencia.

**`netconsole.netconsole=` y no `netconsole=`.** En este kernel `netconsole` es un módulo: `modinfo` le da
vermagic y firma, según `tasks/backlog/FEATURE-FORUM-NETCONSOLE-01.md`. Un módulo recibe sus parámetros de la línea
de comandos como `modulo.param=`, que `modprobe` recoge de `/proc/cmdline`. Un `netconsole=` sin prefijo solo lo
consume la versión compilada dentro del kernel. Con el módulo, el kernel se lo pasa a init como variable de entorno
y el destino no llega a crearse. La forma con prefijo vale en los dos casos.

## Riesgo declarado: la NIC

La NIC de la ATOM es `enP7s7`, con el driver Realtek `r8127`, que es **fuera del árbol** (dkms). netconsole
necesita netpoll y no está verificado que `r8127` lo soporte. Si no lo soporta, habilitar el destino falla con
`netpoll: ... doesn't support polling` y el script lo reporta. El caso peligroso es otro: un netpoll que existe
pero está roto puede colgar un `printk`. Por eso el orden recomendado prueba primero `netconsole-runtime`, que no
toca el arranque. Si `r8127` no sirve, la alternativa es la interfaz ConnectX-7 (driver `mlx5_core`): se cambian
`DEV`, `LOCAL_IP` y `DRIVER` en `/etc/blackbox/netconsole.conf`.

Sin verificar: dentro del initramfs, `netconsole` puede cargarse antes de que udev renombre la interfaz. En ese
caso el destino de arranque no nace (`netconsole: <if> doesn't exist`). Se comprueba tras el primer arranque con
`journalctl -k -b | grep -i netconsole`.

## Comandos exactos, en el orden recomendado

Antes de nada, en el testigo: `nc -ul 6666 | tee netconsole-$(date +%F).txt`. En la ATOM:
`sudo install -m 0644 adopted/opt-in/netconsole.conf.ejemplo /etc/blackbox/netconsole.conf`, y después se
rellena. La herramienta solo lee ese fichero y rechaza los valores `<...>` sin rellenar.

1. `sudo bash tools/opt_in_captura.sh plan netconsole-runtime`, después
   `sudo bash tools/opt_in_captura.sh aplica netconsole-runtime` y `sudo systemctl start bb-netconsole.service`.
   Debe llegar `bb-netconsole-marca destino=bb dev=<if>` al testigo. Para la evidencia de cierre:
   `python3 -m tools.verify_netconsole --evidence tasks/evidence/FEATURE-FORUM-NETCONSOLE-01`.
2. `sudo bash tools/opt_in_captura.sh aplica panic-temprano`. Reiniciar con la consola delante y comprobarlo con
   `estado`, que lee `/proc/cmdline`.
3. `sudo bash tools/opt_in_captura.sh aplica pstore-tras-panico`, y reiniciar igual.
4. `sudo bash tools/opt_in_captura.sh aplica grub-marca`, reiniciar y comprobar `grub-editenv list | grep ^bb_prev_`.
5. Solo si el paso 1 probó que netpoll funciona: `sudo bash tools/opt_in_captura.sh retrocede netconsole-runtime`
   y después `sudo bash tools/opt_in_captura.sh --kernel <version-a-instrumentar> aplica netconsole-arranque`.

Cada `aplica` imprime su retroceso. Las capas de GRUB se retroceden en orden inverso al que se aplicaron.

## Retroceso de emergencia: la máquina no arranca

1. **En el menú de GRUB** (`GRUB_TIMEOUT_STYLE=menu`, `GRUB_TIMEOUT=5`: hay **5 s** para pulsar una flecha y
   detener la cuenta), se elige la entrada y se pulsa **`e`**. En la línea `linux` se borran
   `netconsole.netconsole=...`, `crash_kexec_post_notifiers` o `panic=30`. Si el initrd trae netconsole, se añade
   `modprobe.blacklist=netconsole`. Se arranca con **Ctrl-x** (o F10). El cambio dura solo ese arranque.
2. **O se elige la entrada del 6.17** en *Advanced options*: `6.17.0-1032-nvidia`, el kernel que arrancaba. Su
   initrd queda intacto salvo que `--kernel` fuera justamente ese. Su *recovery mode* no lleva ninguno de los
   parámetros de estas capas.
3. Ya dentro: `sudo bash tools/opt_in_captura.sh estado` y `sudo bash tools/opt_in_captura.sh retrocede <capa>`,
   de la última capa aplicada a la primera.

Sin verificar en DGX OS: en Ubuntu, tras un arranque que no llegó a completarse (`recordfail=1`), el menú espera
`GRUB_RECORDFAIL_TIMEOUT` (30 s por defecto) en vez de 5.

**Si `retrocede` se niega**, es porque algo cambió fuera de la herramienta, por ejemplo un `apt` que regeneró el
initrd o `grub.cfg`. El respaldo y el manifiesto siguen en `/var/lib/blackbox/opt-in/<capa>/`. A mano: se borra el
fichero de la capa (`/etc/default/grub.d/9x-bb-*.cfg` o `/etc/grub.d/09_bb_etapa`), se devuelve
`/etc/initramfs-tools/modules` desde `respaldo/` y se regenera con `sudo update-initramfs -u -k <version>` y
`sudo update-grub`.

## No implementado, y por qué

- **`sbsa_gwdt.action=1`** haría que el primer vencimiento del watchdog SBSA provoque un pánico (y con él kdump y
  pstore) en vez de esperar al reinicio en seco del segundo. No se implementa porque hay un reporte de IRQ
  bloqueada en `sbsa_gwdt`. Si la interrupción no llega, `action=1` no da pánico. Si llega en mal momento, puede
  convertir un cuelgue recuperable en un pánico. Hace falta antes reproducir y entender ese reporte.
- **ramoops** guardaría el log del kernel en una región de RAM que sobrevive a un reinicio en caliente. Para eso
  necesita una dirección y un tamaño **verificados** en `/proc/iomem` (una región reservada que nadie más use) y
  una prueba controlada (un pánico provocado con la consola delante) que demuestre que la región sobrevive al
  reinicio de esta placa. Una dirección equivocada corrompe memoria en uso. Ninguna de las dos cosas está hecha.

## Qué no está verificado

Nada de esto ha corrido en la ATOM. Las pruebas (`tests/test_opt_in_captura.py`) usan una raíz falsa con falsos
de `grub-mkconfig`, `grub-script-check`, `update-initramfs`, `lsinitramfs`, `findmnt`, `lsblk`, `systemctl`,
`modprobe` y `grub-editenv`. Demuestran la disciplina (modo seco, respaldo, sha256, negativas, deshacer), no el
efecto en el kernel real: que `r8127` soporte netpoll, que el destino de arranque nazca antes del renombrado, que
`save_env` escriba en el `/boot` real y que `crash_kexec_post_notifiers` deje un registro en el pstore EFI de
esta placa.

`update-initramfs` puede correr hooks de `/etc/initramfs/post-update.d/` que copien el initrd fuera del respaldo.
Si ese directorio no está vacío, `netconsole-arranque` se niega.
