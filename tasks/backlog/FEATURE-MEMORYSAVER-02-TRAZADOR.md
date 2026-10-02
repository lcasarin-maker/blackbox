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
