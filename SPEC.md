---
spec_version: 2
id: blackbox
kind: tool
owner: lcasarin-maker (GitHub)
runtime: {lang: bash, version: "5.2+"}
scaffold: {name: simplecode, mode: vendored}
debt: tasks/
gate_level: legacy-baseline
---

<!-- El corpus de deuda es `tasks/`. Sin esta declaracion, `ship-freeze` bloqueo
     el push del 2026-09-08 con COULD_NOT_RUN: no podia leer si habia deuda
     abierta, y un corpus que el gate no puede abrir no es un corpus vacio. -->

# SPEC.md - blackbox

## 0. Objective

**Mission**: Prevenir y resolver los crashes y hangs de esta máquina, preservar
su usabilidad y recuperar el servicio cuando falle. La captura forense y la
comprobación de instrumentos permiten encontrar causas, elegir correcciones y
verificar que funcionan; son parte del esfuerzo preventivo y correctivo.

Este objetivo guía el trabajo pendiente. Cada capacidad de protección se
declara con su alcance y evidencia: un presupuesto firmado registra una
política, un límite protege las asignaciones que efectivamente controla y un
watchdog aporta recuperación. La eficacia de cada mecanismo requiere prueba.

## Purpose

Protección, diagnóstico y resolución de fallos de la AI TOP ATOM (NVIDIA GB10,
20 núcleos aarch64, 121 GB de memoria unificada). Reutiliza los mecanismos de la
plataforma y las fuentes existentes; añade los controles y registros que hagan
falta y declara qué comprobación no pudo correr.

Nace del incidente del 2026-09-07: la app de escritorio de Claude quedó colgada
con el proceso vivo, la ventana en pantalla y cero renderizadores. El
diagnóstico descartó OOM, segfault, throttle y térmica, y **no llegó a causa
raíz**, porque `ulimit -c` era 0 y `systemd-coredump` no estaba instalado. Nace
como respuesta a crashes y hangs para prevenir su repetición y solucionarlos;
ese primer hueco de evidencia determinó el comienzo de la implementación.

## Why now

La instrumentación de la máquina existía pero estaba repartida y sin repo: los
scripts de `/srv/ai/gpu_governance/` no estaban versionados en ningún sitio, y
nadie sabía qué instrumento estaba vivo. El 2026-09-08 se midió que `sar` llevaba
días recolectando mientras su variable `ENABLED` decía `false`, y que la
telemetría térmica llevaba 47 minutos muerta sin que nada lo reportara.

## Who is the user

El dueño de la máquina (el maintainer del repo), y las sesiones de agente que
trabajan en ella y compiten por su memoria unificada.

## In scope

- Prevención y corrección de crashes, hangs y agotamiento de recursos mediante
  contención, presupuestos de admisión, configuración de kernel y runtime,
  ajustes de cargas y correcciones de drivers o firmware cuando corresponda.
  Incluye investigar y proponer parches, fixes y recomendaciones externas,
  contrastándolos con el código y la máquina antes de adoptarlos.
- Cada propuesta preventiva o correctiva especifica el fallo que aborda,
  versiones y OEM compatibles, evidencia y grado de certeza, riesgos,
  validación y rollback. Las intervenciones automáticas tienen blancos,
  disparadores y recuperación explícitos. Las pruebas distinguen prevención,
  mitigación, diagnóstico y recuperación, y registran fallos de colección.
- Muestreo de lo no cubierto: renderizadores por app Electron, zombis, PSI,
  linaje de procesos (unit de cgroup), estado del motor de inferencia.
- Informe forense por ventana temporal (`bb scan`) que cruza todas las fuentes,
  incluyendo Xid de GPU, xHCI/USB, PCIe (energía insuficiente, AER/RxErr),
  reloj/pstate cruzado contra throttle, fallback silencioso de GPU a CPU,
  volcados de kernel (kdump) y un boot anterior colgado en GDM.
- Inventario de qué instrumento está armado (`bb status`), incluido kdump.
- Captura de core dumps y protección en caliente de procesos ya arrancados.
- Custodia de la instrumentación adoptada, con detección de divergencia.
- `tools/check_harvest_accepted.py`: close_check reutilizable de las fichas de
  evaluación de mecanismos cosechados por Atlas, con su suite en `tests/` y
  controles de evidencia por mecanismo. Los inventarios siguientes describen
  también las otras herramientas Python del repo.

- **Actuar sobre lo que mide, donde la inacción cuesta la máquina entera.** Esto
  dejó de estar fuera de alcance el 2026-09-23/24, después de cuatro
  congelamientos: `bb-usable` retira el latido del watchdog ante presión
  sostenida y systemd reinicia (medido: 2026-09-24 14:09:38, 10 min 34 s desde
  el inicio del colapso, sin nadie delante); `bb cap` lanza con techo de
  memoria; los techos de `app.slice` y `docker.slice` contienen memoria
  contabilizada por sus cgroups. La cobertura de asignaciones CUDA se investiga
  en `FEATURE-1358-CGROUP-*`: el hueco medido impide extender esa protección a
  toda la memoria unificada. `bb protect` es una de las capas existentes.
- Custodia de la instrumentación de la máquina relativa a **monitoreo y cuelgue**,
  venga de donde venga. Ver "Inventario de propiedad".

## Out of scope

- Interfaz gráfica o dashboard: esto se lee desde una terminal o desde un agente.
- Administración general de una flota: el sujeto protegido es esta unidad.
  La captura externa y las sondas de servicio complementan su protección.
- Reparación genérica de aplicaciones ajenas al objetivo de crashes, hangs y
  usabilidad; cada intervención de BB responde a un fallo dentro de ese alcance.
- Duplicar fuentes o mecanismos que ya cubren el problema. La telemetría de GPU
  y térmica adoptada vive en `tools/atom_gpu_telemetry.py` de este repo; Atlas
  consume su salida según el contrato siguiente.

## Contrato con Atlas

Decidido por el dueno el 2026-09-24, y es la frontera que gobierna los dos repos:

| | **blackbox** | **Atlas** |
| --- | --- | --- |
| que es | el comportamiento **fisico** de la ATOM | la **KB**, y el encolador de trabajo que sale de ella |
| como corre | **100 % automatico** -- timers y unidades, sin nadie delante | encola y drena trabajos; puede **llamar a `bb` a mano** cuando lo necesite |
| telemetria | la **produce** | la **consume** |

De ahi salen tres reglas operativas:

1. **Atlas no importa codigo de blackbox, ni al reves.** Consume su salida:
   el jsonl que escribe `tools/atom_gpu_telemetry.py`, en
   `$BLACKBOX_DATA/atom_gpu_telemetry.jsonl`. Un import cruzado seria un
   acoplamiento con forma de frontera.
2. **Blackbox gobierna el estado físico y expone telemetría y gates.**
   Atlas consulta esos resultados y conserva la política de admisión de trabajos.
   Lo que produce conocimiento vive en Atlas, aunque lea del hardware --
   por eso `tools/detect_atom_crash.py` se queda alli: importa
   `tools.durable_log` y escribe dictamenes en `docs/agent_findings/`.
   Excepcion hallada Y CERRADA el mismo dia: `Atlas/tools/instalar_earlyoom.sh`
   decidia `/etc/default/earlyoom` desde el otro lado de la frontera,
   divergiendo de lo que `enable-privileged.sh` despliega de verdad --
   hallado por la auditoria H1 del 2026-09-28, no investigado aqui porque
   Atlas no es alcance de esta sesion, pero resuelto alla horas despues
   (Atlas `DGX-604`, mergeado a master en `ec9b4288a`): el script vive ahora
   en `tools/_retired/`, y la colision de id con la otra `DGX-600` quedo
   renumerada.
3. **Las unidades de usuario que Blackbox instala pueden arrancar sin sesión
   interactiva.** `enable-privileged.sh` activa `linger` para el dueño. Las
   unidades de sistema arrancan bajo systemd; la comprobación del arranque
   completo requiere observar la máquina sin sesión interactiva.

### Por que la frontera estaba al reves

`DGX-483` (Atlas, cerrada el 2026-09-13) dejo escrito que "Atlas conserva
`tools/atom_gpu_telemetry.py`", justificandolo en que esa herramienta y
`detect_atom_crash.py` **importan `tools.durable_log` y `tools.tool_limits`**.

Medido el 2026-09-24 contra el fichero de ese mismo dia (commit `66fb9e57`):
`atom_gpu_telemetry.py` importaba **solo** `tools.nightly_kb_consolidation._argv_tokens`,
8 lineas. Nunca importo ninguno de los dos. La razon era cierta para
`detect_atom_crash.py` y se **generalizo sin medirla** al otro fichero.

El traspaso es `DGX-585` en Atlas.

## Inventario de funciones

Lo que este repo EJECUTA. Una fila por pieza; si no está aquí, no existe para
efectos de esta spec, y `tools/inventario.py --check` lo bloquea en el commit.

