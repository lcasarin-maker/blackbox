# sudo panic

Un solo comando para salir del problema. La máquina guarda un **punto de restauración** cada vez que demuestra
estar sana y jalando, como el punto de guardado de un videojuego, y `sudo panic` la regresa a ese punto. Si un
día se sube el kernel a 7 otra vez y se cae, `sudo panic` devuelve el kernel y la configuración de GRUB del
punto. Si la máquina entra en un bucle de reinicios de segundos y no da tiempo a teclear, **GRUB se arma solo**:
tras tres arranques seguidos sin confirmar arranca el kernel del punto.

Medido el 2026-11-02/03: el bucle de reinicios (arranques de 3 a 242 s con 7.0.0-1024-nvidia; timeout del GSP
y Xid 154 a los 21-28 s) siguió con las 22 unidades suspendidas. Lo cortó arrancar 6.17.0-1032-nvidia. Por eso
lo primero que guarda un punto, y lo primero que devuelve `panic`, es qué kernel arranca.

Sustituye al botón rojo (`sudo rojo`, 2026-11-02): la suspensión de todo lo no-KEEP sigue igual y es uno de
los pasos de `sudo panic`.

## El comando

```
sudo panic
```

Deshacer SOLO la suspensión (el kernel lo cambia el humano):

```
sudo panic restaura
```

El motor (`ai-nemotron*`, `ai-ollama*`) y los contenedores con GPU esperan confirmación:

```
sudo panic restaura todo si
```

No hay más subcomandos. `sudo panic` nunca reinicia: al final dice qué hizo y qué no pudo, y el reinicio lo
decide Luis.

## Qué guarda un punto

`/var/lib/blackbox/restore/<AAAA-MM-DDTHH-MM>/punto.json` (esquema `bb-restore-point/1`). Lo escribe
`bb-punto-restauracion.timer` cada 30 min, como root, **solo si el arranque demuestra estar sano**:

- uptime del arranque de 6 h o más;
- `journalctl -k -b <boot_id>` sin `rpcRecvPoll timedout` ni `Xid ...: 154` (la firma del GSP, la misma
  detección que `tools/reboot_verdict.gpu_del_boot`) y sin `Oops`, `BUG:` ni `Call Trace`;
- un journal que no se pudo leer niega el punto, nunca lo aprueba;
- si el arranque anterior acabó en `CORTE_ABRUPTO` (`reboots.jsonl`), se registra en el punto y no lo niega.

Contenido:

- el kernel en marcha (`uname -r`) y la entrada de GRUB que lo arranca, resuelta de `/boot/grub/grub.cfg`: el id
  de la entrada (`gnulinux-<versión>-advanced-<uuid>`), el del submenú (`gnulinux-advanced-<uuid>`) y la ruta
  que GRUB acepta como `default` (`<submenú>><entrada>`); también el `GRUB_DEFAULT` efectivo y el
  `grub-editenv list` de ese momento;
- copia, con sha256 y modo, de `/etc/default/grub`, `/etc/default/grub.d/*` y cada `/etc/grub.d/*_bb_*`;
- ruta, sha256, versión y srcversion del `nvidia.ko` cargado;
- versiones dpkg de `linux-image-<v>`, `linux-modules-nvidia-580-open-<v>`, `linux-modules-nvidia-fs-<v>` y
  `nvidia-driver-580-open` (un paquete no instalado sale `null`);
- las unidades de usuario que la suspensión ve, con su estado; las unidades de sistema `bb-*`; la política de
  reinicio de cada contenedor docker; una copia de `~/.local/share/blackbox/interruptores.json`.

Reglas:

