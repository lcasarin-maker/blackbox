---
id: DEBT-TELEMETRIA-GPU-SIN-COTA-EN-CALIENTE
kind: debt
title: "El jsonl de telemetria termica solo se recorta al ARRANCAR el proceso, y lleva 143 MB"
status: open
severity: P3
origin: detected
detector: {"rule": "bb/limpieza-2026-09-25", "confidence": 1.0}
satd_family: UNBOUNDED_GROWTH
created: 2026-09-25
close_check: {"cmd": "python3 -m pytest tests/test_atom_gpu_telemetry.py -k rotacion_en_caliente -q", "expect": "exit_zero"}
---

## Que pasa

`tools/atom_gpu_telemetry.py` tiene su anillo: `rotar_si_hace_falta()` deja
`LINEAS_A_CONSERVAR = 100_000` cuando el fichero pasa de `MAX_LINEAS = 200_000`.
Esta bien escrito, tiene tests, y **se llama una sola vez, en `main()`, al
arrancar el proceso**.

El servicio corre en bucle cada 5 s y solo se reinicia con la maquina. Medido
el 2026-09-25:

```
atom_gpu_telemetry.jsonl   143 MB   148 251 lineas   desde 2026-09-15
17 280 lineas/dia  ->  14.3 MB/dia
```

Esta por debajo del corte, asi que hoy no pasa nada. Lo que no hay es cota
mientras el proceso vive: con un arranque de quince dias serian ~400 000
lineas y ~200 MB, y el recorte no llegaria hasta el siguiente reinicio.

## Lo que NO lo cubre, comprobado

El gate `telemetry-bound` del kit -- "telemetry stays under the 10 MiB horizon
SPEC declares" -- pasa en verde con este fichero a 143 MB, y no es un defecto
suyo: mide `.simplecode/evidence/*.jsonl`, la telemetria del propio kit. Los
datos de bb viven en `$BLACKBOX_DATA` y **ningun gate mira su tamano**. Las
muestras de `bb sample` si se podan por `RETAIN_DAYS`, pero eso borra ficheros
por fecha y este es un solo fichero que crece.

## Como se cierra

Llamar a `rotar_si_hace_falta()` tambien dentro del bucle, sin pagarlo cada
5 s: la funcion lee el fichero ENTERO en memoria para recortarlo, asi que
hacerlo en cada iteracion seria cambiar un problema por otro. Lo barato es un
`stat` -- comparar el tamano contra una cota y solo entonces contar lineas --
cada N iteraciones.

Con su control negativo: un fichero plantado por encima del corte tiene que
recortarse SIN reiniciar el proceso, y uno por debajo no.

## Por que P3 y no mas

No amenaza la maquina: 200 MB en un disco con 2.5 TB libres. Lo que cuesta es
que cada consumidor que lee ese jsonl -- `bb scan`, `_muestras_recientes`, el
gate termico -- paga el tamano. `bb scan` ya lee 1401 muestras de ahi en cada
corrida.
