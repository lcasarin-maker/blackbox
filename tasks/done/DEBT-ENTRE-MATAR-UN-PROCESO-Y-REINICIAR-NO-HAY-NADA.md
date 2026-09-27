---
id: DEBT-ENTRE-MATAR-UN-PROCESO-Y-REINICIAR-NO-HAY-NADA
kind: debt
title: "El unico remedio armado contra el caso medido es reiniciar la maquina entera"
status: done
closure_type: void_wontfix
closed_at: 2026-09-27
severity: P2
origin: detected
detector: {"rule": "bb status", "confidence": 1.0}
satd_family: MISSING_COVERAGE
created: 2026-09-25
close_check: {"cmd": "grep -q 'CERRADO' tasks/done/DEBT-ENTRE-MATAR-UN-PROCESO-Y-REINICIAR-NO-HAY-NADA.md", "expect": "exit_zero", "porque": "cierre solo con evidencia real (comando + salida + control negativo) en el done, patron DEBT-AUDIT-AHOGADO-POR-RUSTDESK."}
evidence:
  pass: tasks/evidence/DEBT-ENTRE-MATAR-UN-PROCESO-Y-REINICIAR-NO-HAY-NADA/pass.txt
  fail: tasks/evidence/DEBT-ENTRE-MATAR-UN-PROCESO-Y-REINICIAR-NO-HAY-NADA/fail.txt
  e2e: tasks/evidence/DEBT-ENTRE-MATAR-UN-PROCESO-Y-REINICIAR-NO-HAY-NADA/e2e.txt
reason: "CERRADO como void_wontfix 2026-09-27, por decision del dueno, que el 2026-09-27 habia votado antes dejarla esperando un quinto incidente y hoy voto cerrarla; manda el voto nuevo. El hallazgo que la cierra no es falta de datos: con el cuarto incidente y sus campos por proceso, CINCO claves por proceso contra CUATRO incidentes y ninguna separa -- el incidente 4 queda POR DEBAJO del p99 sano (10112 frente a 35340 MiB). No hay proceso anomalo que matar; el agregado es el anomalo. Un guardia intermedio con un umbral inventado mataria un proceso Y ADEMAS afirmaria haber tenido razon, que es peor que no tenerlo. El remedio grueso esta armado y calibrado contra los cuatro incidentes (bb-usable, FailureAction=reboot-immediate, WatchdogUSec=6min, activo)."
---
## Root Cause

### Que dice el informe hoy

`bb status` imprime, y lleva imprimiendolo desde que se anadio la fila:

```
  CIEGO     earlyoom ante agotamiento de memoria unificada
            su umbral lee MemAvailable, que marco 56% durante los congelamientos del 2026-09-22/23
```

`armado: 15    falta: 0    ciego: 1`

### Por que earlyoom no puede ver esto

Lee dos senales, `MemAvailable` y `SwapFree`, y ninguna de las dos se movio.
Medido en los congelamientos del 22 y el 23: `MemAvailable` marco **56 %**
durante 17 horas mientras `PSI memory full` estaba en **98-99 %**. earlyoom
disparo **una vez** (05:51:40) y nunca mas.

No es un defecto de configuracion: es que la memoria unificada de la GPU no la
contabiliza ningun cgroup y apenas la toca `MemAvailable`. Contra un OOM
clasico earlyoom sigue sirviendo, y por eso sigue armado.

### Lo que SI esta cubierto, y con que

`bin/bb-usable` lee `/proc/pressure/memory` directamente, actua sobre
`full avg10` sostenida, y su corte (10 % durante 300 s) esta **validado por
`tools/calibra_psi.py` contra los TRES congelamientos reales de esta maquina**
-- no es un numero elegido. Esta armado, y `bb status` lo imprime como tal.

O sea: la maquina no esta desprotegida. Esta ficha no es un agujero de
cobertura.

### Lo que falta, que es otra cosa

