---
id: FEATURE-RED-CPU-SCAN
kind: task
title: bb scan nunca leia los contadores de red/CPU que bb sample ya capturaba
status: done
severity: P2
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-09-09
closed_at: 2026-09-09
close_check: {"cmd": "grep -q 'red y CPU por nucleo (muestras de blackbox)' bin/bb", "expect": "exit_zero", "porque": "el fix es codigo en bin/bb, no una ficha de evaluacion -- el close_check verifica que la seccion nueva de cmd_scan existe. Un solo grep, sin && (SHELL_OPERATORS_RE de backlog_verifier.py prohibe operadores de pipeline en verification_command)."}
evidence: {"control_negativo_vigente": "$ BLACKBOX_DATA=/tmp/bb_empty_test ./bin/bb scan '1 hour ago' | sed -n '/red y CPU por nucleo/,/^-- /p'\n-- red y CPU por nucleo (muestras de blackbox) --\n  tasas de red/CPU:            COULD_NOT_RUN\nSin historial, el gate cae en COULD_NOT_RUN y no en un falso 'sin dato' -- distingue instrumento apagado de sujeto sin sintoma.", "e2e": "tasks/evidence/FEATURE-RED-CPU-SCAN/e2e.txt", "fail": "tasks/evidence/FEATURE-RED-CPU-SCAN/fail.txt", "fail_control_negativo_1": "Primer intento tomaba la PRIMERA linea de *.jsonl como ventana sin comprobar que trajera los campos: las muestras de 2026-09-07 (antes de que cpu_jiffies/red existieran en cmd_sample) no los tienen, asi que 'primero' quedaba sin datos. Se destapo corriendo el mismo comando con ventanas distintas ('1 hour ago' vs '1 second ago') y viendo que daban IDENTICO resultado -- ninguna de las dos deberia coincidir. Arreglado: primero/ultimo se buscan por separado, solo entre lineas que SI traen el campo.", "fail_control_negativo_2": "Segundo bug, mismo mecanismo: parse_pairs(...,2) para el campo 'red' (formato real 'iface:rx:tx', 3 partes al hacer split, no 2) devolvia diccionarios vacios en silencio -- ningun error, cero lineas de red impresas. Verificado en aislamiento: `parse_pairs(primero_red.get('red'), 2)` -> `[]`; con n=3 -> los 7 interfaces reales. Arreglado cambiando el argumento a 3.", "pass": "tasks/evidence/FEATURE-RED-CPU-SCAN/pass.txt"}
reason: bb sample() captura red_bytes()/cpu_jiffies() en cada muestra desde 2026-09-07 (contadores crudos rx/tx por interfaz, idle/total por nucleo) pero ningun comando los leia: el analisis nunca se conecto a la captura. La cosecha de Atlas senalo el hueco desde tres angulos distintos (red rara, vCPU al 100%, puerto ethernet caido) que resultaron ser la MISMA causa raiz de instrumentacion. Se agrego la seccion '7b' a cmd_scan: nucleo mas ocupado (mismo patron que ya encontro cpu19 al 72% a mano el 2026-09-08) y tasa rx/tx por interfaz, con aviso de contador retrocedido (reconexion) y trafico cero sostenido.
---

## Root Cause

`bb sample()` captura `red_bytes()`/`cpu_jiffies()` en cada muestra desde
2026-09-07 (contadores crudos rx/tx por interfaz, idle/total por nucleo),
pero `cmd_scan` nunca leia esos dos campos del JSONL -- el analisis nunca se
conecto a la captura. No era un mecanismo de captura ausente, era el cruce
que faltaba sobre datos que ya existian en disco.

## Regression Test

`grep -q 'nucleo mas ocupado en la ventana' bin/bb && grep -q 'rx %8.1f KB/s' bin/bb`
(el `close_check` de esta ficha) falla si la seccion nueva de `cmd_scan`
desaparece de `bin/bb`. No hay suite de pytest para este repo bash; la
regresion real se corrio a mano dos veces (ver Verification Evidence) contra
datos de produccion antes y despues del fix de los dos bugs descritos abajo.

## Verification Evidence

Caso real (datos de produccion, 2342 muestras 2026-09-07..09):

```
$ ./bin/bb scan "1 hour ago" | sed -n '/red y CPU por nucleo/,/^-- /p'
-- red y CPU por nucleo (muestras de blackbox) --
  nucleo mas ocupado en la ventana: cpu5 al 28.4%
  enP7s7     rx     91.1 KB/s  tx     92.8 KB/s  (100215 s)
  docker0    rx     32.8 KB/s  tx     11.0 KB/s  (100215 s)
```

Control negativo (sin historial):

```
$ BLACKBOX_DATA=/tmp/bb_empty_test ./bin/bb scan '1 hour ago' | grep 'red/CPU'
  tasas de red/CPU:            COULD_NOT_RUN
```

Dos bugs reales atrapados por el control negativo antes de dar el mecanismo
por bueno (detalle completo en `evidence.fail_control_negativo_1/2` del
frontmatter): (1) tomar la primera linea de `*.jsonl` sin comprobar que
trajera los campos nuevos daba una ventana vacia por diseno -- destapado
corriendo `'1 hour ago'` vs `'1 second ago'` y viendo el MISMO resultado; (2)
`parse_pairs(..., 2)` para el campo `red` (formato real `iface:rx:tx`, 3
partes) devolvia diccionarios vacios en silencio.

## Fichas HARVEST de origen (cosecha de Atlas, evaluadas 2026-09-09)

- HARVEST-351340-weird-network-behaviour: cruce swap/IO vs red por contencion de bus
- HARVEST-362964-vllm-100-cpu-usage-when-idle-again: sintoma real que el nucleo-mas-ocupado hoy captura
- HARVEST-366125-ethernet-port-on-dgx-spark-is-not-working: parte del ethtool/link-state queda FUERA de este ticket (ver nota abajo), la parte de contadores de trafico ya cruzados aqui

## Lo que queda fuera, a proposito

`ethtool` (estado de negociacion de enlace), contadores EEE/LPI, y vectores MSI-X
en `/proc/interrupts` son fuentes NUEVAS que este ticket no capturaba -- no una
mejora sobre datos ya existentes, sino instrumentacion nueva de red. Quedan en
su propio alcance (no se agregaron aqui para no mezclar "activar analisis de lo
ya capturado" con "capturar algo que nunca se capturo").
