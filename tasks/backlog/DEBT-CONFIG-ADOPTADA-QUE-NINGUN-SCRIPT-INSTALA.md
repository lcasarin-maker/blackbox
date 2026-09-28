---
id: DEBT-CONFIG-ADOPTADA-QUE-NINGUN-SCRIPT-INSTALA
kind: debt
title: "15 de 27 ficheros de configuracion adoptada no los instala ningun script, asi que editarlos no cambia la maquina"
status: open
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
---

## Que pasa

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

## Lo que costo el 2026-09-28, medido

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

## Por que no basta con "acordarse"

El fallo no fue olvidar un paso: fue que **editar el fichero y aplicarlo se
ven iguales desde el repo**. Es el mismo patron que
DEBT-UNA-BAJADA-MOMENTANEA-ABSUELVE-UN-COLAPSO, cerrada ese mismo dia -- codigo
correcto en disco con el defecto todavia en memoria-- y por eso su criterio de
cierre mira la maquina y no el fichero. Aqui pasa un escalon antes: el fichero
del repo ni siquiera tiene por donde llegar.

## Como se cierra

Cada uno de los 15, una de dos:

1. **Se anade a un instalador**, con su `run cp` y su entrada en el `--revert`,
   como ya tienen los 12 que si lo estan.
2. **Se declara solo-registro** en `adopted/solo-registro.txt` con el motivo por
   el que no se instala -- por ejemplo, que lo instala el paquete de un tercero
   y este repo solo guarda copia para poder compararlo.

Ninguna de las dos es una declaracion vacia: la primera cambia la maquina, y la
segunda obliga a escribir por que este repo guarda algo que no aplica.

`tools/config_entregable.sh` lo verifica y tiene los tres desenlaces (0 cubierto,
1 hueco, 2 `COULD_NOT_RUN` si falta el directorio o el instalador).

## Limites declarados

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
