---
id: DEBT-DGX-438-SIN-CAUSA-RAIZ
kind: debt
title: Algo mata procesos de fondo con SIGTERM y no se sabe que
status: done
closure_type: void_wontfix
closed_at: 2026-09-27
severity: P1
origin: detected
detector: {"rule": "systemd/unit-killed-by-TERM", "confidence": 1.0}
satd_family: UNKNOWN_FAILURE
created: 2026-09-08
close_check: {"cmd": "grep -q 'CERRADO' tasks/done/DEBT-DGX-438-SIN-CAUSA-RAIZ.md", "expect": "exit_zero", "porque": "cierre solo con evidencia real (comando + salida + control negativo) en el done, patron DEBT-AUDIT-AHOGADO-POR-RUSTDESK."}
evidence:
  pass: tasks/evidence/DEBT-DGX-438-SIN-CAUSA-RAIZ/pass.txt
  fail: tasks/evidence/DEBT-DGX-438-SIN-CAUSA-RAIZ/fail.txt
  e2e: tasks/evidence/DEBT-DGX-438-SIN-CAUSA-RAIZ/e2e.txt
reason: "CERRADO como void_wontfix 2026-09-27, por decision del dueno con la objecion puesta delante. El instrumento esta armado, acumula fuera del anillo y su columna de victima quedo arreglada HOY: 44 de 314 capturas (14.0 %) traian el grupo de procesos leido como un pid imposible y 28 mas traian kill(0,sig), o sea 72 (22.9 %) mal clasificadas. Con el arreglo, autolimpieza pasa de 3 a 31 y atribucion incompleta de 70 a 42, y el SUJETO sigue en 0: ni una captura de un demonio matando un proceso ajeno nombrable. No se cierra afirmando que no ocurre -- se cierra porque lo que queda es un limite del corpus (top-5 a 1/min no ve procesos de vida corta) y no una via sin agotar. Se reabre por el trigger de abajo."
---
## Root Cause

### Que pasa

Atlas registro en DGX-438 muertes de procesos python de fondo con `rc=143`
(SIGTERM) a intervalos irregulares (10-15 min), con o sin `setsid`, con o sin
`disown`. Sin causa raiz.

El 2026-09-08 se sumo un caso con dos victimas casi simultaneas:
`atom-gpu-telemetry.service` murio `(code=killed, signal=TERM)` a las 07:41:02 y
el vLLM del gateway cayo a las 07:41:27, 25 segundos despues.

### Descartado con evidencia

- `systemd-oomd`: `is-enabled` devuelve `not-found`, ni instalado.
- La mitigacion de `atom_gpu_telemetry.py`: usa SIGSTOP/SIGCONT, no mata.
- `liberation_watchdog.py`: no envia kill a nadie; el SIGTERM que documenta es el
  que RECIBE por `TimeoutStartSec=245min`, y 245 min no encaja con 10-15.

### Vivos

`earlyoom` y un cgroup ajeno con `TimeoutStopSec`. Tampoco se ha descartado que
el caso del 07:41 lo causara esta misma sesion con alguna operacion de esa
franja: no se identifico quien envio la senal.

### Que la cierra

Identificar al emisor del SIGTERM.

### Instrumento, puesto el 2026-09-23

Hasta hoy la ficha apuntaba a `bb sample`/`bb scan`, y eso no podia cerrarla:
la muestra se toma del lado de la VICTIMA, asi que ve que un proceso
desaparecio y nunca quien lo mato. El emisor solo existe durante el syscall.

El unico sitio de esta caja que guarda esa pareja es el registro de auditoria.
Peldano 4 de la escalera -- la plataforma ya lo hace: `auditd` corre
(`active`/`enabled`), persiste, rota, y `/var/log/audit` es `root:adm`, o sea
que este usuario lo LEE sin root, la misma dependencia de grupo que `bb` ya
tiene para `journalctl -k`. No hacia falta un demonio nuevo con bpftrace.

