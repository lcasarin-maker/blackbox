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

**Mission**: Que un fallo de esta máquina —cuelgue, crash, OOM, servicio caído—
deje evidencia suficiente para diagnosticarlo **después**, y que la ausencia de
un instrumento se vea antes del fallo y no durante la autopsia.

## Purpose

Caja negra de la AI TOP ATOM (NVIDIA GB10, 20 núcleos aarch64, 121 GB de memoria
unificada). Registra continuamente lo que ninguna otra fuente de la máquina
cubre, lee las que sí existen en vez de duplicarlas, y declara qué comprobación
no pudo correr.

Nace del incidente del 2026-09-07: la app de escritorio de Claude quedó colgada
con el proceso vivo, la ventana en pantalla y cero renderizadores. El
diagnóstico descartó OOM, segfault, throttle y térmica, y **no llegó a causa
raíz**, porque `ulimit -c` era 0 y `systemd-coredump` no estaba instalado.

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
  evaluación de mecanismos cosechados por Atlas, con su propia suite (`tests/`,
  100% de cobertura -- la única pieza de Python de este repo).

- **Actuar sobre lo que mide, donde la inacción cuesta la máquina entera.** Esto
  dejó de estar fuera de alcance el 2026-09-23/24, después de cuatro
  congelamientos: `bb-usable` retira el latido del watchdog ante presión
  sostenida y systemd reinicia (medido: 2026-09-24 14:09:38, 10 min 34 s desde
  el inicio del colapso, sin nadie delante); `bb cap` lanza con techo de
  memoria; y los techos de `app.slice` y `docker.slice` matan un proceso en vez
  de dejar caer la máquina. `bb protect` ya no es la excepción: es el caso menor.
- Custodia de la instrumentación de la máquina relativa a **monitoreo y cuelgue**,
  venga de donde venga. Ver "Inventario de propiedad".

## Out of scope

- Interfaz gráfica o dashboard: esto se lee desde una terminal o desde un agente.
- Monitoreo multi-máquina o por SSH: hay una sola unidad.
- Actuar sobre lo que mide **cuando el fallo no cuesta la máquina**: bb informa,
  no repara servicios, no reinicia unidades, no borra nada.
- Duplicar telemetría de GPU y térmica: la produce `Atlas/tools/atom_gpu_telemetry.py`.

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
2. **Lo que decide sobre el hardware vive aqui**, aunque su salida acabe en la
   KB. Lo que produce conocimiento vive en Atlas, aunque lea del hardware --
   por eso `tools/detect_atom_crash.py` se queda alli: importa
   `tools.durable_log` y escribe dictamenes en `docs/agent_findings/`.
