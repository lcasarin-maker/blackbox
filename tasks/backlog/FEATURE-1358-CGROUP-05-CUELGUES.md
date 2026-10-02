---
id: FEATURE-1358-CGROUP-05-CUELGUES
kind: task
domain: GPU
title: "Medir por separado contención y efecto sobre los cuelgues de 1358"
status: open
severity: P2
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-10-02
close_check: {"cmd": "python3 -m tools.verify_cgroup_plan --phase 05-cuelgues --evidence tasks/evidence/FEATURE-1358-CGROUP-05-CUELGUES", "expect": "exit_zero", "porque": "Verificador específico pendiente: debe evaluar resultados reales y controles negativos descritos en esta ficha, no su mera existencia."}
---

## Contexto y dependencias

Plan derivado de [la corrección del README](../../README.md#a-measured-cgroup-accounting-gap-on-this-gb10-stack) y [el informe histórico corregido](../evidence/nvidia-1358-comment.md). Fuente de colaboración: [NVIDIA #1358](https://github.com/NVIDIA/open-gpu-kernel-modules/issues/1358).

Dependencias: FEATURE-1358-CGROUP-03-NATIVO.

## Alcance

Usar la solución nativa evaluada en 03 o, cuando exista, el parche de 04. Preparar comparación de carga acotada con versiones, configuración, clocks, watchdogs y ventanas de observación fijados. Reutilizar muestras, PSI, NVRM, sonda de servicio y exportación externa de Blackbox.

Separar rechazo controlado de asignaciones de pérdida de servicio o cuelgue del host. Conservar timestamps del primer error, última respuesta útil, watchdog y reinicio. Incluir controles sanos y reportar todos los ensayos y fallos de colección. Preparar un paquete reproducible para colaboración en #1358.

## Criterio de cierre

Resultados con exposición y número de ensayos literales, capturas y controles sanos; hipótesis causal limitada a lo observado. Una ventana sin cuelgues se informa como ventana observada. Contención demostrada puede coexistir con cuelgues pendientes de explicación. El análisis y el post para copiar deben conservar esa distinción; publicar el post es una acción separada.

El comando close_check queda especificado para su implementación con el trabajo. Hoy el verificador y sus evidencias están pendientes; esta ficha registra el plan, no resultados ejecutados. Debe rechazar evidencias ausentes y datos fabricados, y tener un control negativo que pruebe que detecta el defecto de su sujeto.