Lo que faltaba era la regla, no el demonio. Medido el 2026-09-23:
`grep -c "syscall=62\|syscall=200\|syscall=234"` sobre `audit.log` y
`audit.log.1` da **0**, y `grep -c "sig=15\|SIGTERM"` da **0** -- cero eventos
de kill en las 4 h 08 min que cubria el anillo. No es que nadie matara: es que
nadie miraba.

- `sudo ./enable-privileged.sh` seccion 7 instala la regla (`kill`/`tkill` con
  la senal en `a1`, `tgkill` con la senal en `a2` -- una sola regla con `-F a1`
  habria dejado pasar todo `tgkill` sin que nada lo dijera).
- `bb sigterm ["hace X"]` lee el registro y empareja el `SYSCALL` (emisor:
  pid/comm/exe/auid) con el `OBJ_PID` (victima: opid/ocomm) por el id de
  evento, que es lo unico que los relaciona.

Los dos sospechosos vivos caen ahi: `earlyoom` manda la senal por syscall, y un
cgroup ajeno con `TimeoutStopSec` la manda via systemd, tambien por syscall.
El `auid` del emisor separa ademas demonio de humano, que descarta de entrada
la hipotesis abierta de que el caso del 07:41 lo causara una sesion a mano.

**Controles corridos** (2026-09-23), porque un lector que solo sabe imprimir
cero no es un lector:

| control | salida |
|---|---|
| positivo: log con 2 eventos, ventana de 10 min | 2 filas, emisor -> victima, `could_not_run: 0` |
| negativo: los mismos eventos con 2 h, ventana de 10 min | `0 senales registradas` |
| y de nuevo con ventana de 3 h | vuelven las 2 filas |
| sobre el registro REAL, hoy | `0 senales` + **`NO ARMADO`** + `could_not_run: 1` |

Esa ultima fila es la mitad del valor del subcomando: hoy el instrumento aun no
esta armado, y `bb sigterm` lo DICE en vez de devolver un cero limpio. El
discriminador no es "cero eventos con mi clave" -- eso es justo lo ambiguo --
sino el efecto de la otra regla que instala la misma seccion: si el sondeo de
rustdesk sigue cayendo en el anillo, la seccion 7 no esta cargada.

### Lo que hubo que resolver antes, y es su propia ficha

El anillo de auditoria estaba ahogado: **99.8 % de sus eventos eran
`/usr/bin/loginctl` ejecutado por `rustdesk.service` a 14.6 por segundo**, lo
que encoge la retencion de 248 min a 37 min mientras vive su hijo `--server`.
A esa retencion, una captura de kill envejece antes de que nadie la lea. La
seccion 7 excluye ese ruido con `auid=unset` sin cegar la regla `reboot_cmd`
que lo produce; la causa queda en `DEBT-AUDIT-AHOGADO-POR-RUSTDESK`.

### ARMADO el 2026-09-23 22:01, y el control lo confirmo

`sudo ./enable-privileged.sh` cargo la seccion 7 y su propia verificacion
respondio `reglas CARGADAS en el kernel (auditctl -l las ve)`.

El control negativo devolvio filas, que es lo que hacia falta:

```
  CUANDO              SENAL    EMISOR                          -> VICTIMA
  2026-09-23 22:01:46 SIGTERM  bash[1695154] humano auid=1000  -> bash[1695156]
  2026-09-23 22:01:48 SIGKILL  python[1657416] humano auid=1000 -> sleep[1698528]
  2026-09-23 22:02:47 SIGKILL  claude-desktop[130715] humano auid=1000 -> bash[1698596]
```

Emisor, victima, `exe` y `auid`, que es exactamente lo que faltaba desde el
2026-09-08.

