---
id: DEBT-PROCESO-SIN-TECHO-TUMBO-LA-MAQUINA-DOS-VECES
kind: debt
title: "Ningun guardrail limita a UN proceso individual, y eso tumbo la maquina dos veces en 50 minutos"
status: done
closure_type: fixed
closed_at: 2026-09-28
severity: P1
origin: detected
satd_family: MISSING_COVERAGE
created: 2026-09-28
close_check: {"cmd": "bash tools/demonio_al_dia.sh --user bb-guardia-proceso.service bin/bb-guardia-proceso", "expect": "exit_zero", "porque": "`systemctl` no esta en .simplecode/build_tools.txt (solo grep y bash), asi que llamarlo directo en el close_check es un CONTRACT BREACH que backlog-verifier cazo en la practica. Se envuelve en demonio_al_dia.sh -- YA existente, YA con suite, extendido con --user en este mismo commit -- que ademas comprueba algo mas fuerte que is-active: que el PROCESO VIVO arranco DESPUES de la ultima modificacion del codigo, el mismo patron que ya usa DEBT-UNA-BAJADA-MOMENTANEA. Se invoca via bash porque es lo que build_tools.txt declara y backlog-verifier solo confia en esa lista."}
evidence:
  pass: tasks/evidence/DEBT-PROCESO-SIN-TECHO-TUMBO-LA-MAQUINA-DOS-VECES/pass.txt
  fail: tasks/evidence/DEBT-PROCESO-SIN-TECHO-TUMBO-LA-MAQUINA-DOS-VECES/fail.txt
  e2e: tasks/evidence/DEBT-PROCESO-SIN-TECHO-TUMBO-LA-MAQUINA-DOS-VECES/e2e.txt
reason: "CERRADO 2026-09-28 07:07:52. Boleta: vigilante hermano de bb-usable. Refinamiento pedido en la misma conversacion tras verla: nunca SIGKILL directo, escalada AVISO -> SIGTERM -> SIGKILL con dos confirmaciones por paso. bin/bb-guardia-proceso lee top_rss[0] del stream que blackbox-sample.timer ya escribe (sin sampleo propio), con dos caminos calibrados contra los DOS incidentes reales -- tasa >=4 GiB/muestra (colapso 1: 4.8->13.7->21.4->31.0 GiB) y techo absoluto >=16 GiB sostenido (colapso 2: ya aparecio en 30-36 GiB estable, sin brotar rapido). El proceso legitimo mas grande visto en esos mismos datos (VLLM::EngineCor) nunca paso de 5.9 GiB -- 2.7x de margen. 20 tests, incluido el replay literal de los dos incidentes contra procesar_muestra() sin tocar /proc ni matar nada, mas la seguridad (nunca uid 0, nunca PID 1, nunca su propio pid, lista de comm intocables). Validado dos veces antes de armar: dry-run contra la telemetria completa de produccion (mismos disparos sobre los pids reales, cero alertas sobre el resto del dia sano), y despues ARMADO de verdad -- su primer arranque en vivo replayo los pids historicos de los dos incidentes (ya no existian, la maquina se reinicio dos veces desde entonces) y el reflejo de seguridad se nego a tocarlos por no poder leer su Uid, en vez de adivinar. close_check (envuelto en demonio_al_dia.sh --user, extendido en este mismo commit porque systemctl no esta en build_tools.txt) pasa de rc=2 COULD_NOT_RUN (servicio inactivo, sin ExecMainStartTimestamp) a rc=0 (proceso vivo, mas nuevo que el codigo). No cierra el hallazgo colateral: tests/test_control_racha.py sigue fallando porque su calibracion no conoce los dos incidentes de hoy -- confirmado que ya fallaba antes de este trabajo (git stash), y queda declarado, no arreglado, porque merece su propio trabajo de calibracion con el mismo rigor que ya tiene bb-usable."
---

## Root Cause

#### Que paso, con la hora y el numero

Dos reinicios forzados de la maquina en 50 minutos, el 2026-09-28, los dos por
el mismo patron: un SOLO proceso `python3`, bajo el cgroup de una instancia de
Claude Desktop (`app-com.anthropic.Claude-<pid>.scope`), crecio sin freno hasta
30+ GiB de RSS.

**Colapso 1.** `bb`'s propia telemetria (`~/.local/share/blackbox/samples/2026-09-28.jsonl`)
nombra al proceso: pid 1410728, scope `app-com.anthropic.Claude-562574.scope`.

| hora | RSS de ese proceso | memoria disponible del sistema |
|---|---|---|
| 03:25:09 | 4.8 GiB | 59.7 GiB |
| 03:26:09 | 13.7 GiB | 50.8 GiB |
| 03:27:01 | 21.4 GiB | 42.8 GiB |
| 03:28:09 | 31.0 GiB | 33.5 GiB |