| pieza | qué hace | qué la verifica |
| --- | --- | --- |
| `bb sample` | una muestra de lo que ninguna otra fuente cubre: renderizadores por app Electron, zombis, PSI, `Committed_AS`, crecimiento de `VmSize` por proceso | `tests/test_bb_bash.py` |
| `bb snapshot [razón]` | volcado forense completo AHORA: `/proc`, journal, `lsmod` de nvidia, estado de GDM | `tests/test_bb_bash.py` |
| `bb scan ["hace X"]` | informe desde el inicio solicitado hasta ahora; filtra JSONL por timestamps, valida registros y conserva `could_not_run` para datos corruptos, faltantes o análisis fallidos | `tests/test_bb_bash.py` + `tests/test_auditoria_bb_regresiones.py` |
| `bb hw` | inventario de hardware y de los límites aplicados | `bash -n` |
| `bb recovery` | Consulta readonly de RCU, watchdog y pstore, devuelve 2 cuando hay `could_not_run` | `tests/test_recovery_profile.py` |
| `bb status` | qué instrumento está armado y cuál no, por sus DATOS donde hay artefacto | `tests/test_bb_bash.py` |
| `bb drift` | compara los 41 sujetos adoptados contra la máquina; distingue igual, divergente, ausente, suspendido y suspensión vencida. Hasta el 2026-09-28 volvía `return 0` sin condición pase lo que pase, y ningún hook ni timer lo llamaba nunca — divergente y ausente sólo se veían si alguien corría el comando a mano. Ahora sale distinto de 0 si diverge o falta algo (suspendido vigente no cuenta), y corre solo una vez al día vía `blackbox-drift.timer` | `tests/test_bb_bash.py` (`BLACKBOX_DRIFT_ROOT` aísla el repo/máquina de mentira de los 41 sujetos reales; control negativo corrido contra el `return 0` de antes: 3 de 5 tests fallan) |
| `bb protect` | sube el límite de core de procesos YA corriendo (`prlimit`) | `bash -n` |
| `bb who [pid]` | qué procesos pesan y QUIÉN los lanzó: unit de cgroup, padre, cwd | `tests/test_bb_bash.py` |
| `bb status_clock_lock` (`bb status clock lock`) | verifica declaración y confirmación del rango GPU tras iniciar la unit en el boot actual | `tests/test_1358_servicio_clock.py` |
| `bb sigterm ["hace X"]` | quién mandó SIGTERM/SIGKILL a quién, desde el registro de auditoría (DEBT-DGX-438). Lee el anillo COMPLETO (`audit.log*`, 5 ficheros) y **declara la ventana que ese anillo cubre**, con `could_not_run` cuando se le pide más — hasta el 2026-09-27 leía sólo `audit.log` y veía 10.1 min de las 76 h que llevaba armado. La víctima sale de `a0` del SYSCALL, en hexadecimal: `auditd` no emite `type=OBJ_PID` para estas reglas (0 en todo el anillo contra 307 SYSCALL con la clave), así que esa columna estaba vacía por construcción | `tests/test_bb_bash.py`, 6 tests nuevos el 2026-09-27, con el control negativo del aviso de ventana |
| `bb cap <GB> <cmd...>` | lanza un proceso con techo de memoria propio, aplicado por el kernel vía `systemd-run --user --scope` | `tests/test_bb_bash.py` |
| `bb install` | instala los timers de usuario: muestreo cada minuto y `bb drift` una vez al día | `bash -n` |
| `bin/bb-usable` | vigila si la máquina SIRVE, no si systemd vive: ante PSI `full avg10 >= 10` sostenido 300 s, retira el latido del watchdog y systemd reinicia. Una sola sonda baja no corta la racha; hacen falta dos. PSI ilegible antes del umbral conserva el latido; después de declarar colapso lo mantiene retirado hasta poder confirmar recuperación. | `tests/test_bb_usable.py` + `tests/test_auditoria_bb_regresiones.py`; dos pruebas de socket requieren un entorno que permita bind Unix |
| `bin/bb-guardia-proceso` | frena a UN proceso individual, sin esperar a que el sistema entero colapse: lee `top_rss[0]` del mismo stream que `blackbox-sample.timer` ya escribe (sin sampleo propio) y, si crece ≥ 4 GiB entre muestras o supera 16 GiB sostenido, escala AVISO → SIGTERM → SIGKILL. El lector nuevo ignora el contenido que ya existía al conectarse, procesa como máximo una muestra nueva por sondeo, y exige fecha reciente, boot actual y `starttime_ticks` coincidente antes de evaluar; revalida starttime antes de enviar una señal. `bin/bb sample` añade boot id y starttime a la telemetría. Nace de DEBT-PROCESO-SIN-TECHO-TUMBO-LA-MAQUINA-DOS-VECES: dos reinicios forzados el 2026-09-28 (03:39:21 y 04:27:29). El servicio se confirmó activo el 2026-09-28 07:07:52; el cambio nuevo aún requiere despliegue y verificación. | `tests/test_bb_guardia_proceso.py` y `tests/test_auditoria_bb_regresiones.py` |
| `bin/bb-parada-diagnostico` | se ejecuta desde `ExecStopPost` de una unit de usuario al detenerse. Escribe en `$BLACKBOX_DATA/paradas.log` el journal de la unit de los últimos 3 min, las llamadas kill/tgkill con SIGTERM o SIGKILL de la regla audit `senales_procesos` (últimos 10 min) y los OOM o kill del kernel. Sale 0 siempre: un diagnóstico no cambia la parada | `bash -n`, y prueba manual con una unit de prueba: escribe el bloque en `paradas.log` |
| `bin/bb-vigilante-motor` | absorbido de Declutter (DECL-CORE-322) el 2026-10-10. Cada 2 min (`ai-nemotron-vigilante.timer`) prueba una llamada minima de chat al motor local; tras 3 fallos seguidos reinicia `ai-nemotron.service`, salvo en los 600 s tras un arranque. Cubre lo que systemd no ve: unidad activa y `/v1/models` en 200 con el chat mudo (medido 2026-10-09: 3.5 h). Escribe `vigilante_motor.log`; `bb scan` cuenta sus `REINICIA` como cuelgues. No tiene presupuesto de reinicios: un cuelgue persistente lo reinicia cada ~8 min | `tests/test_bb_vigilante_motor.py` |
| `tools/motor_caidas.py` | causas de las caidas del motor local para `bb scan`: une cada caida fatal del EngineCore con su clase de error CUDA, los Xid del kernel en +-30 s, los cuelgues del vigilante y los volcados CUDA `vllm_*` (a los tres ultimos les corre `cuda-gdb`). Nombra lo ocurrido, no atribuye causa; la causa sigue abierta en `DEBT-MOTOR-LLM-CAIDAS-CUDA-SIN-CAUSA-01` | `tests/test_motor_caidas.py` |
| `bb sample` → `$BLACKBOX_DATA/sigterm.jsonl` | acumula las señales capturadas FUERA del anillo de auditoría, que en esta caja retiene 127 min mientras el instrumento lleva días armado. Una pasada por muestra (60 s) contra un anillo de 127 min es holgura de 127x; la marca de agua del último `ts.serial` evita reescribir en cada muestra | control negativo corrido: segunda pasada sobre el mismo anillo, 53 → 53 filas, 0 nuevas; 0 ids duplicados |
| `tools/nombra_victimas.py` | le pone NOMBRE a las víctimas de las señales que `bb sample` acumula, cruzando su pid contra `top_rss`/`pidio`/`cpu_top`/`gpu` de las muestras — `auditd` no emite `type=OBJ_PID` para estas reglas y el proceso ya murió cuando se lee el registro. Separa **autolimpieza** (la víctima es el padre del emisor) de **atribución incompleta** (el emisor es `kill`/`pkill`, que es el utensilio y no quien decidió) del sujeto real de DEBT-DGX-438 | `tests/test_nombra_victimas.py`, 24 tests, **100 %** de 121 sentencias. Su primera versión atribuía por nombre y reportó 12 capturas de `rustdesk` limpiando sus hijos como sujeto de la ficha; el arreglo fue capturar `ppid`, no una heurística mejor |
| `tools/calibra_latencia_x.py` | calibra el corte de latencia del escritorio contra episodios ETIQUETADOS por una persona (`bb snapshot "...no responde"`), no contra «muestras con latencia alta» — que es lo que parece la respuesta y depende del umbral que uno elija. Sirve a DEBT-SLUGGISH y a DEBT-BB-USABLE-CIEGO con un solo número | tres salidas corridas: rc=0 CALIBRADO, rc=1 ninguna combinación separa, rc=2 `COULD_NOT_RUN` sin etiqueta — hoy sale 2. `tests/test_calibra_latencia_x.py`, 23 tests, **100 %** de 129 sentencias |
| `tools/calibra_psi.py` | re-deriva los cortes de PSI contra los cuatro incidentes propios y sale 1 si dejan pasar uno o disparan en una muestra sana | su propio veredicto `CALIBRADO` |
| `tools/control_racha.py` | control de FALSOS POSITIVOS de la regla de racha de `bb-usable`: mide el máximo tiempo sostenido que la regla acumula FUERA de toda ventana de incidente conocida, y sale 1 si llega al corte de acción | control negativo: `--corte 180` mete la excursión sana más larga y sale 1. `tests/test_control_racha.py` |
| `tools/demonio_al_dia.sh` | comprueba que el PROCESO VIVO de una unit arrancó después de la última modificación de su código — código correcto en disco con el defecto en memoria es el estado en que la máquina murió el 2026-09-26 | `tests/test_demonio_al_dia.py`, los tres veredictos corridos: 0 al día, 1 viejo, 2 `COULD_NOT_RUN` |
| `tools/check_harvest_accepted.py` | `close_check` reutilizable de las fichas HARVEST | `tests/`, 100% de cobertura |
| `tools/config_entregable.sh` | falla si un fichero de `adopted/system-config/` no lo instala ningún script ni está declarado solo-registro. Un adoptado sin instalador no es configuración: es una fotografía, y editarlo no cambia la máquina — el 2026-09-28 eso dejó los techos comprometiendo 124.1 GiB sobre 121.1, peor que los 121.8 de partida. Cerrado el 2026-09-28: de los 15 sin camino, once se instalan y cuatro están declarados en `adopted/solo-registro.txt` con su motivo medido | `tests/test_config_entregable.py`, 8 tests: los tres veredictos (0 cubierto, 1 hueco nombrándolos, 2 `COULD_NOT_RUN` sin sujeto) y dos que cubren su límite declarado — el comprobador mira si el instalador NOMBRA el fichero, no si lo copia, así que esos dos leen el `--dry-run` real y uno de ellos le quita un `cp` a la salida para comprobar que lo delata |
| `tools/cobertura_bash.sh` | mide qué líneas de un script bash ejecuta una suite (`BASH_ENV` + `BASH_XTRACEFD`), porque `coverage.py` no ve bash | control negativo: suite vacía 0.0%, 3 tests 4.3%, 18 tests 17.6% |
| `tools/status_estable.sh` | falla si el RESUMEN de `bb status` se mueve entre corridas con el sujeto quieto. Vigila la clase, no una fila: cualquier chequeo que se vuelva flaky mueve el resumen. Nació de que `bb status` decía FALTA sobre earlyoom armado por `set -o pipefail` + una tubería a `grep -q` | control negativo corrido contra el código ROTO de verdad (`git show 7e6b011:bin/bb`): 20 corridas, 2 resúmenes distintos, rc=1. Con el arreglo, 8 de 8, rc=0 |
| `tools/piso_cobertura.sh` | trinquete: falla si la cobertura de `bin/bb` baja de `tests/cobertura_bb.piso` | control negativo: con el piso a 99.0 devuelve 1 |
| `tools/verifica_timeout_start.sh` | uso: `[--user] <unit>`. Falla si `TimeoutStartUSec` de una unit oneshot es `infinity` -- sin techo, una sola corrida colgada apaga el instrumento hasta el reinicio (`DEBT-BB-SAMPLE-SIN-TECHO-DE-TIEMPO-SE-QUEDO-COLGADO-EN-EL-COLAPSO`) | close_check de esa ficha, `rc=0` con `blackbox-sample.service` en vivo |
| `tools/verifica_display_en_unit.sh` | uso: `<unit>`. Falla si `Environment` de una unit de sistema no declara `DISPLAY=` -- sin eso, un sondeo que llama a `xset` contra la sesión gráfica devuelve `None` en cada vuelta | leído por `tools/verifica_bb_usable_mide_latencia.sh`; comprueba la DECLARACIÓN, no el comportamiento del proceso vivo (ver el siguiente) |
| `tools/verifica_bb_usable_mide_latencia.sh` | falla si la ÚLTIMA línea real de "latencia del escritorio" en el journal de `bb-usable` sigue diciendo "sin DISPLAY" -- mide COMPORTAMIENTO, no declaración: un `Environment=` nuevo en la unit no llega al proceso ya arrancado hasta que se reinicia, y `systemctl show -p Environment` sólo ve lo primero (`DEBT-BB-USABLE-NUNCA-MIDIO-SU-PROPIA-LATENCIA`) | close_check de esa ficha, `rc=1` hoy porque `bb-usable` sigue sin reiniciarse tras desplegar el arreglo |
| `tools/atom_gpu_telemetry.py` | telemetria de GPU y zonas termicas cada 5 s con PSI de memoria y exportación UDP opcional desactivada por defecto (antes del append local; entrega sin acuse), presupuesto termico con corroboracion, y **mitigacion**: pausa procesos cuando la maquina se calienta con carga real; `--dry-run` imprime la pausa prevista sin enviar señales ni cambiar estado. El servicio persiste boot id, starttime e intención antes de pausar; al reiniciar recupera solo pausas de la misma identidad y reconcilia una interrupción entre señal y confirmación. Traida de Atlas el 2026-09-24 (DGX-585) | `tests/test_atom_gpu_telemetry.py` + `tests/test_atom_gpu_telemetry_bb.py` + `tests/test_mitigacion_solo_con_carga.py` + `tests/test_auditoria_bb_regresiones.py` |
| `tools/service_probe.py` | sonda SSH opcional de loopback con plazo total; `bb sample` registra banner completo, error, timeout o desactivación. Observa respuesta parcial del servicio y no decide reinicios | `tests/test_1358_servicio_clock.py` |
| `tools/hitos_incidente.py` | separa hitos de allocator, PSI, servicio, watchdog, boot y acciones OOMD en journal/muestras aportados; distingue aviso Killed de marca Marked, metadatos contradictorios e inaccesibles, sin autenticar el journal ni atribuir causalidad | `tests/test_1358_hitos_nvrm.py` |
| `tools/scan_samples.py` | lector stdlib de JSONL para `bb scan`: ordena timestamps, recorta al intervalo pedido, separa boots en contadores, y correlaciona fallback GPU solo con solicitudes activas y trabajo CPU del mismo PID/boot; incertidumbre queda en `could_not_run` | `tests/test_auditoria_bb_regresiones.py` |
| `tools/mutacion_alcanza.py` | guarda que el runner de mutación del kit encuentre qué mutar aquí. Llegó vendorizado sin poder resolver un solo test (0 de 9, medido) porque suponía una disposición `src/`; se arregló aguas arriba y esto impide que se pierda en la próxima sincronización | `tests/test_mutacion_alcanza.py`, 23 sentencias al 100 %, con un repo montado a propósito para que NO alcance |
| `tools/presupuesto_memoria.py` | comprueba el presupuesto de memoria en DOS mitades, porque mezclarlas hacia que el criterio no pudiera salir positivo. **Mitad 1, compromisos**: los techos de cada slice (que el kernel aplica) tienen que componer contra el SUELO comprometido de memoria unificada de GPU -- el p95 de la serie, derivado y no elegido: de p50 a p95 se mueve 1.10 GiB sobre 121.1, es una meseta. **Mitad 2, excursion**: el maximo observado (85.4 GiB, un transitorio de 4 min de ocho workers de `pytest-xdist`) tiene que caber en un presupuesto FIRMADO en `tasks/presupuesto_gpu.json`, con `owner`, `expires` y `reason` -- sin firma es ROJO, y no se incluye plantilla porque una plantilla que el gate acepte es el agujero. La ruta CUDA de la medicion historica presento un hueco (7 GiB asignados -> 15 MiB adicionales en memory.current); ese resultado delimita la pila y API ensayadas. El presupuesto firmado es una politica operativa mientras se investiga su contencion | `tests/test_presupuesto_memoria.py`, 39 casos. Seis mutaciones corridas contra el codigo real, de las que DOS no cazaba nadie (volver el suelo al maximo; fijarlo a mano en 50.0): `tasks/evidence/DEBT-TECHOS-SIN-CALIBRAR/controles-negativos-2026-09-25.txt` |
| `tools/calibra_techo_slice.py` | propone el techo de un slice a partir de la serie `slices` que `bb sample` guarda, o se NIEGA diciendo que le falta. Dos frenos: un minimo de 18 944 muestras (PRECEDENTE declarado, el liston que fijo `docker.slice`, no una derivacion) y que el maximo haya DEJADO DE CRECER -- el maximo del ultimo tercio de la ventana contra el de los dos primeros. El segundo es el que de verdad protege: puede decir "todavia no" con 100 000 muestras, porque una serie que aun sube no ha visto el peor caso y un techo puesto ahi se queda corto por construccion. Factor 1.4 por precedente explicito, y se comprueba: sobre `docker` da 11.24 x 1.4 = 15.7 y el techo puesto a mano fue 16G. NO toca la maquina | `tests/test_calibra_techo_slice.py`, 21 casos al 100 %: cada freno en las dos direcciones, mas el que impide que todo pase con un numero fijo (el techo SIGUE al maximo en 2.8->3.9, 5.0->7.0, 11.2->15.7) |
| `tools/inventario.py` | comprueba que estas dos tablas describen el repo y la máquina, no lo que alguien recordaba | él mismo, con `--check` sobre un sujeto mutado |

