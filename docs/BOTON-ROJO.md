# Botón rojo

Si vuelve a pasar un megacrash, o un ciclo de reinicios de segundos: un solo
comando, sin caracteres especiales, suspende todo lo que no es observación
pasiva y deja la máquina en su estado base. Corre como root, sin red, sin
sesión gráfica y aunque el manager de usuario todavía no haya arrancado.

## El comando

```
sudo rojo
```

Ver el plan sin tocar nada:

```
sudo rojo seco
```

Qué está suspendido, desde cuándo y cuándo vence:

```
sudo rojo estado
```

## Qué hace, en este orden

Primero lo que persiste al siguiente arranque, después lo vivo:

1. Manifiesto `~/.local/share/blackbox/suspensiones/<AAAA-MM-DD>-boton-rojo.json`
   (esquema `bb-suspension/1`: fecha, motivo, vence = hoy + 7 días, vigila,
   restaurar; por unidad sha256, modo, destino del enlace y estado
   enabled/active previo; por contenedor su restart policy), con fsync. Si el
   home no deja escribir, cae a `/var/lib/blackbox/rojo/` y lo dice.
2. Marca `/var/lib/blackbox/rojo.activo` (fecha y ruta del manifiesto).
3. Cada `.service`/`.timer` de `/home/lcasarin/.config/systemd/user` (symlinks
   a otros proyectos incluidos) que no esté en KEEP se RENOMBRA a
   `<unidad>.suspendido-<fecha>`. Nunca se borra; el rename conserva dueño y modo.
4. `docker update --restart=no` a los contenedores con GPU (runtime `nvidia` o
   `DeviceRequests` de GPU, corriendo o parados), para que docker no los
   levante en el siguiente arranque.
5. `systemctl --machine=lcasarin@.host --user stop --no-block` de las unidades
   renombradas y `daemon-reload`, en paralelo con `docker stop -t 5` de los
   contenedores con GPU que corren. Si el manager de usuario no está arriba, el
   stop se omite sin fallar: los renombres bastan.
6. Imprime qué suspendió, qué dejó (KEEP), los scopes transitorios que siguen
   corriendo, el `could_not_run` con su motivo, la línea de restauración y la
   duración.

Correrlo dos veces no suspende nada nuevo ni pisa el manifiesto: anexa una
«segunda corrida». Si una corrida se cortó a medias, la siguiente termina lo
que faltaba («continuacion»).

Tiempos medidos con shims (`tests/test_boton_rojo.py`, 2026-11-02): 0.16-0.21 s
sin contenedores; 5.17 s con contenedores cuando `docker stop` agota su `-t 5`.

## Qué deja corriendo

La lista KEEP vive en `adopted/boton-rojo-keep.txt` (instalada junto al
núcleo): `bb-muestreo-corte`, `bb-aviso-*`, `bb-guardia-proceso`,
`bb-portero`, `bb-vigilante-memavail`, `bb-vigilante-termico`,
`bb-reboot-verdict`, `bb-modulo-nvidia-registro`, `bb-arranque-forense`,
`bb-reloj-arranque`, `atom-gpu-telemetry`, `atom-crash-detector`,
`blackbox-*` y `ai-gpu-telemetry`. Las unidades de sistema y de paquetes no
están en `~/.config/systemd/user` y no se tocan. Una unidad que no está ni en
KEEP ni en `[suspende]` se suspende igual y sale marcada `SIN CLASIFICAR`.

## Restaurar

```
sudo rojo restaura
```

Renombra de vuelta solo lo que verifica por sha256, modo y destino del enlace;
lo que no cuadra lo reporta y no lo toca. Después `daemon-reload` y devuelve cada
unidad a su estado enabled/active previo, de una en una. El motor
(`ai-nemotron*`, `ai-ollama*`) y los contenedores con GPU (política de
reinicio y arranque) esperan confirmación:

```
sudo rojo restaura todo si
```

## Instalación (la corre Luis, desde `~/projects/blackbox`)

`sudo rojo` ejecuta una copia root-owned del núcleo, nunca el repo: un root no
corre código de un directorio que un usuario puede escribir.

```
sudo install -D -o root -g root -m 0644 tools/boton_rojo.py /usr/local/lib/blackbox/boton_rojo.py
```

```
sudo install -o root -g root -m 0644 adopted/boton-rojo-keep.txt /usr/local/lib/blackbox/boton-rojo-keep.txt
```

```
sudo install -o root -g root -m 0755 bin/rojo /usr/local/sbin/rojo
```

```
sudo rojo seco
```

Para comprobar que la copia instalada es la del repo (sale 0 si coinciden):

```
cmp tools/boton_rojo.py /usr/local/lib/blackbox/boton_rojo.py
```

Sin sudo, `bb rojo seco` y `bb rojo estado` corren desde el repo como usuario.

## Límites declarados

- No protege contra un corte de energía: es una acción, no una protección.
- No toca docker de bases de datos ni ningún contenedor sin GPU.
- No mata scopes transitorios (`run-*.scope`, `liberation_job_*`) ni procesos
  sueltos de otras sesiones: los lista como «siguen corriendo».
- Actúa sobre el usuario lcasarin (`BB_ROJO_USUARIO` para otro); no corre
  sobre otro usuario sin que se lo digan.
- La copia instalada no se actualiza sola: tras cambiar `tools/boton_rojo.py`
  o la lista KEEP hay que repetir los `install`.
- El camino root (`--machine=lcasarin@.host`) solo está probado con shims; en
  esta máquina solo corrió `seco` como usuario.
- Sin la lista KEEP no toca nada (sale 2): preferible a suspender los
  observadores.
