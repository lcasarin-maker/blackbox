---
id: FEATURE-LIMITADOR-LD-PRELOAD-CUDA-GB10-01
kind: task
domain: GPU
title: "Evaluar un limitador LD_PRELOAD de asignaciones CUDA en GB10 con prueba negativa de variable ausente"
status: open
severity: P2
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-10-12
close_check: {"cmd": "grep -q limitador_cuda_probado tasks/evidence/FEATURE-LIMITADOR-LD-PRELOAD-CUDA-GB10-01/medicion.txt", "expect": "exit_zero", "porque": "Voto de Luis 2026-10-12: traer y probar las soluciones caseras. Cierra con una medicion en esta maquina: un limitador de asignaciones CUDA aplicado a un proceso de prueba que rechaza lo que supera su tope, un control negativo con la variable ausente (debe rechazar o registrar, no correr sin tope) y su efecto en vLLM medido en un contenedor de prueba."}
---

## Antecedentes (lectura, 2026-10-12)
Un reporte (modular/modular #6488) menciona un limitador LD_PRELOAD de 96 GB para GB10 sin fuente publicada. Proyectos de vGPU (HAMi-core y similares) interceptan `cuMemAlloc` y aplican `CUDA_DEVICE_MEMORY_LIMIT`; KAI-Scheduler #2156 documenta su fallo tipico: si la variable falta, el proceso corre SIN tope mientras registra que aplica.
## Plan por partes
1. Cosechar el codigo del limitador (licencia Apache-2.0 o la que tenga) en un directorio aislado, solo lectura.
2. Prueba minima sin torch: un programa Python con `ctypes` sobre `libcuda.so.1` que pide 1 GiB con y sin limitador a 512 MiB; verificar rechazo y control negativo (variable ausente).
3. Valorar el costo: la memoria unificada de GB10 se asigna tambien por rutas que el limitador podria no ver (`cuMemCreate`, UVM): medir cual cubre.
4. Si aplica, integrarlo detras del portero como opcion por clase de contenedor.
