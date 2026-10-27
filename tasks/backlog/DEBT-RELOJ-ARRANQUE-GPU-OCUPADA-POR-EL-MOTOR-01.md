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
close_check: {"cmd": "bid=$(cat /proc/sys/kernel/random/boot_id); f=$HOME/.local/share/blackbox/interruptores/reloj_arranque.jsonl; grep \"$bid\" \"$f\" | tail -n 1 | grep -v GPU_OCUPADA | grep -q .", "expect": "exit_zero", "porque": "Especificacion pendiente: pasa solo si la fila del arranque actual existe y su estado no es GPU_OCUPADA. Hoy no hay fila del arranque posterior al cambio."}
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
