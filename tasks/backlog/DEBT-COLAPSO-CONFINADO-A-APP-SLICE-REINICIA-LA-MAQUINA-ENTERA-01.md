---
id: DEBT-COLAPSO-CONFINADO-A-APP-SLICE-REINICIA-LA-MAQUINA-ENTERA-01
kind: debt
domain: GPU
title: "El 16-oct un atasco de memoria confinado a app.slice reinicio la maquina entera, motor incluido"
status: open
severity: P1
origin: detected
detector: {"rule": "bb reboot: el arranque 934fa20f termino con etiqueta COLAPSO_MEMORIA (bb-usable COLAPSO sostenido 300s, watchdog 6 min) mientras las muestras de bb dan PSI full 0.0 en docker.slice y system.slice y 45-57 solo en app.slice", "confidence": 0.9}
satd_family: BLIND_INSTRUMENT
created: 2026-10-16
close_check: {"cmd": "python3 -m pytest tests/test_bb_usable.py -k atasco_confinado -q", "expect": "exit_zero", "porque": "Todavia no existe: el arreglo debe agregar una prueba con control negativo de que bb-usable distingue un atasco confinado a una slice (PSI de app.slice alto, docker.slice y system.slice en ~0) de uno del host, y no deja de acariciar el watchdog de systemd por el primero. Hoy el selector no recoge ninguna prueba y pytest sale distinto de 0."}
---

## Hueco
El 2026-10-16 a las 10:54:27 el watchdog de `bb-usable` (limite de 6 min) reinicio la maquina. El motor vLLM (`nemotron-server`) y todo lo demas cayeron con ella, y `bb` lo clasifico `COLAPSO_MEMORIA`. El atasco de memoria duraba 17 minutos (desde 10:37) y estaba **confinado a `app.slice`**: el motor y el sistema no tenian presion.

## Medido (evidencia: `tasks/evidence/DEBT-COLAPSO-CONFINADO-A-APP-SLICE-REINICIA-LA-MAQUINA-ENTERA-01/evidencia.txt`)
- Muestras de `bb sample` cada minuto, 10:37 a 10:55: `app.slice` con `memory.pressure full_avg10` de 25.8 a 56.0; `docker.slice` (el motor) y `system.slice` en 0.0 en TODAS. El PSI del host (`mem_full` 39 a 51) es el de `app.slice`.
- Hasta las 10:36 el PSI era ~0 con `app.slice` ya en ~38 GiB de su `memory.max` de 42 GiB (45097156608 B). El uso se quedo plano en ~38 GiB durante el atasco: no crecio.
- Los contadores `max` (5166044) y `oom_kill` (195) de `app.slice` NO cambiaron durante el atasco (son acumulados desde el arranque): no toco su tope en esa ventana.
- Al mismo tiempo el host marcaba `cpu_some` 31 a 71 % e `io_some` 23 a 37 %.
- `MemAvailable` del host 20 a 24 GB todo el rato (telemetria): la maquina no se quedo sin memoria.
- Lo que arranco justo antes (journal): 10:35:11 un `liberation_job` de Atlas (`local_llm_grill_me.py`, usa el motor local); 10:35:21 la suite `pre-push` completa de otro proyecto privado (B); 10:43 trabajos `nice -n 10` de Twiner y de `_consolidacion` (jueces). Tres sesiones de otros proyectos figuraban `busy`. Ninguno era de blackbox: el push 70 de esta sesion habia terminado antes de las 10:33.
- `ESCALON` de `bb-usable` mato procesos python3 de scopes Claude a las 10:37:55, 10:42:56 y 10:47:56; el PSI no bajo.
- Los datos de esa madrugada: el archivo de muestras trae 377 bytes NUL (el corte abrupto).

## Quien estaba corriendo (medido: registros de origen de bb-usable, 10:42:26 y 10:48:57)
Mayores RSS por scope: `pytest` de un proyecto privado (A) bajo el portero (`bb-portero-suite-91364.scope`, 3 procesos) 6.9 a 5.8 GiB; `liberation_job.scope` de Atlas (`python3`, usa el motor local) 3.1 a 5.8 GiB; `un servicio de otro proyecto privado (C)` 3.8 GiB; un job de Twiner 2.7 GiB; el motor (`VLLM::EngineCore`, en docker.slice) 5.3 GiB. Suma de RSS de los mayores: ~15 a 20 GiB; el resto de los ~38 GiB de `app.slice` es cache de archivos (hoy: anon 16.7 GiB, file 20.8 GiB con `app.slice` en 40.3 de 43.0 GiB).
El portero SI vio y congelo una suite (raiz 91364, 10:34:57, `holgura de app.slice 3936744 kB < 4194304 kB`) y la dejo pasar ~27 s despues; su puerta mide la holgura con `memory.current`, que cuenta la cache, y por eso `app.slice` vive casi siempre a 1-4 GiB del tope.

