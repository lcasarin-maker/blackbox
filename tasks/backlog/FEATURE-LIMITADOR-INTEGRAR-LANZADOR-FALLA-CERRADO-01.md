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

## Avance 2026-10-16: el tope por cgroup (dmem.max) ya tiene codigo, pruebas y scripts sellados; falta aprobarlos y aplicarlos
Cambio de camino, con el motivo: la pasada del 2026-10-12 (pasos 1 y 2 de arriba, `bb limita`) cubre el limitador de espacio de usuario (HAMi-core), y su biblioteca `libvgpu.so` no esta en este equipo (`find / -name 'libvgpu*'`: sin resultados). El modulo NVIDIA parcheado cargado desde el 2026-10-12 ya COBRA la memoria de GPU por cgroup y hace cumplir `dmem.max` en el kernel (ficha `FEATURE-DMEM-PARCHE-REGION-Y-COBRO-SYSMEM-GB10-01`: con 512M un pedido de 1 GiB falla; el mismo pedido pasa sin tope). Eso falla cerrado por construccion, asi que el hueco que quedaba era PONER el tope.

Hecho (commit de esta fecha):
- `tools/dmem_tope.py` + `bb dmem-tope` + interruptor `dmem_tope` (off/observar/actuar): mide sin root si los topes caben y, en `actuar`, llama a `sudo -n bb-root-run dmem-tope-aplicar`. 27 pruebas, 100 % de cobertura del modulo.
- `adopted/root-scripts/dmem-tope-aplicar.sh` y `dmem-tope-quitar.sh`: sellados, sin argumentos; topes 40 GiB (motor) y 8 GiB (`user.slice`), calculados de `gpumem_historial.jsonl` (picos medidos: motor 35.23 GiB; user.slice 5.26 y 25.89 GiB en dos arranques; capacidad de la region 50.1 GiB). Se niegan (rc 3) si el consumo actual ya pasa el tope, si el motor esta en mas de un cgroup, si la region no es una, y devuelven los valores previos si la escritura o la lectura de vuelta fallan.
- Controles negativos corridos: quitar la guarda de consumo, quitar la restauracion y quitar la guarda de dos cgroups hace fallar una prueba cada uno.
- Medicion real en `observar` (2026-10-16): `aplicaria`; motor 34042048784 B, user.slice 624801765 B, capacidad 53794045952 B. Con `/proc` vacio el mismo comando da `rechaza` y rc 3 (NOT_COLLECTED).

Falta (por eso la ficha sigue abierta):
1. Luis aprueba el manifiesto nuevo (`python3 -m tools.bb_root_manifest --propose` imprime el comando `sudo sh -c ...`; ahora lista 11 scripts).
2. Poner `dmem_tope` en `observar` en `interruptores.json`, mirar 1 semana, y pasar a `actuar` en una ventana con el motor sirviendo; medir con `bb gpumem` y registrar `limitador_integrado_probado` en `medicion.txt`.
3. Paso 3 original (vLLM real bajo el limitador): con dmem el motor ya corre cobrado; la prueba pendiente es que arranque y sirva con `dmem.max`=40 GiB sin que su presupuesto de arranque (`gpu-memory-utilization`) lo choque contra el tope.
4. Paso 4 (memoria fijada): medido el 2026-10-16 (`FEATURE-DMEM-CLASES-DE-MEMORIA-POR-CGROUP-01`): la memoria fijada y la managed SI tienen tope, el de `memory.max` (el cgroup muere por OOM); el motor tiene 75 GiB y `user-1000.slice` 48 GiB. `bb dmem-tope` avisa si `memory.max` esta en `max`. Queda por decidir si el tope de `user.slice` entero (hoy `max`) debe ponerse.
