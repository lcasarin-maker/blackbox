---
id: FEATURE-1358-CGROUP-01-REPRO
kind: task
domain: GPU
title: "Reproducir y delimitar el hueco de contabilidad CUDA"
status: open
severity: P2
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-10-02
close_check: {"cmd": "python3 -m tools.verify_cgroup_plan --phase 01-repro --evidence tasks/evidence/FEATURE-1358-CGROUP-01-REPRO", "expect": "exit_zero", "porque": "Verificador específico pendiente: debe evaluar resultados reales y controles negativos descritos en esta ficha, no su mera existencia."}
---

## Contexto y dependencias

Plan derivado de [la corrección del README](../../README.md#a-measured-cgroup-accounting-gap-on-this-gb10-stack) y [el informe histórico corregido](../evidence/nvidia-1358-comment.md). Fuente de colaboración: [NVIDIA #1358](https://github.com/NVIDIA/open-gpu-kernel-modules/issues/1358).

Dependencias: ninguna; punto de entrada del plan.

## Alcance

Reutilizar systemd-run, los archivos cgroup v2 y las capturas de Blackbox antes de añadir instrumentación. Crear un reproductor acotado que distinga cudaMalloc, cudaMallocManaged y la API realmente usada por PyTorch. Registrar versiones, boot ID, cgroup efectivo, tamaños solicitados, sincronización, memoria residente, memory.current/events/pressure, dmem.capacity/current y MemAvailable antes, durante y después de liberar.

Control positivo: asignación CPU anónima tocada que sí incremente memory.current. Control negativo: ejecución sin asignación GPU. Repetir con dos cgroups aislados y conservar comando, salida, tiempos y errores de colección. Usar asignaciones pequeñas y límites explícitos; la reproducción busca contabilidad, no provocar un cuelgue.

## Criterio de cierre

El arnés identifica cada API y su cgroup; el control CPU demuestra que el instrumento detecta cargos. Publicar las medidas originales y la repetición, incluida cualquier diferencia. Liberación y sincronización deben quedar observadas. Un resultado sin hueco también cierra la investigación si delimita exactamente la pila donde ocurre y donde no ocurre.

El comando close_check queda especificado para su implementación con el trabajo. Hoy el verificador y sus evidencias están pendientes; esta ficha registra el plan, no resultados ejecutados. Debe rechazar evidencias ausentes y datos fabricados, y tener un control negativo que pruebe que detecta el defecto de su sujeto.