**Estas tres capturas NO son el sujeto de esta ficha**, y se dice para que
nadie las lea como un cierre: las tres son gestion de procesos de la propia
herramienta (el SIGTERM es el del control, y los dos SIGKILL matan shells y
`sleep` de comandos que acababan de terminar), todas con `auid=1000` de una
sesion interactiva. El sujeto son procesos python de FONDO muriendo a
intervalos de 10-15 min sin que nadie lo pida. Eso no ha vuelto a pasar desde
que la regla esta puesta, y cuando pase quedara registrado con su emisor.

Efecto lateral medido: el sondeo de rustdesk **paro en seco** al cargar la
regla -- 408 eventos en los 60 s previos, **0 en los 30 s siguientes**. La
retencion del anillo deja de ser de 37 min, que era la condicion para que una
captura sobreviviera hasta que alguien la leyera.

#### Un defecto que el control encontro en el propio instrumento

La primera lectura tras armar imprimio las dos capturas y debajo dijo
**NO ARMADO**. El estado se calculaba contando ruido de rustdesk en la ventana
que pide el usuario, y en esos 5 minutos cabian 417 eventos ANTERIORES a la
instalacion: el instrumento estaba capturando y su propia linea de estado lo
desmentia. Corregido a una ventana FIJA de 30 s (a 1.9/s el sondeo mas lento,
30 s de silencio son >=57 eventos que no llegaron), con su control en las dos
direcciones: ruido llegando ahora -> NO ARMADO con could_not_run 1; el mismo
ruido de hace 5 min -> armado con could_not_run 0.

Se anadio ademas un tercer veredicto, **NO SE PUDO DETERMINAR**: si rustdesk
no corre, nadie genera el ruido que la regla calla y un cero no distingue
"regla puesta" de "nada que callar". Antes eso se habria leido como armado.

### Lo que sigue sin saberse

Quien manda el SIGTERM del sujeto.

### Que espera esta ficha, reescrito el 2026-09-23

Hasta hoy esperaba un arreglo. **Ya no: espera una REAPARICION con el
instrumento puesto**, y el cambio se hace porque el sujeto dejo de aparecer.
Medido el 2026-09-23:

| medida | resultado |
|---|---|
| senales capturadas desde que se armo (~1 h) | 4 |
| de ellas con emisor DEMONIO, que es la forma del sujeto | **0** |
| muertes `code=killed, signal=TERM` en el journal, ultimos 10 dias | **2** (sep 16, sep 20) |
| `Atlas/uvicorn` en pie | 16 h 24 min |
| `simplecode.daemon` en pie | 16 h 24 min |
| `bb-usable` en pie | 11 h 45 min |

La ficha describe muertes "a intervalos irregulares (10-15 min)". Eso no esta
ocurriendo: los candidatos llevan dieciseis horas vivos y el journal registra
DOS muertes en diez dias, no cientos. Lo medido el 2026-09-08 se midio y no se
retira; lo que cambia es que el fenomeno no se reproduce hoy.

**Por que NO se cierra pese a eso.** Un cierre por no-reproducible tiraria el
contexto que mas cuesta reconstruir: tres sospechosos ya descartados con
evidencia (`systemd-oomd` ni instalado, la mitigacion de
`atom_gpu_telemetry.py` que usa SIGSTOP/SIGCONT, `liberation_watchdog.py` que
no manda kill) y dos todavia vivos (`earlyoom`, un cgroup ajeno con
`TimeoutStopSec`). Si reaparece sin ficha, ese trabajo se repite entero.

**Que la cierra ahora**, cualquiera de las dos:

1. **Reaparece y se identifica al emisor.** `bb sigterm` lo dara con nombre,
   `exe` y `auid`. Los dos sospechosos vivos mandan la senal por syscall, asi
   que los dos caen en la regla. Un emisor con `auid` sin poner es un demonio y
   se distingue de un vistazo de una sesion interactiva.
2. **Pasa el plazo sin una sola captura de demonio.** Entonces se cierra como
   no reproducible, con el instrumento puesto y el trigger de reapertura
   automatica: si `bb sigterm` caza un emisor demonio matando un python de
   fondo, vuelve a abrirse.

