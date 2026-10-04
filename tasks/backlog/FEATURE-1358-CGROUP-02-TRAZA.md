---
id: FEATURE-1358-CGROUP-02-TRAZA
kind: task
domain: GPU
title: "Identificar el camino de asignación y el propietario del cargo"
status: open
severity: P2
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-10-02
close_check: {"cmd": "python3 -m tools.verify_cgroup_plan --phase 02-traza --evidence tasks/evidence/FEATURE-1358-CGROUP-02-TRAZA", "expect": "exit_zero", "porque": "Verificador específico pendiente: debe evaluar resultados reales y controles negativos descritos en esta ficha, no su mera existencia."}
---

## Contexto y dependencias

Plan derivado de [la corrección del README](../../README.md#a-measured-cgroup-accounting-gap-on-this-gb10-stack) y [el informe histórico corregido](../evidence/nvidia-1358-comment.md). Fuente de colaboración: [NVIDIA #1358](https://github.com/NVIDIA/open-gpu-kernel-modules/issues/1358).

Dependencias: FEATURE-1358-CGROUP-01-REPRO.

## Alcance

Sobre la pila de la reproducción, localizar la entrada CUDA y su camino por RM/UVM/allocador del kernel. Reutilizar fuentes y herramientas de trazado disponibles; registrar símbolos, versión y límites de observabilidad. Verificar qué memcg está activo, qué flags se usan y cuándo el trabajo cambia de contexto o pasa a un worker.

Comparar los helpers memcg y __GFP_ACCOUNT existentes en 580.178.04 con la ruta realmente observada. Separar NV_ALLOC_PAGES_NODE_SKIP_RECLAIM y RmNumaAllocSkipReclaimPercent del mecanismo de cargo. Una interpretación de ensamblador debe quedar identificada como inferencia.

## Criterio de cierre

Mapa respaldado por trazas de la asignación real, con archivos/líneas de la versión correspondiente y dueño del cargo. Contrastar una asignación CPU contabilizada y una ejecución sin la llamada GPU. Declarar lo que no pudo trazarse. La mera presencia de helpers en el código no demuestra que la ruta los ejecute.

El comando close_check queda especificado para su implementación con el trabajo. Hoy el verificador y sus evidencias están pendientes; esta ficha registra el plan, no resultados ejecutados. Debe rechazar evidencias ausentes y datos fabricados, y tener un control negativo que pruebe que detecta el defecto de su sujeto.

## Avance del swarm — 2026-10-02

Ejecutor: Luna; coordinación: Codex. Preparado: mapa estático y comprobación de símbolos.
Evidencia: `tasks/evidence/FEATURE-1358-CGROUP-02-TRAZA/trace-map.txt`.
Pendiente para cierre: traza dinámica de memcg/flags/worker; el acceso a probes requiere privilegios root.
La ficha conserva status open; el informe distingue observaciones estáticas
y resultados runtime. El verificador de cierre permanece pendiente.

## Avance de instrumentación — 2026-10-02

Disponible un probe preparatorio en `tools/kernel_charges.bt`, con firmas que
coinciden con los headers 6.17 instalados. El mapa y el control negativo offline
están en `tasks/evidence/FEATURE-1358-CGROUP-02-TRAZA/trace-map.txt` y
`tasks/evidence/FEATURE-MEMORYSAVER-02-TRAZADOR/abi-check.txt`. El probe etiqueta
cgroup del ejecutor y reporta el owner como desconocido; `set_active_memcg(mm)`
impide equiparar ambas identidades. No hubo parse/attach/captura por la barrera
de root. Dueño real, flags observados y transición a worker siguen pendientes;
esta ficha conserva status open.

**FEATURE-FORUM-UVM-TRACE-CAPABILITY-01 (delta del foro 357848).** En GB10/SM121 con driver 580.95.05, CUDA 13.1 y Nsight Systems 2026.1.1, un operador no pudo capturar page faults/migraciones UVM y NVIDIA respondió que el perfilado UVM no está soportado en Spark en esa combinación ([357848](https://forums.developer.nvidia.com/t/357848)). Reusar el mapa de traza de esta ficha para anotar capacidad/no-capacidad por versión; no inferir migraciones UVM a partir de memoria host, faults CPU agregados o `nvidia-smi`, ni abrir un probe separado que Blackbox no usa. Una alternativa solo se admite tras soporte del proveedor y una prueba conocida de UVM contra control host.

## Clasificación del impedimento — 2026-10-04

- Categoría principal: `privileged_access`.
- Impedimento: El mapa estático y ABI probe están disponibles; la captura dinámica quedó sin ejecutar por barrera root.
- Evidencia faltante para cierre: Traza memcg/flags/worker con dueño real, transición observada y control negativo en kernel 6.17; identidad del stack.
- Siguiente acción: Solicitar al operador captura acotada del probe en lab con privilegios root, identidad kernel, owner/flags/transición worker y control negativo; preservar stderr y resultado de attach.
- Responsable del siguiente paso: BB; operador Luis para acceso root/lab.
- Cierre completo accionable hoy: no. Preparación coordinable: sí.
- Evidencias de clasificación: `tasks/backlog/FEATURE-1358-CGROUP-02-TRAZA.md`, `tasks/evidence/FEATURE-1358-CGROUP-02-TRAZA/trace-map.txt`, `tools/kernel_charges.bt`, `tools/verify_cgroup_plan.py`, `tests/test_closure_kernel_selectors.py`.
- Impedimentos de inspección: 0. El criterio original permanece intacto; esta clasificación conserva la ficha abierta.