| `tools/cgroup_repro.py` | arnés acotado para comparar cargos CPU, cudaMalloc, cudaMallocManaged y PyTorch en scopes separados; separa inicialización, asignación tocada y liberación, preservando errores de colección | `tests/test_cgroup_repro.py`; resultados y límites en `tasks/evidence/FEATURE-1358-CGROUP-01-REPRO/` |
| `tools/recovery_profile.py` | `bb recovery`: estado readonly de RCU/watchdog y firmas separadas de pstore; errores contados, sin abrir dispositivos watchdog ni alterar configuración | `tests/test_recovery_profile.py`, controles de permisos/ausencia y archivo vacío |
| `tools/kernel_capture.py` | Captura readonly kernel release/boot/sysctls, firmas pstore y parámetros/targets estáticos o dinámicos de netconsole; confina rutas al root de captura y conserva `could_not_run`. Configuración no demuestra recepción de paquetes ni recuperación, y la lectura pstore no está limitada por tamaño | `tests/test_kernel_capture.py`; `/sys/fs/pstore` denegado en la captura local |
| `tools/memory_profile.py` | Captura páginas/UVM/THP, DGX release declarado, MemAvailable/PSI y comparación de versiones NVIDIA cargada/en disco; preserva ausencia y errores, sin certificar soporte OEM | `tests/test_memory_capture_and_cuda_integrity.py` |
| `tools/recipe_memory.py` | Compara MemAvailable con términos de receta declarados por quien ejecuta; los términos son `caller_supplied_unverified`, faltantes producen unknown, y el registro raw lleva un digest que no autentica la fuente | `tests/test_diagnostic_admission_prototypes.py`; sin admisión ni workload real |
| `tools/thermal_coverage.py` | Inventaría thermal zones, trip points, entradas hwmon de temperatura/fan, identidad OEM disponible, lecturas y errores de enumeración; coverage no determina temperatura segura, soporte OEM ni resultado de soak | `tests/test_diagnostic_admission_prototypes.py`; canales OEM y soak real pendientes |
| `tools/cuda_integrity.py` | Matriz CUDA acotada de readback completo, concurrencia y reutilización en scope temporal | `tests/test_memory_capture_and_cuda_integrity.py` |
| `tools/preflight.py`, `tools/verify_apt_critical_removals.py` | `preflight` clasifica snapshots APT, runtime, GSP, provider, DRM y kernel; el verificador APT contrasta planes capturados y su integridad SHA-256; ninguno instala cambios ni un guard OEM | `tests/test_preflight.py`; `tests/test_debt_registration_controls.py::test_debt_close_check_verify_apt_critical_removals_01` |
| `tools/apt_sources.py` | La captura observa `/etc/apt/sources.list.d/ubuntu.sources`, arquitectura nativa, tuples de `apt-get indextargets` y tuple OTA/kernel/driver; diagnostica la contradicción `archive.ubuntu.com/ubuntu` + `arm64`. Sus evaluadores comparan identidades e índices, integridad Release y frescura bajo política suministrada; la firma se verifica con keyrings explícitas, cuya autorización y compatibilidad OEM requieren evidencia separada | `tests/test_apt_sources.py`; capturas nativas y perfil aprobado pendientes según ficha |
| `tools/host_diagnostics.py` | Captura readonly de sesiones, almacenamiento, red, USB/HID y estado GPU/runtime; relaciona HID con el ancestro USB más cercano y GID con su netdev; serial opcional ausente queda `unknown`, watchdog conserva propietario `UNKNOWN` sin abrir su dispositivo; registra MTU vía `ip -j link`/sysfs y binding PCI/driver, lee firmware RDMA solo desde sysfs; observa parámetro DRM efectivo y presencia de kernel/initrd para el kernel en ejecución sin inferir bootability; el guard CLI de backup exige mountpoint, source y UUID explícitos y coincidencia exacta de `findmnt`; conexión física sigue UNKNOWN y conserva `could_not_run`; ninguna coincidencia autoriza escribir/restaurar y la revisión no valida admisión, NCCL, hotplug o compatibilidad | `tests/test_host_diagnostics.py`, `tests/test_device_inventory.py`, `tests/test_network_inventory.py`, `tests/test_boot_storage_inventory.py` |
| `tools/runtime_provenance.py` | Lee capturas Prometheus guardadas y conserva nombre, TYPE/HELP observados, etiquetas, valor crudo y timestamp opcional; path suministrado queda como no verificado, muestras/type duplicados e ilegibles conservan incidencias y `could_not_run`. Una lectura observada no valida generación, compatibilidad ni bytes de KV | `tests/test_runtime_provenance.py`; captura Prometheus cruda del runtime pendiente |
| `tools/chat_sse_capture.py` | Lee streams SSE guardados de Chat Completions, conserva chunks/deltas, presencia de `tool_calls`, argumentos parciales, `finish_reason` y `[DONE]`; reconstruye texto por choice y evalúa sintaxis JSON solo con terminación válida, distingue refusal/tool_calls/truncamiento y ofrece resumen con hashes sin contenido; stream sin terminador es captura incompleta de causa desconocida, sin inferir cancelación, estado de parser, progreso interno ni MTP acceptance | `tests/test_chat_sse_capture.py`; captura nativa SSE del runtime pendiente |
| `tools/openclaw_contract.py` | Compara una respuesta guardada GET `/v1/models` con el modelo primario y metadatos explícitos OpenClaw, calcula headroom configurado dentro del límite ligado al checkpoint; presupuesto de petición contrasta headroom y maxTokens configurado, y queda desconocido sin conteo de tokens ligado a modelo/checkpoint; entradas caller-supplied quedan sin autenticar y salida nunca incluye prompts | `tests/test_openclaw_contract.py`; respuesta nativa `/v1/models`, config OpenClaw y observación tokenizada pendiente |
| `tools/nvme_readonly.py` | Clasifica señales NVMe corroboradas separando fail de consultas inaccesibles; exporta solo archivos regulares identificados a otro filesystem, con identidad y SHA-256, sin escribir el origen | `tests/test_nvme_readonly.py`; ensayo con medio NVMe de laboratorio y recuperación de copia pendientes |
| `tools/workload_restart_policy.py` | Presupuesta intentos por identidad de workload en estado atómico y bloqueado entre procesos; rechaza reloj regresado y consultas de estado inaccesibles, sin reiniciar procesos ni atribuir reboot a OOM | `tests/test_workload_restart_containment.py`; integración de runtime y ensayo con reboot recuperable pendientes |
| `tools/netconsole_marker.py` | Clasifica marcador literal presente, parcial al final, ausente o ilegible en un log de receptor suministrado; origen sin autenticar y cierre abierto, sin acreditar entrega, Secure Boot, persistencia ni correlación | `tests/test_netconsole_marker.py`; log nativo del receptor pendiente |
| `tools/verify_cgroup_repro.py` | Recalcula fases, scopes y controles CPU desde stdout crudo del arnés; observaciones incompletas son unknown, sin acreditar contención GPU ni procedencia | `tests/test_verify_cgroup_repro.py`, controles de calibración, fases, scopes y lecturas alteradas |
| `tools/verify_telemetry_dispositions.py` | Exige que cada evento solicitado tenga un estado de disposición válido en el ledger JSONL | `tests/test_verify_telemetry_dispositions.py`, ledger vacío, válido y estado pendiente |
| `tools/read_integrity.py` | Compara hashes buffered/O_DIRECT de una región acotada con digest suministrado; preserva fallos y verifica estabilidad del archivo | `tests/test_read_integrity.py`; caso GX10 conserva validación experimental pendiente |
| `tools/provider_trace.py` | Evalúa selección efectiva de proveedor por petición y transición de worker en JSONL; conserva fallback e incompletitud | `tests/test_provider_trace.py`; fixtures declarados y traza real pendiente |
| `tools/kernel_charges.bt` | Borrador de probes de cargo/descargo kmem 6.17 con mapas por cgroup ejecutor; dueño real desconocido | Headers de ABI y limitación de validación bpftrace sin root en `tasks/evidence/FEATURE-MEMORYSAVER-02-TRAZADOR/abi-check.txt`; compilación y captura pendientes |


