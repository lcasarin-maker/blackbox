---
id: FEATURE-RELOJ-VEREDICTO-BAJO-NO-ATASCADO-01
kind: task
domain: GPU
title: "bb reloj: separar 'rendimiento bajo con throttle o reloj alto' de 'atascado'"
status: done
closed_at: 2026-10-26
closure_type: fixed
closure_reason: "INDETERMINADO lleva motivos separados: THROTTLE_ACTIVO (con las razones), RELOJ_EN_BANDA (con la mediana) y RELOJ_ALTO_RENDIMIENTO_BAJO (>= 1400 MHz sin throttle y TFLOP/s bajos). Sin cuarto estado, umbrales 1000/1400 sin tocar; ATASCADO y SANO de hoy sin cambio, con y sin TFLOP/s. Tests en rojo contra el codigo viejo y contra dos mutantes."
evidence:
  fail: tasks/evidence/FEATURE-RELOJ-VEREDICTO-BAJO-NO-ATASCADO-01/fail.txt
  pass: tasks/evidence/FEATURE-RELOJ-VEREDICTO-BAJO-NO-ATASCADO-01/pass.txt
severity: P3
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-10-26
close_check: {"cmd": "python3 -m pytest -q tests/test_reloj_atascado.py -k \"bajo_no_atascado\"", "expect": "exit_zero", "porque": "Especificacion pendiente, no prueba existente: exige que TFLOP/s bajo con razon de throttle activa o reloj >= 1400 MHz de un motivo distinto de 'reloj entre umbrales' y no sea ATASCADO."}
---

## Origen

El script del post [387029](https://forums.developer.nvidia.com/t/387029/1) distingue tres salidas de bajo rendimiento: la
firma clasica (TFLOP/s bajo, reloj bajo, sin throttle) y "LOW, but not the classic stuck signature (a throttle reason is
active or the clock is high)", donde recomienda revisar refrigeracion.

## Hueco

`decide()` en `tools/reloj_atascado.py` devuelve `INDETERMINADO` con el motivo generico "reloj entre los umbrales o con
razones de throttle activas" para casos de causa distinta: reloj en la banda 1000-1400 MHz sin throttle, y throttle activo.
El usuario no sabe si mirar la energia o el calor.

## Alcance

Motivos separados dentro del mismo estado `INDETERMINADO` (no un cuarto estado): `THROTTLE_ACTIVO` (con las razones
listadas) y `RELOJ_EN_BANDA` (con la mediana). Depende de que `prueba()` entregue `tflops` a `decide()`; esa conexion vive en
`FEATURE-RELOJ-ATASCADO-SEGUNDO-EJE-TFLOPS-Y-GUARDA-DE-OCUPACION-01`. No cambiar los umbrales 1000/1400.

## Control negativo exigido

Throttle activo => motivo `THROTTLE_ACTIVO`; reloj 1200 MHz sin throttle => `RELOJ_EN_BANDA`; las dos filas de hoy
(`ATASCADO` y `SANO`) no cambian de estado. Un test que solo prueba los motivos nuevos no cierra la ficha.

## Cerrada 2026-10-26
`decide()` en `tools/reloj_atascado.py` (tras la conexion de `tflops` de la ficha del segundo eje):
- `THROTTLE_ACTIVO: razones <lista ordenada de valores de throttle distintos de cero>` cuando alguna muestra con carga tiene
  throttle y no es SANO.
- `RELOJ_EN_BANDA: mediana <MHz> entre 1000.0 y 1400.0 sin TFLOP/s bajos` sin throttle, sin TFLOP/s o con TFLOP/s >= umbral.
- `RELOJ_ALTO_RENDIMIENTO_BAJO`: mediana >= 1400 MHz, sin throttle y TFLOP/s < umbral. Decision propia: el porque del
  close_check pide un motivo distinto para "reloj >= 1400 MHz" con TFLOP/s bajos y la ficha solo nombraba dos; el post llama
  a ese caso "LOW, but not the classic stuck signature". Sale `INDETERMINADO` (no `SANO`): con TFLOP/s medidos bajos no se
  afirma sano. Solo ocurre con TFLOP/s medidos (`--prueba`); el detector pasivo sobre la telemetria sigue dando `SANO` a >= 1400.
Sin cuarto estado; 1000/1400 sin tocar.

Tests: `test_bajo_no_atascado_throttle_activo_lista_las_razones`, `test_bajo_no_atascado_reloj_alto_con_tflops_bajo_no_es_atascado`,
`test_bajo_no_atascado_reloj_en_banda_sin_throttle_da_la_mediana` y el control negativo
`test_bajo_no_atascado_control_negativo_las_filas_de_hoy_no_cambian` (660 MHz => ATASCADO sin TFLOP/s y con 23.5; 2080 MHz
=> SANO sin TFLOP/s y con 77.4; 2400 MHz con throttle y sin TFLOP/s => SANO, como hoy).