La diferencia con antes es que ahora las dos salidas son medibles. Hasta el
2026-09-23 esta ficha no podia cerrarse por ninguna via, porque no habia
instrumento que distinguiera "no ha pasado" de "no estabamos mirando".

### 2026-09-27: el instrumento no podia encontrar la causa, y no estaba declarado

El 2026-09-23 esta ficha se extendio al 2026-10-23 con esta razon: «el mes nuevo
es para que el instrumento acumule evidencia, no para que la deuda envejezca. Si
el plazo pasa sin una sola captura de emisor demonio, se cierra como no
reproducible con reapertura automatica».

**Ese plan era inejecutable, por cuatro defectos del propio instrumento.** Ninguno
estaba escrito. Medidos y arreglados hoy; evidencia completa en
`tasks/evidence/DEBT-DGX-438-SIN-CAUSA-RAIZ/instrumento-2026-09-27.txt`.

| defecto | medida | despues |
|---|---|---|
| leia sólo `audit.log`, no las 4 rotaciones | veía **10.1 min** de las **76 h** armado (0.2 %) | lee `audit.log*`: 135 min, emisores de 2 a 12 |
| no decía cuánto había mirado | un 0 no distinguía «no hubo señales» de «el anillo no llega» | declara la ventana y levanta su `could_not_run` |
| nada acumulaba fuera del anillo | el mes de espera reciclaba 127 min | `sigterm_persist` en cada muestra, con marca de agua |
| la víctima salía `?` **siempre** | **0 de 53** capturas con víctima | **39 de 39**, leyendo `a0` del SYSCALL |

El cuarto es el que importa para esta ficha: la pregunta es *qué mata* los
procesos, y el instrumento contestaba quién dispara y nunca a quién. `auditd` no
emite `type=OBJ_PID` para estas reglas — **0 en todo el anillo contra 307
SYSCALL con la clave** — así que la rama que unía emisor con víctima no se
ejecutaba nunca. La víctima estaba en el propio SYSCALL, en `a0`, en hexadecimal.

Y un quinto, encontrado al medir el cuarto: `IFS=$'\t' read` **colapsa**
tabuladores consecutivos, porque el tabulador es espacio en blanco para IFS, así
que un campo vacío desplazaba todos los de su derecha. La fila salía
`python3.12[1841782] humano auid=? -> [?]` con `exe: 1000`.

### Por qué esto NO la cierra

Hay 6 capturas de emisor demonio (`rustdesk` 2, `kill` 2, `pkill` 2), que es lo
que la ficha esperaba. No bastan:

- son de **una** ventana de 127 min, y el fenómeno descrito es de cada 10-15 min
  con 2 muertes medidas en 10 días. Una ventana no es una serie.
- `kill` y `pkill` con `auid=unset` son procesos que heredaron un auid sin
  sesión; llamarlos «demonio» es lo que dice la regla, no lo que son.
- la víctima tiene **pid pero no nombre**: el proceso ya está muerto cuando se
  lee el registro. Ponerle nombre es cruzar `victima.pid` contra `top_rss`,
  `cpu_top` y `py_bg` de la muestra del mismo minuto — reuso de la serie que
  `bin/bb` ya graba, y es el siguiente paso.

### Lo que cambia en su criterio de cierre

La regla anterior — «si el plazo pasa sin captura, se cierra como no
reproducible» — **no se puede aplicar a lo medido antes de hoy**: habría sido una
conclusión sobre el 0.2 % de la ventana. El plazo del 2026-10-23 sigue, y a
partir de hoy sí acumula algo que mirar.

### 2026-09-27, mismo dia: la victima ya tiene nombre, y lo que aparecio no es esto

Con el instrumento arreglado, el siguiente paso era cruzar `victima.pid` contra
las muestras. Hecho en `tools/nombra_victimas.py`. Lo que salio:

