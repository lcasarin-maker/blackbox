---
id: FEATURE-ADMISION-TODO-O-NADA-CON-HOLGURA-REAL-01
kind: task
domain: MEMORY
title: "Admision de todo o nada con la holgura real: el portero y los arranques pesados niegan con ambos numeros cuando el espacio no existe (idea de la carga de modelos de Athena's Engine)"
status: open
severity: P2
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-10-30
close_check: {"cmd": "python3 -m pytest -q tests/test_admision_holgura_real.py", "expect": "exit_zero", "porque": "Especificacion pendiente: el archivo de pruebas no existe hoy (rc=4 medido el 2026-10-30), asi que falla. Pasa solo cuando la prueba reproduzca la ventana del 2026-10-16 (10:34:57) y la puerta nueva niegue la suite que la puerta actual dejo pasar, con control negativo de una ventana sana que la puerta nueva admita."}
---

## Idea de origen y hueco propio

Athena libera antes de cargar un modelo y comprueba que el espacio existe; si no, no asigna nada, devuelve el modelo previo y dice ambos numeros (seccion "Several models, one engine"). El hueco de bb es medido en `DEBT-COLAPSO-CONFINADO-A-APP-SLICE-REINICIA-LA-MAQUINA-ENTERA-01`: el portero congelo una suite a las 10:34:57 con "holgura de app.slice 3936744 kB < 4194304 kB" y la dejo pasar unos 27 s despues; su puerta mide la holgura con `memory.current`, que cuenta la cache, y por eso `app.slice` vive casi siempre a 1-4 GiB del tope. A las 10:54:27 el watchdog reinicio la maquina.

## Trampa que la ficha ya conoce

La senal global NO basta. En ese colapso `MemAvailable` del host marcaba 20 a 24 GB todo el rato, y en los colapsos del 2026-10-11 marcaba 15-30 GB (ver `FEATURE-VIGILANTE-MEMAVAILABLE-UMA-01`). Una admision por `MemAvailable` habria admitido. La senal candidata es la del scope: anon + shmem (sin cache) frente al tope de la clase, mas el PSI de `app.slice`. Falta medir cual separa mejor, por serie y no por intuicion.

## Para cerrar

1. Medir en `samples/*.jsonl` y en la evidencia de la ventana 2026-10-16 que senal habria negado la suite y cuantos falsos positivos habria dado sobre el resto de la serie (precedente: a 16 GiB `memavail` marco 560 muestras y 431 fueron falsas).
2. Implementar la puerta en el portero como interruptor `off`/`observar`/`actuar` (`tools/interruptores.py`), arrancando en `observar`. La negativa registra lo necesario y lo disponible, como Athena.
3. Para las cargas que bb no gobierna (arranque del motor vLLM, `FORUM-00-DOCKER-OOM-RESTART-LOOP`), bb PROPONE una condicion previa al arranque (por ejemplo `ExecCondition=` de systemd, a verificar en esta maquina, systemd 255); aplicarla es decision de Luis porque la configuracion del motor es de la pila de IA.
4. `tests/test_admision_holgura_real.py`: reproduce la ventana del 2026-10-16 y la ventana sana; el negativo es que la puerta actual (memory.current) pasa la suite en la primera.

## Limites declarados

Retener trabajo sano tiene costo: una suite congelada sigue corriendo su `timeout` (riesgo ya declarado en `FEATURE-PORTERO-UNIVERSAL-DE-LA-MAQUINA-01`).

## Avance 2026-10-30 (sin cerrar: NECESITA DECISION)

Medido (`tasks/evidence/FEATURE-ADMISION-TODO-O-NADA-CON-HOLGURA-REAL-01/medicion.txt`):
- La serie del 2026-10-16 NO trae anon ni shmem de `app.slice` (el campo `reclaim` empieza el 2026-10-17 20:36): el veredicto de la puerta todo-o-nada sobre la suite de 10:34:57 es NOT_COLLECTED. Las dos composiciones medidas ese mismo dia dan veredictos opuestos (16.7 GiB de anon por la tarde: admite; 37269116 kB de anon+shmem en el atasco de 13:46: niega).
- PSI de `app.slice` no la habria negado (full_avg10 0.0-0.05 a la hora de admision; el atasco empieza a las 10:37) y MemAvailable marcaba 40.9-45.9 GB a esa hora.
- Donde hay dato, `tope - anon < 20 GiB` niega el 0.93 % del tiempo (168 de 18 066 muestras sanas, 157 sin colapso despues) y ve 2 de 6 episodios. Sobre 1168 admisiones reales de suite habria negado 10, una de ellas la unica seguida de colapso: 2026-10-21 16:36:27 (necesario 20971520 kB, disponible 16772852 kB; colapso a las 16:38:03).

Hecho: interruptor `portero_admision` en `tools/portero.py` (`off` por defecto y ante lo ilegible; `observar` registra `habria_negado` con `necesario_kb` y `disponible_kb`; `actuar` congela o mantiene congelada la suite que no cabe). `tests/test_admision_holgura_real.py`: (a) la ventana del 21-oct con fixture de filas reales; (b) ventana sana real (2026-10-17 21:17:24) que admite; (c) la puerta actual admite el caso (a) y reproduce el `descongelar` del 16-oct; mutantes en `mutantes.txt`. El close_check sale rc=0.

Pendiente de Luis: el `porque` del close_check pide negar la suite del 16-oct, y ese dato no existe. Opciones: aceptar la ventana del 21-oct como reproduccion (y reescribir el `porque`), o dejarla abierta hasta tener registro de `observar`. Poner `portero_admision` en `observar` en `interruptores.json` (la ficha dice "arrancando en observar") tambien es suyo. El punto 3 (condicion previa al arranque del motor vLLM) no se toco.
