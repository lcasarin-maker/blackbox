# Etapas de arranque: hasta dónde llega un arranque

## Por qué

Todo lo forense de bb eran unidades de USUARIO que corren después de `default.target`: en un arranque que
no termina no corre ninguna, y no queda registro de hasta qué etapa llegó. Esto lo registra desde el
sistema, sin depender de que el arranque termine. Lo motivó la ATOM que no volvió a encender tras pasar
al kernel 7.0.0-1019-nvidia, instalar el módulo parchado (`tools/dmem_modulo.sh`) y retrocederlo.

Cada etapa deja, en este orden:

1. `<3>bb-etapa <etapa> <boot_id>` en `/dev/kmsg`: llega aunque el disco no, al buffer del kernel
   (pstore en un panic, el journal, `journal-udp-forward`) y a la consola serie `ttyS0`. Es nivel 3 y no 4
   porque `kernel.printk = 4 4 1 7` (procps, `/etc/sysctl.d/10-console-messages.conf` en Ubuntu 24.04)
   solo imprime en consola los niveles menores que 4. En el journal aparece con prioridad `err`.
2. Una línea `{boot_id, etapa, monotonic, realtime}` en `/var/lib/blackbox/arranque/etapas.jsonl`
   (root 0755/0644, legible sin sudo), con fsync del archivo y del directorio. A los 256 KiB rota a
   `etapas.jsonl.1`.

Una falla al escribir nunca rompe el arranque: `etapa-marca.sh` la anuncia en el journal y sale 0.

## Etapas

| etapa | la pide | corre cuando |
| --- | --- | --- |
| `local-fs` | `local-fs.target.d/bb-etapa.conf` | los sistemas de archivos locales están montados |
| `basic` | `basic.target.d/bb-etapa.conf` | `basic.target` activo |
| `gpu-lista` (rama) | `basic.target.d/bb-etapa.conf` | `timeout 10 nvidia-smi -L` lista una GPU; reintenta cada 10 s, hasta 20 veces |
| `network-online` (rama) | `network-online.target.d/bb-etapa.conf` | la red está en línea (si algo pide ese target) |
| `multi-user` | `multi-user.target.d/bb-etapa.conf` | `multi-user.target` activo |
| `gdm` | `gdm.service.d/bb-etapa.conf` | `gdm.service` (gdm3) arrancó |
| `graphical` | `graphical.target.d/bb-etapa.conf` | `graphical.target` activo |
| `sesion-<uid>` | `user@.service.d/bb-etapa.conf` | el gestor de usuario de ese uid quedó listo |

La cadena es `local-fs < basic < multi-user < gdm < graphical < sesion-usuario`; `gpu-lista` y
`network-online` corren en paralelo y no cuentan para la última etapa. `sesion-<uid>` va por uid porque GDM
levanta su propio `user@` (uid de sistema) para la pantalla de entrada: solo un uid ≥ 1000 cuenta como
sesión de una persona. La guardia del parche dmem anota también su decisión (`guardia-dmem-gpu-ok` o
`guardia-dmem-retrocede`).

Nada se habilita con `systemctl enable`: cada etapa la pide un drop-in (`Wants=` + `Before=`) de la unidad que
la marca, así que retroceder es borrar archivos y no queda ningún enlace `.wants/` colgando.

## Instalación (Luis, con sudo, desde el checkout principal con la rama ya en master)

El sha256 es el de `etapa-marca.sh` revisado; `tests/test_etapas_arranque.py` falla si este archivo queda viejo.
La copia de root se instala como `.nuevo`, se compara y solo entonces se mueve: si el archivo del repo cambió
entre la revisión y la instalación, no se instala nada.

```sh
# instala
cd ~/projects/blackbox
d=adopted/system-units
sudo install -m 0755 -o root -g root "$d/etapa-marca.sh" /usr/local/sbin/bb-etapa-marca.nuevo
echo "15c8e5fc1389cbc0b604857e985c1a7c5316a3233936723a933624ae0ca6a722  /usr/local/sbin/bb-etapa-marca.nuevo" | sha256sum -c -
sudo mv -f /usr/local/sbin/bb-etapa-marca.nuevo /usr/local/sbin/bb-etapa-marca
sudo install -m 0644 -o root -g root "$d/bb-etapa@.service" /etc/systemd/system/bb-etapa@.service
for u in local-fs.target basic.target network-online.target multi-user.target graphical.target gdm.service user@.service bb-etapa@gpu-lista.service; do
  sudo install -D -m 0644 -o root -g root "$d/$u.d/bb-etapa.conf" "/etc/systemd/system/$u.d/bb-etapa.conf"
done
```

Comprobar sin recargar nada. Se espera solo silencio, salvo que `gdm.service` no exista con ese nombre
(entonces la etapa `gdm` no se marcará nunca: avisar, porque el drop-in tendría que ir en la unidad real):

