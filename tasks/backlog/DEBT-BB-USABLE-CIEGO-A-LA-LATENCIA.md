---
id: DEBT-BB-USABLE-CIEGO-A-LA-LATENCIA
kind: debt
title: "bb-usable pregunta si la maquina sirve MEMORIA, no si el escritorio responde"
status: open
severity: P2
origin: asserted
satd_family: MISSING_INSTRUMENT
created: 2026-09-25
close_check: {"cmd": "python3 -m pytest tests/test_bb_usable.py -k latencia_del_escritorio -q", "expect": "exit_zero"}
---

## Que pasa

`bb-usable` nacio para contestar "si la maquina SIRVE" en vez de "si systemd
sigue vivo", y lo hace por dos caminos, los dos de MEMORIA: una sonda que pide
64 MiB y los toca, y PSI `memory.full` sostenida.

El 2026-09-25 la maquina fue inusable para teclear durante horas con
`psi.mem_full` en 0.00 casi todo el rato. `bb-usable` vio una maquina sana, y
por su propia definicion tenia razon. La pregunta que no sabe hacer es la que
hizo el dueno: **si el escritorio responde**.

Desde este release esa magnitud existe y se esta registrando: `latencia_x` en
cada muestra (4-7 ms sano en esta maquina, con controles negativos para
TIMEOUT, ERROR y AUSENTE). `bb-usable` no la lee.

## Por que no se conecto de una vez, que es la parte importante

Porque `bb-usable` no informa: **actua**. Su unit lleva
`FailureAction=reboot-immediate`. Enchufarle un canal nuevo sin calibrar
significa darle permiso para reiniciar la maquina por un umbral que nadie ha
validado contra un incidente propio -- que es exactamente el error que su
propio encabezado documenta haber cometido ya una vez con la sonda de 64 MiB.

El corte de memoria (UMBRAL=10, SOSTENIDO=5 min) esta calibrado contra cuatro
congelamientos con sus controles sanos. Para la latencia del escritorio hay
**una sola medida sana** (4-7 ms) y **cero episodios malos registrados**. Con
n=0 del lado positivo no hay calibracion posible.

## Como se cierra

Por pasos, y el primero NO es actuar:

1. Acumular linea base de `x.ms` en operacion normal y bajo carga -- ya hay un
   punto: con 40 quemadores sobre 20 nucleos sube a 8 ms, peor caso 13 ms.
2. Capturar al menos un episodio malo real (lo espera
   `DEBT-SLUGGISH-SIN-CAUSA-PROBADA`).
3. Solo entonces derivar un corte, y que `bb-usable` AVISE con el antes de que
   se le permita actuar.

Lo que NO cierra esto: darle un umbral inventado hoy. Un vigilante que actua
sobre un numero sin calibrar es peor que no tenerlo, porque reinicia la
maquina y ademas afirma haber tenido razon.
