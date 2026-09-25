---
id: DEBT-ESCRITORIO-Y-ARNESES-COMPARTEN-CGROUP
kind: debt
title: "La ventana donde escribes y el arnes que la ahoga son hermanos en app.slice: arreglado en el repo, falta aplicarlo"
status: open
severity: P1
origin: detected
detector: {"rule": "bb/cgroup-memory-low", "confidence": 1.0}
satd_family: UNPROTECTED_RESOURCE
created: 2026-09-25
close_check: {"cmd": "grep -qvx 0 /sys/fs/cgroup/user.slice/user-1000.slice/user@1000.service/app.slice/memory.low", "expect": "exit_zero"}
---

## Que pasa

Medido el 2026-09-25 dentro de `app.slice`:

```
app-com.anthropic.Claude-<pid>.scope        19.74 GB actual   22.70 GB pico   <- ARNES
app-gnome-com.anthropic.Claude-<pid>.scope   1.04 GB actual    1.29 GB pico   <- VENTANA
atlas-api.service                            5.85 GB actual    8.00 GB pico
```

Los dos primeros son hermanos y **ninguno tenia proteccion**: `memory.low = 0`.
Cuando hay que expulsar paginas, las de la ventana en la que se escribe valen
lo mismo que las del arnes que esta usando veinte gigas.

## UNA AFIRMACION DE ESTA FICHA ERA FALSA, y esa es la parte importante

La primera version decia:

> El scope de una app de escritorio lleva el **pid en el nombre**, asi que no
> admite un drop-in estable. [...] Pide una decision de diseno, no un fichero
> mas.

**No es cierto.** systemd resuelve los drop-ins tambien por prefijo truncado en
cada guion -- el mismo mecanismo que esta cadena ya usaba para `user-.slice.d`
y que yo no vi que aplicaba tambien aqui. Comprobado sobre la unit viva:

```
$ printf '[Scope]\nMemoryLow=3G\n' > ~/.config/systemd/user/app-gnome-.scope.d/00-prueba.conf
$ systemctl --user daemon-reload
$ systemctl --user show app-gnome-com.anthropic.Claude-38380.scope -p MemoryLow -p DropInPaths
MemoryLow=3221225472
DropInPaths=/home/lcasarin/.config/systemd/user/app-gnome-.scope.d/00-prueba.conf
$ cat .../app-gnome-com.anthropic.Claude-38380.scope/memory.low
3221225472
$ cat .../app-com.anthropic.Claude-38380.scope/memory.low          # el ARNES
0
```

No hacia falta ninguna decision de diseno. Hacia falta comprobar el mecanismo
en vez de deducir su limite. Se deja escrito porque el error es del tipo que la
ley de este repo nombra: una deduccion sobre la forma de un nombre, sin ninguna
salida que pudiera contradecirla, dada por buena.

## Lo que ya esta en el repo

La cadena de `enable-privileged.sh` seccion 13 pasa de 5 a **7 niveles**:

| cgroup | `MemoryLow` | por que |
| --- | --- | --- |
| `user.slice` | 8G | raiz de la cadena |
| `user-<uid>.slice` | 8G | slice por UID |
| `session-<N>.scope` | 2G | aqui vive **Xorg** |
| `user@.service` | 6G | padre de session y app |
| `session.slice` | 2G | gnome-shell, dbus, pipewire |
| `app.slice` | 4G | **no se protege a si mismo: PASA la proteccion abajo** |
| `app-gnome-<*>.scope` | 2G | **la ventana** |
| `snap.antigravity.antigravity-<*>.scope` | 2G | el editor del episodio |
| `app-com.anthropic.Claude-<*>.scope` | **0, a proposito** | el arnes |

El reparto en cgroup v2 va a los hijos que la PIDEN. La piden los scopes de
ventana; no la pide el scope del arnes. **El arnes queda entero reclamable sin
tener que nombrarlo.**

`bb status` lo comprueba por el DATO -- lee los siete cgroups de la maquina, no
los ficheros -- con 13 tests y controles negativos: cada uno de los siete
eslabones en cero da FALTA, sin ventana da FALTA, y un arnes sin proteccion al
lado de una ventana protegida NO rompe la cadena (si la rompiera, el chequeo
estaria exigiendo proteger justo lo que se quiere reclamar).

## Por que sigue ABIERTA

Porque el repo no es la maquina. El dueno corrio `sudo ./enable-privileged.sh`
a las 07:15:14 y aplico los **cinco** niveles que existian entonces -- medido:
`user.slice` 6G, `user-1000.slice` 6G, `user@1000.service` 4G, `session.slice`
2G, `session-3.scope` 2G. Los dos niveles de ventana se escribieron despues, y
los numeros de la cadena subieron para poder atravesar `app.slice`.

`bb drift` lo dice: 3 divergentes y 3 ausentes. Hace falta una segunda corrida:

```
sudo ./enable-privileged.sh && systemctl --user daemon-reload
```

El `close_check` lee `app.slice/memory.low` en la maquina, no un fichero del
repo, asi que no puede cerrarse en falso. Hoy da rc=1.

## Limites declarados

- El prefijo de antigravity (`snap.antigravity.antigravity-.scope.d`) esta
  DERIVADO del nombre que el journal registro el 2026-09-25, no verificado
  sobre una unit viva -- no estaba corriendo. El mecanismo si esta verificado,
  sobre el scope de la ventana de Claude. Verificar al abrirlo:
  `systemctl --user show <scope> -p MemoryLow -p DropInPaths`.
- Proteger el scope de antigravity protege tambien los `pytest-xdist` que lanza
  dentro, que se vieron en las muestras de bb a las 03:03, 03:10 y 03:11. El
  scope no separa la UI de sus trabajadores. 2G es una fraccion pequena de lo
  que llega a usar, asi que lo protegido es un conjunto de trabajo.
- Esto NO prueba que la expulsion de memoria fuera lo que impedia escribir el
  2026-09-25. La contencion de CPU si quedo descartada con experimento (4 ms en
  reposo, 8 ms con 40 quemadores sobre 20 nucleos). La causa sigue sin probar en
  `DEBT-SLUGGISH-SIN-CAUSA-PROBADA`.