Los siguientes controles reciben evidencias suministradas. Sus pruebas de fixtures verifican el instrumento; los hashes acreditan consistencia de bytes y el cierre de cada investigación exige su captura y criterio originales.

| Instrumento | Alcance | Verificación |
| --- | --- | --- |
| `tools/capture_io.py` | Lectura acotada de archivos de evidencia y decodificación JSON estricta | `tests/test_device_inventory.py`; capturas reales del sujeto pendientes cuando el criterio las exige |
| `tools/forum_finding.py` | Evaluación de preflights de foro a partir de salidas de comandos capturadas | `tests/test_closure_kernel.py`; capturas reales del sujeto pendientes cuando el criterio las exige |
| `tools/forum_hardware_subjects.py` | Predicados de hardware de foro por mecanismo sobre capturas de casos | `tests/test_forum_hardware_subjects.py`; capturas reales del sujeto pendientes cuando el criterio las exige |
| `tools/hardware_batch02_controls.py` | Predicados del lote hardware 02 sobre transcripciones suministradas | `tests/test_debt_registration_controls.py`; capturas reales del sujeto pendientes cuando el criterio las exige |
| `tools/hardware_batch03_controls.py` | Predicados del lote hardware 03 sobre capturas acotadas y recibos de integridad | `tests/test_debt_registration_controls.py`; capturas reales del sujeto pendientes cuando el criterio las exige |
| `tools/hardware_evidence.py` | Lectores y gates de evidencia para la familia hardware | `tests/test_hardware_apt_route.py`; capturas reales del sujeto pendientes cuando el criterio las exige |
| `tools/json_schema_subset.py` | Subconjunto de JSON Schema usado por controles runtime; keywords fuera del subconjunto quedan UNKNOWN | `tests/test_json_schema_subset.py`; capturas reales del sujeto pendientes cuando el criterio las exige |
| `tools/runtime_batch01_controls.py` | Predicados de mediciones y eventos para las fichas runtime del lote 01 | `tests/test_debt_registration_controls.py`; capturas reales del sujeto pendientes cuando el criterio las exige |
| `tools/runtime_batch02_controls.py` | Predicados por ficha runtime del lote 02; códigos de proceso requieren enteros exactos | `tests/test_debt_registration_controls.py`; capturas reales del sujeto pendientes cuando el criterio las exige |
| `tools/runtime_batch03_controls.py` | Predicados de logs y eventos runtime del lote 03 | `tests/test_debt_registration_controls.py`; capturas reales del sujeto pendientes cuando el criterio las exige |
| `tools/runtime_batch04_controls.py` | Predicados de evidencia por ficha runtime del lote 04 | `tests/test_debt_registration_controls.py`; capturas reales del sujeto pendientes cuando el criterio las exige |
| `tools/apt_arm64_evidence.py` | `verify_capture` sobre `commands.json` de DELTA-FORUM-APT-ARM64-SOURCE-VALIDATION-01: arquitectura `arm64` por `dpkg`, fuente Deb822 en `ports.ubuntu.com/ubuntu-ports` (`archive.ubuntu.com/ubuntu` es `fail`), tuple arm64 Packages efectivo en `apt-get indextargets`, `gpgv` con `Good signature` sobre el InRelease, simulación de upgrade sin paquetes a eliminar y negativo de firma rechazado (`BAD signature`). Con todo eso en verde devuelve `unknown`, porque el negativo de fuente equivocada no se corrió | `tests/test_closure_hardware.py` (captura real → `unknown` con `bad_source_negative`; fuente cambiada a `archive` → `fail`) |
| `tools/verify_apt_sources_closure.py` | Verificador de fuentes APT arm64 con bytes acotados, perfil suministrado y firmas bajo keyrings suministrados | `tests/test_debt_registration_controls.py`; capturas reales del sujeto pendientes cuando el criterio las exige |
| `tools/verify_cgroup_plan.py` | Verificador de capturas de las fases de investigación cgroup | `tests/test_closure_kernel.py`; capturas reales del sujeto pendientes cuando el criterio las exige |
| `tools/verify_clock_cap_tradeoff.py` | Evaluación de canales térmicos separada del A/B de clock-cap | `tests/test_clock_tradeoff_observation_semantics.py`; capturas reales del sujeto pendientes cuando el criterio las exige |
| `tools/verify_forum_finding.py` | Verificador de evidencia para hallazgos hardware identificados por ficha | `tests/test_debt_registration_controls.py`; capturas reales del sujeto pendientes cuando el criterio las exige |
| `tools/verify_forum_pstore.py` | Verificador de hallazgos de foro sobre capturas pstore y de proveedor | `tests/test_closure_kernel.py`; capturas reales del sujeto pendientes cuando el criterio las exige |
| `tools/verify_gpu_clock_cap_ab.py` | Evaluación de experimentos clock-cap desde capturas nativas timestamped | `tests/test_debt_registration_controls.py`; capturas reales del sujeto pendientes cuando el criterio las exige |
| `tools/verify_memory_saver.py` | Verificador de capturas del trazador y packing de 4 KiB de Memory Saver | `tests/test_closure_kernel.py`; capturas reales del sujeto pendientes cuando el criterio las exige |
| `tools/verify_netconsole.py` | Evaluación de capturas de netconsole, receptor, seguridad y rollback | `tests/test_closure_kernel.py`; capturas reales del sujeto pendientes cuando el criterio las exige |
| `tools/verify_rcu_panic_pstore.py` | Evaluación de capturas RCU/pstore; el verificador no induce panic | `tests/test_closure_kernel.py`; capturas reales del sujeto pendientes cuando el criterio las exige |
| `tools/verify_usb_hid_postupdate.py` | Evaluación de pérdida USB/HID tras actualización sobre salidas Linux capturadas | `tests/test_debt_registration_controls.py`; capturas reales del sujeto pendientes cuando el criterio las exige |
| `tools/verify_wifi_isolation.py` | Clasificación de aislamiento Wi-Fi sobre probes NetworkManager, host y rutas | `tests/test_debt_registration_controls.py`; capturas reales del sujeto pendientes cuando el criterio las exige |

