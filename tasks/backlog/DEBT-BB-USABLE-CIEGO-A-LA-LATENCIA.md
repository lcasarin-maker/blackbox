---
id: DEBT-BB-USABLE-CIEGO-A-LA-LATENCIA
kind: debt
title: "bb-usable pregunta si la maquina sirve MEMORIA, no si el escritorio responde"
status: open
severity: P2
origin: asserted
satd_family: MISSING_INSTRUMENT
created: 2026-09-25
close_check: {"cmd": "grep -q 'X_ACT_MS' bin/bb-usable", "expect": "exit_zero", "porque": "esta ficha no pide el corte, pide que `bb-usable` ACTUE sobre la latencia -- su PASO 3. El corte lo calibra `python3 -m tools.calibra_latencia_x`, que es el close_check de DEBT-SLUGGISH, y compartirlo dejaria dos fichas cerrandose con un solo comando aunque piden cosas distintas. Aqui el sujeto es el demonio: la constante no puede existir en bin/bb-usable hasta que el calibrador haya dado un numero, porque hoy el modulo sale 2 y no hay numero que escribir. Es el mismo patron que el close_check de DEBT-TECHOS, que lee la maquina y no el repo."}
---

## Que pasa

`bb-usable` nacio para contestar "si la maquina SIRVE" en vez de "si systemd
sigue vivo", y lo hace por dos caminos, los dos de MEMORIA: una sonda que pide
64 MiB y los toca, y PSI `memory.full` sostenida.

El 2026-09-25 la maquina fue inusable para teclear durante horas con
`psi.mem_full` en 0.00 casi todo el rato. `bb-usable` vio una maquina sana, y
por su propia definicion tenia razon. La pregunta que no sabe hacer es la que
hizo el dueno: **si el escritorio responde**.

Desde este release esa magnitud existe y se esta registrando: `latencia_x` en
cada muestra (4-7 ms sano en esta maquina, con controles negativos para
TIMEOUT, ERROR y AUSENTE). `bb-usable` no la lee.

## Por que no se conecto de una vez, que es la parte importante

Porque `bb-usable` no informa: **actua**. Su unit lleva
`FailureAction=reboot-immediate`. Enchufarle un canal nuevo sin calibrar
significa darle permiso para reiniciar la maquina por un umbral que nadie ha
validado contra un incidente propio -- que es exactamente el error que su
propio encabezado documenta haber cometido ya una vez con la sonda de 64 MiB.

El corte de memoria (UMBRAL=10, SOSTENIDO=5 min) esta calibrado contra cuatro
congelamientos con sus controles sanos. Para la latencia del escritorio hay
**una sola medida sana** (4-7 ms) y **cero episodios malos registrados**. Con
n=0 del lado positivo no hay calibracion posible.

## 2026-09-26: la premisa de esta ficha era FALSA, y n = 36

Lo encontro un enjambre de auditoria. Se verifico aqui otra vez, comando por
comando, porque un veredicto devuelto no es evidencia. Todo en
`tasks/evidence/DEBT-BB-USABLE-CIEGO-A-LA-LATENCIA/n-no-es-cero-2026-09-26.txt`.

### Primero: la sonda que el PASO 1 dice haber puesto NO esta corriendo

```
systemctl status bb-usable  -> active (running) since 2026-09-25 05:10:18
stat bin/bb-usable          -> modificado    2026-09-25 07:43:06
el commit de la sonda       ->               2026-09-25 07:54:11
journalctl -u bb-usable | grep -c "latencia del escritorio"  ->  0
```

El demonio vivo arranco **2 h 44 min ANTES** de que el codigo existiera, y
`Restart=no` mas ningun reinicio desde entonces. Python no recarga en caliente.
Cero lineas de esa senal en 34 horas de servicio activo.

El codigo esta en el repo y su test pasa. Lo que no esta es CORRIENDO. Y
`bb status` dice ARMADO porque comprueba que la unit este activa -- cierto, y no
lo mismo. **Una fila ARMADO sobre un demonio que corre codigo viejo es la forma
mas silenciosa de este defecto.**

### Segundo: la sonda HERMANA si midio, y hay 36 episodios

`bin/bb` guarda `x.{estado,ms}` en cada muestra y eso si lleva grabando:

