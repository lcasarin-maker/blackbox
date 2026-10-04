---
id: FEATURE-1358-CGROUP-04-PARCHE
kind: task
domain: GPU
title: "Preparar un parche NVIDIA condicionado al hueco demostrado"
status: open
severity: P2
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-10-02
close_check: {"cmd": "python3 -m tools.verify_cgroup_plan --phase 04-parche --evidence tasks/evidence/FEATURE-1358-CGROUP-04-PARCHE", "expect": "exit_zero", "porque": "Verificador específico pendiente: debe evaluar resultados reales y controles negativos descritos en esta ficha, no su mera existencia."}
---

## Contexto y dependencias

Plan derivado de [la corrección del README](../../README.md#a-measured-cgroup-accounting-gap-on-this-gb10-stack) y [el informe histórico corregido](../evidence/nvidia-1358-comment.md). Fuente de colaboración: [NVIDIA #1358](https://github.com/NVIDIA/open-gpu-kernel-modules/issues/1358).

Dependencias: FEATURE-1358-CGROUP-02-TRAZA, FEATURE-1358-CGROUP-03-NATIVO.

## Alcance

Activar esta implementación únicamente si 02 y 03 demuestran un hueco restante. Reutilizar memcg/dmem del driver y kernel; elegir el mecanismo según la memoria y el propietario observados. El cambio vive en un fork de NVIDIA/open-gpu-kernel-modules y se propone upstream. Blackbox mantiene el arnés y las evidencias.

Validar cargos y descargos en éxito, fallo parcial y rollback; contexto de workers, compartición, migración, concurrencia, teardown y dos cgroups. Prevenir doble contabilización y fugas. Construir contra la combinación compatible de módulo, GSP y espacio de usuario. Preparar diff y texto de propuesta para revisión; publicar requiere autorización.

## Criterio de cierre

Si hace falta parche: diff revisable en el fork, compilación real y resultados de 01/03 contra antes y después, con controles que fallen ante pérdida de cargo, doble cargo o liberación omitida. Si la integración nativa cubre el caso: cerrar por la vía legal de tarea innecesaria, enlazando las medidas de 03; no fabricar un parche para cumplir el plan. El cierre debe distinguir preparación de publicación.

El comando close_check queda especificado para su implementación con el trabajo. Hoy el verificador y sus evidencias están pendientes; esta ficha registra el plan, no resultados ejecutados. Debe rechazar evidencias ausentes y datos fabricados, y tener un control negativo que pruebe que detecta el defecto de su sujeto.

## Avance del swarm — 2026-10-02

Ejecutor: Luna; coordinación: Codex. Preparado: diseño condicionado y criterios para justificar un diff.
Evidencia: `tasks/evidence/FEATURE-1358-CGROUP-04-PARCHE/readiness.txt`.
Pendiente para cierre: ruta responsable y hueco residual bajo la integración nativa.
La ficha conserva status open; el informe distingue observaciones estáticas
y resultados runtime. El verificador de cierre permanece pendiente.

## Clasificación del impedimento — 2026-10-04

- Categoría principal: `workload_or_lab`.
- Impedimento: No diff está preparado, y la evidencia 03-nativo señala que GB10 runtime 615 y la integración real siguen sin probarse; todavía no se ha demostrado una regresión residual que justifique aplicar parche. El close_check exige capturas raw sujetas por fase.
- Evidencia faltante para cierre: Capturas raw ligadas de 02-traza y 03-nativo que indiquen asignación/propietario faltante y comportamiento native; sólo entonces diff/compilación más comparaciones antes/después de 01/03 o prueba de redundancia nativa que satisfaga el contrato.
- Siguiente acción: Preparación coordinable: inspeccionar readiness.txt y comparación 03-nativo contra ruta nativa; no escribir parche hasta identificar caso específico de doble cargo, pérdida o liberación. Cierre condicionado: obtener trace 02 y runtime 615 en sujeto GB10 con comparación antes/después o evidencia de cierre por vía nativa aceptada por el selector. Ref: tasks/evidence/FEATURE-1358-CGROUP-04-PARCHE/readiness.txt; tasks/evidence/FEATURE-1358-CGROUP-03-NATIVO/comparison.txt; tasks/evidence/CLOSURE-CONTROLS-2026-10-03/FEATURE-1358-CGROUP-04-PARCHE-direct-close-current.log. Ref explícita: tasks/backlog/FEATURE-1358-CGROUP-04-PARCHE.md y tasks/evidence/CLOSURE-CONTROLS-2026-10-03/FEATURE-1358-CGROUP-04-PARCHE-direct-close-current.log.
- Responsable del siguiente paso: Coordinación BB; para recuperación de históricos, custodio del artifact store si corresponde..
- Cierre completo accionable hoy: no. Preparación coordinable: sí.
- Evidencias de clasificación: `tasks/backlog/FEATURE-1358-CGROUP-04-PARCHE.md`, `tests/test_debt_registration_controls.py`, `tasks/evidence/OPEN-96-CLASSIFICATION-2026-10-04/batches/batch_09.json`, `tasks/evidence/CLOSURE-CONTROLS-2026-10-03/FEATURE-1358-CGROUP-04-PARCHE-direct-close-current.log`.
- Impedimentos de inspección: 0. El criterio original permanece intacto; esta clasificación conserva la ficha abierta.
