---
id: DEBT-RESIDUO-MAS-RUIDOSO-QUE-SU-PROPIA-SENAL
kind: debt
title: "`residuo_mb` se mueve hasta 2.3 GiB en un segundo, y su comentario dice que no se mueve"
status: done
closed_at: 2026-09-27
closure_type: fixed
evidence:
  pass: tasks/evidence/DEBT-RESIDUO-MAS-RUIDOSO-QUE-SU-PROPIA-SENAL/pass.txt
  fail: tasks/evidence/DEBT-RESIDUO-MAS-RUIDOSO-QUE-SU-PROPIA-SENAL/fail.txt
  e2e: tasks/evidence/DEBT-RESIDUO-MAS-RUIDOSO-QUE-SU-PROPIA-SENAL/e2e.txt
severity: P2
origin: detected
detector: {"rule": "sunset-audit 1.7", "confidence": 1.0}
satd_family: UNCALIBRATED_THRESHOLD
created: 2026-09-25
close_check: {"cmd": "grep -q 'ruido de residuo_mb MEDIDO' tasks/done/DEBT-RESIDUO-MAS-RUIDOSO-QUE-SU-PROPIA-SENAL.md", "expect": "exit_zero", "porque": "cerrar esto pide decidir que afirma `residuo_mb` de verdad, y eso no se puede hacer sin medir su ruido a varios intervalos y contra una reserva con dueno conocido. No es codigo que se escriba hoy: es una caracterizacion. El patron de escribirlo es el de DGX-438."}
---

## Como salio

En la revision de sunset de 1.7, verificando la exencion de `time.sleep(1)` en
`tests/test_bb_bash.py::test_residuo_es_un_numero_y_no_se_mueve_solo` -- la unica
que en 1.6 se retagueo diciendo "NO VERIFICADO", con disparador en 1.7.

El control que faltaba era medir si el residuo se mueve de verdad. Se midio, con
ocho repeticiones por lado en vez de una:

```
espera   |delta| de residuo_mb entre dos muestras, n=8, maquina en reposo
  0 s    min  62   mediana  306   max   635 MiB
  1 s    min  33   mediana  801   max  2305 MiB
```

La exencion queda VERIFICADA: la espera cambia la medida, no es decoracion --
la mediana se multiplica por 2.6 y el maximo por 3.6.

Pero el mismo control deja ver dos cosas peores.

## 1 · El test es FLAKY, y su propio sleep es lo que lo empuja

Su asercion es `abs(b - a) < 2048`. Una de las ocho corridas dio **2305**. O sea
que el test falla por la varianza normal de la maquina en reposo, y falla mas
cuanto mas espera.

Es la cuarta instancia el mismo dia de la misma clase de fallo -- un umbral que
no cubre la varianza real del sujeto. Las otras tres fueron las dos aserciones
de pertenencia a listas `head -5` y el `KeyError` por leer una muestra de rafaga
como si fuera completa.

## 2 · Y el comentario de `bin/bb` afirma una estabilidad que el numero no tiene

`bin/bb:282` dice, sobre el caso de memoria con dueno:

> memoria que SI tiene dueno -- el residuo no se mueve (delta +0.0 GB)

Medido: el residuo se mueve hasta **2.3 GiB en un segundo con la maquina en
reposo**, sin que nadie reserve nada. Un "delta +0.0 GB" no describe este
numero.

Eso importa mas que el flake, porque es la afirmacion sobre la que se apoya el
valor del campo: si el residuo absorbiera 5 GiB cuando un proceso reserva 5 GiB,
el campo no distinguiria memoria con dueno de memoria sin dueno. El ruido
medido (2.3 GiB) es **casi la mitad** de esa senal (5 GiB), asi que la
separacion existe pero es de un factor 2, no de un `+0.0`.

## Por que no se arregla hoy con un numero mas grande

Subir el umbral a 4096 haria desaparecer el flake y no mediria nada mejor: el
maximo del ruido crece con el intervalo y con la carga, asi que el siguiente
umbral tambien se quedaria corto. Y un umbral elegido para que el test pase es
lo contrario de un umbral calibrado.

## Como se cierra

Caracterizando el campo, que es lo que nadie hizo:

