---
id: FEATURE-MEMORYSAVER-02-TRAZADOR
kind: task
domain: GPU
title: "Adaptar trazador de cargos kernel con atribución a cgroup"
status: open
severity: P2
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-10-02
close_check: {"cmd": "python3 -m tools.verify_memory_saver --phase 02-trazador --evidence tasks/evidence/FEATURE-MEMORYSAVER-02-TRAZADOR", "expect": "exit_zero", "porque": "Verificación específica pendiente: ejecutar el sujeto y sus controles, no comprobar solo que el informe exista."}
---

## Fuente y dependencias

[Memory Saver](https://github.com/christopherowen/dgx-spark-memory-saver), commit `55816f0b5c88bbab3c0641f9d6f1d9fd36e5854d`. Revisión local: `tasks/evidence/MEMORY-SAVER-REVIEW-2026-10-02/review.txt` y `code-review.txt`. Dependencias: FEATURE-1358-CGROUP-01-REPRO. Dueño: coordinación de Blackbox; ejecución por asignar en la siguiente ola.

## Alcance

Revisar tools/kernel-charges.bt del proyecto como referencia y adaptar sus puntos de entrada/salida al ABI del kernel que realmente ejecuta el host. Validar el probe contra fuentes/símbolos de esa versión. Registrar identidad de cgroup/memcg y distinguir cgroup del hilo de cgroup propietario del cargo; stack y comm solos no prueban dueño. Imprimir mapas de atribución antes de limpiarlos, conteos de cargos/descargos, fallos, duplicados y órdenes inconsistentes. Usar filtros de los scopes del arnés para acotar observación. Reutilizar herramientas instaladas y tener fallback explícito cuando faltan permisos. Esta ficha produce el instrumento que necesita FEATURE-1358-CGROUP-02-TRAZA; esa ficha conserva la responsabilidad de trazar las APIs reales.

## Criterio de cierre

Traza real del control CPU y de una ejecución sin asignación, más una asignación CUDA acotada cuando haya permiso. Cargos/descargos, dueño y pilas disponibles con comandos y salida literales. El control debe detectar pérdida del registro de atribución; probe inexistente o acceso denegado se reporta como could_not_run. Las asignaciones no cobradas al memcg quedan fuera de la observación de ese probe, límite que debe declararse.

El close_check queda especificado para implementarse junto al trabajo. Verificador y evidencia de esta ficha pendientes. Registrar la ficha conserva status open y no demuestra portabilidad ni resultados GPU.

## Avance — 2026-10-02

Preparado `tools/kernel_charges.bt` para los prototipos 6.17 presentes en los
headers del host. Emite cargos/descargos, fallos, duplicados, órdenes discordantes,
páginas aún vivas y mapas agregados tanto en snapshots como al salir. Filtra los
eventos de cargo por cgroup numérico del task ejecutor. La identidad del dueño
real queda `unknown`: UVM puede activar un memcg a partir de un `mm`, y el cgroup
del task ejecutor no acredita ese memcg. El ledger por dirección de página tampoco
prueba ownership.

Evidencia ABI y control negativo offline:
`tasks/evidence/FEATURE-MEMORYSAVER-02-TRAZADOR/abi-check.txt` y
`probe-list.txt`. Los headers confirman firmas, pero bpftrace exige root incluso
para `-d`/listar probes; parser, símbolos en ejecución, captura runtime y CUDA
quedan `could_not_run`. No se afirma que el script compile o que los probes estén
disponibles. Esta ficha sigue abierta.


## Índice de propuestas registradas del swarm NVIDIA categoría 721

- **`BB-UMA-GPU-ALLOCATABLE-HEADROOM-SEMANTICS`** — On GB10 UMA, general system allocations reduce the pool available for GPU allocation. Forum users say nvtop displays GPU memory but excludes CPU allocations, while some released versions fail on Spark. This can hide reduced… Fuente: [351284](https://forums.developer.nvidia.com/t/nvtop-with-dgx-spark-unified-memory-support/351284/1).

## Clasificación del impedimento — 2026-10-04

- Categoría principal: `privileged_access`.
- Impedimento: ABI y controles offline existen; bpftrace exige root incluso para listar/compilar probes y el host no produjo símbolos/captura runtime/CUDA.
- Evidencia faltante para cierre: ABI y controles offline existen; bpftrace exige root incluso para listar/compilar probes y el host no produjo símbolos/captura runtime/CUDA.
- Siguiente acción: Coordinación BB: dejar comandos/output acotados listos y validar parser con fixtures; operador Luis: autorizar y capturar probes en host canary con root. Ref explícita: tasks/backlog/FEATURE-MEMORYSAVER-02-TRAZADOR.md y tests/test_debt_registration_controls.py. Ref explícita: tasks/backlog/FEATURE-MEMORYSAVER-02-TRAZADOR.md y tasks/evidence/CLOSURE-CONTROLS-2026-10-03/FEATURE-MEMORYSAVER-02-TRAZADOR-direct-close-current.log.
- Responsable del siguiente paso: Coordinación BB prepara/implementa; cuando la acción requiere root/lab/hardware, operador Luis aporta y ejecuta el sujeto indicado..
- Cierre completo accionable hoy: no. Preparación coordinable: sí.
- Evidencias de clasificación: `tasks/backlog/FEATURE-MEMORYSAVER-02-TRAZADOR.md`, `tests/test_debt_registration_controls.py`, `tasks/evidence/OPEN-96-CLASSIFICATION-2026-10-04/batches/batch_03.json`, `tasks/evidence/CLOSURE-CONTROLS-2026-10-03/FEATURE-MEMORYSAVER-02-TRAZADOR-direct-close-current.log`.
- Impedimentos de inspección: 0. El criterio original permanece intacto; esta clasificación conserva la ficha abierta.

## Criterios ejecutables de `tools.verify_memory_saver` (2026-10-14)
Los criterios ejecutables de `tools.verify_memory_saver` se miden en esta ficha: su `close_check` corre ese verificador contra la captura real del sujeto. La meta-ficha `DEBT-CLOSE-CHECK-VERIFY-MEMORY-SAVER-01`, que pedia implementarlos, se cerro el 2026-10-14 como `duplicate` (voto de Luis: consolidar en la ficha sujeto): el verificador existe y hoy, sin esa captura, sale con could_not_run (rc=2); conseguir la captura es trabajo de esta ficha.

## Avance 2026-10-14 (lote 'cierra las pendientes conforme a la opcion recomendada'): espera un disparador, no una decision
Disparador: una captura con bpftrace que corre Luis en persona (bpftrace es root total: no se sella en bb-root-run). Paso exacto: `sudo bpftrace tools/kernel_charges.bt` durante el control CPU, una corrida sin asignacion y una asignacion CUDA acotada de `tools/cgroup_repro.py`, guardando la salida en `tasks/evidence/FEATURE-MEMORYSAVER-02-TRAZADOR/`; despues `python3 -m tools.verify_memory_saver --phase 02-trazador --evidence tasks/evidence/FEATURE-MEMORYSAVER-02-TRAZADOR`. Es la misma captura que pide FEATURE-1358-CGROUP-02-TRAZA.
