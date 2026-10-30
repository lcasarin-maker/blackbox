---
id: FEATURE-RELOJ-PRUEBA-CALENTAMIENTO-ANTES-DE-MEDIR-01
kind: task
domain: GPU
title: "bb reloj --prueba: calentar antes de contar TFLOP/s y medir si el sesgo existe"
status: open
severity: P3
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-10-26
close_check: {"cmd": "python3 -m pytest -q tests/test_reloj_atascado.py -k \"calentamiento\"", "expect": "exit_zero", "porque": "Especificacion pendiente, no prueba existente: exige que los TFLOP/s excluyan la fase de calentamiento y que la ficha cargue la medicion A/B real (con y sin calentamiento) o declare could_not_run."}
---

## Origen

El script del post [387029](https://forums.developer.nvidia.com/t/387029/1) hace 10 matmuls de calentamiento con
sincronizacion antes de cronometrar, y espera 3 s antes de muestrear el reloj ("let clocks ramp under load first").

## Hueco

`prueba()` en `tools/reloj_atascado.py` cronometra desde el primer ciclo y cuenta `hechos` desde ahi, rampa de reloj
incluida; solo descarta 2 s de las muestras de reloj (`filas[2:]`), no del conteo de TFLOP/s. Con una ventana de 15 s los
TFLOP/s podrian quedar sesgados a la baja. **Es una hipotesis: no esta medido.**

## Alcance

1. Medir primero: `bb reloj --prueba` con la GPU libre, N corridas con el codigo actual y N con calentamiento, mediana y
   dispersion de cada grupo, literal. Si la diferencia queda dentro de la dispersion, cerrar la ficha como `void_wontfix`
   con esas cifras; no se agrega codigo por una hipotesis sin efecto.
2. Si el sesgo existe: calentamiento (matmuls + `torch.cuda.synchronize()`) antes de arrancar el cronometro y de contar.

## Control negativo exigido

El A/B con las cifras literales. Sin GPU libre la medicion es `could_not_run`, y la ficha sigue abierta.

## Limite

Hardware unico (AI TOP ATOM sana, 77.4 TFLOPS posterior al arreglo). No dice nada sobre unidades atascadas.

## Avance 2026-10-30 (sigue ABIERTA: falta el A/B real)

Escrito el instrumento del A/B, sin cambiar la medicion por defecto:

- `prueba(segundos, calentamiento=0)`: los `calentamiento` matmuls y su `torch.cuda.synchronize()` van antes del cronometro
  y fuera de `hechos`; la salida declara `calentamiento` (una medicion sin calentar se distingue de una calentada). Por
  defecto 0, la de siempre: el sesgo sigue siendo hipotesis.
- `ab(n)` y `bb reloj --ab N`: N corridas sin y N con `CALENTAMIENTO_MATMULS` (10, como el script del hilo 387029),
  alternando el orden en cada par; mediana y rango (max - min) literales por brazo. Solo cuentan los TFLOP/s con
  `tflops_valido: true`; una corrida con la GPU ocupada o que no pudo cargar va a `no_corrio` y el veredicto es
  `COULD_NOT_RUN` (sale 2), nunca una cifra. Con todo valido: `SESGO_MEDIDO` si la diferencia de medianas supera el mayor
  rango, `DENTRO_DE_LA_DISPERSION` si no. N < 3 es `COULD_NOT_RUN`.
- Pruebas `-k calentamiento` (5), con sus controles negativos: sin calentamiento el primer matmul corre bajo el cronometro;
  brazos sin diferencia real dan `DENTRO_DE_LA_DISPERSION`; una corrida con GPU ocupada deja el A/B en `COULD_NOT_RUN`.
  Fallan las 5 contra el modulo anterior; la mutacion `hechos = calentamiento` (contar el calentamiento) rompe 1 y la que
  quita la guarda de `tflops_valido` rompe 1.

Lo que falta (could_not_run, no corrido por el agente: carga la GPU, prohibido en esa sesion): con la GPU libre (motor
parado), `bb reloj --ab 5` (~2.5 min de carga). Pegar la salida aqui. Si sale `DENTRO_DE_LA_DISPERSION`, cerrar como
`void_wontfix` con esas cifras y dejar `calentamiento=0`; si sale `SESGO_MEDIDO`, poner `calentamiento=CALENTAMIENTO_MATMULS`
como defecto de `prueba` y cerrar `fixed`. El close_check (`-k calentamiento`) ya sale 0, pero el "porque" del close_check y el
control negativo de esta ficha exigen el A/B real: con solo las pruebas la ficha no se cierra.
