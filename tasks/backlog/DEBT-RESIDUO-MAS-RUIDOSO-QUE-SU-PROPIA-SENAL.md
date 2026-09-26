---
id: DEBT-RESIDUO-MAS-RUIDOSO-QUE-SU-PROPIA-SENAL
kind: debt
title: "`residuo_mb` se mueve hasta 2.3 GiB en un segundo, y su comentario dice que no se mueve"
status: open
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
