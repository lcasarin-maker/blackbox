---
id: DEBT-TECHOS-SIN-CALIBRAR
kind: debt
title: Los techos declarados suman 125G en una maquina de 121.1G -- no componen
status: open
severity: P1
origin: asserted
satd_family: UNCALIBRATED_THRESHOLD
created: 2026-09-24
close_check: {"cmd": "python3 -m tools.presupuesto_memoria --check", "expect": "exit_zero"}
---

## Que pasa

No es que los numeros sean flojos: es que **no caben**. Medido hoy en ATOM,
`MemTotal = 121.1 GiB`:

| techo declarado | valor | de donde salio |
|---|---|---|
| `app.slice` `MemoryMax` | 48G | criterio, "holgado sobre el uso observado" |
| `app.slice` `MemorySwapMax` | 4G | criterio |
| `nemotron-server --memory` | 75G | preexistente, no de este repo |
| `atlas-pgvector --memory` | 2G | preexistente |
| **suma** | **125G** | **contra 121.1 GiB de maquina** |

Y eso ignorando los tres contenedores sin techo, el resto de `system.slice`
(19.5 GiB en uso) y el kernel. Si cada dueno reclamara lo suyo, la maquina se
agota con todos los techos respetados. Un conjunto de techos que no compone no
es una proteccion: es aritmetica que nadie hizo.

Los picos reales estan lejos, y ese es el otro lado del problema:

```
app.slice        current 32.3 GiB   peak 35.5 GiB   max 48G
system.slice     current 19.5 GiB   peak 20.5 GiB   max = max
nemotron-server  current  9.9 GiB   peak 10.0 GiB   max 75G
```

Pico agregado observado ~55 GiB sobre 121.1. Hay sitio de sobra; lo que falta
es repartirlo.

Contraste deliberado: el umbral de PSI **si** esta calibrado contra los cuatro
incidentes y sus controles sanos (`tools/calibra_psi.py`, `VEREDICTO: CALIBRADO`).
Aqui se sabe como se hace y no se hizo.

## Como se cierra

1. `tools/presupuesto_memoria.py`, con la forma de `tools/calibra_psi.py`:
   lee `MemTotal`, lee los techos declarados de cada slice y contenedor, y
   **falla si la suma excede el presupuesto** -- descontando la reserva para la
   memoria unificada de GPU, que ningun cgroup ve.
2. Fijar esa reserva con medida, no a ojo: cuanto reserva de verdad el vLLM en
   memoria unificada (`nvidia-smi`, no el cgroup).
3. Reescribir los techos con los numeros que salgan, y que el gate de (1) los
   defienda.
4. Control negativo obligatorio: el gate tiene que FALLAR con el reparto de hoy
   (125G sobre 121.1). Si pasa, no mide.

## Limite declarado

Hasta que esto cierre, los 48G de `app.slice` no son un tope calibrado: son un
tope que existe. Que exista ya cambia el desenlace -- mata un proceso en vez de
congelar la maquina entera -- y eso es mas que nada. No se puede afirmar que sea
el tope correcto, y esta ficha existe para que esa afirmacion no se cuele.
