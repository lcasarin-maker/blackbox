---
id: FEATURE-RELOJ-ATASCADO-SEGUNDO-EJE-TFLOPS-Y-GUARDA-DE-OCUPACION-01
kind: task
domain: GPU
title: "bb reloj: veredicto con un segundo eje (TFLOP/s y potencia); la guarda de GPU ocupada vive en FEATURE-RELOJ-PRUEBA-GUARDA-GPU-OCUPADA-01"
status: done
closed_at: 2026-10-26
closure_type: fixed
closure_reason: "decide() acepta tflops: mediana < 1400 MHz sin throttle y TFLOP/s < 60 => ATASCADO; prueba() le entrega sus TFLOP/s. Umbral 60 PROVISIONAL (de GX10, no de esta ATOM), declarado en el codigo y en la salida (umbral_tflops_estado). Remedio alineado con 387029. 1000/1400 MHz sin tocar. El close_check ya pasaba antes de tocar nada (selector debil); el control negativo real son los tests nuevos contra el codigo viejo y una mutacion del codigo nuevo, ambos en rojo."
evidence:
  fail: tasks/evidence/FEATURE-RELOJ-ATASCADO-SEGUNDO-EJE-TFLOPS-Y-GUARDA-DE-OCUPACION-01/fail.txt
  pass: tasks/evidence/FEATURE-RELOJ-ATASCADO-SEGUNDO-EJE-TFLOPS-Y-GUARDA-DE-OCUPACION-01/pass.txt
severity: P3
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-10-26
close_check: {"cmd": "python3 -m pytest -q tests/test_reloj_atascado.py -k \"test_tflops_\"", "expect": "exit_zero", "porque": "Especificacion pendiente, no prueba existente: exige caso positivo (reloj en la banda 1000-1400 MHz con TFLOP/s bajo = ATASCADO) y caso negativo (mismo reloj con TFLOP/s sano = no ATASCADO)."}
---

## Origen