```
por emisor y victima (primera acumulacion de ~3 h):
   12  demonio  kill / pkill           -> rustdesk (rustdesk.service)
    7  demonio  postgres               -> (ninguna muestra lo vio vivo)
    3  humano   python / pytest        -> pytest, python3
  203  humano   varios                 -> (ninguna muestra lo vio vivo)

SUJETO DE DGX-438 (emisor demonio, victima ajena, atribuible y nombrada): 0
```

**Las 12 capturas de demonio son `rustdesk` limpiando sus propios hijos.** Y esa
conclusion costo un falso positivo MIO, que queda escrito porque es la parte
util: la primera version de `nombra_victimas` comparaba el nombre del emisor con
el de la victima, `kill` no se parece a `rustdesk`, y reporto las 12 como sujeto
de esta ficha. Mandaba a buscar un culpable llamado `kill`.

El arreglo no fue una heuristica mejor de nombres, fue capturar el dato que
faltaba: **`ppid`**. Con el, la prueba es directa y se ve en el registro:

```
pkill pid 2818158 ppid 2818154 -> victima 2818154
                                          ^^^^^^^ la victima ES el padre del emisor
```

`kill`, `pkill`, `killall` y `timeout` son ENVOLTORIOS: su nombre identifica el
utensilio, no a quien decidio. Una captura cuyo emisor es un envoltorio y cuyo
padre no se puede nombrar queda como **ATRIBUCION INCOMPLETA** -- ni sujeto ni
descarte -- en vez de contarse como hallazgo.

### Lo que este cero SI y NO dice

**SI dice:** en lo acumulado no hay una sola captura de un demonio matando un
proceso ajeno con emisor atribuible y victima nombrable. Es un cero medido, no
un cero por ceguera, que es lo que era esta manana.

**NO dice** que el fenomeno no ocurra, por tres razones contadas:

1. la acumulacion lleva ~3 h, no el mes que el plazo concede;
2. **el 92 % de las victimas no se puede nombrar** (18 de 227 en la primera
   pasada): las listas de las muestras son top-5 a 1/min, y un proceso de vida
   corta -- justo el que muere por una senal -- puede no haber sido visto nunca.
   Eso no es un defecto del cruce: es lo que hay grabado;
3. `postgres` aparece 7 veces como emisor demonio con victima sin nombre. No se
   descarta ni se acusa: no se sabe a quien mato.

### El siguiente paso, que ya no es "esperar"

Subir ese 8 % de victimas nombrables. El cruce solo puede usar lo que las
muestras vieron vivo, asi que las opciones son grabar mas procesos por muestra
(coste medido: la pasada de `awk` sobre el glob de /proc cuesta 0.01 s, ya
medido para `swap.in_pag_s`) o grabar el nombre en el momento del barrido -- que
no sirve, porque el barrido corre hasta 10 min despues y la victima ya murio.

## Verification Evidence
### CERRADO 2026-09-27 -- y el instrumento se arreglo antes de cerrar

Este cierre lo decidio el dueno con la objecion puesta delante. Lo que NO se
hizo es cerrar sobre el numero que el modulo daba: al correrlo para escribir la
evidencia, su propia salida delato un defecto.

#### El defecto, encontrado en la salida y no en el codigo

La columna de victima traia `4294965290`, `4294965334`, `4294965221`. Ninguno es
un pid: `pid_max` en Linux llega a 2^22. Son negativos leidos sin signo --
`4294965974 - 2^32 = -1322` -- y un pid negativo es un **grupo de procesos**:
`kill(-pgid, sig)`, que es como `postgres` apaga a sus hijos de una vez.

**Medido a las 05:12 del 2026-09-27.** El instante importa porque el corpus
crece una muestra cada 60 s -- mediana 60.0 s, p10 y p90 los dos en 60.0, 91.5 %
de 20 781 intervalos entre 55 y 65 s -- asi que los porcentajes se mueven y
quien los recorra mas tarde vera otros. A las 05:38 eran 357 capturas y 21.3 %.

