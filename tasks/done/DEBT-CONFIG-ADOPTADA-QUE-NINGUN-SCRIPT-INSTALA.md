---
id: DEBT-CONFIG-ADOPTADA-QUE-NINGUN-SCRIPT-INSTALA
kind: debt
title: "15 configuraciones adoptadas carecían de instalador; editar esos archivos no cambiaba la máquina"
status: done
closure_type: fixed
closed_at: 2026-09-28
severity: P1
origin: detected
detector: {"rule": "blackbox/adoptado-sin-instalador", "confidence": 1.0}
satd_family: MISSING_COVERAGE
created: 2026-09-28
close_check: {"cmd": "bash tools/config_entregable.sh", "expect": "exit_zero", "porque": "el sujeto es la relacion entre adopted/ y los instaladores, y el comprobador la lee de los dos ficheros -- no de una declaracion. Hoy sale 1 nombrando los 15, y no se satisface redactando: hay que anadir cada uno a un instalador o declararlo solo-registro con su motivo. Se invoca via `bash` porque es lo que .simplecode/build_tools.txt declara y backlog-verifier solo confia en esa lista."}
evidence:
  pass: tasks/evidence/DEBT-CONFIG-ADOPTADA-QUE-NINGUN-SCRIPT-INSTALA/pass.txt
  fail: tasks/evidence/DEBT-CONFIG-ADOPTADA-QUE-NINGUN-SCRIPT-INSTALA/fail.txt
  e2e: tasks/evidence/DEBT-CONFIG-ADOPTADA-QUE-NINGUN-SCRIPT-INSTALA/e2e.txt
reason: "CERRADO 2026-09-28. Los 15 resueltos uno a uno: ONCE pasan a instalarse desde `enable-privileged.sh` (el techo de app.slice -- el fichero que costo la ficha --, el vigilante de NVRM OOM con su timer y su script, el bloqueo de clock de la GPU, los tres sysctl adoptados, el drop-in de earlyoom y el de sysstat-collect), cada uno con su entrada en `--revert`; y CUATRO se declaran solo-registro con su motivo medido: dos los instala un paquete (`dpkg -S` los reclama), `bb-usable.service` SI tiene camino pero desde `systemd/bb-usable.service`, y `/etc/default/kdump-tools` es la plantilla del paquete mas una linea local, asi que copiarla entera revertiria en silencio la plantilla nueva de una actualizacion. De paso desaparece una fuente de verdad duplicada: la seccion 8a escribia el fichero de modprobe con un heredoc identico al adoptado, o sea que `bb drift` vigilaba la copia que el script NO usaba. Y se cierra el limite que la propia ficha declaraba -- que el comprobador mira si el instalador NOMBRA el fichero, no si lo copia -- con dos tests que leen `--dry-run`: contra el arbol de antes (5cd2ca6) fallan nombrando los 15, contra este pasan. La maquina no cambia con esto: `bb drift` da 0 divergentes y 0 ausentes, o sea que los 11 ya estaban puestos a mano; lo que cambia es que ahora hay con que reponerlos."
---
## Root Cause

### Que pasa

`adopted/system-config/` tiene **27 ficheros**. `enable-privileged.sh` instala
**12**. Los otros **15** son un retrato de lo que hay en la maquina que ningun
script del repo puede volver a aplicar -- comprobado con `grep -rl` sobre todo
el repo, no solo sobre ese script.

Entre esos 15 hay cosas que no son accesorias:

| fichero | que es |
|---|---|
| `etc_systemd_system_bb-usable.service` | la unit del vigilante que REINICIA la maquina |
| `home_lcasarin_.config_systemd_user_app.slice.d_99-blackbox.conf` | el techo de memoria del escritorio y los arneses |
| `usr_local_bin_nvrm-watch.sh` + su `.service` y su `.timer` | el vigilante de la GPU |
| `etc_security_limits.d_*`, `etc_sysctl.d_99-sysrq.conf`, ... | limites y sysctl del arranque |

Y `bb drift` los compara igual, asi que puede reportar una divergencia cuyo
remedio no existe en el repo. Un adoptado sin instalador **no es
configuracion: es una fotografia.**

### Lo que costo el 2026-09-28, medido

No es un riesgo hipotetico. Ese dia se voto un reparto nuevo de techos de
memoria y se editaron los tres dentro de `adopted/`:

```
app.slice    memory.max = 51539607552   (48 GiB, votado 42)  <- NO se movio
docker.slice memory.max = 15032385536   (14 GiB)             <- si
system.slice memory.max = 12884901888   (12 GiB)             <- si
```

