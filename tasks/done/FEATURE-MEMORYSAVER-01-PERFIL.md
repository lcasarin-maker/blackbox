---
id: FEATURE-MEMORYSAVER-01-PERFIL
kind: task
domain: GPU
title: "Capturar perfil real de páginas y UVM para comparar ensayos"
status: done
reason: "La captura de esta pila registra por separado page size, UVM version/srcversion cargado y en disco, parámetro UVM, THP y contexto de reserva. Los controles distinguen parámetro no soportado, módulo ausente, lecturas denegadas e identidad distinta."
closed_at: 2026-10-02
evidence: {"pass": "tasks/evidence/FEATURE-MEMORYSAVER-01-PERFIL/pass.txt", "fail": "tasks/evidence/FEATURE-MEMORYSAVER-01-PERFIL/fail.txt", "e2e": "tasks/evidence/FEATURE-MEMORYSAVER-01-PERFIL/e2e.txt"}
closure_type: fixed
severity: P2
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-10-02
close_check: {"cmd": "python3 -m pytest -q tests/test_memory_capture_and_cuda_integrity.py -k 'profile or read_text or command'", "expect": "exit_zero", "porque": "Comprueba captura real del host y fixtures de página, parámetro, lectura y diferencias entre UVM cargado y en disco."}
---

## Fuente y dependencias

[Memory Saver](https://github.com/christopherowen/dgx-spark-memory-saver), commit `55816f0b5c88bbab3c0641f9d6f1d9fd36e5854d`. Revisión local: `tasks/evidence/MEMORY-SAVER-REVIEW-2026-10-02/review.txt` y `code-review.txt`. Dependencias: ninguna. Dueño: coordinación de Blackbox; ejecución por asignar en la siguiente ola.

## Alcance

Reutilizar uname, sysconf/getconf, sysfs y las capturas existentes. Añadir al registro de ensayo el tamaño de página CPU real, kernel, driver, identidad del UVM cargado y su parámetro uvm_pack_sysmem_leaf_tables cuando exista. Separar módulo cargado, artefacto en disco y parámetro ausente de fallos de lectura. Registrar THP y reservas del host como contexto; preservar su configuración. Esta captura complementa FEATURE-1358-CGROUP-03-NATIVO y permite comparar pilas sin confundir cambios simultáneos.

## Criterio de cierre

Captura real en la pila actual 4 KiB y controles de fixtures que distingan 64 KiB, UVM stock, parámetro presente, lectura prohibida e identidad cargada/disco diferente. El reporte debe mostrar unsupported/absent/collection_failed por separado. Integrar la información en el arnés o telemetría existente, sin crear un segundo inventario del host.

## Cierre — 2026-10-02

Captura real en `tasks/evidence/FEATURE-MEMORYSAVER-01-PERFIL/profile.json`:
PAGE_SIZE=4096, kernel 6.17.0-1032-nvidia, UVM cargado y en disco 580.178.04,
parámetro del parche ausente/unsupported, THP y contexto de reserva registrados.
La captura también se integra en `host.memory_profile` de
`tasks/evidence/FEATURE-1358-CGROUP-01-REPRO/run-profile-integration.json`.
Fixtures y salida del control negativo: `tasks/evidence/FEATURE-MEMORYSAVER-03-INTEGRIDAD/verification.txt`.
Se cierra el perfil de esta pila; no afirma portabilidad.

## Root Cause

Las capturas de ensayo registraban kernel y memoria, pero omitían la página base
y la identidad UVM cargada frente a la versión instalada. Eso impedía distinguir
un ensayo 4 KiB stock de una versión con el parámetro del parche.

## Regression Test

`tests/test_memory_capture_and_cuda_integrity.py` cubre página 4 KiB y 64 KiB,
parámetro ausente/presente, módulo ausente, UVM version/srcversion cargado y en
disco, error de lectura y archivo ausente.

## Verification Evidence

Resultados literales en `tasks/evidence/FEATURE-MEMORYSAVER-01-PERFIL/{pass,fail,e2e}.txt`.
El registro de captura queda en `profile.json` y en el host del ensayo integrado.

## Complemento del dive, con límites

[384853](https://forums.developer.nvidia.com/t/384853) anuncia OScomunitario64K y dispram framebuffer→KV, y reconoce fallo mmap/safetensors que requiere eager. Sus ganancias son cifras del autor, sin medición/auditoría propia. Host actualgetconfPAGESIZE=4096. Incorporar perfil por versión/page-size y comparación mmap/eager con transientpeak e integridad; [373341](https://forums.developer.nvidia.com/t/373341) relata hardfreeze con carga que evita mmap y sube memoria. No instalar imagen/kernel/daemon comunitarios como fix hasta revisar fuentes/firma/OEM, compatibilidad y retorno probado aOSoriginal. Consolidar con las fichas de integridad/packing existentes, evitando duplicar investigación64K.