3. **Ninguna pieza fisica depende de que alguien inicie sesion.** Es lo que
   costo 4 h 21 min de stack caido el 2026-09-24, y por eso el `linger` esta
   en `enable-privileged.sh`.

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
| `bb scan ["hace X"]` | informe por ventana temporal cruzando todas las fuentes, y **cuenta las comprobaciones que no pudieron correr** | `tests/test_bb_bash.py` |
| `bb hw` | inventario de hardware y de los límites aplicados | `bash -n` |
| `bb status` | qué instrumento está armado y cuál no, por sus DATOS donde hay artefacto | `tests/test_bb_bash.py` |
| `bb drift` | compara los 30 sujetos adoptados contra la máquina; distingue igual, divergente, ausente, suspendido y suspensión vencida | `tests/test_bb_bash.py` |
| `bb protect` | sube el límite de core de procesos YA corriendo (`prlimit`) | `bash -n` |
| `bb who [pid]` | qué procesos pesan y QUIÉN los lanzó: unit de cgroup, padre, cwd | `tests/test_bb_bash.py` |
| `bb sigterm ["hace X"]` | quién mandó SIGTERM/SIGKILL a quién, desde el registro de auditoría (DEBT-DGX-438) | `tests/test_bb_bash.py` |
| `bb cap <GB> <cmd...>` | lanza un proceso con techo de memoria propio, aplicado por el kernel vía `systemd-run --user --scope` | `tests/test_bb_bash.py` |
| `bb install` | instala el timer de usuario del muestreo | `bash -n` |
| `bin/bb-usable` | vigila si la máquina SIRVE, no si systemd vive: ante PSI `full avg10 >= 10` sostenido 300 s, retira el latido del watchdog y systemd reinicia | `tests/test_bb_usable.py`, 16 tests, 8 mutantes en rojo |
| `tools/calibra_psi.py` | re-deriva los cortes de PSI contra los cuatro incidentes propios y sale 1 si dejan pasar uno o disparan en una muestra sana | su propio veredicto `CALIBRADO` |
| `tools/check_harvest_accepted.py` | `close_check` reutilizable de las fichas HARVEST | `tests/`, 100% de cobertura |
| `tools/cobertura_bash.sh` | mide qué líneas de un script bash ejecuta una suite (`BASH_ENV` + `BASH_XTRACEFD`), porque `coverage.py` no ve bash | control negativo: suite vacía 0.0%, 3 tests 4.3%, 18 tests 17.6% |
| `tools/piso_cobertura.sh` | trinquete: falla si la cobertura de `bin/bb` baja de `tests/cobertura_bb.piso` | control negativo: con el piso a 99.0 devuelve 1 |
| `tools/atom_gpu_telemetry.py` | telemetria de GPU y zonas termicas cada 5 s, presupuesto termico con corroboracion, y **mitigacion**: pausa procesos cuando la maquina se calienta con carga real. Traida de Atlas el 2026-09-24 (DGX-585) | `tests/test_atom_gpu_telemetry.py` + `tests/test_atom_gpu_telemetry_bb.py`, 98 tests, **100 %** de 456 sentencias |
| `tools/run_mitigacion_carga_mutation.py` | arnés de mutación de la compuerta de carga: muta `atom_gpu_telemetry.py` y exige que la suite se ponga roja. Vino de Atlas con su sujeto (DGX-585) | él mismo: un mutante que sobrevive es el hallazgo |
| `tools/run_alarm_mark_mutation.py` | lo mismo para el marcado de alarmas térmicas | él mismo |
| `tools/inventario.py` | comprueba que estas dos tablas describen el repo y la máquina, no lo que alguien recordaba | él mismo, con `--check` sobre un sujeto mutado |

## Inventario de propiedad

Todo lo relativo a **monitoreo y cuelgue** de esta máquina es de este repo, sin
importar quién lo escribió (decisión del dueño, 2026-09-24). Estar en esta tabla
significa que hay copia en `adopted/` y que `bb drift` avisa si la máquina se
separa de ella.

Se descubrió midiendo, no recordando: el 2026-09-24 había **11 sujetos de
cuelgue sin dueño**, ocho de ellos creados el 2026-09-09 entre las 15:39 y las
15:40 siguiendo el hilo del foro de NVIDIA #358951, y ninguno versionado en
ningún sitio. `/usr/local/bin/nvrm-watch.sh` — un detector de precursores del
cuelgue que corre cada 5 minutos — existía sólo en el disco.

| desplegado en | por que es de bb |
| --- | --- |
| `/srv/ai/gpu_governance/admission_check.sh` | veta arrancar un motor que no cabe en memoria. Presion de memoria. |
| `/srv/ai/gpu_governance/gpu_lock.sh` | exclusion mutua sobre la GPU. |
| `/srv/ai/gpu_governance/gpu_sampler.sh` | muestreo de GPU (SUSPENDIDO, ver suspended/MANIFIESTO.md). |
| `/srv/ai/gpu_governance/monitor_memory.sh` | el cuerpo del monitor de memoria. |
| `/etc/default/kdump-tools` | captura del volcado tras un panic. Cuelgue. |
| `/etc/modprobe.d/99-blackbox-uvm.conf` | `uvm_global_oversubscription=0`, la causa raiz de NVIDIA #1358. Cuelgue. |
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
| `/etc/systemd/system/nvrm-watch.service` | detector de `NVRM: Out of memory` cada 5 min, precursor del cuelgue. |
| `/etc/systemd/system/nvrm-watch.timer` | su cadencia. |
| `/etc/systemd/system/sysstat-collect.timer.d/override.conf` | cadencia de `sar`, la serie historica de memoria. |
| `/home/lcasarin/.config/systemd/user/app.slice.d/99-blackbox.conf` | techo de la sesion grafica. Presion de memoria. |
| `/usr/local/bin/nvrm-watch.sh` | su cuerpo. Estaba en /usr/local/bin sin versionar en ningun sitio. |
| `~/.config/systemd/user/ai-gpu-telemetry.service` | telemetria de GPU que `bb scan` LEE en vez de duplicar. |
| `~/.config/systemd/user/ai-memory-monitor.service` | monitor de memoria cada 5 min que `bb scan` lee. |
| `~/.config/systemd/user/ai-memory-monitor.timer` | su cadencia. |
| `~/.config/systemd/user/atom-crash-detector.service` | detector de caidas que `bb scan` lee. |
| `~/.config/systemd/user/atom-crash-detector.timer` | su cadencia. |
| `~/.config/systemd/user/atom-gpu-telemetry.service` | la telemetria de Atlas, leida no duplicada. |
| `~/.config/systemd/user/blackbox-sample.service` | el muestreo propio de bb. |
| `~/.config/systemd/user/blackbox-sample.timer` | su cadencia. |

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

