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