- un punto idéntico al último válido (mismo kernel, misma entrada, mismos sha256) no se repite;
- se conservan los 3 válidos más recientes;
- al crear un punto con un kernel que ningún otro punto vigente tiene, `apt-mark hold` de los paquetes
  instalados de ese kernel, para que ni apt ni `autoremove` lo quiten. Al podar, `apt-mark unhold` solo de lo
  que retuvo esta herramienta (`hold_por_bb`) y solo si ningún punto que queda usa ese kernel. Un hold que puso
  Luis a mano no se suelta nunca;
- un punto cuyo kernel (`/boot/vmlinuz-<v>`, `/lib/modules/<v>`), cuyo `nvidia.ko`, cuya copia o cuya entrada
  de GRUB ya no existen se marca `invalido` (con el motivo) y nunca se elige. Un punto nuevo que ya nacería
  inválido no se crea;
- tras cada corrida, `bb_punto_entry` del grubenv nombra la entrada del punto válido más reciente; si no hay
  ninguno, se quita.

## Qué hace `sudo panic`, en este orden

Primero lo que persiste y es rápido, después lo vivo y al final lo lento. Sin red.

1. **(a)** Elige el punto válido más reciente y comprueba sus sha256, su kernel, sus módulos y su entrada en el
   menú. Uno que no cuadra queda `invalido` y se pasa al siguiente.
2. **(c1)** Devuelve a su estado del punto cada archivo de `/etc/default/grub` y `/etc/default/grub.d/` que
   difiera. El archivo de hoy se respalda antes en `/var/lib/blackbox/restore/panic-<fecha>/`. Lo que se añadió
   después del punto no se toca: se nombra.
3. **(b)** Fija el kernel del punto como arranque por defecto: `grub-set-default '<submenú>><entrada>'` si el
   `GRUB_DEFAULT` efectivo es `saved` (capa `grub-default-guardado`). Si no lo es, usa `grub-reboot` (vale solo
   para el próximo arranque) y lo dice en `COULD_NOT_RUN`.
4. **(e)** `bb_intentos=0` y `bb_punto_entry=<entrada>` en el grubenv.
5. **(d)** La suspensión de siempre (`tools/boton_rojo.py`): manifiesto con fsync, renombres
   `<unidad>.suspendido-<fecha>` de todo lo que no es KEEP (`adopted/boton-rojo-keep.txt`),
   `docker update --restart=no` y `docker stop` de los contenedores con GPU, `systemctl --user stop`.
6. **(c2)** Solo si (c1) cambió algo: `grub-mkconfig` a un archivo aparte, `grub-script-check`, comprueba que la
   entrada del punto sigue en el menú, y solo entonces sustituye a `/boot/grub/grub.cfg` (el viejo queda en el
   respaldo). Es el único paso lento.
7. **(f)** Imprime qué hizo, qué no pudo (`COULD_NOT_RUN`, con su motivo) y que no reinició.

Sin punto válido hace (d) igual, pone el contador a 0 y dice en voz alta
`COULD_NOT_RUN: sin punto de restauracion valido`: no inventa uno ni toca el kernel.

Tiempo medido con shims (`tests/test_panic.py::test_panic_tarda_segundos`, 2026-11-03): 0.31 s con punto,
configuración cambiada y regeneración de `grub.cfg` (el `grub-mkconfig` real tarda más; sin medir aquí).

## El autoarmado en GRUB

Para el bucle de segundos, sin teclear. Dos capas de `tools/opt_in_captura.sh` y un temporizador:

- **`grub-default-guardado`**: `/etc/default/grub.d/zzz-bb-grub-default-guardado.cfg` pone `GRUB_DEFAULT=saved`
  y `GRUB_SAVEDEFAULT=false`. `grub-mkconfig` lee `/etc/default/grub` y DESPUÉS `/etc/default/grub.d/*.cfg` en
  orden de glob (`/usr/sbin/grub-mkconfig`, líneas 160-168, GRUB 2.12-1ubuntu7.3): `zzz-` carga la última y gana
  sobre el `GRUB_DEFAULT` literal del archivo principal. La capa lo comprueba antes de escribir simulando ese
  orden, y se niega si algún `.cfg` posterior vuelve a fijar `GRUB_DEFAULT`. Al aplicarse, `saved_entry` se
  inicializa con lo que `GRUB_DEFAULT` nombraba hasta hoy (el título de 6.17): el kernel que arranca no cambia.