## Inventario de propiedad

Todo lo relativo a **monitoreo y cuelgue** de esta máquina es de este repo, sin
importar quién lo escribió (decisión del dueño, 2026-09-24). Estar en esta tabla
significa que hay copia en `adopted/` y que `bb drift` avisa si la máquina se
separa de ella.

Se descubrió midiendo, no recordando: el 2026-09-24 se adoptaron **12 rutas**
(no 11 -- corregido el 2026-09-28, ver Risks), de las cuales **4** fueron
creadas el 2026-09-09 entre las 15:39 y las 15:40 siguiendo el hilo del foro
de NVIDIA #358951 (no ocho -- confirmado con `stat -c %w`; las otras 8 tienen
cada una su propia historia, ver Risks). De esas 12, 3 (`bb-usable.service`, `blackbox-sample.service`,
`blackbox-sample.timer`) ya estaban versionadas en `systemd/`; las otras 9
no lo estaban en ningún sitio. `/usr/local/bin/nvrm-watch.sh` — un detector
de precursores del cuelgue que corre cada 5 minutos — existía sólo en el
disco.

| desplegado en | por que es de bb |
| --- | --- |
| `/srv/ai/gpu_governance/admission_check.sh` | veta arrancar un motor que no cabe en memoria. Presion de memoria. |
| `/srv/ai/gpu_governance/gpu_lock.sh` | exclusion mutua sobre la GPU. |
| `/srv/ai/gpu_governance/gpu_sampler.sh` | muestreo de GPU (SUSPENDIDO, ver suspended/MANIFIESTO.md). |
| `/srv/ai/gpu_governance/monitor_memory.sh` | el cuerpo del monitor de memoria. |
| `/etc/default/kdump-tools` | captura del volcado tras un panic. Cuelgue. |
| `/etc/modprobe.d/99-blackbox-uvm.conf` | `uvm_global_oversubscription=0`, mitigación parcial para NVIDIA #1358: puede convertir algunos fallos de asignación UVM en OOM recuperable, pero no evita todos los cuelgues. |
| `/etc/security/limits.d/99-nv-spark-limits.conf` | limites de proceso (memlock, core). |
| `/etc/security/limits.d/nv-limits.conf` | idem, del fabricante. |
| `/etc/sysctl.d/99-blackbox-panic.conf` | `kernel.panic=10`: que un panic salga reiniciando si kdump falla. Cuelgue. |
| `/etc/sysctl.d/99-freeze-panic.conf` | obliga al kernel a entrar en panic ante hung_task/softlockup/hardlockup. Cuelgue. |
| `/etc/sysctl.d/99-nvidia-unified-memory.conf` | `min_free_kbytes`, `swappiness`, `vfs_cache_pressure`. Presion de memoria. |
| `/etc/sysctl.d/99-sysrq.conf` | `kernel.sysrq=1`: la salida manual de un cuelgue desde el teclado. Cuelgue. |
| `/etc/systemd/system.conf.d/99-blackbox-watchdog.conf` | el watchdog SBSA por hardware, la ultima capa. Cuelgue. |
| `/etc/systemd/system/atom-clock-lock.service` | fija el reloj de GPU; sin el, el throttle se confunde con un fallo. |
| `/etc/systemd/system/bb-usable.service` | el vigilante por PSI que reinicia la maquina. Cuelgue. |
| `/etc/systemd/system/docker.slice.d/99-blackbox.conf` | techo agregado de los contenedores. Presion de memoria. |
| `/etc/systemd/system/earlyoom.service.d/override.conf` | punteria del OOM killer antes de que la maquina se atasque. |
| `/etc/systemd/system/nvrm-watch.service` | registra cada 5 min los errores `NVRM: Out of memory`, señal que puede aparecer con o sin cuelgue. |
| `/etc/systemd/system/nvrm-watch.timer` | su cadencia. |
| `/etc/systemd/system/system.slice.d/99-blackbox.conf` | techo agregado de los servicios del sistema. Sin él entraba en el presupuesto por lo que USABA y no por lo que prometía, y los compromisos no cuadraban. Presion de memoria. |
| `/etc/systemd/system/sysstat-collect.timer.d/override.conf` | cadencia de `sar`, la serie historica de memoria. |
| `/home/lcasarin/.config/systemd/user/app.slice.d/99-blackbox.conf` | techo de la sesion grafica. Presion de memoria. |
| `/etc/systemd/system/user.slice.d/99-blackbox-escritorio.conf` | nivel 1 de la cadena de `memory.low`. Sin ella los niveles de abajo no protegen nada. |
| `/etc/systemd/system/user-.slice.d/99-blackbox-escritorio.conf` | nivel 2: el slice por UID. |
| `/etc/systemd/system/session-.scope.d/99-blackbox-escritorio.conf` | nivel 3a: aqui vive **Xorg**, medido en `/proc/<pid>/cgroup`, no en `session.slice`. |
| `/etc/systemd/system/user@.service.d/99-blackbox-escritorio.conf` | nivel 3b: el gestor de usuario, padre de `session.slice` y de `app.slice`. |
| `/home/lcasarin/.config/systemd/user/session.slice.d/99-blackbox-escritorio.conf` | nivel 4: gnome-shell, dbus, pipewire, ibus. El camino de una tecla tras el servidor X. |
| `/home/lcasarin/.config/systemd/user/app.slice.d/99-blackbox-escritorio.conf` | nivel 5: no se protege a sí mismo, **pasa** la protección a los scopes de ventana. |
| `/home/lcasarin/.config/systemd/user/app-gnome-.scope.d/99-blackbox-escritorio.conf` | nivel 6: **la ventana** donde se escribe. Prefijo truncado: alcanza al scope lleve el pid que lleve. |
| `/home/lcasarin/.config/systemd/user/snap.antigravity.antigravity-.scope.d/99-blackbox-escritorio.conf` | nivel 7: el editor del episodio del 2026-09-25. Prefijo **derivado del journal**, no verificado sobre unit viva. |
| `/usr/local/bin/nvrm-watch.sh` | su cuerpo. Estaba en /usr/local/bin sin versionar en ningun sitio. |
| `~/.config/systemd/user/ai-gpu-telemetry.service` | telemetria de GPU que `bb scan` LEE en vez de duplicar. |
| `~/.config/systemd/user/ai-memory-monitor.service` | monitor de memoria cada 5 min que `bb scan` lee. |
| `~/.config/systemd/user/ai-memory-monitor.timer` | su cadencia. |
| `~/.config/systemd/user/atom-crash-detector.service` | detector de caidas que `bb scan` lee. |
| `~/.config/systemd/user/atom-crash-detector.timer` | su cadencia. |
| `~/.config/systemd/user/ai-nemotron-vigilante.service` | ejecuta `bin/bb-vigilante-motor`; sin esta unit el motor colgado (chat mudo, `/v1/models` en 200) no lo reinicia nadie. |
| `~/.config/systemd/user/ai-nemotron-vigilante.timer` | su cadencia: cada 2 min tras 5 min de arranque. |
| `~/.config/systemd/user/atom-gpu-telemetry.service` | la telemetria de Atlas, leida no duplicada. |
| `~/.config/systemd/user/blackbox-sample.service` | el muestreo propio de bb. |
| `~/.config/systemd/user/blackbox-sample.timer` | su cadencia. |
| `~/.config/systemd/user/blackbox-drift.service` | corre `bb drift`; hasta el 2026-09-28 era comando manual, sin instrumentar. |
| `~/.config/systemd/user/blackbox-drift.timer` | su cadencia: una vez al día. |

