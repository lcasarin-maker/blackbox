---
id: DEBT-TELEMETRIA-GPU-SIN-COTA-EN-CALIENTE
kind: debt
title: "El jsonl de telemetria termica solo se recorta al ARRANCAR el proceso, y lleva 143 MB"
status: done
severity: P3
origin: detected
detector: {"rule": "bb/limpieza-2026-09-25", "confidence": 1.0}
satd_family: UNBOUNDED_GROWTH
created: 2026-09-25
closed_at: 2026-09-25
close_check: {"cmd": "python3 -m pytest tests/test_atom_gpu_telemetry.py -k rotacion_en_caliente -q", "expect": "exit_zero"}
evidence: {"pass": "tasks/evidence/DEBT-TELEMETRIA-GPU-SIN-COTA-EN-CALIENTE/pass.txt", "fail": "tasks/evidence/DEBT-TELEMETRIA-GPU-SIN-COTA-EN-CALIENTE/fail.txt", "e2e": "tasks/evidence/DEBT-TELEMETRIA-GPU-SIN-COTA-EN-CALIENTE/e2e.txt"}
reason: "El anillo actua ahora tambien en caliente, cada 720 muestras (una hora), mirando el TAMANO con un stat en vez de contar lineas. Y de paso se corrigio el techo declarado: el docstring decia ~400 bytes por linea y son 966 medidos, asi que las 200,000 lineas del anillo son 184 MB y no los 75 que afirmaba."
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


## Root Cause

Dos, y la segunda no estaba en la ficha.

**El anillo se llamaba una sola vez**, en `main()`. El servicio corre en bucle
cada 5 s y sólo se reinicia con la máquina, así que entre que el fichero pasa
del corte y el siguiente arranque no había cota ninguna.

**Y el corte declarado estaba mal medido.** El docstring de
`rotar_si_hace_falta` decía "~75 MB a ~400 bytes por línea". Medido sobre el
fichero que el propio código produce -- 138.3 MB en 150,040 líneas -- son **966
bytes por línea**: las 200,000 del anillo son **184 MB**, 2.4 veces más. Era
una estimación escrita al lado del código y nunca contrastada con su salida.
Nadie lo habría notado porque el único momento en que se comprobaba algo era
al arrancar el proceso.

## Regression Test

Cinco tests en `tests/test_atom_gpu_telemetry.py`:

- recorta cuando el fichero pasa del techo de bytes;
- **por debajo del techo NO toca el fichero** -- si recortara igual, la
  "rotación en caliente" sería una pérdida de datos periódica con otro nombre;
- pasa de `MAX_LINEAS` pero no de `MAX_BYTES` y **no se toca**: prueba que la
  puerta es el tamaño, que es lo que la hace barata. Contar líneas exige LEER
  el fichero, y leer 138 MB cada hora para descubrir que no hay nada que hacer
  sería cambiar un problema por otro;
- sin fichero no revienta: corre dentro del bucle del sampler, y una excepción
  ahí mata la telemetría entera para ahorrar un recorte;
- el techo en bytes está por ENCIMA del techo en líneas a la densidad medida,
  para que el guardia de bytes no se adelante al de líneas: tiene que actuar
  cuando el de líneas ya debería haber actuado y no pudo.

## Verification Evidence

```
fichero real     138.3 MB   150,040 lineas
bytes/linea             966   (el docstring decia ~400)
MAX_LINEAS=200000       184 MB a esa densidad, no 75
MAX_BYTES               192 MB  -- por encima, no se adelanta
revision               cada 720 muestras = 1 hora a 5 s
coste de revisar       un stat
```

Cuando el guardia dispara escribe su propio evento `rotacion` en el jsonl, con
cuántas líneas recortó y por qué: un recorte silencioso sería indistinguible de
una pérdida de datos.

## Limites declarados

- El guardia revisa cada hora, no continuamente. Entre dos revisiones el
  fichero puede pasar del techo en ~0.7 MB a la tasa medida (15.9 MB/día). Es
  deliberado: lo que dispara es caro y lo que vigila tarda días en ocurrir.
- Sigue sin haber ningún gate que mire el tamaño de los datos de bb.
  Comprobado: `telemetry-bound` del kit pasa en verde con este fichero a 138 MB
  porque mide `.simplecode/evidence`, no `$BLACKBOX_DATA`. Esta ficha acota el
  crecimiento; no añade un gate que lo vigile desde fuera.