```sh
# comprueba
systemctl cat gdm.service >/dev/null && echo "gdm.service existe"
sudo systemd-analyze verify bb-etapa@basic.service bb-etapa@gpu-lista.service graphical.target network-online.target "user@$(id -u).service"
```

`daemon-reload` NO hace falta: el siguiente arranque lee las unidades nuevas igual. Con contenedores que usan la
GPU en marcha (vLLM), recargar systemd puede quitarles la GPU (hilo 352743 del foro; por eso `dmem_modulo.sh`
tampoco recarga). Solo con esos contenedores parados:

```sh
# recarga
sudo systemctl daemon-reload
```

Tras el siguiente arranque, sin sudo:

```sh
# verifica
cat /var/lib/blackbox/arranque/etapas.jsonl
journalctl -k -b | grep bb-etapa
systemctl list-units 'bb-etapa@*'
```

Esperado: una línea por etapa con el `boot_id` de `/proc/sys/kernel/random/boot_id`, las mismas en el
kernel, y las unidades `active (exited)`.

## Resumen del arranque anterior

`python3 -m tools.etapas_arranque` (sin sudo, desde el repo), en el primer arranque sano (el actual ya llegó a
`multi-user`), anota una fila en `~/.local/share/blackbox/etapas_arranque.jsonl` (o `$BLACKBOX_DATA`) con la
última etapa del arranque anterior, las que le faltaron, sus ramas y decisiones, y el contexto del actual:
bootstatus y sysfs de cada watchdog (sin abrir `/dev/watchdog`), la línea de comandos del kernel, srcversion y
firmante del módulo nvidia y `dmem.capacity`. Correrlo otra vez en el mismo arranque no escribe nada;
`--imprime` muestra la fila sin escribirla. Esquema y códigos de salida: el docstring de `tools/etapas_arranque.py`.
Lo corre `bb-reboot-verdict.service` (`systemd/` y su copia adoptada) como `ExecStartPre=-`, una vez por arranque,
3 min después de iniciar y justo antes del veredicto, que lee las etapas. El `-` es deliberado: su rc 1 (el
arranque actual aún no llegó a `multi-user`) o rc 2 (no hay `etapas.jsonl`) no impide el veredicto. En una
máquina con la unidad vieja instalada no corre hasta reinstalarla (`~/.config/systemd/user/`).

Límite: un arranque que no llegó a `local-fs` no deja marca en disco, y el resumen no lo distingue de uno que no
existió. Ese caso solo lo delata la ausencia de `bb-etapa` en la consola serie o en pstore.

## Retroceso (Luis, con sudo)

No hay `systemctl disable`: nada se habilitó. Borrar los drop-ins quita los `Wants=`; `rmdir` solo quita un
directorio `.d` que quedó vacío (`user@.service.d` conserva `99-blackbox-escritorio.conf`).

```sh
# retrocede
for u in local-fs.target basic.target network-online.target multi-user.target graphical.target gdm.service user@.service bb-etapa@gpu-lista.service; do
  sudo rm -f "/etc/systemd/system/$u.d/bb-etapa.conf"
  sudo rmdir --ignore-fail-on-non-empty "/etc/systemd/system/$u.d"
done
sudo rm -f /etc/systemd/system/bb-etapa@.service /usr/local/sbin/bb-etapa-marca
```

Después, la misma regla de `daemon-reload` que en la instalación: no hace falta (el siguiente arranque ya no las
carga) y solo se corre con los contenedores de GPU parados. Las marcas ya escritas se conservan como evidencia
en `/var/lib/blackbox/arranque/`.

Nada de esto toca GRUB, la línea de comandos del kernel ni el initramfs.

## La guardia del parche dmem (`tools/dmem_modulo.sh`)

- Cada `nvidia-smi -L` lleva `timeout 10` y cuenta solo si lista una GPU. Reintenta durante 120 s; si la GPU no
  responde, anota `guardia-dmem-retrocede` y retrocede. Si responde, anota `guardia-dmem-gpu-ok`.
- La unidad que genera `instala` ya no espera a `multi-user.target`: `DefaultDependencies=no`, va después de
  `local-fs.target` y `systemd-modules-load.service`, la pide `basic.target` y lleva `TimeoutStartSec=300`.
  Una unidad ya instalada conserva la versión anterior hasta el próximo `instala`. El código nuevo de la guardia
  sí corre desde ya, porque la unidad llama al script del repo.
- `retrocede --kernel <versión>` y `estado --kernel <versión>` actúan sobre `/lib/modules/<versión>` y no sobre el
  kernel en marcha. `retrocede` solo borra lo instalado en `updates/` de ese kernel, conserva las líneas de otros
  kernels y corre `depmod -a <versión>`. Si ese kernel no tiene `updates/`, sale 0 sin tocar nada.
- `instala` se niega si algún `.ko` no está firmado con la llave de `MOK.der`: compara el `sig_key` de `modinfo`
  con la serie del certificado (`openssl x509 -serial`). Esto se suma a la comprobación de que la llave esté
  enrolada (`mokutil --test-key`).
