---
id: FEATURE-VENTANA-GPU-NOCTURNA-SECUENCIA-01
kind: task
domain: GPU
title: "Secuencia de la ventana nocturna de GPU (02:00-05:00) con el chat local apagado: cazador del kill, medicion de gpt-oss y restauracion"
status: open
severity: P1
origin: measured
satd_family: BLIND_INSTRUMENT
created: 2026-11-07
close_check: {"cmd": "test -s ~/.local/share/blackbox/ventana-gpu/resumen.txt && grep -q 'quien_mata=' ~/.local/share/blackbox/ventana-gpu/resumen.txt", "expect": "exit_zero", "porque": "Falla hoy (no existe el resumen). Cierra cuando una ventana supervisada deja el resumen con quien_mata=<proceso> o quien_mata=NO_REPRODUCIDO, el valor de --gpu-memory-utilization probado (o el motivo de no haberlo logrado) y nemotron restaurado (health 200)."}
---

## Decision que la habilita
`DECISIONS.md` 2026-11-07: ventana fija de 02:00 a 05:00, admision del lanzador hasta el fin de la ventana, primera ventana supervisada.

## Por que hace falta una secuencia
Dos pruebas de gpt-oss (2026-11-06 21:45 y 21:59) murieron a los ~4 min con `systemd: Sending signal SIGKILL ... on client request`; nadie ha identificado quien pidio el kill. Cada prueba apaga el chat local; sin orden ni tope, ese apagon se repite sin dar un dato.

## Tiempos medidos (para fijar los topes)
- Carga de gpt-oss-120b: 28 a 36 s por bloque, 15 bloques (≈ 7 a 9 min) — `docker logs` de las dos pruebas.
- Restauracion de nemotron: ≈ 3,5 a 4 min hasta `/health` 200 (21:47:25 arranque, 200 poco despues de las 21:51).
- Las dos muertes ocurrieron a los 3 min 58 s y 4 min 22 s de iniciado el contenedor.

## Secuencia (secuencial; cada paso tiene su condicion de parada)
1. **Preflight (T-10 min).** Todo debe cumplirse o no se empieza y se avisa por ntfy: alarma de la Dell con latido de menos de 2 min; `bb-guardia-gpu` y `bb-aviso-earlyoom` activos; `nemotron` con health 200; MemAvailable ≥ 45 000 MB; ningun otro proceso en la GPU salvo nemotron; no existe el contenedor `gpt-oss-runtime`.
2. **Encender el cazador** (`cazador.sh`: procesos `docker stop|kill`, llamadas D-Bus a systemd con PID de quien llama, eventos de Docker) y dejar su salida en `~/.local/share/blackbox/ventana-gpu/<fecha>/`.
3. **Prueba 0.60** con el lanzador de sisifo (admision hasta las 05:00) y la guarda de 15 000 MB.
   - Si muere antes de `/health`: leer la salida del cazador, escribir `quien_mata=<proceso>` en el resumen y **parar** (no se prueba 0.55). Ir al paso 6.
   - Si llega a `/health`: pedir una respuesta corta, anotar GPU maxima y latencia, detener el contenedor.
4. **Prueba 0.55** (solo si 0.60 arranco), igual que el paso 3.
5. **Prueba 0.50** (solo si 0.55 arranco). Se para en la primera que falle.
6. **Restaurar** nemotron con el teardown certificado de sisifo y esperar health 200 (hasta 5 min). Si pasan las 04:40, se restaura sin importar lo que falte.
7. **Resumen** en `resumen.txt` con: `quien_mata=`, valores probados con arranque si/no, GPU maxima por valor, MemAvailable minima, nemotron restaurado si/no. Aviso final por ntfy.

## Despues de la primera ventana limpia
- Automatizar con un timer de usuario (OnCalendar 02:00) y pasar el resumen a la ficha del techo de GPU (`DEBT-MEMORIA-GPU-SIN-LIMITE-APLICADO-COLAPSOS-5-Y-6-NOV-01`).
- Cola de la ventana para las demas fichas de GPU (1358, relojes A/B, CPU-PIN, calentamiento, residentes inactivos): cada una necesita leer su procedimiento; no se secuencian aqui hasta resolver el kill.
- `netconsole-arranque` se hace en su propia noche, con un reinicio controlado: requiere `DRIVER=r8127` en `/etc/blackbox/netconsole.conf`, `--kernel 6.17.0-1032-nvidia` y retroceder antes `netconsole-runtime` (dos destinos duplican cada mensaje).

## Limite
No se sabe aun si el kill vuelve a ocurrir con el cazador encendido; si no se reproduce, el resumen dice `NO_REPRODUCIDO` y el cierre pasa al valor de utilizacion medido.
