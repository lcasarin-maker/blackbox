---
id: DEBT-SWAP-SIN-ATRIBUCION
kind: debt
title: "`swap.in_pag_s` cuenta paginas que vuelven del disco, no dice quien las trae"
status: done
severity: P2
origin: asserted
satd_family: MISSING_INSTRUMENT
created: 2026-09-25
closed_at: 2026-09-25
close_check: {"cmd": "python3 -m pytest tests/test_bb_bash.py -k swap_por_proceso -q", "expect": "exit_zero"}
evidence: {"pass": "tasks/evidence/DEBT-SWAP-SIN-ATRIBUCION/pass.txt", "fail": "tasks/evidence/DEBT-SWAP-SIN-ATRIBUCION/fail.txt", "e2e": "tasks/evidence/DEBT-SWAP-SIN-ATRIBUCION/e2e.txt"}
reason: "El coste que esta ficha daba como motivo para no hacerlo era el de la implementacion ingenua, no el del dato: un awk por proceso cuesta 0.78 s y una sola pasada sobre el glob cuesta 0.01 s. La muestra sigue durando 0.30 s."
---

## Que pasa

La muestra ya lleva `swap.{free_kb,total_kb,in_pag_s,out_pag_s}`, anadido el
2026-09-25 porque esa noche el swap fue la unica magnitud que se movio en una
sola direccion: 16383 MiB libres a las 20:51, 12067 a las 03:28 -- 4.3 GB
expulsados y nunca recuperados, con el 53 % de la RAM libre. El numero hubo
que sacarlo del log de earlyoom porque bb no lo registraba.

Ahora lo registra, y sigue siendo un TOTAL. Dice cuantas paginas vuelven del
disco por segundo; no dice de quien. Es exactamente el defecto que tenian
`Committed_AS` antes de `pidio` y `cpu_some` antes de `cpu_top`: un contador
agregado no nombra a nadie, y el trabajo de diagnostico empieza por el nombre.

## Por que no se hizo ya

Porque el coste no esta medido. La atribucion exige leer `VmSwap` de
`/proc/<pid>/status` de los ~500 procesos de esta caja en cada muestra, y eso
es un `open` + parse por proceso. La muestra completa corre cada minuto con
`Nice=19` e `IOSchedulingClass=idle` precisamente para no competir con lo que
vigila; anadir medio millar de lecturas sin haberlas cronometrado seria meter
carga en el instrumento que mide la carga.

`pidio` y `cpu_top` se libraron de esto porque `ps -eo` ya trae VmSize y
tiempo de CPU en UNA llamada. Para `VmSwap` no hay columna de `ps`.

## Como se cierra

1. **Medir primero** cuanto cuesta el barrido: `/proc/*/status` de los procesos
   vivos, cronometrado en esta maquina, y contra el presupuesto de la muestra.
2. Si cabe, emitir `swap_top` con el mismo patron que `cpu_top`: los cinco de
   mayor `VmSwap`, con su unit de cgroup.
3. Si no cabe, emitirlo solo DENTRO de la rafaga, o solo cuando `in_pag_s`
   pase de un corte -- y decir por que en el propio codigo.

## Limite declarado

`VmSwap` es un NIVEL, no un ritmo: dice cuanta memoria de ese proceso esta
fuera, no cuanta esta trayendo de vuelta ahora. El delta entre muestras se
acerca, pero una pagina que sale y vuelve dentro del mismo intervalo es
invisible. La atribucion exacta del trafico de vuelta por proceso vive en
`/proc/<pid>/stat` (majflt), que cuenta fallos mayores y no solo swap.


## Root Cause

La ficha declaraba que la atribucion "exige leer VmSwap de ~500 procesos en
cada muestra" y que ese coste no estaba medido. Medirlo fue el arreglo:

```
un awk por proceso, 533 procesos ....... 0.72 / 0.77 / 0.78 s
UNA pasada de awk sobre el glob ........ 0.00 / 0.01 / 0.01 s
la muestra completa, antes ............. 0.31 s
la muestra completa, ahora ............. 0.30 s
```

El bucle habria triplicado la muestra. La pasada unica cuesta el 3 % y no se
nota. **El coste que impedia hacerlo era el de la implementacion que se
imagino, no el del dato**, y la ficha lo dio por medido sin medirlo.

Tambien era falsa la premisa de que `ps` no sirve como precedente: `pidio` y
`cpu_top` usan `ps -eo` porque ahi hay columna; para VmSwap no la hay, pero
`awk` sobre el glob de `/proc/*/status` es una sola invocacion igual.

## Regression Test

Tres tests en `tests/test_bb_bash.py` con un `/proc` plantado -- necesario
porque en esta maquina el swap esta al 100 % libre casi siempre, asi que un
campo que sale vacio no demuestra que sepa nombrar a nadie, y forzar swap de
verdad sobre 60 GB libres arriesga la maquina que se vigila. Mismo precedente
que `BB_VMSTAT`.

- nombra a los tres con swap, ordenados, con su unit de cgroup;
- un proceso con `VmSwap: 0` existe, se lee y NO aparece;
- sin nadie en swap la lista va vacia y no con una fila de relleno: una lista
  vacia dice "nadie", que es un hecho; una fila con ceros diria "este", que
  seria falso.

## Verification Evidence

```
swap.top:
   {'pid': 111, 'swap_kb': 9000000, 'comm': 'gordo',   'unit': 'prueba-gordo.scope'}
   {'pid': 444, 'swap_kb': 4000000, 'comm': 'mediano', 'unit': 'prueba-mediano.scope'}
   {'pid': 222, 'swap_kb':     512, 'comm': 'chico',   'unit': 'prueba-chico.scope'}
```

El de `VmSwap: 0` no esta. Coste de la muestra: 0.30 s.

## Limites declarados

- `VmSwap` es un NIVEL: cuanta memoria de ese proceso esta fuera, no cuanta
  esta trayendo de vuelta. Una pagina que sale y vuelve dentro del mismo
  intervalo es invisible aqui. El ritmo agregado sigue siendo `swap.in_pag_s`.
- El pid se saca del penultimo componente de la ruta, no de una posicion fija,
  para que la raiz sustituible de los tests no cambie lo que se mide.
