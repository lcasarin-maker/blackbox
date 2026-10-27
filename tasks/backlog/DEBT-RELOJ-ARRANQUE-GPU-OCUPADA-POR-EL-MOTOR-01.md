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

## Implementado, falta verificar en un arranque real

Commit `30aaa9fe` (rama del worktree `agent-a27a3dfb1203f896d`, sin aterrizar en master al escribir esto). Estado de la ficha:
`open`. El `close_check` exige una fila de un arranque real posterior a 2026-10-27T01:30Z y ningun agente la puede producir.

Lo que cambio en `tools/reloj_atascado.py`:
- `prueba()` con ocupantes (en la consulta de antes o en la de despues) corre la carga igual y decide SOLO por reloj y potencia
  (`decide()` sin `tflops`, el segundo eje no se aplica). Los TFLOP/s se miden y salen con `tflops_valido: false` y
  `tflops_motivo: "COMPETENCIA: pid ... en la GPU durante la carga; ..."`; `ocupantes` es la union por pid de las dos consultas.
- GPU libre: el veredicto de antes, segundo eje incluido, mas `tflops_valido: true`.
- La carga que falla (OOM de CUDA, sin torch, sin CUDA: cualquier excepcion de `_carga`) da `INDETERMINADO` con motivo
  `CARGA_NO_PUDO_CORRER: <Tipo>: <primera linea>; GPU ocupada por <lista>` o `; GPU libre`.
- Consulta de ocupantes fallida (antes o despues): `NOT_COLLECTED` como antes.
- `evento_arranque` escribe `tflops_valido` (y `tflops_motivo` cuando existe) en `reloj_arranque.jsonl`, junto a `ocupantes`.

Eleccion del codigo de salida (punto 3), nueva funcion pura `codigo(r, es_arranque)`: 0 sano, 1 atascado, 2 indeterminado, como
antes, con UNA excepcion solo en `--arranque`: `INDETERMINADO` con motivo `CARGA_NO_PUDO_CORRER` y `ocupantes` no vacio sale 0. Es
el entorno (motor y Atlas arrancan solos) y la fila ya lo registra; con 2 systemd marcaba `Failed` en cada boot. Siguen en 2 en
`--arranque`: `CARGA_NO_PUDO_CORRER` con la GPU libre (instrumento roto), `NOT_COLLECTED`, `THROTTLE_ACTIVO`, `RELOJ_EN_BANDA`,
`RELOJ_ALTO_RENDIMIENTO_BAJO`. `--prueba` a mano conserva el 2 para todo `INDETERMINADO`. Un `ATASCADO` sale 1 y avisa como antes.
No se toco la unidad (`SuccessExitStatus` habria exigido reinstalarla y ocultaria tambien los 2 del instrumento roto).

Limites declarados:
- El `close_check` acepta una fila `CARGA_NO_PUDO_CORRER` (su motivo no contiene `GPU_OCUPADA`) aunque esa fila tampoco midio el
  reloj. Quien lo lea tras el reinicio mira tambien `estado` y `reloj_mediano_mhz` (comando abajo).
- Un proceso que entre y salga entre las dos consultas no se ve; sus TFLOP/s contarian como validos.
- La fila de SPEC.md de `tools/reloj_atascado.py` dice "sale 0 sano, 1 atascado, 2 indeterminado" y no menciona la excepcion de
  `--arranque` ni `tflops_valido`; no se edito (invalida el ledger H1).

Evidencia (2026-10-26, worktree):

`close_check` antes de tocar nada:
```
$ python3 -c "...close_check de la ficha..."; echo "rc=$?"
rc=1
```
Ultima fila real: `"ts": "2026-10-27T02:04:46.825766+00:00", ... "estado": "INDETERMINADO", "motivo": "GPU_OCUPADA: pid 3382 (python3, 4522 MiB); ..."`.

Suite pedida, antes y despues:
```
$ python3 -m pytest -q tests/test_reloj_atascado.py tests/test_reloj_verificador_limites.py tests/test_incident_report.py tests/test_fan_rpm.py
antes (master 6b4d1442): 111 passed, 1 xfailed in 0.75s
despues (30aaa9fe):      120 passed, 1 xfailed in 0.75s
```

Control negativo: los tests nuevos y reescritos contra `tools/reloj_atascado.py` de master (`git show master:tools/reloj_atascado.py`
sobre el archivo, con el test nuevo; luego restaurado):
```
$ python3 -m pytest -q tests/test_reloj_atascado.py -k "motor_ or ocupada_antes_de_la_prueba_carga or ocupada_durante_la_prueba_invalida"
FAILED tests/test_reloj_atascado.py::test_ocupada_antes_de_la_prueba_carga_igual_y_juzga_por_reloj
FAILED tests/test_reloj_atascado.py::test_ocupada_durante_la_prueba_invalida_los_tflops_no_el_reloj
FAILED tests/test_reloj_atascado.py::test_motor_a_gpu_ocupada_y_reloj_sano_es_sano_con_tflops_no_valido
FAILED tests/test_reloj_atascado.py::test_motor_b_gpu_ocupada_y_reloj_atascado_es_atascado
FAILED tests/test_reloj_atascado.py::test_motor_b_control_negativo_ocupada_con_throttle_no_es_atascado
FAILED tests/test_reloj_atascado.py::test_motor_c_gpu_libre_conserva_el_segundo_eje
FAILED tests/test_reloj_atascado.py::test_motor_d_la_carga_no_puede_correr_es_indeterminado
FAILED tests/test_reloj_atascado.py::test_motor_e_consulta_que_falla_sigue_siendo_not_collected
FAILED tests/test_reloj_atascado.py::test_motor_codigo_de_salida_en_arranque
FAILED tests/test_reloj_atascado.py::test_motor_main_arranque_usa_el_codigo_de_arranque
FAILED tests/test_reloj_atascado.py::test_motor_la_fila_de_arranque_registra_ocupantes_y_tflops_valido
11 failed, 53 deselected in 0.36s
rc=1
```
Con el codigo nuevo los mismos 11 pasan (dentro de los 120). El test de la fila reproduce la condicion del `close_check` sobre un
archivo temporal: la fila real del 2026-10-27T02:04Z la hace fallar y la fila nueva (SANO, `tflops_valido: false`) la hace pasar.
Ninguna corrida de `bb reloj --prueba` ni `--arranque` se hizo sobre la maquina: motor (pid 100762, 30953 MiB) y Atlas (pid 3382,
4522 MiB) estaban en la GPU (`nvidia-smi --query-compute-apps`, solo lectura).

Tras el proximo reinicio (con este commit en master, que es lo que corre la unidad: `WorkingDirectory=%h/projects/blackbox`):
```
systemctl --user status bb-reloj-arranque.service --no-pager | head -5
tail -1 ~/.local/share/blackbox/interruptores/reloj_arranque.jsonl | python3 -m json.tool
python3 -c "import json,os,sys;f=os.path.expanduser('~/.local/share/blackbox/interruptores/reloj_arranque.jsonl');r=[json.loads(l) for l in open(f) if l.strip()];r=[x for x in r if x['ts']>'2026-10-27T01:30'];sys.exit(0 if r and 'GPU_OCUPADA' not in str(r[-1].get('motivo')) else 1)"; echo "rc=$?"
```
Se espera: unidad sin `Failed`, fila con `estado` SANO o ATASCADO, `reloj_mediano_mhz` numerico, `tflops_valido: false` y
`ocupantes` con el motor/Atlas, y `rc=0`. Si la fila sale `CARGA_NO_PUDO_CORRER`, el `rc=0` no basta: el reloj sigue sin medirse.
