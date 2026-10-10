---
id: DEBT-VIGILANTE-MOTOR-SIN-PRESUPUESTO-DE-REINICIOS-01
kind: task
domain: INFERENCE
title: "Limitar los reinicios de bin/bb-vigilante-motor con tools/workload_restart_policy.py"
status: open
severity: P2
origin: asserted
satd_family: UNBOUNDED_ACTION
created: 2026-10-10
close_check: {"cmd": "python3 -m pytest -q tests/test_bb_vigilante_motor.py -k presupuesto", "expect": "exit_zero", "porque": "Debe existir una prueba que muestre que, agotado el presupuesto de reinicios por hora, el vigilante deja de reiniciar y lo registra, con su control negativo (dentro del presupuesto SI reinicia)."}
---

## Hueco

`bin/bb-vigilante-motor` reinicia `ai-nemotron.service` tras 3 fallos de chat seguidos, sin
tope. Con un cuelgue persistente reinicia cada ~8 min (3 sondeos de 2 min mas 2 min de
espera de chat) y cada arranque carga ~4 min el modelo. El repo ya tiene el mecanismo:
`tools/workload_restart_policy.py` presupuesta intentos por identidad de workload con
estado atomico, 3 por hora por defecto, y nunca reinicia por si mismo.

## Medido

`~/.local/share/blackbox/vigilante_motor.log`: 4 reinicios en 18 h (09-oct 10:15, 11:42,
12:59 y 10-oct 04:21). Hoy no hay bucle; el hueco es que nada lo impediria.

## Cuidado

La sesion Declutter espera al servidor hasta 30 min por llamada. Un tope que deje al motor
colgado sin reiniciar tambien la detiene: al agotarse el presupuesto hay que AVISAR, no
quedarse mudo.
