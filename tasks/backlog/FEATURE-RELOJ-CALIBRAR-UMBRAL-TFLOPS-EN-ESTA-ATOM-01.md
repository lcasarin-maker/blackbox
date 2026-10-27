---
id: FEATURE-RELOJ-CALIBRAR-UMBRAL-TFLOPS-EN-ESTA-ATOM-01
kind: task
domain: GPU
title: "bb reloj: calibrar en esta ATOM el umbral PROVISIONAL de TFLOP/s (60, de GX10)"
status: open
severity: P3
origin: detected
satd_family: BLIND_INSTRUMENT
created: 2026-10-26
close_check: {"cmd": "python3 -c \"from tools import reloj_atascado as r; import sys; sys.exit(r.UMBRAL_TFLOPS_ESTADO.startswith('PROVISIONAL'))\"", "expect": "exit_zero", "porque": "Mientras el umbral siga marcado PROVISIONAL sale 1; solo pasa cuando alguien cambia la marca, y la ficha exige que ese cambio cargue la medicion real."}
---

## Origen

Abierta al cerrar `FEATURE-RELOJ-ATASCADO-SEGUNDO-EJE-TFLOPS-Y-GUARDA-DE-OCUPACION-01` (2026-10-26). `decide()` usa
`UMBRAL_TFLOPS = 60.0`, el corte de `gb10_clockcheck.py` (hilo 387029), medido en GX10. Esta ATOM no tiene linea base: su
unica lectura propia (2080 MHz, 67 W, 77.4 TFLOPS fp16) es posterior al arreglo. El codigo lo declara con `ponytail:` y la
salida lo imprime en `umbral_tflops_estado`.

## Alcance

1. Con la GPU libre (la guarda `GPU_OCUPADA` ya lo exige), N corridas de `bb reloj --prueba`; mediana y dispersion literal
   de TFLOP/s, reloj y potencia. Conviene hacerlo junto con `FEATURE-RELOJ-PRUEBA-CALENTAMIENTO-ANTES-DE-MEDIR-01`, que
   puede mover la cifra.
2. Fijar el umbral con la regla escrita (por ejemplo, una fraccion de la mediana sana con la dispersion a la vista) y
   cambiar `UMBRAL_TFLOPS_ESTADO` para que cite la medicion.

## Control negativo exigido

El close_check sale 1 hoy (el estado empieza por PROVISIONAL). Una corrida sana propia debe salir `SANO` con el umbral nuevo y
las filas sinteticas de 40 TFLOP/s a 1200 MHz deben seguir `ATASCADO`. Sin GPU libre la medicion es `could_not_run` y la
ficha sigue abierta.

## Limite

Una sola unidad sana; sin una ATOM atascada medida, el lado positivo del umbral sigue siendo de GX10.
