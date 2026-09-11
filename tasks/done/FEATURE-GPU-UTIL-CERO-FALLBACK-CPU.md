---
id: FEATURE-GPU-UTIL-CERO-FALLBACK-CPU
kind: task
title: Detectar 0% de utilizacion GPU con carga activa = fallback silencioso a CPU
status: done
severity: P2
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-09-09
closed_at: 2026-09-09
close_check: {"cmd": "grep -q 'fallback.*CPU\\|fallback a CPU' tasks/done/FEATURE-GPU-UTIL-CERO-FALLBACK-CPU.md", "expect": "exit_zero", "porque": "cierre solo con evidencia real (comando + salida + control negativo) en el done, patron DEBT-DGX-438."}
evidence: {"e2e": "tasks/evidence/FEATURE-GPU-UTIL-CERO-FALLBACK-CPU/e2e.txt", "fail": "tasks/evidence/FEATURE-GPU-UTIL-CERO-FALLBACK-CPU/fail.txt", "pass": "tasks/evidence/FEATURE-GPU-UTIL-CERO-FALLBACK-CPU/pass.txt", "pass_fixture_sintetico": "1 muestra con gpu_procs (38903MiB reservados) seguida de 4 muestras con gpu_util_pct=0.0, corridas por la MISMA logica python en aislamiento:\n  AVISO: 1 caso(s) de 0% de utilizacion sostenida con memoria de GPU reservada:\n    2026-09-09T18:50:03  proceso(s): VLLM::EngineCore (38903MiB)", "pass_real": "$ ./bin/bb scan '10 minutes ago' | grep 'GPU con memoria reservada'\n  GPU con memoria reservada y 0% util sostenido: 0\n(linea base real: vLLM sirviendo a 95% de utilizacion en la ventana probada, sin fallback)"}
reason: Se agrego una seccion a cmd_scan que correlaciona gpu_procs (memoria de GPU reservada, ya en el JSONL de Atlas 1 de cada 3 muestras) contra una racha de gpu_util_pct=0 sostenida (3 muestras seguidas, ~15s) -- mismo patron que el tok/s de trafico real ya adoptado, coste cero sobre datos existentes. Bug real atrapado: el primer intento imprimia '0%%' literal en el caso sin avisos porque ese print() no usaba el operador % de formato (el escape %% solo colapsa a % cuando SI hay formato aplicado) -- corregido a un simple '%' en el print plano.
---

## Root Cause

`atom_gpu_telemetry.py` ya muestrea utilizacion de GPU cada 5s, y `bb scan`
ya deriva tok/s del trafico real para pescar degradacion silenciosa de
inferencia. El mismo patron -- proceso activo, memoria de GPU reservada, 0%
de utilizacion sostenido -- indica un fallback silencioso a CPU, y antes de
este ticket nadie cruzaba "proceso con memoria de GPU" contra "0% de
utilizacion sostenido".

## Regression Test

No hay suite de pytest para este repo bash (`bin/bb` es el 100% del codigo ejecutable). La regresion mecanica es el propio `close_check` de esta ficha:

```
grep -q 'fallback.*CPU\|fallback a CPU' tasks/done/FEATURE-GPU-UTIL-CERO-FALLBACK-CPU.md
```

que falla si el marcador de codigo desaparece de `bin/bb`. La regresion real se corrio a mano contra datos de produccion antes y despues del fix -- ver Verification Evidence.

## Verification Evidence

**pass_real**:
```
$ ./bin/bb scan '10 minutes ago' | grep 'GPU con memoria reservada'
  GPU con memoria reservada y 0% util sostenido: 0
(linea base real: vLLM sirviendo a 95% de utilizacion en la ventana probada, sin fallback)
```

**pass_fixture_sintetico**:
```
1 muestra con gpu_procs (38903MiB reservados) seguida de 4 muestras con gpu_util_pct=0.0, corridas por la MISMA logica python en aislamiento:
  AVISO: 1 caso(s) de 0% de utilizacion sostenida con memoria de GPU reservada:
    2026-09-09T18:50:03  proceso(s): VLLM::EngineCore (38903MiB)
```

## Fichas HARVEST de origen (cosecha de Atlas, evaluadas 2026-09-09)

- HARVEST-348356-step-1-of-text-to-knowledge-graph-playbook-ha
- HARVEST-353683-dgx-spark-gpu-usage-0-after-24-hours-open-web
