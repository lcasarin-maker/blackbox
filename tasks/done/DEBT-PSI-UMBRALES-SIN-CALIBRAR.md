---
id: DEBT-PSI-UMBRALES-SIN-CALIBRAR
kind: debt
title: Los umbrales LOW/MODERATE/HIGH/CRITICAL de PSI vienen de otra maquina y no de una medicion propia
status: done
severity: P2
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-09-08
closed_at: 2026-09-23
close_check: {"cmd": "grep -q 'calibrado 2026' bin/bb", "expect": "exit_zero"}
evidence: {"pass": "tasks/evidence/DEBT-PSI-UMBRALES-SIN-CALIBRAR/pass.txt", "fail": "tasks/evidence/DEBT-PSI-UMBRALES-SIN-CALIBRAR/fail.txt", "e2e": "tasks/evidence/DEBT-PSI-UMBRALES-SIN-CALIBRAR/e2e.txt", "control_cruzado": "tasks/evidence/DEBT-PSI-UMBRALES-SIN-CALIBRAR/sar_control_cruzado.txt", "suite": "python3 -m pytest tests/ -q --cov=tools --cov-report=term-missing -> 33 passed, tools/calibra_psi.py 89 stmts 0 miss 100%"}
reason: El trigger se cumplio por las dos vias a la vez (tercer incidente con PSI registrado, Y un umbral que dejo pasar un colapso). Calibrados los cortes contra los dos congelamientos propios del 2026-09-22/23 sobre 19804 muestras. El hallazgo obligo a cambiar la FORMA del corte, no solo sus numeros - el nivel instantaneo no discrimina en esta maquina y la tasa de subida tampoco; lo que discrimina es la duracion sostenida. Cerrada tambien la linea base de .simplecode/backlog_baseline.json que la cubria, para no dejar una LINEA BASE MUERTA.
---

## Root Cause

`bb scan` clasificaba la presion de memoria con la escala de `sparkview` (foro
NVIDIA 366877): LOW <5 %, MODERATE <20 %, HIGH <50 %, CRITICAL. Esos cortes
nunca se midieron en esta maquina. Con dos medidas propias no se podia calibrar
una escala de cuatro bandas, asi que quedaron declarados provisionales en el
codigo, en el README y en SPEC.md -- pero en uso.

El 2026-09-22/23 llegaron los datos que faltaban: **dos congelamientos, ambos
con reset duro**, con PSI registrado minuto a minuto alrededor.

| | inicio | fin | duracion |
| --- | --- | --- | --- |
| congelamiento 1 | 2026-09-22 05:45 | 2026-09-22 23:30 | 17 h 45 min |
| congelamiento 2 | 2026-09-22 23:49 | 2026-09-23 05:44 | 5 h 55 min |

## Que mostraron las mediciones

Corpus: 19804 muestras con PSI, 2026-09-08 07:57 -> 2026-09-23 10:53.

**1. El nivel instantaneo no discrimina, y se equivoca en las DOS direcciones.**

- Seis excursiones llegaron hasta **98.53 %** sin que la maquina se colgara.
- El valor mas bajo que **sostuvo** un congelamiento real fue **48.80 %**
  (2026-09-22 16:12, en mitad del congelamiento 1).

Un corte por nivel en 50 % grita en dias sanos y se calla dentro de un colapso.

**2. Las bandas intermedias de la escala ajena no se ocupan.**

97.84 % de las muestras tienen `mem_full` **exactamente 0.00**; solo 26 de 19804
caen entre 5 y 50. MODERATE y HIGH etiquetaban un tramo por el que esta maquina
no pasa. Una banda que nunca se ocupa no informa de nada.

**3. La tasa de subida tampoco discrimina** -- contra la hipotesis con la que se
abrio el analisis. Las dos mayores subidas de todo el corpus en <= 90 s son de
dias **sanos**:

```
  +76.30  09-20 16:54 -> 16:55  ( 7.25 -> 83.55)  sano
  +68.96  09-09 11:25 -> 11:26  (21.73 -> 90.69)  sano
  +65.60  09-22 05:44 -> 05:45  ( 1.78 -> 67.38)  DENTRO de congelamiento
```

Un corte por tasa dispara dos veces en falso antes de acertar una.

**4. Lo que discrimina es la DURACION**, por dos ordenes de magnitud:

| | excursiones sanas (n=6) | congelamientos (n=2) |
| --- | --- | --- |
| duracion sobre el 10 % | <= 2 min | 1042 min y 292 min |
| desenlace | se recuperan solas | reset duro |

**5. Y por eso ninguna metrica de NIVEL de memoria los vio venir**: durante las
dos ventanas `kbavail` marcaba entre **32 y 47 GB LIBRES** (`%memused` 58-69 %)
mientras todas las tareas estaban paradas. Es exactamente el hueco que PSI
existe para tapar, y la escala ajena lo tapaba mal.

## El corte nuevo

```
  mem_full >= 10 %  sostenido  >= 5 min   ->  COLAPSO
                               3 - 5 min  ->  SIN OBSERVAR
                               <= 3 min   ->  PICO
```

- **10 %** esta 4.9x por debajo del valor mas bajo que sostuvo un congelamiento
  (48.80 %) y es el punto donde la excursion sana mas larga se encoge a 2 min
  (a 5 % dura 3 min, a 1 % dura 5 min y ya produce un falso positivo).
