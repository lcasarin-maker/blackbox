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

## Out of scope

- Interfaz gráfica o dashboard: esto se lee desde una terminal o desde un agente.
- Monitoreo multi-máquina o por SSH: hay una sola unidad.
- Actuar sobre lo que mide. `bb protect` es la única excepción, y es explícita.
- Duplicar telemetría de GPU y térmica: la produce `Atlas/tools/atom_gpu_telemetry.py`.

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

## Risks

| Risk | Likelihood | Mitigation |
| --- | --- | --- |
| Un instrumento deja de escribir en silencio | Alta | `bb status` mira la antigüedad de los datos sólo donde hay un artefacto que revisar (sar, memory-monitor, telemetría de Atlas: "por sus datos, no por la unit"); el resto (timer del muestreo, clock lock de GPU, earlyoom) sigue leyendo `systemctl is-active`, que no detecta una unit activa que dejó de trabajar -- verificado 2026-09-16, gap real y sin cerrar en esos tres |
| Una comprobación que no puede fallar da falsa confianza | Alta | Cada gate se verifica con control negativo; `bb scan` cuenta las que no pudieron correr |
| El propio muestreo compite por la memoria unificada | Media | Sólo lee `/proc` y endpoints ya existentes; `Nice=19` e `IOSchedulingClass=idle` |
| Los umbrales de PSI vienen de otra máquina | Baja | Calibrados 2026-09-23 contra los dos congelamientos propios del 2026-09-22/23 sobre 19 804 muestras (2026-09-08 07:57 -> 2026-09-23 10:53): el corte pasó de nivel instantáneo a duración sostenida (≥10 % durante ≥5 min), porque el nivel se equivoca en las dos direcciones — seis excursiones sanas llegaron a 98.53 % y un congelamiento real bajó a 48.80 %. `tools/calibra_psi.py` re-deriva los cortes y sale 1 si dejan pasar un incidente o disparan en una muestra sana. Sigue abierto: n=2 del lado positivo y las dos la misma noche, y sólo el canal de memoria está calibrado — `io_some`/`cpu_some` se imprimen sin etiqueta a propósito |
| Un repo adoptado diverge de lo desplegado sin avisar | Media | `bb drift` compara repo contra máquina y se verificó en ambos sentidos |

## Acceptance Criteria

- `bb status` distingue instrumento armado de instrumento ausente, y cuenta los
  que faltan.
- `bb scan` termina con el número de comprobaciones que **no** pudieron correr;
  un informe con ese número por encima de cero no se presenta como limpio.
- Cada detector se verifica en los dos sentidos: dice sí cuando hay y no cuando
  no hay.
- `bb drift` detecta una divergencia introducida a propósito y vuelve a cero al
  restaurarla.
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
