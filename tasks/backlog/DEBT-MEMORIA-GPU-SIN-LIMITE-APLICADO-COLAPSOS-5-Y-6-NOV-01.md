---
id: DEBT-MEMORIA-GPU-SIN-LIMITE-APLICADO-COLAPSOS-5-Y-6-NOV-01
kind: task
domain: GPU
title: "Nada aplica un limite a la memoria de la GPU: dos colapsos (5 y 6 nov) con el presupuesto vencido y el limitador CUDA sin integrar"
status: open
severity: P1
origin: measured
satd_family: BLIND_INSTRUMENT
created: 2026-11-06
close_check: {"cmd": "grep -q '\"aplicado_por\"' tasks/presupuesto_gpu.json", "expect": "exit_zero", "porque": "Falla hoy (medido 2026-11-06: grep -c devuelve 0). tasks/presupuesto_gpu.json declara 88.7 GiB de excursion de GPU 'sin que nada la detenga'; el campo aplicado_por debe nombrar el mecanismo que si la detiene (limitador CUDA integrado al lanzador, o tope en el lanzador de sisifo) y la ficha FEATURE-LIMITADOR-INTEGRAR-LANZADOR-FALLA-CERRADO-01 debe tener su medicion."}
---

## Medido el 2026-11-06 (journal del arranque anterior y del actual)

| Fecha | Disparador | Efecto |
|---|---|---|
| 2026-11-05 19:58:27 | NVRM `NV_ERR_NO_MEMORY` en `_memdescAllocInternal`; disponible de 42 GB a 5,8 % en segundos | earlyoom envio 54 senales (21 a ChatGPT, 6 `python3`, 4 `gjs`, `rustdesk` y otros). `tailscaled` y `NetworkManager` recibieron SIGKILL, systemd se rindio ("Start request repeated too quickly" a las 19:59:09 y 19:59:24) y quedaron caidos 17,6 h hasta el reinicio de las 13:37 del 6 nov. Sin acceso por Tailscale ni RustDesk. |
| 2026-11-06 15:04:47 | Contenedor `gpt-oss-runtime` (sisifo-benchmark.slice) con `vllm serve ... --gpu-memory-utilization 0.7`; GPU 89 577 MiB | Disponible en 9,99 % (umbral de earlyoom). 59 senales de earlyoom en 3 min a ChatGPT/Codex, que la app reabria sola: ciclo de reinicios. Se detuvo con `docker stop` por orden de Luis; disponible de 14,2 GB a 107,9 GB. |

## Por que ningun guardrail actuo

1. `tasks/presupuesto_gpu.json` es una firma, no un limite: autoriza 88,7 GiB "sin que nada la detenga" y **vencio el 2026-11-04**. El contenedor del 6 nov (87,5 GiB) cabia dentro de lo firmado.
2. `sisifo.slice` y `sisifo-benchmark.slice`: `MemoryMax=infinity`, `MemoryHigh=infinity` (medido con `systemctl show`). Ningun cgroup acota la memoria unificada de la GPU.
3. earlyoom elige por memoria residente: vLLM ocupa 89 GB de GPU pero `VmRSS` 0,9 GB (`vllm serve`) y 1,7 GB (`EngineCore`). Nunca es candidato; mata procesos de escritorio de 14 a 585 MiB sin bajar la presion.
4. `ai-memory-monitor` ("deteccion, no prevencion"), `nvrm-watch` ("evidencia, no predictor suficiente") y `bb-canario-motor` (apagado por defecto) solo observan.
5. El limitador CUDA existe (`tools/limita_cuda.py`, `tools/limitador_cuda_lab.sh`) y tiene prueba de laboratorio, pero su integracion al lanzador esta abierta desde 2026-10-12 (`FEATURE-LIMITADOR-INTEGRAR-LANZADOR-FALLA-CERRADO-01`): 25 dias.
6. La lista `--avoid` de earlyoom no incluia `tailscaled`, `NetworkManager` ni `rustdesk` hasta el 2026-11-06 15:06 (arreglado ese dia, ver Hecho). Sigue sin incluir ChatGPT/Codex.

## Hecho el 2026-11-06 (fuera del repo, en /etc)

- `/etc/default/earlyoom`: `--avoid` ahora incluye `tailscaled|NetworkManager|rustdesk` (copia en `/etc/default/earlyoom.bak`). Verificado en el journal de earlyoom tras el reinicio del servicio.
- Drop-ins `/etc/systemd/system/{tailscaled,NetworkManager}.service.d/bb-reinicio-ilimitado.conf` con `StartLimitIntervalSec=0`, `Restart=always`, `RestartSec=2`. Verificado con `systemctl show`; control negativo: `ssh`, sin drop-in, conserva `StartLimitIntervalUSec=10s`.
- **No esta en el repo**: `adopted/system-config/etc_default_earlyoom` conserva la lista vieja y el chequeo nocturno lo marca `DIVERGE`.

## Alcance

