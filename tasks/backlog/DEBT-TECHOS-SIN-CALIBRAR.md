---
id: DEBT-TECHOS-SIN-CALIBRAR
kind: debt
title: "Los techos declarados suman 168.3 GiB en una maquina de 121.1: el hueco es la memoria unificada que ningun cgroup ve"
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

## Pasos 1, 2 y 4: HECHOS el 2026-09-25

**(1) El gate existe**: `tools/presupuesto_memoria.py`, ocho tests. Lee
`MemTotal`, los techos de cada slice desde la maquina, y la reserva de GPU.

**(4) El control negativo se cumple**: falla con el reparto de hoy, y tambien
pasa cuando los techos caben -- las dos direcciones tienen test, porque un
presupuesto que siempre cuadra no es un presupuesto.

```
MemTotal                                    121.1 GiB
reserva de GPU (ningun cgroup la ve)         86.0 GiB
  app.slice (escritorio y arneses)           48.0 GiB   (usa 30.8)
  docker.slice (contenedores)                32.0 GiB   (usa 11.0)
  system.slice                             SIN TECHO    (usa 2.3, y eso es una observacion)
SUMA declarada                              168.3 GiB   -- 47.2 de mas
```

**(2) La reserva se fijo con medida, y la medida desmintio lo esperado.**

Era tentador presupuestar contra lo que el vLLM declara:
`--gpu-memory-utilization 0.3`, que sobre 121.1 GiB son 36.3. Los picos DIARIOS
de memoria unificada, sacados de las muestras que bb ya guardaba, lo superan
**todos los dias**:

```
09-10  70.3   09-13  53.3   09-16  50.2   09-19  49.1   09-22  57.4
09-11  53.5   09-14  54.8   09-17  49.5   09-20  66.6   09-23  38.0  <- el minimo
09-12  74.2   09-15  50.1   09-18  49.1   09-21  85.4   09-24  67.0
```

## EL HALLAZGO: el techo que falta no es el del vLLM

El pico de 85.4 GiB del 2026-09-21T00:33, abierto:

```
  34363 MiB = 33.6 GiB   docker-86305327...        <- vLLM, coherente con su 0.3
   9761 MiB =  9.5 GiB   cov-solo.scope
   7959 MiB =  7.8 GiB   cov-solo.scope
   5715 MiB =  5.6 GiB   cov-solo.scope
   5703 MiB =  5.6 GiB   cov-solo.scope
   5431 MiB =  5.3 GiB   cov-solo.scope
   4815 MiB =  4.7 GiB   cov-solo.scope
   4631 MiB =  4.5 GiB   cov-solo.scope
   4587 MiB =  4.5 GiB   cov-solo.scope           <- OCHO, 48 GiB entre todos
   4522 MiB =  4.4 GiB   atlas-api.service
  mem_avail en esa muestra: 0.2 GB   load1: 18.38
```

**El vLLM se porto.** Lo que no tiene techo es el abanico: ocho procesos de GPU
simultaneos de un `cov-solo.scope` -- que no existe en este repo ni en el kit,
viene de fuera-- llevandose 48 GiB de memoria unificada que **ningun cgroup ve**
(medido aqui: 7 GiB de CUDA se contabilizan como 15 MiB).

Los techos de 48G y 32G se pusieron como si esa memoria no existiera.

## La decision se tomo el 2026-09-25: VIGILAR, no cuadrar a la fuerza

Boleta con las cuatro salidas y su coste. Elegida: **que bb vigile el agregado
de GPU y se apriete lo que sale gratis**. Las otras tres, con lo que las
descarto:

- **Bajar los techos al peor caso** -- DESCARTADA POR MEDICION, no por juicio.
  Con la reserva de 86 GiB quedan 31.1 para `app.slice` y `docker.slice`
  juntos, y `app.slice` SOLO pico 39.8 GiB hoy. Garantizaria el invariante
  matando trabajo en operacion normal, no solo en el pico.
- **Acotar el abanico donde se lanza** -- es la solucion de fondo y hace cuadrar
  la aritmetica (con el abanico en ~40 quedan 77.1 para app+docker y 48+29
  cabe), pero el codigo que lanza esos procesos no esta en blackbox.
- **void_wontfix** -- se descarto por ahora: el desborde es real y medible.

## Lo que se hizo, y el numero que lo valida

**`docker.slice` baja de 32G a 16G.** Su pico agregado es 11.2 GiB, asi que el
recorte no tiene coste observado. Pero no es margen: es lo que hace usable la
alarma. El presupuesto que le queda a la GPU es `MemTotal - techos`:

```
con docker.slice=32G  ->  37.1 GiB  ->  se supera el 75.4 % del tiempo   (ruido)
con docker.slice=16G  ->  53.1 GiB  ->  se supera el  0.9 % del tiempo   (senal)

serie observada: 18 944 muestras, mediana 49.0 GiB, p90 50.1, maximo 85.4
```

El corte de 53.1 **no se eligio: se resta**. Que caiga justo por encima del p90
del estado estacionario es lo que valida el reparto -- el presupuesto derivado
y la conducta observada coinciden, y eso no estaba puesto a mano.

**`tools/presupuesto_memoria.py` calcula ese umbral y cuenta las excursiones**,
con las tres ultimas fechadas: un porcentaje sin fechas no sirve para
diagnosticar. `bb scan` lo muestra como vista de operacion; la aritmetica vive
en un solo sitio.

Y el fichero de `docker.slice` traia una holgura declarada que era FALSA:
"dejando 41 GiB para el kernel, el resto de system.slice y la memoria unificada
de GPU". La memoria unificada sola tiene mediana 49.0 y maximo 85.4. Nunca cupo.

## Por que sigue ABIERTA

Porque vigilar no es cuadrar. El `close_check` sigue siendo
`presupuesto_memoria --check`, que exige que la suma quepa, y hoy da
**167.7 GiB sobre 121.1**. Lo elegido hace el desborde VISIBLE; no lo impide.

Lo que falta para cerrarla de verdad es acotar el abanico, y eso vive fuera de
este repo. Mientras tanto:

- bb no puede impedirlo -- no intercepta la creacion de procesos, y un cgroup
  no ve la memoria unificada, asi que no hay techo que aplicar desde aqui;
- el recorte de `docker.slice` necesita `sudo ./enable-privileged.sh` para
  llegar a la maquina. Hasta entonces `bb drift` lo marca DIVERGENTE y el
  umbral real sigue siendo 39.6, no 53.

## Limite declarado

El presupuesto resta el USO de los slices sin techo (`system.slice`), no un
compromiso, porque no lo tienen. El umbral se mueve con ellos, y eso se imprime
en cada corrida en vez de disimularse.
## Limite declarado

Hasta que esto cierre, los 48G de `app.slice` no son un tope calibrado: son un
tope que existe. Que exista ya cambia el desenlace -- mata un proceso en vez de
congelar la maquina entera -- y eso es mas que nada. No se puede afirmar que sea
el tope correcto, y esta ficha existe para que esa afirmacion no se cuele.
