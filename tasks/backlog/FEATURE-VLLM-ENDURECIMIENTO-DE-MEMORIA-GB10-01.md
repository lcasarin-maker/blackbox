---
id: FEATURE-VLLM-ENDURECIMIENTO-DE-MEMORIA-GB10-01
kind: task
domain: GPU
title: "Endurecer vLLM en GB10: gpu-memory-utilization, expandable_segments y tope de concurrencia, con medicion"
status: open
severity: P2
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-10-12
close_check: {"cmd": "grep -qx vllm_memoria_medida tasks/evidence/FEATURE-VLLM-ENDURECIMIENTO-DE-MEMORIA-GB10-01/medicion.txt", "expect": "exit_zero", "porque": "Voto de Luis 2026-10-12. Cierra con una medicion de memoria y atascos antes y despues de cada ajuste en el motor local, con la configuracion anotada y su inverso."}
---

## Antecedentes (lectura)
- vLLM #46307: en GB10 `gpu_memory_utilization` no es tope duro durante el arranque (una configuracion de 0.70 dejo la maquina inutilizable).
- vLLM #55569: `PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True` mantuvo plana la memoria del host en prefills largos.
- Aqui: `/srv/ai/gateway/active_engine.json` declara `gpu_memory_utilization=0.3`, `container_memory_gb=75`, `admission_check_gb=68`; el motor se atasco con 32 peticiones el 2026-10-12 06:35 (`DEBT-MOTOR-VLLM-ATASCO-CON-32-PETICIONES-01`).
## Plan por partes
1. Medir el consumo real del motor (GPU y cgroup) a distintas utilizaciones y concurrencias sin tocar produccion en horas de uso.
2. Probar `expandable_segments` y `--max-num-seqs` menor; anotar tokens/s y atascos.
3. La configuracion del motor es de la pila de IA, no de bb: bb mide y propone; el cambio lo aplica Luis en `active_engine.json` con su respaldo.

## Residuo del vigilante (2026-10-12)

De FEATURE-VIGILANTE-MEMAVAILABLE-UMA-01 (cerrada, medido negativo): la rampa de carga de vLLM (29 a 2.5 GiB en 9 s, segun la cosecha) no tiene muestra propia en nuestras series. Medir MemAvailable a 1 Hz durante el siguiente arranque de modelo antes de promoverlo.

## Correccion del residuo (2026-10-12)
El residuo anterior decia que la rampa de vLLM no tenia muestra propia. Falso: las rafagas de `bb sample` la contienen (mayor caida 20.9 GiB en 9 s, ninguna cruza 8 GiB). Ver medicion.txt. Queda por medir antes/despues de cada ajuste cuando Luis lo aplique.

## Defecto del close_check corregido (2026-10-13)
`grep -q vllm_memoria_medida medicion.txt` daba exit 0 con la ficha explicitamente abierta: la propia frase "NO cerrado: falta vllm_memoria_medida" de `medicion.txt` contiene el centinela. Se cambia a `grep -qx` (la linea entera debe ser el centinela). Antes: rc=0 (falso cierre); despues: rc=1; control positivo: un archivo cuya unica linea es el centinela da rc=0.
