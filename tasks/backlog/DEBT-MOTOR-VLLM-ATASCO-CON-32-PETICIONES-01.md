---
id: DEBT-MOTOR-VLLM-ATASCO-CON-32-PETICIONES-01
kind: task
domain: GPU
title: "vLLM se atasco con 32 peticiones y 0 tokens: atribuir al cliente que las manda"
status: open
severity: P1
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-10-12
close_check: {"cmd": "grep -q atasco_vllm_atribuido tasks/evidence/DEBT-MOTOR-VLLM-ATASCO-CON-32-PETICIONES-01/medicion.txt", "expect": "exit_zero", "porque": "El 2026-10-12 a las 06:35-06:41 el motor dejo de responder (http=000) con 32 peticiones corriendo y 0 tokens avanzados; bb-vigilante-motor reinicio ai-nemotron a las 06:41:24. En los dos colapsos de memoria del 11-oct tambien habia 31-33 peticiones simultaneas. Cierra cuando se atribuya quien manda esa concurrencia (cliente, sesion, cadena) y haya un tope de concurrencia medido que evite el atasco."}
---

## Medido (2026-10-12)
- `vigilante_motor.log`: 06:35:23 chat sin respuesta (http=000, espera 120 s) fallo 1 de 3; 06:37:23 atasco por metricas 1 de 2; 06:41:24 atasco 2 de 2 y `REINICIA ai-nemotron.service`.
- Tras el reinicio el motor volvio a tener 32 peticiones corriendo apenas arranco: los clientes reintentan en tropel.
- La sesion de proyecto-D-fichas.service aparece como cliente habitual (RSS 2.7-3.4 GB); no atribuido.
- Relacionada con `DEBT-MOTOR-LLM-CAIDAS-CUDA-SIN-CAUSA-01` (caidas fatales del 08-10 oct).
## Que falta
1. Atribuir los clientes de las 32 peticiones (origen por `bb origen` o registro del gateway).
2. Medir el tope de concurrencia que el motor sostiene (vLLM `--max-num-seqs` y/o limite en el gateway) sin atascarse.
3. Que el vigilante registre el cliente mayoritario al reiniciar.