**Deliberadamente fuera**: `dcgm.service` y la familia `nvsm-*` son la pila de
monitoreo del fabricante; `bb scan` las lee, no las custodia. `/etc/systemd/system.conf`
tampoco se adopta entero, porque el paquete `systemd` lo reescribe: lo que bb
posee es el drop-in `system.conf.d/99-blackbox-watchdog.conf`, que sobrevive a
la actualización.

## Constraints

Python version: 3.11+
Deployment target: local

El ejecutable es bash sin dependencias fuera de lo ya instalado (coreutils,
procps, systemd, nvidia-smi, curl). Python sólo se usa para analizar muestras.

## ADRs

| ADR | Decision | Status |
| --- | --- | --- |
| 0001 | Adopt simplecode gates | Accepted |
| 0002 | Leer las fuentes existentes en vez de duplicarlas; consolidar cuando se solapan | Accepted |
| 0003 | Guardar contadores crudos y derivar tasas al analizar, nunca al muestrear | Accepted |
| 0004 | Suspender es renombrar con manifiesto y caducidad, nunca borrar | Accepted |
| 0005 | Comprobar el dato, no la variable de configuración ni el estado de la unit | Accepted |
| 0006 | Actuar cuando la inacción cuesta la máquina entera, no sólo informar | Accepted |
| 0007 | Todo lo de monitoreo y cuelgue es de este repo, lo escribiera quien lo escribiera | Accepted |
| 0008 | Los inventarios de esta spec los ata un gate al sujeto, nunca la memoria de nadie | Accepted |
| 0009 | blackbox produce telemetria y Atlas la consume; ningun import cruzado entre los dos | Accepted |
| 0010 | Una frontera de propiedad se traza midiendo el acoplamiento, no afirmandolo | Accepted |
| 0011 | Un total de máquina no puede ver un cuello de botella de un solo hilo: se mide también la latencia del camino y se nombra al proceso | Accepted |
| 0012 | El camino interactivo se protege del reclamo de memoria por cadena completa de cgroups; una protección con un eslabón en cero no protege nada | Accepted |
| 0013 | La protección discrimina por **cómo se lanzó** el proceso (prefijo de scope), nunca por el nombre del producto; el arnés queda reclamable por no pedir protección, no por estar en una lista | Accepted |
| 0014 | Un comparador que nunca puede fallar (`bb drift`, `return 0` incondicional) no es un gate y nadie lo corre solo: su exit code refleja lo que encontró, y corre por su propio timer diario -- no sólo a mano ni sólo atado a un `git push`, porque la máquina diverge sin que nadie haga commit | Accepted |

## Risks