1. el ruido de `residuo_mb` a varios intervalos y con la maquina cargada, no
   solo en reposo -- la carga es justo lo que rompio los otros tres tests de hoy;
2. el delta CONTRA una reserva de tamano conocido y dueno conocido, que es la
   afirmacion que el comentario de `bin/bb` hace y nadie midio;
3. y con las dos cosas, o un umbral derivado, o la conclusion de que el campo no
   sostiene la afirmacion y hay que cambiar lo que afirma.

## Limite declarado

Esta ficha no dice que `residuo_mb` este mal. Dice que **nadie sabe cuanto ruido
tiene**, que su comentario declara un `+0.0 GB` que la medida contradice, y que
su test pasa o falla por azar dentro de esa ignorancia. Cabe perfectamente que
la conclusion sea que el campo sirve y lo que sobra es la palabra "no se mueve".

## CERRADA 2026-09-27 -- ruido de residuo_mb MEDIDO

### Root Cause

El campo nunca tuvo su ruido medido, y sobre esa ignorancia se escribieron dos
cosas falsas: el `+0.0 GB` del comentario de `bin/bb:282` y el tope de 2048 MiB
del test. Un cero escrito sin ruido con que compararlo, y un umbral elegido para
que el test pasara.

### Regression Test

`tests/test_bb_bash.py::test_residuo_es_un_numero_y_CABE_en_la_maquina`, que ya
no afirma que el residuo «no se mueve» -- esa mitad se retiró en la revisión de
sunset de 1.7, cuando la medida la refutó. Afirma lo que se puede afirmar: que es
un entero y que cabe en la máquina. Un `residuo_mb` mayor que `MemTotal` sería
una resta mal hecha, y eso sí es un defecto y no ruido.

No se añade un umbral nuevo, y es deliberado: **el ruido escala con la carga por
un factor de 29**, así que cualquier tope fijo sobre este campo depende de lo
ocupada que esté la caja. Poner uno sería repetir el defecto con otro número.

### Verification Evidence

**ruido de residuo_mb MEDIDO**, n = 3308 pares contiguos del corpus, |delta| MiB:

```
estado                   n     mediana   p95    p99     max
reposo (load1 < 4)     2690        47    825   1825    4007
media  (4-20)           535       849   4576   7193    8035
carga  (load1 >= 20)     83      1370   7096   8053    8053
```

Contra una reserva de 6 GiB con dueño (RSS confirmado en 6.0 GiB, tocada página
por página, con techo vía `bb cap`):

```
antes  media -2824.8   durante media -3262.2   despues media -2903.0
se movio -437 MiB = 7.1 % de la reserva  ->  RECHAZA el 92.9 %
```

Los 437 MiB caben dentro del ruido en reposo (p95 = 825), así que no se
distinguen de él. Lo cierto no es «+0.0 GB» sino «menos que su propio ruido».

### La conclusión: el campo sirve

```
senal que el campo existe para ver: 21 000 MiB desaparecidos sin dueno
separacion sobre el ruido en reposo:  25x
separacion sobre el ruido con carga:  3.0x
```

Es exactamente lo que esta ficha dejó abierto como posibilidad: «cabe
perfectamente que la conclusión sea que el campo sirve y lo que sobra es la
palabra "no se mueve"». Es lo que salió. `bin/bb:282` queda reescrito con estos
números, **incluido el 3.0x**, que es el margen incómodo y el que un lector
necesita saber.

### Lo que este cierre NO afirma

- El bucket de carga tiene **n = 83**, el menos poblado, y es el que da el margen
  de 3.0x. Con más días de carga real esa cifra puede empeorar.
- La reserva del control es RAM ordinaria, no memoria unificada de GPU. La
  afirmación original hablaba de 4 GiB de CUDA por torch y eso **no se repitió**:
  la máquina murió de un kernel panic por presión de memoria doce horas antes, y
  tomar memoria de GPU para un control no lo justifica. Lo medido es «rechaza
  memoria con dueño visible en RSS»; la variante de GPU queda sin repetir.
- Y la tasa de flake del test se corrige: la ficha la estimó en «1 de 8» con ocho
  repeticiones; con 3308 pares es **1 de 23** (142 pares sobre 2048 MiB), y sube
  con la carga.
