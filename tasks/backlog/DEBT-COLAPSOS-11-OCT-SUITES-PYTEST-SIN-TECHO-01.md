---
id: DEBT-COLAPSOS-11-OCT-SUITES-PYTEST-SIN-TECHO-01
kind: task
domain: GPU
title: "Dos colapsos de memoria el 11-oct coinciden con suites pytest de Atlas sin techo de memoria"
status: open
severity: P1
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-10-12
close_check: {"cmd": "grep -q suites_pytest_con_techo tasks/evidence/DEBT-COLAPSOS-11-OCT-SUITES-PYTEST-SIN-TECHO-01/medicion.txt", "expect": "exit_zero", "porque": "Dos colapsos (boots 5461291a a las 22:02 y 7b217d8b a las 22:44, PSI memory full 98 % con 15-30 GB disponibles, reinicio por watchdog, BERT 0x10) arrancaron con una suite pytest de Atlas corriendo (scopes liberation_job_test_* a las 21:48 y 22:43), vLLM con 33 peticiones y, la primera vez, un pre-push de otro proyecto. En el segundo no corria ningun job de la cola. Cierra cuando haya una medicion con las suites bajo un scope con MemoryMax y el colapso no se reproduzca, escrita en medicion.md con la frase suites_pytest_con_techo."}
---

## Diagnostico a fondo (2026-10-12), medido en `samples/` de bb

Cadena: enjambre de procesos en `app-com.anthropic.Claude-*.scope` (sesiones de agente y sus pytest-xdist) -> `app.slice` pegado a ~39-40 GiB de su `MemoryMax=42G` -> estancamiento (PSI memory full 98 %) con 18-30 GB libres en el sistema -> `bb-usable` declara COLAPSO a los 300 s y, por diseno, deja de acariciar el watchdog -> reinicio de TODA la maquina. vLLM seguia sirviendo (el journal lo muestra con 200 OK durante el colapso 1): el fallo era local al slice de apps, la maquina entera se reinicio por la politica.

- Colapso 1 (22:02): scope Claude 25-30 GB con 150-193 procesos desde las 21:44 (antes 14-15 GB y ~90-115 procesos); `app.slice` 41.1-41.5 M kiB entre 21:58 y 22:00 (94 % del tope).
- Colapso 2 (22:44): scope Claude de 23.6 a 34.5 a 38.4 GB en dos minutos, procesos 46 -> 62 -> 136; un `python3` (pid 73493) tomo 26 GB en un minuto; swap out 12 000 paginas/s; `app.slice` 41.1 M kiB; `scope_pressure_alert` encendio a las 22:45:03 (solo observa). Ningun job de la cola de Atlas corria; si la suite de Atlas (22:43:47), 4-5 procesos `claude` reanudando sesiones (+6 GB cada uno) y vLLM.
- 05-oct (`DEBT-COLAPSO-05-OCT-ENJAMBRE-DE-PROCESOS-SIN-TECHO-01`): `app.slice` 40.32 GiB, PSI 49 %: el mismo mecanismo, y dice que el `MemoryMax=42G` no lo freno.
- Calibracion con 489 muestras que traen scope y PSI: con el scope Claude por debajo de 35 GB, 0 de 439 muestras tuvo PSI full >= 10 (maximo 7.17); con 35-40 GB, 2 de 2 la tuvieron (maximo 64.7). Muestra pequena para el tramo alto.
- No fue hardware ni el reindexado de Atlas (el colapso 2 ocurrio sin el) ni calor (sin throttle termico).