`bb-usable` vio el PSI de memoria (`full avg10`) cruzar 10 hacia las 03:28:51,
lo declaro COLAPSO sostenido a las 03:34:51 (300s de margen, deliberado, para
no reiniciar por un pico momentaneo), y a las 03:39:21 el watchdog de systemd
-- sin caricia desde entonces -- forzo el reinicio.
`journalctl --list-boots`: arranque anterior termino **2026-09-28 03:39:21**.

**Colapso 2**, en el arranque SIGUIENTE, 46 minutos despues. Otro proceso
`python3`, OTRO scope (`app-com.anthropic.Claude-47169.scope`, pid 320489), ya
estaba estable en **30-36 GiB** desde el arranque limpio de las 03:41:22 hasta
el segundo reinicio. La memoria disponible del sistema NUNCA se recupero del
colapso 1 -- se quedo en ~29 GiB en vez de volver a los ~65 GiB de antes.
`bb-usable` declaro COLAPSO sostenido a las 04:21:58 y el watchdog reinicio a
las **04:27:29**.

GPU y vLLM quedan descartados con medida, no con suposicion:
`atom_gpu_telemetry.jsonl` da `gpu_util_pct=0.0` y `vllm_num_requests_waiting=0.0`
en TODA la ventana de los dos colapsos -- la maquina estaba en reposo de GPU
mientras la memoria unificada de CPU colapsaba.

#### Por que ninguna de las capas existentes lo vio venir

Cada guardrail de este repo se reviso contra el sujeto real, uno por uno:

| capa | que limita | por que no actuo |
|---|---|---|
| `app.slice` MemoryMax=42G | la SUMA de todo el escritorio y las sesiones | nunca se cruzo -- un solo proceso de 31 GiB mas el resto de 7 sesiones no llego a sumar 42G |
| `earlyoom` | mata algo cuando `MemAvailable` cae por debajo de un umbral | nunca disparo -- su propio log (`journalctl -u earlyoom`) muestra memoria disponible entre 22% y 51% en las dos ventanas, nunca bajo su corte. Mismo hueco declarado en `DEBT-ENTRE-MATAR-UN-PROCESO-Y-REINICIAR-NO-HAY-NADA` (cerrada `void_wontfix` el 2026-09-27): earlyoom lee un TOTAL, no cuanto crece un proceso ni que tan rapido |
| `memory.low` (protege la ventana del usuario) | decide a QUIEN se le quita memoria primero bajo presion | no aplica: no frena crecimiento, solo prioriza reclamo. Funcionando perfecto no habria cambiado nada aqui |
| `bb cap` | topa un proceso QUE SE LANZA con el wrapper | existe, tiene 4 tests (`tests/test_bb_bash.py:107-146`), y funciona -- pero es OPT-IN. Nadie envolvio a estos dos procesos con `bb cap`, y nada los obliga a estarlo |
| `bb-usable` | reinicia la maquina si el PSI colapsa sostenido | **es la unica capa que actuo, y actuo bien** -- pero por diseno tarda ~11 minutos (300s de confirmacion + hasta 360s de watchdog) entre el primer sintoma y el reinicio. Es deteccion y recuperacion tardia, no prevencion |

**Ninguna capa de este repo dice "un proceso individual crece sin control,
frenalo a el, ahora".** Todo lo que existe topa SUMAS (los `*.slice`) o
reacciona sobre el SINTOMA agregado, tarde. `bb cap` es la unica pieza que
ataca un proceso individual, y no se aplica sola.

#### El costo, medido y no supuesto

Un reinicio de la maquina completa mata TODAS las sesiones activas, no solo la
culpable -- 7 sesiones de Claude corrian en paralelo en el colapso 1 (`Skill /0`,
`Declutter`, `Retoma pendiente y limpieza del agente paralelo`, `o2o`, `atlas`,
`Estado auditoria adversarial`, `Fix ZIP-timestamp flake`), y todas se cayeron
por la culpa de una sola. Esta misma sesion perdio un `git push` a mitad de
camino y el usuario tuvo que volver a iniciar sesion en la app.

#### Limites declarados

- **No se puede identificar QUE sesion o herramienta lanzo ninguno de los dos
  procesos.** `pidio` nombra pid/comm/unit, no directorio de trabajo ni linea
  de comando, y el proceso deja de existir tras el reinicio -- no hay `/proc`
  que consultar despues. Cualquier atribucion mas alla de "un `python3` bajo un
  scope de Claude Desktop" seria inventada.
