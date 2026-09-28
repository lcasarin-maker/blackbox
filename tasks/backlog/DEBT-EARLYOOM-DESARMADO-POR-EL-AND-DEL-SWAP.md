---
id: DEBT-EARLYOOM-DESARMADO-POR-EL-AND-DEL-SWAP
kind: debt
title: "earlyoom no dispara con la RAM al 0.19% porque el swap libre bloquea su AND"
status: open
severity: P1
origin: measured
satd_family: MISSING_INSTRUMENT
created: 2026-09-28
close_check: {"cmd": "grep -qE \"^EARLYOOM_ARGS=.*-s 100,100\" /etc/default/earlyoom", "expect": "exit_zero", "porque": "la compuerta vive en el fichero desplegado, no en el repo; el cierre exige que el SIGKILL tambien quede abierto (-s 100 a secas lo deja en 50%)."}
evidence: {"medicion": "tasks/evidence/DEBT-EARLYOOM-DESARMADO-POR-EL-AND-DEL-SWAP/medicion-2026-09-28.txt"}
---

# Technical Debt: earlyoom desarmado por el AND del swap

## Finding

El 2026-09-28 a las 11:28:27 el OOM killer del kernel mato el renderer de
`claude-desktop` (PID 137261, SIGTRAP, core truncado de 166.1M) y el usuario
perdio la interfaz grafica. `earlyoom` estaba vivo, con `--avoid
'(claude-desktop|...)'` puesto, y **no disparo ni una vez**: 0 kills en 744
lineas de journal ese dia.

No fue el umbral de memoria. `MemAvailable` llego a **0.19%**, muy por debajo
del 10% configurado. Lo que lo bloqueo fue que la condicion de earlyoom es
**AND**, y el swap se quedo al 65% libre:

```
-s PERCENT[,KILL_PERCENT] ...
     Note: both memory and swap must be below minimum for earlyoom to act.
```

## Por que esto no es el ciego ya declarado

`bb status` declara: *"CIEGO earlyoom ante agotamiento de memoria unificada --
su umbral lee MemAvailable, que marco 56% durante los congelamientos del
2026-09-22/23"*. Ese ciego es que el instrumento LEE mal la magnitud.

Aqui el instrumento leyo bien: 0.19%, exacto. Lo que fallo es la **compuerta
del swap**, que es un defecto distinto y no esta declarado en ninguna parte.
Los dos regimenes son opuestos y hay que separarlos: el 22/23 MemAvailable
mentia con swap a cero; el 28 MemAvailable decia la verdad con swap al 65%.

`enable-privileged.sh:357` declara el limite como *"esto corrige la punteria,
NO el umbral (...) Quien cubre eso es bb-usable, no earlyoom"*. bb-usable no lo
cubrio tampoco, por un motivo propio -- ver
`DEBT-BB-USABLE-NUNCA-MIDIO-SU-PROPIA-LATENCIA`.

## Por que el --avoid no salvo al escritorio

Porque earlyoom nunca llego a elegir victima. Cuando el AND no se cumple, el
que actua es el kernel, y el kernel no lee `--avoid`: lee `oom_score_adj`. En
la tabla del OOM killer el renderer llevaba **300**, el valor mas alto de toda
la lista (los demas `claude-desktop` en 100/200, `earlyoom` en -1000). Chromium
marca sus renderers como victima preferida a proposito.

Un `--avoid` solo protege mientras earlyoom siga siendo quien mata. En cuanto
el AND lo desarma, la lista de protegidos no vale nada.

## Como se cierra

`-s 100,100` en `EARLYOOM_ARGS`, y no `-s 100` a secas. Medido: `-s 100` deja
`SIGKILL when mem <= 5.00% and swap <= 50.00%`, y durante el evento el swap
estaba al 65% -- por encima de ese 50%. Con `-s 100` habria habido SIGTERM y
nunca SIGKILL.

```
sudo sed -i "s/-m 10 -s 10/-m 10 -s 100,100/" /etc/default/earlyoom
sudo systemctl restart earlyoom.service
```

La punteria NO hay que tocarla, y eso esta medido, no supuesto: con las dos
compuertas abiertas la victima seria `VLLM::EngineCor`, `oom_score` **1026**,
el mas alto de la maquina -- el consumidor real de 50 GB. `claude-desktop` va
en 866 y baja mas con `--avoid`. El `--prefer '(pytest|python3|triton)'` no
empareja `VLLM::EngineCor` y no le hace falta.

## Limite declarado

Esto abre la compuerta; NO prueba que el corte del 10% sea el correcto. El 10%
de 121 GB son 12 GB, y esta maquina paso de 1592 MiB a 234 MiB en 61 segundos
-- una sola muestra entre "hay margen" y "no hay". Si la caida es mas rapida
que el intervalo de sondeo de earlyoom, la compuerta abierta llega tarde igual.
Ese numero no se midio aqui.

Tampoco se midio el coste del lado contrario: con el swap fuera de la ecuacion,
earlyoom pasa a poder matar en cualquier episodio de RAM baja con swap sano, y
en esta caja eso incluye las rafagas normales de vLLM. No hay cuenta de cuantas
veces al dia habria disparado retroactivamente sobre el corpus de muestras.

## Progreso -- correccion de registro (2026-09-28)

El commit `d3d7980` puso el arreglo (`sed` en `enable-privileged.sh`) en
presente ("earlyoom deja de ser un AND ciego"), pero eso describe el
INSTALADOR, no la maquina. Una sesion par lo midio en vivo, minutos despues:

```
$ grep -o 'EARLYOOM_ARGS=.*' /etc/default/earlyoom
EARLYOOM_ARGS="-r 60 -m 10 -s 10 --avoid '(...)' --prefer '(pytest|python3|triton)'"
$ systemctl show earlyoom -p ActiveEnterTimestamp
ActiveEnterTimestamp=Mon 2026-09-28 04:29:31 CST
```

Sigue en `-s 10`, con el demonio vivo desde ANTES del incidente de las 11:28
y nunca reiniciado. El arreglo esta escrito y probado sobre una copia (ver
mas arriba), pero **no aplicado**: falta `sudo ./enable-privileged.sh`, que
necesita la contrasena de Luis. El close_check ya elegido
(`grep -qE "^EARLYOOM_ARGS=.*-s 100,100" /etc/default/earlyoom`) mide
justo esto -- el sujeto, no el repo -- por eso sigue en `status: open`.

Es la misma familia de error que `tools/config_entregable.sh` ya documenta:
editar `adopted/` (o aqui, el instalador) y asumir que correr el script
alguna vez basta, sin verificar que se corrio DESPUES del cambio.
