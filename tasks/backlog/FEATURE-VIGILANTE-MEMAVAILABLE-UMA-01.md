---
id: FEATURE-VIGILANTE-MEMAVAILABLE-UMA-01
kind: task
domain: MEMORY
title: "Vigilante de MemAvailable para memoria unificada de GB10 que detenga la unidad antes del OOM del kernel"
status: open
severity: P2
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-10-12
close_check: {"cmd": "grep -q vigilante_uma_probado tasks/evidence/FEATURE-VIGILANTE-MEMAVAILABLE-UMA-01/medicion.txt", "expect": "exit_zero", "porque": "Voto de Luis 2026-10-12. Cierra con una medicion: un vigilante que, bajo una linea dura de MemAvailable, detiene la unidad culpable con registro de su origen, probado con un acaparador pequeno en un scope y con su control negativo; y la comparacion con el escalon y `earlyoom` ya presentes."}
---

## Antecedentes (lectura)
evanwtf/local-llm #456 (GB10): ni el `MemoryMax` de systemd ni `docker --memory` acotan las asignaciones CUDA; `earlyoom` es la unica red de seguridad del lado GPU; un guardia externo cada 2 s que detiene la unidad bajo una linea dura de MemAvailable evito OOM del kernel.
## Ya existe aqui
`earlyoom` (global, ve `MemAvailable` y swap) y el escalon de `bb-usable` (PSI + slice, un proceso). Falta decidir si una linea dura de `MemAvailable` anade algo: en los colapsos del 2026-10-11 `MemAvailable` marcaba 15-30 GB mientras el slice estaba estancado, asi que esa senal sola no los habria visto.
## Plan por partes
1. Medir en las muestras (`samples/*.jsonl`) cuantos episodios de estancamiento habria detectado una linea de MemAvailable a distintos valores (por serie, no por intuicion).
2. Si no aporta, documentarlo y cerrar con evidencia; si aporta, implementarlo en el portero.