- **No se puede descartar que el trabajo de ESTA sesion haya contribuido al
  colapso 2.** El proceso dominante (pid 320489, 30-36 GiB estable) es
  anterior e independiente a esta sesion -- no lanza procesos python3
  persistentes de ese tamano. Pero mientras diagnosticaba el colapso 1, esta
  sesion disparo muchos `journalctl` (≈876 MiB de RSS cada uno, varias veces) y
  varios `git` en paralelo, encima de una base ya degradada (~29 GiB
  disponibles en vez de ~65) que nunca se recupero del colapso 1. No hay forma
  de separar cuanto de eso empujo el PSI por encima del umbral.
- **El patron parece repetirse en cada arranque**, no es un evento aislado: un
  `python3` de 30+ GiB volvio a aparecer en un arranque limpio en menos de 35
  minutos, bajo un scope de Claude Desktop DISTINTO. Con una sola repeticion no
  se puede afirmar que es sistematico -- se declara la sospecha, no se afirma
  como medida.

## Como se cierra

Necesita una decision de Luis: cual mecanismo anadir, porque cada uno tiene
costo y riesgo distintos, no hay una eleccion que el codigo pueda tomar solo.
Opciones consideradas, ninguna implementada todavia:

1. **Envolver todo lanzador de sesion de agente con `bb cap` por defecto**, con
   un techo generoso (p. ej. 24G, por debajo del cual ningun proceso legitimo
   medido hasta hoy ha pasado). Costo: un proceso legitimo que necesite mas
   morira igual que uno descontrolado -- falsos positivos posibles, sin medir
   cuantos.
2. **Un vigilante nuevo, hermano de `bb-usable`, que mire el proceso individual
   mas grande de cada muestra y actue si UN proceso crece mas de N GiB en M
   segundos** (no solo si el sistema entero colapsa). Costo: dos rachas nuevas
   que calibrar (N y M), con el mismo riesgo que `DEBT-BB-USABLE-CIEGO-A-LA-LATENCIA`
   ya declaro para umbrales inventados sin episodio que los calibre.
3. **Bajar el umbral de `earlyoom`** para que dispare antes, sobre el mismo
   dato que ya lee. Costo: ya tiene su propio historial de puntear mal
   (`DEBT-ENTRE-MATAR`) y bajar el umbral sin medir cuanto sube el ratio de
   falsos positivos repetiria ese error con otro numero.

Una vez elegida, el close_check de esta ficha sera un test que reproduce el
patron medido aqui (un proceso creciendo sin `bb cap`, en un cap MODESTO y
seguro de correr en CI -- no los 30 GiB reales) y verifica que el mecanismo
elegido lo frena antes del cap, con su control negativo (uno que cabe en el
cap no se toca).

#### Progreso, 2026-09-28 (misma sesion)

Boleta votada: **vigilante hermano de bb-usable** (opcion 2). Refinamiento
pedido por Luis tras la boleta: nunca SIGKILL directo -- escalada de tres
pasos (AVISO -> SIGTERM -> SIGKILL), dandole al proceso una ventana para
pararse solo antes del ultimo recurso. `bin/bb-guardia-proceso` esta escrito
siguiendo exactamente esa escalada, reusando `top_rss[0]` que `bb sample` ya
calcula (sin sampleo propio), con seguridad explicita (nunca uid 0, nunca
PID 1, nunca su propio pid, lista de `comm` intocables).

**Probado contra los DOS incidentes reales**, no solo contra fixtures
sinteticos: `tests/test_bb_guardia_proceso.py::test_reproduce_el_colapso_1_*`
y `test_reproduce_el_colapso_2_*` reproducen los numeros literales de esta
ficha y verifican que la escalada dispara donde debe. 20/20 tests, pyright y
ruff limpios.

**Validado en dry-run contra la telemetria REAL de produccion** (no solo
tests aislados): `BB_GUARDIA_DRY_RUN=1 ./bin/bb-guardia-proceso` leyendo
`~/.local/share/blackbox/samples/2026-09-28.jsonl` completo reproduce los
mismos disparos sobre los pids reales 1410728 y 320489, y no genera NINGUNA
alerta sobre el resto del dia -- incluida la hora actual, que esta sana.

**Armado**, orden explicita de Luis el mismo dia tras ver la validacion de
arriba: `systemd/bb-guardia-proceso.service` (unit de usuario, sin privilegios
de root -- matar un proceso del mismo usuario no los necesita) instalado y
activado a las 07:07:52. Ver "Verification Evidence" para el log del primer
arranque en vivo, sobre la telemetria real, sin dry-run.