`sudo ./enable-privileged.sh` se corrio **dos veces**. El techo de `app.slice`
no se movio porque ese fichero es uno de los 15. Docker y system si bajaron, asi
que los compromisos pasaron de **121.8 GiB sobre 121.1** (holgura -0.8) a
**124.1 sobre 121.1** (holgura -3.1): el estado intermedio quedo **peor que el
de partida**, y por una razon que no se ve desde el repo. Se cerro copiando el
fichero a mano, fuera de todo script.

### Por que no basta con "acordarse"

El fallo no fue olvidar un paso: fue que **editar el fichero y aplicarlo se
ven iguales desde el repo**. Es el mismo patron que
DEBT-UNA-BAJADA-MOMENTANEA-ABSUELVE-UN-COLAPSO, cerrada ese mismo dia -- codigo
correcto en disco con el defecto todavia en memoria-- y por eso su criterio de
cierre mira la maquina y no el fichero. Aqui pasa un escalon antes: el fichero
del repo ni siquiera tiene por donde llegar.

### Como se cierra

Cada uno de los 15, una de dos:

1. **Se anade a un instalador**, con su `run cp` y su entrada en el `--revert`,
   como ya tienen los 12 que si lo estan.
2. **Se declara solo-registro** en `adopted/solo-registro.txt` con el motivo por
   el que no se instala -- por ejemplo, que lo instala el paquete de un tercero
   y este repo solo guarda copia para poder compararlo.

Ninguna de las dos es una declaracion vacia: la primera cambia la maquina, y la
segunda obliga a escribir por que este repo guarda algo que no aplica.

**Como se cerro, el 2026-09-28: once por la primera via y cuatro por la
segunda.** Los once entraron al instalador con su `cp`, su destino y su entrada
en `--revert`; los cuatro estan en `adopted/solo-registro.txt`, y los cuatro
motivos son medidas, no opiniones -- dos `dpkg -S` que reclaman el fichero, un
`diff` que prueba que la unit sale de otro fichero del repo, y un `diff` contra
la plantilla del paquete que dice exactamente que linea es local.

`tools/config_entregable.sh` lo verifica y tiene los tres desenlaces (0 cubierto,
1 hueco, 2 `COULD_NOT_RUN` si falta el directorio o el instalador).

### Limites declarados

El comprobador busca el **nombre del fichero** dentro del instalador. Un script
que construyera la ruta por partes lo enganaria, y un instalador que nombre un
fichero sin llegar a copiarlo pasaria igual. Detecta la ausencia de mencion, que
es el fallo medido hoy, no la correccion de la instalacion. La segunda mitad la
cubre `bb drift`, que compara contenidos contra la maquina.

Tampoco juzga los 12 que si tienen camino: que `enable-privileged.sh` los
mencione no prueba que los copie bien. El 2026-09-28 se encontro, en ese mismo
script, que sus mensajes anunciaban `MemoryMax=32G` mientras el fichero que
copiaba decia 16G, y que su control negativo pedia esperar `34359738368` cuando
el valor real era `17179869184` -- o sea que seguirlo hacia concluir que el
techo NO estaba puesto cuando si lo estaba. Eso se corrigio, pero nada impide
que vuelva a divergir.

## Verification Evidence

El `close_check` pasa de 1 a 0, y el sujeto que mide es la relacion entre
`adopted/` y los instaladores, no una declaracion:

```
$ bash tools/config_entregable.sh
adoptados: 27   sin camino a la maquina ni declaracion: 0
OK: cada adoptado se instala o esta declarado solo-registro.
rc=0
```

Ese comprobador busca el NOMBRE del fichero dentro del instalador, que es su
limite declarado. Asi que el cierre NO se apoya en el: se apoya en lo que el
instalador dice que HARIA, que es `--dry-run` y no necesita root.

```
$ ./enable-privileged.sh --dry-run | grep -c "cp adopted/system-config/"
23
```

23 = los 12 que ya estaban mas los 11 nuevos. Uno por uno, y con el control
negativo al lado -- los cuatro declarados solo-registro tienen que salir 0, o
el instrumento no sabria decir que no:

