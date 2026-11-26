---
id: FEATURE-RELOJ-PRUEBA-GUARDA-GPU-OCUPADA-01
kind: task
domain: GPU
title: "bb reloj --prueba: no emitir veredicto si otros procesos usan la GPU"
status: done
closed_at: 2026-10-26
closure_type: fixed
closure_reason: "prueba() consulta los procesos de computo con _APPS_CMD/parse_apps/_docker_runner de verifica_proveedor_gpu antes de cargar (ajenos => no carga) y al final de la carga; ajenos => INDETERMINADO/GPU_OCUPADA con pid, nombre y MiB; pid propio excluido; consulta fallida o ilegible => NOT_COLLECTED, nunca libre. El temporizador de arranque registra la fila GPU_OCUPADA sin avisar ni reintentar (declarado). Tests en rojo contra el codigo viejo y contra dos mutantes."
evidence:
  fail: tasks/evidence/FEATURE-RELOJ-PRUEBA-GUARDA-GPU-OCUPADA-01/fail.txt
  pass: tasks/evidence/FEATURE-RELOJ-PRUEBA-GUARDA-GPU-OCUPADA-01/pass.txt
severity: P3
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-10-26
close_check: {"cmd": "python3 -m pytest -q tests/test_reloj_atascado.py -k \"ocupada\"", "expect": "exit_zero", "porque": "Especificacion pendiente, no prueba existente: exige caso GPU ocupada => INDETERMINADO con motivo GPU_OCUPADA y caso GPU libre => veredicto normal."}
---

## Origen

Script `gb10_clockcheck.py` del post [387029](https://forums.developer.nvidia.com/t/387029/1): si
`nvidia-smi --query-compute-apps` lista procesos ajenos, la corrida se declara "NOT VALID". El post advierte que una GPU
ocupada da un puntaje falsamente bajo.

## Hueco

`prueba()` en `tools/reloj_atascado.py` mide TFLOP/s con la GPU compartida sin consultar quien mas la usa. Con un motor de
modelos activo el numero baja por competencia, no por el estado de energia, y la salida no lo distingue.

## Alcance

Reutilizar `_APPS_CMD` de `tools/verifica_proveedor_gpu.py:26` (no copiar el codigo del script de Anantus). Antes y durante
la prueba, si hay procesos de computo que no son el propio: `INDETERMINADO`, motivo `GPU_OCUPADA`, con la lista de pid y
nombre. Excluir el pid propio de la lista. Sin consulta posible (`nvidia-smi` falla): `NOT_COLLECTED`, nunca "libre".

## Control negativo exigido

GPU libre => el veredicto de siempre; GPU ocupada => `INDETERMINADO`; consulta que falla => `NOT_COLLECTED`. Un test sin el
caso ocupado no cierra la ficha.

## Limite

El temporizador de arranque corre seis minutos despues del boot: si el motor ya arranco, la prueba saldra `GPU_OCUPADA` y el
detector de arranque quedara ciego en ese boot. La ficha debe decidir y declarar que hace el temporizador en ese caso
(reintentar o registrar `NOT_COLLECTED`), no ocultarlo.

## Cerrada 2026-10-26
`tools/reloj_atascado.py`: `ocupantes(runner, propio, proc)` corre `vpg._APPS_CMD` con `vpg._docker_runner` y lo parsea con
`vpg.parse_apps` (`tools/verifica_proveedor_gpu.py`, importado, no copiado). Devuelve la lista de ajenos
(`pid`, `nombre` de `/proc/<pid>/comm` o None si no se puede leer, `mib`) sin el pid propio, o None si la consulta sale con
rc != 0 o con una linea malformada. `prueba()` la llama ANTES de importar torch y reservar tensores: con ajenos no carga la
GPU y sale `INDETERMINADO`, motivo `GPU_OCUPADA: pid ... (nombre, MiB)`, campo `ocupantes`; con None sale
`NOT_COLLECTED`. La llama otra vez al final de la carga, con los tensores vivos: ajenos => mismo `GPU_OCUPADA` conservando las
cifras medidas; None => `NOT_COLLECTED`.

Decision sobre el temporizador de arranque: registrar, no reintentar. `arranque()` guarda la fila tal cual
(`estado: INDETERMINADO`, motivo `GPU_OCUPADA`, `ocupantes` en `evento_arranque`) y no avisa. Reintentar no sirve: el motor de
modelos no se va solo y un reintento competiria con el. Consecuencia declarada en el docstring de `prueba()`: con el motor
arriba a los 6 min del boot, el detector de arranque queda ciego en ese boot y la fila lo dice.

Limite: son dos consultas puntuales; un proceso que entre y salga entre ellas no se ve.

Tests: `test_ocupada_consulta_reutiliza_apps_cmd_y_excluye_el_pid_propio`, `test_ocupada_consulta_que_falla_o_ilegible_es_none_nunca_libre`,
`test_ocupada_antes_de_la_prueba_da_indeterminado_sin_cargar_la_gpu`, `test_ocupada_durante_la_prueba_anula_el_veredicto`,
`test_ocupada_control_negativo_gpu_libre_da_el_veredicto_de_siempre`, `test_ocupada_consulta_que_falla_es_not_collected_sin_cargar`,
`test_ocupada_en_el_arranque_registra_sin_avisar`. El helper `_prepara_prueba` inyecta ahora la consulta (por defecto GPU
libre), para que los tests de `prueba()` sigan sin tocar el `nvidia-smi` real.
