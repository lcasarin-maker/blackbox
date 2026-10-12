---
id: FEATURE-LIMITADOR-INTEGRAR-LANZADOR-FALLA-CERRADO-01
kind: task
domain: GPU
title: "Lanzador del limitador CUDA que falla cerrado, interruptor y prueba con vLLM real"
status: open
severity: P2
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-10-12
close_check: {"cmd": "grep -q limitador_integrado_probado tasks/evidence/FEATURE-LIMITADOR-INTEGRAR-LANZADOR-FALLA-CERRADO-01/medicion.txt", "expect": "exit_zero", "porque": "La medicion de laboratorio (FEATURE-LIMITADOR-LD-PRELOAD-CUDA-GB10-01) prueba que HAMi-core limita device y managed en GB10, pero falla abierto sin variable, falsea mem_get_info y no cubre memoria fijada. Cierra con un lanzador que se niega a arrancar si la variable falta o la biblioteca no es la Debug verificada, registrado como interruptor, y una medicion del arranque real de vLLM con el limitador."}
---

## Por hacer (en este orden, cada paso con su medicion)
1. Lanzador `bb limita -- <cmd>`: exige `CUDA_DEVICE_MEMORY_LIMIT`, verifica que `libvgpu.so` exporta simbolos `cu*` (`nm -D`), y hace una asignacion centinela sobre el tope que DEBE fallar antes de lanzar el comando; si no falla, no lanza (fallo cerrado).
2. Interruptor `limitador` (off/observar/actuar) en `tools/interruptores.py`: en `observar` solo corre la centinela y registra.
3. Medir vLLM real bajo el limitador (mem_get_info falseado cambia su presupuesto) en el laboratorio de contenedores, no en el daemon de produccion.
4. Memoria fijada del anfitrion: sin cobertura; decidir si se acota con cgroup (cuenta) o se acepta.