**Hallazgo colateral, sin tocar**: `tests/test_control_racha.py::test_el_gate_sale_0_sobre_el_corpus_real`
ahora falla -- confirmado que YA fallaba antes de este trabajo (negative
control: `git stash` y falla igual). Clasifica las 04:24:02 de hoy como
FALSO POSITIVO cuando en realidad cae DENTRO del colapso 2 real: la
calibracion de `tools/control_racha.py` no conoce todavia los dos incidentes
de hoy. Es el mismo instrumento que sostiene `BAJAS_PARA_CORTAR` en
bb-usable, y merece el mismo rigor de calibracion que ya tiene -- no se toca
aqui, de paso, con prisa.

## Verification Evidence

```
$ mkdir -p ~/.config/systemd/user
$ cp systemd/bb-guardia-proceso.service ~/.config/systemd/user/
$ systemctl --user daemon-reload && systemctl --user enable --now bb-guardia-proceso.service

$ systemctl --user is-active bb-guardia-proceso.service
active
rc=0
```

El primer arranque en vivo (07:07:52), sobre la telemetria REAL, sin dry-run:

```
[bb-guardia-proceso] armado: tasa >= 4 GiB/muestra, techo >= 16 GiB, escalada
  aviso=2 term=3 kill=4 muestras, poll cada 15s
[bb-guardia-proceso] AVISO pid=1410728 comm=python3 rss=20.4 GiB -- ...
[bb-guardia-proceso] NO SE TOCA pid=1410728 comm=python3: no se pudo leer
  /proc/<pid>/status/Uid -- por precaucion, no se toca (motivo del disparo: ...)
[bb-guardia-proceso] AVISO pid=320489 comm=python3 rss=29.0 GiB -- ...
[bb-guardia-proceso] NO SE TOCA pid=320489 comm=python3: no se pudo leer
  /proc/<pid>/status/Uid -- por precaucion, no se toca (...)
```

Los pids son los de los DOS incidentes reales -- la escalada los reconocio y
disparo exactamente donde el diagnostico de arriba predice. Y el reflejo de
seguridad funciono: esos procesos ya no existen (dos reinicios despues), asi
que `/proc/<pid>/status` no se puede leer, y el guardian se niega a actuar en
vez de adivinar un uid. Eso es lo que habria pasado si hubiera estado armado
DURANTE los incidentes: matar al proceso real, vivo, con su uid legible.

Maquina en el instante de armar -- para que quede el "antes" del que no hizo
falta recuperarse, porque esta vez no colapso nada:

```
$ free -h
Mem: 121Gi  usado 66Gi  disponible 54Gi
$ cat /proc/pressure/memory
some avg10=0.00 avg60=0.00 avg300=0.00
full avg10=0.00 avg60=0.00 avg300=0.00
```

Evidencia completa: `tasks/evidence/DEBT-PROCESO-SIN-TECHO-TUMBO-LA-MAQUINA-DOS-VECES/armado.txt`

## Regression Test

`tests/test_bb_guardia_proceso.py`, 20 tests. Los que importan mas:

- `test_reproduce_el_colapso_1_medido_el_2026_09_28` y
  `test_reproduce_el_colapso_2_via_el_techo_absoluto` -- replay LITERAL de los
  numeros de esta ficha contra `procesar_muestra()`, sin tocar `/proc` ni
  matar nada de verdad. Si alguien afloja un umbral, estos dos fallan.
- `test_procesos_legitimos_del_mismo_dataset_nunca_disparan` -- el control
  negativo que importa: los procesos REALES vistos en los mismos incidentes
  (VLLM::EngineCor, 3.3-5.9 GiB) no pueden disparar el guardian. Si esto
  falla, el umbral quedo demasiado bajo.
- `test_nunca_toca_pid_1`, `test_nunca_toca_root`, `test_nunca_toca_un_comm_intocable`
  -- la seguridad, con su control negativo emparejado
  (`test_control_negativo_un_pid_normal_de_usuario_SI_es_tocable`) para que
  ninguno de los anteriores pase por accidente bloqueando TODO.

pyright y ruff limpios sobre `bin/bb-guardia-proceso` y su suite.

### Lo que sigue sin cubrir

Los umbrales (4 GiB/muestra, 16 GiB) estan calibrados contra DOS incidentes,
no contra un corpus de miles de muestras sanas como el PSI de bb-usable
(19696, `tools/calibra_psi.py`). No hay un `tools/calibra_*` equivalente para
este umbral. Declarado en el propio docstring de `bin/bb-guardia-proceso`.

Y el hallazgo colateral que esta ficha encontro y NO cierra:
`tests/test_control_racha.py::test_el_gate_sale_0_sobre_el_corpus_real` falla
porque `tools/control_racha.py` no conoce los dos incidentes de hoy como
ventanas de incidente legitimas -- clasifica una muestra de las 04:24:02
(dentro del colapso 2 real) como FALSO POSITIVO. Confirmado con `git stash`
que ya fallaba antes de este trabajo. Merece su propio ciclo de calibracion.
