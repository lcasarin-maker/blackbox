---
id: DEBT-APP-SLICE-TOPE-42G-ESTRANGULA-LA-CACHE-DE-ARCHIVOS-01
kind: task
domain: MEMORY
title: "El tope de 42 GiB de app.slice expulsa y relee la cache de archivos con 60 GiB libres en la maquina"
status: open
severity: P2
origin: detected
detector: {"rule": "tests/test_reclaim_app_slice.py::test_reclamo_directo_de_app_slice_por_debajo_de_la_mitad", "confidence": 1.0}
satd_family: BLIND_INSTRUMENT
created: 2026-10-17
close_check: {"cmd": "python3 -m pytest -q -p no:cacheprovider --runxfail tests/test_reclaim_app_slice.py::test_reclamo_directo_de_app_slice_por_debajo_de_la_mitad", "expect": "exit_zero", "porque": "Medido 2026-10-17 en app.slice (arranque de las 17:07): 99 % del escaneo de memoria es reclamo directo (pgscan_direct 308390552 contra pgscan_kswapd 2934489) y workingset_refault_file 47837196 (unos 182 GB de cache releidos en 3 h), con memory.events max 55588 y MemAvailable global 60 GiB. El test lee el memory.stat vivo y exige que el reclamo directo baje de la mitad del escaneo; falla hoy con 99.1 %."}
---

## Medido (2026-10-17, ATOM, arranque de las 17:07)
Leido de `/sys/fs/cgroup/user.slice/user-1000.slice/user@1000.service/app.slice`:
- `memory.max` 42 GiB; `memory.current` 38.7 GiB, de ellos `inactive_file` 15.6 GiB.
- `memory.events`: `max 55588` (veces que el slice toco su tope). A las 20:23 ya iba en `max 63091`, con `oom 18` y `oom_kill 8`.
- `memory.stat`: `pgscan_direct 308390552` contra `pgscan_kswapd 2934489` (99 % de reclamo directo: lo pagan los procesos que piden memoria, dentro de su propio tiempo) y `workingset_refault_file 47837196` (unos 182 GB de cache expulsada y vuelta a leer del disco en 3 h).
- A la vez `MemAvailable` global era 60 GiB y `memory.pressure` del slice se quedaba cerca de 0.

Lectura: la cache de archivos se expulsa y se relee del disco de forma continua contra el tope del slice, no por falta de memoria en la maquina.

## Voto de Luis (2026-10-17)
MEDIR antes de tocar el tope. Ningun cambio de limites ahora. Revisitar en la revision del 2026-10-23, junto con `memory.high`.

## Instrumento (hecho)
- `bb sample` guarda en cada slice un bloque `reclaim` con los acumulados `refault_file`, `pgscan_direct`, `pgscan_kswapd`, `pgsteal_direct`, `inactive_file_kb`, `anon_kb`, `file_kb` (`NOT_COLLECTED` si falta o no se lee).
- `python3 -m tools.reclaim_ventana --desde 2026-10-17T18:00 --hasta 2026-10-17T19:00` imprime los deltas por minuto, la parte de reclamo directo y los GiB releidos, para cruzarlos con cada "la maquina iba lenta a las HH:MM".

## Que falta
Una decision sobre el tope (o `memory.high`) de app.slice tomada con la serie por delante: cuantos minutos de reclamo directo y refault coinciden con los reportes de lentitud, y si subir el tope o poner `memory.high` lo baja sin dejar al resto de la maquina sin margen. Cambiar el tope es un despliegue de root de Luis.

## Revision 2026-10-26 (vencida desde el 2026-10-23), voto de Luis: revisar con `reclaim_ventana`

`python3 -m tools.reclaim_ventana --desde 2026-10-25T19:34 --hasta 2026-10-26T19:34` (solo lectura), 1440 intervalos, NOT_COLLECTED 0:
`refault_file 150196976` paginas (~573 GiB releidos), `pgscan_direct 627202780`, `pgscan_kswapd 127087893`, reclamo directo 83.2 %.
Contra la medicion del 2026-10-17: entonces 99 % de reclamo directo y unos 182 GB releidos en 3 h (~61 GB/h); ahora 83.2 % y
~573 GiB en 24 h (~26 GB/h). La tasa baja a menos de la mitad y el reclamo directo sigue siendo la mayoria del escaneo. La
decision de tope o `memory.high` sigue exigiendo cruzar estos minutos con los reportes de lentitud, que esta serie no trae.
Sin cambio de limites hasta ese cruce.

## Voto de Luis 2026-10-30 (boleta de /cerrar-deuda): sin cambio y seguir midiendo

- **Decidido:** el tope de 42 GiB de `app.slice` no cambia. Se sigue la serie con `python3 -m tools.reclaim_ventana`.
- **Por que:** la relectura de cache bajo de ~61 GB/h (2026-10-17) a ~26 GB/h (2026-10-26) y no hay reportes de lentitud con hora para cruzar con los minutos de reclamo directo.
- **Descarta:** subir `MemoryMax` a ~48 GiB (sin efecto medido; los techos deben componer, `tools/presupuesto_memoria.py`); reponer `memory.high` (el 2026-10-16, a 38 GiB, coincidio con un segundo atasco a 30 s de reiniciar y se revirtio).
- **Reabrir si:** aparecen reportes de lentitud con hora que coincidan con minutos de reclamo directo alto en la serie.