Hilo [387029](https://forums.developer.nvidia.com/t/387029/1) (Anantus, 2026-10): script autonomo `gb10_clockcheck.py`
(matmul bf16 8192x8192, 45 s) que acredita a blackbox y al hilo 386060 como origen del detector. No existe un "clock
monitor" separado de Anantus: lo que el post llama detector es `bb reloj` (`tools/reloj_atascado.py`). El script va
pegado en el cuerpo del post (162 lineas, sin enlace de descarga). Leido completo el 2026-10-26 sobre el JSON crudo del
hilo; sus unicos imports son argparse, shutil, subprocess, sys, threading, time y torch, y no abre archivos.
`anantus.org` no aparece en 387029 ni en 386060 (grep: 0 y 0).

## Lo que bb ya cubre

Veredicto de tres estados por reloj mediano con carga y sin throttle (`ATASCADO` < 1000 MHz, `SANO` >= 1400 MHz, el
mismo corte de 1400 MHz que usa la herramienta del hilo), historial (`inicio`), prueba activa (`--prueba`), prueba de
arranque y remedio impreso. Cifras propias confirmadas en esta maquina el 2026-10-12: 663 MHz, 16 W, 23.5 TFLOPS.

## Huecos medidos contra el post

1. **Un solo eje.** `decide()` mira solo `sm_clk_mhz`. `prueba()` calcula `tflops` y `potencia_mediana_w` y el veredicto
   los ignora. El post usa TFLOP/s < 60 con reloj mediano < 1400 MHz y sin throttle como firma. Un reloj entre 1000 y
   1400 MHz hoy sale `INDETERMINADO`; con TFLOP/s bajo y potencia baja seria candidato a atascado.
2. **Sin guarda de GPU ocupada.** El post marca la corrida como no valida si `nvidia-smi --query-compute-apps` lista otros
   procesos. `prueba()` no consulta eso: con un servidor de modelos activo, los TFLOP/s salen bajos por competencia,
   no por el estado de potencia, y la salida no lo distingue.
3. **Cifras de referencia ausentes del repo.** Sano en GX10 (7 unidades): 88.8-93.7 TFLOP/s, 2275-2333 MHz, ~89-92 W.
   DGX Spark sano (1 unidad): ~77 TFLOP/s (chasis de menor potencia). Atascado (2 GX10): 42.5 TFLOP/s, 851 MHz, 20.7 W.
   Son reportes de un usuario sin verificar por NVIDIA. La unidad de este repo (AI TOP ATOM) tiene una lectura posterior
   al arreglo, no una linea base previa: 2080 MHz, 67 W, 77.4 TFLOPS (fp16, `bb reloj --prueba`, hilo 386060 post 1). Cae
   en la banda "OK, chasis de menor potencia" del script (60-80), sobre su corte de 60. Anantus la ve plausible para ATOM
   y dice que no puede confirmarlo sin una segunda ATOM. Ademas: "los relojes en reposo no diagnostican nada" (post 2).
4. **Remedio mas pobre que el del post.** El texto de `bb reloj` dice "esperar unos minutos". El post: minimo 5 min
   desconectado, desenchufar tambien los USB, reconectar en orden pared -> adaptador -> equipo, y algunas unidades
   necesitaron mas tiempo o no se recuperaron. Registrado como reporte, no como garantia.

## Alcance

- `decide()` acepta `tflops` opcional: reloj < 1400 MHz, sin throttle y TFLOP/s < umbral => ATASCADO; el umbral de TFLOP/s
  se declara PROVISIONAL (viene de GX10, no de ATOM) y se calibra con una corrida sana propia antes de fijarlo.
- Fuera de esta ficha, partida el 2026-10-26: guarda de GPU ocupada (`FEATURE-RELOJ-PRUEBA-GUARDA-GPU-OCUPADA-01`), motivos
  separados para bajo rendimiento con throttle (`FEATURE-RELOJ-VEREDICTO-BAJO-NO-ATASCADO-01`, depende de esta) y
  calentamiento previo a medir (`FEATURE-RELOJ-PRUEBA-CALENTAMIENTO-ANTES-DE-MEDIR-01`).
- Texto del remedio alineado con el post (5 min, USB, orden de reconexion), citando 387029.
- No ejecutar ningun ciclo de corriente ni alterar el reloj del host.

## Control negativo exigido

Caso positivo (reloj 1200 MHz, 40 TFLOP/s, sin throttle => ATASCADO) y caso negativo cercano (1200 MHz, 90 TFLOP/s =>
no ATASCADO). Sin corrida sana real en esta unidad el umbral queda provisional y se imprime asi.

## Cerrada 2026-10-26
`tools/reloj_atascado.py`: `decide(filas, minimas, tflops=None)`. Con `tflops` < `UMBRAL_TFLOPS` (60.0, estricto), mediana
< 1400 MHz y sin throttle => `ATASCADO`. Sin `tflops` (detector pasivo sobre la telemetria) el veredicto es el de antes.
`prueba()` calcula los TFLOP/s antes de decidir y se los pasa a `decide()`. Con `tflops` la salida lleva `umbral_tflops` y
`umbral_tflops_estado` = "PROVISIONAL: corte de GX10 (hilo 387029), sin linea base sana medida en esta ATOM"; el codigo lo
marca con `ponytail:` (techo y disparador: una corrida sana propia con la GPU libre o una segunda ATOM). No se invento una
linea base: la unica lectura propia (77.4 TFLOPS, 2080 MHz) es posterior al arreglo.
`REMEDIO`: 5 min minimo desconectado, tambien los USB, reconexion pared -> adaptador -> equipo, algunas unidades no se
recuperaron; cita 376039/376239/387029. `UMBRAL_ATASCADO_MHZ`/`UMBRAL_SANO_MHZ` sin tocar.

Tests (`tests/test_reloj_atascado.py`): `test_tflops_bajo_con_reloj_en_banda_y_sin_throttle_es_atascado` (1200 MHz, 40),
`test_tflops_control_negativo_mismo_reloj_con_tflops_sano_no_es_atascado` (1200 MHz, 90), `test_tflops_frontera_del_umbral_es_estricta`
(60.0 no, 59.9 si), `test_tflops_bajo_con_throttle_o_sin_carga_no_es_atascado`, `test_tflops_ausente_deja_los_tres_estados_de_hoy`,
`test_tflops_la_prueba_entrega_sus_tflops_a_decide` (con su negativo: mismas filas, umbral bajo => no ATASCADO),
`test_main_atascado_remedio_alineado_con_el_hilo_387029`.

Defecto del instrumento, declarado: el selector `-k "tflops"` ya casaba antes de tocar nada con
`test_prueba_con_falsos_mide_tflops_y_veredicto_atascado` y salia rc 0 sin la funcion. No se edito el close_check. El
control negativo que si puede salir en rojo esta en `fail.txt`: los tests nuevos contra el codigo de 3894bbc4 (7 fallan) y
el codigo nuevo con el segundo eje quitado por `sed` (3 fallan).

Limite: el umbral sigue sin calibrar en esta ATOM; hasta una corrida sana propia, un ATASCADO por el segundo eje (reloj
entre 1000 y 1400 MHz) descansa en una cifra de GX10.
