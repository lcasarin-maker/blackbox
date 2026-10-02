---
id: FEATURE-1358-CGROUP-03-NATIVO
kind: task
domain: GPU
title: "Evaluar la contabilidad nativa de NVIDIA y dmem en GB10"
status: open
severity: P2
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-10-02
close_check: {"cmd": "python3 -m tools.verify_cgroup_plan --phase 03-nativo --evidence tasks/evidence/FEATURE-1358-CGROUP-03-NATIVO", "expect": "exit_zero", "porque": "Verificador específico pendiente: debe evaluar resultados reales y controles negativos descritos en esta ficha, no su mera existencia."}
---

## Contexto y dependencias

Plan derivado de [la corrección del README](../../README.md#a-measured-cgroup-accounting-gap-on-this-gb10-stack) y [el informe histórico corregido](../evidence/nvidia-1358-comment.md). Fuente de colaboración: [NVIDIA #1358](https://github.com/NVIDIA/open-gpu-kernel-modules/issues/1358).

Dependencias: FEATURE-1358-CGROUP-01-REPRO, FEATURE-1358-CGROUP-02-TRAZA.

## Alcance

Evaluar la integración dmem y los cargos existentes en NVIDIA 615.71.09 frente a la pila 580 medida. Primero revisar compatibilidad GB10, kernel, GSP y espacio de usuario; una versión visible en el repositorio necesita validación de soporte. Preparar la comparación con versiones fijadas y retorno a la pila original antes de cualquier despliegue.

Reutilizar el arnés de 01. Comprobar registro de región, cargos por propietario, límites independientes de memory y dmem, rechazo controlado, liberación, compartición y dos cgroups. Distinguir asignación, residencia y migración para evitar doble cargo. Registrar operaciones no soportadas o no ejecutadas.

## Criterio de cierre

Informe comparativo respaldado por resultados reales del arnés y controles negativos: límite inferior a una asignación, segundo cgroup independiente y liberación. Demostrar el mecanismo que contiene cada API o delimitar el hueco que persiste. could_not_run debe imprimirse junto a los resultados; una evaluación incompleta conserva la ficha abierta. El despliegue del driver queda como acción separada que requiere autorización concreta.

El comando close_check queda especificado para su implementación con el trabajo. Hoy el verificador y sus evidencias están pendientes; esta ficha registra el plan, no resultados ejecutados. Debe rechazar evidencias ausentes y datos fabricados, y tener un control negativo que pruebe que detecta el defecto de su sujeto.