## Inferido (NO medido)
Que el atasco fue contencion por jobs paralelos pesados dentro de `app.slice` (reclamo/swap/IO) y no por llegar al tope. No se capturo que tarea estaba atascada ni `memory.stat` (anon/file/shmem) ni la lectura de swap de `app.slice`.

## Por que importa
La respuesta (reinicio de toda la maquina) es desproporcionada a un atasco confinado: el motor llevaba horas sano y no tenia presion. `bb-usable` decide por el PSI GLOBAL de `/proc/pressure/memory`, que incluye el de `app.slice`.

## Que podria cerrarlo (decision de Luis, en boleta)
1. Que `bb-usable` compare el PSI por slice y, si el atasco esta confinado a `app.slice`, actue sobre `app.slice` (congelar o matar al mayor consumidor con senales ya probadas) en vez de dejar de acariciar el watchdog que reinicia todo.
2. Bajar la concurrencia de trabajos pesados en `app.slice` (el portero ya admite suites; aqui entraron jobs de otros proyectos).
3. Cambiar `app.slice` `memory.max`/`memory.high` para que reclame antes.
Cada una exige una prueba con control negativo antes de tocar el watchdog, porque un cambio ahi falla en silencio.

## Voto de Luis 2026-10-16 (las tres, multiseleccion)
1. `bb-usable` mira el PSI por slice. Se implementa tras el interruptor `atasco_confinado` (off/observar/actuar), empieza en `observar`: registra la clase del atasco y que habria hecho, y captura `memory.stat`, swap y presion de IO/CPU, SIN cambiar cuando se reinicia. `actuar` acaricia el watchdog solo mientras el atasco sea confinado y dure menos de `CONFINADO_MAX_S`; docker.slice o system.slice con presion lo devuelven al comportamiento de siempre. Limite declarado: sin una accion de alivio que funcione, `actuar` solo retrasa el reinicio (el ESCALON de bb-usable mato 3 procesos de 0.4-0.5 GiB sin bajar el PSI).
2. Frenar jobs pesados de otros proyectos. El portero ya gobierna las suites; lo que no gobierna son `liberation_job` (Atlas), `otro proyecto privado (C)` y los jobs `nice` de Twiner, y su puerta usa `memory.current` (con cache). Cambiar la metrica exige recalibrar `HOLGURA_MIN_KB` contra las muestras: pendiente.
3. Bajar `memory.high` de `app.slice`: aplicado en caliente (`systemctl --user set-property --runtime`, no sobrevive al reinicio) como prueba reversible; ver el avance.

## Avance 2026-10-16 (misma tarde del reinicio)
- (1) `bin/bb-usable`: clasificacion por slice tras el interruptor `atasco_confinado`, `off` por defecto. `observar` registra en `$BLACKBOX_DATA/interruptores/atasco_confinado.jsonl` la clase, las presiones, que habria hecho y (cada 5 min) `memory.stat`, swap y presion de IO/CPU; `actuar` acaricia solo con atasco confinado y menos de 1200 s (`CONFINADO_MAX_S`, sin medir: `ponytail`). 29 pruebas en `tests/test_atasco_confinado.py`, 6 mutantes muertos, bloque nuevo 100 % cubierto. NO esta desplegado: `bb-usable` es una unidad de sistema que corre este archivo; hace falta `sudo systemctl restart bb-usable.service` y poner `atasco_confinado` en `observar` en `interruptores.json`. Pasar a `actuar` es decision aparte, con un atasco confinado visto en el registro.
- (3) `memory.high` de `app.slice` en 38 GiB, EN CALIENTE y sin persistir (`systemctl --user set-property --runtime`): en 2 minutos el slice bajo de 38.9 a ~35 GiB (cache), `high` conto 9347 eventos y la presion se quedo en 0.00. Un solo ensayo corto con el motor cargando; no demuestra nada sobre el atasco. Se pierde al reiniciar. Para fijarlo hay que escribir un drop-in; no se hizo.
- (2) Sin cambios de codigo: el hallazgo (la puerta del portero mide con `memory.current`, que incluye ~20 GiB de cache) pide recalibrar `HOLGURA_MIN_KB` contra las muestras antes de cambiar la metrica.

## Avance 2026-10-16 13:20: desplegado
- `bb-usable` reiniciado con el codigo nuevo (13:15:42, PID 1497378, sonda de referencia 30 ms) y `atasco_confinado` en `observar` en `interruptores.json`; `bb-usable` lee el modo y las presiones por slice (app 0.0, docker 0.0, system 0.0 -> `general`, sin atasco). Desde ahora cualquier atasco deja fila en `$BLACKBOX_DATA/interruptores/atasco_confinado.jsonl` con `memory.stat`, swap y presion de IO/CPU; la decision de pasar a `actuar` sigue pendiente de ver uno.
- `memory.high` de `app.slice` = 38 GiB persistente: drop-in `~/.config/systemd/user/app.slice.d/memory-high.conf` (copia en `adopted/system-config/`), `systemctl --user show app.slice -p MemoryHigh` = 40802189312. Efecto medido solo 2 minutos con el motor cargando (presion 0.00); sigue sin medirse contra un atasco.