## Risks

| Risk | Likelihood | Mitigation |
| --- | --- | --- |
| Un instrumento deja de escribir en silencio | Alta | `bb status` mira la antigüedad de los datos sólo donde hay un artefacto que revisar (sar, memory-monitor, telemetría de Atlas: "por sus datos, no por la unit"); el resto (timer del muestreo, clock lock de GPU, earlyoom) sigue leyendo `systemctl is-active`, que no detecta una unit activa que dejó de trabajar -- verificado 2026-09-16, gap real y sin cerrar en esos tres |
| Una comprobación que no puede fallar da falsa confianza | Alta | Cada gate se verifica con control negativo; `bb scan` cuenta las que no pudieron correr |
| El propio muestreo compite por la memoria unificada | Media | Sólo lee `/proc` y endpoints ya existentes; `Nice=19` e `IOSchedulingClass=idle` |
| Los umbrales de PSI vienen de otra máquina | Baja | Calibrados 2026-09-23 contra los dos congelamientos propios del 2026-09-22/23 sobre 19 804 muestras (2026-09-08 07:57 -> 2026-09-23 10:53): el corte pasó de nivel instantáneo a duración sostenida (≥10 % durante ≥5 min), porque el nivel se equivoca en las dos direcciones — seis excursiones sanas llegaron a 98.53 % y un congelamiento real bajó a 48.80 %. `tools/calibra_psi.py` re-deriva los cortes y sale 1 si dejan pasar un incidente o disparan en una muestra sana. Sigue abierto: n=2 del lado positivo y las dos la misma noche, y sólo el canal de memoria está calibrado — `io_some`/`cpu_some` se imprimen sin etiqueta a propósito |
| Un repo adoptado diverge de lo desplegado sin avisar | Media | `bb drift` compara repo contra máquina y se verificó en ambos sentidos |
| Esta spec envejece y pasa a describir lo que alguien recordaba | **Ocurrió** | Pasó: declaraba "Out of scope: actuar sobre lo que mide" mientras `bb-usable` reiniciaba la máquina. `tools/inventario.py --check` corre en `pre-commit` y ata las dos tablas a `bin/bb`, `tools/` y `adopted/`; cazó 6 desajustes en su primera corrida, 2 de ellos defectos del propio instrumento |
| Un instrumento de cuelgue vive en la máquina y en ningún repo | **Ocurrió** | Pasó con 11 sujetos, 8 creados el 2026-09-09 siguiendo el foro de NVIDIA #358951; `/usr/local/bin/nvrm-watch.sh` existía sólo en disco. Adoptados el 2026-09-24; `bb drift` vigila 30 sujetos, antes 19 |
| `bin/bb` es el 100% del código ejecutable y ningún gate mide su cobertura | **Ocurrió** | `coverage.py` no instrumenta bash, así que `coverage-target` pasaba sin mirarlo. `tools/cobertura_bash.sh` lo mide (17.7%, 149 de 843 líneas, medido el 2026-09-24 tras añadirle `smi_salud`) y `bb-cobertura-piso` impide que baje. El número es bajo y es el hallazgo, no la solución |

## Acceptance Criteria

- `bb status` distingue instrumento armado de instrumento ausente, y cuenta los
  que faltan.
- `bb scan` termina con el número de comprobaciones que **no** pudieron correr;
  un informe con ese número por encima de cero no se presenta como limpio.
- Cada detector se verifica en los dos sentidos: dice sí cuando hay y no cuando
  no hay.
- `bb drift` detecta una divergencia introducida a propósito y vuelve a cero al
  restaurarla.
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
