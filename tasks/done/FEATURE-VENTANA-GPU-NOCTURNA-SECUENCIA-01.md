---
id: FEATURE-VENTANA-GPU-NOCTURNA-SECUENCIA-01
kind: task
domain: GPU
title: "Secuencia de la ventana nocturna de GPU (02:00-05:00) con el chat local apagado: cazador del kill, medicion de gpt-oss y restauracion"
status: done
severity: P1
origin: measured
satd_family: BLIND_INSTRUMENT
created: 2026-11-07
close_check: {"cmd": "test -s ~/.local/share/blackbox/ventana-gpu/resumen.txt && grep -q 'quien_mata=' ~/.local/share/blackbox/ventana-gpu/resumen.txt", "expect": "exit_zero", "porque": "Falla hoy (no existe el resumen). Cierra cuando una ventana supervisada deja el resumen con quien_mata=<proceso> o quien_mata=NO_REPRODUCIDO, el valor de --gpu-memory-utilization probado (o el motivo de no haberlo logrado) y nemotron restaurado (health 200)."}
closed_at: 2026-11-09
closure_type: void_wontfix
reason: "Luis voto el 2026-11-09 cancelar la ventana: proyecto-local DECISIONS 2026-11-09 retira sisifo (DGX-706) y el runtime gpt-oss, unico objeto de la medicion, queda sin dueno ni cliente. No se corrio la ventana; quien_mata queda sin medir."
evidence: {"pass":"tasks/evidence/FEATURE-VENTANA-GPU-NOCTURNA-SECUENCIA-01/pass.txt"}
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
2. **Coordinar con quien usa el chat local (metodologia de skilletor y proyecto-local).** Hoy el unico cliente del motor en `127.0.0.1:8000` es `skilletor-cola-local.service` (`tools/cola_local_durable.py` de skilletor, medido con `ss -tnp`). Ese cliente toma el candado compartido `catalogo/garantias/local/local_llm.lock` (`flock` exclusivo) antes de cada inferencia, y el acuerdo de `coordinacion-proyecto-local.json` dice: «proyecto-local gestiona servicio y recursos; Skilletor conserva catalogo». Por tanto bb toma ese mismo candado (`flock` exclusivo, espera a que termine la inferencia en curso) ANTES de detener nemotron y lo suelta DESPUES de restaurarlo con health 200: la cola de skilletor espera sin fallar. Ademas: aviso a Luis por ntfy al empezar y al terminar; `SendMessage` a las sesiones de Claude abiertas que dependan del motor; y una nota en el resumen de la ventana para la sesion de proyecto-local y la de skilletor. Si el candado no se obtiene en 10 min, no se empieza.
   - **Aviso escrito el 2026-11-08** (por orden de Luis): `aviso-ventana-gpu-bb.txt` en la carpeta de coordinacion de sisifo, SHA-256 del cuerpo `45bb18d779e481238dc148217473acd2440b278b7941c7faa88daddf092fbd9c`. Pide al Codex coordinador no suspender lo que corra mientras exista `~/.local/share/blackbox/ventana-gpu/activa.json` con `ahora < fin`, y que confirme leerlo con `respuesta-coordinador-ventana-gpu.txt` (SHA copiado en la primera linea).
   - **Condicion de arranque:** no se empieza sin esa respuesta o sin que Luis diga expresamente que se omite. bb crea `activa.json` al empezar y lo borra al terminar.
3. **Encender el cazador** (`cazador.sh`: procesos `docker stop|kill`, llamadas D-Bus a systemd con PID de quien llama, eventos de Docker) y dejar su salida en `~/.local/share/blackbox/ventana-gpu/<fecha>/`.
4. **Prueba 0.60** con el lanzador de sisifo (admision hasta las 05:00) y la guarda de 15 000 MB.
   - Si muere antes de `/health`: leer la salida del cazador, escribir `quien_mata=<proceso>` en el resumen y **parar** (no se prueba 0.55). Ir al paso 7.
   - Si llega a `/health`: pedir una respuesta corta, anotar GPU maxima y latencia, detener el contenedor.
5. **Prueba 0.55** (solo si 0.60 arranco), igual que el paso 4.
6. **Prueba 0.50** (solo si 0.55 arranco). Se para en la primera que falle.
7. **Restaurar** nemotron con el teardown certificado de sisifo y esperar health 200 (hasta 5 min). Si pasan las 04:40, se restaura sin importar lo que falte.
8. **Resumen** en `resumen.txt` con: `quien_mata=`, valores probados con arranque si/no, GPU maxima por valor, MemAvailable minima, nemotron restaurado si/no. Aviso final por ntfy.

## Despues de la primera ventana limpia
- Automatizar con un timer de usuario (OnCalendar 02:00) y pasar el resumen a la ficha del techo de GPU (`DEBT-MEMORIA-GPU-SIN-LIMITE-APLICADO-COLAPSOS-5-Y-6-NOV-01`).
- Cola de la ventana para las demas fichas de GPU (1358, relojes A/B, CPU-PIN, calentamiento, residentes inactivos): cada una necesita leer su procedimiento; no se secuencian aqui hasta resolver el kill.
- `netconsole-arranque` se hace en su propia noche, con un reinicio controlado: requiere `DRIVER=r8127` en `/etc/blackbox/netconsole.conf`, `--kernel 6.17.0-1032-nvidia` y retroceder antes `netconsole-runtime` (dos destinos duplican cada mensaje).

## Limite
No se sabe aun si el kill vuelve a ocurrir con el cazador encendido; si no se reproduce, el resumen dice `NO_REPRODUCIDO` y el cierre pasa al valor de utilizacion medido.

## Hallazgo del 2026-11-08: quien mato las dos pruebas fue el Codex coordinador

- **Evidencia:** `reports/coordinacion-limite-gpu-gpt-oss/suspension-bb-medicion-gpu-060.json` (repo de sisifo) lo escribio el `Codex coordinador` con marca `2026-11-06T21:59:57.986`, el mismo segundo en que systemd registro `bb-medicion-gpu-060.service: Sending signal SIGKILL ... on client request`. El manifiesto renombra `medir_gpu.sh` a `medir_gpu.sh.suspendido-caida-rvlpwk` (sha256 `3e619424...`), nombra la unidad, fija `revisar_antes_de` 2026-11-13 y dice: «Solo por instruccion expresa. Verificar hash y modo antes de restaurar». Es el contrato de suspension de Luis aplicado por otro agente.
- **Por que:** el agente vio caer el chat local (el lanzador detiene nemotron) y suspendio lo que lo causaba. El primer kill (21:45:30) coincide con una rafaga de SIGKILL de `tokio-rt-worker` (el servidor de Codex) en el registro de senales de blackbox.
- **Consecuencia para la secuencia:** el paso 2 (coordinar) deja de ser opcional. Antes de apagar nemotron hay que avisar al Codex coordinador de la ventana, y el script suspendido solo se reactiva por instruccion expresa de Luis; se recrea desde el repo en vez de restaurar el archivo marcado. El contenedor `gpt-oss-runtime` detenido (creado 2026-11-06 21:56) debe retirarse antes de lanzar (el lanzador aborta si preexiste); su registro ya esta archivado en `prueba-0.60-abortada-2/`.
- **Lo que no se probo:** que avisar al coordinador impida el kill. Se prueba en la primera ventana, con el cazador encendido.