Dato aportado por la sesion `ae` (aequitas_os, 2026-10-12): lanzo `git push origin main` con pre-push de suite completa (~8.7k tests, ~40 min) hacia las 22:43 del 11-oct, sin tope, y seguia corriendo al reiniciar a las 22:54; sus pushes de las ~19:40, 20:20 y 21:00 no colapsaron nada. Coincide con el `python3` de 26 GB del colapso 2 (no probado que sea ese pid) y deja la hipotesis de trabajo: el colapso aparece cuando DOS o mas suites completas coinciden dentro de `app.slice` (colapso 1: suite de Atlas 21:48 + push de Declutter 21:51 + mi pre-push; colapso 2: push de aequitas 22:43 + suite de Atlas 22:43:47), no cuando corre una sola. Es correlacion temporal con n=2; el escalon de prevencion no depende de ella.

## Origen atribuido por las transcripciones de las sesiones (2026-10-12)

Fuente: ordenes `Bash` con hora en `~/.claude/projects/*/*.jsonl` (UTC; CST = UTC-6). Quien lanzo que:

Colapso 2 (~22:44:03): tres `git push` con pre-push (suite completa) en 3 minutos, de tres sesiones distintas:
- 22:41:25 sesion Atlas: `setsid nohup bash -c "git push origin master"`.
- 22:44:00 sesion aequitas_os: `git push origin main` con `DATABASE_URL` cargada de `~/secrets/aequitas.env`; el `python3` pid 73493 que tomo 26 GB aparece 3 s despues (muestra de 22:44:03). Es la atribucion mas probable, no probada: las muestras no guardaron el cmdline del pid.
- 22:44:14 sesion office2office: comando en segundo plano de push (`timeout 1200 git push origin main` en la ronda anterior).

Colapso 1 (21:42-21:58, colapso 22:02): al menos seis pushes/suites simultaneos, todos tras el cambio de kit 9.9.0 de la flota: blackbox 21:42:20 (el `git push` de `/clean`), Atlas (varios, uno matado con pkill a las 21:44:56), simple 21:46:06 (migracion_atom) y 21:47:05 (simplecode), office2office 21:49:39 (`timeout 1200 git push origin main`), declutter 21:51:04, y una suite pytest de Twiner a las 21:55:42; aequitas esperaba con un vigia a que terminara un push.

Causa de origen: la orden de sincronizar la flota con el kit 9.9.0 hizo que cada proyecto commiteara y empujara a la vez, y cada pre-push corre su suite completa (pytest-xdist con decenas de workers) sin tope. No fue un proceso de un solo dueno: fue una estampida coordinada por una orden. El `/clean` de esta sesion fue uno de los pushes.

Pendiente: el instrumento no guarda quien lanza (solo pid, comm, unit). Ver el requisito de origen de procesos (cadena de ancestros, cmdline enmascarado, repo del hook) en `bb origen`.

Limite declarado: `memory.events` de `app.slice` (cuantas veces toco `max`, `oom_kill`) se pierde al reiniciar; que el slice estuviera contra su techo es inferencia por su 94 % de uso, no una lectura directa.

## Prevencion propuesta

1. Escalon antes del reinicio en `bb-usable`: con PSI full >= 10 sostenido 60 s y `app.slice` >= 90 % del tope, matar el proceso mayor del scope Claude que no sea `claude`/`node` (el pytest o python desbocado) en vez de esperar 300 s y reiniciar la maquina. Con control negativo: un acaparador sintetico en un scope de prueba.
2. Persistir `memory.events` y `memory.pressure` de `app.slice` en cada muestra de `bb sample`, para convertir la inferencia en medicion.
3. Demanda: limitar `-n` de pytest-xdist a 4 workers en los repos y correr suites completas bajo `systemd-run --user --scope -p MemoryMax=20G -p MemorySwapMax=0`.

### Implementado el 2026-10-12 (sin desplegar; la ficha sigue abierta)

