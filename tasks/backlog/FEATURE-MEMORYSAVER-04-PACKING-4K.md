---
id: FEATURE-MEMORYSAVER-04-PACKING-4K
kind: task
domain: GPU
title: "Evaluar subasignación de tablas UVM bajo páginas de 4 KiB"
status: open
severity: P2
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-10-02
close_check: {"cmd": "python3 -m tools.verify_memory_saver --phase 04-packing-4k --evidence tasks/evidence/FEATURE-MEMORYSAVER-04-PACKING-4K", "expect": "exit_zero", "porque": "Verificación específica pendiente: ejecutar el sujeto y sus controles, no comprobar solo que el informe exista."}
---

## Fuente y dependencias

[Memory Saver](https://github.com/christopherowen/dgx-spark-memory-saver), commit `55816f0b5c88bbab3c0641f9d6f1d9fd36e5854d`. Revisión local: `tasks/evidence/MEMORY-SAVER-REVIEW-2026-10-02/review.txt` y `code-review.txt`. Dependencias: FEATURE-MEMORYSAVER-01-PERFIL, FEATURE-MEMORYSAVER-02-TRAZADOR, FEATURE-MEMORYSAVER-03-INTEGRIDAD. Dueño: coordinación de Blackbox; ejecución por asignar en la siguiente ola.

## Alcance

Medir primero cuánto consume hoy el backing de tablas UVM por carga y cuánto corresponde a tablas hoja elegibles. El parche publicado fija slots de 4096 bytes y PAGE_SIZE==65536; en nuestro kernel 4096 ese diseño ofrece un slot por página y vuelve al asignador stock. Estudiar un diseño de slots menores únicamente si la medición demuestra un coste que justifique cambiarlo.

Revisar alineación de base de tabla GPU, DMA coherente, separación de líneas de caché, offsets de mapping CPU, unmap de la página madre, espera de tracker antes de reutilizar y teardown concurrente. Conservar cargos memcg al propietario y comprobar sharing/migración de procesos, evitando transferir deuda a otra ruta. Considerar también el cargo de los descriptores del pool. El código candidato viviría en un fork separado del driver, con revisión upstream; Blackbox mantiene mediciones. Cambiar a un kernel 64 KiB es otro experimento de pila completa y no forma parte de este port.

## Criterio de cierre

Informe de coste literal del backing actual, requisitos de alineación extraídos de fuente/HAL y decisión respaldada por medidas. Si se justifica: diff mínimo revisable, compilación y matriz de integridad de 03 contra stock/candidato, más pruebas de cargo/descargo y fallos. Si los requisitos o el coste descartan el port: registrar evidencia y cerrar por la vía legal correspondiente. Evitar estimaciones de ahorro y promesas de corregir los cuelgues.

El close_check queda especificado para implementarse junto al trabajo. Verificador y evidencia de esta ficha pendientes. Registrar la ficha conserva status open y no demuestra portabilidad ni resultados GPU.

## Clasificación del impedimento — 2026-10-04

- Categoría principal: `workload_or_lab`.
- Impedimento: No hay captura de sujeto para fase 04-packing-4k; el verificador de fase ya existe.
- Evidencia faltante para cierre: Captura cruda de packing 4K, stack/hardware fijados, costo/beneficio y negativos/controles exigidos por fase.
- Siguiente acción: Solicitar captura real de packing 4K y control de referencia en hardware/runtime fijado, con los campos requeridos por verify_memory_saver; ejecutar el selector focal sobre esos recibos.
- Responsable del siguiente paso: BB; operador Luis para workload/lab.
- Cierre completo accionable hoy: no. Preparación coordinable: sí.
- Evidencias de clasificación: `tasks/backlog/FEATURE-MEMORYSAVER-04-PACKING-4K.md`, `tools/verify_memory_saver.py`, `tools/hardware_evidence.py`, `tests/test_closure_kernel.py`.
- Impedimentos de inspección: 0. El criterio original permanece intacto; esta clasificación conserva la ficha abierta.

## Criterios ejecutables de `tools.verify_memory_saver` (2026-10-14)
Los criterios ejecutables de `tools.verify_memory_saver` se miden en esta ficha: su `close_check` corre ese verificador contra la captura real del sujeto. La meta-ficha `DEBT-CLOSE-CHECK-VERIFY-MEMORY-SAVER-01`, que pedia implementarlos, se cerro el 2026-10-14 como `duplicate` (voto de Luis: consolidar en la ficha sujeto): el verificador existe y hoy, sin esa captura, sale con could_not_run (rc=2); conseguir la captura es trabajo de esta ficha.

## Avance 2026-10-14 (lote 'cierra las pendientes conforme a la opcion recomendada'): espera un disparador, no una decision
Dudosa entre sin sujeto y espera: `getconf PAGESIZE` = 4096 hoy, y el parche publicado (slots de 4096 con PAGE_SIZE 65536) aqui da un slot por pagina, asi que su sujeto literal no existe en este kernel; pero la ficha pide medir antes de decidir un diseno de slots menores, y esa medicion es la traza de FEATURE-MEMORYSAVER-02-TRAZADOR. Disparador: esa captura con bpftrace (la corre Luis). Paso exacto despues: medir el backing de tablas UVM por carga desde esa traza y decidir con el numero delante; si no justifica el port, cerrar por la via que la ficha nombra.
