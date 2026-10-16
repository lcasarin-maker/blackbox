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
- Lo que arranco justo antes (journal): 10:35:11 un `liberation_job` de Atlas (`local_llm_grill_me.py`, usa el motor local); 10:35:21 la suite `pre-push` completa de office2office; 10:43 trabajos `nice -n 10` de Twiner y de `_consolidacion` (jueces). Tres sesiones de otros proyectos figuraban `busy`. Ninguno era de blackbox: el push 70 de esta sesion habia terminado antes de las 10:33.
- `ESCALON` de `bb-usable` mato procesos python3 de scopes Claude a las 10:37:55, 10:42:56 y 10:47:56; el PSI no bajo.
- Los datos de esa madrugada: el archivo de muestras trae 377 bytes NUL (el corte abrupto).

## Inferido (NO medido)
Que el atasco fue contencion por jobs paralelos pesados dentro de `app.slice` (reclamo/swap/IO) y no por llegar al tope. No se capturo que tarea estaba atascada ni `memory.stat` (anon/file/shmem) ni la lectura de swap de `app.slice`.

## Por que importa
La respuesta (reinicio de toda la maquina) es desproporcionada a un atasco confinado: el motor llevaba horas sano y no tenia presion. `bb-usable` decide por el PSI GLOBAL de `/proc/pressure/memory`, que incluye el de `app.slice`.

## Que podria cerrarlo (decision de Luis, en boleta)
1. Que `bb-usable` compare el PSI por slice y, si el atasco esta confinado a `app.slice`, actue sobre `app.slice` (congelar o matar al mayor consumidor con senales ya probadas) en vez de dejar de acariciar el watchdog que reinicia todo.
2. Bajar la concurrencia de trabajos pesados en `app.slice` (el portero ya admite suites; aqui entraron jobs de otros proyectos).
3. Cambiar `app.slice` `memory.max`/`memory.high` para que reclame antes.
Cada una exige una prueba con control negativo antes de tocar el watchdog, porque un cambio ahi falla en silencio.