- **`grub-autoarmado`**: `/etc/grub.d/09_bb_zautoarmado`, que cae después de `00_header` (con `load_env` y la
  entrada por defecto ya resueltos) y de `09_bb_etapa` (grub-marca), y antes de `10_linux`. Lógica:
  - sin grubenv (`have_grubenv` vacío) no hace nada;
  - `bb_intentos` vacío cuenta como 0;
  - si GRUB lee 0, 1 o 2, lo sube a 1, 2 o 3 y lo guarda (`save_env`);
  - si lee 3 o más (o basura) y existe `bb_punto_entry`: `set default=$bb_punto_entry`, `bb_intentos=0` y deja
    `bb_autoarmado=1` para que el SO lo registre;
  - sin `bb_punto_entry` el contador se queda en 3 y el arranque no cambia;
  - si `default` llega vacío (`saved` sin `saved_entry`: GRUB arrancaría la primera entrada, el kernel más nuevo)
    y hay `bb_punto_entry`, usa el punto;
  - sin bucles: el bloque corre una vez por arranque; si `save_env` falla, GRUB sigue con el `default` que tenía.
- **`bb-arranque-ok.timer`** (180 s tras arrancar, como root): si el arranque lleva 180 s o más y su journal de
  kernel no tiene la firma del GSP, `grub-editenv /boot/grub/grubenv set bb_intentos=0`; registra una línea en
  `/var/lib/blackbox/arranque-ok.jsonl` (boot_id, fecha, kernel, sano, motivos, contador anterior, autoarmado,
  `fijado_a`) y quita `bb_autoarmado` tras anotarlo. La condición del GSP va más allá de «180 s» a propósito: un
  arranque del bucle duró 242 s, así que el tiempo solo lo habría dado por bueno.
- **Sin oscilación** (decisión de Luis, 2026-11-03): si GRUB dejó `bb_autoarmado=1` y ese arranque del punto
  resulta sano, `arranque-ok` hace `grub-set-default <bb_punto_entry>` y anota `"fijado_a": "<entrada>"`. Así el
  siguiente reinicio manual arranca el punto y no vuelve al kernel malo. Si `GRUB_DEFAULT` efectivo no es `saved`
  no fija nada y lo dice en `could_not_run` (`fijado_a: null`). Un arranque del punto que NO resulta sano no fija
  nada.

Tabla de verdad del contador (salida literal de `tests/test_grub_autoarmado.py`, que ejecuta el texto que emite
la plantilla con un intérprete del subconjunto de GRUB que usa):

| Arranque | `bb_intentos` que lee GRUB | Arranca | `bb_intentos` al acabar |
|---|---|---|---|
| 1 corto | (no existe) | saved | 1 |
| 2 corto | 1 | saved | 2 |
| 3 corto | 2 | saved | 3 |
| 4 | 3 | **punto** | 0, `bb_autoarmado=1` |
| 5 corto | 0 | saved | 1 (la marca sigue hasta que arranque-ok la lea) |
| largo (en cualquier punto) | n | saved | 0 (arranque-ok a los 180 s) |

Y cuando el arranque del punto SÍ sale sano (3 cortos, el punto largo, después reinicios):

| Arranque | `bb_intentos` que lee GRUB | Arranca | `bb_intentos` al acabar |
|---|---|---|---|
| 1-3 cortos | (no existe), 1, 2 | saved (kernel malo) | 1, 2, 3 |
| 4 largo | 3 | **punto** | 0; arranque-ok: `grub-set-default` al punto, `fijado_a` |
| 5, 6, 7 | 0, 1, 2 | **punto** (ya es `saved_entry`) | 1, 2, 3 |