| Risk | Likelihood | Mitigation |
| --- | --- | --- |
| Un instrumento deja de escribir en silencio | Alta | `bb status` mira la antigüedad de los datos sólo donde hay un artefacto que revisar (sar, memory-monitor, telemetría térmica de este repo: "por sus datos, no por la unit" — y el 2026-09-25 ese mismo chequeo se midió mintiendo al revés, declarando FALTA sobre un instrumento activo porque leía la ruta que Atlas ya había borrado); los cuatro que quedaban leyendo `systemctl is-active` se cerraron —tres el 2026-09-25, el de bb-usable el 2026-09-28— y ahora leen también su artefacto: la muestra más fresca del día, la confirmación que el driver imprimió al aplicar el clock lock contrastada con los argumentos que la unit declara, las dos regex de puntería que earlyoom imprimió al arrancar, y el latido que el bucle de `bin/bb-usable` imprime en cada vuelta de 30 s ("latencia del escritorio"), exigido dentro de los últimos 120 s (`bin/bb`, `journalctl -S`). Los cuatro pueden ahora salir mal por el motivo que vigilan, con cinco controles negativos corridos de los tres originales en `tests/test_bb_bash.py` -- `test_control_negativo_sin_muestra_fresca_el_muestreo_esta_FALTA`, `test_control_negativo_clock_lock_con_OTRO_rango_que_el_declarado`, `test_control_negativo_clock_lock_sin_confirmacion_del_driver`, `test_control_negativo_earlyoom_de_serie_no_cuenta_como_armado`, `test_control_negativo_earlyoom_con_UNA_sola_regex_no_basta` (citados por nombre, no por línea, porque el fichero se mueve con cada test que se añade -- la cifra de "cuatro" venía mal desde el commit `37ccd7d`, corregida el 2026-09-28) -- más tres del latido de bb-usable (rancio, journal vacío, sólo la línea de arranque). Queda declarado lo que sigue sin comprobarse: que el contenido sea correcto, no sólo fresco |
| Una comprobación que no puede fallar da falsa confianza | Alta | Los controles negativos comprobados en este repo se declaran por nombre y alcance, sin inferir cobertura universal: `bash-sintaxis` (`tests/test_bash_sintaxis.py`, 2 passed), `ruff` y `gitleaks` (`tests/test_ruff_gitleaks_controles_negativos.py`, 4 passed), `spec-check` y `no-perder-lineas` (`tests/test_hook_native_controls.py`, cada uno pasa contenido válido y rechaza una falla inyectada). Estos casos confirman que esos controles detectan sus fallas probadas; no certifican otros hooks que bloquean. `telemetry-bound` sigue fuera porque su hook termina en `\|\| true` y no bloquea. El registro histórico de `spec-check` y `no-perder-lineas` contiene cuatro `could_not_run` el 2026-09-08, no hallazgos (`.simplecode/evidence/telemetry.jsonl`). `bb scan` marca un Field Diagnostic ilegible o con esquema inválido como `could_not_run` (`tests/test_auditoria_bb_regresiones.py::test_scan_fielddiag_summary_invalido_incrementa_cnr`); un resumen válido con errores de hardware se analiza como resultado.
| El propio muestreo compite por la memoria unificada | Media | La adquisición de muestras lee `/proc`, sysfs, el journal, `nvidia-smi` y endpoints existentes. El muestreador térmico también escribe telemetría, persiste su estado y puede pausar y reanudar procesos mediante `SIGSTOP`/`SIGCONT` bajo sus condiciones de alarma y carga; `Nice=19` e `IOSchedulingClass=idle` en **los dos muestreadores que blackbox escribe y gobierna** (`blackbox-sample`, `atom-gpu-telemetry` -- corregido el 2026-09-28, corría en `Nice=10`, ver `adopted/systemd-user/atom-gpu-telemetry.service`; ambos confirmados en vivo con `systemctl --user show ... -p Nice`). La auditoría H1 del 2026-09-28 encontró que la fila decía "los tres" sin nombrar un tercero: `ai-memory-monitor` (activo, cada 5 min, `Nice=0`) y `ai-gpu-telemetry` (deshabilitado, `Nice=10`) también muestrean, pero son instrumentos **adoptados** de `/srv/ai/gpu_governance/`, no escritos ni gobernados por blackbox -- misma frontera que Atlas: se les hace custodia de deriva, no se les impone la convención de prioridad de blackbox. `bb-guardia-proceso` queda fuera a propósito: no muestrea, sólo lee lo que ya existe (y escribe su propio `guardia_proceso.jsonl`), y su unit declara `Nice=10` (consulta del 2026-10-03: enabled, inactive; no 19, corregido el 2026-09-28 tras la verificación H1: "prioridad normal" era impreciso) -- más alto que los DOS muestreadores de blackbox (`Nice=19`), pero no que `ai-memory-monitor` (`Nice=0`, la auditoría H1 del 2026-09-28 encontró la frase anterior contradiciendo la fila que la precede) -- para poder actuar bajo presión de memoria en vez de esperar su turno |
| Los umbrales de PSI vienen de otra máquina | Baja | Calibrados 2026-09-23 contra los dos congelamientos propios del 2026-09-22/23 sobre 19 804 muestras (2026-09-08 07:57 -> 2026-09-23 10:53; esta cifra y las de 98.53 % y 48.80 % vienen del mensaje de 90847b3 y del docstring de tools/calibra_psi.py y no se re-derivan: RETAIN_DAYS=14 ya no conserva ese corpus): el corte pasó de nivel instantáneo a duración sostenida (≥10 % durante ≥5 min), porque el nivel se equivoca en las dos direcciones — seis excursiones sanas llegaron a 98.53 % y un congelamiento real bajó a 48.80 %. `tools/calibra_psi.py` re-deriva los cortes y sale 1 si dejan pasar un incidente o si el instante en que se completa la duración sostenida cae fuera de una ventana etiquetada; una excursión que sólo se solapa con un incidente no cuenta como detección (`tests/test_calibra_psi.py::test_control_negativo_excursion_solapa_incidente_pero_dispara_despues`). Sigue abierto: n=6 del lado positivo -- dos ventanas del 2026-09-28 se sumaron el mismo día que ocurrieron -- y sólo el canal de memoria está calibrado. Corrido el 2026-10-06 sobre el corpus vivo (2026-09-21 00:00 -> 2026-10-06 01:11, 23776 muestras con PSI): rc=1, un falso positivo (colapso del 2026-10-05 de 00:18:38 a 00:26:00, 7.4 min) y un incidente no detectado; el arranque que termina a las 00:29:49 del 2026-10-05 es un posible séptimo incidente aún sin etiquetar — `io_some`/`cpu_some` se imprimen sin etiqueta a propósito. Corrido el 2026-09-28: `python3 -m tools.calibra_psi` sale rc=1, VEREDICTO CORTE INVALIDO, porque `bb sample` dejó de escribir entre las 03:29:02 y las 03:39:21 de ese mismo día (corregido el 2026-09-28: la última línea real es un `burst_fin` a las 03:29:02, no la muestra con datos de las 03:28:58 que la cerró -- la ráfaga sí terminó limpia; la misma invocación, la de las 03:28:09, se colgó después de escribir ese `burst_fin` -- `Type=oneshot` no deja arrancar una invocación siguiente mientras la anterior sigue activa) -- un hueco del propio instrumento que ninguna clasificación automática puede corroborar, declarado, no corregido aquí |
| Un repo adoptado diverge de lo desplegado sin avisar | Media | `bb drift` compara repo contra máquina y se verificó en ambos sentidos. Hasta el 2026-09-28 esto era verdad a medias: el comando comparaba bien, pero volvía `return 0` sin condición y nada lo llamaba nunca — un hallazgo de la auditoría H1 de ese mismo día, fuera de las afirmaciones que esa auditoría estaba revisando. Corregido: exit distinto de 0 si diverge o falta algo, y `blackbox-drift.timer` lo corre una vez al día sin que nadie tenga que acordarse |
| Esta spec envejece y pasa a describir lo que alguien recordaba | **Ocurrió** | Pasó: declaraba "Out of scope: actuar sobre lo que mide" mientras `bb-usable` reiniciaba la máquina. `tools/inventario.py --check` corre en `pre-commit` y ata las dos tablas a `bin/bb`, `tools/` y `adopted/`; el código registra dos defectos iniciales del instrumento (`tools/inventario.py:76-99`). El mensaje versionado de `1ec66b3` atribuye seis desajustes a la primera corrida; conserva ese registro histórico, pero el commit carece del stdout original que permitiría repetir la verificación del recuento |
| Un instrumento de cuelgue vive en la máquina y en ningún repo | **Ocurrió** | Pasó con `/usr/local/bin/nvrm-watch.sh`, que existía sólo en disco. El commit `1ec66b3` añadió **12** rutas a `adopted/` (no 11 -- `git diff --diff-filter=A --name-only 1ec66b3^ 1ec66b3 -- adopted/` da 12; sin el filtro da 13, porque ese mismo commit tambien MODIFICA `atom-gpu-telemetry.service`, no sólo añade), pero las 12 no son 12 casos del mismo hallazgo: la clasificación archivada de la auditoría H1 del 2026-09-28 atribuye **4** al foro de NVIDIA #358951 (la evidencia original de fechas queda pendiente, ver abajo); tres (`bb-usable.service`, `blackbox-sample.service`, `blackbox-sample.timer`) ya estaban versionados, idénticos byte a byte, en `systemd/` desde antes de `1ec66b3`, y los 5 restantes tienen cada uno su propia historia (corregido el 2026-09-28, la ronda anterior decía "el resto salía de un heredoc" y sólo era cierto para uno): `99-blackbox-uvm.conf` sí salía de un heredoc de `enable-privileged.sh`; `99-blackbox-panic.conf` y `99-blackbox-watchdog.conf` entraron en el propio `1ec66b3` desplegados con `cp adopted/...`; `99-sysrq.conf` (nacido el 08-28) y `/etc/default/kdump-tools` (instalado fuera de blackbox) no tenían ningún escritor en el repo. La fila anterior generalizaba la historia de los 4 a los 12. La clasificación archivada de la revisión H1 (`tasks/evidence/RELEASE-2.1.0/h1-items.json`) atribuye cuatro sujetos (`99-freeze-panic.conf` y los tres `nvrm-watch`) a la ventana de creación del 2026-09-09 entre las 15:39 y las 15:40; esta copia conserva la conclusión, pero carece del stdout de `stat -c %w` y del control negativo de re-despliegue. La fecha y la discrepancia histórica de cuatro frente a ocho quedan pendientes de revalidación independiente. Adoptados el 2026-09-24 (commit `1ec66b3`); `bb drift` vigila 41 sujetos, **antes 30** (no 19 -- ese "antes 19" viene del propio mensaje de `1ec66b3`, que ya contaba mal: `git ls-tree` sobre el commit anterior da 18 sujetos, no 19; corregido el 2026-09-28). El 39º es `system.slice.d_99-blackbox.conf`, sumado en el commit `e4cb0e2` del 2026-09-28; los sujetos 40 y 41 son `blackbox-drift.service`/`.timer`, el propio instrumento que el arreglo de `bb drift` añadió el mismo día. Corrido el 2026-09-28: `./bin/bb drift` imprimió `revisados: 41   divergentes: 0   ausentes: 0   suspendidos: 1`, captura fechada en `tasks/evidence/DEBT-BB-SAMPLE-SIN-TECHO-DE-TIEMPO-SE-QUEDO-COLGADO-EN-EL-COLAPSO/e2e.txt`. Corrido el 2026-10-03: `./bin/bb drift` imprime `revisados: 41   divergentes: 2   ausentes: 0   suspendidos: 1`, exit 1; salida fechada en `tasks/evidence/DEBT-H1-RELEASE-CLAIMS-01/drift-current.txt` |
| La máquina es inusable mientras todos los totales leen sanos | **Ocurrió** | Pasó el 2026-09-25: el dueño reinició a mano porque "casi no se podía escribir" y veinticinco segundos antes bb medía load1 0.95 sobre 20 núcleos, 64.3 GiB disponibles de 121, PSI en cero y nvidia-smi en 22 ms. Medido después en el journal: el scope de antigravity consumió 2 h 37 min de CPU en 2 h 15 min de reloj (116.5 % de UN núcleo) y el de Claude 15 h 09 min 54 s de CPU en las 9 h 08 min que el scope vivió de verdad (20:00:33 -> 05:08:27, no el arranque entero) — 166 % de otro núcleo. Entre los dos, el 14 % de una máquina de 20 núcleos (no el 11 % que decía esta fila antes de que la auditoría H1 del 2026-09-28 encontrara el denominador equivocado; el mismo error estaba en `tasks/done/DEBT-SLUGGISH-SIN-CAUSA-PROBADA.md` (corregida: la frase del 14 % está en la línea 57 de la revisión 11e3cfb y hoy en la 72; la otra línea que corrigió el mismo error es la 52, hoy la 67), corregido igual), que no mueve ningún total. Se añadieron `cpu_top` (quién quema CPU, con su unit), `x.{estado,ms}` (ida y vuelta contra el servidor X) y `swap.{free_kb,total_kb,in_pag_s,out_pag_s}`. Medido hacia las 00:36 del 2026-09-28 sobre 3563 muestras con `x.estado` OK (la cifra que el propio SPEC.md de ese momento registró, commit `2460f20`; el CUERPO de ese mismo commit da 3568, una re-medición de las 00:41 con la misma distribución -- ambas cifras conviven en la historia, se cita la del texto que quedó escrito): mediana 4 ms, p75 5, p95 8 -- corpus que crece con cada muestra y rota con `RETAIN_DAYS=14`, así que no se cita como cifra viva (verificación H1 del 2026-09-28: horas después ya eran 4138 muestras con p95 9) — y **ningún corte sano de `x.ms` está calibrado**, porque no hay episodio etiquetado con muestras (`python3 -m tools.calibra_latencia_x` sale rc=2). La causa del episodio **nunca se probó** y la ficha `DEBT-SLUGGISH-SIN-CAUSA-PROBADA` se cerró el 2026-09-27 como `void_wontfix`, con la objeción escrita en el cuerpo: la sonda empezó a grabar 32 minutos después de que acabara el único episodio etiquetado, así que no existe lado positivo contra el que calibrar. Se reabre con `bb snapshot "el escritorio no responde"` durante el próximo episodio |
| `bin/bb` ronda el 67% del bash del repo (2768 de 4111 líneas trackeadas al commit `d3d7980`, todo `*.sh` más `bin/bb`, sin excluir nada -- la verificación H1 del 2026-09-28 encontró que el "71%" anterior excluía `adopted/` y `tests/fixtures/` sin decirlo, y que el total mismo se mueve con cualquier commit a un `.sh`, así que no se cita como cifra viva) y ningún gate medía su cobertura | **Ocurrió** | `coverage.py` no instrumenta bash, así que `coverage-target` pasaba sin mirarlo. `tools/cobertura_bash.sh` lo mide y `bb-cobertura-piso` (pre-push) impide que baje del piso de 32.8 — **35.0%-35.3% según el estado versionado de `SPEC.md` en `57ae066`, 39.8% según el mensaje versionado de `09deb5b` (el paquete H1 no conserva el stdout original de esas corridas)** (la verificación H1 del 2026-09-28 encontró que el salto descrito en esos mensajes no es carga de máquina, como decía la fila anterior, sino los cinco tests de `bb drift` que añadió `09deb5b` -- el `SPEC.md` de su padre, `57ae066`, registra 35.0%-35.3%; `3a91866` no está en esa historia de commits y no mueve la cifra -- más test, más cobertura real; no se cita como cifra viva porque cambia con cada test que se añade), contra el 33.1% que dejó el arreglo del medidor el 2026-09-25. **El salto desde 27.0 no fue cobertura ganada**: el medidor ponía `PS4='+${BASH_SOURCE}:${LINENO}:'` y buscaba las líneas con un patrón anclado en UN solo `+`, y bash repite ese carácter según la profundidad de anidamiento, así que lo que corría dentro de una sustitución `$(...)` cuya traza llevaba varios `+` se contaba SIN CUBRIR; una tubería o un subshell con traza de un solo `+` sí se contaba — en `bin/bb` es casi todo, porque cada bloque de la muestra se arma con `x=$(funcion)`. Sobre 947 líneas candidatas, las cubiertas pasaron de 256 a 313 según el mensaje de `2a228fa` (ese mismo mensaje da 26.8 % = 254 en su párrafo inicial). La medición en el mismo trace da una diferencia de 58 o 59 líneas, nunca 57; nadie escribió un test entre las dos cifras. El piso de 32.8 sale del mínimo de tres corridas (33.1) menos el vaivén medido de 0.2-0.3 entre reposo y carga. El número sigue siendo bajo y es el hallazgo, no la solución. (El docstring de `tests/test_cobertura_bash.py` decía 33.3%/59 líneas para la misma corrida; se eligió el 2026-09-28 contra la medida que el propio commit `2a228fa` guarda — 256 cubiertas de 947 antes, 313 después: 313−256 = 57 según el mensaje del commit (medido en el mismo trace: 58-59) y 313/947 = 33.1%, y el piso de 32.8 se derivó de 33.1, no de 33.3. El docstring quedó corregido) |

