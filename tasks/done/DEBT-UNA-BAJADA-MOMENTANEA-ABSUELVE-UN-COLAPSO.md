---
id: DEBT-UNA-BAJADA-MOMENTANEA-ABSUELVE-UN-COLAPSO
kind: debt
title: "Una sonda baja de 30 s absolvia un colapso entero: la maquina murio de kernel panic con el vigilante armado"
status: done
closure_type: relocated_prior_verification
closed_at: 2026-10-03
severity: P1
origin: detected
detector: {"rule": "kernel panic 2026-09-26 15:38:26 hung_task", "confidence": 1.0}
satd_family: BLIND_INSTRUMENT
created: 2026-09-27
close_check: {"cmd": "bash tools/demonio_al_dia.sh bb-usable.service bin/bb-usable", "expect": "exit_zero", "porque": "es la unica condicion que NO se puede fingir desde el repo: que el PROCESO VIVO haya arrancado despues de la ultima modificacion de bin/bb-usable. Codigo correcto en disco con el defecto todavia en memoria es exactamente el estado en que la maquina murio el 2026-09-26, y un criterio que solo mirara los tests cerraria la ficha ahi. Las otras dos condiciones -- control de falsos positivos limpio y suite verde-- ya las aplica el pre-push en cada commit, asi que repetirlas aqui seria una copia peor de un gate ya cableado; `backlog-verifier` prohibe encadenarlas con && de todas formas. El script distingue COULD_NOT_RUN (rc=2) de codigo viejo (rc=1), y los cuatro caminos estan corridos en tests/test_demonio_al_dia.py. Se invoca via `bash` porque es lo que este repo declara en .simplecode/build_tools.txt y backlog-verifier solo confia en esa lista."}
evidence:
  pass: tasks/evidence/ZERO-2026-10-02/service-restart/pass.txt
  fail: tasks/evidence/ZERO-2026-10-02/service-restart/fail.txt
  e2e: tasks/evidence/ZERO-2026-10-02/service-restart/e2e.txt
reason: "Recierre 2026-10-03: 41 pruebas pasan y Luis reinició bb-usable.service; proceso vivo posterior al código, active/running, close_check rc=0. Historial anterior conservado abajo."
---
## Root Cause

### Que paso

El 2026-09-26 a las 15:38:26 esta maquina murio de un kernel panic
(`hung_task: blocked tasks`, ~20 tareas `python` bloqueadas mas de 123 s).
`bb-usable` estaba armado, corriendo, y vio el colapso entero: su journal tiene
las 35 lecturas de PSI, una cada 30 segundos.

No lo detuvo. Su propio journal explica por que:

```
15:29:01  racha  1/10 (30s de 300s)   avg10=30.4
15:30:01  racha  3/10                 avg10=78.7
15:32:32  racha  8/10 (240s)          avg10=84.1
15:33:02  racha  9/10 (270s)          avg10=83.2      <- ULTIMA CARICIA
15:33:32  COLAPSO sostenido 300s  --  NO se acaricia el watchdog
15:34:02  COLAPSO sostenido 330s  --  NO se acaricia
15:34:32  COLAPSO sostenido 360s  --  NO se acaricia
15:35:02  PSI bajo a 9.8: la racha de 360s SE CORTA. "Era un pico, no un colapso"
15:35:32  racha  1/10 (30s de 300s)   avg10=80.2
15:38:02  racha  6/10 (180s)          avg10=92.2      <- ultima caricia real
15:38:26  KERNEL PANIC
```

Una lectura de **9.8** -- dos decimas por debajo del umbral de 10.0, una sola
sonda, dentro de un colapso de dieciseis minutos-- puso la racha a cero Y
volvio a acariciar el watchdog, devolviendole sus seis minutos enteros. Hubo
**tres** de esas bajadas en la misma ventana: 2.4, 3.7 y 9.8.

Sin la bajada de las 15:35:02, la ultima caricia habria sido la de 15:33:02 y
`WatchdogSec=360` habria cobrado a las 15:39:02. El panico gano por 36
segundos. Con el arreglo entero, el reinicio entra a las 15:32:01.

### Los dos defectos, que son distintos y se necesitan los dos

**1 · Una sola bajada corta la racha.** El criterio de este demonio es la
DURACION -- eso esta calibrado y documentado, y es lo que distingue los siete
picos sanos del corpus de los tres congelamientos reales. Una duracion que
cualquier muestra suelta puede poner a cero no es una duracion.

**2 · Y en esa misma sonda baja, acaricia.** Aunque la racha sobreviva, si el
codigo acaricia en la bajada el watchdog vuelve a cero y el colapso no cobra
nunca. Medido replicando las 35 lecturas del arranque muerto:

```
hoy                            1er COLAPSO 15:33:32  reinicio 15:44:02   -5.6 min
solo no-cortar-con-1           1er COLAPSO 15:26:31  reinicio 15:41:02   -2.6 min
solo no-acariciar-en-colapso   1er COLAPSO 15:33:32  reinicio 15:44:02   -5.6 min
LAS DOS                        1er COLAPSO 15:26:31  reinicio 15:32:01   +6.4 min
```

Ninguna mitad sola llega antes del panico. `WatchdogSec` no hace falta tocarlo.

### Lo que se escribio, y que lo respalda

`bin/bb-usable`: `BAJAS_PARA_CORTAR = 2`, el contador de bajas consecutivas, y
el `continue` que impide acariciar mientras la racha sigue cumpliendo el
criterio de accion.

El numero 2 no es redondo, sale de un control que se corrio:

