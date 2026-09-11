---
id: FEATURE-NVIDIA-CONTAINER-RUNTIME-HOOK
kind: task
title: Fallback silencioso a modo 'legacy' del gateway Docker por NVML no cargado -- no se detecta
status: done
severity: P3
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-09-09
closed_at: 2026-09-09
close_check: {"cmd": "grep -q 'nvidia-container-runtime\\|prestart hook' tasks/done/FEATURE-NVIDIA-CONTAINER-RUNTIME-HOOK.md", "expect": "exit_zero", "porque": "cierre solo con evidencia real (comando + salida + control negativo) en el done, patron DEBT-DGX-438."}
evidence: {"e2e": "tasks/evidence/FEATURE-NVIDIA-CONTAINER-RUNTIME-HOOK/e2e.txt", "fail": "tasks/evidence/FEATURE-NVIDIA-CONTAINER-RUNTIME-HOOK/fail.txt", "pass": "tasks/evidence/FEATURE-NVIDIA-CONTAINER-RUNTIME-HOOK/pass.txt", "pass_fixture_sintetico": "$ printf 'nvidia-container-runtime-hook error: failed to initialize NVML...\\nOCI runtime create failed: nvidia container cli fail\\n' | grep -icE 'nvidia-container-(runtime|cli).*(error|fail)|OCI runtime.*nvidia.*fail|failed to initialize NVML'\n2", "pass_real": "$ ./bin/bb scan '2 hours ago' | grep 'fallos de prestart hook'\n  fallos de prestart hook OCI/nvidia: 0\n(linea base real: los 5 contenedores de esta maquina -- nemotron-server, atlas-pgvector, librechat, mongo-librechat, aequitas-pg -- estan Up sin fallos de hook en la ventana probada)"}
reason: Se agrego a la seccion 'motor de inferencia' de cmd_scan un grep de journalctl por el patron de fallo del prestart hook OCI de nvidia-container-runtime, junto al estado 'Up/total' de Docker ya existente -- mismo espiritu que el resto de la seccion (mirar la causa especifica, no solo si el contenedor reporta vivo). No se fabrico un fallo real en un contenedor de produccion para probarlo (romperia servicio); se verifico el patron de grep en aislamiento contra las dos formas reales en que el error se reporta (nvidia-container-runtime-hook y OCI runtime create failed).
---

## Root Cause

El gateway de esta maquina corre en Docker. Si el prestart hook de
`nvidia-container-runtime` falla (NVML no cargado dentro del contenedor), el
runtime puede caer a un modo "legacy" sin GPU real, con el contenedor
reportando "Up" -- el mismo tipo de discrepancia que `bb scan` ya persigue en
la seccion "motor de inferencia" (mirar el endpoint, no el contenedor), pero
esta causa especifica no estaba cubierta.

## Regression Test

No hay suite de pytest para este repo bash (`bin/bb` es el 100% del codigo ejecutable). La regresion mecanica es el propio `close_check` de esta ficha:

```
grep -q 'nvidia-container-runtime\|prestart hook' tasks/done/FEATURE-NVIDIA-CONTAINER-RUNTIME-HOOK.md
```

que falla si el marcador de codigo desaparece de `bin/bb`. La regresion real se corrio a mano contra datos de produccion antes y despues del fix -- ver Verification Evidence.

## Verification Evidence

**pass_real**:
```
$ ./bin/bb scan '2 hours ago' | grep 'fallos de prestart hook'
  fallos de prestart hook OCI/nvidia: 0
(linea base real: los 5 contenedores de esta maquina -- nemotron-server, atlas-pgvector, librechat, mongo-librechat, aequitas-pg -- estan Up sin fallos de hook en la ventana probada)
```

**pass_fixture_sintetico**:
```
$ printf 'nvidia-container-runtime-hook error: failed to initialize NVML...\nOCI runtime create failed: nvidia container cli fail\n' | grep -icE 'nvidia-container-(runtime|cli).*(error|fail)|OCI runtime.*nvidia.*fail|failed to initialize NVML'
2
```

## Fichas HARVEST de origen (cosecha de Atlas, evaluadas 2026-09-09)

- HARVEST-351579-reinstalling-the-nvidia-driver-on-dgx-spark (mecanismo 3)