El remedio de `bb-usable` es `FailureAction=reboot-immediate`. El de earlyoom
es matar un proceso. **Entre "muere un proceso" y "se reinicia la maquina
entera" no hay nada armado**, y el caso que se midio TRES veces cae del lado
caro: el unico remedio que lo alcanza es el mas destructivo que existe.

Un guardia que matara al proceso que se come la memoria unificada antes de que
haga falta reiniciar es lo que falta. No existe.

### Por que esto no tenia ficha hasta hoy

La fila CIEGO se venia reportando en cada corrida de `bb status`, y el control
compensatorio (`bb-usable`) estaba nombrado **solo en un comentario de
`bin/bb`**. Una brecha que se declara en un informe y no se escribe como deuda
es exactamente lo que la regla prohibe: declararla no la paga. Contarla como
`ciego: 1` corrida tras corrida la vuelve paisaje.

### Como se cierra, con las dos mitades

1. **Dispara sobre el sujeto real**: sobre los tres congelamientos que
   `tools/calibra_psi.py` ya usa como sujeto, el guardia tiene que haber
   elegido un proceso antes del punto en que `bb-usable` habria reiniciado.
2. **Control negativo, corrido y no argumentado**: sobre las 19 045 muestras de
   operacion normal ya acumuladas, cero disparos. Sin esta mitad el arreglo es
   peor que la brecha -- un guardia que mata por un umbral inventado hoy mata
   un proceso y ademas afirma haber tenido razon.

El corte no se inventa aqui: se calibra igual que se calibro el de
`bb-usable`, contra medidas propias.

### 2026-09-26: se intento calibrar. La VENTANA existe; la ATRIBUCION no

Evidencia completa en
`tasks/evidence/DEBT-ENTRE-MATAR-UN-PROCESO-Y-REINICIAR-NO-HAY-NADA/calibracion-2026-09-26.txt`.

#### Primero, un hallazgo que cambia lo que se puede pedir a estos datos

**Durante un congelamiento el muestreador se muere con la maquina:**

```
incidente 1   17h45m de ventana  ->  94 muestras   (una cada  9.7 min)
incidente 2    5h55m             ->   9 muestras   (una cada 40.3 min)
incidente 3    5h54m             ->  43 muestras   (una cada  7.3 min)
```

A una por minuto habrian sido ~1065, ~355 y ~354. Y los campos que nombran a un
proceso por memoria ordinaria -- `pidio`, `cpu_top`, `swap`, `slices` -- estan
VACIOS en los tres: no existian aun.

#### La ventana SI cabe: 6 minutos en el peor caso

Barrido de `load1`, contra el punto en que `bb-usable` reiniciaria (PSI mem_full
>= 10 % sostenido 300 s):

```
load1 >  falsos   aviso i1  aviso i2  aviso i3
     25     121          6        57         6
     50       6          6        57         6
     60       2          6        57         6
    100       0         -7        57       -36   <- dispara DESPUES del reinicio
```

Un corte en 50-60 caza los TRES con 6 min de aviso en el peor caso y 2-6 falsos
de 21 159 muestras sanas. Eso responde la pregunta del limite declarado: **la
ventana no es de segundos.**

#### Pero el remedio que esta ficha imagina no se puede calibrar

Ninguna clave POR PROCESO separa los tres incidentes de la operacion normal:

| clave | i1 | i2 | i3 | p99 sanas | discrimina |
|---|---|---|---|---|---|
| rss max (GiB) | 5.6 | 2.5 | 3.9 | 8.5 | no |
| gpu agregada (GiB) | 50.7 | 38.0 | 67.0 | 51.8 | no |
| gpu del mayor (GiB) | 34.5 | 5.6 | 32.0 | 47.3 | no |
| commit_pct | 0.0 | 0.0 | 0.0 | 61.2 | no |
| **load1** | 153.0 | 176.9 | 115.0 | 23.6 | **SI** |

El caso que lo decide es el **incidente 2**: su proceso de GPU mas grande llego a
**5.6 GiB** contra un p99 sano de 47.3, y su GPU agregada maxima fue 38.0 GiB,
por DEBAJO de la mediana sana. **No habia proceso dominante que matar.**

