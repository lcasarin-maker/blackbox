---
id: FEATURE-1358-CGROUP-01-REPRO
kind: task
domain: GPU
title: "Reproducir y delimitar el hueco de contabilidad CUDA"
status: open
severity: P2
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-10-02
close_check: {"cmd": "python3 -m tools.verify_cgroup_repro tasks/evidence/FEATURE-1358-CGROUP-01-REPRO/run-profile-integration.json", "expect": "exit_zero", "porque": "Recalcula fases, scopes, deltas y calibración CPU desde stdout crudo; fail por control fallido y unknown por observación ilegible. No acredita contención GPU ni autenticidad del origen."}
---

## Contexto y dependencias

Plan derivado de [la corrección del README](../../README.md#a-measured-cgroup-accounting-gap-on-this-gb10-stack) y [el informe histórico corregido](../evidence/nvidia-1358-comment.md). Fuente de colaboración: [NVIDIA #1358](https://github.com/NVIDIA/open-gpu-kernel-modules/issues/1358).

Dependencias: ninguna; punto de entrada del plan.

## Alcance

Reutilizar systemd-run, los archivos cgroup v2 y las capturas de Blackbox antes de añadir instrumentación. Crear un reproductor acotado que distinga cudaMalloc, cudaMallocManaged y la API realmente usada por PyTorch. Registrar versiones, boot ID, cgroup efectivo, tamaños solicitados, sincronización, memoria residente, memory.current/events/pressure, dmem.capacity/current y MemAvailable antes, durante y después de liberar.

Control positivo: asignación CPU anónima tocada que sí incremente memory.current. Control negativo: ejecución sin asignación GPU. Repetir con dos cgroups aislados y conservar comando, salida, tiempos y errores de colección. Usar asignaciones pequeñas y límites explícitos; la reproducción busca contabilidad, no provocar un cuelgue.

## Criterio de cierre

El arnés identifica cada API y su cgroup; el control CPU demuestra que el instrumento detecta cargos. Publicar las medidas originales y la repetición, incluida cualquier diferencia. Liberación y sincronización deben quedar observadas. Un resultado sin hueco también cierra la investigación si delimita exactamente la pila donde ocurre y donde no ocurre.

El close_check ejecuta el verificador de observaciones implementado. Rechaza entradas ausentes, inconsistentes e incompletas y tiene controles negativos de calibración CPU. La autenticidad del origen exige conservar los comandos y las capturas; la consistencia de un JSON por sí sola no la demuestra. La ficha conserva el ensayo completo como criterio de cierre.

## Avance del swarm — 2026-10-02

Ejecutor: Luna; coordinación: Codex. Arnés `tools/cgroup_repro.py`, con seis
scopes y solicitudes de 32 MiB: ninguna, CPU tocada, cudaMalloc dos veces,
cudaMallocManaged y PyTorch. Separó inicialización, llenado/sincronización
y liberación, con techo MemoryMax=512M y RuntimeMaxSec=60s por scope.

Resultados corregidos en `tasks/evidence/FEATURE-1358-CGROUP-01-REPRO/run.json`
y `run.txt`. CPU: +33554432 bytes; cudaMalloc: 0 bytes en ambas corridas;
managed: +33554432 bytes; PyTorch: 0 bytes después de warmup. Son incrementos
observados de memory.current, no trazas del asignador ni ahorro de memoria.
La capacidad dmem se leyó en la raíz, donde existe según el ABI; estaba vacía.
Faltó dmem.current en los seis scopes: could_not_run=6 y rc=2.
La reproducción histórica de 7 GiB se conserva como entrada y no se repitió
a ese tamaño. La ficha permanece abierta para completar observación y cierre.

Verificación final del arnés: 32 tests y 100% de sentencias/ramas; Ruff y Pyright pasan. Salidas y control negativo en `tasks/evidence/FEATURE-1358-CGROUP-01-REPRO/verification.txt`.

## Verificador de observaciones — 2026-10-02

Implementado `tools/verify_cgroup_repro.py`: ignora el veredicto guardado y recalcula las seis APIs desde stdout JSONL, exige fases ordenadas, PID/scope estable y scopes independientes, comprueba tamaño solicitado y control CPU frente al ruido sin asignación y liberación. Retorna pass=0, fail=1 y unknown=2. Los controles negativos eliminan fases, duplican scopes, alteran lecturas y neutralizan el incremento/liberación CPU. El fixture positivo es sintético y no se presenta como captura real.

La captura histórica retorna unknown y conserva los deltas legibles. Cuenta 23 lecturas dmem.current ilegibles por fase, repartidas en seis scopes; este conteo por observación difiere del conteo anterior de seis scopes. El verificador verifica consistencia, no puede autenticar un JSON fabricado ni afirmar ownership/contención. Continúa abierta.


## Índice de propuestas registradas del swarm NVIDIA categoría 721

- **`BB-DASHBOARD-MEMORY-UNIT-CALIBRATION`** — DGX Spark users report that dashboard memory usage disagrees with `free`/`/proc/meminfo`, potentially mixing GiB and GB; one reply says an update fixed it while a later user says the mismatch persists. In a separate report, a vLLM model… Fuente: [350359](https://forums.developer.nvidia.com/t/350359/1).
- **`BB-RAY-UMA-OBJECT-STORE-MONITOR-GATE`** — On a reported TP=3 MiniMax-M3 workload, Ray reserves roughly 30% (~36GB) of per-node RAM for an object store the author says TP does not use; head also loads ~84GB shard plus KV, triggering driver OOM during weight load. After warmup,… Fuente: [373387](https://forums.developer.nvidia.com/t/373387/1).