1. Decidir y aplicar UN mecanismo que detenga el consumo de GPU por encima del techo: integrar el limitador CUDA al lanzador (ficha de 2026-10-12) o fijar el tope en el lanzador de sisifo. Decision de Luis y de la sesion de sisifo.
2. Renovar o retirar `tasks/presupuesto_gpu.json` (vencio 2026-11-04) y anadir `aplicado_por`.
3. Adoptar al repo los cambios de /etc del 2026-11-06 (earlyoom y los dos drop-ins) para que el chequeo nocturno deje de marcar `DIVERGE`.
4. Decidir si ChatGPT/Codex entran al `--avoid` de earlyoom.
5. Un gate que avise cuando un presupuesto firmado vence, porque este vencio sin aviso conocido (no se verifico si el gate actual lo marco).

## Limite

No se identifico quien lanzo `gpt-oss-runtime` ni que sesion de sisifo estaba midiendo; no se aviso a sisifo de que el contenedor se detuvo. Tampoco se identifico quien pidio los ~30 GB del 2026-11-05. La proteccion de red de hoy no se probo con un colapso real.

## Decisiones de Luis, 2026-11-06

- **Quien muere primero cuando la memoria llega al 10 %:** el trabajo de GPU. Se logra con `--oom-score-adj 1000` en el lanzador de sisifo (hecho en `launch_gpt_oss_runtime.sh`, linea 179, archivo sin versionar, sin lanzamiento real todavia). Descartado: un guardian propio que detenga contenedores al 15 % (codigo nuevo sin probar) y dejar morir al escritorio como hoy (repite el ciclo de Codex). Medido con `earlyoom --dryrun`: con puntaje 1000 el contenedor es la primera victima, 1032 aun con `--avoid`; con la lista sin `vllm` el motor de chat real (`nemotron-server`, badness 1019) pasaria a ser la primera victima, por eso `/etc/default/earlyoom` NO se toca.
- **`proyecto-local-api`:** se deja apagada (se detuvo limpia a las 15:19:44, quien la detuvo no consta; la unidad instalada no tiene `KB_EMBEDDER_DEVICE`). Descartado: instalar la unidad de proyecto-local con embedder en CPU (cambio persistente pedido por proyecto-local, no verificado por otro canal) y arrancarla como esta (su embedder usa GPU). Motivo declarado: ninguno (eligio la opcion distinta de la recomendada). Consecuencia: proyecto-local no responde en :8011 y su chequeo de salud falla hasta que alguien la levante.

## Decision de Luis, 2026-11-06 (boleta «Techo GPU»): no firmar; medir primero

- **Medido con `python3 -m tools.presupuesto_memoria`:** maximo observado de GPU 100,0 GiB (2026-11-05T09:48-0600), por encima de los 88,7 GiB firmados; los techos suman 137,6 GiB sobre 121,1 (holgura −16,5 GiB: suelo de GPU 67,6 + app.slice 42,0 + docker.slice 16,0 + system.slice 12,0); 2 151 de 17 624 muestras (12,2 %) por encima del presupuesto; firma `SIN FIRMAR` (caduco el 2026-11-04). `presupuesto_memoria --check` sale con rc=1.
- **Decidido:** no se firma ninguna cifra hoy. Se mide primero el `--gpu-memory-utilization` minimo con el que arranca el modelo de sisifo (`gpt-oss-120b`; hoy 0.7, unos 87,5 GiB de GPU) y el techo se fija con esa medida. Motivo del voto: ninguno adicional (eligio la opcion recomendada).
- **Descartado:** firmar 100,1 GiB un mes (deja 21 GiB al resto, el escenario de los dos colapsos) y firmar 88,7 GiB otro mes (nace contradicha por la medida).
- **Pedido a sisifo (escrito como encargo el 2026-11-06 en el formato de sisifo, `reports/coordinacion-limite-gpu-gpt-oss/encargo-codex-sisifo.txt` del repo de sisifo, SHA-256 del cuerpo `0fda877d238391415975eb47740fda46283f896e4dee87629ed1b22b510ba814`; falta que la sesion de Codex de sisifo lo lea y entregue `entrega-sisifo.txt`):** arrancar `gpt-oss-120b` con `--gpu-memory-utilization` 0.60, 0.55 y 0.50 en ese orden, anotar si arranca, la GPU usada y el rendimiento, y entregar el menor valor que funciona. Hasta tener ese numero, `close_check` sigue fallando a proposito.
- **Reabrir si:** el modelo no arranca por debajo de 0.7; entonces la decision pasa a ser cuanta memoria se le quita al escritorio (el tope de `app.slice` de 42 GiB tiene su propia decision de 2026-10-17).

## Decision de Luis, 2026-11-09: se cancela la ventana de medicion; el alcance se reorienta
- **Decidido:** sisifo se retira (proyecto-local DECISIONS 2026-11-09, DGX-706). El 0.60/0.55/0.50 de `gpt-oss-120b` ya no se mide: el modelo no tiene dueno ni cliente. Ficha de la ventana cerrada `void_wontfix`.
- **Sigue abierto:** nada aplica un limite de memoria de GPU. El techo ya no se deriva de gpt-oss sino de lo que usa el motor de chat (`nemotron-server`) mas lo que lance un trabajo futuro. `guardia_gpu` solo detiene contenedores con `lanzado_por`; sin sisifo no hay ninguno, asi que queda sin objetivo hasta que alguien lance uno con la etiqueta.
- **Pendiente de voto:** que techo firmar para el motor de chat, o dejar `presupuesto_gpu.json` retirado.
- **Limite:** quien tiro los ~30 GB del 5 nov sigue sin identificarse.