```
$ python3 tools/control_racha.py
corpus 20207 muestras  ventanas de incidente excluidas: 4  corte 300s
  1 baja(s) para cortar (defecto)     180 s   no dispara
  2 baja(s) para cortar (ARREGLO)     180 s   no dispara
  6 baja(s) para cortar (mas flojo)   180 s   no dispara
VEREDICTO: LIMPIO -- margen del corte contra el peor caso sano: 1.67x   rc=0

$ python3 tools/control_racha.py --corte 180     # control negativo
VEREDICTO: FALSO POSITIVO en 2026-09-21 00:33:00                        rc=1
```

El maximo tiempo sostenido fuera de un incidente es el MISMO con 1 baja y con
6: en quince dias no hay una sola excursion sana con una bajada suelta dentro,
asi que la superficie nueva de falso positivo es 0 medida.

Ademas: 5 mutantes del arreglo, los 5 cazados; y el control de falsos positivos
es un modulo versionado con su suite, no un numero en un mensaje de commit.
Todo en `tasks/evidence/DEBT-UNA-BAJADA-MOMENTANEA-ABSUELVE-UN-COLAPSO/`.

### Un test afirmaba lo contrario, y su premisa era falsa

`test_la_racha_se_REINICIA_tras_un_pico_no_se_acumula` exigia que
[9 altas, 1 baja, 1 alta] no diera colapso, llamando a esa unica lectura baja
"una recuperacion real". Nadie habia medido esa premisa; el panico la refuto.

Se reescribio al limite nuevo en vez de borrarse, porque existia para cazar un
mutante concreto (`sostenido = 0` -> `pass`) y ese mutante sigue vivo. El
control de mutacion comprueba que lo sigue cazando.

### Por que esto sigue abierto

**El proceso vivo corre la regla vieja.** El demonio carga el codigo al
arrancar y reiniciarlo pide `sudo`, que este asistente no puede dar. Codigo
correcto en disco con el defecto en memoria es exactamente el estado en que la
maquina murio, y desde el repo no se distingue de estar arreglado:

```
$ ./tools/demonio_al_dia.sh bb-usable.service bin/bb-usable
bb-usable.service arranco Sat 2026-09-26 23:36:57 CST y bin/bb-usable se modifico despues
el proceso vivo corre codigo VIEJO. Lo arregla:  sudo systemctl restart bb-usable.service
rc=1
```

Por eso el `close_check` incluye ese chequeo. Lo cierra:

```
sudo systemctl restart bb-usable
```

### Limite declarado

Esto no dice que el arreglo funcione en produccion: dice que reinicia 6.4
minutos antes del panico **en la replica de una traza**, y que no dispara sobre
las 6 excursiones sanas del corpus. Seis excursiones sanas no son muchas, y el
1.67x de margen es mas fino que el 2.5x de `calibra_psi`. Verlo cobrar de
verdad pide un cuarto colapso, que no se provoca a proposito.

Tampoco dice nada de la CAUSA del colapso -- un herd de workers de
`pytest-xdist` sin techo a nivel de maquina, que es `DEBT-DGX-438` y la
sugerencia que llego de office2office. Este arreglo acota el DANO de un
colapso; no evita ninguno.

## Verification Evidence

### CERRADO 2026-09-28 -- el proceso vivo ya carga la regla nueva

```
$ bash tools/demonio_al_dia.sh bb-usable.service bin/bb-usable
bb-usable.service arranco Sun 2026-09-27 23:48:05 CST, despues de la ultima
modificacion de bin/bb-usable
rc=0
```

Control negativo, el mismo comando unas horas antes: `arranco Sat 2026-09-26
23:36:57 CST y bin/bb-usable se modifico despues / el proceso vivo corre codigo
VIEJO`, rc=1. El criterio distingue los dos estados.

### Lo que el cierre NO afirma

No se ha observado un colapso desde el reinicio, asi que la regla nueva esta
armada pero no ejercitada contra un incidente real. Lo que si esta medido es su
comportamiento contra las 35 lecturas del arranque que murio: el reinicio entra
a las 15:32:01 en vez del panico de las 15:38:26, y ninguna de las dos mitades
del arreglo sola llega antes.

## Regression Test

### Trigger de reapertura

1. **`bash tools/demonio_al_dia.sh bb-usable.service bin/bb-usable` vuelve a dar
   rc=1**: alguien toco `bin/bb-usable` y nadie reinicio el demonio. Es el mismo
   hueco de 24 h que esta ficha cerro, y se repite con cada cambio al fichero.
2. **La maquina vuelve a morir de hung_task con `bb-usable` activo**: la regla
   nueva no basto, y el corte de 2 sondas necesita re-calibrarse contra ese
   quinto incidente.

### Lo que sigue sin comprobarse

Nada avisa automaticamente cuando el disco y la memoria divergen: el
`close_check` lo detecta si alguien lo corre, y el pre-push no lo corre porque
mira el repo. Un watcher que compare `ExecMainStartTimestamp` contra el mtime en
cada `bb status` cerraria eso, y no esta escrito.

## Reapertura /0 — 2026-10-02

backlog_verifier detectó rc=1 en el close_check tras cambiar bin/bb-usable: el proceso vivo arrancó 2026-09-30 y el archivo fue modificado después. El arreglo de lógica sigue probado en disco; la condición explícita del proceso vivo requiere cargar la versión actual. Reinicio del vigilante pendiente de autorización/privilegios; no se debilita el criterio. Informe literal tasks/evidence/ZERO-2026-10-02/verifier-wave1.txt.

## Recierre verificado — 2026-10-03

Luis reinició el servicio tras 41 pruebas aprobadas. El close_check real da rc=0: el proceso arrancó a las 00:10:01 después del mtime del ejecutable. active/running y journal muestran la sonda de memoria y lectura posterior del escritorio. Se conserva el historial anterior; este cierre acredita carga del código actual, no un nuevo ensayo de colapso.
