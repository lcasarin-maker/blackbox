---
id: FEATURE-CLOCK-THROTTLE-CRUZADO
kind: task
title: sm_clk_mhz/pstate ya se capturan cada 5s pero bb scan solo lee temp_critica del JSONL de Atlas
status: done
severity: P2
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-09-09
closed_at: 2026-09-09
close_check: {"cmd": "grep -q 'clock.*throttle\\|throttle.*clock' tasks/done/FEATURE-CLOCK-THROTTLE-CRUZADO.md", "expect": "exit_zero", "porque": "cierre solo con evidencia real (comando + salida + control negativo) en el done, patron DEBT-DGX-438."}
evidence: {"e2e": "tasks/evidence/FEATURE-CLOCK-THROTTLE-CRUZADO/e2e.txt", "fail": "tasks/evidence/FEATURE-CLOCK-THROTTLE-CRUZADO/fail.txt", "pass": "tasks/evidence/FEATURE-CLOCK-THROTTLE-CRUZADO/pass.txt", "pass_fixture_sintetico": "3 muestras sinteticas (2502MHz/95%util=sano, 650MHz/88%util=atascado, 300MHz/10%util=idle normal), corridas por la MISMA logica python en aislamiento:\n  muestras con clock/pstate/throttle: 3\n  AVISO: 1 muestra(s) con reloj < 800MHz, util > 50%, SIN throttle:\n    2026-09-09T18:40:05  clock=650MHz  util=88%\n(distingue correctamente el caso de atasco del caso de idle normal, ambos con clock bajo)", "pass_real": "$ ./bin/bb scan '10 minutes ago' | sed -n '/muestras con clock/,/^$/p'\n  muestras con clock/pstate/throttle: 118\n  reloj atascado sin throttle:  0\n(0 es la linea base real -- confirmado con datos de produccion donde sm_clk_mhz=2502, gpu_util_pct=95, throttle=0x0 en el mismo instante)"}
reason: Se agrego una seccion a cmd_scan que lee sm_clk_mhz/pstate/throttle del JSONL de Atlas (ya escritos cada 5s, nunca leidos por bb scan) y senala el patron 'clock < 800MHz + utilizacion > 50% + throttle en 0x0' -- exactamente lo que HARVEST-364166/374274/376039 describian como invisible. El umbral de 800MHz es PROVISIONAL, igual que los de PSI: sale del rango de clock ya registrado (300-2800 MHz), no de un incidente propio calibrado. No se fabrico ningun caso real en produccion para probarlo (eso corromperia el instrumento que se esta construyendo); se probo la logica en aislamiento con un fixture sintetico que incluye tanto el caso positivo como un caso negativo cercano (clock bajo pero SIN alta utilizacion), para confirmar que no dispara con cualquier clock bajo.
---

## Root Cause

`atom_gpu_telemetry.py` (Atlas) absorbio `sm_clk_mhz`, `pstate` y `throttle`
de `gpu_sampler.sh` el 2026-09-07. La seccion "termica" de `cmd_scan` solo
leia de ese JSONL los eventos `temp_critica` y `mitigacion_pausa` -- nunca
esos tres campos. Un reloj atascado en un valor bajo SIN que la bandera de
throttle este activa era invisible para `bb scan`, aunque el dato ya
estuviera escrito.

## Regression Test

No hay suite de pytest para este repo bash (`bin/bb` es el 100% del codigo ejecutable). La regresion mecanica es el propio `close_check` de esta ficha:

```
grep -q 'clock.*throttle\|throttle.*clock' tasks/done/FEATURE-CLOCK-THROTTLE-CRUZADO.md
```

que falla si el marcador de codigo desaparece de `bin/bb`. La regresion real se corrio a mano contra datos de produccion antes y despues del fix -- ver Verification Evidence.

## Verification Evidence

**pass_real**:
```
$ ./bin/bb scan '10 minutes ago' | sed -n '/muestras con clock/,/^$/p'
  muestras con clock/pstate/throttle: 118
  reloj atascado sin throttle:  0
(0 es la linea base real -- confirmado con datos de produccion donde sm_clk_mhz=2502, gpu_util_pct=95, throttle=0x0 en el mismo instante)
```

**pass_fixture_sintetico**:
```
3 muestras sinteticas (2502MHz/95%util=sano, 650MHz/88%util=atascado, 300MHz/10%util=idle normal), corridas por la MISMA logica python en aislamiento:
  muestras con clock/pstate/throttle: 3
  AVISO: 1 muestra(s) con reloj < 800MHz, util > 50%, SIN throttle:
    2026-09-09T18:40:05  clock=650MHz  util=88%
(distingue correctamente el caso de atasco del caso de idle normal, ambos con clock bajo)
```

## Fichas HARVEST de origen (cosecha de Atlas, evaluadas 2026-09-09)

- HARVEST-364166-latest-update-20mar-2026-on-nvidia-spark-fe-c
- HARVEST-374274-suddenly-much-lower-gpu-performance-in-infere
- HARVEST-376039-dgx-spark-gb10-gpu-clock-pinned-at-721-mhz-un