## Acceptance Criteria

- `bb status` distingue instrumento armado de instrumento ausente, y cuenta los
  que faltan.
- `bb scan` termina con el número de comprobaciones que **no** pudieron correr;
  un informe con ese número por encima de cero no se presenta como limpio.
- Cada detector se verifica en los dos sentidos: dice sí cuando hay y no cuando
  no hay.
- `bb drift` detecta una divergencia introducida a propósito y vuelve a cero al
  restaurarla; el exit code distingue los dos casos, y corre sin que nadie lo
  llame a mano (`blackbox-drift.timer`, diario).
- `bb-usable` retira el latido ante presión sostenida y la máquina reinicia sola,
  sin intervención humana.
- Los dos inventarios de esta spec describen el repo y la máquina, comprobado por
  un gate que se verificó mutando el sujeto.
- La cobertura de `bin/bb` es un número medido, y no puede bajar en silencio.
- `simplecode check` passes.

## Requirements

### REQ-0001
WHEN an operator runs `bb status` THEN the system SHALL distinguish each
instrument that is armed from one that is absent or stale.
verify: `python -m pytest tests -q`
expect: exit_zero

### REQ-0002
WHEN an operator runs `bb scan` THEN the system SHALL report the number of
checks that could not run instead of presenting the report as clean.
verify: `python -m pytest tests -q`
expect: exit_zero

### REQ-0003
WHEN a managed shell command changes THEN the system SHALL preserve valid Bash
syntax before it can be committed.
verify: `bash -n bin/bb enable-privileged.sh`
expect: exit_zero

### REQ-0004
WHEN memory pressure stays above the calibrated cut for its calibrated duration
THEN the system SHALL withhold the systemd watchdog heartbeat so the machine
reboots itself without human intervention.
verify: `python -m pytest tests/test_bb_usable.py -q`
expect: exit_zero

### REQ-0005
WHEN a subcommand, a tool or an adopted subject is added THEN the system SHALL
refuse the commit until both inventories in SPEC.md name it.
verify: `python -m pytest tests/test_inventario.py -q`
expect: exit_zero

### REQ-0006
WHEN the test suite of `bin/bb` covers fewer lines than the recorded floor THEN
the system SHALL block the push instead of reporting a coverage number nobody
measured.
verify: `bash tools/piso_cobertura.sh`
expect: exit_zero

### REQ-0007
WHEN the machine is sampled THEN the system SHALL record how long the desktop
takes to answer and which processes burned CPU since the previous sample, so
that a single-threaded bottleneck is distinguishable from an idle machine
instead of both reading identical.
verify: `python3 -m pytest tests/test_bb_bash.py -k "latencia_x or cpu_top" -q`
expect: exit_zero
