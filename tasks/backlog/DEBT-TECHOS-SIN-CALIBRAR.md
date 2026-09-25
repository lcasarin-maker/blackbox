---
id: DEBT-TECHOS-SIN-CALIBRAR
kind: debt
title: Los techos de memoria (48G/4G/16G) son generosos, no medidos
status: open
severity: P2
origin: asserted
satd_family: UNCALIBRATED_THRESHOLD
created: 2026-09-24
close_check: {"cmd": "python3 -m tools.calibra_techos --check", "expect": "exit_zero"}
---

## Que pasa

Los tres numeros que gobiernan los techos instalados el 2026-09-24 se
escogieron por criterio, no por medicion:

| numero | donde | de donde salio |
|---|---|---|
| `MemoryMax=48G` | `app.slice` | "holgado sobre el uso normal observado a ojo" |
| `MemorySwapMax=4G` | `app.slice` | "que pueda sudar un poco sin thrashear" |
| `16G` | techo sugerido para Antigravity | punto de partida, sin una sola muestra |

Ninguno tiene detras una serie de uso real. Un techo demasiado alto no corta a
tiempo y no protege; uno demasiado bajo mata a Atom en pleno trabajo, que es
precisamente lo que Luis pidio evitar ("quiero abrir simultaneamente
antigravity y ya estoy hasta los huevos que se caiga la atom").

Esto contrasta con el umbral de PSI, que **si** esta calibrado contra los
cuatro incidentes y sus controles sanos (`tools/calibra_psi.py`,
`VEREDICTO: CALIBRADO`). El contraste es el punto: aqui se sabe como se hace y
no se hizo.

## Como se cierra

1. Recolectar dias de uso real. `bb` ya muestrea; falta persistir la serie por
   slice (`systemd-cgtop`/`memory.peak` de cada cgroup) en `logs/`.
2. Escribir `tools/calibra_techos.py` con la misma forma que
   `tools/calibra_psi.py`: propone un corte y **corre el control negativo** --
   que el corte propuesto habria matado a los procesos en las sesiones sanas.
   Un techo que no puede salir "mal calibrado" no esta calibrado.
3. Actualizar el drop-in con los numeros que salgan, no con los actuales.

## Limite declarado

Hasta que esto cierre, los 48G no son una proteccion medida: son un tope que
existe. Que exista ya cambia el desenlace (mata un proceso en vez de congelar
la maquina), y eso es mas que nada -- pero no se puede afirmar que sea el tope
correcto, y esta ficha existe para no dejar que esa afirmacion se cuele.