## Cómo probarlo (lo corre Luis; la lógica en GRUB NO se ha probado en un arranque real)

Requisitos: las dos capas aplicadas, los dos timers activos y al menos un punto (`sudo grub-editenv list` muestra
`bb_punto_entry=...`).

1. Mirar el estado de partida:

```
sudo grub-editenv list
```

2. Fijar el contador en 3. GRUB lo leerá en 3 en el próximo arranque y arrancará el punto (con 2 lo leería en 2,
   lo subiría a 3 y arrancaría lo de siempre: así se prueba el incremento):

```
sudo grub-editenv /boot/grub/grubenv set bb_intentos=3
```

3. Reiniciar:

```
sudo reboot
```

4. Comprobar que arrancó el kernel del punto y que GRUB dejó la marca (antes de los 180 s):

```
uname -r
```

```
sudo grub-editenv list
```

   Debe salir el kernel del punto, `bb_intentos=0` y `bb_autoarmado=1`. Tras 180 s, la última línea de
   `/var/lib/blackbox/arranque-ok.jsonl` debe decir `"autoarmado": true` y `"fijado_a": "<entrada del punto>"`, la
   marca debe haber desaparecido y `saved_entry` debe ser la entrada del punto (un reinicio más arranca el punto):

```
sudo tail -n 1 /var/lib/blackbox/arranque-ok.jsonl
```

5. Retroceder la capa si algo no cuadra (deja grub.cfg y el grubenv como estaban):

```
sudo bash tools/opt_in_captura.sh retrocede grub-autoarmado
```

Si el punto y `saved_entry` son el mismo kernel (lo normal hoy: 6.17), el paso 4 solo distingue el autoarmado
por `bb_autoarmado=1` y por `bb_prev_default` (grub-marca), no por `uname -r`.

## Instalación (la corre Luis, desde `~/projects/blackbox`, un bloque a la vez)

`sudo panic` y los dos servicios ejecutan una copia root-owned, nunca el repo: un root no corre código de un
directorio que un usuario puede escribir.

0. Antes de actualizar las copias root-owned, crear `/etc/blackbox/rojo.json`
   fuera del repo: JSON con `usuario` igual a la cuenta local operadora.
   Partir de `config/rojo.json.example`, completar el dato local y crear el archivo
   con propietario root y modo 0600 (directorio /etc/blackbox con modo 0755).
   Debe poder leerlo root; BB_ROJO_CONFIG permite otra ruta y BB_ROJO_USUARIO
   prevalece. Comprobar localmente la clave y la cuenta antes del siguiente paso.
   `bb-punto-restauracion.timer` y `bb-arranque-ok.timer` tambien construyen ese
   contexto como root y dependen de esta configuracion. Mantener las copias
   instaladas hasta crearla; los destinos de emergencia jamas se adivinan.

1. El núcleo y lo que importa (lista exacta en `tools/panic.INSTALA`, comprobada por
   `tests/test_panic.py::test_la_copia_instalada_importa_con_python_I_y_solo_con_lo_de_INSTALA`):

```
sudo install -d -o root -g root -m 0755 /usr/local/lib/blackbox/tools
```

```
sudo install -o root -g root -m 0644 -t /usr/local/lib/blackbox/tools tools/__init__.py tools/panic.py tools/punto_restauracion.py tools/boton_rojo.py tools/modulo_nvidia_registro.py tools/reboot_verdict.py tools/etapas_arranque.py tools/hallazgo.py tools/medidor_energia.py tools/observador_ping.py tools/ultimo_aliento.py tools/interruptores.py adopted/boton-rojo-keep.txt
```

2. El comando:

```
sudo install -o root -g root -m 0755 bin/panic /usr/local/sbin/panic
```

3. Si `sudo rojo` llegó a instalarse, retirarlo (renombrar, no borrar):