- (1) Escalon en `bin/bb-usable` (`decidir_escalon`, `matar_en_grupo`, puras; lectura y senal aparte). PSI full >= 10 sostenido `ESCALON_SOSTENIDO_S`=60 s Y un app.slice >= `ESCALON_FRACCION_SLICE`=0.90 de su `memory.max` -> SIGKILL al grupo del mayor RSS de los scopes `app*com.anthropic.Claude-*.scope` no protegido (claude, node, claude-desktop, escritorio, docker/vLLM, piezas de bb, root, PID 1, fuera de scope); solo el pid si el grupo incluye algo protegido o ajeno. Una muerte por `ESCALON_ENFRIAMIENTO_S`=300 s (= `PSI_ACT_SOSTENIDO_S`). El COLAPSO y el watchdog quedan intactos (test con el escalon "matando" en cada vuelta: mismas 9 caricias). Falla cerrado: cgroup o /proc ilegible -> no mata y lo dice; una excepcion del escalon se registra y no tumba al vigilante. Cada decision, tambien "nada" y su motivo, va a `$BLACKBOX_DATA/escalon/<dia>.jsonl`; al cumplirse la condicion y al declararse COLAPSO se guarda el origen de los 10 mayores del sistema en `$BLACKBOX_DATA/origen/`, y el evento de una muerte cita el origen del proceso muerto.
- (2) `bb sample` guarda `events` y `pressure` de cada slice (cgroup v2; `null` si no se leen) y `pidio_origen` (cadena y cmdline enmascarado del que mas crece cuando pasa de 2 GiB de VmSize; corte medido) y captura el origen al encender `scope_pressure_alert`.
- Origen: `tools/origen_proceso.py` (fuente primaria y regla de "padre salio" portadas de witr, Apache-2.0, ver `NOTICE`) y `bb origen` para leerlo.
- Numeros y su procedencia: `tasks/evidence/DEBT-COLAPSOS-11-OCT-SUITES-PYTEST-SIN-TECHO-01/calibracion-escalon.txt`. Mutaciones (22 del escalon, 12 del origen, todas muertas): `mutaciones.txt`.
- Superficie medida de accion sin reinicio posterior: el 2026-10-06 08:50 y 09:10 hubo episodios de PSI 49-66 % durante 180-240 s con app.slice al 93.4-94.6 % que se recuperaron solos; el escalon habria matado ahi.
- Despliegue pendiente (lo corre Luis, requiere sudo): ver `tasks/evidence/DEBT-COLAPSOS-11-OCT-SUITES-PYTEST-SIN-TECHO-01/despliegue.txt`. Ojo: `ExecStart` apunta al checkout, asi que el codigo nuevo entra en el SIGUIENTE arranque de `bb-usable` aunque nadie lo despliegue; sin la linea `BLACKBOX_DATA` de la unit, sus eventos irian a /root.
- Pendiente aqui: la fila de `bin/bb-usable` en el inventario de SPEC.md no menciona el escalon (no se edito: solo se tocan filas que `tools/inventario.py --check` exige).

## Medido antes (2026-10-12, primera version de esta ficha)


- Colapso 1: PSI full 42 % a las 22:02:07 (boot 5461291a) hasta el reinicio de las 22:12:46. Corria el job 79_00 de Atlas, una suite de Atlas desde las 21:48 y un pre-push de otro proyecto desde las 21:51.
- Colapso 2: PSI full >= 10 sostenido desde ~22:44:12 (boot 7b217d8b), reinicio a las 22:54:41. Solo corrian jobs pequenos de la cola (terminaron 22:27) y una suite pytest de Atlas desde las 22:43:47.
- En ambos, `earlyoom` veia 15-30 GB disponibles: el disponible no predice este colapso.
- El job de reindexado 79_00 no es causa suficiente: el colapso 2 ocurrio sin el. Otro reindexado igual (68) llego a 15 GB disponibles y termino bien.
- Las 5 s de telemetria se cortan antes del colapso (el sampler se estrangula): no hay RSS por proceso dentro de la ventana.

## Que falta

1. Un tope de memoria por scope para suites y pushes (la sesion de Declutter propuso MemoryMax=20G sin swap).
2. Captura de los procesos mayores al entrar PSI full >= 10, antes de que el sampler se estrangule.
3. Reproducir con el tope puesto.