```
muestras con campo x:                          2016
por encima del techo sano (13 ms) o no-OK:       69   (3.42 %)
de esas, con los TOTALES SANOS                   44
```

### El control que separa "escritorio lento" de "bb sin CPU"

`x.ms` incluye lanzar `xset`, asi que podria estar midiendo que el muestreador se
quedo sin CPU. `smi.ms` mide igual contra OTRO sujeto, y su linea base es
**mediana 21 ms, p95 25**. Si suben los dos, el confundido es bb.

```
ts                   x.ms  smi.ms  load1  cpu_some  lectura
2026-09-25T13:38      773      41  18.82      4.71  ESCRITORIO lento
2026-09-26T05:53      577      46   2.63      0.00  ESCRITORIO lento
2026-09-25T12:56      654      42   5.05      0.08  ESCRITORIO lento
2026-09-26T06:11      334    2728  14.00      0.01  bb sin CPU
2026-09-25T08:13      289     963  10.97     24.91  bb sin CPU

de las 44:  36 escritorio lento de verdad  ·  8 bb descheduleado
```

El control sabe decir NO -- caza 8 como confundidos, uno con `smi.ms` en 2728 ms.

**Peor caso real: 773 ms, 59 veces el techo sano**, con nvidia-smi contestando en
41 ms y los totales limpios. Y el mas limpio: `2026-09-26 05:53`, 577 ms con
`load1=2.63` y `cpu_some=0.00` -- la maquina en reposo por todos los totales, y
medio segundo para que el escritorio conteste.

### Lo que esto le hace a la ficha

La premisa decia: "UNA medida sana (4-7 ms) y CERO episodios malos. Con n=0 del
lado positivo no hay calibracion posible."

**n = 36.** Con techo sano medido, peor caso medido y un control que separa la
senal del artefacto. El PASO 3 ya tiene sujeto.

Lo que NO cambia: el corte sigue sin derivarse, y antes hay que arreglar que el
demonio que tendria que usarlo no corre el codigo que mide. Ese orden importa --
derivar un corte para un demonio que no lo va a leer es trabajo que se pierde.

## Como se cierra: por pasos, y el primero NO es actuar

**PASO 1 -- HECHO el 2026-09-25.** `bb-usable` mide la latencia del servidor X
en cada sonda (cada 30 s) y la deja en el journal. **No entra en ninguna
decision**, y eso tiene su propio test: recorre el AST de `main()` y falla si
`xms` aparece en la condicion de un `if` o un `while`. Lo que se guarda ahi es
una AUSENCIA, y una ausencia sin test se pierde en la siguiente edicion.

Cinco controles negativos corridos: un servidor que se cuelga devuelve el
PLAZO entero y no un numero pequeno (si devolviera algo bajo, una grafica
leeria "rapido" justo durante el incidente); sin `DISPLAY` devuelve `None` y no
`0`, porque "no se midio" e "instantaneo" no son lo mismo; un servidor que
rechaza devuelve `None`; y el comando se lee del entorno EN CADA LLAMADA.

Ese ultimo salio de un fallo real de esta misma tarde: ligar el comando al
importar dejaba los casos negativos sin poder montarse -- al cambiar la
variable despues, la funcion seguia llamando al `xset` real y devolvia un
numero donde debia devolver `None`. Lo encontro el control negativo, no leer
el codigo.

**PASO 2 -- pendiente.** Capturar al menos un episodio malo real, con la sonda
puesta. Lo espera `DEBT-SLUGGISH-SIN-CAUSA-PROBADA`.

**PASO 3 -- pendiente.** Solo entonces derivar un corte, y que `bb-usable`
AVISE con el antes de que se le permita actuar.

Linea base acumulada hasta hoy, que es lo unico que el paso 1 compra:
4-7 ms en reposo, 8 ms de mediana y 13 ms el peor caso con 40 quemadores sobre
20 nucleos. **Cero episodios malos.** Con n=0 del lado positivo no hay
calibracion posible: un corte derivado solo de medidas sanas no puede fallar
por el motivo que vigila.

Lo que NO cierra esto: darle un umbral inventado hoy. El `close_check` exige
que alguien escriba la calibracion en `tasks/done/`, con la frase literal
`umbral de latencia CALIBRADO`, porque no hay forma honesta de que un gate
provoque el episodio que falta.