```
test -e /usr/local/sbin/rojo && sudo mv /usr/local/sbin/rojo /usr/local/sbin/rojo.retirado-2026-11-03
```

4. Las unidades de sistema:

```
sudo install -o root -g root -m 0644 -t /etc/systemd/system systemd/bb-punto-restauracion.service systemd/bb-punto-restauracion.timer systemd/bb-arranque-ok.service systemd/bb-arranque-ok.timer
```

```
sudo systemctl daemon-reload
```

5. La capa `grub-default-guardado` (ver el plan primero):

```
sudo bash tools/opt_in_captura.sh plan grub-default-guardado
```

```
sudo bash tools/opt_in_captura.sh aplica grub-default-guardado
```

6. Reiniciar UNA vez y comprobar que sigue arrancando 6.17 (`saved_entry` nombra el título de hoy; si no
   cuadrara, GRUB arrancaría la primera entrada, que es el kernel más nuevo):

```
sudo reboot
```

```
uname -r
```

7. Los dos temporizadores. `--now` sobre un `OnBootSec` ya vencido dispara al momento: `arranque-ok` pone el
   contador a 0 y, si el arranque lleva 6 h sano, nace el primer punto:

```
sudo systemctl enable --now bb-arranque-ok.timer
```

```
sudo systemctl enable --now bb-punto-restauracion.timer
```

8. Comprobar que hay punto y que el grubenv lo nombra:

```
sudo ls /var/lib/blackbox/restore/
```

```
sudo grub-editenv list
```

9. La capa `grub-autoarmado`, con el punto ya publicado:

```
sudo bash tools/opt_in_captura.sh aplica grub-autoarmado
```

10. La prueba de la sección anterior.

Para comprobar que la copia instalada es la del repo (sale 0 si coinciden):

```
cmp tools/panic.py /usr/local/lib/blackbox/tools/panic.py
```

`bb panic` sin sudo solo recuerda el comando de verdad: sin root no toca nada.

## Límites declarados

- No revierte firmware (SOCFW, EC, USBPD) ni hardware dañado: desde Linux no se puede.
- Un punto es tan bueno como su criterio de «sano»: 6 h sin la firma del GSP ni Oops. Un kernel que falla
  después de 6 h, o de otra forma, puede quedar guardado como bueno, y `panic` elige el punto válido más
  reciente.
- El autoarmado NO se probó en un arranque real (could_not_run): solo su sintaxis (`grub-script-check`) y su
  lógica (intérprete del subconjunto de GRUB sobre el texto emitido). El procedimiento está arriba.
- El autoarmado fija el punto solo si el arranque del punto sale sano y `GRUB_DEFAULT` es `saved`. Si el propio
  punto también muere antes de 180 s, nada se fija: el siguiente arranque vuelve a `saved_entry` (el kernel de
  antes) y el contador vuelve a empezar.
- Si `bb_punto_entry` nombra una entrada que no existe en el menú, GRUB arranca la primera entrada (el kernel más
  nuevo). El servicio solo publica la de un punto válido, cuya entrada se comprueba en `grub.cfg` en cada corrida.
- `apt-mark hold` deja a propósito los kernels de los puntos sin actualizar ni quitar: una subida de esos paquetes
  queda retenida hasta que la poda los suelte.
- Con `recordfail=1` (el arranque anterior no terminó), el `00_header` de Ubuntu espera 30 s en el menú
  (`GRUB_RECORDFAIL_TIMEOUT`, 30 por defecto) antes de arrancar: el autoarmado funciona igual, pero cada vuelta
  del bucle tarda esos 30 s más.
- `sudo panic` no protege contra un corte de energía: es una acción, no una protección.
- La copia instalada no se actualiza sola: tras cambiar algo de `tools/panic.INSTALA`, repetir el bloque 1.
- `sudo panic` no toca contenedores sin GPU ni mata scopes transitorios ni procesos sueltos (los lista).