Y `load1`, la unica clave que discrimina, es un total de la maquina: no trae pid,
ni comm, ni unit. Ve el cuello y no ve al culpable -- que es esta misma ficha por
el otro extremo.

#### Lo que esto deja

Un remedio intermedio **cabe en el tiempo**, pero no puede ser un kill dirigido:
tiene que ser mas grueso que matar un proceso y mas fino que reiniciar. Congelar
o estrangular un slice, o negar reservas nuevas de GPU. Cual, y con que control,
es lo que sigue abierto -- y ya no por falta de ventana.

#### Un error de medicion propio, y un hallazgo aparte

La primera medida dio "6 y 8 min de ventana" porque tomaba el primer PSI>=10 de
cada ventana, y las ventanas de `calibra_psi.py` estan DEFINIDAS como los tramos
donde el PSI ya estaba alto: el cruce coincidia con el inicio por construccion.
Instrumento en vez de sujeto, otra vez. Se repitio mirando las 4 h previas.

Y de los 6 "falsos positivos" de `load1>50`, **cinco son mios** -- las pruebas de
carga de hoy, con psi_full entre 0.00 y 1.16. El sexto no es falso:
`2026-09-20 16:55` con **PSI memory full en 83.55 %** es un estancamiento real y
**NO esta en la lista `INCIDENTES` de `tools/calibra_psi.py`**. Si esa lista esta
incompleta, toda calibracion hecha contra ella -- incluida la de `bb-usable` --
se hizo sobre n=3 cuando habia mas. Eso se declara aqui y necesita su propia
mirada.

### Limite declarado

Esta ficha **no prueba que el remedio intermedio sea lo que hacia falta**. Cabe
que para esta maquina el reinicio SEA proporcionado y que un asesino
intermedio solo anada una forma nueva de equivocarse. Decidir eso tambien
necesita la medicion: cuanto tiempo pasa entre el punto en que un proceso ya
es identificable como el culpable y el punto en que `bb-usable` reinicia. Si
esa ventana es de segundos, no hay remedio intermedio que quepa, y esta ficha
se cierra escribiendo ESO.

### 2026-09-27: con el cuarto incidente y sus campos por proceso, sigue sin separar

Evidencia: `tasks/evidence/DEBT-ENTRE-MATAR-UN-PROCESO-Y-REINICIAR-NO-HAY-NADA/calibracion-2026-09-27.txt`.

El intento anterior se quedó sin atribución porque `pidio`, `cpu_top` y `slices`
estaban **vacíos** en los tres congelamientos: no existían aún. El kernel panic
del 2026-09-26 es posterior, así que por primera vez hay datos por proceso dentro
de un incidente.

**La ráfaga sí nombra al culpable.** La muestra de las 15:35:16, la última antes
del pánico, con `psi=84.75` y `load1=221.55`, dice `pytest:10112MiB`. Es el herd,
visto por el instrumento de este repo.

**Y ninguna clave separa. Ni una.**

| clave | contra el incidente 4 | falsos positivos |
|---|---|---|
| `cpu_top` sostenido (600-1100 %) | lo caza | **12-19** de 2750 sanas |
| crecimiento de `pidio` en ráfaga | max 10 112 MiB | el **p99 sano es 35 340** |

La segunda fila es la decisiva: **el incidente queda por debajo del p99 sano**. La
operación normal de esta máquina hace rutinariamente cosas que, mirando un
proceso, se ven peores que lo que precedió al pánico. Y eso con un filtro
derivado — un crecimiento mayor que `MemTotal` no puede ser residente, lo que
quita el artefacto de 1.4 TB de VmSize con `MAP_NORESERVE`.

### Lo que esto cambia: puede no ser falta de datos, sino falta de señal

Cuatro claves por proceso probadas contra cuatro incidentes — `rss max`, `gpu`
agregada, `gpu` del mayor, `cpu_top` sostenido y crecimiento de `pidio` — y
ninguna discrimina. El colapso **no se distingue porque un proceso se vuelva
anómalo**: se distingue porque el agregado cruza un límite, que es exactamente lo
que `bb-usable` ya mide con PSI.

