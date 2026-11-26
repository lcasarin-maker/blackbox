---
id: FEATURE-DMEM-CLASES-DE-MEMORIA-POR-CGROUP-01
kind: task
domain: GPU
title: "Cada clase de memoria de CUDA tiene su tope: device en dmem.max, managed y pinned en memory.max (medido en GB10)"
status: done
closed_at: 2026-10-16
closure_type: fixed
reason: "El hueco declarado el 2026-10-16 ('pinned y managed no se cobran al cgroup, asi que dmem.max no las frena') se midio y NO es un hueco de contencion: managed y pinned se cobran a memory.current y memory.max las frena (OOM del cgroup, exit 137); device se cobra a dmem y memory.max no lo frena. Verificador, captura reproducible y aviso en bb dmem-tope cuando memory.max esta en max."
evidence: {"pass": "tasks/evidence/FEATURE-DMEM-CLASES-DE-MEMORIA-POR-CGROUP-01.pass.txt", "fail": "tasks/evidence/FEATURE-DMEM-CLASES-DE-MEMORIA-POR-CGROUP-01.fail.txt", "e2e": "tasks/evidence/FEATURE-DMEM-CLASES-DE-MEMORIA-POR-CGROUP-01.e2e.txt"}
severity: P2
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-10-16
close_check: {"cmd": "python3 -m tools.verify_clases_memoria tasks/evidence/FEATURE-DMEM-CLASES-DE-MEMORIA-POR-CGROUP-01/raw.json", "expect": "exit_zero", "porque": "Recalcula el veredicto desde la captura cruda (deltas de dmem.current y memory.current por clase, y la muerte o supervivencia sobre el tope); el control negativo 'nada' prueba que el instrumento ve cero y la fila alterada de managed hace que el verificador diga fail. No acredita que el motor de produccion use solo estas clases ni la autenticidad del origen de raw.json."}
---

## Root Cause
La ficha FEATURE-DMEM-PARCHE-REGION-Y-COBRO-SYSMEM-GB10-01 dejo anotado como abierto que "pinned y managed no se cobran" al cgroup, y el 2026-10-16 se repitio como hueco del aislamiento. Era una medicion que nadie habia hecho en las dos columnas: se miraba solo dmem.current. En GB10 la memoria unificada se reparte entre dos contadores segun la clase de asignacion, y cada uno tiene su propio tope.

## Medido (2026-10-16, `python3 tasks/evidence/FEATURE-DMEM-CLASES-DE-MEMORIA-POR-CGROUP-01/capture.py`, 12 corridas, cada una en su scope de systemd de usuario)
| clase (API de driver) | delta de dmem.current | delta de memory.current | pidiendo 2 GiB con MemoryMax=1G |
|---|---|---|---|
| nada (control) | ~0 | ~0 | n/a |
| device (cuMemAlloc) | +256 MiB | ~0 | sigue vivo: memory.max no lo frena, lo frena dmem.max |
| managed (cuMemAllocManaged, paginas tocadas) | ~0 | +257 MiB | muere (exit 137, `oom-kill` en el journal) |
| pinned (cuMemHostAlloc, paginas tocadas) | ~0 | +257 MiB | muere (exit 137, `oom-kill` en el journal) |
Control bajo el tope: managed de 512 MiB en el mismo scope de 1G pasa (exit 0). El texto anterior del foro ("el cgroup se salta la memoria unificada de CUDA") es cierto para device y falso para managed y pinned en esta pila (driver 580.178.04 parcheado, `uvm_disable_hmm=Y`).

## Regression Test
`tests/test_verify_clases_memoria.py` (29 pruebas, 100 % de cobertura del verificador): una prueba con control negativo por regla (nada con ruido, device cobrado a memory, managed cobrado a dmem, managed que sobrevive, device que muere, control que muere), unknown cuando faltan filas, y el verificador corrido como modulo sobre la captura real. `tests/test_dmem_tope.py` cubre el aviso (memory.max en max) y `--estado`; `tests/test_bb_bash.py` la fila de `bb status`.

## Verification Evidence
- pass: `tasks/evidence/FEATURE-DMEM-CLASES-DE-MEMORIA-POR-CGROUP-01.pass.txt` (verificador sobre raw.json: pass, rc 0).
- fail: `tasks/evidence/FEATURE-DMEM-CLASES-DE-MEMORIA-POR-CGROUP-01.fail.txt` (raw con managed alterado a exit=0: fail, rc 1).
- e2e: `tasks/evidence/FEATURE-DMEM-CLASES-DE-MEMORIA-POR-CGROUP-01.e2e.txt` (las 12 filas crudas, las lineas oom-kill del journal y `bb dmem-tope --estado`).

## Lo desarrollado
- `tools/verify_clases_memoria.py` y `tasks/evidence/FEATURE-DMEM-CLASES-DE-MEMORIA-POR-CGROUP-01/{capture.py,prueba.py}`: la captura reproducible y el verificador que recalcula.
- `bb dmem-tope` avisa (sin bloquear) si `memory.max` del motor o del slice del usuario esta en `max`: ahi managed y pinned no tendrian tope. Hoy el motor tiene 75 GiB (80530636800 B) y `user-1000.slice` 48 GiB (51539607552 B); `user.slice` esta en `max`, pero el aviso mira `user-<uid>.slice`, que es finito: la corrida real de `bb dmem-tope` (timer, 2026-10-16) registra `avisos: []`. El aviso se probo contra un arbol falso con `memory.max=max`, no contra el sistema real. (Correccion del 2026-10-16: la primera version de este texto decia que el aviso senalaba a user.slice en la corrida real; era falso.)
- `bb status` muestra el tope puesto (`bb dmem-tope --estado`) cuando el interruptor `dmem_tope` no esta en off. Hoy: sin tope, porque nadie ha aprobado el manifiesto.

## Limites declarados
- Solo se midieron paginas TOCADAS: una reserva managed sin tocar no deja huella en memory.current. La API de runtime de CUDA (cudaMallocManaged) no se midio por separado; se uso la de driver. PyTorch no se midio.
- El tope de memory.max mata el cgroup entero por OOM; no devuelve un error de asignacion al proceso.
- Que el motor de produccion solo use device, managed y pinned no se verifico: un mapeo de otra clase (p. ej. dma-buf) no esta cubierto.
- Una sola maquina, un solo driver (580.178.04 parcheado), 12 corridas.
