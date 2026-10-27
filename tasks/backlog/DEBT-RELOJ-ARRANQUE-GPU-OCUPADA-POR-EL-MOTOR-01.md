---
id: DEBT-RELOJ-ARRANQUE-GPU-OCUPADA-POR-EL-MOTOR-01
kind: task
domain: GPU
title: "bb reloj --arranque: la guarda de GPU ocupada puede dejar ciego el detector de arranque si el motor arranca antes"
status: open
severity: P2
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-10-26
close_check: {"cmd": "python3 -c \"import json,os,sys;f=os.path.expanduser('~/.local/share/blackbox/interruptores/reloj_arranque.jsonl');r=[json.loads(l) for l in open(f) if l.strip()];r=[x for x in r if x['ts']>'2026-10-27T01:30'];sys.exit(0 if r and 'GPU_OCUPADA' not in str(r[-1].get('motivo')) else 1)\"", "expect": "exit_zero", "porque": "Especificacion pendiente: exige una fila posterior al merge de la guarda (2026-10-27T01:30Z) cuyo motivo no sea GPU_OCUPADA. Hoy no hay filas posteriores, asi que falla (control negativo)."}
---

## Origen

La ola 1 (`455cb237`) hizo que `prueba()` de `tools/reloj_atascado.py` consulte `--query-compute-apps` antes de cargar la GPU: con
procesos ajenos devuelve `INDETERMINADO` con motivo `GPU_OCUPADA` y no mide. El agente lo declaro en el docstring: "el detector de
arranque queda ciego en ese boot". El orquestador lo acepto sin medir su efecto en esta maquina.

## Por que importa aqui

`bb-reloj-arranque.timer` (habilitado, interruptor `reloj_arranque` en `observar`) corre `bb reloj --arranque` unos 6 minutos tras
el arranque. El motor vLLM (contenedor `nemotron-server`) arranca solo con la maquina. Si el motor ya ocupa la GPU a los 6 minutos,
cada arranque registra `GPU_OCUPADA` y el detector que existe para no tardar 8 horas en notar un reloj atascado no mide nada.
Antes del cambio la prueba corria con el motor presente y juzgaba por reloj. No esta medido el orden real motor/temporizador en
esta unidad.

## Alcance

1. Medir en el proximo arranque: hora de inicio del motor frente a la hora de la fila de `reloj_arranque.jsonl` (comandos en el
   reporte del 2026-10-26: `systemctl --user list-timers bb-reloj-arranque.timer`, `docker inspect -f '{{.State.StartedAt}}' nemotron-server`).
2. Si la fila sale `GPU_OCUPADA`: con la GPU ocupada por el motor, juzgar por el reloj y la potencia observados durante la carga
   propia del motor (camino pasivo de `decide()` sobre la telemetria) en vez de abandonar; los TFLOP/s se marcan no validos.
3. Conservar la guarda para los TFLOP/s: la ocupacion invalida el rendimiento, no el reloj.

## Control negativo exigido

Arranque con motor ya activo => la fila trae un veredicto por reloj (no GPU_OCUPADA) y `tflops` marcado no valido; GPU libre =>
el comportamiento de hoy; un reloj atascado con el motor activo (fixture) => ATASCADO.

## Medido en el arranque del 2026-10-26 (boot 56a1942a): el detector quedo ciego

`bb-reloj-arranque.timer` disparo a las 20:04:46 (6 min tras el boot de las 19:58:45). Fila nueva de `reloj_arranque.jsonl`:
`"estado": "INDETERMINADO", "reloj_mediano_mhz": null, "tflops": null, "motivo": "GPU_OCUPADA: pid 3382 (python3, 4522 MiB)..."`. El
servicio termino con `status=2/INVALIDARGUMENT` y systemd lo marco `Failed`. El ocupante fue el uvicorn de Atlas (pid 3382, 4.5 GiB),
no el contenedor del motor; el motor (`nemotron-server`, StartedAt 02:00:44Z, 2 min tras el boot) ya estaba cargado. Tres procesos
figuraban en `nvidia-smi --query-compute-apps` en ese momento y la guarda listo uno.
Consecuencia: cualquier proceso residente en la GPU a los 6 minutos anula la prueba del arranque. Con motor y Atlas arrancando solos,
eso ocurre en cada boot. El `close_check` falla hoy (rc=1), como corresponde.
Direccion de arreglo: la ocupacion invalida los TFLOP/s, no el reloj. En el arranque, correr la carga igualmente, juzgar por reloj y
potencia observados durante ella, marcar `tflops` no valido, y que `INDETERMINADO` por GPU_OCUPADA deje de ser un fallo de unidad.