```
  etc_modprobe.d_99-blackbox-uvm.conf                               1
  etc_sysctl.d_99-freeze-panic.conf                                 1
  etc_sysctl.d_99-nvidia-unified-memory.conf                        1
  etc_sysctl.d_99-sysrq.conf                                        1
  etc_systemd_system_atom-clock-lock.service                        1
  etc_systemd_system_earlyoom.service.d_override.conf               1
  etc_systemd_system_nvrm-watch.service                             1
  etc_systemd_system_nvrm-watch.timer                               1
  etc_systemd_system_sysstat-collect.timer.d_override.conf          1
  home_lcasarin_.config_systemd_user_app.slice.d_99-blackbox.conf   1
  usr_local_bin_nvrm-watch.sh                                       1
  --- control negativo: los declarados solo-registro ---
  etc_default_kdump-tools                                           0
  etc_systemd_system_bb-usable.service                              0
  etc_security_limits.d_nv-limits.conf                              0
  etc_security_limits.d_99-nv-spark-limits.conf                     0
```

El camino de vuelta tambien se comprobo, porque un instalador que no sabe
deshacer lo que hizo es una via de una sola direccion:
`./enable-privileged.sh --dry-run --revert` lista las ocho retiradas nuevas,
cada una con el efecto que tiene sobre la maquina escrito al lado.

**La maquina no cambia con esto**, y decirlo importa para no vender una mejora
que no ocurrio: `bb drift` da `revisados: 39   divergentes: 0   ausentes: 0`,
o sea que los 11 ya estaban puestos -- a mano, uno de ellos esa misma tarde.
Lo que cambia es que ahora existe con que reponerlos.

Evidencia literal: `tasks/evidence/DEBT-CONFIG-ADOPTADA-QUE-NINGUN-SCRIPT-INSTALA/cierre.txt`

### Los cuatro que NO se instalan, y por que

Estan en `adopted/solo-registro.txt` con su medicion. Resumen:

| fichero | por que no se copia |
|---|---|
| `etc_security_limits.d_nv-limits.conf` | `dpkg -S` lo reclama: paquete `nv-limits` |
| `etc_security_limits.d_99-nv-spark-limits.conf` | `dpkg -S` lo reclama: paquete `nvidia-spark-limits` |
| `etc_systemd_system_bb-usable.service` | SI tiene camino: la seccion 5 lo escribe desde `systemd/bb-usable.service` sustituyendo la ruta del repo. Verificado byte a byte (`diff` rc=0, y rc=1 contra otro fichero) |
| `etc_default_kdump-tools` | es la plantilla del paquete `kdump-tools` 1:1.10.3ubuntu2 mas UNA linea local (`KDUMP_SKIP_VMCORE=1`); copiarla entera revertiria en silencio la plantilla nueva de una actualizacion |

## Regression Test

Dos tests nuevos en `tests/test_config_entregable.py`, y miden lo que el
`close_check` no puede: que el instalador COPIE el fichero, no que lo nombre.

- `test_el_instalador_COPIA_cada_adoptado_no_solo_lo_nombra` -- corre el
  `--dry-run` de verdad (0.03, 0.03 y 0.04 s en tres corridas medidas) y exige
  que cada adoptado salga copiado o declarado.
- `test_control_negativo_quitar_un_cp_lo_delata` -- le quita a esa salida la
  linea que copia UN fichero y exige que salga ese y solo ese. Sin el, el
  anterior pasaria con un lector que devolviera siempre todo.

Y su control negativo sobre el SUJETO, no sobre un fixture: los dos tests
corridos contra el arbol de antes del arreglo (`git archive HEAD` de `5cd2ca6`
desplegado aparte) **fallan**, nombrando los 15:

```
2 failed, 6 passed in 0.14s
AssertionError: adoptados que el instalador NO copia y que tampoco estan
declarados en adopted/solo-registro.txt: ['etc_default_kdump-tools',
'etc_modprobe.d_99-blackbox-uvm.conf', ...  y los 13 restantes]
```

Si el `dry-run` no llegara a correr, el fixture falla diciendo `COULD_NOT_RUN`
en vez de dar el test por bueno: un instrumento caido no prueba que el sujeto
este limpio.

### Lo que sigue sin cubrir

`config_entregable.sh` no cambio, y su limite es el mismo de siempre: mira el
nombre. Lo que lo cubre ahora es el test de arriba, que vive en la suite y no en
el `close_check` -- o sea que un `bash tools/config_entregable.sh` aislado sigue
pudiendo decir OK sobre un instalador que solo menciona. Quien lo caza es
`pytest`, en `pre-push`.

Y ninguno de los dos comprueba que el `cp` deje el fichero BIEN: eso lo mira
`bb drift`, comparando contenidos contra la maquina.