- **5 min** esta 2.5x por encima de la excursion sana mas larga (2 min) y 58x
  por debajo del congelamiento mas corto (292 min).
- **3-5 min**: no hay NI UNA excursion ahi en 15 dias. Se imprime como
  `SIN OBSERVAR` en vez de asignarse a un lado.

`io_some` y `cpu_some` **se quedan sin etiqueta a proposito**. Tienen otra
distribucion entera -- `cpu_some` pasa de 5 % en 1473 muestras, `mem_full` solo
en 132 -- y no hay incidente propio que los etiquete. Aplicarles la misma escala
fue el error original; heredarla otra vez no lo arregla.

## Regression Test

- `python3 tools/calibra_psi.py` re-deriva los cortes desde el corpus y **sale 1**
  si dejan pasar un incidente o si disparan en una muestra sana. Existe para que
  la calibracion se pueda volver a comprobar cuando lleguen mas incidentes: una
  calibracion cuya evidencia solo vive en un comentario es el mismo instrumento
  ciego que esta ficha vino a cerrar, un nivel mas arriba.
- `tests/test_calibra_psi.py` -- 23 tests, cobertura 100 % de `tools/calibra_psi.py`
  (el watermark del repo es 100.00). Incluyen los controles negativos del propio
  calibrador.

## Verification Evidence

Ver los cuatro ficheros de `tasks/evidence/DEBT-PSI-UMBRALES-SIN-CALIBRAR/`.
Resumen:

**pass** -- el corte bueno sobre el corpus real:

```
  PICO        (<= 3 min)    11
  SIN OBSERVAR               0
  COLAPSO     (>= 5 min)     2   09-22 05:45 (1042 min), 09-22 23:49 (292 min)
  falsos positivos:          0
  incidentes no detectados:  0
  VEREDICTO: CALIBRADO            rc=0
```

**fail** -- cuatro controles negativos, cada uno moviendo un corte distinto.
Ninguno se argumenta: los cuatro se corren y salen en rojo.

| control | que afloja | resultado | rc |
| --- | --- | --- | --- |
| `--sostenido 0` | quita el corte de duracion | 11 falsos positivos | 1 |
| `--umbral 50 --sostenido 0` | **la escala vieja** (CRITICAL = nivel >= 50) | 4 falsos positivos | 1 |
| `--sostenido 500` | corte de duracion demasiado largo | 1 incidente no detectado | 1 |
| `--umbral 1` | corte de nivel demasiado bajo | 1 falso positivo | 1 |

Los cuatro importan: demuestran que **los dos** cortes son carga util, y que
este gate puede salir en rojo. El control negativo encontro ademas un defecto
real en el propio calibrador -- con la banda de `PICO` comprobada primero,
`--sostenido 0` salia `CALIBRADO` y rc=0, o sea el control no podia salir en
rojo. Invertido el orden de las dos comprobaciones (`clasifica`, comentado en
sitio) y vuelto a correr.

**e2e** -- `bb scan` sobre el corpus real (2 COLAPSO) y el mismo codigo sobre un
corpus sintetico 100 % sano con picos de 98.53 %: **COLAPSO 0**. La escala vieja
sobre ese mismo corpus habria dicho `CRITICAL`.

**control_cruzado** -- las etiquetas "sana"/"congelamiento" no salen de PSI, que
seria circular: salen de `sar`, que muestreo aparte y siguio corriendo cada
minuto durante las dos ventanas.

- las seis excursiones sanas: `ldavg-1` vuelve por debajo de 5 en menos de 6 min
  y `plist-sz` se desploma -- el proceso que comia memoria salio solo;
- los dos congelamientos: `ldavg-1` sostenido entre 100 y 185 la ventana entera
  (media 132 sobre 17 h), y la unica fila que lo rompe es el arranque limpio tras
  el reset.

## Limites declarados

1. **n=2 del lado positivo, y las dos la misma noche**: probablemente la misma
   causa raiz. La banda `COLAPSO` esta calibrada, no validada.
2. **La banda 3-5 min esta vacia.** No se afirma nada sobre ella.
3. **Las duraciones son cota inferior, nunca superior**: durante un congelamiento
   el propio muestreador se queda sin CPU (sus intervalos pasaron de 1 min a
   17-66 min), asi que los bordes caen donde alcanzo a correr.
4. **Esto REPORTA, no avisa a tiempo.** La confirmacion del segundo
   congelamiento llego 57 min despues de empezar, por ese mismo motivo. El
   guardarrail en vivo sigue siendo `bin/bb-usable` (commit 64d3daa), que **no**
   usa esta escala: decide por una sonda de asignacion.
5. **Solo el canal de memoria esta calibrado.** `io_some` y `cpu_some` siguen sin
   incidente propio que los etiquete, y por eso se imprimen sin etiqueta.

## Linea base

`.simplecode/backlog_baseline.json` cubria esta ficha hasta 2026-10-08. Al
cerrarla se saco de `entries`: una linea base que cubre algo que ya no existe se
lee como proteccion y no protege nada -- el propio gate lo llama LINEA BASE
MUERTA. Queda `DEBT-DGX-438-SIN-CAUSA-RAIZ`, que sigue abierta y sigue esperando
su medicion.
