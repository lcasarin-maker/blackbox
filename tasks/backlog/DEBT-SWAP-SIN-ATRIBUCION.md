---
id: DEBT-SWAP-SIN-ATRIBUCION
kind: debt
title: "`swap.in_pag_s` cuenta paginas que vuelven del disco, no dice quien las trae"
status: open
severity: P2
origin: asserted
satd_family: MISSING_INSTRUMENT
created: 2026-09-25
close_check: {"cmd": "python3 -m pytest tests/test_bb_bash.py -k swap_por_proceso -q", "expect": "exit_zero"}
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
