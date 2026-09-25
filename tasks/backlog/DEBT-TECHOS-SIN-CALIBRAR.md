---
id: DEBT-TECHOS-SIN-CALIBRAR
kind: debt
title: "El criterio de los techos no podia salir positivo: reservaba un transitorio de 4 min como si fuera un compromiso"
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

Esa `SUMA declarada` ya no se calcula asi, y el cambio no es de numeros: sumaba
un maximo observado junto a compromisos. Se deja como registro de lo que decia
el 2026-09-24. Lo que imprime hoy esta en la seccion del 2026-09-25.

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

> **Actualizado el 2026-09-25**: `cov-solo.scope` ya no es anonimo. Son ocho
> workers de `pytest-xdist` corriendo una suite de tests, y el episodio duro
> cuatro minutos. Ver la seccion "el criterio no podia salir positivo" mas
> abajo, que es la que manda sobre este parrafo.

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
  cabe), pero el codigo que lanza esos procesos no esta en blackbox. Sigue
  siendo cierto, y desde el 2026-09-25 tiene direccion: es el `-n` de una
  corrida de `pytest-xdist` de la suite de otro repo.
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

## 2026-09-25: el criterio no podia salir positivo, y eso se midio

Se abrio el pico del 2026-09-21T00:33 y los ocho procesos tienen nombre:

```
34363 MiB  pid 3302207  [No data]                                  <- vLLM
 9761 MiB  pid 3540458  [pytest-xdist idle]
 7959 MiB  pid 3540461  test_structured_chunking.py::test_structured_legal_chunking_axes
 5715 MiB  pid 3540455  [pytest-xdist idle]
 5703 MiB  pid 3540464  test_scjn_delta_refresh_service.py::...
 5431 MiB  pid 3540544  [pytest-xdist idle]
 5273 MiB  pid 3540467  test_ingestion_router_complementary_merge.py::...
 4817 MiB  pid 3540498  test_debt_canibal_atlas_hyde.py::...
 4631 MiB  pid 3540444  test_tfja_jurisprudence.py::...
```

El abanico es **una corrida de `pytest-xdist` con ocho workers**, cada uno con su
modelo en la GPU. No es carga de servicio: es una suite de tests. Y duro lo que
dura una suite --  **cuatro minutos**, de 00:30 a 00:33.

La serie entera, 19 067 muestras del 09-10 al 09-25:

```
p50 49.05 | p75 49.48 | p85 50.00 | p90 50.15 | p95 50.15 | p99 52.18 | max 85.40
por encima de 55.3 GiB: 18 episodios, 67 min EN TOTAL, el mas largo 11 min
```

### El muro

```
121.1 GiB (MemTotal) - 86.0 (reserva) = 35.1 GiB para TODOS los cgroups
app.slice, pico de este arranque      = 39.8 GiB   (memory.peak = 42731823104)
```

`app.slice` **sola**, en su pico observado, se pasa por 4.7 GiB del presupuesto
entero -- antes de docker, antes de `system.slice`, antes del kernel. No hay
reparto que satisfaga el criterio sin poner el techo del escritorio por debajo
de lo que el escritorio ya uso, que es la salida que esta misma ficha descarto
por medicion.

**Un `close_check` que no puede salir positivo sin matar al sujeto no es un
criterio.** Es el gemelo de la regla de la flota: una verificacion que no puede
salir negativa no verifica, y una que no puede salir positiva tampoco.

### Y un defecto en el instrumento, que era mio

La herramienta imprimia `SUMA declarada` sumando dos cosas distintas: los techos
(48G, 16G) son **compromisos** que el kernel aplica; la reserva de 86.0 es un
**maximo observado** que no aplica nadie. El propio gate marca a `system.slice`
por exactamente eso -- "entra por lo que usa HOY y no por un compromiso"-- sobre
1.9 GiB, mientras hacia lo mismo con 86.

### Lo que se hizo: partir el criterio, sin aflojarlo

- **MITAD 1, compromisos.** Los techos componen contra el SUELO comprometido de
  GPU: el p95 de la serie, **derivado y no elegido**. De p50 a p95 el suelo se
  mueve 1.10 GiB sobre 121.1; de p85 a p95, 0.15. Es una meseta, asi que el
  numero lo pone el sujeto. De p99 al maximo hay un salto de 33.26 GiB, y ese
  salto es justo lo que la mitad 2 obliga a firmar.
- **MITAD 2, excursion.** El maximo observado tiene que caber en un presupuesto
  **FIRMADO** (`tasks/presupuesto_gpu.json`), con `owner`, `expires` y `reason`.
  Sin firma es ROJO, y ese es el estado por defecto a proposito: este repo no
  trae plantilla firmada, porque una plantilla que el gate acepte es el agujero.

**Partir el criterio NO lo puso en verde**, y eso es lo que separa esto de
aflojarlo:

```
rc=1 hoy
  MITAD 1 (compromisos)  PASA:  115.8 sobre 121.1, holgura 5.3
  MITAD 2 (excursion)    FALLA: nadie ha firmado
  y ademas: system.slice sigue sin techo
```

Seis mutaciones corridas contra el codigo real, en
`tasks/evidence/DEBT-TECHOS-SIN-CALIBRAR/controles-negativos-2026-09-25.txt`.
**Dos de ellas no las cazaba nadie** -- volver el suelo al maximo, y fijarlo a
mano en 50.0-- y por eso existen ahora `test_el_suelo_es_la_MESETA_y_no_el_pico`
y su control.

### Lo que falta ahora, que ya no es imposible

`system.slice` es el ultimo slice sin techo, y con la mitad 1 en 115.8 sobre
121.1 hay 5.3 GiB de holgura: **ponerle un techo ahora hace que el presupuesto
componga**, cosa que con la reserva en 86 no podia hacer ningun reparto.

No se le puso hoy a proposito. Lo unico que hay para elegir el numero es su
`memory.peak` de UN arranque (2.8 GiB en 8 h 19 min), y un techo sacado de un
arranque es exactamente el techo sin calibrar que esta ficha vino a quitar --
el de `docker.slice` salio de 18 944 muestras, y ese es el liston.

Asi que se creo la serie que faltaba: `bb sample` guarda desde hoy un bloque
`slices` con `cur_kb` y `peak_kb` de los tres slices. Un slice ilegible se
OMITE en vez de entrar como 0 (un 0 se promediaria como medida, y un techo
calibrado sobre ceros inventados mata procesos por un dato que nadie tomo), y un
kernel sin `memory.peak` escribe `null` y no 0.

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