| | capturas | % |
|---|---|---|
| totales | 314 | |
| con `a0 >= 2^31` (grupos leidos como pid) | 44 | 14.0 % |
| con `a0 == 0` (`kill(0,sig)`, el propio grupo del emisor) | 28 | 8.9 % |
| **mal clasificadas** | **72** | **22.9 %** |

#### El arreglo esta vivo en el flujo, y las dos formas no se solapan

| forma | capturas | ventana |
|---|---|---|
| `a0 >= 2^31` (vieja) | 44 | 03:02:12 -> **05:08:00** |
| `a0` negativo (nueva) | 9 | **05:15:53** -> |

Cero capturas de la forma vieja despues de las 05:15:53, mientras el total subia
de 314 a 357. `bin/bb` es un script que bash lee del disco en cada invocacion,
asi que el parche entra en la muestra siguiente sin reiniciar nada. Lo contrario
de `bb-usable`, que es un proceso python de vida larga y sigue corriendo el
codigo que cargo al arrancar -- que es exactamente DEBT-UNA-BAJADA y por que su
criterio de cierre mira el proceso vivo y no el fichero.

Esto es atribucion por coincidencia temporal y es mas debil que un test. El test
controlado es el mutante M4: `bin/bb` sin la conversion a signo deja rojo a
`test_un_a0_NEGATIVO_es_un_GRUPO_y_conserva_su_signo`.

#### Lo que el arreglo mueve

| | antes | despues |
|---|---|---|
| autolimpieza | 3 | **31** |
| atribucion incompleta | 70 | **42** |
| SUJETO (demonio -> proceso ajeno nombrable) | 0 | **0** |

La fila que lo confirma sola: `timeout` sale con **28 de 57 autolimpieza**, que
es literalmente lo que `timeout` hace al vencer el plazo -- matar su propio
grupo. Cuatro mutantes, uno por rama nueva, los cuatro cazados.

#### Por que se cierra, y que NO se afirma

El veredicto no cambio: **0 sujetos**. Lo que cambio es que ahora el 0 descansa
sobre denominadores honestos. Y lo que queda no es una via sin agotar sino un
limite del corpus: las listas de las muestras son top-5 a 1/min, asi que un
proceso de vida corta -- justo el que muere por una senal -- puede no haber sido
visto nunca vivo. 19 de 314 victimas son nombrables, el 6 %.

**NO se afirma que nada mate procesos de fondo.** Se afirma que en 19 dias con
el instrumento puesto no hay una sola captura que lo demuestre, y que las que
hay se explican por autolimpieza o no se pueden atribuir.

## Regression Test

### Trigger de reapertura

Se reabre por cualquiera de estas tres, las tres comprobables con un comando:

1. **`nombra_victimas` reporta SUJETO >= 1**: una captura de emisor demonio
   contra un proceso ajeno y nombrable. Eso es la pregunta de la ficha
   contestada, y la reabre para nombrar al culpable.
2. **Una unit de fondo vuelve a morir por SIGTERM sin emisor identificado**:
   `bb status` o el journal lo dicen, y el instrumento ya no tiene excusa
   porque acumula fuera del anillo.
3. **La tasa de victimas nombrables baja del 6 %** con el corpus creciendo, que
   significaria que el muestreo se quedo corto y hay que subir su resolucion.

### Lo que sigue sin comprobarse, y por eso no se afirma

No se probo subir la resolucion del muestreo para nombrar mas victimas: se
arreglo el signo, no el tamano de la ventana. Nombrar al lider de un grupo no
afirma que muriera el lider -- murio el grupo -- y la etiqueta lo dice
(`"postgres (y su grupo)"`) en vez de dejarlo implicito. Y los 42 de atribucion
incompleta siguen siendo 42: cuando el emisor es un envoltorio y su padre no
esta en ninguna muestra, no se sabe quien decidio, y contarlos como sujeto
mandaria a buscar un culpable llamado `kill`.
