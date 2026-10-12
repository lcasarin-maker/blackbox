---
id: FEATURE-LIMITADOR-LD-PRELOAD-CUDA-GB10-01
kind: task
domain: GPU
title: "Evaluar un limitador LD_PRELOAD de asignaciones CUDA en GB10 con control negativo"
status: done
closed_at: 2026-10-12
closure_type: relocated_prior_verification
evidence: {"pass": "tasks/evidence/FEATURE-LIMITADOR-LD-PRELOAD-CUDA-GB10-01/pass.txt", "fail": "tasks/evidence/FEATURE-LIMITADOR-LD-PRELOAD-CUDA-GB10-01/fail.txt", "e2e": "tasks/evidence/FEATURE-LIMITADOR-LD-PRELOAD-CUDA-GB10-01/e2e.txt", "measure": "tasks/evidence/FEATURE-LIMITADOR-LD-PRELOAD-CUDA-GB10-01/medicion.txt", "harvest": "tasks/evidence/FEATURE-LIMITADOR-LD-PRELOAD-CUDA-GB10-01/cosecha.txt", "torch": "tasks/evidence/FEATURE-LIMITADOR-LD-PRELOAD-CUDA-GB10-01/prueba_torch.py.txt", "rutas": "tasks/evidence/FEATURE-LIMITADOR-LD-PRELOAD-CUDA-GB10-01/prueba_rutas.py.txt"}
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

## Root Cause
No existia medicion de si un limitador LD_PRELOAD de asignaciones CUDA aplica en GB10.

## Regression Test
Las pruebas B y D de medicion.txt: B rechaza sobre el tope; D (sin variable) corre sin tope. Si el limitador estuviera mal compilado (Release), B pasaria 1024 MiB y el cierre no se cumpliria.

## Verification Evidence
Ver medicion.txt: HAMi-core compilado aarch64 funciona con torch 2.13+cu130 y driver 580.178.04; cubre device y managed; no cubre memoria fijada del anfitrion; falla abierto sin variable. Siguiente: FEATURE-LIMITADOR-INTEGRAR-LANZADOR-FALLA-CERRADO-01.
