---
id: DEBT-VIGILANTE-MOTOR-SIN-PRESUPUESTO-DE-REINICIOS-01
kind: task
domain: INFERENCE
title: "Limitar los reinicios de bin/bb-vigilante-motor con tools/workload_restart_policy.py"
status: done
closed_at: 2026-10-10
closure_type: fixed
reason: "bin/bb-vigilante-motor cuenta sus reinicios con tools/workload_restart_policy.py (3 por hora); agotado el tope deja de reiniciar, guarda bb snapshot, escribe motor_alerta.json, avisa al escritorio y bb status marca FALTA; una tarea programada lee la alerta cada 10 min y avisa a Luis."
evidence: {"pass":"tasks/evidence/DEBT-VIGILANTE-MOTOR-SIN-PRESUPUESTO-DE-REINICIOS-01/pass.txt","fail":"tasks/evidence/DEBT-VIGILANTE-MOTOR-SIN-PRESUPUESTO-DE-REINICIOS-01/fail.txt","e2e":"tasks/evidence/DEBT-VIGILANTE-MOTOR-SIN-PRESUPUESTO-DE-REINICIOS-01/e2e.txt"}
owner: Luis; tope y aviso votados en la boleta del 2026-10-10
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

## Datos de la sesion Declutter (2026-10-10, mensaje entre sesiones, sin verificar aqui)

- Su corrida de fichas sobrevive a caidas por conexion rechazada y por chat colgado sin
  perder documentos (sus fichas DECL-CORE-326 y 327). Un reinicio rapido le sale barato.
- Lo caro es un servidor que no vuelve en mas de 30 min: su lanzador espera 20 min y aborta.
- Recomienda tope de 3 reinicios por hora y, agotado, dejar de reiniciar y mostrar una
  alerta visible en `bb status`. Pide que se le avise el numero final para ajustar su lanzador.

Propuesta pendiente de decision: 3 por hora (el valor por defecto de la politica) y fila
nueva en `bb status` que diga FALTA mientras el presupuesto este agotado.

## Cierre (2026-10-10)

Votado por Luis: tope de 3 por hora con snapshot, alerta y una tarea programada que la lea. La tarea `motor-llm-alerta` corre cada 10 min, no hace nada si no hay `motor_alerta.json` y avisa una sola vez por alerta. Solo funciona con la app de escritorio abierta: si esta cerrada, la tarea corre al abrirla.

Si la politica de reinicios no puede correr, el vigilante reinicia igual y lo registra: el instrumento no debe tumbar el servicio que cuida. Con tope 3 y los 4 reinicios medidos (86 min, 77 min y 15.4 h de distancia) el tope no habria bloqueado ninguno.

`fail.txt` es la misma suite contra un vigilante con el limite subido a 99: el cuarto reinicio ocurre y la prueba cae. `pass.txt` es el `close_check` y la suite completa. `e2e.txt` es el simulacro contra el motor vivo, las filas de `bb status` y `bb drift`.