Así que el remedio que esta ficha imagina — elegir una víctima y matarla — puede
no ser alcanzable aquí. Ningún proceso es el culpable; el culpable es cuántos hay.

Lo que sí apunta a algo es un techo **agregado** sobre el herd, que es
`DEBT-TECHOS-SIN-CALIBRAR` y es también lo que la sesión office2office sugirió por
su cuenta el mismo día. Dos caminos independientes al mismo sitio.

**Esto no cierra la ficha**, porque «no alcanzable» es una conclusión con
consecuencias y la decisión de retirar el remedio no es de un agente. Queda
planteada con su medida.

## Verification Evidence
### CERRADO 2026-09-27 -- y lo que la cierra es una SENAL que no existe, no un dato que falte

El dueno voto dos veces el mismo dia sobre esta ficha: primero dejarla abierta
esperando un quinto incidente, luego cerrarla con las demas. Manda el voto nuevo,
y queda dicho que hubo dos para que nadie lea el cierre como si la duda no
hubiera existido.

#### Lo que SI esta armado, verificado sobre la maquina

```
$ systemctl show bb-usable.service -p WatchdogUSec -p FailureAction --value
6min
reboot-immediate
$ systemctl is-active bb-usable.service earlyoom.service
active
active
```

El remedio grueso existe, esta activo y esta **calibrado contra cuatro
incidentes** (`tools/control_racha.py`, 9 tests). Lo que esta ficha pedia es el
intermedio: matar un proceso en vez de la maquina.

#### Por que el intermedio no se puede calibrar, y no es por falta de datos

El cuarto incidente aporto lo que los tres primeros no tenian: campos por
proceso DENTRO del colapso. La rafaga del 15:35:16 -- la ultima antes del panico
-- nombra `pytest` creciendo **10 112 MiB** en el intervalo. Parece el culpable.

No lo es:

```
  p99 de las ventanas SANAS :  35340 MiB
  max de las sanas          :  54172 MiB
  el incidente 4            :  10112 MiB
```

**El incidente queda por debajo del p99 sano.** La operacion normal de esta
maquina hace rutinariamente cosas que, mirando un proceso, se ven PEORES que lo
que precedio al panico. Cinco claves por proceso probadas contra cuatro
incidentes, y ninguna separa: los cortes que avisan del incidente 4 dan 12 a 19
falsos positivos.

Eso no es "faltan datos". Es que **la senal no vive en ningun proceso**. El
agregado es el anomalo, y contra el agregado ya hay un remedio armado.

## Regression Test

### Trigger de reapertura

1. **Un incidente cuyo peor proceso supere el p99 sano** (35 340 MiB de
   crecimiento, o su equivalente en CPU). Eso seria la primera evidencia de que
   la senal existe por proceso, y entonces el guardia intermedio es construible
   con un corte medido.
2. **`bb-usable` reinicia la maquina mas de una vez por semana.** El remedio
   grueso funcionando de mas es la senal de que hacia falta uno mas fino, y es
   contable desde el journal.
3. **`earlyoom` deja de estar activo** o pierde su punteria: entonces el unico
   remedio contra el caso medido seria el reinicio, sin nada antes, y la brecha
   que esta ficha describe volveria sin control compensatorio.

### Lo que sigue sin comprobarse, y por eso no se afirma

El bucket de carga del que sale la comparacion tiene **n=83**, y las ventanas
sanas se definieron excluyendo los cuatro incidentes -- si hubo un quinto sin
registrar, esta contaminando el p99 hacia arriba y el incidente 4 quedaria
menos por debajo de lo que dice la tabla. Y no se probo una clave AGREGADA por
cgroup (suma de crecimiento por slice) en vez de por proceso: la conclusion es
que ningun PROCESO separa, no que ninguna agregacion lo haga. Esa via queda sin
agotar y se cierra igual, por decision del dueno.
